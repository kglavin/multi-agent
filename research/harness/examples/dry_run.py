"""Runs C1 to C4 on a toy lookup task with the stub model. Checks the harness, not agents.

    uv run python examples/dry_run.py [out_dir]
"""

import json
import re
import sys
import tempfile
from pathlib import Path

from harness import (FINAL, Case, StubModel, Tool, ToolCall, ToolSpec, direct, group_chat, orchestrator,
                     run_experiment, single, summarise)

CAPITALS = {"france": "Paris", "japan": "Tokyo", "kenya": "Nairobi"}

LOOKUP = Tool(
    ToolSpec("lookup", "Return the capital of a country.",
             {"type": "object", "properties": {"country": {"type": "string"}}, "required": ["country"]}),
    lambda country: CAPITALS.get(country.lower(), "unknown"),
)


def policy(messages, tools):
    """Stands in for a model: delegate if it can, otherwise look up, then answer."""
    names = {t.name for t in tools}
    system, last = messages[0].content, messages[-1]
    if last.role == "tool":
        prefix = f"{FINAL} " if FINAL in system else ""
        return prefix + last.content, []
    if "delegate" in names:
        return "", [ToolCall("d1", "delegate", {"task": last.content})]
    match = re.search(r"capital of (\w+)", last.content)
    if "lookup" in names and match:
        return "", [ToolCall("l1", "lookup", {"country": match.group(1)})]
    return "I do not know", []


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="dry-run-"))
    model = StubModel(policy)
    chat_system = f"Answer the task. Start your answer with '{FINAL}'."
    configs = {
        "C1-direct": direct(model, "Answer the question."),
        "C2-single": single(model, "Answer using the tools.", [LOOKUP]),
        "C3-orchestrator": orchestrator(model, "Delegate the work.", "Answer using the tools.", [LOOKUP]),
        "C4-group-chat": group_chat(model, {"researcher": chat_system, "checker": chat_system}, [LOOKUP]),
    }
    cases = [Case(c, f"What is the capital of {c}?", capital) for c, capital in CAPITALS.items()]
    results = run_experiment(out, cases, configs, runs=2, max_tokens=5000)
    print(json.dumps(summarise(results), indent=2))
    print(f"logs in {out}")


if __name__ == "__main__":
    main()
