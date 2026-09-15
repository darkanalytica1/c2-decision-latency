import pytest

from c2latency import LatencyBudget, decision_margin, kmh_to_ms, knots_to_ms, time_to_impact

FPV_STAGES = {"track": 5, "identify": 10, "decide": 20, "effect": 5}


def test_fpv_time_to_impact():
    v = kmh_to_ms(150)
    assert v == pytest.approx(41.67, abs=0.01)
    assert time_to_impact(2000, v) == pytest.approx(48.0, abs=0.05)
    assert time_to_impact(3000, v) == pytest.approx(72.0, abs=0.05)


def test_fpv_decision_margin_is_8_seconds():
    b = LatencyBudget(2000, kmh_to_ms(150), FPV_STAGES)
    assert b.chain_s == 40
    assert b.margin_s == pytest.approx(8.0, abs=0.05)
    assert b.closes
    assert b.binding_stage == "decide"
    assert b.share("decide") == pytest.approx(0.5)


def test_doubling_decision_time_goes_negative():
    b = LatencyBudget(2000, kmh_to_ms(150), FPV_STAGES).with_stage("decide", 40)
    assert b.margin_s == pytest.approx(-12.0, abs=0.05)
    assert not b.closes


def test_loop_budget_with_minimum_range():
    stages = {"detect": 5, "fuse": 20, "decide": 30, "act": 10, "comms": 15}
    b = LatencyBudget(3000, 30, stages, min_range_m=300)
    assert b.available_s == pytest.approx(90)
    assert b.chain_s == 80
    assert b.margin_s == pytest.approx(10)
    faster = b.with_speed(60)
    assert faster.available_s == pytest.approx(45)
    assert faster.margin_s == pytest.approx(-35)


def test_inverse_quantities():
    b = LatencyBudget(2000, kmh_to_ms(150), FPV_STAGES)
    assert b.required_detect_range_m == pytest.approx(1666.7, abs=0.1)
    assert b.max_closing_speed_m_s == pytest.approx(50.0)
    assert LatencyBudget(b.required_detect_range_m, b.closing_speed_m_s, FPV_STAGES).margin_s == pytest.approx(0, abs=1e-9)


def test_decision_margin_function_and_units():
    assert decision_margin(48, [5, 10, 20, 5]) == 8
    assert decision_margin(48, FPV_STAGES) == 8
    assert knots_to_ms(20) == pytest.approx(10.29, abs=0.01)
    with pytest.raises(ValueError):
        decision_margin(48, [-1])
    with pytest.raises(ValueError):
        time_to_impact(2000, 0)


def test_text_report():
    text = LatencyBudget(2000, kmh_to_ms(150), FPV_STAGES).as_text()
    assert "decision margin    +8.0 s  (closes in time)" in text
    assert "binding stage    decide (50% of chain)" in text
