"""Per-run logging to JSONL and a budget that stops a run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from .model import Response


class BudgetExceeded(Exception):
    pass


class Budget:
    """Caps on tokens and model calls. Shared by every agent in one run."""

    def __init__(self, max_tokens: int | None = None, max_calls: int | None = None):
        self.max_tokens = max_tokens
        self.max_calls = max_calls
        self.tokens = 0
        self.calls = 0

    def charge(self, response: Response) -> None:
        self.tokens += response.input_tokens + response.output_tokens
        self.calls += 1
        if self.max_tokens is not None and self.tokens > self.max_tokens:
            raise BudgetExceeded(f"tokens {self.tokens} > {self.max_tokens}")
        if self.max_calls is not None and self.calls > self.max_calls:
            raise BudgetExceeded(f"calls {self.calls} > {self.max_calls}")


class Recorder:
    """Writes one JSON object per event. Every event carries the run's fields."""

    def __init__(self, out: TextIO, **run_fields):
        self.out = out
        self.run_fields = run_fields

    def event(self, kind: str, **fields) -> None:
        self.out.write(json.dumps({**self.run_fields, "event": kind, **fields}, default=str) + "\n")

    def model_call(self, agent: str, step: int, r: Response) -> None:
        self.event(
            "model_call",
            agent=agent,
            step=step,
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            latency_s=round(r.latency_s, 4),
            reasoning_chars=len(r.reasoning),
            reasoning=r.reasoning,
            text=r.text,
            tool_calls=[{"name": c.name, "args": c.args} for c in r.tool_calls],
        )

    def tool_result(self, agent: str, step: int, name: str, args: dict, result: str) -> None:
        self.event("tool_result", agent=agent, step=step, name=name, args=args, chars=len(result))


def read_log(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f]
