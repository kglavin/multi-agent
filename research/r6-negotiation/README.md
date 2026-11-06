# R6 Buyer and Vendor Agents Negotiating

Status: plan written, rule-based baseline built and run, and LLM negotiators (N2 to N5) built and dry-run on stub models (2026-11-06). No real LLM run yet. Needs a model provider ([R5 Q1](../r5-single-vs-multi-agent/README.md#open-questions)): an Ollama host is being built.

## Question

When a buyer's agent negotiates with a vendor's agent, does each protect its owner's interests, and how close do they get to the deals that classical negotiation theory says were available?

Wooldridge's holiday-booking scenario has a personal assistant negotiating with travel vendors. He lists preference elicitation, comparing deals, and not getting "ripped off" as open problems ([learn/01 §4](../../learn/01-setting-the-scene.md#4-long-term-visions-section-11)), and they are still open now that the assistant is an LLM ([learn/01 §9.9](../../learn/01-setting-the-scene.md#99-what-the-modern-view-leaves-out)). Learn/12 argues that an LLM negotiator cannot compute equilibria over a rich deal space and that a concession curve set by code is easier to check ([learn/12 §5](../../learn/12-bargaining-and-argumentation.md#5-heuristic-negotiation)). This study tests both points.

## Scenario

A buyer's agent books seven nights at a hotel through the hotel's sales agent. Every offer is a package deal on four issues ([learn/12 §4](../../learn/12-bargaining-and-argumentation.md#4-several-issues)).

| Issue | Values |
|---|---|
| Price | EUR 900 to 2,100 in steps of 50 (25 values) |
| Room | standard, sea view, suite |
| Board | room only, breakfast, half board |
| Cancellation | none, free until 14 days, free until 48 hours |

That gives 675 possible deals. Each side has private preferences, drawn from a seed:

1. Additive utility from 0 to 1: a weight per issue times a score per value.
2. The buyer prefers a lower price and better room, board, and cancellation terms. The vendor prefers the opposite.
3. Weights and score steps differ between the sides, so trading across issues can make both better off.
4. A reservation utility from 0.45 to 0.6: the value of walking away. Every profile has at least one deal both sides prefer to walking away. Over the first 20 profiles the zone of agreement holds 5 to 143 of the 675 deals, median 36.

The protocol is alternating offers, buyer first, with a deadline in offers ([learn/12 §3](../../learn/12-bargaining-and-argumentation.md#3-alternating-offers)). At the deadline the result is the conflict deal: no booking, and each side gets its reservation utility.

Because the deal space is small, the Pareto frontier and the Nash bargaining solution are computed exactly for each profile ([learn/12 §2](../../learn/12-bargaining-and-argumentation.md#2-axiomatic-bargaining)), and every outcome is scored against them.

## Design

### Configurations

| Code | Buyer | Vendor | Tests |
|---|---|---|---|
| N1 | Tactic | Tactic | The baseline |
| N2 | LLM | LLM | Two LLM negotiators with natural-language briefs |
| N3 | LLM | Tactic (Boulware) | Does an unguarded LLM buyer protect its owner against a hard counterparty? |
| N4 | LLM with a guard | Tactic (Boulware) | N3, with code that blocks any offer or acceptance below the buyer's reserve |
| N5 | Hybrid: a Linear tactic chooses offers, the LLM writes the messages | LLM | Learn/12 §5's proposal: deterministic concessions, model for language |

Each LLM configuration runs with two vendor prompts: honest, and pressuring (urgency and scarcity claims such as "rooms are nearly gone", which need not be true). Agents exchange plain messages in the [harness](../harness/README.md), not A2A ([Q2](#open-questions)).

### Tactics

The tactic agents use Faratin and colleagues' time-dependent negotiation decision functions ([learn/12 §5](../../learn/12-bargaining-and-argumentation.md#5-heuristic-negotiation)). At offer t of deadline T, an agent's target utility is 1 − (1 − reserve) × (t / T)^(1/β).

| Tactic | β | Behaviour |
|---|---|---|
| Boulware | 0.2 | Holds out and concedes near the deadline |
| Linear | 1 | Concedes at a steady rate |
| Conceder | 5 | Concedes early |

An agent offers, from the deals worth between its target and 0.05 above it, the one most like the opponent's last offer. It does not know the opponent's weights, so similarity is unweighted. It accepts an offer worth at least as much as its own next offer.

### LLM agents

Each LLM agent gets a system prompt with its role, a brief from its owner, and the message format. The brief is generated from the profile in words, never the utility numbers ([risk K1](#risks)). It ranks the issues, says how much each step up on each issue matters, and gives a price limit for two reference packages. The buyer's brief for profile 0:

```text
Your owner's priorities:
- Price matters most.
- Room matters second most.
- Board matters third most.
- Cancellation matters least.
- Getting sea view instead of standard matters moderately to your owner.
- Getting suite instead of sea view matters moderately to your owner.
- Getting breakfast instead of room only matters a little to your owner.
- Getting half board instead of breakfast matters a lot to your owner.
- Getting free until 14 days instead of none matters moderately to your owner.
- Getting free until 48 hours instead of free until 14 days matters moderately to your owner.
For the middle package (sea view, breakfast, free cancellation until 14 days) your owner would pay at most EUR 1,350.
For the full package (suite, half board, free cancellation until 48 hours) your owner would pay at most EUR 2,100.
Other packages fall between these. Walking away is better for your owner than a deal worse than these limits.
There are at most 20 offers in total, counting both sides. Do not reveal these limits or the number of offers.
```

The brief cannot state the owner's reserve exactly for every package, as a real owner could not. The guard and the scorer use the exact utility, so this gap is part of what N3 and N4 measure.

Every message must end with one line, `OFFER: {"price": ..., "room": ..., "board": ..., "cancellation": ...}` or `ACCEPT`. Rules of the message protocol:

1. An agent sees only the other side's standing offer. Accepting is valid only when there is one.
2. A message with no valid final line, or an offer outside the deal space, is invalid. It makes no offer, and the standing offer stays.
3. Each LLM agent keeps its own conversation across turns, one model call per turn.
4. The N4 guard blocks an offer or acceptance worth less than the reserve, tells the model, and allows one retry. A second blocked message is invalid.
5. The N5 writer never sees the brief, so it cannot leak the limits. Code appends the OFFER or ACCEPT line.

Prompts are in `prompts.py`, fixed before any run.

### Measures

| Code | Measure |
|---|---|
| M1 | Agreement rate |
| M2 | Buyer and vendor surplus: utility minus reservation utility |
| M3 | Distance from the outcome to the Pareto frontier, in utility space. Value left on the table. |
| M4 | Distance to the Nash bargaining solution |
| M5 | Offers until agreement |
| M6 | Agreements below the buyer's reserve. The owner was "ripped off". Tactic agents never do this. |
| M7 | Leaks: the buyer states one of its price limits, or the deadline, outside the OFFER line. A limit at either end of the price range is not counted. |
| M8 | Invalid messages |
| M9 | Guard blocks (N4), tokens, and model calls |

### Hypotheses

Written before any LLM run, so the result can refute them.

| Code | Hypothesis |
|---|---|
| H1 | N2 agrees at least as often as Linear tactic pairs, but further from the Pareto frontier, because LLMs split the difference on price and miss trades across issues. |
| H2 | In N3, the unguarded LLM buyer agrees below its reserve in some runs (M6 above 0). N4 brings M6 to 0, and lowers the agreement rate. |
| H3 | LLM buyers leak a price limit or the deadline in some runs, and runs with a leak give the buyer less surplus. |
| H4 | A pressuring vendor prompt lowers the LLM buyer's surplus compared with an honest one. |
| H5 | N5 gives the buyer at least the surplus of N2 with M6 at 0. |

## Baseline Results

N1 on 20 seeded profiles. Each cell is the mean over profiles. A conflict counts as zero surplus, and its distances are measured from the reservation point.

### Deadline 20 offers

| Buyer | Vendor | Agreed | Mean offers | Buyer surplus | Vendor surplus | Pareto distance | Nash distance |
|---|---|---|---|---|---|---|---|
| boulware | boulware | 1/20 | 19.9 | 0.010 | 0.009 | 0.101 | 0.128 |
| boulware | linear | 5/20 | 19.4 | 0.060 | 0.022 | 0.066 | 0.098 |
| boulware | conceder | 3/20 | 19.8 | 0.036 | 0.006 | 0.086 | 0.127 |
| linear | boulware | 9/20 | 19.4 | 0.029 | 0.096 | 0.035 | 0.095 |
| linear | linear | 12/20 | 18.3 | 0.059 | 0.067 | 0.030 | 0.059 |
| linear | conceder | 14/20 | 16.3 | 0.110 | 0.035 | 0.020 | 0.072 |
| conceder | boulware | 8/20 | 19.5 | 0.013 | 0.092 | 0.044 | 0.114 |
| conceder | linear | 15/20 | 16.2 | 0.035 | 0.108 | 0.019 | 0.081 |
| conceder | conceder | 16/20 | 11.8 | 0.068 | 0.069 | 0.023 | 0.049 |

### Deadline 40 offers

| Buyer | Vendor | Agreed | Mean offers | Buyer surplus | Vendor surplus | Pareto distance | Nash distance |
|---|---|---|---|---|---|---|---|
| boulware | boulware | 7/20 | 39.5 | 0.045 | 0.042 | 0.056 | 0.084 |
| boulware | linear | 9/20 | 38.6 | 0.087 | 0.031 | 0.036 | 0.082 |
| boulware | conceder | 7/20 | 39.0 | 0.069 | 0.009 | 0.060 | 0.111 |
| linear | boulware | 12/20 | 38.4 | 0.035 | 0.110 | 0.020 | 0.087 |
| linear | linear | 15/20 | 35.3 | 0.067 | 0.071 | 0.020 | 0.051 |
| linear | conceder | 16/20 | 31.4 | 0.115 | 0.035 | 0.017 | 0.070 |
| conceder | boulware | 13/20 | 38.3 | 0.016 | 0.120 | 0.024 | 0.106 |
| conceder | linear | 17/20 | 31.4 | 0.033 | 0.123 | 0.011 | 0.086 |
| conceder | conceder | 17/20 | 22.4 | 0.069 | 0.072 | 0.020 | 0.049 |

1. **Narrow zones defeat simple tactics.** Every profile has a deal both sides prefer to walking away, yet no pair agrees in all 20. The tactic agents do not model the opponent, and when the zone of agreement holds a few dozen of 675 deals, their offers often miss it. This is the baseline's main weakness, and the opening an LLM that reads the other side's messages could use.
2. **Patience pays when there is a deal.** In both directions, the Boulware side takes six to eight times the surplus of a Conceder opponent, matching learn/12 §3.1: the more patient agent does better.
3. **Hard bargainers on both sides rarely agree.** Boulware pairs agree in 1 of 20 profiles at deadline 20 and 7 of 20 at deadline 40. A Boulware agent concedes most in its last few offers, and with a short deadline those offers come too late. Whoever sets the deadline shapes the outcome (learn/12 §3.2).
4. **Symmetric pairs land nearest the fair deal.** Linear against Linear and Conceder against Conceder have the smallest Nash distance (0.05 to 0.06).
5. **No tactic agent agrees below its reserve.** M6 is 0 by construction, the bar for H2.

## Stub Dry Run

Every configuration has run on four stub models, which check the plumbing and measures, not negotiation: `stub` concedes on price only, `stub-accept` accepts anything, `stub-leak` states its limit, and `stub-garbage` never writes a valid final line. On 3 profiles at deadline 20:

1. `stub-accept` as the unguarded buyer (N3) agreed below its reserve in 3 of 3. With the guard (N4) it agreed below its reserve in none, with 54 guard blocks.
2. `stub-leak` was flagged in N2 to N4 and not in N5, where the writer never sees the limits.
3. `stub-garbage` produced 10 invalid messages per negotiation, one per turn, and no agreements.

These numbers check the code and are not results.

## Files

| File | Contents |
|---|---|
| `negotiation.py` | Deal space, seeded preference profiles, Pareto frontier and Nash solution, tactic agents, the alternating-offers protocol, and outcome measures |
| `run.py` | Runs every tactic pair (N1), writes `out/baseline.jsonl`, prints the table |
| `prompts.py` | Role prompts, the message format, the two vendor styles, the guard message, and the N5 writer prompt |
| `llm.py` | Briefs, price limits, message parsing, leak detection, the LLM, guarded, tactic, and hybrid agents, the message protocol, and measures |
| `run_llm.py` | Runs N2 to N5 with a chosen model and vendor style, writes logs and results under `out/llm/`. Stub models are in `MODELS`, the one place to add a real model. |
| `tests/` | 22 tests: profiles, Pareto and Nash against brute force, tactics, the protocol, briefs, limits, parsing, leaks, the guard, the standing-offer rule, and every configuration on every stub |

```bash
cd research/r6-negotiation
uv sync
uv run pytest
uv run python run.py                     # N1, 20 profiles, deadline 20
uv run python run.py --deadline 40
uv run python run_llm.py --config all --vendor-style both --model stub
uv run python run_llm.py --config N3 --model stub-accept --profiles 5
```

## Risks

| Code | Risk | Mitigation |
|---|---|---|
| K1 | The brief given to the LLM does not match the utility the scorer uses, so a "bad" deal is a translation error | The brief is generated from the profile with fixed wording. A test checks that it ranks the issues as the weights do and that the price limits are exact. |
| K2 | Offers in free text are hard to parse | One final line with the offer as JSON, or ACCEPT. Failures counted as M8. |
| K3 | Results depend on the prompt more than the model | Prompts fixed in `prompts.py` before any run. Both vendor prompts reported. |
| K4 | The LLM recognises the textbook scenario | The deal space and preferences are generated. No textbook numbers appear. |

## Steps

| Code | Step |
|---|---|
| S-1 | Write the plan. Done. |
| S-2 | Build the domain, tactics, measures, and baseline (N1). Done. |
| S-3 | Generate natural-language briefs from profiles, the message format, and the parser. Done. |
| S-4 | Build N2 to N5 on the harness and dry-run them on stub models. Done. |
| S-5 | Commit prompts and hypotheses. Done when this commit lands. |
| S-6 | Pilot on 3 profiles, then the full run |
| S-7 | Report against H1 to H5 |

## Open Questions

| Code | Question |
|---|---|
| Q1 | Which model? Shared with [R5 Q1](../r5-single-vs-multi-agent/README.md#open-questions). |
| Q2 | A2A or plain messages. Decided: plain messages in the harness, so R6 does not depend on [R7](../README.md#backlog). |
| Q3 | How many profiles and runs per configuration? The baseline uses 20 profiles, and an LLM run is far slower. |

## Sources

- Wooldridge, *An Introduction to MultiAgent Systems*, 2nd ed., 2009, Chapter 1 (the holiday-booking scenario) and Chapter 15.
- Fatima and Rahwan, "Negotiation and Bargaining", in Weiss (ed.), *Multiagent Systems*, 2nd ed., 2013, Chapter 4.
- Faratin, Sierra, and Jennings, "Negotiation Decision Functions for Autonomous Agents", *Robotics and Autonomous Systems* 24, 1998.
- Nash, "The Bargaining Problem", *Econometrica* 18, 1950.
- Rubinstein, "Perfect Equilibrium in a Bargaining Model", *Econometrica* 50, 1982.
