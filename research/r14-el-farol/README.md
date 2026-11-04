# R14 El Farol with LLM Agents

Status: rule-based baseline built and run (2026-11-03). LLM agents not started. They need a model provider ([R5 Q1](../r5-single-vs-multi-agent/README.md#open-questions)).

## Question

N agents decide each week whether to go to a bar that is worth going to only when it is not crowded. Do LLM agents that share one model and prompt behave like Arthur's agents that share one predictor, and does diversity of models, prompts, or private information restore the outcome that diverse rule-based agents reach? Background in [learn/17 §3](../../learn/17-agents-in-complex-systems.md#3-monoculture).

## Baseline

The LLM runs will be docked against this rule-based model ([learn/17 §8](../../learn/17-agents-in-complex-systems.md#8-studying-a-population)).

### Model

[el_farol.py](el_farol.py) follows the NetLogo El Farol model (Rand and Wilensky 2007) used in Wilensky and Rand Chapter 3, after Arthur (1994). It is written with Mesa 3.5.1.

1. 100 agents. Each holds a bag of `number-strategies` strategies, fixed for the whole run.
2. A strategy is a constant c and one weight per remembered week, each drawn uniformly from -1 to 1. Its prediction is 100 × c plus the sum of weight × attendance over the last `memory-size` weeks.
3. Each week every agent predicts attendance with its current best strategy and goes if the prediction is at or below `overcrowding-threshold`.
4. An agent's reward rises by 1 for each week it went and the bar was not crowded.
5. After each week, each agent scores every strategy by its total absolute error over the last `memory-size` weeks and uses the lowest.
6. The run starts with `memory-size` × 2 weeks of random attendance from 0 to 99.

| Parameter | Value | Source |
|---|---|---|
| Agents | 100 | Book and NetLogo model |
| `overcrowding-threshold` | 60 | Book and NetLogo default |
| `memory-size` | 5 | NetLogo default. The book names the parameter but gives no value. |
| `number-strategies` | 10 | NetLogo default. As above. |
| Weeks per run | 1,000 | Our choice |
| Burn-in excluded from attendance measures | 100 weeks | Our choice. Rewards count all weeks. |

The book describes the strategies but does not print their code. The code here follows the NetLogo source in the [NetLogo models repository](https://github.com/NetLogo/models/tree/main/IABM%20Textbook/chapter%203/El%20Farol%20Extensions). The reward is the book's first extension (pp. 143-145).

### Conditions

| Condition | Strategies |
|---|---|
| Diverse | Each agent draws its own bag. This is the book's model. |
| Homogeneous | One bag is drawn and every agent gets it. All agents then make the same prediction every week. This is the monoculture case from Arthur (1994), which the book does not run. |

### Measures

| Measure | Meaning |
|---|---|
| Mean attendance | Average weekly attendance after burn-in |
| Attendance SD | Population standard deviation of weekly attendance after burn-in |
| Crowded fraction | Share of weeks with attendance above 60 |
| Reward Gini | Inequality of reward across agents. 0 means equal. |
| Mean reward | Average number of good nights per agent over the run |

### Results

10 seeds per condition, 1,000 weeks each. Mean across seeds, with the range in brackets.

| Condition | Mean attendance | Attendance SD | Crowded fraction | Reward Gini | Mean reward |
|---|---|---|---|---|---|
| Diverse | 58.2 (56.9 to 59.7) | 6.2 (2.6 to 11.2) | 0.35 (0.18 to 0.46) | 0.39 (0.32 to 0.46) | 353 (282 to 462) |
| Homogeneous | 65.1 (50 to 100) | 42.3 (0 to 50) | 0.65 (0.50 to 1.00) | 0 (0 to 0) | 0 (0 to 0) |

1. Diverse agents keep mean attendance just under 60 in every seed, which matches the book's report of attendance around 60. Over a third of weeks are still crowded, and reward is unequal, with a Gini near 0.4. This matches the book's observation that a few agents do much better than the rest (p. 148).
2. Homogeneous agents never get a good night. All 100 go or all 100 stay home. In 9 of 10 seeds attendance swings between 0 and 100. In seed 2 it locks at 100 every week, because none of the shared strategies ever predicts crowding. The mean attendance of 50 to 100 hides this, which is why R14 needs the SD and reward measures and not attendance alone.

### Run

```bash
cd research/r14-el-farol
uv sync
uv run pytest                     # 5 tests, about 10 s
uv run python run.py              # 20 runs, about 1 minute, writes out/baseline.jsonl
uv run python run.py --seeds 3 --weeks 300
```

## Sources

- Arthur, W. B., "Inductive Reasoning and Bounded Rationality", *American Economic Review* 84(2), 1994.
- Wilensky and Rand, *An Introduction to Agent-Based Modeling*, MIT Press, 2015, Chapter 3, pp. 141-150, and Exploration 32, p. 155.
- Rand and Wilensky, El Farol model, NetLogo, 2007. [Source](https://github.com/NetLogo/models/tree/main/IABM%20Textbook/chapter%203/El%20Farol%20Extensions).
- [Mesa](https://github.com/projectmesa/mesa), version 3.5.1.
