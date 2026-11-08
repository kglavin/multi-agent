"""One agent loop: call the model, run any tool calls, repeat until a text answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .model import Message, Model, ToolSpec
from .record import Budget, BudgetExceeded, Recorder


EMPTY_NUDGE = "Your last reply was empty. Call a tool, or give your answer in the format the task asks for."


@dataclass
class Tool:
    spec: ToolSpec
    fn: Callable[..., str]


class Agent:
    def __init__(self, name: str, model: Model, system: str, tools: list[Tool] | None = None,
                 max_steps: int = 20):
        self.name = name
        self.model = model
        self.system = system
        self.tools = {t.spec.name: t for t in tools or []}
        self.max_steps = max_steps

    def step(self, messages: list[Message], recorder: Recorder, budget: Budget, step: int):
        """One model call. Returns the response after logging and charging it."""
        r = self.model.complete(messages, [t.spec for t in self.tools.values()])
        recorder.model_call(self.name, step, r)
        budget.charge(r)
        return r

    def run(self, task: str, recorder: Recorder, budget: Budget) -> str:
        """Runs in a fresh context. Returns the final text, or "" if the step cap is hit or the
        reply is still empty after one nudge."""
        messages = [Message("system", self.system), Message("user", task)]
        nudged = False
        for step in range(self.max_steps):
            r = self.step(messages, recorder, budget, step)
            messages.append(Message("assistant", r.text, r.tool_calls))
            if not r.tool_calls:
                if r.text.strip() or nudged:
                    return r.text
                # An empty reply (no text, no tool call) gets one fixed nudge.
                nudged = True
                recorder.event("empty_reply", agent=self.name, step=step)
                messages.append(Message("user", EMPTY_NUDGE))
                continue
            for call in r.tool_calls:
                tool = self.tools.get(call.name)
                if tool is None:
                    result = f"error: unknown tool {call.name}"
                else:
                    try:
                        result = tool.fn(**call.args)
                    except BudgetExceeded:  # includes ContextOverflow: stops the whole run
                        raise
                    except Exception as e:  # bad arguments from the model go back to it as an error
                        result = f"error: {type(e).__name__}: {e}"
                recorder.tool_result(self.name, step, call.name, call.args, result)
                messages.append(Message("tool", result, tool_call_id=call.id))
        recorder.event("step_cap", agent=self.name, max_steps=self.max_steps)
        return ""
