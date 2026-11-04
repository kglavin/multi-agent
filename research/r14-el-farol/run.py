"""Runs the baseline for both conditions over several seeds.

    uv run python run.py [--seeds 10] [--weeks 1000] [--out out/baseline.jsonl]

Writes one JSON line per run and prints the mean and spread across seeds.
"""

import argparse
import json
import statistics
from pathlib import Path

from el_farol import run

MEASURES = ["mean_attendance", "sd_attendance", "crowded_fraction", "reward_gini", "mean_reward"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--weeks", type=int, default=1000)
    p.add_argument("--out", type=Path, default=Path("out/baseline.jsonl"))
    args = p.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(args.out, "w") as f:
        for homogeneous in (False, True):
            for seed in range(args.seeds):
                row = run(weeks=args.weeks, seed=seed, homogeneous=homogeneous)
                f.write(json.dumps(row) + "\n")
                rows.append(row)

    print("| Condition | " + " | ".join(MEASURES) + " |")
    print("|---|" + "---|" * len(MEASURES))
    for homogeneous in (False, True):
        group = [r for r in rows if r["homogeneous"] == homogeneous]
        cells = []
        for m in MEASURES:
            values = [r[m] for r in group]
            cells.append(f"{statistics.fmean(values):.3g} ({min(values):.3g} to {max(values):.3g})")
        name = "Homogeneous" if homogeneous else "Diverse"
        print(f"| {name} | " + " | ".join(cells) + " |")
    print(f"\n{len(rows)} runs written to {args.out}")


if __name__ == "__main__":
    main()
