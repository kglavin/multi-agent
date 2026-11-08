# R5 Single Agent versus Multi-Agent

Status: two pilots done. Full run (600 runs) started on qwen3:8b on 2026-11-07.

## Question

On the same tasks, with the same model and the same tools, does a multi-agent system beat a single agent, and at what cost in tokens and time?

The classical texts justify multiple agents by distributed information, robustness, and parallelism, and Vlassis expects lower cost from decentralisation ([learn/01 §7.4](../../learn/01-setting-the-scene.md#74-benefits-and-testbeds)). For LLM agents, every coordination message is billed, and a shared transcript is billed again on every turn ([learn/14 §5](../../learn/14-context-engineering.md#5-cost-and-latency)). The question is whether the benefit survives that cost, and on which kinds of task.

## Prior Evidence

The only comparison in the series' sources is Dibia's Chapter 10 study ([learn/15 §5](../../learn/15-evaluating-agent-systems.md#5-what-the-evidence-says-about-multi-agent-designs)):

| Configuration | Score (of 10) | Tokens per task |
|---|---|---|
| Direct model call | 8.5 | 355 |
| Single agent with tools | 9.2 | Not reported |
| Multi-agent, fixed rotation | 9.2 | Not reported |
| Multi-agent, LLM selector | 9.3 | 15,343 |

Its weaknesses define what this study must do differently:

| Code | Weakness in the prior study | This study |
|---|---|---|
| W1 | 10 tasks, one run each, no variance | 5 runs per case, pass rates with intervals |
| W2 | The judge prompt was changed after the results, toward the expected answer | Scoring fixed and committed before any run. Deterministic checks wherever possible. |
| W3 | The judge was the same model as the system under test | Deterministic scoring. Any judge uses a different model and is validated on known cases first. |
| W4 | Tasks mostly fit in one context window | One suite deliberately exceeds one window |
| W5 | Tokens reported for two configurations only | Tokens, calls, and time for every run |

Dibia's Chapter 15 adds that isolating a sub-agent used the fewest tokens but scored second lowest on one code-review task ([learn/14 §4.3](../../learn/14-context-engineering.md#43-thrashing)).

## Design

### Configurations

All configurations use the same model, the same tools, and the same agent loop code, so that only the structure differs.

| Code | Configuration | Structure |
|---|---|---|
| C1 | Direct call | One model call, no tools |
| C2 | Single agent | One agent loop with all tools |
| C3 | Orchestrator with subagents | An orchestrator delegates to subagents wrapped as tools. Each subagent has its own context and the same tools. ([learn/14 §3.1](../../learn/14-context-engineering.md#31-isolation-by-delegation)) |
| C4 | Group chat, fixed rotation | Three agents share one transcript and take turns ([learn/14 §3.2](../../learn/14-context-engineering.md#32-shared-transcripts)) |

### Task suites

Each suite uses a local corpus so that runs are reproducible and answers can be checked without a judge.

| Code | Suite | Why | Corpus | Scoring |
|---|---|---|---|---|
| S1 | Short reasoning with exact answers | Where the prior study found the direct call best | None. Ten original word problems. Each answer is computed in `cases.py`. | Exact match |
| S2 | One fact from each of 20 independent documents | Parallel, independent parts: the case for subagents | 20 fictional supplier profiles (`corpus/s2/`, 2,300 words), generated from seed 1 and committed. Each profile has an old and a current value for headquarters, lead time, and contact, and some mention a certification not yet held. | Fraction of facts correct, or F1 for lists. Map values are compared on the part before the first comma. |
| S3 | Questions over a corpus larger than one context window | The LLM-specific reason to split work ([learn/01 §9.7](../../learn/01-setting-the-scene.md#97-a-new-reason-to-use-multiple-agents)) | The Python files of the Django 5.2 package at commit `9e7cc2b`, fetched by `corpus.py` and not committed: 883 files, 5.6 MB, about 1.4 million tokens at four characters per token | F1 for lists, fraction correct for maps. Answers computed from the source with Python's `ast` module. |

Every configuration gets the same four tools over the case's corpus: `list_files` (one level), `find_files` (glob on names, all levels), `read_file` (optionally a line range), and `search` (regular expression on contents, at most 200 matches). `find_files` was added after pilot 1. S1 cases have no corpus.

Lists in S2 have 3 to 10 answers. S3 cases ask for, among others, the classes that subclass `Field` (19), the middleware classes (19), and the signals defined across the package (21). An answer must be the requested JSON, or it scores 0.

Ten cases per suite. Five runs per case and configuration: 3 suites × 10 cases × 4 configurations × 5 runs = 600 runs.

### Measures

| Code | Measure |
|---|---|
| M1 | Pass rate per case, suite, and configuration |
| M2 | Input and output tokens, per run and per agent |
| M3 | Model calls per run |
| M4 | Wall-clock time per run |
| M5 | Duplicate tool calls (the same file read twice), as a sign of thrashing |

### Hypotheses

Written before any run, so the result can refute them.

| Code | Hypothesis |
|---|---|
| H1 | On S1, C1 and C2 score at least as well as C3 and C4. |
| H2 | On S2 and S1, C2 scores within the confidence interval of C3. |
| H3 | On S3, C3 scores higher than C2. |
| H4 | C3 and C4 use more tokens than C2 on every suite. |

H2 and H3 together test the claim from [learn/15 §5](../../learn/15-evaluating-agent-systems.md#5-what-the-evidence-says-about-multi-agent-designs): coordination helps only when one context window is not enough.

## Files

| File | Contents |
|---|---|
| `corpus.py` | Generates the S2 profiles and fetches the S3 source at the pinned commit |
| `cases.py` | Builds `cases.jsonl` (30 cases with expected answers) and loads it as harness cases |
| `score.py` | Exact, list (F1), and map scoring |
| `tools.py` | The four corpus tools: `list_files`, `find_files`, `read_file`, `search`. Each result is cut at 20,000 characters (about 5,000 tokens), because the largest S3 file is 119,000 characters and one read would fill a small model's window. |
| `prompts.py` | System prompts for C1 to C4. The C3 worker uses the C2 prompt. C4's three roles are planner, researcher, and checker. |
| `run.py` | Runs suites and configurations, writes per-suite logs and a Mermaid `report.md`, and a `summary.md` with M1 to M5. `--pilot` runs 1 case per suite once. Models are chosen in one place, `MODELS`. |
| `tests/test_r5.py` | Checks the answers, the committed corpus, the scorers, the tool limits, duplicate counting, and a stub run of every configuration |

```bash
cd research/r5-single-vs-multi-agent
uv sync
uv run python corpus.py   # writes corpus/s2, fetches corpus/s3
uv run python cases.py    # rebuilds cases.jsonl
uv run pytest
uv run python run.py --pilot   # 12 runs on the stub model, output in out/
```

S1 cases have no corpus, so S1 agents get no tools. In C4, tool calls stay inside an agent's turn and only its text joins the shared transcript. C4 runs at most 3 rotations.

## Pilots

### Pilot 1 (2026-11-07)

qwen3:8b with thinking on, 1 case per suite, 1 run, at most 100 model calls per run. 12 runs took 2,118 seconds, 132,841 tokens, and 81 model calls. Model calls took all of the wall time. No run reached the call cap or the context limit.

| Suite | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| S1 | 1.00 | 1.00 | 0.00 | 1.00 |
| S2 | 0.00 | 0.00 | 0.00 | 0.00 |
| S3 | 0.53 | 0.00 | 0.00 | 0.13 |

| Code | Finding | Change |
|---|---|---|
| P1 | On S2 the agents guessed directories such as `supplier_profiles/` and `s2/`, and never listed `.`. On S3 they used `search`, which matches file contents, to look for file names, and one worker concluded that no directory holds an `apps.py`. `list_files` lists one level and no tool found files by name. | The prompt and tool descriptions say the root is `.`. A leading `/` means the root. `search` says it matches contents. New tool `find_files` matches names in all subdirectories. |
| P2 | Three model calls returned no text and no tool call after 450 to 2,800 tokens of thinking, ending the run with an empty answer. Only the length of the thinking text was logged. | The agent loop answers an empty reply once with a fixed nudge and logs `empty_reply`. The full thinking text is logged. |
| P3 | C1 has no tools, yet scored 0.53 on S3-01 from training data: 8 of 15 Django app names. On S2 it invented cities. | None. C1 measures what the model knows or invents without the corpus, so it stays on every suite ([Q5](#open-questions)). |
| P4 | C3 on S1 returned its working instead of the number. | None. A format failure under exact match ([Q1](#open-questions)). |
| P5 | One C4 run on S3 took 1,439 seconds. At pilot rates the full 600 runs take about 29 hours. | Decide runs per case after pilot 2 ([Q6](#open-questions)). |

### Pilot 2 (2026-11-07)

The same settings after the P1 and P2 changes. 12 runs took 2,440 seconds, 173,437 tokens, and 84 model calls. One model call, the first C3 orchestrator call on S2, ran at about 2 tokens a second for 939 seconds against about 50 elsewhere, which points to a stall on the server. Without it the pilot took about 25 minutes.

| Suite | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| S1 | 1.00 | 1.00 | 1.00 | 1.00 |
| S2 | 0.00 | 0.10 | 0.00 | 0.00 |
| S3 | 0.33 | 0.00 | 0.00 | 0.87 |

| Code | Finding |
|---|---|
| P6 | The agents now use the tools: `find_files` in 5 of 6 tool runs, and `read_file` up to 6 times in a run. No empty answers. One empty reply was nudged and recovered. |
| P7 | C3 on S2 found all 20 current cities, but wrote each as city and country ("Wroclaw, Poland"), so exact match scored it 0. Scored on the part before the comma it gets 20 of 20. |
| P8 | C2 on S2 read 2 of the 20 profiles and answered for those 2 only (both right). C4 read one profile, keyed its answer by file name, and invented the rest. |
| P9 | C4 on S3 scored 0.87, 13 of 15 app names from the source. C2 and C3 found the files but returned the wrong JSON shape (C2) or an empty object (C3). |

## Risks

| Code | Risk | Mitigation |
|---|---|---|
| K1 | Task design favours one configuration | Suites chosen for different reasons, fixed before any run |
| K2 | Results hold for one model only | Record the model version. Repeat S3 on a second model if budget allows. |
| K3 | Prompt quality differs between configurations | Shared prompts where possible. Prompts committed with the results. |
| K4 | Cost exceeds budget | Pilot with one case per suite and one run each (12 runs) to measure cost before the full study |

## Steps

| Code | Step |
|---|---|
| S-1 | Settle the open questions. Q2 to Q4 done, Q1 open. |
| S-2 | Build the corpus and the 30 cases with answers. Done. |
| S-3 | Write one agent loop and the four configurations. Done, in the [harness](../harness/README.md) and `run.py`. |
| S-4 | Commit scoring, prompts, and hypotheses. Done when this commit lands. |
| S-5 | Pilot (12 runs), check cost and logs. Dry run on the stub done. |
| S-6 | Full run (600 runs) |
| S-7 | Report results against H1 to H4 |

## Open Questions

| Code | Question |
|---|---|
| Q1 | Model. Decided (2026-11-07): qwen3:8b (Q4_K_M) on a local Ollama server with an RTX 3060, through the harness's OpenAI-style adapter, with thinking on. Each request is limited to 20,480 tokens of context. Exact-match scoring stays as committed: an answer wrapped in working counts as a format failure. After pilot 2 (finding P7), map values are compared on the part before the first comma, unless the value is a number (decision O4). |
| Q2 | Budget. Decided: run the pilot first under a small cap, measure the cost per run, then set the full-run budget from that. |
| Q3 | Plain loop or agent SDK. Decided: the plain loop in the shared [harness](../harness/README.md). |
| Q4 | Corpus. Decided: synthetic documents for S2, a pinned public repository (Django 5.2) for S3. |
| Q5 | Should C1 run on S2 and S3, where it cannot see the corpus? Decided after pilot 1: yes. It measures what the model knows or invents without the corpus. |
| Q6 | Runs per case. Decided after pilot 2: 5 runs as planned, 600 runs in all, started 2026-11-07 on qwen3:8b with thinking on, one suite at a time. |

## Sources

- Dibia, *Designing Multi-Agent Systems*, 2025, Chapter 10 section 10.6 and Chapter 15 section 15.5.
- [Django](https://github.com/django/django) 5.2, commit 9e7cc2b628fe8fd3895986af9b7fc9525034c1b0, BSD 3-Clause licence (S3 corpus).
- Vlassis, *A Concise Introduction to Multiagent Systems and Distributed Artificial Intelligence*, 2007, Chapter 1.
