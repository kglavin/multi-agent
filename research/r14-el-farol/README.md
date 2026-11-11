# R14 El Farol with LLM Agents

Status: rule-based baseline built and run (2026-11-03). LLM runs on qwen3:8b done for three of four conditions (2026-11-09 to 2026-11-11). See [LLM Results](#llm-results). `varied_models` is deferred.

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
uv run pytest                     # 17 tests, about 10 s
uv run python run.py              # 20 runs, about 1 minute, writes out/baseline.jsonl
uv run python run.py --seeds 3 --weeks 300
```

## LLM Agents

[llm_el_farol.py](llm_el_farol.py) plays the same game with LLM agents. It uses the shared [harness](../harness/README.md) for the model interface, the JSONL log, and the budget. [run_llm.py](run_llm.py) runs it.

### Design

1. Each week, each agent gets one model call with no tools. Agents keep no memory between weeks except what the prompt shows.
2. The system prompt gives the rules: N people decide at once, the bar is good only at or below the threshold, a point for each good night, no talking. It ends by asking for one line, `DECISION: GO` or `DECISION: STAY`. The text is `SYSTEM` in [llm_el_farol.py](llm_el_farol.py).
3. The user prompt gives the week number, attendance for the last 10 weeks, and the agent's own last 10 outcomes (went and it was a good night, went and it was crowded, or stayed home).
4. As in the baseline, the game starts with 10 weeks of random attendance so the first prompt has a history.
5. The last decision line in a reply counts. A reply without one counts as STAY and is counted as unparseable.
6. The default size is 20 agents with a threshold of 12, the book's 60%, over 50 weeks. That is 1,000 model calls per run, sized for a local model. All three are parameters.

### Conditions

| Condition | What differs between agents |
|---|---|
| `homogeneous` | Nothing. One model, one prompt, the same information. The LLM version of the monoculture case. |
| `varied_prompts` | One of five reasoning instructions added to the system prompt, assigned in turn: trend, average, contrarian, own record, and cautious. The texts are `STYLES` in [llm_el_farol.py](llm_el_farol.py). |
| `private_info` | Each agent sees its own view of past attendance. Each week shows as unknown with probability 0.3, otherwise with noise of up to 20% of N either way. The view of a given week is fixed per agent, so it does not change between prompts. |
| `varied_models` | Models assigned in turn from a list. Deferred: the second model on the server, gemma4:e4b, got 0.5 GB of GPU memory and ran mostly on the CPU, and with thinking off it answered without the decision line. |

Example user prompt under `private_info`, week 1:

```text
This is week 1.

Attendance in recent weeks, most recent first:
- 1 week ago: unknown
- 2 weeks ago: 11
- 3 weeks ago: 0
...

Your own recent weeks, most recent first:
- no record yet
```

### Measures

The baseline's five measures, plus:

| Measure | Meaning |
|---|---|
| Unparseable | Replies with no decision line |
| Tokens | Input plus output tokens for the run |
| Calls | Model calls for the run |

Each run also runs the rule-based model at the same N, threshold, weeks, and seed, in both of its conditions, so the comparison is like for like. The baseline's prediction now scales with N, and its results at 100 agents are unchanged.

### Run

```bash
cd research/r14-el-farol
uv run pytest                                          # 17 tests
uv run python run_llm.py --condition all --model stub
uv run python run_llm.py --condition varied_models --model stub --model stub-go
uv run python run_llm.py --condition homogeneous --agents 20 --threshold 12 --weeks 50 --seed 0 --max-tokens 500000
```

Output goes to `out/llm/`: one log per condition and seed with every model call, decision, and week, and `results.jsonl` with one row per run. A budget stop ends the run early, and the row records the weeks played.

The only models are two stubs: `stub` answers GO or STAY at random from the seed, and `stub-go` always answers GO. Their figures check the code and are not results. Adding a real model means adding one entry to `MODELS` in [run_llm.py](run_llm.py).

### LLM Results

qwen3:8b (Q4_K_M) on a local Ollama server with an RTX 3060, 20 agents, threshold 12, 50 weeks, 1,000 model calls per run. Each run also ran the rule-based model at the same size and seed. Every reply had a decision line.

A pilot of 3 weeks measured the cost. With thinking on, a call took 36 seconds and about 2,000 output tokens, so one run takes about 13 hours. With thinking off, a run took about 13 minutes. So the main run has thinking off with 10 seeds, and thinking on was run for one seed of two conditions as a check.

```bash
uv run python run_llm.py --condition all --model qwen3:8b-nothink --seed 0 --out out/llm-full/nothink   # seeds 0 to 9
uv run python run_llm.py --condition homogeneous --model qwen3:8b --seed 0 --out out/llm-full/think
uv run python analyse_llm.py out/llm-full/nothink/results.jsonl
```

Thinking off, 10 seeds. Mean across seeds, with the range in brackets.

| Condition | Mean attendance | Attendance SD | Crowded fraction | Reward Gini | Mean reward |
|---|---|---|---|---|---|
| homogeneous | 4.3 (3.1 to 6.5) | 5.9 (4.7 to 6.9) | 0.12 (0.06 to 0.14) | 0.47 (0.17 to 0.73) | 5.3 (0.9 to 14.0) |
| varied_prompts | 9.9 (9.4 to 10.4) | 2.9 (2.6 to 3.5) | 0.17 (0.14 to 0.22) | 0.31 (0.23 to 0.38) | 18.6 (17.1 to 19.6) |
| private_info | 5.3 (4.0 to 6.6) | 4.0 (2.9 to 5.3) | 0.06 (0.02 to 0.10) | 0.17 (0.11 to 0.26) | 11.1 (5.7 to 15.5) |
| rule-diverse | 11.4 (10.5 to 12.0) | 2.6 (1.6 to 3.6) | 0.34 (0.22 to 0.44) | 0.30 (0.22 to 0.38) | 16.2 (13.3 to 20.8) |
| rule-homogeneous | 12.3 (9.6 to 16.0) | 9.5 (8.0 to 10.0) | 0.62 (0.48 to 0.80) | 0.00 | 0.0 |

Seed 0, thinking off against thinking on.

| Condition | Thinking | Mean attendance | Attendance SD | Crowded fraction | Reward Gini | Mean reward | Tokens |
|---|---|---|---|---|---|---|---|
| homogeneous | off | 3.7 | 6.4 | 0.14 | 0.47 | 2.9 | 311,422 |
| homogeneous | on | 12.1 | 6.3 | 0.50 | 0.19 | 7.8 | 2,904,596 |
| varied_prompts | off | 10.4 | 2.6 | 0.22 | 0.38 | 18.2 | 383,126 |
| varied_prompts | on | 11.8 | 2.5 | 0.50 | 0.35 | 12.2 | 2,868,323 |
| rule-diverse | | 11.2 | 3.6 | 0.40 | 0.27 | 13.3 | |

Attendance in the first 12 weeks of seed 0:

| Condition | Thinking | Attendance |
|---|---|---|
| homogeneous | off | 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20 |
| homogeneous | on | 20, 4, 19, 5, 18, 9, 18, 7, 15, 6, 11, 18 |
| varied_prompts | off | 7, 11, 15, 8, 13, 11, 12, 9, 9, 10, 8, 10 |

| Code | Finding |
|---|---|
| L1 | A shared model and prompt does not reproduce the rule-based monoculture exactly, but it fails too. With thinking off, the agents mostly all stay home, with an occasional week when all 20 go. The bar is seldom crowded, and mean reward is 5.3 good nights in 50, against 16.2 for the diverse rule-based agents. |
| L2 | With thinking on, the shared agents swing on a two-week cycle, high after low and low after high, which is the monoculture pattern from Arthur (1994) with some spread. Half the weeks are crowded. One seed only. |
| L3 | Varied prompts is the only condition that restores the diverse outcome. Attendance stays near but under the threshold in every seed, with an SD close to the diverse rule-based agents, and mean reward (18.6) is above theirs (16.2), with fewer crowded weeks (0.17 against 0.34). |
| L4 | Private information makes the agents cautious more than diverse. Crowded weeks are the fewest of any condition (0.06), but attendance is low and so is reward. Reward is the most equal (Gini 0.17). |
| L5 | Thinking costs 8 to 9 times the tokens and about 60 times the time per call. On seed 0 it moved attendance up to the threshold in both conditions and made half the weeks crowded. Whether that holds needs more seeds. |

Not yet done: `varied_models` (needs a second model that fits on the GPU), and more thinking-on seeds.

## Sources

- Arthur, W. B., "Inductive Reasoning and Bounded Rationality", *American Economic Review* 84(2), 1994.
- Wilensky and Rand, *An Introduction to Agent-Based Modeling*, MIT Press, 2015, Chapter 3, pp. 141-150, and Exploration 32, p. 155.
- Rand and Wilensky, El Farol model, NetLogo, 2007. [Source](https://github.com/NetLogo/models/tree/main/IABM%20Textbook/chapter%203/El%20Farol%20Extensions).
- [Mesa](https://github.com/projectmesa/mesa), version 3.5.1.
