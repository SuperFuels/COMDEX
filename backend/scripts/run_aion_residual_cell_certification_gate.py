#!/usr/bin/env python3
"""Bound useful coverage of a compact residual calculator before selector work."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from backend.scripts.train_aion_top1_residual_mlp import ResidualMLP, features


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", default="semantic_holdout")
    parser.add_argument("--maximum-relative-l2", type=float, default=0.02)
    parser.add_argument("--minimum-oracle-coverage", type=float, default=0.05)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.dataset_manifest.read_text())
    training = json.loads(args.training_report.read_text())
    dataset_path = Path(manifest["dataset_path"])
    if digest(dataset_path) != manifest["dataset_sha256"]:
        raise SystemExit("dataset hash mismatch")
    if digest(args.cartridge) != training["cartridge_sha256"]:
        raise SystemExit("cartridge hash mismatch")
    arrays = dict(np.load(dataset_path))
    rows = manifest["rows"]
    selected = np.asarray([
        index for index, row in enumerate(rows) if row["split"] == args.split
    ])
    if not len(selected):
        raise SystemExit("requested split is empty")
    x = features(arrays, rows)
    # The file is generated locally under a hash-bound authorization.  Its hash
    # is verified above before permitting PyTorch deserialization.
    cartridge = torch.load(args.cartridge, map_location="cpu", weights_only=False)
    model = ResidualMLP(x.shape[1], int(cartridge["selected"]["hidden"]))
    model.load_state_dict(cartridge["state_dict"])
    model.eval()
    normalized = ((x[selected] - cartridge["feature_mean"]) /
                  cartridge["feature_scale"]).astype(np.float32)
    with torch.no_grad():
        prediction = model(torch.from_numpy(normalized)).numpy()
    target = np.asarray(arrays["omitted"], dtype=np.float32)[selected]
    layer_output = (np.asarray(arrays["ffn"], dtype=np.float32) +
                    np.asarray(arrays["full"], dtype=np.float32))[selected]
    errors = np.linalg.norm(prediction - target, axis=1) / np.maximum(
        np.linalg.norm(layer_output, axis=1), 1e-30,
    )
    safe = errors <= args.maximum_relative_l2
    coverage = float(np.mean(safe))
    status = ("ADVANCE_TO_DEPLOYABLE_SELECTOR" if
              coverage >= args.minimum_oracle_coverage else
              "STOP_RESIDUAL_CELL_NO_SAFE_COVERAGE")
    observations = [{
        "position": int(rows[index]["position"]),
        "layer": int(rows[index]["layer"]),
        "relative_l2": float(error),
        "oracle_safe": bool(is_safe),
    } for index, error, is_safe in zip(selected, errors, safe, strict=True)]
    report = {
        "schema": "aion.gptoss-120b-residual-cell-certification-bound.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True,
        "split": args.split,
        "rows": len(selected),
        "maximum_relative_l2": args.maximum_relative_l2,
        "minimum_oracle_coverage": args.minimum_oracle_coverage,
        "oracle_safe_rows": int(np.sum(safe)),
        "oracle_coverage": coverage,
        "relative_l2_p50": float(np.median(errors)),
        "relative_l2_p95": float(np.percentile(errors, 95)),
        "relative_l2_max": float(np.max(errors)),
        "observations": observations,
        "dataset_manifest_canonical_sha256": manifest["canonical_sha256"],
        "training_report_canonical_sha256": training["canonical_sha256"],
        "cartridge_sha256": digest(args.cartridge),
        "exact_fallback_required": True,
        "claim_boundary": (
            "Oracle coverage is an optimistic existence bound computed from the true "
            "held-out error after evaluation. A deployable runtime cannot observe that "
            "error without calculating the omitted original expert. Zero oracle coverage "
            "proves that no confidence selector can safely admit this cartridge on the "
            "evaluated family under the declared error ceiling."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "rows", "oracle_safe_rows", "oracle_coverage",
        "relative_l2_p50", "relative_l2_p95", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
