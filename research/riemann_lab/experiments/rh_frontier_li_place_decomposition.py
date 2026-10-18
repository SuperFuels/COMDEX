#!/usr/bin/env python3
"""Certified local-place decomposition of the Li distance-Gram matrix.

The Taylor construction of log xi at s=1 is split linearly into:
  * the elementary/pole and pi-normalization terms,
  * the archimedean Gamma term,
  * the regularized finite-place zeta term.

The experiment asks whether any piece is positive semidefinite by itself.
A certified negative principal minor rules out a termwise-local positivity
proof and shows that cancellation between places is essential.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from flint import acb, arb, arb_mat, ctx

from rh_frontier_li_full_arb import log_unit_series


def component_li_coefficients(count: int, digits: int) -> dict[str, list[arb]]:
    ctx.dps = digits
    euler = arb.const_euler()
    log2 = arb.const_log2()
    pi = arb.const_sqrt_pi() ** 2
    logpi = pi.log()

    regularized = [arb(0) for _ in range(count + 1)]
    regularized[0] = arb(1)
    for degree in range(1, count + 1):
        gamma = acb.stieltjes(degree - 1)
        if gamma.imag != 0:
            raise ArithmeticError("nonreal Stieltjes enclosure")
        coefficient = gamma.real / math.factorial(degree - 1)
        regularized[degree] = coefficient if degree % 2 else -coefficient
    log_regularized = log_unit_series(regularized)

    taylor = {
        "elementary_pole_pi": [arb(0) for _ in range(count + 1)],
        "archimedean_gamma": [arb(0) for _ in range(count + 1)],
        "regularized_finite_place": [arb(0) for _ in range(count + 1)],
    }
    for k in range(1, count + 1):
        taylor["elementary_pole_pi"][k] = (
            arb(1 if k % 2 else -1) / k
            + (-logpi / 2 if k == 1 else arb(0))
        )
        taylor["archimedean_gamma"][k] = (
            (-euler - 2 * log2) / 2
            if k == 1
            else arb(1 if k % 2 == 0 else -1)
            * ((arb(2) ** k) - 1)
            * arb(k).zeta()
            / (k * (arb(2) ** k))
        )
        taylor["regularized_finite_place"][k] = log_regularized[k]

    result = {}
    for name, series in taylor.items():
        li = [arb(0) for _ in range(count + 1)]
        for n in range(1, count + 1):
            coefficient = sum(
                (math.comb(n - 1, k - 1) * series[k] for k in range(1, n + 1)),
                arb(0),
            )
            li[n] = n * coefficient
        result[name] = li
    result["complete"] = [
        sum((result[name][n] for name in taylor), arb(0))
        for n in range(count + 1)
    ]
    return result


def minor_report(sequence: list[arb], max_order: int) -> dict:
    minors = []
    first_negative = None
    first_unresolved = None
    for order in range(1, max_order + 1):
        matrix = arb_mat(
            [[sequence[i] + sequence[j] - sequence[abs(i - j)]
              for j in range(1, order + 1)]
             for i in range(1, order + 1)]
        )
        determinant = matrix.det()
        positive = bool(determinant > 0)
        negative = bool(determinant < 0)
        if negative and first_negative is None:
            first_negative = order
        if not positive and not negative and first_unresolved is None:
            first_unresolved = order
        minors.append(
            {
                "order": order,
                "lower": str(determinant.lower()),
                "upper": str(determinant.upper()),
                "certified_positive": positive,
                "certified_negative": negative,
            }
        )
        if negative or not positive:
            break
    return {
        "first_certified_negative_order": first_negative,
        "first_unresolved_order": first_unresolved,
        "all_checked_positive": all(x["certified_positive"] for x in minors),
        "leading_principal_minors": minors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-order", type=int, default=30)
    parser.add_argument("--digits", type=int, default=250)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_order < 2 or args.digits < 50:
        raise SystemExit("invalid order or precision")

    components = component_li_coefficients(args.max_order, args.digits)
    reports = {
        name: {
            "lambda_1": {"lower": str(values[1].lower()), "upper": str(values[1].upper())},
            **minor_report(values, args.max_order),
        }
        for name, values in components.items()
    }
    payload = {
        "experiment": "certified_li_distance_gram_place_decomposition",
        "claim_boundary": (
            "This linear Taylor decomposition isolates an obstruction to local termwise "
            "positivity. It neither proves nor disproves RH."
        ),
        "backend": "python-flint/Arb ball arithmetic",
        "max_order": args.max_order,
        "digits": args.digits,
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
