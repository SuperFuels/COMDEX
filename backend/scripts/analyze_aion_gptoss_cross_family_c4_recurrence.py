#!/usr/bin/env python3
"""Measure whether fourth-expert activation regions recur across prompt families."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


WIDTH = 2880
SIMILARITY_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def load_capture(root: Path) -> list[dict]:
    rows = []
    for metadata_path in sorted(root.glob("position-*-layer-*.json")):
        metadata = json.loads(metadata_path.read_text())
        route = metadata.get("route", [])
        if len(route) != 4:
            continue
        stem = metadata_path.with_suffix("")
        arrays = {}
        for name in ("router", "ffn", "output", "residual"):
            path = Path(f"{stem}-{name}.bin")
            if digest(path) != metadata[f"{name}_sha256"]:
                raise SystemExit(f"capture hash mismatch: {path}")
            value = np.fromfile(path, dtype="<f4")
            if value.size != WIDTH:
                raise SystemExit(f"capture width mismatch: {path}")
            arrays[name] = value.astype(np.float64)
        rows.append({
            "position": int(metadata["position"]),
            "layer": int(metadata["layer"]),
            "expert": int(route[3]),
            "gate": float(metadata["gates"][3]),
            **arrays,
        })
    if not rows:
        raise SystemExit(f"no complete four-expert captures found in {root}")
    return rows


def unit(values: np.ndarray) -> np.ndarray:
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-30)


def percentile(values: list[float], q: float) -> float | None:
    return None if not values else float(np.percentile(values, q))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-capture", type=Path, required=True)
    parser.add_argument("--development-capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-relative-l2", type=float, default=0.02)
    parser.add_argument("--minimum-similarity", type=float, default=0.80)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    training = load_capture(args.training_capture)
    development = load_capture(args.development_capture)
    training_by_expert: dict[tuple[int, int], list[dict]] = {}
    for row in training:
        training_by_expert.setdefault((row["layer"], row["expert"]), []).append(row)

    observations = []
    for row in development:
        candidates = training_by_expert.get((row["layer"], row["expert"]), [])
        if not candidates:
            observations.append({
                "position": row["position"], "layer": row["layer"],
                "expert": row["expert"], "identity_covered": False,
            })
            continue
        router = unit(np.stack([candidate["router"] for candidate in candidates]))
        ffn = unit(np.stack([candidate["ffn"] for candidate in candidates]))
        router_query = unit(row["router"][None, :])[0]
        ffn_query = unit(row["ffn"][None, :])[0]
        router_similarity = router @ router_query
        ffn_similarity = ffn @ ffn_query
        joint_similarity = (router_similarity + ffn_similarity) / 2.0
        nearest_index = int(np.argmax(joint_similarity))
        nearest = candidates[nearest_index]
        # The stored residual is the exact gated four-expert contribution.  The
        # balanced C4 datasets provide individual omitted targets, but these
        # captures do not.  A prototype correction therefore uses the exact
        # top-three counterfactual magnitude only as a post-hoc error bound;
        # no approximate value is injected into the model here.
        counterfactual = json.loads(
            next(args.development_capture.glob(
                f"position-{row['position']}-layer-{row['layer']}.json"
            )).read_text()
        )["counterfactuals"]["3"]
        observations.append({
            "position": row["position"], "layer": row["layer"],
            "expert": row["expert"], "identity_covered": True,
            "training_examples": len(candidates),
            "nearest_training_position": nearest["position"],
            "router_cosine": float(router_similarity[nearest_index]),
            "ffn_cosine": float(ffn_similarity[nearest_index]),
            "joint_cosine": float(joint_similarity[nearest_index]),
            "drop_e4_output_relative_l2": float(
                counterfactual["output_relative_l2"]
            ),
        })

    covered = [row for row in observations if row["identity_covered"]]
    recurrence = {
        str(threshold): {
            "development_calls": sum(
                row["joint_cosine"] >= threshold for row in covered
            ),
            "development_traffic_fraction": sum(
                row["joint_cosine"] >= threshold for row in covered
            ) / len(development),
        }
        for threshold in SIMILARITY_THRESHOLDS
    }
    region_rows = [
        row for row in covered if row["joint_cosine"] >= args.minimum_similarity
    ]
    region_drop_errors = [row["drop_e4_output_relative_l2"] for row in region_rows]
    report = {
        "schema": "aion.gptoss-120b-cross-family-c4-recurrence.v1",
        "status": "MEASURED_CROSS_FAMILY_C4_RECURRENCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_capture": str(args.training_capture.resolve()),
        "development_capture": str(args.development_capture.resolve()),
        "training_rows": len(training),
        "development_rows": len(development),
        "identity_covered_rows": len(covered),
        "identity_coverage_fraction": len(covered) / len(development),
        "similarity_thresholds": recurrence,
        "declared_region_similarity": args.minimum_similarity,
        "declared_region_rows": len(region_rows),
        "declared_region_traffic_fraction": len(region_rows) / len(development),
        "declared_region_drop_e4_relative_l2_p50": percentile(
            region_drop_errors, 50
        ),
        "declared_region_drop_e4_relative_l2_p95": percentile(
            region_drop_errors, 95
        ),
        "maximum_relative_l2_for_future_correction": args.maximum_relative_l2,
        "observations": observations,
        "training_capture_tree_sha256": canonical({
            path.name: digest(path) for path in sorted(args.training_capture.iterdir())
        }),
        "development_capture_tree_sha256": canonical({
            path.name: digest(path) for path in sorted(args.development_capture.iterdir())
        }),
        "claim_boundary": (
            "This report measures cross-family identity and activation recurrence only. "
            "The stored top-three counterfactual bounds the error of dropping E4; no C4 "
            "correction is trained or injected, selection and holdout prompts remain sealed, "
            "and no model-quality or tokens-per-second improvement is claimed."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "training_rows", "development_rows",
        "identity_coverage_fraction", "declared_region_traffic_fraction",
        "declared_region_drop_e4_relative_l2_p50",
        "declared_region_drop_e4_relative_l2_p95", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
