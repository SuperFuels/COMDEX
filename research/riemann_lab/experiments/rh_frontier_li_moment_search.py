#!/usr/bin/env python3
"""Certified rejection search for simple Li moment/Gram representations.

A moment sequence of a positive measure has positive-semidefinite Hankel
matrices.  A rigorously negative principal determinant therefore rules out
that entire representation, even though only a small matrix is needed as the
certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from flint import arb_mat, ctx

from rh_frontier_li_full_arb import certified_li_coefficients


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-order", type=int, default=8)
    parser.add_argument("--digits", type=int, default=200)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_order < 2:
        raise SystemExit("max-order must be at least two")

    ctx.dps = args.digits
    li = certified_li_coefficients(2 * args.max_order + 2, args.digits)
    candidates = {
        "lambda_shifted": lambda n: li[n + 1],
        "lambda_over_index": lambda n: li[n + 1] / (n + 1),
        "first_difference": lambda n: li[n + 2] - li[n + 1],
    }

    reports = []
    for name, sequence in candidates.items():
        determinants = []
        first_negative_order = None
        for order in range(1, args.max_order + 1):
            matrix = arb_mat(
                [[sequence(i + j) for j in range(order)] for i in range(order)]
            )
            determinant = matrix.det()
            negative = bool(determinant < 0)
            if negative and first_negative_order is None:
                first_negative_order = order
            determinants.append(
                {
                    "order": order,
                    "lower": str(determinant.lower()),
                    "upper": str(determinant.upper()),
                    "certified_negative": negative,
                    "certified_positive": bool(determinant > 0),
                }
            )
        reports.append(
            {
                "candidate": name,
                "first_negative_order": first_negative_order,
                "positive_measure_moment_representation_rejected":
                    first_negative_order is not None,
                "leading_principal_determinants": determinants,
            }
        )

    payload = {
        "experiment": "certified_li_hankel_moment_search",
        "claim_boundary": (
            "Rejects only the three stated moment ansatzes; it does not reject general Gram "
            "or sum-of-squares representations and does not prove/disprove RH."
        ),
        "backend": "python-flint/Arb ball arithmetic",
        "digits": args.digits,
        "max_order": args.max_order,
        "candidates": reports,
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
