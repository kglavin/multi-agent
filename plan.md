# Plan

Status as of 2026-11-02. Detail for each item lives in the linked section README.

## Done

### Repo

- Repo structure with [learn/](learn/README.md), [research/](research/README.md), and [engineer/](engineer/README.md) sections, each with conventions.
- References list in the [README](README.md). PDFs are kept locally and gitignored.

### Learn

1. [01 Setting the Scene](learn/01-setting-the-scene.md): Wooldridge, Vlassis, Weiss, Sayfan, and Nagahara et al., with diagrams.
2. [02 Agent Architectures](learn/02-agent-architectures.md): logic-based, reactive, BDI, and layered architectures, and where LLM agents fit.
3. [03 Agent Landscape 2026](learn/03-agent-landscape-2026.md): vendor agent products, OpenClaw, and open multi-agent systems.
4. [04 Multiagent Organisations](learn/04-multiagent-organisations.md): roles, norms, and institutions (Weiss Ch. 2).
5. [05 Trust and Reputation](learn/05-trust-and-reputation.md): trust and reputation in open MAS (Weiss Ch. 9).
6. [06 Control of Cooperative MAS](learn/06-control-of-cooperative-mas.md): consensus, coverage, and formation control (Nagahara et al. Ch. 3-5).
7. [07 Agent Communication](learn/07-agent-communication.md): speech acts, KQML, FIPA ACL, commitments, MCP, and A2A (Wooldridge Ch. 6-7, Weiss Ch. 3, Sayfan Ch. 7-8).
8. [08 Working Together](learn/08-working-together.md): CDPS, Contract Net, coordination, multiagent planning, and coordination failures (Wooldridge Ch. 8, Sayfan Ch. 8 and 10).
9. [09 Strategic Interaction](learn/09-strategic-interaction.md): game theory for self-interested agents (Wooldridge Ch. 11, Weiss Ch. 17).
10. [10 Group Decisions](learn/10-group-decisions.md): voting, social choice, and fair division (Wooldridge Ch. 12, Weiss Ch. 6).
11. [11 Coalitions and Auctions](learn/11-coalitions-and-auctions.md): mechanism design, coalitions, auctions, and VCG (Wooldridge Ch. 13-14, Weiss Ch. 7-8).
12. [12 Bargaining and Argumentation](learn/12-bargaining-and-argumentation.md): negotiation and argumentation (Wooldridge Ch. 15-16, Weiss Ch. 4-5).
13. [13 Multiagent Learning and Coordination](learn/13-multiagent-learning.md): multiagent reinforcement learning, equilibrium selection, and sparse coordination (Sadhu and Konar, Vlassis Ch. 4 and 7, Weiss Ch. 10).
14. [14 Context Engineering](learn/14-context-engineering.md): context windows, retrieval, context across agents, compaction, and token cost (Rothman, Dibia, O'Brien).
15. [15 Evaluating Agent Systems](learn/15-evaluating-agent-systems.md): trajectories, evaluation sets, LLM judges, the evidence on multi-agent designs, and change control (Dibia, O'Brien, Rothman).
16. [16 Agent-Oriented Programming and Platforms](learn/16-agent-programming-and-platforms.md): agent languages, actors, environments, protocols, accountability, LLMs in agent platforms, and Agentic Mesh (Collier et al., Broda and Broda).
- LLM-era sections added to [05](learn/05-trust-and-reputation.md) (section 8, content as instructions), [07](learn/07-agent-communication.md) (section 7, LLM senders), and [08](learn/08-working-together.md) (section 9, stopping and human control).

### Research

- Backlog R1 to R13 recorded in [research/README.md](research/README.md).
- R11 viability pass: [r11-browser-agent/](research/r11-browser-agent/README.md). Result: viable. The main unknown is whether `ractor_cluster` compiles to WebAssembly.
- Prior art from agent platforms (P1 to P8) added to R11 for R11 and R12. R7 linked to protocol-based refusal in learn/16 section 5.

## To Do

### Learn

- Backlog empty.

### Research

- R11 spike: run Q1 to Q3 from the [spike plan](research/r11-browser-agent/README.md#spike-plan).
- R12 viability pass, after R11.
- R1 to R10 and R13: not started. See the [backlog](research/README.md#backlog).

### Engineer

- Nothing planned yet.
