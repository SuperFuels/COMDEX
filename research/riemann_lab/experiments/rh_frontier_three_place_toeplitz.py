#!/usr/bin/env python3
"""Certified Fejer-symbol probe for the completed Li increment kernel.

For lambda_0 = 0, the mixed difference of the Li distance kernel has Toeplitz
lags

    tau_0 = lambda_1,
    tau_k = (lambda_{k-1} - 2 lambda_k + lambda_{k+1}) / 2.

The order-N Fejer symbol is

    F_N(theta) = tau_0 + 2 sum_{k=1}^N (1-k/(N+1)) tau_k cos(k theta).

It is evaluated with Arb balls on a uniform grid.  A rigorous derivative
majorant closes every gap between grid points, so a positive reported global
lower bound certifies the whole interval theta in [0, pi], not just samples.
This remains a finite necessary-condition experiment, not a proof of RH.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from flint import arb, ctx

from rh_frontier_li_place_decomposition import component_li_coefficients


def interval_record(value: arb) -> dict[str, str]:
    return {"lower": str(value.lower()), "upper": str(value.upper())}


def increment_lags(li: list[arb], order: int) -> list[arb]:
    return [li[1]] + [
        (li[k - 1] - 2 * li[k] + li[k + 1]) / 2
        for k in range(1, order + 1)
    ]


def certify_fejer_symbol(lags: list[arb], order: int, grid: int) -> dict:
    pi = arb.const_sqrt_pi() ** 2
    weighted = [lags[0]] + [
        arb(order + 1 - k) * lags[k] / (order + 1)
        for k in range(1, order + 1)
    ]
    derivative_bound = sum(
        (2 * k * abs(weighted[k]) for k in range(1, order + 1)),
        arb(0),
    )

    minimum = None
    minimum_index = None
    for index in range(grid + 1):
        theta = pi * index / grid
        value = weighted[0] + sum(
            (2 * weighted[k] * (k * theta).cos()
             for k in range(1, order + 1)),
            arb(0),
        )
        if minimum is None or value.lower() < minimum.lower():
            minimum = value
            minimum_index = index

    assert minimum is not None and minimum_index is not None
    covering_radius = pi / (2 * grid)
    certified_global_lower = minimum.lower() - (
        derivative_bound.upper() * covering_radius.upper()
    )
    return {
        "minimum_grid_index": minimum_index,
        "minimum_grid_angle_over_pi": f"{minimum_index}/{grid}",
        "minimum_grid_value": interval_record(minimum),
        "derivative_majorant": interval_record(derivative_bound),
        "covering_radius": interval_record(covering_radius),
        "certified_global_lower": str(certified_global_lower),
        "certified_positive_on_closed_interval": bool(certified_global_lower > 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", type=int, default=30)
    parser.add_argument("--digits", type=int, default=150)
    parser.add_argument("--grid", type=int, default=131072)
    parser.add_argument(
        "--component",
        action="append",
        choices=(
            "elementary_pole_pi",
            "archimedean_gamma",
            "regularized_finite_place",
            "complete",
        ),
        help="component to certify; repeat as needed (default: all)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.order < 1 or args.digits < 50 or args.grid < 1024:
        raise SystemExit("invalid order, precision, or grid")

    ctx.dps = args.digits
    components = component_li_coefficients(args.order + 1, args.digits)
    selected = args.component or list(components)
    reports = {
        name: certify_fejer_symbol(
            increment_lags(components[name], args.order), args.order, args.grid
        )
        for name in selected
    }
    payload = {
        "experiment": "certified_completed_li_increment_fejer_symbol",
        "backend": "python-flint/Arb ball arithmetic",
        "order": args.order,
        "digits": args.digits,
        "grid_subintervals_on_zero_pi": args.grid,
        "formula": (
            "F_N(theta)=tau_0+2*sum_{k=1}^N"
            "(1-k/(N+1))*tau_k*cos(k*theta)"
        ),
        "claim_boundary": (
            "A positive complete result certifies one finite Fejer polynomial "
            "on a continuum. It does not establish the infinite family, a "
            "positive representing measure, or RH."
        ),
        "components": reports,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
