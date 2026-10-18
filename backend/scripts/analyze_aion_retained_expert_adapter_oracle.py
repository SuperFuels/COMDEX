#!/usr/bin/env python3
"""Upper-bound a retained-expert low-rank adapter before training/runtime work."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--fit-family", action="append", required=True)
    parser.add_argument("--development-family", required=True)
    parser.add_argument("--maximum-relative-l2", type=float, default=0.02)
    parser.add_argument("--minimum-coverage", type=float, default=0.10)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.dataset_manifest.read_text())
    dataset_path = Path(manifest["dataset_path"])
    if digest(dataset_path) != manifest["dataset_sha256"]:
        raise SystemExit("dataset hash mismatch")
    arrays = dict(np.load(dataset_path))
    rows = manifest["rows"]
    fit = np.asarray([i for i, row in enumerate(rows)
                      if int(row["layer"]) == args.layer
                      and row["family_id"] in args.fit_family])
    development = np.asarray([i for i, row in enumerate(rows)
                              if int(row["layer"]) == args.layer
                              and row["family_id"] == args.development_family])
    if len(fit) < 2 or not len(development):
        raise SystemExit("insufficient family-isolated rows")
    targets = np.asarray(arrays["omitted"], dtype=np.float64)
    mean = targets[fit].mean(0)
    _, _, basis = np.linalg.svd(targets[fit] - mean, full_matrices=False)
    layer_outputs = (np.asarray(arrays["ffn"], dtype=np.float64)[development]
                     + np.asarray(arrays["full"], dtype=np.float64)[development])
    denominators = np.maximum(np.linalg.norm(layer_outputs, axis=1), 1e-30)
    ranks = sorted(set([4, 8, 12, 16, 24, 32, 48, len(fit) - 1]))
    candidates = []
    observations = []
    for rank in ranks:
        active = basis[:rank]
        # This intentionally uses each held-out target itself to choose its
        # best coefficients. No deployable predictor can outperform it while
        # restricted to this learned output subspace.
        prediction = mean + (targets[development] - mean) @ active.T @ active
        errors = np.linalg.norm(prediction - targets[development], axis=1) / denominators
        safe = errors <= args.maximum_relative_l2
        candidates.append({
            "rank": rank,
            "relative_l2_p50": float(np.median(errors)),
            "relative_l2_p95": float(np.percentile(errors, 95)),
            "relative_l2_max": float(np.max(errors)),
            "oracle_safe_rows": int(np.sum(safe)),
            "oracle_coverage": float(np.mean(safe)),
        })
        if rank == len(fit) - 1:
            observations = [{
                "position": int(rows[int(index)]["position"]),
                "top_expert": int(rows[int(index)]["route"][0]),
                "omitted_experts": [int(value) for value in rows[int(index)]["route"][1:]],
                "relative_l2": float(error), "oracle_safe": bool(is_safe),
            } for index, error, is_safe in zip(development, errors, safe, strict=True)]
    best = max(candidates, key=lambda item: (item["oracle_safe_rows"],
                                             -item["relative_l2_p95"]))
    accepted = best["oracle_coverage"] >= args.minimum_coverage
    report = {
        "schema": "aion.gptoss-120b-retained-expert-adapter-oracle.v1",
        "status": ("ADVANCE_RETAINED_EXPERT_ADAPTER" if accepted
                   else "STOP_RETAINED_EXPERT_LOW_RANK_ADAPTER"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "oracle_uses_true_target": True,
        "layer": args.layer, "fit_families": sorted(args.fit_family),
        "development_family": args.development_family,
        "fit_rows": len(fit), "development_rows": len(development),
        "maximum_relative_l2": args.maximum_relative_l2,
        "minimum_coverage": args.minimum_coverage,
        "candidates": candidates, "best": best,
        "full_training_span_observations": observations,
        "dataset_manifest_canonical_sha256": manifest["canonical_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "claim_boundary": (
            "This impossible oracle observes each held-out omitted-expert target and chooses "
            "its optimal coefficients in the complete output span learned from both genuine "
            "fit families. A route-conditioned low-rank down adapter trained on the same "
            "targets cannot exceed this coverage without introducing new output directions "
            "or additional genuine-family teacher data. No token-speed claim is made."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "fit_rows", "development_rows", "best", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
