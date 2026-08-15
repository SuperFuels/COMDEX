#!/usr/bin/env python3
"""Finite spectral-amplifier search for the Pascal--Toeplitz RH programme.

For a target quartet with u=q+q^{-1}=a+ib, use the real polynomial

  C(z) = (z^2-a*z+1) * (1-z)^(2r) * (1+z^(2M)).

The first factor is the exact sparse off-line witness.  The middle factor
damps high critical zeros because 2-u is O(gamma^-2).  The final sparse factor
is the cleared Laurent form of a Chebyshev localizer.

This script sums only a finite list of critical-line zeros returned by mpmath.
It is a conjecture-mining experiment, not a certified full-divisor bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mpmath as mp


def q_of(rho: mp.mpc) -> mp.mpc:
    return 1 - 1 / rho


def u_of(rho: mp.mpc) -> mp.mpc:
    q = q_of(rho)
    return q + 1 / q


def amplifier_product(rho: mp.mpc, a: mp.mpf, damping: int, mode: int) -> mp.mpc:
    q = q_of(rho)
    u = q + 1 / q
    return (
        (u - a) ** 2
        * (2 - u) ** (2 * damping)
        * (1 + q ** (2 * mode))
        * (1 + q ** (-2 * mode))
    )


def quartet_contribution(rho: mp.mpc, a: mp.mpf, damping: int, mode: int) -> mp.mpf:
    return 4 * mp.re(amplifier_product(rho, a, damping, mode))


def critical_pair_contribution(
    rho: mp.mpc, a: mp.mpf, damping: int, mode: int
) -> mp.mpf:
    return 2 * mp.re(amplifier_product(rho, a, damping, mode))


def finite_search(
    beta_text: str,
    gamma: mp.mpf,
    critical_zeros: list[mp.mpc],
    max_damping: int,
    max_mode: int,
) -> dict:
    target = mp.mpc(mp.mpf(beta_text), gamma)
    a = mp.re(u_of(target))
    rows = []
    for damping in range(1, max_damping + 1):
        for mode in range(1, max_mode + 1):
            target_value = quartet_contribution(target, a, damping, mode)
            background = mp.fsum(
                critical_pair_contribution(zero, a, damping, mode)
                for zero in critical_zeros
            )
            net = target_value + background
            if target_value < 0 and background > 0:
                rows.append(
                    {
                        "damping": damping,
                        "mode": mode,
                        "polynomial_degree": 2 + 2 * damping + 2 * mode,
                        "target_quartet": mp.nstr(target_value, 40),
                        "finite_critical_background": mp.nstr(background, 40),
                        "finite_net": mp.nstr(net, 40),
                        "target_to_background_ratio": mp.nstr(
                            -target_value / background, 30
                        ),
                        "finite_net_negative": bool(net < 0),
                    }
                )
    rows.sort(key=lambda row: mp.mpf(row["target_to_background_ratio"]), reverse=True)
    best = rows[:10]
    return {
        "beta": beta_text,
        "gamma": mp.nstr(gamma, 50),
        "target_a": mp.nstr(a, 50),
        "best_candidates": best,
        "any_finite_net_negative": any(row["finite_net_negative"] for row in rows),
    }


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zero-count", type=int, default=30)
    parser.add_argument("--max-damping", type=int, default=10)
    parser.add_argument("--max-mode", type=int, default=100)
    parser.add_argument("--digits", type=int, default=80)
    parser.add_argument("--betas", nargs="+", default=["0.5001", "0.51", "0.55"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.zero_count < 1 or args.max_damping < 1 or args.max_mode < 1:
        raise SystemExit("search bounds must be positive")
    if args.digits < 50:
        raise SystemExit("digits must be at least 50")

    mp.mp.dps = args.digits
    zeros = [mp.zetazero(index) for index in range(1, args.zero_count + 1)]
    gamma = mp.im(zeros[0])
    cases = [
        finite_search(
            beta, gamma, zeros, args.max_damping, args.max_mode
        )
        for beta in args.betas
    ]
    payload = {
        "experiment": "finite_chebyshev_damped_quartet_amplifier",
        "amplifier": "(z^2-a*z+1)*(1-z)^(2r)*(1+z^(2M))",
        "critical_zeros_included": args.zero_count,
        "digits": args.digits,
        "max_damping": args.max_damping,
        "max_mode": args.max_mode,
        "cases": cases,
        "claim_boundary": (
            "Finite high-precision experiment only. The omitted infinite zero tail is not "
            "bounded here, and the test assumes the included background zeros lie on the "
            "critical line. It neither proves nor disproves RH."
        ),
        "next_proof_obligation": (
            "Give an explicit tail bound using zero counting, then transfer the same "
            "amplifier through the prime/Gamma/pole explicit formula."
        ),
    }
    payload["payload_sha256"] = canonical_hash(payload)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
