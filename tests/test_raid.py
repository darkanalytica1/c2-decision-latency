import pytest

from c2latency import (
    Layer,
    common_mode_pra,
    expected_leakers,
    layered_raid,
    leaker_distribution,
    magazine,
    p_any_leak,
    p_raid_annihilation,
    shots_needed,
)


@pytest.mark.parametrize(
    "shots, pra, leakers, rounds",
    [(1, 0.107, 2.0, 10), (2, 0.665, 0.4, 20), (3, 0.923, 0.08, 30)],
)
def test_ten_threat_raid_worked_example(shots, pra, leakers, rounds):
    assert p_raid_annihilation(10, 0.8, shots) == pytest.approx(pra, abs=5e-4)
    assert expected_leakers(10, 0.8, shots) == pytest.approx(leakers)
    assert magazine(10, shots) == rounds


def test_twenty_threat_raid_three_shots():
    assert p_raid_annihilation(20, 0.8, 3) == pytest.approx(0.852, abs=5e-4)


def test_interception_rate_is_not_a_defended_outcome():
    # 95% single-shot, one shot each, twenty threats: still leaks with probability 0.64
    assert p_any_leak(20, 0.95, 1) == pytest.approx(0.64, abs=5e-3)


def test_leaker_distribution():
    dist = leaker_distribution(10, 0.8, 1)
    assert sum(dist) == pytest.approx(1.0)
    assert dist[0] == pytest.approx(p_raid_annihilation(10, 0.8, 1))
    assert sum(k * pk for k, pk in enumerate(dist)) == pytest.approx(2.0)


def test_shots_needed():
    assert shots_needed(10, 0.8, 0.9) == 3
    assert shots_needed(10, 0.8, 0.6) == 2
    with pytest.raises(ValueError):
        shots_needed(10, 0.0, 0.9)


def test_layered_defence():
    result = layered_raid(10, [Layer("outer", 0.5, 1), Layer("inner", 0.8, 2)])
    assert result.leak_per_threat == pytest.approx(0.02)
    assert result.pra == pytest.approx(0.98**10)
    assert result.expected_leakers == pytest.approx(0.2)
    assert result.expected_rounds == {"outer": pytest.approx(10), "inner": pytest.approx(10)}


def test_single_layer_matches_closed_form():
    result = layered_raid(10, [Layer("only", 0.8, 2)])
    assert result.pra == pytest.approx(p_raid_annihilation(10, 0.8, 2))


def test_common_mode_failure_caps_the_defence():
    assert common_mode_pra(10, 0.8, 3, 0.1) == pytest.approx(0.9 * 0.923, abs=1e-3)
    assert common_mode_pra(10, 0.8, 50, 0.1) <= 0.9


def test_validation():
    with pytest.raises(ValueError):
        p_raid_annihilation(10, 1.2, 1)
    with pytest.raises(ValueError):
        Layer("bad", 0.5, -1)
