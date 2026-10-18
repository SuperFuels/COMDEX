#!/usr/bin/env python3
"""Adversarial Li-coefficient contribution of a hypothetical zero quartet.

This is a falsification and sensitivity experiment, not evidence that such a
zero exists.  For rho = beta + i*gamma it evaluates the isolated contribution

    sum_{z in {rho, conj rho, 1-rho, 1-conj rho}}
        (1 - (1 - 1/z)^n).

On the critical line the corresponding conjugate pair is nonnegative.  An
off-line quartet contains an exponentially growing mode and is therefore a
useful detector model for Li positivity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path


ComplexDecimal = tuple[Decimal, Decimal]


def cadd(a: ComplexDecimal, b: ComplexDecimal) -> ComplexDecimal:
    return (a[0] + b[0], a[1] + b[1])


def cmul(a: ComplexDecimal, b: ComplexDecimal) -> ComplexDecimal:
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def cinv(a: ComplexDecimal) -> ComplexDecimal:
    denominator = a[0] * a[0] + a[1] * a[1]
    return (a[0] / denominator, -a[1] / denominator)


def csub(a: ComplexDecimal, b: ComplexDecimal) -> ComplexDecimal:
    return (a[0] - b[0], a[1] - b[1])


def cabs(a: ComplexDecimal) -> Decimal:
    return (a[0] * a[0] + a[1] * a[1]).sqrt()


def scan_quartet(beta: str, gamma: str, max_n: int, digits: int) -> dict:
    getcontext().prec = digits
    b = Decimal(beta)
    g = Decimal(gamma)
    one = (Decimal(1), Decimal(0))
    rho = (b, g)
    conjugate = (b, -g)
    quartet = (rho, conjugate, csub(one, rho), csub(one, conjugate))
    ratios = tuple(csub(one, cinv(z)) for z in quartet)
    powers = [one for _ in ratios]

    first_negative = None
    minimum_n = 1
    minimum_value = Decimal("Infinity")
    for n in range(1, max_n + 1):
        for j, ratio in enumerate(ratios):
            powers[j] = cmul(powers[j], ratio)
        total = (Decimal(0), Decimal(0))
        for power in powers:
            total = cadd(total, power)
        value = Decimal(4) - total[0]
        if value < minimum_value:
            minimum_value = value
            minimum_n = n
        if first_negative is None and value < 0:
            first_negative = {"n": n, "contribution": format(value, ".30E")}

    return {
        "beta": str(beta),
        "gamma": str(gamma),
        "max_n": max_n,
        "digits": digits,
        "ratio_moduli": [format(cabs(q), ".30E") for q in ratios],
        "first_negative": first_negative,
        "minimum": {"n": minimum_n, "contribution": format(minimum_value, ".30E")},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gamma", default="14.134725141734693790457251983562")
    parser.add_argument(
        "--betas", nargs="+", default=["0.50", "0.51", "0.55", "0.60", "0.75"]
    )
    parser.add_argument("--max-n", type=int, default=200000)
    parser.add_argument("--digits", type=int, default=80)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = [scan_quartet(beta, args.gamma, args.max_n, args.digits) for beta in args.betas]
    payload = {
        "experiment": "hypothetical_off_critical_quartet_li_contribution",
        "claim_boundary": (
            "Sensitivity study only. It neither exhibits a zeta zero nor proves/disproves RH."
        ),
        "formula": "sum_z (1 - (1 - 1/z)^n) over the symmetry quartet",
        "cases": cases,
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
