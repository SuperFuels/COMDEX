#!/usr/bin/env python3
"""Evaluate a real-anchor, expert-conditioned local correction cartridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def percentile(values: np.ndarray, q: float) -> float:
    return float(np.percentile(values, q))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--augmentation-report", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--fit-family", default="arithmetic_real_48")
    parser.add_argument("--selection-family", default="extraction_real_48")
    parser.add_argument("--development-family", default="reasoning_real_40")
    args = parser.parse_args()
    if args.cartridge.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    source = json.loads(args.source_manifest.read_text())
    source_path = Path(source["dataset_path"])
    if digest(source_path) != source["dataset_sha256"]:
        raise SystemExit("source dataset hash mismatch")
    augmentation = json.loads(args.augmentation_report.read_text())
    augmented_path = Path(augmentation["dataset_path"])
    if digest(augmented_path) != augmentation["dataset_sha256"]:
        raise SystemExit("augmentation dataset hash mismatch")
    if augmentation["training_families"] != [args.fit_family]:
        raise SystemExit("augmentation was not isolated to the declared fit family")
    arrays = dict(np.load(source_path))
    augmented = dict(np.load(augmented_path))
    rows = source["rows"]
    fit = np.asarray([i for i, row in enumerate(rows)
                      if int(row["layer"]) == args.layer
                      and row["family_id"] == args.fit_family])
    selection = np.asarray([i for i, row in enumerate(rows)
                            if int(row["layer"]) == args.layer
                            and row["family_id"] == args.selection_family])
    development = np.asarray([i for i, row in enumerate(rows)
                              if int(row["layer"]) == args.layer
                              and row["family_id"] == args.development_family])
    basis = np.asarray(augmented["activation_basis"], dtype=np.float64)
    mean = np.asarray(augmented["activation_mean"], dtype=np.float64)
    scale = np.maximum(np.asarray(augmented["activation_scale"], dtype=np.float64), 1e-8)
    router = np.asarray(arrays["router"], dtype=np.float64)
    coordinates = ((router - mean) @ basis.T) / scale
    fit_targets = np.asarray(arrays["omitted"], dtype=np.float64)[fit]
    fit_experts = np.asarray([int(rows[i]["route"][3]) for i in fit])
    aug_coordinates = ((np.asarray(augmented["router"], dtype=np.float64) - mean)
                       @ basis.T) / scale
    aug_targets = np.asarray(augmented["target"], dtype=np.float64)
    aug_anchor = np.asarray(augmented["anchor"], dtype=np.int64)

    configurations = [(rank, ridge) for rank in (4, 8, 12, 16, 24)
                      for ridge in (1e-3, 1e-2, 1e-1)]

    def compile_candidate(rank: int, ridge: float) -> list[np.ndarray]:
        models = []
        identity = np.eye(rank)
        for anchor_index in range(len(fit)):
            chosen = aug_anchor == anchor_index
            x = aug_coordinates[chosen, :rank] - coordinates[fit[anchor_index], :rank]
            y = aug_targets[chosen] - fit_targets[anchor_index]
            models.append(np.linalg.solve(x.T @ x + ridge * identity, x.T @ y))
        return models

    def evaluate(indices: np.ndarray, models: list[np.ndarray], rank: int) -> tuple[np.ndarray, int]:
        errors = []
        covered = 0
        for index in indices:
            expert = int(rows[int(index)]["route"][3])
            candidates = np.flatnonzero(fit_experts == expert)
            if not len(candidates):
                continue
            distances = np.sum((coordinates[fit[candidates], :rank]
                                - coordinates[index, :rank]) ** 2, axis=1)
            anchor_index = int(candidates[int(np.argmin(distances))])
            delta = coordinates[index, :rank] - coordinates[fit[anchor_index], :rank]
            prediction = fit_targets[anchor_index] + delta @ models[anchor_index]
            layer_output = arrays["ffn"][index].astype(np.float64) + arrays["full"][index]
            error = np.linalg.norm(prediction - arrays["omitted"][index]) / max(
                np.linalg.norm(layer_output), 1e-30,
            )
            errors.append(error)
            covered += 1
        return np.asarray(errors), covered

    candidates = []
    compiled = []
    for rank, ridge in configurations:
        models = compile_candidate(rank, ridge)
        errors, covered = evaluate(selection, models, rank)
        candidates.append({
            "rank": rank, "ridge": ridge, "covered_rows": covered,
            "selection_rows": len(selection),
            "selection_coverage": covered / len(selection),
            "selection_relative_l2_p50": percentile(errors, 50),
            "selection_relative_l2_p95": percentile(errors, 95),
            "selection_safe_rows": int(np.sum(errors <= 0.02)),
        })
        compiled.append(models)
    chosen_index = min(range(len(candidates)),
                       key=lambda i: candidates[i]["selection_relative_l2_p95"])
    chosen = candidates[chosen_index]
    models = compiled[chosen_index]
    development_errors, development_covered = evaluate(
        development, models, int(chosen["rank"]),
    )
    timings = []
    if development_covered:
        for _ in range(1000):
            started = time.perf_counter_ns()
            _ = evaluate(development[:1], models, int(chosen["rank"]))
            timings.append((time.perf_counter_ns() - started) / 1e6)
    object_models = np.empty(len(models), dtype=object)
    object_models[:] = models
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.cartridge, basis=basis[:int(chosen["rank"])].astype("<f4"),
        mean=mean.astype("<f4"), scale=scale[:int(chosen["rank"])].astype("<f4"),
        fit_indices=fit.astype("<i4"), fit_experts=fit_experts.astype("<i4"),
        fit_coordinates=coordinates[fit, :int(chosen["rank"])].astype("<f4"),
        fit_targets=fit_targets.astype("<f4"), models=object_models,
    )
    safe = int(np.sum(development_errors <= 0.02))
    accepted = {
        "development_nonzero_coverage": development_covered > 0,
        "development_oracle_safe_coverage_at_least_10_percent": safe / len(development) >= 0.10,
        "development_p95_at_most_two_percent": (
            development_covered == len(development)
            and percentile(development_errors, 95) <= 0.02
        ),
    }
    report = {
        "schema": "aion.gptoss-120b-route-concentrated-local-gate.v1",
        "status": ("ADVANCE_ROUTE_CONCENTRATED_LOCAL" if all(accepted.values())
                   else "STOP_ROUTE_CONCENTRATED_LOCAL"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "exact_fallback_required": True,
        "layer": args.layer, "fit_family": args.fit_family,
        "selection_family": args.selection_family,
        "development_family": args.development_family,
        "candidates": candidates, "selected": chosen,
        "development_rows": len(development),
        "development_covered_rows": development_covered,
        "development_coverage": development_covered / len(development),
        "development_safe_rows": safe,
        "development_oracle_safe_coverage": safe / len(development),
        "development_relative_l2_p50": percentile(development_errors, 50),
        "development_relative_l2_p95": percentile(development_errors, 95),
        "development_relative_l2_max": float(np.max(development_errors)),
        "calculation_ms_p50": float(np.median(timings)) if timings else None,
        "calculation_ms_p95": percentile(np.asarray(timings), 95) if timings else None,
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_bytes": args.cartridge.stat().st_size,
        "cartridge_sha256": digest(args.cartridge),
        "source_manifest_canonical_sha256": source["canonical_sha256"],
        "augmentation_canonical_sha256": augmentation["canonical_sha256"],
        "acceptance": accepted,
        "claim_boundary": (
            "The cartridge uses exact teacher queries around real arithmetic anchors. "
            "Extraction selected rank and regularization; reasoning remained unseen until "
            "the final gate. Missing expert identities require exact fallback. Reported safe "
            "coverage is an oracle bound based on post-calculation held-out error."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "selected", "development_covered_rows",
        "development_safe_rows", "development_relative_l2_p50",
        "development_relative_l2_p95", "cartridge_bytes", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
