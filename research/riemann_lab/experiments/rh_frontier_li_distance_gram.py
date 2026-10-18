#!/usr/bin/env python3
"""Certified distance-Gram test for the Li sequence.

For a real sequence lambda with lambda_0 = 0, form

    G[i,j] = lambda_i + lambda_j - lambda_|i-j|,  i,j >= 1.

If RH holds, the unit-circle description of every zero mode makes this a
Gram matrix.  Conversely, positivity of every such finite matrix forces
lambda_n >= 0 from its diagonal, hence recovers Li's criterion.  The script
checks finite matrices only and uses synthetic off-line quartets only as
adversarial falsification cases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from flint import acb, arb, arb_mat, ctx

from rh_frontier_li_full_arb import certified_li_coefficients


def quartet_contributions(beta: str, gamma: str, count: int) -> list[arb]:
    rho = acb(arb(beta), arb(gamma))
    ratio = 1 - 1 / rho
    values = [arb(0)]
    for n in range(1, count + 1):
        # The orbit ratios are w, conjugate(w), 1/w, 1/conjugate(w).
        values.append(arb(4) - 2 * (ratio**n + ratio ** (-n)).real)
    return values


def leading_minors(sequence: list[arb], max_order: int, stop_on_failure: bool) -> dict:
    rows = []
    first_negative = None
    first_unresolved = None
    for order in range(1, max_order + 1):
        matrix = arb_mat(
            [
                [sequence[i] + sequence[j] - sequence[abs(i - j)]
                 for j in range(1, order + 1)]
                for i in range(1, order + 1)
            ]
        )
        determinant = matrix.det()
        positive = bool(determinant > 0)
        negative = bool(determinant < 0)
        if negative and first_negative is None:
            first_negative = order
        if not positive and not negative and first_unresolved is None:
            first_unresolved = order
        rows.append(
            {
                "order": order,
                "lower": str(determinant.lower()),
                "upper": str(determinant.upper()),
                "certified_positive": positive,
                "certified_negative": negative,
            }
        )
        if stop_on_failure and (negative or not positive):
            break
    return {
        "all_checked_leading_minors_positive": all(
            row["certified_positive"] for row in rows
        ),
        "first_certified_negative_order": first_negative,
        "first_unresolved_order": first_unresolved,
        "leading_minors": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-order", type=int, default=100)
    parser.add_argument("--digits", type=int, default=800)
    parser.add_argument("--adversarial-digits", type=int, default=250)
    parser.add_argument("--gamma", default="14.134725141734693790457251983562")
    parser.add_argument(
        "--betas", nargs="+", default=["0.51", "0.55", "0.60", "0.75"]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_order < 1 or args.digits < 50 or args.adversarial_digits < 50:
        raise SystemExit("invalid order or precision")

    ctx.dps = args.digits
    base = certified_li_coefficients(args.max_order, args.digits)
    base_report = leading_minors(base, args.max_order, stop_on_failure=False)

    adversarial = []
    for beta in args.betas:
        ctx.dps = args.adversarial_digits
        # Recompute the full background at the precision used by this test;
        # do not down-convert stored decimal midpoints.
        background = certified_li_coefficients(args.max_order, args.adversarial_digits)
        quartet = quartet_contributions(beta, args.gamma, args.max_order)
        perturbed = [background[n] + quartet[n] for n in range(args.max_order + 1)]
        report = leading_minors(perturbed, args.max_order, stop_on_failure=True)
        adversarial.append(
            {
                "beta": beta,
                "gamma": args.gamma,
                "interpretation": "full zeta Li background plus one synthetic quartet",
                **report,
            }
        )

    payload = {
        "experiment": "certified_li_distance_gram",
        "matrix": "G_ij = lambda_i + lambda_j - lambda_abs(i-j), i,j=1..N",
        "claim_boundary": (
            "Finite positive-definiteness is not an RH proof. Synthetic quartets are "
            "detector tests and are not asserted to be zeta zeros."
        ),
        "backend": "python-flint/Arb ball arithmetic",
        "max_order": args.max_order,
        "digits": args.digits,
        "unmodified_full_li": base_report,
        "synthetic_off_line_quartets": adversarial,
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
