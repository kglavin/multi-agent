"""Runs every pair of tactics on seeded preference profiles and prints the baseline table.

    uv run python run.py [--profiles 20] [--deadline 20]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from negotiation import BETAS, TacticAgent, make_profile, measure, negotiate

HERE = Path(__file__).parent


def run(profiles: int, deadline: int) -> list[dict]:
    rows = []
    for seed in range(profiles):
        buyer, vendor = make_profile(seed)
        for bt in BETAS:
            for vt in BETAS:
                outcome = negotiate(TacticAgent(buyer, bt, deadline), TacticAgent(vendor, vt, deadline), deadline)
                rows.append({"profile": seed, "buyer": bt, "vendor": vt, "deadline": deadline,
                             **measure(outcome, buyer, vendor)})
    return rows


def table(rows: list[dict]) -> str:
    lines = ["| Buyer | Vendor | Agreed | Mean offers | Buyer surplus | Vendor surplus | Pareto distance "
             "| Nash distance |", "|---|---|---|---|---|---|---|---|"]
    for bt in BETAS:
        for vt in BETAS:
            rs = [r for r in rows if r["buyer"] == bt and r["vendor"] == vt]
            ok = [r for r in rs if r["agreed"]]
            lines.append(
                f"| {bt} | {vt} | {len(ok)}/{len(rs)} | {mean(r['rounds'] for r in rs):.1f} "
                f"| {mean(r['buyer_surplus'] for r in rs):.3f} | {mean(r['vendor_surplus'] for r in rs):.3f} "
                f"| {mean(r['pareto_distance'] for r in rs):.3f} | {mean(r['nash_distance'] for r in rs):.3f} |")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--profiles", type=int, default=20)
    p.add_argument("--deadline", type=int, default=20)
    a = p.parse_args()
    rows = run(a.profiles, a.deadline)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "baseline.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(table(rows))


if __name__ == "__main__":
    main()
