# R11 Ractor in the Browser

Status: viability pass done (2026-11-01). Not started.

## Question

Can ractor actors run in the browser as WebAssembly, act as a helper to a React/TypeScript web app, and exchange typed messages with a server-side ractor actor over a WebSocket?

```mermaid
flowchart LR
  subgraph browser["Browser"]
    subgraph mainth["Main thread"]
      UI[React/TypeScript app]
    end
    subgraph worker["Web Worker (WebAssembly)"]
      BA[Ractor actor]
    end
    UI <-->|"typed messages"| BA
  end
  subgraph server["Server (native Rust)"]
    SA[Ractor actor]
  end
  BA <-->|"WebSocket<br/>(ractor_cluster messages)"| SA
```

## Findings

| Code | Finding | Effect |
|---|---|---|
| F1 | ractor supports the browser target `wasm32-unknown-unknown` since v0.15.3, with browser-run tests and thread-local actors. Current version is 0.16. | A ractor actor can run in the browser. |
| F2 | `ractor_cluster` supports "bring your own transport": implement `ClusterBidiStream` and inject the connection. Remote actors exchange serialized messages. No ready-made WebSocket adapter was found. Whether `ractor_cluster` compiles to `wasm32-unknown-unknown` is unconfirmed. | The main unknown. If it compiles, browser and server actors join one cluster. If not, messages need a hand-written protocol over WebSocket. |
| F3 | WebAssembly threads need cross-origin isolation headers. Memory64 (over 4 GB) is not in Safari. | Plan for single-threaded actors under 4 GB. |
| F4 | Rust compiled with `wasm-bindgen` imports into a React/TypeScript app as an ES module. Message types defined in Rust can generate TypeScript types (`tsify` or `ts-rs`) and cross the boundary with `serde-wasm-bindgen`. | React talks to the actor through a typed interface defined once in Rust. Running the actor in a Web Worker keeps it off React's rendering thread. |

## Risk

`ractor_cluster` does not compile to WebAssembly, forcing a hand-written message protocol between browser and server actors.

## Spike Plan

| Code | Question | Smallest test |
|---|---|---|
| Q1 | Can a browser actor and a server actor exchange typed messages using `ractor_cluster` over a WebSocket `ClusterBidiStream`? | One actor in the browser and one native actor on a server exchanging a typed request and reply. |
| Q2 | Does ractor run inside a Web Worker? | Run the Q1 browser actor in a Web Worker instead of the main thread. |
| Q3 | Can a React app use the actor as a helper through generated TypeScript types? | A React component sends a typed request to the worker actor and renders a stream of typed replies. Check UI responsiveness under a fast stream. |

## Prior Art from Agent Platforms

From Collier, Mascardi, and Ricci (eds.), *Agents and Multi-Agent Systems Development*, Springer, 2026, and [learn/16](../../learn/16-agent-programming-and-platforms.md). Covers R11 and [R12](../README.md#backlog). None of the platforms addresses messages sent while offline, reconnection, or supervising an absent node.

| Code | Prior art | Use |
|---|---|---|
| P1 | JS-son shadow agent (Ch. 5.5.2). The server holds a proxy agent whose runner forwards percepts over a WebSocket to the real agent on a client. Each environment cycle starts when the client's message arrives. The wire format, and whether the client is a browser, are not stated. | R11: a server-side proxy actor standing in for the browser actor. R12: if the cycle waits on the client, a disconnected client stalls it, so the proxy must not block. |
| P2 | Orleans virtual actors (Ch. 3.3.6). An actor has a permanent identity, is activated when called, and has its state persisted. | R12: reclaiming identity and state after reconnecting. |
| P3 | Akka supervision trees and event sourcing (Ch. 3.3.5). Restart failed actors and rebuild state by replaying events. | R12: restart and catch-up. |
| P4 | Jadex 4 overlay network (Ch. 3.7.7). Relay nodes and hole punching reach peers behind firewalls. Being ported to Jadex V. | R11: the WebSocket server plays the relay role for a browser that cannot accept inbound connections. |
| P5 | Jadex V boundaries (Ch. 3.4.5, 3.4.7). Calls between components copy arguments and results to keep isolation. The exception registry's default kills the component, with no restart strategy. | R11: copy semantics at the browser-server boundary. Contrast with ractor supervision. |
| P6 | JaKtA virtualisation API (Ch. 6.4.3). Time, scheduling, perception, and randomness sit behind one interface for reproducible simulation. | R12: deterministic tests of disconnect and reconnect. |
| P7 | Yggdrasil body artifacts (Ch. 7.3.1). An agent's presence in a workspace is separate from the process running it. WebSub perception needs a reachable subscriber, which a browser is not. | R12: a server-side presence for an offline frontend. |
| P8 | BSPL information protocols and Mandrake (Ch. 8.3.1, 8.3.4). Messages depend on information, not order, so reordering and duplicates are harmless. Agents resend or remind when a reply may be lost. | R12: design messages so that redelivery after reconnecting is safe. |

## Possible Follow-ups

Ideas raised during the viability pass, out of scope for R11:

- Use the browser actor as an agent orchestrator, with a small hosted gateway holding API keys and proxying LLM calls.
- Run worker agents, source, and tools in a per-user dev container, with the orchestrator in the browser.
- Host the agent in VS Code, using VS Code Remote for files, terminal, and search.

## Sources

- Collier, Mascardi, and Ricci (eds.), *Agents and Multi-Agent Systems Development: Platforms, Toolkits, Technologies*, Springer, 2026, Chapters 3, 5, 6, 7, and 8.
- [ractor releases](https://github.com/slawlor/ractor/releases)
- [ractor repository](https://github.com/slawlor/ractor)
- [ractor_cluster README](https://docs.rs/crate/ractor_cluster/latest/source/README.md)
- [Memory64 browser support (web-features explorer)](https://web-platform-dx.github.io/web-features-explorer/features/wasm-memory64/)
