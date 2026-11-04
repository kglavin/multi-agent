import statistics

import pytest

from el_farol import ElFarol, gini, measures, predict_attendance, run


def test_same_seed_same_run():
    assert run(weeks=50, burn_in=0, seed=7) == run(weeks=50, burn_in=0, seed=7)
    assert run(weeks=50, burn_in=0, seed=7) != run(weeks=50, burn_in=0, seed=8)


def test_prediction_formula():
    # 100 * 0.5 + 1.0 * 40 - 0.5 * 20
    assert predict_attendance([0.5, 1.0, -0.5], [40, 20]) == pytest.approx(80.0)


def test_measures_on_hand_case():
    m = measures([50, 70, 60, 80], [0, 0, 0, 4], threshold=60)
    assert m["mean_attendance"] == 65
    assert m["sd_attendance"] == pytest.approx(statistics.pstdev([50, 70, 60, 80]))
    assert m["crowded_fraction"] == 0.5  # 70 and 80, since 60 is not crowded
    assert m["reward_gini"] == pytest.approx(0.75)
    assert gini([3, 3, 3]) == 0.0


def test_homogeneous_agents_act_together():
    model = ElFarol(seed=1, homogeneous=True)
    for _ in range(200):
        model.step()
    assert set(model.attendance) <= {0, 100}


def test_diverse_beats_homogeneous():
    diverse = [run(weeks=300, seed=s) for s in range(3)]
    homogeneous = [run(weeks=300, seed=s, homogeneous=True) for s in range(3)]
    for d, h in zip(diverse, homogeneous):
        assert 45 < d["mean_attendance"] < 70
        assert d["sd_attendance"] < 15
        assert d["mean_reward"] > 0
        assert h["mean_reward"] == 0  # all at home or all crowded, every week
        assert h["crowded_fraction"] > d["crowded_fraction"] or h["mean_attendance"] == 0
