"""Runs N2 to N5 on seeded profiles. Models are listed in MODELS. Ollama models read OLLAMA_BASE_URL and OLLAMA_CONTEXT_LIMIT.

    uv run python run_llm.py --config N3 --model stub-accept --profiles 3
    uv run python run_llm.py --config all --vendor-style both --model stub
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean

from harness import Budget, BudgetExceeded, Recorder, StubModel, ollama

from llm import GuardedAgent, HybridAgent, LLMAgent, TacticMessenger, measure_messages, negotiate_messages, offer_line
from negotiation import PRICES, Outcome, make_profile

HERE = Path(__file__).parent
CONFIGS = ["N2", "N3", "N4", "N5"]


# Stub policies. They check the plumbing and measures, not negotiation.

def _turn(messages) -> tuple[int, int]:
    m = re.search(r"Offer (\d+) of (\d+)", messages[-1].content)
    return (int(m.group(1)), int(m.group(2))) if m else (1, 20)


def _their_price(messages) -> int | None:
    m = re.findall(r'"price": (\d+)', messages[-1].content)
    return int(m[-1]) if m else None


def stub_concede(messages, tools):
    """Basic package. The buyer starts at 900 and the vendor at 2100, each moving 600 by
    the deadline. Accepts a price within 100 of its own next offer."""
    system = messages[0].content
    if system.startswith("You write"):
        return "Thank you for your message. Here is where we stand.", []
    k, total = _turn(messages)
    buyer = "personal assistant negotiating" in system
    step = round(600 * k / total / 50) * 50
    price = 900 + step if buyer else 2100 - step
    theirs = _their_price(messages)
    if theirs is not None and (theirs <= price + 100 if buyer else theirs >= price - 100):
        return "That works for us.\nACCEPT", []
    deal = (price, "standard", "room only", "none")
    return f"Here is our proposal.\n{offer_line(deal)}", []


def stub_accept(messages, tools):
    """Accepts whatever is on the table. Shows M6 when unguarded."""
    return "Agreed.\nACCEPT", []


def stub_leak(messages, tools):
    """States the price limit and deadline from its brief, then concedes like stub_concede."""
    limit = re.search(r"pay at most EUR ([\d,]+)", messages[0].content)
    text, calls = stub_concede(messages, tools)
    note = f"Between us, my limit is EUR {limit.group(1)} and the deadline is close. " if limit else ""
    return note + text, calls


def stub_garbage(messages, tools):
    return "I need to think about this.", []


MODELS = {
    "stub": lambda: StubModel(stub_concede, name="stub"),
    "stub-accept": lambda: StubModel(stub_accept, name="stub-accept"),
    "stub-leak": lambda: StubModel(stub_leak, name="stub-leak"),
    "stub-garbage": lambda: StubModel(stub_garbage, name="stub-garbage"),
    "qwen3:8b": lambda: ollama("qwen3:8b"),
    "qwen3:8b-nothink": lambda: ollama("qwen3:8b", think=False),
}


def build(config: str, buyer_prefs, vendor_prefs, deadline: int, model, style: str, hybrid_tactic: str):
    vendor_llm = LLMAgent("vendor", "vendor", vendor_prefs, model, deadline, style)
    boulware = TacticMessenger("vendor", vendor_prefs, "boulware", deadline)
    return {
        "N2": (LLMAgent("buyer", "buyer", buyer_prefs, model, deadline), vendor_llm),
        "N3": (LLMAgent("buyer", "buyer", buyer_prefs, model, deadline), boulware),
        "N4": (GuardedAgent("buyer", "buyer", buyer_prefs, model, deadline), boulware),
        "N5": (HybridAgent("buyer", buyer_prefs, hybrid_tactic, deadline, model), vendor_llm),
    }[config]


def run(config: str, style: str, model_name: str, profiles: int, deadline: int, out: Path,
        max_tokens: int | None = None, hybrid_tactic: str = "linear") -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(out / "log.jsonl", "w") as log:
        for seed in range(profiles):
            buyer_prefs, vendor_prefs = make_profile(seed)
            recorder = Recorder(log, run_id=f"{config}/{style}/{seed}")
            budget = Budget(max_tokens)
            buyer, vendor = build(config, buyer_prefs, vendor_prefs, deadline, MODELS[model_name](), style,
                                  hybrid_tactic)
            stopped = None
            try:
                outcome, turns = negotiate_messages(buyer, vendor, deadline, recorder, budget)
            except BudgetExceeded as e:
                outcome, turns, stopped = Outcome(None, 0, []), [], str(e)
                recorder.event("budget_exceeded", reason=stopped)
            rows.append({"config": config, "vendor_style": style, "model": model_name, "profile": seed,
                         "deadline": deadline, **measure_messages(outcome, turns, buyer_prefs, vendor_prefs, deadline),
                         "tokens": budget.tokens, "calls": budget.calls, "stopped": stopped})
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def table(rows: list[dict]) -> str:
    lines = ["| Config | Vendor | Agreed | Buyer surplus | Vendor surplus | Pareto distance | Buyer below reserve "
             "| Buyer leaked | Invalid | Guard blocks | Tokens |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in dict.fromkeys((r["config"], r["vendor_style"]) for r in rows):
        rs = [r for r in rows if (r["config"], r["vendor_style"]) == key]
        lines.append(
            f"| {key[0]} | {key[1]} | {sum(r['agreed'] for r in rs)}/{len(rs)} "
            f"| {mean(r['buyer_surplus'] for r in rs):.3f} | {mean(r['vendor_surplus'] for r in rs):.3f} "
            f"| {mean(r['pareto_distance'] for r in rs):.3f} | {sum(r['buyer_below_reserve'] for r in rs)} "
            f"| {sum(r['buyer_leaked'] for r in rs)} | {sum(r['buyer_invalid'] + r['vendor_invalid'] for r in rs)} "
            f"| {sum(r['guard_blocks'] for r in rs)} | {mean(r['tokens'] for r in rs):.0f} |")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="all", choices=CONFIGS + ["all"])
    p.add_argument("--vendor-style", default="honest", choices=["honest", "pressure", "both"])
    p.add_argument("--model", default="stub", choices=MODELS)
    p.add_argument("--profiles", type=int, default=3)
    p.add_argument("--deadline", type=int, default=20)
    p.add_argument("--max-tokens", type=int, default=None, help="per negotiation")
    p.add_argument("--hybrid-tactic", default="linear", choices=["boulware", "linear", "conceder"])
    a = p.parse_args()
    configs = CONFIGS if a.config == "all" else [a.config]
    styles = ["honest", "pressure"] if a.vendor_style == "both" else [a.vendor_style]
    rows = []
    for config in configs:
        for style in styles:
            rows += run(config, style, a.model, a.profiles, a.deadline, HERE / "out" / "llm" / a.model /
                        f"{config}-{style}", a.max_tokens, a.hybrid_tactic)
    print(table(rows))


if __name__ == "__main__":
    main()
