"""Command line interface: python -m c2latency <command> ..."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Sequence

from .architecture import Architecture, compare, divergence_probability
from .budget import LatencyBudget, kmh_to_ms
from .ddil import PRESETS, Link, degrade_budget, delivery_time
from .raid import Layer, expected_leakers, layered_raid, magazine, p_raid_annihilation, shots_needed


def _stages(items: Sequence[str]) -> dict:
    stages = {}
    for item in items:
        name, _, value = item.partition("=")
        if not value:
            raise argparse.ArgumentTypeError(f"stage must look like name=seconds, got {item!r}")
        stages[name] = float(value)
    return stages


def _speed(args: argparse.Namespace) -> float:
    if args.speed_ms is not None:
        return args.speed_ms
    return kmh_to_ms(args.speed_kmh)


def cmd_margin(args: argparse.Namespace) -> None:
    budget = LatencyBudget(args.range_m, _speed(args), _stages(args.stage), args.min_range_m)
    print(budget.as_text())
    if args.ddil:
        link = PRESETS[args.ddil]
        if args.comms_stage not in budget.stages:
            raise ValueError(f"--comms-stage {args.comms_stage!r} is not one of the stages")
        degraded = degrade_budget(budget, args.comms_stage, link, args.hops, args.message_bits)
        print(f"\nunder '{args.ddil}' ({args.hops} hop(s), {args.message_bits:,.0f} bit message):")
        print(degraded.as_text())


def cmd_raid(args: argparse.Namespace) -> None:
    print(f"raid of {args.threats}, single-shot p = {args.p}")
    print(f"{'shots':>5} {'P(no leaker)':>13} {'E[leakers]':>11} {'rounds':>7}")
    for n in args.shots:
        print(f"{n:>5} {p_raid_annihilation(args.threats, args.p, n):>13.3f} "
              f"{expected_leakers(args.threats, args.p, n):>11.2f} {magazine(args.threats, n):>7}")
    if args.target:
        print(f"shots per threat for P(no leaker) >= {args.target}: {shots_needed(args.threats, args.p, args.target)}")


def cmd_layers(args: argparse.Namespace) -> None:
    layers = []
    for spec in args.layer:
        try:
            name, p, shots = spec.split(":")
            layers.append(Layer(name, float(p), int(shots)))
        except ValueError:
            raise ValueError(f"layer must look like name:p:shots, got {spec!r}") from None
    print(layered_raid(args.threats, layers).as_text())


def cmd_raid_curve(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sizes = list(range(1, args.max_threats + 1))
    path = out.with_suffix(".csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["threats"] + [f"pra_{n}_shots" for n in args.shots])
        for size in sizes:
            writer.writerow([size] + [f"{p_raid_annihilation(size, args.p, n):.4f}" for n in args.shots])
    print(f"wrote {path}")


def cmd_ddil(args: argparse.Namespace) -> None:
    print(f"{'condition':<13} {'track msg':>10} {'video clip':>11}")
    for name, link in PRESETS.items():
        track = delivery_time(link, args.track_bits)
        clip = delivery_time(link, args.clip_bits)
        fmt = lambda v: "never" if v == float("inf") else f"{v:.1f} s"  # noqa: E731
        print(f"{name:<13} {fmt(track):>10} {fmt(clip):>11}")


def cmd_compare(args: argparse.Namespace) -> None:
    central = Architecture("centralised", local_s=5, hops=args.hops, queue_s=args.queue_s,
                           decide_s=args.decide_s, act_s=5, message_bits=args.message_bits)
    edge = Architecture("distributed", local_s=5, hops=0, decide_s=args.decide_s, act_s=5)
    for name in ("connected", "degraded", "intermittent", "limited", "denied"):
        print(f"[{name}]")
        for row in compare([central, edge], PRESETS[name], args.available_s):
            print("  " + row.as_row())
    print(f"\nconsistency cost: with {args.nodes} edge deciders and a 10% partition chance each, "
          f"P(some picture diverges) = {divergence_probability(args.nodes, 0.10):.0%}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="c2latency", description="Decision latency and layered defence arithmetic.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("margin", help="decision margin for a detect-to-effect chain")
    p.add_argument("--range-m", type=float, required=True, help="first reliable detection range, m")
    speed = p.add_mutually_exclusive_group(required=True)
    speed.add_argument("--speed-kmh", type=float)
    speed.add_argument("--speed-ms", type=float)
    p.add_argument("--min-range-m", type=float, default=0.0)
    p.add_argument("--stage", nargs="+", required=True, metavar="NAME=SECONDS")
    p.add_argument("--ddil", choices=sorted(PRESETS), help="re-run with the comms stage under this condition")
    p.add_argument("--comms-stage", default="comms")
    p.add_argument("--hops", type=int, default=1)
    p.add_argument("--message-bits", type=float, default=2_000)
    p.set_defaults(func=cmd_margin)

    p = sub.add_parser("raid", help="probability no threat leaks, expected leakers, rounds")
    p.add_argument("--threats", type=int, required=True)
    p.add_argument("--p", type=float, required=True, help="single-shot defeat probability")
    p.add_argument("--shots", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--target", type=float, help="report shots needed for this P(no leaker)")
    p.set_defaults(func=cmd_raid)

    p = sub.add_parser("layers", help="raid through several layers")
    p.add_argument("--threats", type=int, required=True)
    p.add_argument("--layer", nargs="+", required=True, metavar="NAME:P:SHOTS")
    p.set_defaults(func=cmd_layers)

    p = sub.add_parser("raid-curve", help="write P(no leaker) against raid size as CSV")
    p.add_argument("--p", type=float, required=True)
    p.add_argument("--max-threats", type=int, default=20)
    p.add_argument("--shots", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--out", default="out/raid")
    p.set_defaults(func=cmd_raid_curve)

    p = sub.add_parser("ddil", help="message delivery time under DDIL presets")
    p.add_argument("--track-bits", type=float, default=2_000)
    p.add_argument("--clip-bits", type=float, default=2_000_000)
    p.set_defaults(func=cmd_ddil)

    p = sub.add_parser("compare", help="centralised versus distributed decision loop")
    p.add_argument("--hops", type=int, default=3)
    p.add_argument("--queue-s", type=float, default=15.0)
    p.add_argument("--decide-s", type=float, default=20.0)
    p.add_argument("--message-bits", type=float, default=2_000)
    p.add_argument("--available-s", type=float, default=48.0)
    p.add_argument("--nodes", type=int, default=6)
    p.set_defaults(func=cmd_compare)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (ValueError, KeyError, OSError, argparse.ArgumentTypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
