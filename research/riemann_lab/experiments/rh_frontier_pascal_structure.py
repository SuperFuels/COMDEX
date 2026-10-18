#!/usr/bin/env python3
"""Mine the exact Pascal structure behind the Li distance--Gram rover.

This analysis has two deliberately separate parts.

* It measures how closely the saved unit-lower LDL factor follows the Pascal
  matrix ``P[n,k] = binom(n,k)``.  These measurements are numerical clues,
  not theorems.
* It verifies, using exact integer arithmetic, the coefficient formula for
  the inverse-Pascal congruence of the abstract Li distance kernel after the
  Li coefficients are expanded in reciprocal-zero power sums.

Nothing here assumes RH.  Positive finite rover stages do not prove RH, and
the reciprocal-zero power sums are used only as formal symbols in the exact
identity check.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from decimal import Decimal, getcontext
from pathlib import Path


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def verify_state_hash(state: dict) -> None:
    saved = state.get("state_sha256")
    core = {key: value for key, value in state.items() if key != "state_sha256"}
    if saved != canonical_hash(core):
        raise ValueError("rover state hash mismatch")


def arb_bounds(text: str) -> tuple[Decimal, Decimal]:
    """Parse the midpoint/radius format written by python-flint's Arb."""
    stripped = text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    if " +/- " not in stripped:
        value = Decimal(stripped)
        return value, value
    midpoint_text, radius_text = stripped.split(" +/- ", 1)
    midpoint = Decimal(midpoint_text)
    radius = Decimal(radius_text)
    return midpoint - radius, midpoint + radius


def interval_record(lower: Decimal, upper: Decimal) -> dict:
    return {
        "lower": str(lower),
        "upper": str(upper),
        "midpoint": str((lower + upper) / 2),
    }


def add_vectors(*vectors: list[int]) -> list[int]:
    return [sum(values) for values in zip(*vectors)]


def scale_vector(coefficient: int, vector: list[int]) -> list[int]:
    return [coefficient * value for value in vector]


def li_mode_coefficients(order: int, width: int) -> list[int]:
    """Coefficients of lambda_order in formal reciprocal power sums mu_k."""
    result = [0] * width
    for k in range(1, order + 1):
        result[k - 1] = (-1) ** (k + 1) * math.comb(order, k)
    return result


def gram_coefficients(i: int, j: int, width: int) -> list[int]:
    return add_vectors(
        li_mode_coefficients(i, width),
        li_mode_coefficients(j, width),
        scale_vector(-1, li_mode_coefficients(abs(i - j), width)),
    )


def inverse_pascal_entry(n: int, k: int) -> int:
    return (-1) ** (n - k) * math.comb(n, k)


def transformed_coefficients(n: int, m: int, width: int) -> list[int]:
    result = [0] * width
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            result = add_vectors(
                result,
                scale_vector(
                    inverse_pascal_entry(n, i) * inverse_pascal_entry(m, j),
                    gram_coefficients(i, j, width),
                ),
            )
    return result


def closed_form_coefficients(n: int, m: int, width: int) -> list[int]:
    """Closed coefficient formula for B G B^T, with B=P^{-1}."""
    sign = (-1) ** (n + m)
    result = [0] * width
    for k in range(1, max(n, m) + 1):
        top = n + m - k - 1
        left = math.comb(top, n - 1) if top >= n - 1 else 0
        right = math.comb(top, m - 1) if top >= m - 1 else 0
        result[k - 1] = sign * (left + right)
    return result


def verify_exact_identity(max_order: int) -> dict:
    checked = 0
    examples = []
    for n in range(1, max_order + 1):
        for m in range(1, n + 1):
            actual = transformed_coefficients(n, m, max_order)
            expected = closed_form_coefficients(n, m, max_order)
            if actual != expected:
                raise AssertionError(f"exact Pascal identity failed at ({n}, {m})")
            checked += 1
            if (n, m) in {(1, 1), (3, 2), (5, 3), (max_order, max_order)}:
                examples.append(
                    {
                        "n": n,
                        "m": m,
                        "nonzero_mu_coefficients": [
                            {"k": k + 1, "coefficient": value}
                            for k, value in enumerate(expected)
                            if value
                        ],
                    }
                )
    return {
        "verified_through_order": max_order,
        "matrix_entries_checked": checked,
        "formula": (
            "(B G B^T)_(n,m) = (-1)^(n+m) sum_k "
            "[C(n+m-k-1,n-1)+C(n+m-k-1,m-1)] mu_k"
        ),
        "examples": examples,
    }


def pascal_proximity(state: dict, rows: list[int], max_depth: int) -> dict:
    lambda_one_lower, lambda_one_upper = arb_bounds(state["coefficients"][1])
    records = []
    for n in rows:
        if not 2 <= n <= state["completed_order"]:
            continue
        row = state["lower_triangular"][n - 1]
        depths = []
        for depth in range(1, min(max_depth, n - 1) + 1):
            lower, upper = arb_bounds(row[-(depth + 1)])
            pascal = Decimal(math.comb(n, depth))
            ratio_lower, ratio_upper = lower / pascal, upper / pascal
            normalizer = Decimal(math.comb(n - 1, depth - 1))
            defect_lower = (pascal - upper) / normalizer
            defect_upper = (pascal - lower) / normalizer
            depths.append(
                {
                    "depth": depth,
                    "pascal_entry": str(pascal),
                    "ldl_entry": interval_record(lower, upper),
                    "ratio_to_pascal": interval_record(ratio_lower, ratio_upper),
                    "normalized_defect": interval_record(defect_lower, defect_upper),
                }
            )
        records.append({"row": n, "depths": depths})
    return {
        "definition": (
            "depth j compares saved L_(n,n-j) with C(n,j); normalized defect "
            "is [C(n,j)-L_(n,n-j)]/C(n-1,j-1)"
        ),
        "lambda_1_reference": interval_record(lambda_one_lower, lambda_one_upper),
        "rows": records,
        "interpretation": (
            "The near-Pascal pattern and apparent drift of the normalized defect "
            "toward lambda_1 are conjecture-mining observations only."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exact-order", type=int, default=12)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--rows", default="20,50,100,150,200,240")
    args = parser.parse_args()
    if args.exact_order < 1 or args.max_depth < 1:
        raise SystemExit("orders and depths must be positive")

    state = read_json(args.state)
    verify_state_hash(state)
    getcontext().prec = max(100, min(1000, int(state["digits"])))
    requested_rows = [int(value) for value in args.rows.split(",") if value]
    payload = {
        "experiment": "li_gram_pascal_structure",
        "source_state": str(args.state),
        "source_state_sha256": state["state_sha256"],
        "completed_order": state["completed_order"],
        "digits": state["digits"],
        "exact_inverse_pascal_identity": verify_exact_identity(args.exact_order),
        "ldl_pascal_proximity": pascal_proximity(
            state, requested_rows, args.max_depth
        ),
        "claim_boundary": (
            "The finite exact combinatorial identity is verified independently of RH. "
            "The LDL proximity data are finite numerical observations and neither prove "
            "nor disprove RH."
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
