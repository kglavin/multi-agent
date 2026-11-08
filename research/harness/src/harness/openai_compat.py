"""A model on any server with an OpenAI-style /chat/completions endpoint, such as Ollama.

    OLLAMA_BASE_URL       default http://localhost:11434/v1
    OLLAMA_CONTEXT_LIMIT  tokens per request. A prompt at or over it stops the run.

Ollama cuts an over-long prompt from the front without an error, so the model answers
from a prompt it did not fully see. With a context limit set, such a call raises
ContextOverflow, which stops the run like a budget stop and records why.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request

from .model import Message, Response, ToolCall, ToolSpec
from .record import BudgetExceeded


class ContextOverflow(BudgetExceeded):
    pass


def _to_wire(m: Message) -> dict:
    out: dict = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [{"id": c.id, "type": "function",
                              "function": {"name": c.name, "arguments": json.dumps(c.args)}} for c in m.tool_calls]
    if m.tool_call_id:
        out["tool_call_id"] = m.tool_call_id
    return out


def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"_unparsed": raw}
    return value if isinstance(value, dict) else {"_unparsed": raw}


def text_tool_calls(text: str, tool_names: set[str]) -> list[ToolCall]:
    """Tool calls written as text, which qwen3 behind Ollama sometimes does: the whole
    reply is one JSON object per line, each {"name": <known tool>, "arguments": {...}},
    optionally in a code fence or <tool_call> tags. Anything else is left as text.
    Recovered calls get ids starting text_ so the log shows them."""
    body = re.sub(r"</?tool_call>|^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    if not body:
        return []
    calls = []
    for i, line in enumerate(l for l in body.splitlines() if l.strip()):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not (isinstance(obj, dict) and obj.get("name") in tool_names and isinstance(obj.get("arguments"), dict)):
            return []
        calls.append(ToolCall(f"text_{i}", obj["name"], obj["arguments"]))
    return calls


class OpenAICompatModel:
    def __init__(self, model: str, base_url: str | None = None, name: str | None = None,
                 context_limit: int | None = None, extra: dict | None = None, timeout_s: float = 900,
                 retries: int = 8, api_key: str | None = None):
        self.model = model
        self.name = name or model
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        limit = context_limit or os.environ.get("OLLAMA_CONTEXT_LIMIT")
        self.context_limit = int(limit) if limit else None
        self.extra = extra or {}
        self.timeout_s = timeout_s
        self.retries = retries
        self.api_key = api_key

    def _post(self, payload: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(f"{self.base_url}/chat/completions", json.dumps(payload).encode(), headers)
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                # The server answered. A 4xx is a bad request and will not improve on retry.
                if e.code < 500 or attempt == self.retries:
                    raise RuntimeError(f"HTTP {e.code} from {self.base_url}: {e.read()[:500]!r}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
                if attempt == self.retries:
                    raise
                time.sleep(min(60, 2 ** attempt))  # about 4 minutes in all before giving up
        raise AssertionError("unreachable")

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        payload = {"model": self.model, "messages": [_to_wire(m) for m in messages], **self.extra}
        if tools:
            payload["tools"] = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                                  "parameters": t.parameters}} for t in tools]
        start = time.perf_counter()
        data = self._post(payload)
        latency = time.perf_counter() - start
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        if self.context_limit and prompt_tokens >= self.context_limit:
            raise ContextOverflow(f"prompt {prompt_tokens} tokens reached the context limit {self.context_limit}")
        msg = data["choices"][0]["message"]
        calls = [ToolCall(c.get("id") or f"call_{i}", c["function"]["name"], _args(c["function"].get("arguments")))
                 for i, c in enumerate(msg.get("tool_calls") or [])]
        text = msg.get("content") or ""
        if not calls and tools:
            calls = text_tool_calls(text, {t.name for t in tools})
            if calls:
                text = ""
        return Response(
            text=text,
            tool_calls=calls,
            input_tokens=prompt_tokens,
            output_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", self.model),
            latency_s=latency,
            reasoning=msg.get("reasoning") or msg.get("reasoning_content") or "",
        )


def ollama(model: str, think: bool = True) -> OpenAICompatModel:
    """An Ollama model. think=False sends reasoning_effort "none", which Ollama 0.40
    honours on this endpoint."""
    extra = {} if think else {"reasoning_effort": "none"}
    return OpenAICompatModel(model, name=model if think else f"{model}-nothink", extra=extra)
