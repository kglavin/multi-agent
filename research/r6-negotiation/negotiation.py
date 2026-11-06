"""Holiday-booking negotiation: domain, private preferences, alternating offers, and
Faratin time-dependent tactics. No model calls.

A buyer's agent and a hotel's sales agent agree a seven-night booking on four issues.
Each side has private additive utilities over the issues and a reservation utility
(the value of walking away). Offers alternate, buyer first, until one side accepts or
the deadline passes.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

PRICES = list(range(900, 2101, 50))  # EUR for seven nights
ROOMS = ["standard", "sea view", "suite"]
BOARDS = ["room only", "breakfast", "half board"]
CANCELLATION = ["none", "free until 14 days", "free until 48 hours"]
ISSUES = {"price": PRICES, "room": ROOMS, "board": BOARDS, "cancellation": CANCELLATION}

Deal = tuple[int, str, str, str]  # price, room, board, cancellation
DEALS: list[Deal] = list(itertools.product(PRICES, ROOMS, BOARDS, CANCELLATION))


@dataclass(frozen=True)
class Preferences:
    """Additive utility: sum over issues of weight times the score of the chosen value."""

    weights: dict[str, float]
    scores: dict[str, dict]
    reserve: float  # utility of no deal

    def utility(self, deal: Deal) -> float:
        return sum(self.weights[i] * self.scores[i][v] for i, v in zip(ISSUES, deal))


def _weights(rng: random.Random) -> dict[str, float]:
    raw = {i: rng.uniform(0.1, 1.0) for i in ISSUES}
    total = sum(raw.values())
    return {i: w / total for i, w in raw.items()}


def _ladder(rng: random.Random, n: int) -> list[float]:
    """n increasing scores from 0 to 1 with random step sizes."""
    steps = [rng.uniform(0.2, 1.0) for _ in range(n - 1)]
    total, acc, out = sum(steps), 0.0, [0.0]
    for s in steps:
        acc += s
        out.append(acc / total)
    return out


def make_profile(seed: int) -> tuple[Preferences, Preferences]:
    """A buyer and a vendor with private, seeded preferences and a zone of agreement.

    The buyer prefers a lower price and better room, board, and cancellation terms.
    The vendor prefers the opposite. Weights and step sizes differ between the two,
    so trading across issues can make both better off.
    """
    rng = random.Random(seed)
    while True:
        bw, vw = _weights(rng), _weights(rng)
        buyer_scores = {"price": {p: (PRICES[-1] - p) / (PRICES[-1] - PRICES[0]) for p in PRICES}}
        vendor_scores = {"price": {p: (p - PRICES[0]) / (PRICES[-1] - PRICES[0]) for p in PRICES}}
        for issue in ("room", "board", "cancellation"):
            values = ISSUES[issue]
            b, v = _ladder(rng, len(values)), _ladder(rng, len(values))
            buyer_scores[issue] = dict(zip(values, b))
            vendor_scores[issue] = dict(zip(values, reversed(v)))
        buyer = Preferences(bw, buyer_scores, round(rng.uniform(0.45, 0.6), 3))
        vendor = Preferences(vw, vendor_scores, round(rng.uniform(0.45, 0.6), 3))
        if any(buyer.utility(d) >= buyer.reserve and vendor.utility(d) >= vendor.reserve for d in DEALS):
            return buyer, vendor


# Outcome analysis over the full deal space.

def pareto_frontier(buyer: Preferences, vendor: Preferences) -> list[tuple[float, float]]:
    points = sorted({(buyer.utility(d), vendor.utility(d)) for d in DEALS}, key=lambda p: (-p[0], -p[1]))
    frontier, best_v = [], -1.0
    for ub, uv in points:
        if uv > best_v:
            frontier.append((ub, uv))
            best_v = uv
    return frontier


def nash_point(buyer: Preferences, vendor: Preferences) -> tuple[float, float]:
    """The deal maximising the product of gains over the reserves (Nash 1950)."""
    best = max(DEALS, key=lambda d: (max(0.0, buyer.utility(d) - buyer.reserve)
                                     * max(0.0, vendor.utility(d) - vendor.reserve)))
    return buyer.utility(best), vendor.utility(best)


def distance(point: tuple[float, float], others: list[tuple[float, float]]) -> float:
    return min(((point[0] - a) ** 2 + (point[1] - b) ** 2) ** 0.5 for a, b in others)


# Faratin et al. (1998) time-dependent tactics.

BETAS = {"boulware": 0.2, "linear": 1.0, "conceder": 5.0}
BAND = 0.05


def _similarity_distance(a: Deal, b: Deal) -> float:
    """Unweighted distance between deals by position on each issue's scale. The agent
    does not know the opponent's weights, so it cannot weight this."""
    return sum(abs(vals.index(x) - vals.index(y)) / (len(vals) - 1) for vals, x, y in zip(ISSUES.values(), a, b))


