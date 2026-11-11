"""Tables for the R14 LLM results: one row per condition, the mean across seeds with
the range in brackets.

    uv run python analyse_llm.py out/llm-full/nothink/results.jsonl
    uv run python analyse_llm.py out/llm-full/nothink/results.jsonl --seed 0
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

ORDER = ["homogeneous", "varied_prompts", "private_info", "varied_models", "rule-diverse", "rule-homogeneous"]
MEASURES = [("mean_attendance", "Mean attendance", "{:.1f}"), ("sd_attendance", "Attendance SD", "{:.1f}"),
            ("crowded_fraction", "Crowded fraction", "{:.2f}"), ("reward_gini", "Reward Gini", "{:.2f}"),
            ("mean_reward", "Mean reward", "{:.1f}")]


def table(rows: list[dict]) -> str:
    out = ["| Condition | Seeds | " + " | ".join(label for _, label, _ in MEASURES) + " | Unparseable | Mean tokens |",
           "|---|---|" + "---|" * (len(MEASURES) + 2)]
    for condition in [c for c in ORDER if any(r["condition"] == c for r in rows)]:
        rs = [r for r in rows if r["condition"] == condition]
        cells = []
        for key, _, fmt in MEASURES:
            values = [r[key] for r in rs]
            cell = fmt.format(st.mean(values))
            if len(rs) > 1:
                cell += f" ({fmt.format(min(values))} to {fmt.format(max(values))})"
            cells.append(cell)
        llm = "tokens" in rs[0]
        unparseable = str(sum(r["unparseable"] for r in rs)) if llm else ""
        tokens = f"{st.mean(r['tokens'] for r in rs):,.0f}" if llm else ""
        out.append(f"| {condition} | {len(rs)} | " + " | ".join(cells) + f" | {unparseable} | {tokens} |")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument("--seed", type=int, default=None, help="only this seed")
    a = p.parse_args()
    rows = [json.loads(line) for line in a.results.read_text().splitlines()]
    # Each run_llm.py call adds the rule-based rows for its seed, so a seed run in two calls repeats them.
    rows = list({(r["condition"], r["seed"]): r for r in rows}.values())
    if a.seed is not None:
        rows = [r for r in rows if r["seed"] == a.seed]
    print(table(rows))


if __name__ == "__main__":
    main()
