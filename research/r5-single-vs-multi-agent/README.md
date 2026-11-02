# R5 Single Agent versus Multi-Agent

Status: plan written (2026-11-02). Not started. Needs the decisions in [Open Questions](#open-questions) before any run.

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

| Code | Suite | Why | Scoring |
|---|---|---|---|
| S1 | Short reasoning with exact answers | Where the prior study found the direct call best | Exact match |
| S2 | Questions over many independent documents, for example extracting one fact from each of 20 files | Parallel, independent parts: the case for subagents | Exact match per fact |
| S3 | Questions over a corpus larger than one context window, such as a code repository | The LLM-specific reason to split work ([learn/01 §9.7](../../learn/01-setting-the-scene.md#97-a-new-reason-to-use-multiple-agents)) | Exact match or a checked list |

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

## Risks

| Code | Risk | Mitigation |
|---|---|---|
| K1 | Task design favours one configuration | Suites chosen for different reasons, fixed before any run |
| K2 | Results hold for one model only | Record the model version. Repeat S3 on a second model if budget allows. |
| K3 | Prompt quality differs between configurations | Shared prompts where possible. Prompts committed with the results. |
| K4 | Cost exceeds budget | Pilot with one case per suite and one run each (48 runs) to measure cost before the full study |

## Steps

| Code | Step |
|---|---|
| S-1 | Settle the open questions |
| S-2 | Build the corpus and the 30 cases with answers |
| S-3 | Write one agent loop and the four configurations |
| S-4 | Commit scoring, prompts, and hypotheses |
| S-5 | Pilot (48 runs), check cost and logs |
| S-6 | Full run (600 runs) |
| S-7 | Report results against H1 to H4 |

## Open Questions

| Code | Question |
|---|---|
| Q1 | Which model and provider? No API key is set in this environment. |
| Q2 | Budget for the pilot and the full run? |
| Q3 | Plain API loop written here, or an agent SDK? A plain loop keeps the four configurations identical apart from structure. |
| Q4 | Corpus: this repo plus a public code repository for S3, or something else? |

## Sources

- Dibia, *Designing Multi-Agent Systems*, 2025, Chapter 10 section 10.6 and Chapter 15 section 15.5.
- Vlassis, *A Concise Introduction to Multiagent Systems and Distributed Artificial Intelligence*, 2007, Chapter 1.
