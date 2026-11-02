# 00 Map

One page from a practice or failure in LLM agent systems to the concept that explains it and where the series covers it. The last column names the research item that tests it, where there is one ([backlog](../research/README.md#backlog)).

Most rows have a classical concept. The rows marked "None" are the LLM-era disciplines with no classical counterpart.

## Building One Agent

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| A model in a loop with tools, given a goal | The agent: autonomous action in an environment | [01 §2](01-setting-the-scene.md#2-core-definitions), [01 §9.2](01-setting-the-scene.md#92-the-llm-as-the-decision-maker) | |
| A subagent that always runs when called | Agents versus objects: the receiver decides | [01 §8.4](01-setting-the-scene.md#84-agents-versus-objects) | R7 |
| Plans and to-do lists in coding agents | BDI intentions, commitment versus reconsideration | [02 §3](02-agent-architectures.md#3-belief-desire-intention-bdi-architectures) | R8 |
| Guardrails that override the model | Layered architectures, censor rules | [02 §4](02-agent-architectures.md#4-layered-architectures) | R9 |
| The context window as what the agent knows | Belief base, with a fixed size and uneven attention | [02 §6](02-agent-architectures.md#6-where-llm-agents-fit), [14 §1](14-context-engineering.md#1-the-context-window-as-a-constraint) | |
| Retrieval returns the nearest wrong match | Plan library selection, without a threshold | [14 §2](14-context-engineering.md#2-assembling-context-per-call) | |
| Context compaction, summarisation, thrashing | None | [14 §4](14-context-engineering.md#4-reducing-context) | |
| Behaviour written in prompts, with no goal model | Agent-oriented programming languages | [16 §2](16-agent-programming-and-platforms.md#2-agent-oriented-programming-languages) | |
| An LLM inside a symbolic agent loop | Hybrid BDI with LLM plans | [16 §7](16-agent-programming-and-platforms.md#7-llms-inside-agent-platforms) | |

## Communication

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| MCP tool call versus A2A request | Method invocation versus communicative act | [07 §1](07-agent-communication.md#1-communication-as-action), [07 §6](07-agent-communication.md#6-mcp-and-a2a) | |
| The kind of request hidden in natural language | Performatives in KQML and FIPA ACL | [07 §4](07-agent-communication.md#4-agent-communication-languages), [07 §6.3](07-agent-communication.md#63-classical-and-modern-compared) | |
| Tool schemas, agent cards, registries | Ontologies, directory facilitator | [07 §3](07-agent-communication.md#3-shared-meaning-ontologies), [07 §4.3](07-agent-communication.md#43-conformance-and-platforms) | |
| An orchestrator promising work for a subagent | Commitments: one agent cannot commit another | [07 §5.3](07-agent-communication.md#53-commitments-social-semantics) | |
| Model output fed unchecked to other systems | The sincerity condition, which an LLM cannot meet | [07 §7.1](07-agent-communication.md#71-assertions-without-beliefs) | |
| "Nothing found" passed on as ordinary text | `failure` and `refuse` as typed messages | [07 §7.3](07-agent-communication.md#73-saying-i-do-not-know) | R7 |
| Citations that do not support the claim | Justification, source of a trust image | [07 §7.4](07-agent-communication.md#74-where-a-claim-came-from) | |

## Working as a Team

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| Orchestrator delegating to subagents | Contract Net, by directed contract | [08 §3](08-working-together.md#3-task-sharing-the-contract-net) | R7 |
| Parallel agents with a judge | Result sharing | [08 §4](08-working-together.md#4-result-sharing-and-inconsistency) | |
| Sequential, parallel, hierarchical patterns | Cooperative distributed problem solving | [08 §7](08-working-together.md#7-modern-practice-sayfans-patterns) | |
| Each agent succeeds, the team goal fails | Joint persistent goals | [08 §5.2](08-working-together.md#52-joint-intentions), [08 §8](08-working-together.md#8-coordination-failures) | |
| An agent reports success it did not achieve | A broken team convention | [08 §8](08-working-together.md#8-coordination-failures), [16 §6](16-agent-programming-and-platforms.md#6-exceptions-and-accountability) | |
| Duplicated work, agents undoing each other | Partial global planning, social laws | [08 §5](08-working-together.md#5-coordination) | |
| Agents that do not know when to stop | Commitment strategies, stop conditions | [08 §9](08-working-together.md#9-stopping-and-human-control) | R13 |
| Human approval of risky actions | Adjustable autonomy | [08 §9.5](08-working-together.md#95-human-control) | |
| Central orchestrator versus peers | Communication topology | [01 §10](01-setting-the-scene.md#10-a-control-theory-view-nagahara-azuma-and-ahn) | R1 |
| Agents debating toward one answer | Consensus | [06 §1](06-control-of-cooperative-mas.md#1-consensus-agreeing-on-a-value) | R2 |
| Splitting a codebase among subagents | Coverage | [06 §2](06-control-of-cooperative-mas.md#2-coverage-dividing-a-space) | R3 |
| Workflows and task graphs | Protocols checked for safety and liveness | [16 §5](16-agent-programming-and-platforms.md#5-protocols-as-programs) | R7 |
| A shared file or board several agents use | Artifacts in a shared environment | [16 §4](16-agent-programming-and-platforms.md#4-the-environment-as-a-programming-abstraction) | |
| Roles, rules, and who may do what | Organisations, norms, institutions | [04](04-multiagent-organisations.md) | |
| Supervision and restart of agents | Actor frameworks | [16 §3](16-agent-programming-and-platforms.md#3-agents-and-actors) | R11, R12 |

## Trust and Security

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| Prompt injection | Trust as evaluation then decision. Content as instructions is new. | [05 §3](05-trust-and-reputation.md#3-trust), [05 §8](05-trust-and-reputation.md#8-content-as-instructions) | |
| Gamed skill rankings, malicious updates | Attacks on reputation | [05 §5](05-trust-and-reputation.md#5-attacks-on-reputation) | R10 |
| Agent certification | Institutional power | [04 §4](04-multiagent-organisations.md#4-institutions-norms-permission-and-power), [16 §8.2](16-agent-programming-and-platforms.md#82-trust-and-governance) | |
| Policies written in natural language | Regimented versus regulated norms | [04 §4.2](04-multiagent-organisations.md#42-regimented-versus-regulated-norms) | |

## Agents with Different Owners

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| A buyer's agent meets a vendor's agent | Strategic interaction, equilibria | [09](09-strategic-interaction.md) | R6 |
| Agents or judges voting | Social choice, manipulation | [10](10-group-decisions.md), [15 §4](15-evaluating-agent-systems.md#4-llm-judges) | |
| Allocating tasks or resources by bids | Auctions, mechanism design | [11](11-coalitions-and-auctions.md) | |
| Agent-to-agent negotiation | Bargaining, argumentation | [12](12-bargaining-and-argumentation.md) | R6 |
| Agents adapting while others adapt, team credit | Multiagent learning | [13](13-multiagent-learning.md) | |

## Agents in a Complex World

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| Good agents, bad collective outcome | Emergence, levels slippage | [17 §1](17-agents-in-complex-systems.md#1-complex-systems-and-emergence) | |
| Cascades once automated traffic passes a threshold | Tipping points, leverage points | [17 §2](17-agents-in-complex-systems.md#2-outcomes-nobody-chose) | |
| Agents on one base model rushing the same resource | Monoculture of predictors (El Farol) | [17 §3](17-agents-in-complex-systems.md#3-monoculture) | R14 |
| Coordination through repos, boards, shared files | Stigmergy, sematectonic information | [17 §2](17-agents-in-complex-systems.md#2-outcomes-nobody-chose), [17 §4](17-agents-in-complex-systems.md#4-self-organisation) | |
| Registries and popular agents as single points of spread | Hubs, preferential attachment | [17 §5](17-agents-in-complex-systems.md#5-networks-and-hubs) | |
| Forming teams under residency, latency, budget limits | Constrained coalition formation | [17 §6](17-agents-in-complex-systems.md#6-coalitions-under-real-constraints) | |
| Dropping bad counterparties in an open ecosystem | Reputation with partner switching | [17 §7](17-agents-in-complex-systems.md#7-reputation-and-partner-switching) | |
| Testing a population, not one agent | Validation, replication, docking | [17 §8](17-agents-in-complex-systems.md#8-studying-a-population) | R14 |

## Cost, Evaluation, and Change

| Practice or failure | Concept | Where | Test |
|---|---|---|---|
| Every message and turn billed by length | Communication cost, bounded rationality | [14 §5](14-context-engineering.md#5-cost-and-latency) | R4, R5 |
| Same input, different output | None | [15 §1](15-evaluating-agent-systems.md#1-why-classical-evaluation-does-not-transfer) | |
| LLM judges and their bias | Governors, which were deterministic | [15 §4](15-evaluating-agent-systems.md#4-llm-judges) | |
| Multi-agent versus a single agent with tools | Coherence and coordination measures | [15 §5](15-evaluating-agent-systems.md#5-what-the-evidence-says-about-multi-agent-designs) | R5 |
| Behaviour changes with prompt, model, or data | None. Nearest is non-stationarity. | [15 §6](15-evaluating-agent-systems.md#6-change-control) | |
