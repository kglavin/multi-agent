"""Runs R5: every case under C1 to C4, several times, one output directory per suite.

    uv run python run.py --pilot                 # 1 case per suite, 1 run: 12 runs
    uv run python run.py --runs 5                # full study: 600 runs
    uv run python run.py --suites S2 --configs C2 C3 --cases 2 --runs 1

Models are listed in MODELS. Ollama models read OLLAMA_BASE_URL and OLLAMA_CONTEXT_LIMIT.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from harness import FINAL, StubModel, ToolCall, direct, group_chat, ollama, orchestrator, run_experiment, single
from harness.record import read_log
from harness.report import build_report

import prompts
from cases import CASES_FILE, Case
from score import score
from tools import corpus_tools

HERE = Path(__file__).parent


def dry_policy(messages, tools):
    """Stub behaviour that exercises the real tools: list the corpus, read the first
    file, then answer. Orchestrators delegate. Scores are meaningless."""
    names = {t.name for t in tools}
    system, last = messages[0].content, messages[-1]
    done = sum(1 for m in messages if m.role == "tool")
    if "delegate" in names and done == 0:
        return "", [ToolCall("d", "delegate", {"task": messages[1].content})]
    if "list_files" in names and done == 0:
        return "", [ToolCall("l", "list_files", {"path": "."})]
    if "read_file" in names and done == 1:
        first = last.content.splitlines()[0] if last.content else "."
        return "", [ToolCall("r", "read_file", {"path": first.rstrip("/")})]
    return (f"{FINAL} []" if FINAL in system else "[]"), []


MODELS = {
    "stub": lambda: StubModel(dry_policy, name="stub"),
    "qwen3:8b": lambda: ollama("qwen3:8b"),
    "qwen3:8b-nothink": lambda: ollama("qwen3:8b", think=False),
}


def load_suite(suite: str, limit: int | None) -> tuple[list[Case], Path | None]:
    rows = [json.loads(line) for line in CASES_FILE.read_text().splitlines()]
    rows = [r for r in rows if r["suite"] == suite][:limit]
    corpus = HERE / rows[0]["corpus"] if rows[0]["corpus"] else None
    return [Case(r["id"], r["task"], {"kind": r["kind"], "value": r["expected"]}) for r in rows], corpus


def build_configs(model, corpus: Path | None, max_steps: int) -> dict:
    """S1 has no corpus, so its agents get no tools."""
    tools = corpus_tools(corpus) if corpus else []
    return {
        "C1": direct(model, prompts.DIRECT),
        "C2": single(model, prompts.SINGLE, tools, max_steps),
        "C3": orchestrator(model, prompts.ORCHESTRATOR, prompts.WORKER, tools, max_steps),
        "C4": group_chat(model, prompts.GROUP, tools, max_rounds=3, max_steps=max_steps),
    }


def duplicate_tool_calls(log: list[dict]) -> Counter:
    """M5: per run, tool calls that repeat an earlier call with the same name and arguments."""
    seen, dupes = set(), Counter()
    for e in log:
        if e["event"] == "tool_result" and e["name"] != "delegate":
            key = (e["run_id"], e["name"], json.dumps(e["args"], sort_keys=True))
            if key in seen:
                dupes[e["run_id"]] += 1
            seen.add(key)
    return dupes


def suite_table(out: Path) -> list[str]:
    results = read_log(out / "results.jsonl")
    log = read_log(out / "log.jsonl")
    dupes = duplicate_tool_calls(log)
    biggest = max((e["chars"] for e in log if e["event"] == "tool_result"), default=0)
    rows = []
    for config in sorted({r["config"] for r in results}):
        rs = [r for r in results if r["config"] == config]
        n = len(rs)
        rows.append(f"| {out.name} | {config} | {n} | {sum(r['score'] for r in rs) / n:.2f} "
                    f"| {sum(r['tokens'] for r in rs) / n:.0f} | {sum(r['calls'] for r in rs) / n:.1f} "
                    f"| {sum(r['wall_s'] for r in rs) / n:.2f} | {sum(dupes[r['run_id']] for r in rs) / n:.1f} "
                    f"| {sum(1 for r in rs if r['stopped'])} |")
    return rows + [f"<!-- {out.name}: largest tool result {biggest} characters -->"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="stub", choices=MODELS)
    p.add_argument("--suites", nargs="+", default=["S1", "S2", "S3"])
    p.add_argument("--configs", nargs="+", default=["C1", "C2", "C3", "C4"])
    p.add_argument("--cases", type=int, default=None, help="cases per suite, default all 10")
    p.add_argument("--case-ids", nargs="+", default=None, help="only these cases, such as S3-09 S3-10")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--pilot", action="store_true", help="1 case per suite and 1 run")
    p.add_argument("--max-tokens", type=int, default=None, help="per run")
    p.add_argument("--max-calls", type=int, default=None, help="per run")
    p.add_argument("--max-steps", type=int, default=20, help="per agent")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    if a.pilot:
        a.cases, a.runs = 1, 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out or HERE / "out" / f"{a.model}-{stamp}"
    model = MODELS[a.model]()
    table = ["| Suite | Config | Runs | Mean score | Mean tokens | Mean calls | Mean seconds "
             "| Mean duplicate tool calls | Stopped |", "|---|---|---|---|---|---|---|---|---|"]
    for suite in a.suites:
        cases, corpus = load_suite(suite, a.cases)
        if a.case_ids:
            cases = [c for c in cases if c.id in a.case_ids]
        configs = {k: v for k, v in build_configs(model, corpus, a.max_steps).items() if k in a.configs}
        suite_out = out / suite
        run_experiment(suite_out, cases, configs, a.runs, score=score, max_tokens=a.max_tokens,
                       max_calls=a.max_calls)
        (suite_out / "report.md").write_text(build_report(suite_out))
        table += suite_table(suite_out)
    summary = "\n".join(table) + "\n"
    (out / "summary.md").write_text(f"# R5 {out.name}\n\nModel: {a.model}\n\n{summary}")
    print(re.sub(r"<!--.*?-->\n", "", summary))
    print("\n".join(re.findall(r"<!-- (.*?) -->", summary)))
    print(f"output in {out}")


if __name__ == "__main__":
    main()
