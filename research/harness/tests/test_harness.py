import io
import json

from harness import (FINAL, Agent, Budget, BudgetExceeded, Case, Recorder, StubModel, Tool, ToolCall,
                     ToolSpec, direct, group_chat, orchestrator, run_experiment, single, summarise)

ADD = Tool(
    ToolSpec("add", "Add two numbers.", {"type": "object", "properties": {"a": {}, "b": {}}}),
    lambda a, b: str(a + b),
)


def events(buf: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buf.getvalue().splitlines()]


def test_single_agent_calls_tool_then_answers():
    model = StubModel(script=[("", [ToolCall("1", "add", {"a": 2, "b": 2})]), ("4", [])])
    buf = io.StringIO()
    budget = Budget()
    answer = single(model, "sys", [ADD])("2+2?", Recorder(buf, run_id="r"), budget)
    assert answer == "4"
    kinds = [e["event"] for e in events(buf)]
    assert kinds == ["model_call", "tool_result", "model_call"]
    assert budget.calls == 2 and budget.tokens > 0


def test_direct_is_one_call_without_tools():
    model = StubModel(script=[("4", [])])
    budget = Budget()
    assert direct(model, "sys")("2+2?", Recorder(io.StringIO()), budget) == "4"
    assert budget.calls == 1


def test_budget_stops_run():
    model = StubModel(script=[("", [ToolCall("1", "add", {"a": 1, "b": 1})]), ("2", [])])
    budget = Budget(max_calls=1)
    try:
        single(model, "sys", [ADD])("1+1?", Recorder(io.StringIO()), budget)
        assert False, "expected BudgetExceeded"
    except BudgetExceeded:
        pass


def test_step_cap_returns_empty():
    loop = ("", [ToolCall("1", "add", {"a": 1, "b": 1})])
    model = StubModel(script=[loop, loop])
    buf = io.StringIO()
    agent = Agent("a", model, "sys", [ADD], max_steps=2)
    assert agent.run("go", Recorder(buf), Budget()) == ""
    assert events(buf)[-1]["event"] == "step_cap"


def test_orchestrator_delegates_to_fresh_worker():
    model = StubModel(script=[
        ("", [ToolCall("1", "delegate", {"task": "add 2 and 2"})]),  # orchestrator
        ("", [ToolCall("2", "add", {"a": 2, "b": 2})]),              # worker-1
        ("4", []),                                                    # worker-1
        ("4", []),                                                    # orchestrator
    ])
    buf = io.StringIO()
    answer = orchestrator(model, "orch", "worker", [ADD])("2+2?", Recorder(buf), Budget())
    assert answer == "4"
    agents = [e["agent"] for e in events(buf) if e["event"] == "model_call"]
    assert agents == ["orchestrator", "worker-1", "worker-1", "orchestrator"]


def test_group_chat_shares_growing_transcript():
    model = StubModel(script=[("a long draft " * 20, []), (f"{FINAL} 4", [])])
    buf = io.StringIO()
    chat = group_chat(model, {"writer": "w", "critic": "c"}, [])
    assert chat("2+2?", Recorder(buf), Budget()) == "4"
    calls = [e for e in events(buf) if e["event"] == "model_call"]
    assert [c["agent"] for c in calls] == ["writer", "critic"]
    assert calls[1]["input_tokens"] > calls[0]["input_tokens"]


def test_run_experiment_writes_logs_and_scores(tmp_path):
    cases = [Case("c1", "q1", "stub answer"), Case("c2", "q2", "other")]
    configs = {"direct": direct(StubModel(), "sys"), "single": single(StubModel(), "sys", [ADD])}
    results = run_experiment(tmp_path, cases, configs, runs=3)
    assert len(results) == 12
    assert (tmp_path / "meta.json").exists()
    assert len((tmp_path / "results.jsonl").read_text().splitlines()) == 12
    s = summarise(results)
    assert s["direct"]["mean_score"] == 0.5 and s["direct"]["runs"] == 6


def test_run_experiment_records_budget_stop(tmp_path):
    configs = {"single": single(StubModel(), "sys", [ADD])}
    results = run_experiment(tmp_path, [Case("c1", "q", "stub answer")], configs, runs=1, max_tokens=1)
    assert results[0]["stopped"] and results[0]["score"] == 0.0
