"""Raid arithmetic for layered defence: probability that no threat leaks
through, expected leakers, and magazine use.

Standard independent-trial probability. Independence flatters the defence:
correlated failures (the same library gap, the same blind sector) make every
number here worse, which :func:`common_mode_pra` illustrates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "leak_probability",
    "p_raid_annihilation",
    "p_any_leak",
    "expected_leakers",
    "magazine",
    "leaker_distribution",
    "shots_needed",
    "Layer",
    "RaidResult",
    "layered_raid",
    "common_mode_pra",
]


def _check(n_threats: int, p_kill: float, shots: int) -> None:
    if n_threats < 0:
        raise ValueError("number of threats must be non-negative")
    if not 0 <= p_kill <= 1:
        raise ValueError("p_kill must lie in [0, 1]")
    if shots < 0:
        raise ValueError("shots must be non-negative")


def leak_probability(p_kill: float, shots: int = 1) -> float:
    """Probability one threat survives ``shots`` independent shots: (1 - p)^n."""
    _check(1, p_kill, shots)
    return (1.0 - p_kill) ** shots


def p_raid_annihilation(n_threats: int, p_kill: float, shots: int = 1) -> float:
    """P_RA = [1 - (1 - p)^n]^N: every threat in the raid is defeated.

    >>> round(p_raid_annihilation(10, 0.8, 1), 3)
    0.107
    """
    _check(n_threats, p_kill, shots)
    return (1.0 - leak_probability(p_kill, shots)) ** n_threats


def p_any_leak(n_threats: int, p_kill: float, shots: int = 1) -> float:
    return 1.0 - p_raid_annihilation(n_threats, p_kill, shots)


def expected_leakers(n_threats: int, p_kill: float, shots: int = 1) -> float:
    """E[L] = N (1 - p)^n."""
    _check(n_threats, p_kill, shots)
    return n_threats * leak_probability(p_kill, shots)


def magazine(n_threats: int, shots: int = 1) -> int:
    """Rounds used under shoot-shoot doctrine before reload: M = n N."""
    if n_threats < 0 or shots < 0:
        raise ValueError("inputs must be non-negative")
    return n_threats * shots


def leaker_distribution(n_threats: int, p_kill: float, shots: int = 1) -> list[float]:
    """P(L = k) for k = 0..N, binomial with per-threat leak probability."""
    q = leak_probability(p_kill, shots)
    return [math.comb(n_threats, k) * q**k * (1 - q) ** (n_threats - k) for k in range(n_threats + 1)]


def shots_needed(n_threats: int, p_kill: float, target_pra: float, max_shots: int = 50) -> int:
    """Smallest shots per threat reaching ``target_pra``."""
    if not 0 < target_pra < 1:
        raise ValueError("target_pra must lie in (0, 1)")
    if not 0 < p_kill <= 1:
        raise ValueError("p_kill must lie in (0, 1]")
    for n in range(1, max_shots + 1):
        if p_raid_annihilation(n_threats, p_kill, n) >= target_pra:
            return n
    raise ValueError(f"target P_RA not reachable within {max_shots} shots per threat")


@dataclass(frozen=True)
class Layer:
    """One defensive layer: single-shot defeat probability and shots it fires
    at each threat that reaches it."""

    name: str
    p_kill: float
    shots: int = 1

    def __post_init__(self) -> None:
        _check(1, self.p_kill, self.shots)


@dataclass(frozen=True)
class RaidResult:
    n_threats: int
    leak_per_threat: float
    pra: float
    expected_leakers: float
    expected_rounds: dict

    def as_text(self) -> str:
        lines = [
            f"threats                    {self.n_threats}",
            f"leak probability / threat  {self.leak_per_threat:.4f}",
            f"P(no leaker)               {self.pra:.3f}",
            f"P(at least one leaker)     {1 - self.pra:.3f}",
            f"expected leakers           {self.expected_leakers:.2f}",
        ]
        for name, rounds in self.expected_rounds.items():
            lines.append(f"expected rounds, {name:<10}{rounds:6.1f}")
        return "\n".join(lines)


def layered_raid(n_threats: int, layers: Sequence[Layer]) -> RaidResult:
    """Threats pass layers in order; each layer fires all its shots at every
    threat that reached it (shoot-shoot within a layer, look between layers).
    Layers are assumed independent."""
    survive = 1.0
    rounds = {}
    for layer in layers:
        rounds[layer.name] = n_threats * survive * layer.shots
        survive *= leak_probability(layer.p_kill, layer.shots)
    return RaidResult(
        n_threats=n_threats,
        leak_per_threat=survive,
        pra=(1.0 - survive) ** n_threats,
        expected_leakers=n_threats * survive,
        expected_rounds=rounds,
    )


def common_mode_pra(n_threats: int, p_kill: float, shots: int, p_common_mode: float) -> float:
    """Illustrative correlated-failure model (author's): with probability
    ``p_common_mode`` the raid exploits a shared gap that no shot covers, so at
    least one threat leaks; otherwise shots are independent."""
    if not 0 <= p_common_mode <= 1:
        raise ValueError("p_common_mode must lie in [0, 1]")
    return (1.0 - p_common_mode) * p_raid_annihilation(n_threats, p_kill, shots)
