"""Runs every case under every configuration, several times, and logs it all."""

from __future__ import annotations

import json
import random
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .configs import Config
from .record import Budget, BudgetExceeded, Recorder


@dataclass
class Case:
    id: str
    task: str
    expected: Any = None


Score = Callable[[Case, str], float]


def exact_match(case: Case, answer: str) -> float:
    return float(answer.strip().lower() == str(case.expected).strip().lower())


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_experiment(out_dir: Path, cases: list[Case], configs: dict[str, Config], runs: int,
                   score: Score = exact_match, seed: int = 0, max_tokens: int | None = None,
                   max_calls: int | None = None) -> list[dict]:
    """Writes meta.json, log.jsonl (every event), and results.jsonl (one row per run).

    The budget applies to each run separately. A run that exceeds it scores 0 and is
    marked stopped, and the experiment continues.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "started": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "cases": len(cases),
        "configs": list(configs),
        "runs": runs,
        "seed": seed,
        "max_tokens": max_tokens,
        "max_calls": max_calls,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    results = []
    with open(out_dir / "log.jsonl", "w") as log, open(out_dir / "results.jsonl", "w") as res:
        for case in cases:
            for config_name, config in configs.items():
                for i in range(runs):
                    run_seed = seed + i
                    random.seed(run_seed)
                    run_id = f"{case.id}/{config_name}/{i}"
                    recorder = Recorder(log, run_id=run_id)
                    budget = Budget(max_tokens, max_calls)
                    stopped = None
                    start = time.perf_counter()
                    try:
                        answer = config(case.task, recorder, budget)
                    except BudgetExceeded as e:
                        answer, stopped = "", str(e)
                        recorder.event("budget_exceeded", reason=stopped)
                    row = {
                        "run_id": run_id,
                        "case": case.id,
                        "config": config_name,
                        "run": i,
                        "seed": run_seed,
                        "answer": answer,
                        "score": 0.0 if stopped else score(case, answer),
                        "tokens": budget.tokens,
                        "calls": budget.calls,
                        "wall_s": round(time.perf_counter() - start, 4),
                        "stopped": stopped,
                    }
                    res.write(json.dumps(row) + "\n")
                    results.append(row)
    return results


def summarise(results: list[dict]) -> dict[str, dict]:
    """Mean score, tokens, and calls per configuration."""
    groups = defaultdict(list)
    for r in results:
        groups[r["config"]].append(r)
    return {
        name: {
            "runs": len(rows),
            "mean_score": sum(r["score"] for r in rows) / len(rows),
            "mean_tokens": sum(r["tokens"] for r in rows) / len(rows),
            "mean_calls": sum(r["calls"] for r in rows) / len(rows),
            "stopped": sum(1 for r in rows if r["stopped"]),
        }
        for name, rows in groups.items()
    }
