# Harness

Shared Python code for the LLM research items (R1 to R8, R13, R14). It runs cases under several agent configurations, repeats each run, and logs every model call with its tokens and time.

Status: runs with the stub model and with any OpenAI-style server, used with qwen3:8b on Ollama.

## Layout

| File | Contents |
|---|---|
| `src/harness/model.py` | Message and tool types, the `Model` interface, and `StubModel` |
| `src/harness/agent.py` | One agent loop: call the model, run tool calls, repeat until a text answer or the step cap |
| `src/harness/configs.py` | R5's configurations built from that loop: `direct` (C1), `single` (C2), `orchestrator` (C3), `group_chat` (C4) |
| `src/harness/record.py` | `Recorder` (JSONL events) and `Budget` (token and call caps per run) |
| `src/harness/openai_compat.py` | `OpenAICompatModel` and `ollama()`. See [Real models](#real-models). |
| `src/harness/run.py` | `run_experiment` and `summarise` |
| `examples/dry_run.py` | C1 to C4 on a toy lookup task with the stub |

## Use

```bash
cd research/harness
uv sync
uv run pytest
uv run python examples/dry_run.py [out_dir]
```

A research item keeps its own cases, scoring, configuration choices, and results in its folder, and calls `run_experiment`. Each experiment writes:

| File | Contents |
|---|---|
| `meta.json` | Start time, git commit, configurations, runs, seed, and budget |
| `log.jsonl` | One line per event: model calls (agent, step, tokens, latency, text, tool calls), tool results (name, arguments, size), step and round caps, budget stops |
| `results.jsonl` | One line per run: answer, score, tokens, calls, wall time, and whether the budget stopped it |

Run experiments as scripts. Use notebooks only to read these files.

## Real models

`ollama("qwen3:8b")` or `ollama("qwen3:8b", think=False)` returns a model for any study's `MODELS`. It reads two settings from the environment, which the justfile loads from a gitignored `.env` at the repo root:

```text
OLLAMA_BASE_URL=http://<host>:11434/v1
OLLAMA_CONTEXT_LIMIT=20480
```

Behaviour found on Ollama 0.40 with qwen3:8b:

1. Ollama cuts an over-long prompt from the front without an error. With `OLLAMA_CONTEXT_LIMIT` set, a prompt that reaches it raises `ContextOverflow`, which stops the run like a budget stop. Ollama divides its context length between parallel slots (`OLLAMA_NUM_PARALLEL`), so the limit per request can be half what `/api/ps` reports.
2. `think=False` sends `reasoning_effort: "none"`, which turns thinking off. `think: false` is ignored on this endpoint. Thinking text is logged as `reasoning_chars`.
3. qwen3 sometimes writes a tool call as JSON text. When the whole reply is such JSON naming a known tool, the adapter turns it into a tool call with an id starting `text_`.
4. Tool calls with bad arguments return the error to the model instead of stopping the run.

## Limits

- Stub token counts are estimates at four characters per token. They check the harness and are not results.
- In `group_chat`, tool calls stay inside an agent's turn and only its final text joins the shared transcript.
- No peer-to-peer configuration yet. R1 will define who messages whom.
