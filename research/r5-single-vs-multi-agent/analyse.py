"""Tables for the R5 write-up from one or more run directories.

    uv run python analyse.py out/full-qwen3-8b/S1-run/S1 out/full-qwen3-8b/S2-run/S2 \
        out/full-qwen3-8b/S3-run/S3 out/full-qwen3-8b/S3-resume-run/S3

A case found in a later directory replaces that case from earlier ones, so a re-run of
some cases can be merged with the run it repairs. Confidence intervals are 95% bootstrap
intervals over cases: runs of the same case are not independent, so cases are resampled
and each case contributes the mean of its runs.
"""

from __future__ import annotations

import random
import statistics as st
import sys
from pathlib import Path

from harness.record import read_log

from run import duplicate_tool_calls

CONFIGS = ["C1", "C2", "C3", "C4"]


def load(dirs: list[Path]) -> tuple[list[dict], dict]:
    by_case: dict[str, list[dict]] = {}
    dupes = {}
    for d in dirs:
        rows = read_log(d / "results.jsonl")
        for case in {r["case"] for r in rows}:
            by_case[case] = [r for r in rows if r["case"] == case]
        dupes.update(duplicate_tool_calls(read_log(d / "log.jsonl")))
    return [r for case in sorted(by_case) for r in by_case[case]], dupes


def case_means(rows: list[dict]) -> list[float]:
    cases = sorted({r["case"] for r in rows})
    return [st.mean(r["score"] for r in rows if r["case"] == c) for c in cases]


def bootstrap(values: list[float], n: int = 10_000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def tables(rows: list[dict], dupes: dict) -> str:
    out = ["| Suite | Config | Runs | Mean score | 95% CI | Mean tokens | Mean calls | Mean seconds "
           "| Mean duplicate tool calls | Stopped |", "|---|---|---|---|---|---|---|---|---|---|"]
    for suite in sorted({r["case"][:2] for r in rows}):
        for config in CONFIGS:
            rs = [r for r in rows if r["case"].startswith(suite) and r["config"] == config]
            if not rs:
                continue
            lo, hi = bootstrap(case_means(rs))
            out.append(f"| {suite} | {config} | {len(rs)} | {st.mean(r['score'] for r in rs):.2f} "
                       f"| {lo:.2f} to {hi:.2f} | {st.mean(r['tokens'] for r in rs):,.0f} "
                       f"| {st.mean(r['calls'] for r in rs):.1f} | {st.mean(r['wall_s'] for r in rs):.0f} "
                       f"| {st.mean(dupes.get(r['run_id'], 0) for r in rs):.1f} "
                       f"| {sum(1 for r in rs if r['stopped'])} |")
    out += ["", "| Case | " + " | ".join(CONFIGS) + " |", "|---|" + "---|" * len(CONFIGS)]
    for case in sorted({r["case"] for r in rows}):
        cells = [st.mean(r["score"] for r in rows if r["case"] == case and r["config"] == c) for c in CONFIGS]
        out.append(f"| {case} | " + " | ".join(f"{v:.2f}" for v in cells) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    print(tables(*load([Path(a) for a in sys.argv[1:]])))
