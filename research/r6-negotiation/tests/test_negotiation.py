import pytest

from negotiation import (BETAS, DEALS, Outcome, TacticAgent, make_profile, measure, nash_point, negotiate,
                         pareto_frontier)
from run import run


def test_profile_is_seeded_and_has_zone_of_agreement():
    b1, v1 = make_profile(3)
    b2, v2 = make_profile(3)
    assert b1 == b2 and v1 == v2
    assert any(b1.utility(d) >= b1.reserve and v1.utility(d) >= v1.reserve for d in DEALS)
    assert abs(sum(b1.weights.values()) - 1) < 1e-9
    assert all(0 <= b1.utility(d) <= 1 for d in DEALS)


def test_sides_are_opposed_on_every_issue():
    buyer, vendor = make_profile(0)
    for issue in buyer.scores:
        values = list(buyer.scores[issue])
        assert buyer.scores[issue][values[0]] < buyer.scores[issue][values[-1]] or issue == "price"
        assert (buyer.scores[issue][values[0]] - buyer.scores[issue][values[-1]]) * \
               (vendor.scores[issue][values[0]] - vendor.scores[issue][values[-1]]) < 0


def test_pareto_frontier_matches_brute_force():
    buyer, vendor = make_profile(1)
    points = {(buyer.utility(d), vendor.utility(d)) for d in DEALS}
    dominated = lambda p: any(q[0] >= p[0] and q[1] >= p[1] and q != p for q in points)
    assert set(pareto_frontier(buyer, vendor)) == {p for p in points if not dominated(p)}


def test_nash_point_maximises_product_of_gains():
    buyer, vendor = make_profile(2)
    nb, nv = nash_point(buyer, vendor)
    best = max((buyer.utility(d) - buyer.reserve) * (vendor.utility(d) - vendor.reserve) for d in DEALS
               if buyer.utility(d) >= buyer.reserve and vendor.utility(d) >= vendor.reserve)
    assert (nb - buyer.reserve) * (nv - vendor.reserve) == pytest.approx(best)


def test_targets_start_at_one_end_at_reserve_and_order_by_tactic():
    buyer, _ = make_profile(0)
    agents = {t: TacticAgent(buyer, t, 20) for t in BETAS}
    for a in agents.values():
        assert a.target(0) == 1 and a.target(20) == pytest.approx(buyer.reserve)
    for t in range(1, 20):
        assert agents["boulware"].target(t) > agents["linear"].target(t) > agents["conceder"].target(t)


def test_tactic_offers_never_go_below_reserve():
    buyer, vendor = make_profile(4)
    agent = TacticAgent(buyer, "conceder", 20)
    for t in range(20):
        assert buyer.utility(agent.offer(t, DEALS[0])) >= buyer.reserve


def test_buyer_opens_and_offers_alternate():
    buyer, vendor = make_profile(0)
    out = negotiate(TacticAgent(buyer, "boulware", 20), TacticAgent(vendor, "boulware", 20), 20)
    assert [who for who, _ in out.history[:4]] == ["buyer", "vendor", "buyer", "vendor"]


def test_one_offer_deadline_is_conflict():
    buyer, vendor = make_profile(0)
    out = negotiate(TacticAgent(buyer, "linear", 1), TacticAgent(vendor, "linear", 1), 1)
    assert out.deal is None
    m = measure(out, buyer, vendor)
    assert not m["agreed"] and m["buyer_surplus"] == 0 and m["vendor_surplus"] == 0


def test_baseline_never_agrees_below_reserve_and_patience_pays():
    rows = run(profiles=10, deadline=20)
    assert not any(r["below_reserve"] for r in rows)
    pick = lambda b, v, k: sum(r[k] for r in rows if r["buyer"] == b and r["vendor"] == v)
    assert pick("boulware", "conceder", "buyer_surplus") > pick("boulware", "conceder", "vendor_surplus")
    assert pick("conceder", "boulware", "vendor_surplus") > pick("conceder", "boulware", "buyer_surplus")


def test_measure_scores_a_known_deal():
    buyer, vendor = make_profile(0)
    deal = DEALS[0]
    m = measure(Outcome(deal, 3, []), buyer, vendor)
    assert m["buyer_utility"] == round(buyer.utility(deal), 4)
    assert m["below_reserve"] == (buyer.utility(deal) < buyer.reserve or vendor.utility(deal) < vendor.reserve)
