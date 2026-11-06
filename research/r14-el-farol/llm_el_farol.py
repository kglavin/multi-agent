"""El Farol with LLM agents, the R14 experiment.

Each week every agent gets one model call, with no tools and no memory beyond what
the prompt shows: the rules, the attendance it can see for recent weeks, and its own
recent outcomes. It must end with "DECISION: GO" or "DECISION: STAY". A reply
without a decision counts as STAY and is counted.

Conditions:
- homogeneous: one model, one prompt, the same information for every agent.
- varied_prompts: the same, plus one of STYLES per agent, assigned round-robin.
- private_info: each agent sees its own noisy and partial view of past attendance.
- varied_models: models assigned round-robin from a list. Needs more than one model.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from harness import Budget, BudgetExceeded, Message, Model, Recorder

from el_farol import measures

CONDITIONS = ["homogeneous", "varied_prompts", "private_info", "varied_models"]

SYSTEM = (
    "You are one of {n} people who each decide every week, independently and at the same time, "
    "whether to go to the El Farol bar. The bar is enjoyable only if {threshold} or fewer people go. "
    "If more than {threshold} go, it is crowded and going is worse than staying at home. "
    "Staying at home is neutral. You score a point for each week you go and the bar is not crowded. "
    "You cannot talk to the others. Think briefly, then end your reply with exactly one line: "
    "DECISION: GO or DECISION: STAY."
)

STYLES = [
    "Reason from the trend: estimate next week's attendance from the recent direction of change.",
    "Reason from the average: assume next week will be close to the average of the weeks you can see.",
    "Reason as a contrarian: expect others to repeat what worked last week, and do the opposite.",
    "Reason from your own record: favour whatever has given you good nights recently.",
    "Reason cautiously: go only if you are fairly sure the bar will not be crowded.",
]

DECISION = re.compile(r"DECISION:\s*(GO|STAY)\b", re.IGNORECASE)


def parse_decision(text: str) -> bool | None:
    """True for GO, False for STAY, None when the reply has no decision. The last one counts."""
    found = DECISION.findall(text)
    return found[-1].upper() == "GO" if found else None


@dataclass
class Config:
    condition: str = "homogeneous"
    n_agents: int = 20
    threshold: int = 12
    weeks: int = 50
    memory: int = 10  # weeks of attendance and own outcomes shown in each prompt
    seed: int = 0
    noise: float = 0.2  # private_info: noise of up to this fraction of n_agents, either way
    missing: float = 0.3  # private_info: chance that a week shows as unknown
    max_tokens: int | None = None
    max_calls: int | None = None
    burn_in: int = 0

    def __post_init__(self):
        if self.condition not in CONDITIONS:
            raise ValueError(f"unknown condition {self.condition}")


@dataclass
class Game:
    """State of one run. history[0] is the most recent week."""

    config: Config
    models: list[Model]
    history: list[int] = field(default_factory=list)
    outcomes: list[list[str]] = field(default_factory=list)  # per agent, most recent first
    attendance: list[int] = field(default_factory=list)
    rewards: list[int] = field(default_factory=list)
    unparseable: int = 0

    def __post_init__(self):
        c = self.config
        if c.condition == "varied_models" and len(self.models) < 2:
            raise ValueError("varied_models needs at least two models")
        rng = random.Random(c.seed)
        # Like the baseline, start from random attendance so the first prompt has history.
        self.history = [rng.randrange(c.n_agents) for _ in range(c.memory)]
        self.outcomes = [[] for _ in range(c.n_agents)]
        self.rewards = [0] * c.n_agents

    def model_for(self, agent: int) -> Model:
        if self.config.condition == "varied_models":
            return self.models[agent % len(self.models)]
        return self.models[0]

    def system_prompt(self, agent: int) -> str:
        c = self.config
        text = SYSTEM.format(n=c.n_agents, threshold=c.threshold)
        if c.condition == "varied_prompts":
            text += " " + STYLES[agent % len(STYLES)]
        return text

    def seen_attendance(self, agent: int) -> list[str]:
        """What one agent sees for the last `memory` weeks, most recent first.

        Under private_info, each (agent, week) gets its own fixed noise and gaps, so an
        agent's view of a given week does not change from one prompt to the next.
        """
        c = self.config
        weeks_done = len(self.attendance)
        seen = []
        for i, value in enumerate(self.history[: c.memory]):
            if c.condition != "private_info":
                seen.append(str(value))
                continue
            week = weeks_done - 1 - i  # negative for the random starting history
            rng = random.Random(f"{c.seed}/{agent}/{week}")
            if rng.random() < c.missing:
                seen.append("unknown")
            else:
                spread = round(c.noise * c.n_agents)
                seen.append(str(min(c.n_agents, max(0, value + rng.randint(-spread, spread)))))
        return seen

    def user_prompt(self, agent: int) -> str:
        c = self.config
        week = len(self.attendance) + 1
        seen = self.seen_attendance(agent)
        lines = [f"This is week {week}.", "", "Attendance in recent weeks, most recent first:"]
        lines += [f"- {i} week{'s' if i > 1 else ''} ago: {v}" for i, v in enumerate(seen, 1)]
        own = self.outcomes[agent][: c.memory]
        lines += ["", "Your own recent weeks, most recent first:"]
        lines += [f"- {o}" for o in own] if own else ["- no record yet"]
        return "\n".join(lines)

    def play_week(self, recorder: Recorder, budget: Budget) -> None:
        c = self.config
        week = len(self.attendance)
        going = []
        for agent in range(c.n_agents):
            messages = [Message("system", self.system_prompt(agent)), Message("user", self.user_prompt(agent))]
            r = self.model_for(agent).complete(messages, [])
            recorder.model_call(f"agent-{agent}", week, r)
            budget.charge(r)
            decision = parse_decision(r.text)
            if decision is None:
                self.unparseable += 1
            going.append(bool(decision))
            recorder.event("decision", agent=f"agent-{agent}", step=week, go=bool(decision),
                           parsed=decision is not None)
        count = sum(going)
        crowded = count > c.threshold
        for agent, went in enumerate(going):
            if went and not crowded:
                self.rewards[agent] += 1
            outcome = ("went, crowded" if crowded else "went, good night") if went else "stayed home"
            self.outcomes[agent].insert(0, outcome)
        self.history.insert(0, count)
        self.attendance.append(count)
        recorder.event("week", step=week, attendance=count, crowded=crowded)


def run(config: Config, models: list[Model], recorder: Recorder) -> dict:
    """Plays one game. A budget stop ends the game early and the row says so."""
    game = Game(config, models)
    budget = Budget(config.max_tokens, config.max_calls)
    stopped = None
    try:
        for _ in range(config.weeks):
            game.play_week(recorder, budget)
    except BudgetExceeded as e:
        stopped = str(e)
        recorder.event("budget_exceeded", reason=stopped)
    played = game.attendance[config.burn_in:]
    row = {
        "condition": config.condition,
        "agents": config.n_agents,
        "threshold": config.threshold,
        "weeks": config.weeks,
        "weeks_played": len(game.attendance),
        "seed": config.seed,
        "models": [m.name for m in models],
        **(measures(played, game.rewards, config.threshold) if played else {}),
        "unparseable": game.unparseable,
        "tokens": budget.tokens,
        "calls": budget.calls,
        "stopped": stopped,
    }
    return row