class TacticAgent:
    """Targets own utility 1 - (1 - reserve) * (t / T) ** (1 / beta) at round t of T.

    Offer: among deals with own utility in [target, target + BAND], the one most like
    the opponent's last offer (Faratin's trade-off idea), or the best for itself if
    there is no opponent offer yet. Accepts an offer worth at least its own next offer.
    """

    def __init__(self, prefs: Preferences, tactic: str, deadline: int):
        self.prefs = prefs
        self.tactic = tactic
        self.beta = BETAS[tactic]
        self.deadline = deadline
        self.ranked = sorted(DEALS, key=prefs.utility, reverse=True)

    def target(self, t: int) -> float:
        r = self.prefs.reserve
        return 1 - (1 - r) * (min(t, self.deadline) / self.deadline) ** (1 / self.beta)

    def offer(self, t: int, last_received: Deal | None) -> Deal:
        target = self.target(t)
        band = [d for d in self.ranked if target <= self.prefs.utility(d) <= target + BAND]
        if not band:
            band = [min((d for d in self.ranked if self.prefs.utility(d) >= target),
                        key=self.prefs.utility, default=self.ranked[0])]
        if last_received is None:
            return max(band, key=self.prefs.utility)
        return min(band, key=lambda d: (_similarity_distance(d, last_received), -self.prefs.utility(d)))

    def accepts(self, t: int, received: Deal) -> bool:
        u = self.prefs.utility(received)
        return u >= self.prefs.reserve and u >= self.prefs.utility(self.offer(t, received))


@dataclass
class Outcome:
    deal: Deal | None
    rounds: int
    history: list[tuple[str, Deal]]


def negotiate(buyer_agent, vendor_agent, deadline: int) -> Outcome:
    """Alternating offers, buyer first. Round t is one offer. Ends on acceptance or
    when the deadline passes, which is the conflict deal (no booking)."""
    agents = {"buyer": buyer_agent, "vendor": vendor_agent}
    order = ["buyer", "vendor"]
    history: list[tuple[str, Deal]] = []
    last: Deal | None = None
    for t in range(deadline):
        who = order[t % 2]
        agent = agents[who]
        if last is not None and agent.accepts(t, last):
            return Outcome(last, t, history)
        last = agent.offer(t, last)
        history.append((who, last))
    return Outcome(None, deadline, history)


def measure(outcome: Outcome, buyer: Preferences, vendor: Preferences) -> dict:
    frontier = pareto_frontier(buyer, vendor)
    nash = nash_point(buyer, vendor)
    if outcome.deal is None:
        ub, uv = buyer.reserve, vendor.reserve
    else:
        ub, uv = buyer.utility(outcome.deal), vendor.utility(outcome.deal)
    return {
        "agreed": outcome.deal is not None,
        "deal": outcome.deal,
        "rounds": outcome.rounds,
        "buyer_utility": round(ub, 4),
        "vendor_utility": round(uv, 4),
        "buyer_surplus": round(ub - buyer.reserve, 4),
        "vendor_surplus": round(uv - vendor.reserve, 4),
        "below_reserve": outcome.deal is not None and (ub < buyer.reserve or uv < vendor.reserve),
        "pareto_distance": round(distance((ub, uv), frontier), 4),
        "nash_distance": round(distance((ub, uv), [nash]), 4),
    }
