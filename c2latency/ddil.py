"""DDIL: denied, degraded, intermittent, limited.

A first-order model by the author of how each condition inflates the time to
deliver one message across one link. It is meant to show which condition
breaks which assumption, not to model a specific radio or network.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

__all__ = ["Link", "delivery_time", "CONNECTED", "PRESETS", "degrade_budget"]


@dataclass(frozen=True)
class Link:
    """One hop.

    base_latency_s  propagation plus processing per attempt
    loss            probability an attempt is lost (degraded)
    retry_timeout_s wait before a lost attempt is retried
    up_fraction     long-run share of time the link is up (intermittent; 0 = denied)
    mean_outage_s   mean outage duration when down (exponential outages)
    bandwidth_bps   link rate (limited); None means not the constraint
    """

    name: str = "link"
    base_latency_s: float = 0.2
    loss: float = 0.0
    retry_timeout_s: float = 0.0
    up_fraction: float = 1.0
    mean_outage_s: float = 0.0
    bandwidth_bps: float | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.loss < 1:
            raise ValueError("loss must lie in [0, 1)")
        if not 0 <= self.up_fraction <= 1:
            raise ValueError("up_fraction must lie in [0, 1]")
        if min(self.base_latency_s, self.retry_timeout_s, self.mean_outage_s) < 0:
            raise ValueError("times must be non-negative")
        if self.bandwidth_bps is not None and self.bandwidth_bps <= 0:
            raise ValueError("bandwidth must be positive")

    @property
    def denied(self) -> bool:
        return self.up_fraction == 0


def delivery_time(link: Link, message_bits: float = 0.0) -> float:
    """Expected seconds to deliver one message over one hop.

    attempt   = base latency + message_bits / bandwidth
    retries   : attempts are geometric, so E = attempt/(1 - loss) + timeout * loss/(1 - loss)
    outages   : a message arriving while the link is down waits the residual
                outage, mean_outage_s for exponential outages, so add
                (1 - up_fraction) * mean_outage_s (store and forward)
    denied    : infinite; the loop cannot close through this link
    """
    if message_bits < 0:
        raise ValueError("message_bits must be non-negative")
    if link.denied:
        return math.inf
    serialise = message_bits / link.bandwidth_bps if link.bandwidth_bps else 0.0
    attempt = link.base_latency_s + serialise
    with_retries = attempt / (1.0 - link.loss) + link.retry_timeout_s * link.loss / (1.0 - link.loss)
    waiting = (1.0 - link.up_fraction) * link.mean_outage_s
    return with_retries + waiting


CONNECTED = Link("connected", base_latency_s=0.5)

PRESETS = {
    "connected": CONNECTED,
    "degraded": Link("degraded", base_latency_s=0.5, loss=0.3, retry_timeout_s=2.0),
    "intermittent": Link("intermittent", base_latency_s=0.5, up_fraction=0.8, mean_outage_s=20.0),
    "limited": Link("limited", base_latency_s=0.5, bandwidth_bps=9_600),
    "denied": Link("denied", up_fraction=0.0),
}


def degrade_budget(budget, comms_stage: str, link: Link, hops: int = 1, message_bits: float = 0.0):
    """Return a copy of a :class:`~c2latency.budget.LatencyBudget` whose
    ``comms_stage`` is replaced by ``hops`` deliveries over ``link``."""
    if hops < 0:
        raise ValueError("hops must be non-negative")
    stages = dict(budget.stages)
    stages[comms_stage] = hops * delivery_time(link, message_bits) if hops else 0.0
    return replace(budget, stages=stages)
