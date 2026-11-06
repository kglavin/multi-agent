"""Rule-based El Farol model, the baseline for R14.

Follows the NetLogo El Farol model (Rand and Wilensky 2007) that Wilensky and Rand
use in Chapter 3, after Arthur (1994). Each agent has a bag of strategies. A strategy
is a constant plus one weight per remembered week, each drawn from -1 to 1. Each week
an agent predicts attendance with its best strategy and attends if the prediction is
at or below the overcrowding threshold. After the week, it picks as best the strategy
with the lowest total error over the last MEMORY_SIZE weeks.

`homogeneous=True` gives every agent the same bag of strategies, so all agents make
the same prediction every week.
"""

from __future__ import annotations

import statistics

import mesa


def predict_attendance(strategy: list[float], subhistory: list[int], scale: int = 100) -> float:
    """p(t) = scale * c + sum of weight * attendance for each remembered week.

    scale is the number of agents, 100 in the book's model.
    """
    return scale * strategy[0] + sum(w * x for w, x in zip(strategy[1:], subhistory))


class Patron(mesa.Agent):
    def __init__(self, model: ElFarol, strategies: list[list[float]]):
        super().__init__(model)
        self.strategies = strategies
        self.best_strategy = strategies[0]
        self.attend = False
        self.prediction = 0.0
        self.reward = 0  # good nights attended: went and the bar was not crowded
        self.update_strategies()

    def decide(self) -> None:
        m = self.model.memory_size
        self.prediction = predict_attendance(self.best_strategy, self.model.history[:m], self.model.n_agents)
        self.attend = self.prediction <= self.model.overcrowding_threshold

    def update_strategies(self) -> None:
        """Score each strategy on the last MEMORY_SIZE weeks. Ties go to the later one, as in NetLogo."""
        m, history, n = self.model.memory_size, self.model.history, self.model.n_agents
        best_score = m * n + 1
        for strategy in self.strategies:
            score = sum(abs(history[week - 1] - predict_attendance(strategy, history[week:week + m], n))
                        for week in range(1, m + 1))
            if score <= best_score:
                best_score = score
                self.best_strategy = strategy


class ElFarol(mesa.Model):
    def __init__(self, n_agents: int = 100, memory_size: int = 5, number_strategies: int = 10,
                 overcrowding_threshold: int = 60, homogeneous: bool = False, seed: int | None = None):
        super().__init__(rng=seed)
        self.n_agents = n_agents
        self.memory_size = memory_size
        self.overcrowding_threshold = overcrowding_threshold
        # Twice the memory, so each remembered week can be scored with a full window.
        self.history = [self.random.randrange(n_agents) for _ in range(memory_size * 2)]
        self.attendance: list[int] = []
        shared = [self.random_strategy() for _ in range(number_strategies)] if homogeneous else None
        for _ in range(n_agents):
            Patron(self, shared or [self.random_strategy() for _ in range(number_strategies)])

    def random_strategy(self) -> list[float]:
        return [1.0 - self.random.uniform(0, 2) for _ in range(self.memory_size + 1)]

    def step(self) -> None:
        self.agents.do("decide")
        attendance = sum(1 for a in self.agents if a.attend)
        if attendance <= self.overcrowding_threshold:
            for a in self.agents:
                if a.attend:
                    a.reward += 1
        self.history = [attendance] + self.history[:-1]
        self.attendance.append(attendance)
        self.agents.do("update_strategies")


def gini(values: list[float]) -> float:
    """0 when everyone has the same, approaching 1 when one agent has everything."""
    n, total = len(values), sum(values)
    if n == 0 or total == 0:
        return 0.0
    ranked = sorted(values)
    return sum((2 * i - n + 1) * v for i, v in enumerate(ranked)) / (n * total)


def measures(attendance: list[int], rewards: list[int], threshold: int) -> dict:
    """R14's measures over a run, or over the part of it passed in."""
    return {
        "mean_attendance": statistics.fmean(attendance),
        "sd_attendance": statistics.pstdev(attendance),
        "crowded_fraction": sum(1 for a in attendance if a > threshold) / len(attendance),
        "reward_gini": gini(rewards),
        "mean_reward": statistics.fmean(rewards),
    }


def run(weeks: int = 1000, burn_in: int = 100, **params) -> dict:
    """Runs one model. Attendance measures skip the first `burn_in` weeks. Rewards count all weeks."""
    model = ElFarol(**params)
    for _ in range(weeks):
        model.step()
    rewards = [a.reward for a in model.agents]
    return {
        **params,
        "weeks": weeks,
        "burn_in": burn_in,
        **measures(model.attendance[burn_in:], rewards, model.overcrowding_threshold),
    }
