import io
import json

import pytest
from harness import Budget, Recorder, StubModel

import el_farol
from llm_el_farol import STYLES, Config, Game, parse_decision, run
from run_llm import always_go, random_policy


def go_model():
    return StubModel(always_go, name="stub-go")


def test_parse_decision():
    assert parse_decision("Crowds are falling.\nDECISION: GO") is True
    assert parse_decision("decision: stay") is False
    assert parse_decision("DECISION: GO\nOn reflection, DECISION: STAY") is False
    assert parse_decision("I will go.") is None
    assert parse_decision("DECISION: GONE") is None


def test_homogeneous_prompts_are_identical():
    game = Game(Config(condition="homogeneous"), [go_model()])
    assert len({game.system_prompt(a) for a in range(20)}) == 1
    assert len({game.user_prompt(a) for a in range(20)}) == 1


def test_varied_prompts_differ_only_in_style():
    game = Game(Config(condition="varied_prompts"), [go_model()])
    systems = [game.system_prompt(a) for a in range(20)]
    assert len(set(systems)) == len(STYLES)
    assert all(s.endswith(STYLES[a % len(STYLES)]) for a, s in enumerate(systems))
    assert len({game.user_prompt(a) for a in range(20)}) == 1


def test_private_info_views_differ_and_are_stable():
    game = Game(Config(condition="private_info"), [go_model()])
    assert len({game.system_prompt(a) for a in range(20)}) == 1
    views = [game.user_prompt(a) for a in range(20)]
    assert len(set(views)) > 1
    assert any("unknown" in v for v in views)
    assert game.user_prompt(3) == views[3]


def test_varied_models_assigns_round_robin():
    a, b = go_model(), StubModel(name="other")
    game = Game(Config(condition="varied_models"), [a, b])
    assert [game.model_for(i).name for i in range(4)] == ["stub-go", "other", "stub-go", "other"]
    with pytest.raises(ValueError):
        Game(Config(condition="varied_models"), [a])


def test_always_go_gives_full_attendance_and_no_reward():
    row = run(Config(condition="homogeneous", weeks=10), [go_model()], Recorder(io.StringIO()))
    assert row["mean_attendance"] == 20 and row["sd_attendance"] == 0
    assert row["crowded_fraction"] == 1.0
    assert row["mean_reward"] == 0 and row["reward_gini"] == 0
    assert row["calls"] == 200 and row["unparseable"] == 0


def test_unparseable_counts_as_stay():
    model = StubModel(lambda m, t: ("I think I will go.", []))
    row = run(Config(weeks=3), [model], Recorder(io.StringIO()))
    assert row["unparseable"] == 60 and row["mean_attendance"] == 0


def test_rewards_match_hand_count():
    game = Game(Config(n_agents=4, threshold=2, weeks=1), [StubModel()])
    game.outcomes = [[] for _ in range(4)]
    # Agents 0 and 1 go: 2 is not crowded, so both score.
    replies = iter(["DECISION: GO", "DECISION: GO", "DECISION: STAY", "nothing"])
    game.models = [StubModel(lambda m, t: (next(replies), []))]
    game.play_week(Recorder(io.StringIO()), Budget())
    assert game.attendance == [2] and game.rewards == [1, 1, 0, 0] and game.unparseable == 1
    assert game.outcomes[0] == ["went, good night"] and game.outcomes[2] == ["stayed home"]


def test_budget_stops_the_game():
    row = run(Config(weeks=50, max_calls=45), [go_model()], Recorder(io.StringIO()))
    assert row["stopped"] and row["weeks_played"] == 2 and row["calls"] == 46


def test_random_stub_is_seeded():
    def once(seed):
        return run(Config(weeks=5, seed=seed), [StubModel(random_policy(seed))], Recorder(io.StringIO()))
    assert once(1) == once(1)
    assert once(1)["mean_attendance"] != once(2)["mean_attendance"]


def test_log_has_every_call_and_decision():
    buf = io.StringIO()
    run(Config(weeks=2, n_agents=3, threshold=1), [go_model()], Recorder(buf, run_id="r"))
    kinds = [json.loads(line)["event"] for line in buf.getvalue().splitlines()]
    assert kinds.count("model_call") == 6 and kinds.count("decision") == 6 and kinds.count("week") == 2


def test_baseline_runs_at_small_size():
    row = el_farol.run(weeks=50, burn_in=0, n_agents=20, overcrowding_threshold=12, seed=0)
    assert 0 <= row["mean_attendance"] <= 20
    model = el_farol.ElFarol(n_agents=20, overcrowding_threshold=12, homogeneous=True, seed=1)
    for _ in range(50):
        model.step()
    assert set(model.attendance) <= {0, 20}
