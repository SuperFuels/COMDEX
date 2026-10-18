#!/usr/bin/env python3
"""Exact checks for the Pascal--Toeplitz Li kernel generating function.

For one reciprocal-zero variable x = 1/rho, let h[n,m](x) be the naturally
truncated inverse-Pascal transform of (1-x)^|i-j|.  The proposed bivariate
generating function for positive n,m is

  sum h[n,m](x) z^n w^m
    = x*z*w*(2 + x*(z+w)) / ((1+z+w)*(1+x*z)*(1+x*w)).

The script checks the coefficient recurrence implied by this rational identity
using exact integer polynomial arithmetic.  It is a finite verifier and does
not replace the universal Lean proof of the Toeplitz reduction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rh_frontier_pascal_structure import closed_form_coefficients


Polynomial = tuple[int, ...]


def trim(poly: list[int] | tuple[int, ...]) -> Polynomial:
    values = list(poly)
    while values and values[-1] == 0:
        values.pop()
    return tuple(values)


def add_poly(left: Polynomial, right: Polynomial) -> Polynomial:
    width = max(len(left), len(right))
    return trim(
        [
            (left[k] if k < len(left) else 0)
            + (right[k] if k < len(right) else 0)
            for k in range(width)
        ]
    )


def mul_poly(left: Polynomial, right: Polynomial) -> Polynomial:
    if not left or not right:
        return ()
    result = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] += a * b
    return trim(result)


DENOMINATOR: dict[tuple[int, int], Polynomial] = {
    (0, 0): (1,),
    (1, 0): (1, 1),
    (0, 1): (1, 1),
    (2, 0): (0, 1),
    (0, 2): (0, 1),
    (1, 1): (0, 2, 1),
    (2, 1): (0, 0, 1),
    (1, 2): (0, 0, 1),
}

NUMERATOR: dict[tuple[int, int], Polynomial] = {
    (1, 1): (0, 2),
    (2, 1): (0, 0, 1),
    (1, 2): (0, 0, 1),
}


def kernel_polynomial(n: int, m: int, width: int) -> Polynomial:
    if n < 1 or m < 1:
        return ()
    # `closed_form_coefficients` stores the coefficient of x^k at index k-1.
    return trim((0, *closed_form_coefficients(n, m, width)))


def denominator_times_kernel(n: int, m: int, width: int) -> Polynomial:
    total: Polynomial = ()
    for (dn, dm), coefficient in DENOMINATOR.items():
        if dn <= n and dm <= m:
            total = add_poly(
                total,
                mul_poly(coefficient, kernel_polynomial(n - dn, m - dm, width)),
            )
    return total


def verify(order: int) -> dict:
    width = 2 * order + 4
    checks = []
    for n in range(1, order + 1):
        for m in range(1, order + 1):
            actual = denominator_times_kernel(n, m, width)
            expected = NUMERATOR.get((n, m), ())
            if actual != expected:
                raise AssertionError(
                    f"rational generating-function recurrence failed at ({n},{m})"
                )
            checks.append((n, m))
    examples = {
        f"h_{n}_{m}": list(kernel_polynomial(n, m, width))
        for n, m in ((1, 1), (3, 2), (5, 3), (5, 5), (order, order))
        if n <= order and m <= order
    }
    return {
        "verified_square_order": order,
        "coefficient_pairs_checked": len(checks),
        "generating_function": (
            "sum_(n,m>=1) h_nm(x) z^n w^m = "
            "x*z*w*(2+x*(z+w))/((1+z+w)*(1+x*z)*(1+x*w))"
        ),
        "examples_as_x_coefficient_lists": examples,
    }


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", type=int, default=24)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.order < 2:
        raise SystemExit("order must be at least two")
    payload = {
        "experiment": "exact_pascal_toeplitz_generating_function",
        **verify(args.order),
        "claim_boundary": (
            "Finite exact-integer verification of a rational coefficient identity. "
            "It neither proves the universal identity nor proves/disproves RH."
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
