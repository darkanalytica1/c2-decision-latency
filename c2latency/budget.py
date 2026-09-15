"""Decision-cycle latency budgets and decision margin.

    T_impact = (R_detect - R_min) / v_threat
    M        = T_impact - sum(T_i)

A negative margin means the defence cannot act in time, however good any
single sensor or effector is.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

__all__ = [
    "kmh_to_ms",
    "knots_to_ms",
    "time_to_impact",
    "decision_margin",
    "LatencyBudget",
]


def kmh_to_ms(speed_kmh: float) -> float:
    return speed_kmh / 3.6


def knots_to_ms(speed_kt: float) -> float:
    return speed_kt * 1852.0 / 3600.0


def time_to_impact(detect_range_m: float, closing_speed_m_s: float, min_range_m: float = 0.0) -> float:
    """Seconds between first reliable detection and the threat reaching the
    minimum range at which an effect is still useful.

    >>> round(time_to_impact(2000, kmh_to_ms(150)), 1)
    48.0
    """
    if closing_speed_m_s <= 0:
        raise ValueError("closing speed must be positive")
    if detect_range_m < 0 or min_range_m < 0:
        raise ValueError("ranges must be non-negative")
    return max(0.0, detect_range_m - min_range_m) / closing_speed_m_s


def decision_margin(t_impact_s: float, stage_latencies_s) -> float:
    """M = T_impact - sum(T_i)."""
    values = list(stage_latencies_s.values()) if isinstance(stage_latencies_s, Mapping) else list(stage_latencies_s)
    if any(v < 0 for v in values):
        raise ValueError("stage latencies must be non-negative")
    return t_impact_s - sum(values)


@dataclass(frozen=True)
class LatencyBudget:
    """A detect-to-effect chain against one threat geometry.

    ``stages`` is an ordered mapping of stage name to seconds, for example
    ``{"track": 5, "identify": 10, "decide": 20, "effect": 5}``. Include every
    communications hop, either as its own stage or inside the stages it delays.
    """

    detect_range_m: float
    closing_speed_m_s: float
    stages: Mapping[str, float] = field(default_factory=dict)
    min_range_m: float = 0.0

    def __post_init__(self) -> None:
        if any(v < 0 for v in self.stages.values()):
            raise ValueError("stage latencies must be non-negative")
        time_to_impact(self.detect_range_m, self.closing_speed_m_s, self.min_range_m)  # validates

    @property
    def available_s(self) -> float:
        return time_to_impact(self.detect_range_m, self.closing_speed_m_s, self.min_range_m)

    @property
    def chain_s(self) -> float:
        return float(sum(self.stages.values()))

    @property
    def margin_s(self) -> float:
        return self.available_s - self.chain_s

    @property
    def closes(self) -> bool:
        """True if the loop completes before the threat reaches minimum range."""
        return self.margin_s >= 0

    @property
    def binding_stage(self) -> str | None:
        """The largest single stage: where a second saved is easiest to find."""
        if not self.stages:
            return None
        return max(self.stages, key=self.stages.get)

    def share(self, stage: str) -> float:
        return self.stages[stage] / self.chain_s if self.chain_s else 0.0

    @property
    def required_detect_range_m(self) -> float:
        """Detection range at which the same chain has exactly zero margin."""
        return self.min_range_m + self.closing_speed_m_s * self.chain_s

    @property
    def max_closing_speed_m_s(self) -> float:
        """Fastest threat the chain can still beat at this detection range."""
        if self.chain_s == 0:
            return float("inf")
        return max(0.0, self.detect_range_m - self.min_range_m) / self.chain_s

    def with_stage(self, name: str, seconds: float) -> "LatencyBudget":
        stages = dict(self.stages)
        stages[name] = seconds
        return replace(self, stages=stages)

    def with_speed(self, closing_speed_m_s: float) -> "LatencyBudget":
        return replace(self, closing_speed_m_s=closing_speed_m_s)

    def as_text(self, width: int = 40) -> str:
        avail = self.available_s
        scale = width / max(avail, self.chain_s, 1e-9)
        lines = [
            f"time to impact   {avail:6.1f} s  (detect {self.detect_range_m:,.0f} m, "
            f"min range {self.min_range_m:,.0f} m, {self.closing_speed_m_s:.1f} m/s)",
        ]
        for name, secs in self.stages.items():
            bar = "#" * max(1, round(secs * scale)) if secs else ""
            lines.append(f"  {name:<14} {secs:6.1f} s  {bar}")
        lines.append(f"chain total      {self.chain_s:6.1f} s")
        verdict = "closes in time" if self.closes else "DOES NOT CLOSE"
        lines.append(f"decision margin  {self.margin_s:+6.1f} s  ({verdict})")
        if self.binding_stage:
            lines.append(f"binding stage    {self.binding_stage} ({self.share(self.binding_stage):.0%} of chain)")
        lines.append(f"zero-margin detection range {self.required_detect_range_m:,.0f} m; "
                     f"fastest beatable threat {self.max_closing_speed_m_s:.1f} m/s")
        return "\n".join(lines)
