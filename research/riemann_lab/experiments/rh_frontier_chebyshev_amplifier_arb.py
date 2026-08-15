#!/usr/bin/env python3
"""Arb-certified finite block and parametric tail budget for the amplifier.

Arb's ``acb.zeta_zeros`` isolates consecutive zeta zeros with ball
arithmetic. The infinite tail is deliberately kept symbolic in the local
zero-count intercept A; the script reports how large A may be before the
certified negative margin is lost.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from flint import acb, arb, ctx


def q_of(rho: acb) -> acb:
    return 1 - 1 / rho


def amplifier_product(rho: acb, a: arb, damping: int, mode: int) -> acb:
    q = q_of(rho)
    u = q + 1 / q
    oscillation = (1 + q ** (2 * mode)) * (1 + 1 / q ** (2 * mode))
    return (u - a) ** 2 * (2 - u) ** (2 * damping) * oscillation


def quartet_contribution(rho: acb, a: arb, damping: int, mode: int) -> arb:
    return 4 * amplifier_product(rho, a, damping, mode).real


def critical_pair_contribution(
    rho: acb, a: arb, damping: int, mode: int
) -> arb:
    return 2 * amplifier_product(rho, a, damping, mode).real


def interval(value: arb) -> dict:
    return {
        "lower": str(value.lower()),
        "upper": str(value.upper()),
        "midpoint": str(value.mid()),
        "radius": str(value.rad()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zero-count", type=int, default=30)
    parser.add_argument("--digits", type=int, default=120)
    parser.add_argument("--damping", type=int, default=10)
    parser.add_argument("--mode", type=int, default=33)
    parser.add_argument("--betas", nargs="+", default=["0.5001", "0.51", "0.55"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.zero_count < 1 or args.digits < 50:
        raise SystemExit("zero count must be positive and digits at least 50")

    ctx.dps = args.digits
    zeros = acb.zeta_zeros(1, args.zero_count)
    gamma = zeros[0].imag
    tail_start = zeros[-1].imag.lower().floor()
    p = 4 * args.damping
    if p <= 1 or tail_start <= 1:
        raise SystemExit("tail majorant requires p > 1 and tail start > 1")

    # The checked local zero-count theorem has slope B=12/log(8/7).
    # If a unit window contains at most A+B log(t) zeros, the integral test
    # bounds the critical-line tail by coef_A*A + fixed_slope_tail.
    log_eight_sevenths = (arb(8) / 7).log()
    slope = 12 / log_eight_sevenths
    x = arb(tail_start)
    coef_a = 128 * x ** (1 - p) / (p - 1)
    coef_b = 128 * x ** (1 - p) * (
        x.log() / (p - 1) + arb(1) / (p - 1) ** 2
    )
    fixed_slope_tail = coef_b * slope

    cases = []
    for beta_text in args.betas:
        target = acb(arb(beta_text), gamma)
        a = (q_of(target) + 1 / q_of(target)).real
        target_value = quartet_contribution(target, a, args.damping, args.mode)
        background = sum(
            (critical_pair_contribution(zero, a, args.damping, args.mode)
             for zero in zeros),
            arb(0),
        )
        net = target_value + background
        negative_margin = -net
        intercept_budget = (negative_margin - fixed_slope_tail) / coef_a
        log_constant_budget = intercept_budget * log_eight_sevenths
        cases.append(
            {
                "beta": beta_text,
                "target_a": interval(a),
                "target_quartet": interval(target_value),
                "certified_target_negative": bool(target_value < 0),
                "certified_first_zero_block": interval(background),
                "certified_block_nonnegative": bool(background >= 0),
                "certified_finite_net": interval(net),
                "certified_finite_net_negative": bool(net < 0),
                "tail_intercept_budget_A": interval(intercept_budget),
                "equivalent_log_jensen_constant_budget": interval(log_constant_budget),
                "budget_positive": bool(intercept_budget > 0),
            }
        )

    payload = {
        "experiment": "arb_certified_chebyshev_damped_quartet_amplifier",
        "backend": "python-flint 0.9.0 / Arb ball arithmetic",
        "digits": args.digits,
        "consecutive_zeta_zeros_enclosed": args.zero_count,
        "last_zero_ordinate": interval(zeros[-1].imag),
        "damping": args.damping,
        "mode": args.mode,
        "polynomial_degree": 2 + 2 * args.damping + 2 * args.mode,
        "tail_power": p,
        "tail_unit_window_model": "count([t,t+1]) <= A + (12/log(8/7))*log(t)",
        "tail_start_floor": int(str(tail_start).split(".", maxsplit=1)[0]),
        "tail_coefficient_of_A": interval(coef_a),
        "tail_fixed_log_slope_part": interval(fixed_slope_tail),
        "cases": cases,
        "claim_boundary": (
            "The first finite zero block and its signs are rigorous Arb enclosures. "
            "The infinite tail is a parametric budget, not yet a closed certificate: "
            "the Lean Jensen intercept must be given an explicit upper bound, and a "
            "general RH argument must handle an arbitrary collection of off-line zeros."
        ),
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
