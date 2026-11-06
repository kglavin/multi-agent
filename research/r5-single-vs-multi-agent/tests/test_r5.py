import json

import pytest

import cases
from corpus import S2_DIR, S3_DIR, generate_s2
from score import extract_json, score_exact, score_list, score_map
from tools import corpus_tools

needs_s3 = pytest.mark.skipif(not (S3_DIR / "django").exists(), reason="run corpus.py to fetch S3")


def rows():
    return [json.loads(line) for line in cases.CASES_FILE.read_text().splitlines()]


def by_id():
    return {r["id"]: r["expected"] for r in rows()}


def test_thirty_cases_ten_per_suite():
    suites = [r["suite"] for r in rows()]
    assert len(suites) == 30 and all(suites.count(s) == 10 for s in ("S1", "S2", "S3"))


def test_list_cases_have_at_least_three_answers():
    assert all(len(r["expected"]) >= 3 for r in rows() if r["kind"] == "list")


def test_s1_answers_match_hand_working():
    expected = [245, "Friday", 14, 44, 6, "12:25", "apple", 7, 15, 20]
    assert [by_id()[f"S1-{i:02d}"] for i in range(1, 11)] == expected


def test_committed_s2_corpus_matches_generator():
    docs, _ = generate_s2()
    assert {p.name: p.read_text() for p in S2_DIR.glob("*.md")} == docs


def test_s2_current_facts_appear_in_their_document():
    docs, facts = generate_s2()
    for f in facts:
        text = docs[f["name"].lower().replace(" ", "-") + ".md"]
        assert f", to {f['city']}, {f['country']}," in text
        assert f"it is now {f['lead_time_days']} days" in text
        assert f"The account contact is {f['contact']}," in text


def test_cases_file_is_current():
    if not (S3_DIR / "django").exists():
        pytest.skip("run corpus.py to fetch S3")
    assert rows() == cases.build()


@needs_s3
def test_s3_spot_checks():
    e = by_id()
    assert e["S3-07"]["sqlite3"] == "sqlite"
    assert e["S3-08"] == {"oracle": "19", "postgresql": "14", "sqlite3": "3.31"}
    assert {"CharField", "CompositePrimaryKey"} <= set(e["S3-02"])
    assert "post_save" in e["S3-10"]
    assert e["S3-01"]["auth"] == "Authentication and Authorization"


def test_load_gives_harness_cases():
    loaded = cases.load()
    assert loaded[0].id == "S1-01" and loaded[0].expected == {"kind": "exact", "value": 245}


def test_score_exact_normalises():
    assert score_exact(245, " 245. ") == 1.0
    assert score_exact("Friday", "friday") == 1.0
    assert score_exact(7, "7.0") == 1.0
    assert score_exact(7, "seven") == 0.0


def test_score_list_is_f1():
    assert score_list(["a", "b"], '```json\n["A", "b"]\n```') == 1.0
    assert score_list(["a", "b"], '["a", "c"]') == 0.5
    assert score_list(["a", "b"], "a and b") == 0.0


def test_score_map_counts_matching_keys():
    expected = {"Tandor Works": 33, "Vikzet Supply": 19}
    assert score_map(expected, 'Here: {"tandor works": "33", "Vikzet Supply": 21}') == 0.5
    assert score_map(expected, "no json") == 0.0


def test_extract_json_skips_wrong_type():
    assert extract_json('{"a": [1]} then ["x"]', list) == [1]
    assert extract_json('["x"] then {"a": 1}', dict) == {"a": 1}


def test_tools_stay_inside_corpus():
    tools = {t.spec.name: t.fn for t in corpus_tools(S2_DIR)}
    assert "error" in tools["read_file"]("../../cases.py")
    assert "error" in tools["list_files"]("..")
    first = sorted(S2_DIR.glob("*.md"))[0].name
    assert first in tools["list_files"]()
    assert tools["read_file"](first, 1, 1).startswith("# ")
    assert "lead time" in tools["search"]("now \\d+ days")


def test_tool_output_is_capped(tmp_path):
    (tmp_path / "big.txt").write_text("x" * 50 + "\n" + "y" * 50)
    tools = {t.spec.name: t.fn for t in corpus_tools(tmp_path, max_chars=40)}
    out = tools["read_file"]("big.txt")
    assert out.startswith("x" * 40) and "cut at 40 characters" in out
    assert tools["read_file"]("big.txt", 2, 2).startswith("y" * 40)


def test_duplicate_tool_calls_counts_repeats_per_run():
    from run import duplicate_tool_calls

    def ev(run, name, args):
        return {"event": "tool_result", "run_id": run, "name": name, "args": args}

    log = [ev("r1", "read_file", {"path": "a"}), ev("r1", "read_file", {"path": "a"}),
           ev("r1", "read_file", {"path": "b"}), ev("r2", "read_file", {"path": "a"}),
           ev("r1", "delegate", {"task": "x"}), ev("r1", "delegate", {"task": "x"})]
    assert duplicate_tool_calls(log) == {"r1": 1}


def test_pilot_runs_every_suite_and_config_on_stub(tmp_path):
    from harness import run_experiment
    from run import MODELS, build_configs, load_suite
    from score import score

    for suite in ("S1", "S2"):
        cases, corpus = load_suite(suite, 1)
        results = run_experiment(tmp_path / suite, cases, build_configs(MODELS["stub"](), corpus, 20), 1,
                                 score=score)
        assert [r["config"] for r in results] == ["C1", "C2", "C3", "C4"]
        assert not any(r["stopped"] for r in results)
