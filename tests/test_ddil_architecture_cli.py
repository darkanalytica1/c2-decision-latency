import math

import pytest

from c2latency import (
    PRESETS,
    Architecture,
    LatencyBudget,
    Link,
    compare,
    degrade_budget,
    delivery_time,
    divergence_probability,
    evaluate,
    kmh_to_ms,
)
from c2latency.cli import main


def test_delivery_time_per_condition():
    assert delivery_time(PRESETS["connected"]) == pytest.approx(0.5)
    # 0.5 / 0.7 + 2 * 0.3 / 0.7
    assert delivery_time(PRESETS["degraded"]) == pytest.approx(1.5714, abs=1e-4)
    # 0.5 + 0.2 * 20
    assert delivery_time(PRESETS["intermittent"]) == pytest.approx(4.5)
    assert math.isinf(delivery_time(PRESETS["denied"]))


def test_limited_bandwidth_punishes_raw_data():
    limited = PRESETS["limited"]
    track = delivery_time(limited, 2_000)
    clip = delivery_time(limited, 2_000_000)
    assert track == pytest.approx(0.708, abs=1e-3)
    assert clip == pytest.approx(208.8, abs=0.1)


def test_degrade_budget_turns_margin_negative():
    stages = {"track": 5, "identify": 10, "decide": 20, "effect": 5, "comms": 0}
    base = LatencyBudget(2000, kmh_to_ms(150), stages)
    assert degrade_budget(base, "comms", PRESETS["connected"], hops=3).margin_s == pytest.approx(6.5, abs=0.05)
    assert degrade_budget(base, "comms", PRESETS["intermittent"], hops=3).margin_s < 0
    assert not degrade_budget(base, "comms", PRESETS["denied"], hops=1).closes


CENTRAL = Architecture("centralised", local_s=5, hops=3, queue_s=15, decide_s=20, act_s=5, message_bits=2_000)
EDGE = Architecture("distributed", local_s=5, hops=0, decide_s=20, act_s=5)


def test_centralised_versus_distributed_connected():
    central, edge = compare([CENTRAL, EDGE], PRESETS["connected"], available_s=48)
    assert central.loop_s == pytest.approx(48.0)
    assert central.margin_s == pytest.approx(0.0)
    assert edge.loop_s == pytest.approx(30.0)
    assert edge.margin_s == pytest.approx(18.0)
    assert central.availability == 1.0


def test_intermittent_links_cut_central_availability():
    central = evaluate(CENTRAL, PRESETS["intermittent"])
    assert central.availability == pytest.approx(0.8**6)
    assert evaluate(EDGE, PRESETS["intermittent"]).availability == 1.0
    assert math.isinf(evaluate(CENTRAL, PRESETS["denied"]).loop_s)


def test_divergence_probability():
    assert divergence_probability(6, 0.10) == pytest.approx(0.469, abs=1e-3)
    assert divergence_probability(1, 0.0) == 0.0


def test_link_validation():
    with pytest.raises(ValueError):
        Link(loss=1.0)
    with pytest.raises(ValueError):
        Link(up_fraction=1.5)


def test_cli_commands(capsys, tmp_path):
    assert main(["margin", "--range-m", "2000", "--speed-kmh", "150",
                 "--stage", "track=5", "identify=10", "decide=20", "effect=5"]) == 0
    assert "+8.0 s" in capsys.readouterr().out
    assert main(["raid", "--threats", "10", "--p", "0.8", "--target", "0.9"]) == 0
    out = capsys.readouterr().out
    assert "0.107" in out and "0.665" in out and "0.923" in out and "0.9: 3" in out
    assert main(["layers", "--threats", "10", "--layer", "outer:0.5:1", "inner:0.8:2"]) == 0
    assert "0.817" in capsys.readouterr().out
    assert main(["raid-curve", "--p", "0.8", "--out", str(tmp_path / "raid")]) == 0
    lines = (tmp_path / "raid.csv").read_text().splitlines()
    assert lines[0] == "threats,pra_1_shots,pra_2_shots,pra_3_shots"
    assert lines[10].startswith("10,0.1074,0.6648,0.9228")
    assert main(["ddil"]) == 0
    assert "never" in capsys.readouterr().out
    assert main(["compare"]) == 0
    assert "distributed" in capsys.readouterr().out
    assert main(["margin", "--range-m", "2000", "--speed-kmh", "150", "--stage", "track=5",
                 "--ddil", "degraded", "--comms-stage", "missing"]) == 2
