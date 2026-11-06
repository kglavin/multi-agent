"""Runs El Farol with LLM agents, and the rule-based baseline at the same size.

    uv run python run_llm.py --condition all --model stub
    uv run python run_llm.py --condition varied_models --model stub --model stub-go

Writes out/llm/<condition>-seed<seed>.log.jsonl (every model call and decision) and
appends one row per run, including the two rule-based rows, to out/llm/results.jsonl.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from harness import Model, Recorder, StubModel

import el_farol
from llm_el_farol import CONDITIONS, Config, run


def random_policy(seed: int, p_go: float = 0.5):
    rng = random.Random(seed)
    return lambda messages, tools: (f"DECISION: {'GO' if rng.random() < p_go else 'STAY'}", [])


def always_go(messages, tools):
    return "DECISION: GO", []


MEASURES = ["mean_attendance", "sd_attendance", "crowded_fraction", "reward_gini", "mean_reward"]

# The one place to add a model. Each entry builds a Model from the run seed.
MODELS = {
    "stub": lambda seed: StubModel(random_policy(seed), name="stub-random"),
    "stub-go": lambda seed: StubModel(always_go, name="stub-go"),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--condition", choices=CONDITIONS + ["all"], default="homogeneous")
    p.add_argument("--agents", type=int, default=20)
    p.add_argument("--threshold", type=int, default=12)
    p.add_argument("--weeks", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--model", action="append", choices=list(MODELS),
                   help="repeat for varied_models. Other conditions use the first.")
    p.add_argument("--out", type=Path, default=Path("out/llm"))
    args = p.parse_args()

    names = args.model or ["stub"]
    models: list[Model] = [MODELS[n](args.seed + i) for i, n in enumerate(names)]
    if args.condition == "all":
        conditions = [c for c in CONDITIONS if c != "varied_models" or len(models) > 1]
    else:
        conditions = [args.condition]

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for condition in conditions:
        config = Config(condition=condition, n_agents=args.agents, threshold=args.threshold,
                        weeks=args.weeks, seed=args.seed, max_tokens=args.max_tokens)
        log_path = args.out / f"{condition}-seed{args.seed}.log.jsonl"
        with open(log_path, "w") as log:
            rows.append(run(config, models, Recorder(log, run_id=f"{condition}/{args.seed}")))

    # The rule-based model at the same size, for docking.
    for homogeneous in (False, True):
        base = el_farol.run(weeks=args.weeks, burn_in=0, n_agents=args.agents,
                            overcrowding_threshold=args.threshold, homogeneous=homogeneous, seed=args.seed)
        rows.append({"condition": "rule-homogeneous" if homogeneous else "rule-diverse",
                     "agents": args.agents, "threshold": args.threshold, "weeks": args.weeks,
                     "seed": args.seed, **{k: base[k] for k in MEASURES}})

    with open(args.out / "results.jsonl", "a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    cols = MEASURES + ["unparseable", "tokens", "calls"]
    print("| Condition | " + " | ".join(cols) + " |")
    print("|---|" + "---|" * len(cols))
    for r in rows:
        cells = [f"{r[c]:.3g}" if isinstance(r.get(c), float) else str(r.get(c, "")) for c in cols]
        print(f"| {r['condition']} | " + " | ".join(cells) + " |")
    if any(r.get("stopped") for r in rows):
        print("\nStopped by budget: " + ", ".join(r["condition"] for r in rows if r.get("stopped")))
    print(f"\nResults appended to {args.out / 'results.jsonl'}")


if __name__ == "__main__":
    main()
