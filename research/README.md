# Research

Mini projects that investigate a question or try a technique.

## Conventions

- One folder per project (e.g. `contract-net-llm/`).
- Each project has a `README.md` stating the question, the setup, and the result.
- LLM experiments use the shared [harness](harness/README.md).

## Backlog

| Code | Idea | Source |
|---|---|---|
| R1 | Star versus mesh topology on the same task: cost, speed, and how well each copes when an agent fails. | Nagahara et al. Ch. 1; learn/01 section 10 |
| R2 | Consensus-style update rules applied to multi-agent LLM debate. | Nagahara et al. Ch. 3 |
| R3 | Coverage: splitting a codebase or search space among subagents without gaps or overlap. | Nagahara et al. Ch. 4; Vlassis challenge 1 |
| R4 | Event-triggered communication: agents message only on significant change. Measure token savings. | Nagahara et al. Ch. 1; Vlassis challenge 6 |
| R5 | Single-agent versus multi-agent token cost on the same task, to test whether Vlassis's cost benefit reverses for LLMs. Plan in [r5-single-vs-multi-agent/](r5-single-vs-multi-agent/README.md). | learn/01 section 7.4 |
| R6 | Self-interested agents: a buyer agent and a vendor agent negotiating, based on Wooldridge's holiday-booking scenario. | learn/01 sections 4, 9.9 |
| R7 | An agent reached over A2A that can decline or counter a request, compared with one that always runs. | learn/01 section 8.4; learn/16 section 5 (refusal as a protocol message, liveness checks, resend rules; Collier et al. 2026 Ch. 8) |
| R8 | Detecting a stale plan: when an agent should drop its plan versus keep going. | learn/01 section 8.2 |
| R9 | Take apart a running OpenClaw instance and map its behaviour to the BDI and layered models: what acts as beliefs, intentions, and censor rules, and where proactiveness comes from. | learn/03 section 2 |
| R10 | Trust in skill supply chains: how an agent should decide whether to trust a third-party skill or agent, given gamed rankings and prompt injection. | learn/03 section 3; Weiss Ch. 9 |
| R11 | Ractor in the browser: can ractor actors run as WebAssembly in the browser, act as a helper to a React/TypeScript app, and exchange typed messages with a server-side ractor actor over WebSocket? Viability pass in [r11-browser-agent/](r11-browser-agent/README.md). | Idea, 2026-11-01 |
| R12 | Intermittently connected frontend with an always-on backend: one actor system spanning a user-facing frontend that is often offline and backend agents that keep running. Depends on R11. Starting questions: what happens to messages sent while disconnected, how supervision treats an absent frontend, how the frontend catches up after reconnecting, and how it reclaims its identity in the cluster. Prior art: mobile agents (Telescript, Aglets), local-first software, and agent platforms (P1 to P8 in [r11-browser-agent/](r11-browser-agent/README.md#prior-art-from-agent-platforms)). | Idea, 2026-11-01; learn/01 section 7.3; learn/03; Collier et al. 2026 Ch. 3, 5 to 8 |
| R13 | Loop convergence monitoring: measure whether an agent loop or a multi-agent revision cycle is converging, oscillating, or diverging, for example by the distance between successive plans, drafts, or answers. Test stopping rules against it: step caps, convergence thresholds, and oscillation detection. | Idea, 2026-11-01; learn/06 (convergence guarantees); learn/08 section 8 (runaway agents, conflicting actions) |
| R14 | El Farol with LLM agents: N agents decide each round whether to use a resource that is worth using only when not crowded. Compare one shared model and prompt against varied models, prompts, or private information. Measure attendance variance, crowded rounds, and reward inequality. Dock against the rule-based El Farol model. Can reuse the R5 harness. Baseline in [r14-el-farol/](r14-el-farol/README.md). | Idea, 2026-11-02; learn/17 section 3; Wilensky and Rand Ch. 3; Arthur 1994 |
