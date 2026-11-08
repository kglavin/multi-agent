import io
import json

import pytest

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


def test_report_draws_delegation_and_charts(tmp_path):
    from harness.report import build_report, sequence_diagram

    model = StubModel(script=[
        ("", [ToolCall("1", "delegate", {"task": "add 2 and 2"})]),
        ("", [ToolCall("2", "add", {"a": 2, "b": 2})]),
        ("4", []),
        ("4", []),
    ])
    configs = {"C3": orchestrator(model, "orch", "worker", [ADD])}
    run_experiment(tmp_path, [Case("c1", "2+2?", "4")], configs, runs=1)
    report = build_report(tmp_path)
    assert report.count("```mermaid") == 4
    diagram = sequence_diagram([json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()])
    assert 'a_orchestrator->>a_worker_1: delegate "add 2 and 2"' in diagram
    assert 'a_worker_1-->>a_orchestrator: "4"' in diagram


def test_bad_tool_arguments_go_back_to_the_model():
    model = StubModel(script=[("", [ToolCall("1", "add", {"x": 1})]), ("sorry", [])])
    buf = io.StringIO()
    assert single(model, "sys", [ADD])("q", Recorder(buf), Budget()) == "sorry"
    result = [e for e in events(buf) if e["event"] == "tool_result"][0]
    assert result["chars"] > 0


def test_openai_compat_round_trip_and_overflow(monkeypatch):
    from harness import ContextOverflow, OpenAICompatModel, Message
    from harness import openai_compat

    sent = {}

    def fake_post(self, payload):
        sent.update(payload)
        return {"model": "m", "usage": {"prompt_tokens": 120, "completion_tokens": 7},
                "choices": [{"message": {"content": "", "reasoning": "hmm",
                                         "tool_calls": [{"id": "c1", "function": {"name": "add",
                                                                                  "arguments": '{"a": 1, "b": 2}'}}]}}]}

    monkeypatch.setattr(openai_compat.OpenAICompatModel, "_post", fake_post)
    model = OpenAICompatModel("m", base_url="http://x/v1", extra={"reasoning_effort": "none"})
    history = [Message("user", "q"), Message("assistant", "", [ToolCall("c0", "add", {"a": 0, "b": 0})]),
               Message("tool", "0", tool_call_id="c0")]
    r = model.complete(history, [ADD.spec])
    assert r.tool_calls[0].args == {"a": 1, "b": 2} and r.reasoning == "hmm" and r.input_tokens == 120
    assert sent["reasoning_effort"] == "none" and sent["tools"][0]["function"]["name"] == "add"
    assert sent["messages"][1]["tool_calls"][0]["function"]["arguments"] == '{"a": 0, "b": 0}'
    assert sent["messages"][2]["tool_call_id"] == "c0"
    with pytest.raises(ContextOverflow):
        OpenAICompatModel("m", base_url="http://x/v1", context_limit=100).complete(history, [])


def test_text_tool_calls_are_recovered_only_when_unambiguous():
    from harness.openai_compat import text_tool_calls

    names = {"list_files", "read_file"}
    got = text_tool_calls('{"name": "list_files", "arguments": {"path": "."}}', names)
    assert [(c.id, c.name, c.args) for c in got] == [("text_0", "list_files", {"path": "."})]
    fenced = '```json\n{"name": "read_file", "arguments": {"path": "a.md"}}\n```'
    assert text_tool_calls(fenced, names)[0].name == "read_file"
    assert text_tool_calls('<tool_call>\n{"name": "read_file", "arguments": {"path": "a"}}\n</tool_call>', names)
    assert text_tool_calls('{"name": "delete_all", "arguments": {}}', names) == []
    assert text_tool_calls('Here you go: {"name": "list_files", "arguments": {}}', names) == []
    assert text_tool_calls('{"Tandor Works": "Leipzig"}', names) == []


def test_empty_reply_gets_one_nudge():
    model = StubModel(script=[("", []), ("4", [])])
    buf = io.StringIO()
    assert single(model, "sys", [ADD])("q", Recorder(buf), Budget()) == "4"
    assert [e["event"] for e in events(buf)] == ["model_call", "empty_reply", "model_call"]
    model = StubModel(script=[("", []), ("", [])])
    assert single(model, "sys", [ADD])("q", Recorder(io.StringIO()), Budget()) == ""


def test_delegate_rejects_a_non_string_task_and_continues():
    model = StubModel(script=[
        ("", [ToolCall("1", "delegate", {"task": {"type": "string", "value": "add"}})]),
        ("4", []),
    ])
    buf = io.StringIO()
    assert orchestrator(model, "orch", "worker", [ADD])("2+2?", Recorder(buf), Budget()) == "4"
    agents = [e["agent"] for e in events(buf) if e["event"] == "model_call"]
    assert agents == ["orchestrator", "orchestrator"]


def test_budget_stop_inside_a_worker_stops_the_run():
    model = StubModel(script=[
        ("", [ToolCall("1", "delegate", {"task": "add"})]),
        ("", [ToolCall("2", "add", {"a": 1, "b": 1})]),
        ("2", []),
        ("2", []),
    ])
    with pytest.raises(BudgetExceeded):
        orchestrator(model, "orch", "worker", [ADD])("q", Recorder(io.StringIO()), Budget(max_calls=2))


def test_http_client_errors_are_not_retried(monkeypatch):
    import urllib.error
    import urllib.request

    from harness import OpenAICompatModel, Message

    attempts = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        raise urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b"content must be a string"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="HTTP 400.*content must be a string"):
        OpenAICompatModel("m", base_url="http://x/v1").complete([Message("user", "q")], [])
    assert len(attempts) == 1
