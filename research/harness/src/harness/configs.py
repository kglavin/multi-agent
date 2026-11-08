"""Agent configurations built from the one loop in agent.py.

Each configuration is a function (task, recorder, budget) -> answer, so the runner
treats them alike and only the structure differs. These are R5's C1 to C4.
"""

from __future__ import annotations

from typing import Callable

from .agent import Agent, Tool
from .model import Model, ToolSpec
from .record import Budget, Recorder

Config = Callable[[str, Recorder, Budget], str]

FINAL = "FINAL ANSWER:"


def direct(model: Model, system: str) -> Config:
    """C1: one model call, no tools."""
    agent = Agent("direct", model, system, max_steps=1)
    return agent.run


def single(model: Model, system: str, tools: list[Tool], max_steps: int = 20) -> Config:
    """C2: one agent loop with all tools."""
    agent = Agent("single", model, system, tools, max_steps)
    return agent.run


def orchestrator(model: Model, system: str, worker_system: str, tools: list[Tool],
                 max_steps: int = 20) -> Config:
    """C3: an orchestrator whose only tool is `delegate`. Each delegation starts a new
    worker with its own context and all the tools."""

    def run(task: str, recorder: Recorder, budget: Budget) -> str:
        count = 0

        def delegate(task: str) -> str:
            if not isinstance(task, str):
                raise TypeError(f"task must be a string, got {type(task).__name__}")
            nonlocal count
            count += 1
            worker = Agent(f"worker-{count}", model, worker_system, tools, max_steps)
            return worker.run(task, recorder, budget)

        spec = ToolSpec(
            "delegate",
            "Give a self-contained subtask to a new worker agent and get its answer back.",
            {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]},
        )
        return Agent("orchestrator", model, system, [Tool(spec, delegate)], max_steps).run(task, recorder, budget)

    return run


def group_chat(model: Model, systems: dict[str, str], tools: list[Tool], max_rounds: int = 5,
               max_steps: int = 20) -> Config:
    """C4: agents take turns in a fixed order and share one transcript.

    Every turn sends the whole transcript so far, so its cost grows with each turn.
    Tool calls stay inside the agent's turn. Only its final text joins the transcript.
    The chat ends when a message contains FINAL, or after max_rounds full rotations.
    """
    agents = [Agent(name, model, system, tools, max_steps) for name, system in systems.items()]

    def run(task: str, recorder: Recorder, budget: Budget) -> str:
        transcript: list[str] = []
        for _ in range(max_rounds):
            for agent in agents:
                context = "\n\n".join([f"Task: {task}", *transcript])
                text = agent.run(context, recorder, budget)
                transcript.append(f"[{agent.name}] {text}")
                if FINAL in text:
                    return text.split(FINAL, 1)[1].strip()
        recorder.event("round_cap", max_rounds=max_rounds)
        return transcript[-1].split("] ", 1)[1] if transcript else ""

    return run
