"""c2latency: decision-cycle latency budgets, decision margin, layered-defence
raid arithmetic, DDIL degradation and centralised versus distributed control.
Pure standard library."""

from .architecture import Architecture, ArchitectureResult, compare, divergence_probability, evaluate
from .budget import LatencyBudget, decision_margin, kmh_to_ms, knots_to_ms, time_to_impact
from .ddil import CONNECTED, PRESETS, Link, degrade_budget, delivery_time
from .raid import (
    Layer,
    RaidResult,
    common_mode_pra,
    expected_leakers,
    layered_raid,
    leak_probability,
    leaker_distribution,
    magazine,
    p_any_leak,
    p_raid_annihilation,
    shots_needed,
)

__version__ = "0.1.0"

__all__ = [
    "Architecture", "ArchitectureResult", "CONNECTED", "LatencyBudget", "Layer", "Link", "PRESETS",
    "RaidResult", "common_mode_pra", "compare", "decision_margin", "degrade_budget", "delivery_time",
    "divergence_probability", "evaluate", "expected_leakers", "kmh_to_ms", "knots_to_ms",
    "layered_raid", "leak_probability", "leaker_distribution", "magazine", "p_any_leak",
    "p_raid_annihilation", "shots_needed", "time_to_impact",
]
