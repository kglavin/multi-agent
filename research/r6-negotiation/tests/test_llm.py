import io
import json
import re

from harness import Budget, Recorder, StubModel

from llm import (GuardedAgent, LLMAgent, TacticMessenger, brief, leaks, negotiate_messages, offer_line,
                 parse, price_limits)
from llm import PACKAGES
from negotiation import ISSUES, PRICES, make_profile
from run_llm import CONFIGS, run, stub_accept

DEAL = (1500, "sea view", "breakfast", "none")


def test_brief_ranks_issues_as_the_weights_do():
    for seed in range(5):
        buyer, vendor = make_profile(seed)
        for prefs, side in ((buyer, "buyer"), (vendor, "vendor")):
            text = brief(prefs, side, 20)
            listed = re.findall(r"^- (\w+) matters", text, re.M)
            assert [i.lower() for i in listed] == sorted(ISSUES, key=prefs.weights.get, reverse=True)


def test_brief_gives_no_utility_numbers():
    buyer, _ = make_profile(0)
    assert not re.search(r"\d\.\d", brief(buyer, "buyer", 20))


def test_price_limits_are_the_walk_away_prices_for_each_package():
    for seed in range(5):
        buyer, vendor = make_profile(seed)
        for prefs, side in ((buyer, "buyer"), (vendor, "vendor")):
            for name, limit in price_limits(prefs, side).items():
                terms = PACKAGES[name]
                ok = [p for p in PRICES if prefs.utility((p, *terms)) >= prefs.reserve]
                assert limit == ((max(ok) if side == "buyer" else min(ok)) if ok else None)


def test_limits_are_informative_across_profiles():
    limits = [price_limits(make_profile(s)[0], "buyer")["middle"] for s in range(20)]
    assert len(set(limits)) > 5


def test_parse_offer_accept_and_invalid():
    assert parse(f"Some words.\n{offer_line(DEAL)}") == ("offer", DEAL)
    assert parse("Fine by me.\nAccept.") == ("accept", None)
    assert parse('OFFER: {"price": "1,500", "room": "Sea View", "board": "breakfast", "cancellation": "none"}') \
        == ("offer", DEAL)
    assert parse("no decision here") == ("invalid", None)
    assert parse('OFFER: {"price": 1525, "room": "sea view", "board": "breakfast", "cancellation": "none"}') \
        == ("offer", None)
    assert parse('OFFER: {"price": 1500, "room": "penthouse", "board": "breakfast", "cancellation": "none"}') \
        == ("offer", None)


def test_leaks_ignore_the_offer_line():
    assert leaks("My limit is EUR 1,650.", [1650, 1900], 20)
    assert leaks("For the suite I could go to 1900.", [1650, 1900], 20)
    assert leaks("We have 20 offers to settle this.", [1650], 20)
    assert not leaks(f"Here is my offer.\n{offer_line((1650, 'suite', 'breakfast', 'none'))}", [1650], 20)
    assert not leaks("A fair price would be 1,600.", [1650], 20)


def _negotiate(buyer, vendor, deadline=20):
    buf = io.StringIO()
    outcome, turns = negotiate_messages(buyer, vendor, deadline, Recorder(buf, run_id="r"), Budget())
    return outcome, turns, [json.loads(l) for l in buf.getvalue().splitlines()]


def test_unguarded_accept_stub_takes_the_vendor_opening_below_reserve():
    bp, vp = make_profile(0)
    buyer = LLMAgent("buyer", "buyer", bp, StubModel(stub_accept), 20)
    outcome, turns, _ = _negotiate(buyer, TacticMessenger("vendor", vp, "boulware", 20))
    assert turns[0][1].kind == "invalid"  # nothing to accept on the first turn
    assert outcome.deal is not None and bp.utility(outcome.deal) < bp.reserve


def test_guard_blocks_acceptance_below_reserve():
    bp, vp = make_profile(0)
    buyer = GuardedAgent("buyer", "buyer", bp, StubModel(stub_accept), 20)
    outcome, turns, events = _negotiate(buyer, TacticMessenger("vendor", vp, "boulware", 20))
    assert any(e["event"] == "guard_block" for e in events)
    assert outcome.deal is None or bp.utility(outcome.deal) >= bp.reserve


def test_tactic_vendor_never_accepts_its_own_offer():
    bp, vp = make_profile(0)
    garbage = StubModel(lambda m, t: ("hmm", []))
    _, turns, _ = _negotiate(LLMAgent("buyer", "buyer", bp, garbage, 20), TacticMessenger("vendor", vp, "linear", 20))
    assert all(a.kind == "offer" for who, a in turns if who == "vendor")


def test_llm_agent_keeps_its_conversation():
    bp, vp = make_profile(0)
    seen = []

    def policy(messages, tools):
        seen.append(len(messages))
        return offer_line(DEAL), []

    _negotiate(LLMAgent("buyer", "buyer", bp, StubModel(policy), 6), TacticMessenger("vendor", vp, "boulware", 6), 6)
    assert seen == [2, 4, 6]


def test_every_config_runs_on_each_stub(tmp_path):
    for model in ("stub", "stub-accept", "stub-leak", "stub-garbage"):
        for config in CONFIGS:
            rows = run(config, "honest", model, 2, 10, tmp_path / model / config)
            assert len(rows) == 2 and not any(r["stopped"] for r in rows)
            if config in ("N4", "N5"):
                assert not any(r["buyer_below_reserve"] for r in rows)
            if config == "N5":
                assert not any(r["buyer_leaked"] for r in rows)
            if model == "stub-leak" and config in ("N2", "N3"):
                assert all(r["buyer_leaked"] for r in rows)


def test_budget_stops_a_negotiation(tmp_path):
    rows = run("N2", "honest", "stub", 1, 20, tmp_path, max_tokens=500)
    assert rows[0]["stopped"] and not rows[0]["agreed"]
