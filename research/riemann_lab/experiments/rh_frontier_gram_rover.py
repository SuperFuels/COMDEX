#!/usr/bin/env python3
"""Governed incremental Li distance-Gram positivity rover.

The rover extends an LDL^T certificate one row/column at a time.  Its next
pivot is the Schur complement, so a positive interval extends the certificate,
a negative interval produces a finite quadratic-form countercertificate, and
an interval containing zero triggers a full retry at higher precision.

Finite successful travel is not a proof of RH.  A certified negative pivot in
the unmodified full-Li lane would be a finite failure of the tested Weil/Li
positivity condition and would require independent mathematical review before
any disproof claim.  Synthetic quartet lanes are controls, not zeta zeros.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from flint import arb, arb_mat, ctx

from rh_frontier_li_distance_gram import quartet_contributions
from rh_frontier_li_full_arb import certified_li_coefficients


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def interval_record(value: arb) -> dict:
    return {
        "lower": str(value.lower()),
        "upper": str(value.upper()),
        "midpoint": str(value.mid()),
        "radius": str(value.rad()),
    }


def overlaps(a: arb, b: arb) -> bool:
    return not bool(a.upper() < b.lower()) and not bool(b.upper() < a.lower())


def mine_invariant_candidates(stages: list[dict]) -> dict:
    """Extract certified trends and explicitly heuristic scaling candidates."""
    pivots = [arb(stage["schur_complement"]["midpoint"]) for stage in stages]
    certified_decreases = [
        bool(pivots[n].upper() < pivots[n - 1].lower())
        for n in range(1, len(pivots))
    ]
    ratios = [pivots[n] / pivots[n - 1] for n in range(1, len(pivots))]
    tail_start = max(1, len(pivots) - 30)

    candidates = []
    if ratios:
        for quarter_power in range(0, 17):
            power = quarter_power / 4
            scaled = [
                float((ratios[n - 1] * (n + 1) ** power).mid())
                for n in range(tail_start, len(pivots))
            ]
            if not scaled:
                continue
            mean = sum(scaled) / len(scaled)
            variance = sum((value - mean) ** 2 for value in scaled) / len(scaled)
            relative_spread = math.sqrt(variance) / abs(mean) if mean else math.inf
            candidates.append(
                {
                    "model": f"d_n/d_(n-1) approximately C/n^{power}",
                    "power": power,
                    "tail_mean_C": mean,
                    "tail_relative_spread": relative_spread,
                }
            )
        candidates.sort(key=lambda item: item["tail_relative_spread"])

    return {
        "claim_boundary": (
            "Trend facts use certified intervals; fitted scaling laws use midpoints only "
            "and are conjecture-generation diagnostics, not inequalities or proofs."
        ),
        "certified_all_pivots_positive": all(
            stage["status"] == "positive" for stage in stages
        ),
        "certified_strict_decrease_transitions": sum(certified_decreases),
        "total_transitions": len(certified_decreases),
        "tail_start_stage": tail_start + 1,
        "best_ratio_scaling_candidates": candidates[:5],
    }


@dataclass
class LaneResult:
    name: str
    status: str
    stages: list[dict]
    checkpoints: list[dict]
    stop_certificate: dict | None
    retry_stage: int | None


class IncrementalLDL:
    def __init__(self) -> None:
        self.lower: list[list[arb]] = []
        self.pivots: list[arb] = []

    def extend(self, off_diagonal: list[arb], diagonal: arb) -> tuple[arb, list[arb]]:
        size = len(self.pivots)
        if len(off_diagonal) != size:
            raise ValueError("border length does not match factorization")

        # y = L^{-1} g, where L is unit lower triangular.
        y: list[arb] = []
        for i in range(size):
            correction = sum(
                (self.lower[i][j] * y[j] for j in range(i)), arb(0)
            )
            y.append(off_diagonal[i] - correction)

        pivot = diagonal - sum(
            (y[i] * y[i] / self.pivots[i] for i in range(size)), arb(0)
        )
        new_row = [y[i] / self.pivots[i] for i in range(size)] + [arb(1)]
        self.lower.append(new_row)
        self.pivots.append(pivot)
        return pivot, y

    def negative_witness(self, y: list[arb]) -> list[arb]:
        """Return [-A^{-1}g, 1] for the failed bordered matrix."""
        size = len(y)
        z = [y[i] / self.pivots[i] for i in range(size)]
        solution = [arb(0) for _ in range(size)]
        for i in range(size - 1, -1, -1):
            correction = sum(
                (self.lower[j][i] * solution[j] for j in range(i + 1, size)),
                arb(0),
            )
            solution[i] = z[i] - correction
        return [-value for value in solution] + [arb(1)]


def gram_entry(sequence: list[arb], i: int, j: int) -> arb:
    return sequence[i] + sequence[j] - sequence[abs(i - j)]


def quadratic_form(sequence: list[arb], witness: list[arb]) -> arb:
    size = len(witness)
    return sum(
        (
            witness[i]
            * witness[j]
            * gram_entry(sequence, i + 1, j + 1)
            for i in range(size)
            for j in range(size)
        ),
        arb(0),
    )


def run_lane(
    name: str,
    sequence: list[arb],
    count: int,
    digits: int,
    checkpoint_every: int,
    progress_every: int,
) -> LaneResult:
    factor = IncrementalLDL()
    stages: list[dict] = []
    checkpoints: list[dict] = []
    previous_hash = "0" * 64

    for n in range(1, count + 1):
        border = [gram_entry(sequence, i, n) for i in range(1, n)]
        diagonal = gram_entry(sequence, n, n)
        pivot, y = factor.extend(border, diagonal)
        if pivot > 0:
            status = "positive"
        elif pivot < 0:
            status = "negative"
        else:
            status = "unresolved"

        stage_core = {
            "lane": name,
            "n": n,
            "digits": digits,
            "status": status,
            "schur_complement": interval_record(pivot),
            "previous_stage_hash": previous_hash,
        }
        stage_hash = canonical_hash(stage_core)
        stage = {**stage_core, "stage_hash": stage_hash}
        stages.append(stage)
        previous_hash = stage_hash

        if progress_every and (n == 1 or n % progress_every == 0 or status != "positive"):
            print(
                f"[gram-rover] lane={name} n={n}/{count} status={status} "
                f"digits={digits} pivot={pivot.mid().str(8)}",
                file=sys.stderr,
                flush=True,
            )

        if status == "negative":
            # Remove the failed pivot/row: the witness concerns the previous
            # positive block bordered by the current row and column.
            factor.pivots.pop()
            factor.lower.pop()
            witness = factor.negative_witness(y)
            qvalue = quadratic_form(sequence, witness)
            certificate = {
                "kind": "negative_quadratic_form",
                "order": n,
                "schur_complement": interval_record(pivot),
                "quadratic_form": interval_record(qvalue),
                "quadratic_form_certified_negative": bool(qvalue < 0),
                "witness": [interval_record(value) for value in witness],
                "stage_hash": stage_hash,
            }
            return LaneResult(name, "halted_negative", stages, checkpoints, certificate, None)

        if status == "unresolved":
            return LaneResult(name, "needs_more_precision", stages, checkpoints, None, n)

        if checkpoint_every and (n % checkpoint_every == 0 or n == count):
            matrix = arb_mat(
                [[gram_entry(sequence, i, j) for j in range(1, n + 1)]
                 for i in range(1, n + 1)]
            )
            direct = matrix.det()
            factored = arb(1)
            for value in factor.pivots:
                factored *= value
            checkpoint = {
                "order": n,
                "direct_determinant": interval_record(direct),
                "ldl_determinant": interval_record(factored),
                "intervals_overlap": overlaps(direct, factored),
                "direct_certified_positive": bool(direct > 0),
                "stage_hash": stage_hash,
            }
            checkpoint["checkpoint_hash"] = canonical_hash(checkpoint)
            checkpoints.append(checkpoint)
            if not checkpoint["intervals_overlap"] or not checkpoint["direct_certified_positive"]:
                return LaneResult(
                    name, "checkpoint_failure", stages, checkpoints,
                    {"kind": "checkpoint_mismatch", **checkpoint}, None
                )

    return LaneResult(name, "completed_finite_range", stages, checkpoints, None, None)


def execute_attempt(
    count: int,
    digits: int,
    checkpoint_every: int,
    progress_every: int,
    gamma: str,
    betas: list[str],
) -> dict:
    ctx.dps = digits
    full_li = certified_li_coefficients(count, digits)
    lanes: list[LaneResult] = [
        run_lane("unmodified_full_li", full_li, count, digits, checkpoint_every, progress_every)
    ]
    for beta in betas:
        quartet = quartet_contributions(beta, gamma, count)
        perturbed = [full_li[n] + quartet[n] for n in range(count + 1)]
        lanes.append(
            run_lane(
                f"synthetic_beta_{beta}", perturbed, count, digits,
                checkpoint_every, progress_every,
            )
        )
    return {
        "digits": digits,
        "lanes": [lane.__dict__ for lane in lanes],
        "needs_more_precision": any(
            lane.status == "needs_more_precision" for lane in lanes
            if lane.name == "unmodified_full_li"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--initial-digits", type=int, default=120)
    parser.add_argument("--max-digits", type=int, default=1920)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--gamma", default="14.134725141734693790457251983562")
    parser.add_argument("--betas", nargs="+", default=["0.51", "0.55", "0.75"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.count < 1 or args.initial_digits < 50 or args.max_digits < args.initial_digits:
        raise SystemExit("invalid count or precision range")

    attempts = []
    digits = args.initial_digits
    while True:
        print(f"[gram-rover] starting attempt at {digits} digits", file=sys.stderr, flush=True)
        attempt = execute_attempt(
            args.count, digits, args.checkpoint_every, args.progress_every,
            args.gamma, args.betas,
        )
        attempts.append(attempt)
        if not attempt["needs_more_precision"]:
            break
        if digits >= args.max_digits:
            break
        digits = min(args.max_digits, digits * 2)
        print(f"[gram-rover] refuelling: precision -> {digits} digits", file=sys.stderr, flush=True)

    final_attempt = attempts[-1]
    main_lane = next(
        lane for lane in final_attempt["lanes"] if lane["name"] == "unmodified_full_li"
    )
    payload = {
        "experiment": "governed_incremental_li_gram_rover",
        "claim_boundary": (
            "Finite travel is not an RH proof. Synthetic lanes are controls. "
            "Any unmodified negative certificate requires independent review before a disproof claim."
        ),
        "backend": "python-flint/Arb ball arithmetic with incremental LDL^T",
        "count": args.count,
        "adaptive_precision_attempts": [attempt["digits"] for attempt in attempts],
        "checkpoint_every": args.checkpoint_every,
        "main_lane_status": main_lane["status"],
        "invariant_diagnostics": mine_invariant_candidates(main_lane["stages"]),
        "attempts": attempts,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
