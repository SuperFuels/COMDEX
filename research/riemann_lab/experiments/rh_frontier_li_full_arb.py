#!/usr/bin/env python3
"""Certified Li coefficients from the Taylor expansion of the completed zeta.

Requires python-flint, which wraps Arb ball arithmetic.  Every reported
interval is therefore an enclosure, not a rounded point estimate.

For t = s-1 we expand

  log xi(1+t) = log(1+t) - (1+t)log(pi)/2
                + log Gamma((1+t)/2) + log(t*zeta(1+t)) - log(2).

The substitution t=z/(1-z) then gives

  log xi(1/(1-z)) = log xi(1) + sum_{n>=1} lambda_n z^n/n.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from flint import acb, arb, ctx
except ImportError as exc:  # pragma: no cover - explicit runtime diagnostic
    raise SystemExit(
        "python-flint is required; install the pinned experiments/requirements-li-arb.txt"
    ) from exc


def log_unit_series(coefficients: list[arb]) -> list[arb]:
    """Return log(A), where A[0]=1, through the supplied degree."""
    degree = len(coefficients) - 1
    result = [arb(0) for _ in range(degree + 1)]
    for n in range(1, degree + 1):
        correction = arb(0)
        for k in range(1, n):
            correction += k * result[k] * coefficients[n - k]
        result[n] = coefficients[n] - correction / n
    return result


def certified_li_coefficients(count: int, digits: int) -> list[arb]:
    ctx.dps = digits
    euler = arb.const_euler()
    log2 = arb.const_log2()
    pi = arb.const_sqrt_pi() ** 2
    logpi = pi.log()

    # t*zeta(1+t), using the Laurent expansion in Stieltjes constants.
    zeta_regularized = [arb(0) for _ in range(count + 1)]
    zeta_regularized[0] = arb(1)
    for degree in range(1, count + 1):
        gamma = acb.stieltjes(degree - 1)
        if gamma.imag != 0:
            raise ArithmeticError("Stieltjes enclosure unexpectedly has a nonzero imaginary part")
        coefficient = gamma.real / math.factorial(degree - 1)
        zeta_regularized[degree] = coefficient if degree % 2 else -coefficient
    log_regularized_zeta = log_unit_series(zeta_regularized)

    log_xi_taylor = [arb(0) for _ in range(count + 1)]
    for k in range(1, count + 1):
        log_one_plus_t = arb(1 if k % 2 else -1) / k
        if k == 1:
            log_gamma = (-euler - 2 * log2) / 2
            archimedean_linear = -logpi / 2
        else:
            log_gamma = (
                arb(1 if k % 2 == 0 else -1)
                * ((arb(2) ** k) - 1)
                * arb(k).zeta()
                / (k * (arb(2) ** k))
            )
            archimedean_linear = arb(0)
        log_xi_taylor[k] = (
            log_one_plus_t
            + archimedean_linear
            + log_gamma
            + log_regularized_zeta[k]
        )

    li = [arb(0) for _ in range(count + 1)]
    for n in range(1, count + 1):
        coefficient = arb(0)
        for k in range(1, n + 1):
            coefficient += math.comb(n - 1, k - 1) * log_xi_taylor[k]
        li[n] = n * coefficient
    return li


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--digits", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.count < 1 or args.digits < 30:
        raise SystemExit("count must be positive and digits must be at least 30")

    values = certified_li_coefficients(args.count, args.digits)
    rows = []
    for n in range(1, args.count + 1):
        value = values[n]
        rows.append(
            {
                "n": n,
                "lower": str(value.lower()),
                "upper": str(value.upper()),
                "midpoint": str(value.mid()),
                "radius": str(value.rad()),
                "certified_positive": bool(value > 0),
            }
        )

    payload = {
        "experiment": "arb_certified_full_li_coefficients",
        "claim_boundary": (
            "Finite rigorous enclosures only; positivity through a finite index does not prove RH."
        ),
        "backend": "python-flint/Arb ball arithmetic",
        "count": args.count,
        "digits": args.digits,
        "all_certified_positive": all(row["certified_positive"] for row in rows),
        "coefficients": rows,
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
