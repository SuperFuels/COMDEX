#!/usr/bin/env python3
"""Evaluate a frozen GHX route-crystal Shadow Expert hypothesis.

The candidate is deliberately narrow.  It uses the normalized router activation
and the four gated expert identities as a compact route crystal.  Configuration
was frozen after an exploratory diagnostic, so only separately captured rows may
be used for the reported validation decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


WIDTH = 2880
LAYER = 6
ROUTE_WEIGHT = 16.0
RIDGE = 1e-6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def vector(path: str | Path) -> np.ndarray:
    value = np.fromfile(path, dtype="<f4").astype(np.float64)
    if value.size != WIDTH:
        raise SystemExit(f"capture width mismatch: {path}")
    return value


def route_vector(record: dict) -> np.ndarray:
    value = np.zeros(128, dtype=np.float64)
    for expert, gate in zip(record["route"], record["gates"]):
        value[int(expert)] = float(gate)
    return value


def router_vector(record: dict) -> np.ndarray:
    value = vector(record["router_path"])
    return value / max(np.linalg.norm(value), np.finfo(np.float64).tiny)


def kernel(left_router: np.ndarray, left_route: np.ndarray,
           right_router: np.ndarray, right_route: np.ndarray) -> np.ndarray:
    return (left_router @ right_router.T +
            ROUTE_WEIGHT * (left_route @ right_route.T) + 1.0)


def relative_l2(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.linalg.norm(prediction - target) /
                 max(np.linalg.norm(target), np.finfo(np.float64).tiny))


def capture_record(root: Path, layer: int) -> dict:
    stem = root / f"position-0-layer-{layer}"
    metadata_path = Path(f"{stem}.json")
    metadata = json.loads(metadata_path.read_text())
    record = {
        "family_id": root.name,
        "layer": layer,
        "route": metadata["route"],
        "gates": metadata["gates"],
        "router_path": str(Path(f"{stem}-router.bin").resolve()),
        "residual_path": str(Path(f"{stem}-residual.bin").resolve()),
        "metadata_path": str(metadata_path.resolve()),
    }
    for name in ("router", "residual"):
        path = Path(record[f"{name}_path"])
        expected = metadata[f"{name}_sha256"]
        if sha256(path) != expected:
            raise SystemExit(f"fresh validation {name} hash mismatch")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--validation-capture", type=Path, action="append", required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if not authorization.get("authorized"):
        raise SystemExit("training is not authorized")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("manifest is not training-ready")

    split_by_family = {
        family: split
        for split, families in manifest["family_disjoint_split"].items()
        for family in families
    }
    train = []
    development = []
    for family in manifest["families"]:
        for record in family["records"]:
            if record["layer"] != LAYER:
                continue
            for name in ("router", "residual"):
                if sha256(Path(record[f"{name}_path"])) != record[f"{name}_sha256"]:
                    raise SystemExit(f"manifest {name} hash mismatch")
            item = {**record, "family_id": family["family_id"],
                    "split": split_by_family[family["family_id"]]}
            (train if item["split"] == "train" else development).append(item)
    validation = [capture_record(path, LAYER) for path in args.validation_capture]

    train_router = np.stack([router_vector(row) for row in train])
    train_route = np.stack([route_vector(row) for row in train])
    targets = np.stack([vector(row["residual_path"]) for row in train])
    gram = kernel(train_router, train_route, train_router, train_route)
    alpha = np.linalg.solve(gram + RIDGE * np.eye(len(train)), targets)

    def evaluate(rows: list[dict]) -> list[dict]:
        observations = []
        for row in rows:
            prediction = kernel(router_vector(row)[None, :],
                                route_vector(row)[None, :],
                                train_router, train_route)[0] @ alpha
            observations.append({
                "family_id": row["family_id"],
                "split": row.get("split", "fresh_validation"),
                "layer": LAYER,
                "route": row["route"],
                "relative_l2": relative_l2(prediction, vector(row["residual_path"])),
            })
        return observations

    timings = []
    sample_router = router_vector(validation[0])[None, :]
    sample_route = route_vector(validation[0])[None, :]
    for _ in range(300):
        began = time.perf_counter_ns()
        kernel(sample_router, sample_route, train_router, train_route)[0] @ alpha
        timings.append((time.perf_counter_ns() - began) / 1e6)

    validation_observations = evaluate(validation)
    development_observations = evaluate(development)
    validation_errors = [row["relative_l2"] for row in validation_observations]
    validation_p95 = sorted(validation_errors)[int(.95 * (len(validation_errors) - 1))]
    p50_ms = statistics.median(timings)
    p95_ms = sorted(timings)[int(.95 * (len(timings) - 1))]

    # A single accepted layer among the twelve measured layers saves 1/12 of
    # route traffic: 12/11 = 1.0909x, below the predeclared >1.10x rung.
    projected_traffic_reduction = 12 / 11
    numerical_passed = validation_p95 <= .02 and max(validation_errors) <= .05
    latency_passed = p50_ms < 1.0
    traffic_passed = projected_traffic_reduction > 1.10
    status = ("ADVANCE_EXPERIMENTAL_RUNG" if numerical_passed and latency_passed
              and traffic_passed else "STOP_GHX_ROUTE_CRYSTAL")

    args.cartridge.mkdir(parents=True, exist_ok=False)
    alpha32 = alpha.astype(np.float32)
    routers32 = train_router.astype(np.float32)
    routes32 = train_route.astype(np.float32)
    for name, value in (("alpha-f32.bin", alpha32),
                        ("router-prototypes-f32.bin", routers32),
                        ("route-glyphs-f32.bin", routes32)):
        value.tofile(args.cartridge / name)
    experts = sorted({int(expert) for row in train for expert in row["route"]})
    edge_counts: dict[tuple[int, int], int] = {}
    for row in train:
        for left in row["route"]:
            for right in row["route"]:
                if left < right:
                    edge_counts[(int(left), int(right))] = edge_counts.get(
                        (int(left), int(right)), 0) + 1
    ghx = {
        "schema": "aion.ghx-expert-route-crystal.v1",
        "kind": "shadow_expert_route_memory",
        "layer": LAYER,
        "nodes": [{"id": f"expert:{expert}", "kind": "model_expert"}
                  for expert in experts],
        "edges": [{"source": f"expert:{left}", "target": f"expert:{right}",
                   "co_route_count": count}
                  for (left, right), count in sorted(edge_counts.items())],
        "numerical_role": (
            "Audit and route identity. Numerical selection uses the bound gated "
            "expert vector; graph diffusion was diagnostic-only and was not retained."
        ),
    }
    ghx["canonical_sha256"] = canonical(ghx)
    (args.cartridge / "route-crystal.ghx.json").write_text(
        json.dumps(ghx, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schema": "aion.ghx-route-crystal-cartridge.v1",
        "quality_track": True,
        "exact_fallback_required": True,
        "layer": LAYER,
        "configuration": {"kernel": "linear", "router_normalized": True,
                          "route_weight": ROUTE_WEIGHT, "ridge": RIDGE},
        "source_manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": sha256(args.authorization),
        "files": {path.name: sha256(path) for path in args.cartridge.iterdir()},
    }
    receipt["canonical_sha256"] = canonical(receipt)
    (args.cartridge / "cartridge.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    report = {
        "schema": "aion.shadow-expert-ghx-route-crystal-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "quality_track": True,
        "exact_fallback_required": True,
        "layer": LAYER,
        "configuration_frozen_before_fresh_validation": True,
        "configuration": receipt["configuration"],
        "training_rows": len(train),
        "fresh_validation_rows": len(validation),
        "fresh_validation_relative_l2_p50": statistics.median(validation_errors),
        "fresh_validation_relative_l2_p95": validation_p95,
        "fresh_validation_relative_l2_max": max(validation_errors),
        "calculation_ms_p50": p50_ms,
        "calculation_ms_p95": p95_ms,
        "projected_expert_traffic_reduction": projected_traffic_reduction,
        "acceptance": {
            "fresh_validation_p95_at_most_0_02": validation_p95 <= .02,
            "fresh_validation_max_at_most_0_05": max(validation_errors) <= .05,
            "calculation_p50_below_1ms": latency_passed,
            "projected_traffic_reduction_above_1_10x": traffic_passed,
        },
        "fresh_validation_observations": validation_observations,
        "development_observations": development_observations,
        "source_manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": sha256(args.authorization),
        "cartridge_receipt_sha256": sha256(args.cartridge / "cartridge.json"),
        "claim_boundary": (
            "Changed-arithmetic layer-6 microgate. Earlier holdouts were used during "
            "hypothesis development and are reported only as development diagnostics. "
            "Only separately captured rows determine numerical validation. No full-model "
            "speed, quality, or exactness claim is made."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "fresh_p95": validation_p95,
                      "fresh_max": max(validation_errors), "p50_ms": p50_ms,
                      "traffic_reduction": projected_traffic_reduction,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
