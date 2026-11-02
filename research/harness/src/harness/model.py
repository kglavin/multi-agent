"""Model interface and a stub model that needs no API key."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class Message:
    role: str  # "system", "user", "assistant", or "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class Response:
    text: str
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int
    model: str
    latency_s: float = 0.0


class Model(Protocol):
    name: str

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Response: ...


def estimate_tokens(text: str) -> int:
    """Rough count, four characters per token. Used only by the stub."""
    return max(1, len(text) // 4)


def _message_text(m: Message) -> str:
    return m.content + "".join(f"{c.name}{c.args}" for c in m.tool_calls)


Policy = Callable[[list[Message], list[ToolSpec]], tuple[str, list[ToolCall]]]


def answer_policy(text: str = "stub answer") -> Policy:
    """A policy that always replies with the same text and calls no tools."""
    return lambda messages, tools: (text, [])


class StubModel:
    """Replies from a policy function or a fixed script, and bills by estimated tokens.

    Token counts are estimates, so cost figures from stub runs are only for
    checking the harness, never for results.
    """

    def __init__(self, policy: Policy | None = None, script: list[tuple[str, list[ToolCall]]] | None = None,
                 name: str = "stub"):
        if policy is None and script is None:
            policy = answer_policy()
        self.policy = policy
        self.script = list(script) if script is not None else None
        self.name = name

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        start = time.perf_counter()
        if self.script is not None:
            if not self.script:
                raise RuntimeError("stub script exhausted")
            text, calls = self.script.pop(0)
        else:
            text, calls = self.policy(messages, tools)
        prompt = "".join(_message_text(m) for m in messages) + "".join(t.name + t.description for t in tools)
        return Response(
            text=text,
            tool_calls=calls,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text + "".join(f"{c.name}{c.args}" for c in calls)),
            model=self.name,
            latency_s=time.perf_counter() - start,
        )
