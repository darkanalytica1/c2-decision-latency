"""Centralised versus distributed control: loop time, loop availability and
the consistency cost of deciding at the edge.

A first-order comparison model by the author. Centralisation buys one
authoritative picture and coherent decisions; distribution buys speed and
survivability. The model makes both sides of that trade visible in numbers
under stated assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ddil import Link, delivery_time

__all__ = ["Architecture", "ArchitectureResult", "evaluate", "compare", "divergence_probability"]


@dataclass(frozen=True)
class Architecture:
    """Where the decision sits.

    local_s        sensing, tracking and identification at the edge
    hops           network hops from the edge to the decision point (0 = decide locally)
    queue_s        waiting for attention at the decision point (shared operators)
    decide_s       the decision itself, including authority
    act_s          effector response
    message_bits   size of what is sent up (a track, a clip, a video feed)
    """

    name: str
    local_s: float
    hops: int
    decide_s: float
    act_s: float
    queue_s: float = 0.0
    message_bits: float = 0.0

    def __post_init__(self) -> None:
        if self.hops < 0 or min(self.local_s, self.decide_s, self.act_s, self.queue_s, self.message_bits) < 0:
            raise ValueError("inputs must be non-negative")


@dataclass(frozen=True)
class ArchitectureResult:
    name: str
    loop_s: float
    comms_s: float
    availability: float
    margin_s: float | None

    def as_row(self) -> str:
        never = self.loop_s == float("inf")
        if self.margin_s is None:
            margin = "n/a"
        else:
            margin = "loop cannot close" if never else f"{self.margin_s:+.1f} s"
        loop = "never" if never else f"{self.loop_s:.1f} s"
        comms = "   never" if never else f"{self.comms_s:6.1f} s"
        return f"{self.name:<14} loop {loop:>9}  comms {comms}  loop possible {self.availability:5.1%}  margin {margin}"


def evaluate(arch: Architecture, link: Link, available_s: float | None = None) -> ArchitectureResult:
    """Loop time = local + up and back over ``hops`` + queue + decide + act.

    Availability is the probability that every hop the loop depends on is up
    at a random instant, assuming independent hops: up_fraction ** (2 * hops).
    A loop that decides locally does not depend on the network to close.
    """
    per_hop_up = delivery_time(link, arch.message_bits) if arch.hops else 0.0
    per_hop_down = delivery_time(link, 2_000) if arch.hops else 0.0  # a short order back down
    comms = arch.hops * (per_hop_up + per_hop_down)
    loop = arch.local_s + comms + arch.queue_s + arch.decide_s + arch.act_s
    availability = link.up_fraction ** (2 * arch.hops) if arch.hops else 1.0
    margin = None if available_s is None else available_s - loop
    return ArchitectureResult(arch.name, loop, comms, availability, margin)


def compare(architectures, link: Link, available_s: float | None = None) -> list[ArchitectureResult]:
    return [evaluate(a, link, available_s) for a in architectures]


def divergence_probability(nodes: int, partition_probability: float) -> float:
    """Probability that at least one of ``nodes`` edge deciders is partitioned
    from the others at a random instant, so local pictures can diverge and
    must be reconciled later: 1 - (1 - p)^nodes. The consistency cost of
    distribution, stated as a number to design reconciliation against."""
    if nodes < 0 or not 0 <= partition_probability <= 1:
        raise ValueError("invalid inputs")
    return 1.0 - (1.0 - partition_probability) ** nodes
