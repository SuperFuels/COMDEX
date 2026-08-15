#!/usr/bin/env python3
"""Persistent block runner for the unmodified full-Li Gram rover.

This complements `rh_frontier_gram_rover.py`.  It saves the certified LDL
factorization and Li coefficient intervals, then resumes at the next order at
the same precision.  A precision increase still requires rebuilding the
factorization: low-precision intervals cannot honestly be promoted to high
precision merely by reloading them.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

from flint import arb, arb_mat, ctx

from rh_frontier_gram_rover import (
    IncrementalLDL,
    canonical_hash,
    gram_entry,
    interval_record,
    overlaps,
)
from rh_frontier_li_full_arb import certified_li_coefficients


STATE_FORMAT = "aion_li_gram_rover_state_v1"


def save_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        if path.suffix == ".gz":
            with os.fdopen(descriptor, "wb") as raw:
                with gzip.open(raw, "wt", encoding="utf-8", compresslevel=6) as handle:
                    json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                    handle.write("\n")
                raw.flush()
                os.fsync(raw.fileno())
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def read_json(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def serialize_state(
    factor: IncrementalLDL,
    coefficients: list[arb],
    completed_order: int,
    digits: int,
    last_stage_hash: str,
    checkpoint_hashes: list[str],
) -> dict:
    core = {
        "format": STATE_FORMAT,
        "digits": digits,
        "completed_order": completed_order,
        "last_stage_hash": last_stage_hash,
        "checkpoint_hashes": checkpoint_hashes,
        "coefficients": [str(value) for value in coefficients[: completed_order + 1]],
        "lower_triangular": [[str(value) for value in row] for row in factor.lower],
        "pivots": [str(value) for value in factor.pivots],
        "claim_boundary": "Finite resumable positivity certificate; not an RH proof.",
    }
    return {**core, "state_sha256": canonical_hash(core)}


def load_state(path: Path, digits: int) -> tuple[dict, IncrementalLDL, list[arb]]:
    payload = read_json(path)
    if payload.get("format") != STATE_FORMAT:
        raise ValueError("unsupported rover state format")
    saved_hash = payload.pop("state_sha256", None)
    if saved_hash != canonical_hash(payload):
        raise ValueError("rover state hash mismatch")
    payload["state_sha256"] = saved_hash
    if payload["digits"] != digits:
        raise ValueError(
            "saved precision differs from requested precision; rebuild rather than promote intervals"
        )
    factor = IncrementalLDL()
    factor.lower = [[arb(value) for value in row] for row in payload["lower_triangular"]]
    factor.pivots = [arb(value) for value in payload["pivots"]]
    coefficients = [arb(value) for value in payload["coefficients"]]
    completed = payload["completed_order"]
    if len(factor.pivots) != completed or len(factor.lower) != completed:
        raise ValueError("factor dimensions disagree with completed order")
    return payload, factor, coefficients


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--digits", type=int, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.target < 1 or args.digits < 50:
        raise SystemExit("invalid target or precision")

    ctx.dps = args.digits
    coefficients = certified_li_coefficients(args.target, args.digits)
    if args.state.exists():
        saved, factor, cached_coefficients = load_state(args.state, args.digits)
        completed = saved["completed_order"]
        if completed > args.target:
            raise SystemExit("saved state is already beyond the requested target")
        if any(
            not overlaps(cached_coefficients[n], coefficients[n])
            for n in range(completed + 1)
        ):
            raise SystemExit("recomputed Li coefficients do not overlap the saved state")
        previous_hash = saved["last_stage_hash"]
        checkpoint_hashes = list(saved["checkpoint_hashes"])
        print(
            f"[gram-rover-block] resumed order={completed} digits={args.digits}",
            file=sys.stderr,
            flush=True,
        )
    else:
        factor = IncrementalLDL()
        completed = 0
        previous_hash = "0" * 64
        checkpoint_hashes = []

    new_stages = []
    status = "completed_finite_block"
    stop_detail = None
    permit_state_update = True
    for n in range(completed + 1, args.target + 1):
        border = [gram_entry(coefficients, i, n) for i in range(1, n)]
        diagonal = gram_entry(coefficients, n, n)
        pivot, _ = factor.extend(border, diagonal)
        sign = "positive" if pivot > 0 else "negative" if pivot < 0 else "unresolved"
        core = {
            "n": n,
            "digits": args.digits,
            "status": sign,
            "schur_complement": interval_record(pivot),
            "previous_stage_hash": previous_hash,
        }
        stage_hash = canonical_hash(core)
        new_stages.append({**core, "stage_hash": stage_hash})
        previous_hash = stage_hash
        if args.progress_every and (n % args.progress_every == 0 or sign != "positive"):
            print(
                f"[gram-rover-block] n={n}/{args.target} status={sign} "
                f"pivot={pivot.mid().str(8)}",
                file=sys.stderr,
                flush=True,
            )
        if sign != "positive":
            status = "halted_negative" if sign == "negative" else "needs_more_precision"
            stop_detail = {"order": n, "status": sign, "pivot": interval_record(pivot)}
            factor.pivots.pop()
            factor.lower.pop()
            previous_hash = new_stages[-2]["stage_hash"] if len(new_stages) > 1 else (
                saved["last_stage_hash"] if args.state.exists() else "0" * 64
            )
            new_stages.pop()
            break

        completed = n
        if args.checkpoint_every and (n % args.checkpoint_every == 0 or n == args.target):
            matrix = arb_mat(
                [[gram_entry(coefficients, i, j) for j in range(1, n + 1)]
                 for i in range(1, n + 1)]
            )
            direct = matrix.det()
            factored = arb(1)
            for value in factor.pivots:
                factored *= value
            checkpoint = {
                "order": n,
                "direct": interval_record(direct),
                "factored": interval_record(factored),
                "overlap": overlaps(direct, factored),
                "positive": bool(direct > 0),
                "stage_hash": previous_hash,
            }
            checkpoint_hashes.append(canonical_hash(checkpoint))
            if not checkpoint["overlap"] or not checkpoint["positive"]:
                status = "checkpoint_failure"
                stop_detail = checkpoint
                permit_state_update = False
                break
            state = serialize_state(
                factor, coefficients, completed, args.digits,
                previous_hash, checkpoint_hashes,
            )
            save_json_atomic(args.state, state)
            print(
                f"[gram-rover-block] checkpoint saved order={n}",
                file=sys.stderr,
                flush=True,
            )

    # Persist the last certified prefix even when the next pivot was unresolved.
    if permit_state_update:
        state = serialize_state(
            factor, coefficients, completed, args.digits, previous_hash, checkpoint_hashes
        )
        save_json_atomic(args.state, state)
        final_state_hash = state["state_sha256"]
    else:
        final_state_hash = (
            read_json(args.state)["state_sha256"]
            if args.state.exists() else None
        )
    result = {
        "experiment": "persistent_li_gram_rover_block",
        "status": status,
        "digits": args.digits,
        "starting_order": saved["completed_order"] if args.state.exists() and 'saved' in locals() else 0,
        "completed_order": completed,
        "target_order": args.target,
        "new_stages": new_stages,
        "stop_detail": stop_detail,
        "state_sha256": final_state_hash,
        "claim_boundary": "Finite block certificate only; not an RH proof.",
    }
    result["payload_sha256"] = canonical_hash(result)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.result:
        save_json_atomic(args.result, result)
    print(rendered, end="")


if __name__ == "__main__":
    main()
