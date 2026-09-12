#!/usr/bin/env python3
"""Build teacher-queried local augmentation for a route-concentrated student."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore,
)


WIDTH = 2880


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--warehouse-manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--augmentations", type=int, default=16)
    parser.add_argument("--activation-rank", type=int, default=32)
    parser.add_argument("--perturbation-scale", type=float, default=0.10)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--seed", type=int, default=12012026)
    parser.add_argument("--training-family", action="append", default=[])
    args = parser.parse_args()
    if args.dataset.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")
    manifest = json.loads(args.dataset_manifest.read_text())
    source_path = Path(manifest["dataset_path"])
    if digest(source_path) != manifest["dataset_sha256"]:
        raise SystemExit("source dataset hash mismatch")
    arrays = dict(np.load(source_path))
    rows = manifest["rows"]
    selected = np.asarray([
        index for index, row in enumerate(rows)
        if row["split"] == "train" and int(row["layer"]) == args.layer
        and (not args.training_family or row["family_id"] in args.training_family)
    ])
    if len(selected) < 16:
        raise SystemExit("insufficient layer-specific training anchors")
    activations = np.asarray(arrays["router"], dtype=np.float32)[selected]
    mean = activations.mean(0, dtype=np.float64)
    centered = activations.astype(np.float64) - mean
    _, _, vectors = np.linalg.svd(centered, full_matrices=False)
    rank = min(args.activation_rank, len(vectors))
    basis = vectors[:rank].astype(np.float32)
    coordinates = centered @ basis.T
    coordinate_scale = np.maximum(coordinates.std(0), 1e-5).astype(np.float32)
    rng = np.random.default_rng(args.seed)

    augmented_inputs: list[np.ndarray] = []
    augmented_targets: list[np.ndarray] = []
    augmented_experts: list[int] = []
    augmented_gates: list[float] = []
    augmented_anchors: list[int] = []
    teacher_timings: list[float] = []
    store = GptOssExpertFrameStore(args.warehouse_manifest, 512 * 1024 * 1024)
    native = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    with tempfile.TemporaryDirectory(prefix="aion-route-student-augment-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_one_expert_contribution_batch
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        by_expert: dict[int, list[tuple[int, np.ndarray, float]]] = {}
        for local_index, source_index in enumerate(selected):
            row = rows[int(source_index)]
            expert = int(row["route"][3])
            gate = float(row["gates"][3])
            noise = rng.normal(size=(args.augmentations, rank)).astype(np.float32)
            offsets = ((noise * coordinate_scale * args.perturbation_scale) @ basis)
            values = np.ascontiguousarray(activations[local_index] + offsets,
                                          dtype=np.float32)
            by_expert.setdefault(expert, []).extend(
                (local_index, value, gate) for value in values
            )
        for expert, work in sorted(by_expert.items()):
            value = store.get_layer_route_parallel(args.layer, [expert], workers=1)[0]
            blobs = [value[projection][kind] for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * 6)(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references
            ])
            for start in range(0, len(work), 64):
                chunk = work[start:start + 64]
                inputs = np.ascontiguousarray(np.stack([item[1] for item in chunk]),
                                              dtype=np.float32)
                gates = np.ascontiguousarray([item[2] for item in chunk], dtype=np.float32)
                outputs = np.empty_like(inputs)
                elapsed = ctypes.c_double()
                status = function(
                    inputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                    gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), len(chunk),
                    outputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    args.threads, ctypes.byref(elapsed),
                )
                if status:
                    raise RuntimeError(f"teacher expert batch status {status}")
                teacher_timings.append(elapsed.value)
                for item, output in zip(chunk, outputs, strict=True):
                    augmented_anchors.append(item[0])
                    augmented_inputs.append(item[1])
                    augmented_targets.append(output.copy())
                    augmented_experts.append(expert)
                    augmented_gates.append(item[2])
            _ = references
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.dataset,
        router=np.stack(augmented_inputs).astype("<f4"),
        target=np.stack(augmented_targets).astype("<f4"),
        expert=np.asarray(augmented_experts, dtype="<i4"),
        gate=np.asarray(augmented_gates, dtype="<f4"),
        anchor=np.asarray(augmented_anchors, dtype="<i4"),
        activation_mean=mean.astype("<f4"),
        activation_basis=basis.astype("<f4"),
        activation_scale=coordinate_scale.astype("<f4"),
    )
    report = {
        "schema": "aion.gptoss-120b-route-concentrated-augmentation.v1",
        "status": "READY_FOR_ROUTE_CONCENTRATED_TRAINING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True,
        "layer": args.layer,
        "training_anchors": len(selected),
        "training_families": sorted({rows[int(index)]["family_id"]
                                     for index in selected}),
        "unique_omitted_experts": len(by_expert),
        "augmentations_per_anchor": args.augmentations,
        "augmented_rows": len(augmented_inputs),
        "activation_rank": rank,
        "perturbation_scale": args.perturbation_scale,
        "seed": args.seed,
        "teacher_batch_ms_p50": float(np.median(teacher_timings)),
        "teacher_batch_ms_p95": float(np.percentile(teacher_timings, 95)),
        "dataset_path": str(args.dataset.resolve()),
        "dataset_sha256": digest(args.dataset),
        "source_manifest_canonical_sha256": manifest["canonical_sha256"],
        "warehouse_manifest_sha256": digest(args.warehouse_manifest),
        "authorization_sha256": digest(args.authorization),
        "contains_prompt_text": False,
        "contains_personal_or_customer_data": False,
        "claim_boundary": (
            "Synthetic activation perturbations are training data only. Every target was "
            "recalculated by the original SD-backed fourth expert. Calibration and held-out "
            "families were neither perturbed nor opened by this builder."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "training_anchors", "unique_omitted_experts", "augmented_rows",
        "teacher_batch_ms_p50", "dataset_sha256", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
