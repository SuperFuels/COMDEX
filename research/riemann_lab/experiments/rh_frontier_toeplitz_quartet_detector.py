#!/usr/bin/env python3
"""High-precision controls for the Lean three-lag quartet determinant.

These are synthetic off-line points, not zeta zeros.  The determinant identity
and its sign theorem are proved separately in Lean; this script reports the
scale of the certificate for representative perturbations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path


def analyse_case(beta_text: str, gamma_text: str) -> dict:
    beta = Decimal(beta_text)
    gamma = Decimal(gamma_text)
    one = Decimal(1)
    four = Decimal(4)
    x = gamma * gamma + beta * (one - beta)
    c = gamma * (2 * beta - one)
    denominator = x * x + c * c
    a = 2 - x / denominator
    b = -c / denominator
    sign_factor = a * a - b * b - four
    determinant = Decimal(16) * b * b * sign_factor
    return {
        "beta": beta_text,
        "gamma": gamma_text,
        "X": str(x),
        "C": str(c),
        "a": str(a),
        "b": str(b),
        "a_squared_minus_b_squared_minus_four": str(sign_factor),
        "determinant_3x3": str(determinant),
        "critical_line": beta == Decimal("0.5"),
        "lean_sign_hypotheses_hold": x > Decimal("0.25") and c != 0,
        "determinant_negative": determinant < 0,
    }


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gamma", default="14.134725141734693790457251983562"
    )
    parser.add_argument(
        "--betas", nargs="+", default=["0.5", "0.5001", "0.51", "0.55", "0.60", "0.75"]
    )
    parser.add_argument("--digits", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.digits < 50:
        raise SystemExit("digits must be at least 50")
    getcontext().prec = args.digits
    cases = [analyse_case(beta, args.gamma) for beta in args.betas]
    payload = {
        "experiment": "three_lag_toeplitz_quartet_detector",
        "formula": "det_3 = 16*b^2*(a^2-b^2-4)",
        "cases": cases,
        "off_line_cases_all_negative": all(
            case["determinant_negative"]
            for case in cases
            if not case["critical_line"]
        ),
        "critical_case_zero": all(
            Decimal(case["determinant_3x3"]) == 0
            for case in cases
            if case["critical_line"]
        ),
        "claim_boundary": (
            "Synthetic sensitivity controls only. The isolated-quartet sign theorem is "
            "Lean-verified, but the positive background from the full zero divisor can "
            "mask this local determinant. No zeta zero or RH disproof is claimed."
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
