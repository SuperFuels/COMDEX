#!/usr/bin/env python3
"""Gate one cross-family local fourth-expert contribution prototype."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore,
)


WIDTH = 2880
ORIGINAL_EXPERT_BYTES = int(13.25 * 1024 * 1024)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def load(stem: Path) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    metadata_path = Path(f"{stem}.json")
    metadata = json.loads(metadata_path.read_text())
    values = []
    for name in ("router", "ffn", "output"):
        path = Path(f"{stem}-{name}.bin")
        if digest(path) != metadata[f"{name}_sha256"]:
            raise SystemExit(f"capture hash mismatch: {path}")
        value = np.fromfile(path, dtype="<f4")
        if value.size != WIDTH:
            raise SystemExit(f"capture width mismatch: {path}")
        values.append(value)
    return metadata, values[0], values[1], values[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--training-stem", type=Path, required=True)
    parser.add_argument("--development-stem", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--maximum-relative-l2", type=float, default=0.02)
    parser.add_argument("--maximum-cost-fraction", type=float, default=0.25)
    parser.add_argument("--fit-development-secant", action="store_true",
                        help="Fit a two-anchor affine refinement; development is then training, not validation")
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")

    training, training_x, training_ffn, _ = load(args.training_stem)
    development, development_x, _, development_output = load(args.development_stem)
    if training["layer"] != development["layer"]:
        raise SystemExit("captures have different layers")
    if len(training["route"]) != 4 or len(development["route"]) != 4:
        raise SystemExit("captures must contain unrestricted four-expert routes")
    if training["route"][3] != development["route"][3]:
        raise SystemExit("captures have different omitted expert identities")
    layer = int(training["layer"])
    expert = int(training["route"][3])

    source = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    original = store.get_layer_route_parallel(layer, [expert], workers=1)[0]
    blobs = [original[projection][kind]
             for projection in ("gate", "up", "down")
             for kind in ("weight", "bias")]
    references = [ctypes.c_char_p(blob) for blob in blobs]
    pointers = (ctypes.c_void_p * 6)(*[
        ctypes.cast(reference, ctypes.c_void_p).value for reference in references
    ])

    with tempfile.TemporaryDirectory(prefix="aion-local-c4-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        function = ctypes.CDLL(
            str(library_path)
        ).aion_gptoss_one_expert_contribution_batch
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        contributions = []
        exact_times = []
        for metadata, activation in (
                (training, training_x), (development, development_x)):
            gate = np.asarray([metadata["gates"][3]], dtype=np.float32)
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = function(
                activation.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"expert contribution failed: {status}")
            contributions.append(output)
            exact_times.append(elapsed.value)

    scale = np.float32(development["gates"][3] / training["gates"][3])
    secant_fields = {}
    if args.fit_development_secant:
        direction = development_x.astype(np.float64) - training_x.astype(np.float64)
        squared_length = float(direction @ direction)
        if squared_length <= 1e-30:
            raise SystemExit("secant anchors must have distinct activations")
        # Store a rank-one affine response to activation movement.  Both
        # endpoints are fitting data; interpolation error is NOT holdout evidence.
        secant_fields = {
            "activation_anchor": training_x.astype("<f4"),
            "secant_dual": (direction / squared_length).astype("<f4"),
            "secant_response": (contributions[1] / scale - contributions[0]).astype("<f4"),
        }
    timings = []
    for _ in range(10_000):
        started = time.perf_counter_ns()
        prediction = contributions[0] * scale
        if secant_fields:
            coordinate = np.float32(np.dot(
                development_x - secant_fields["activation_anchor"],
                secant_fields["secant_dual"],
            ))
            prediction = (contributions[0] + coordinate * secant_fields["secant_response"]) * scale
        timings.append((time.perf_counter_ns() - started) / 1e6)
    denominator = max(
        np.linalg.norm(development_output.astype(np.float64)), 1e-30,
    )
    drop_error = float(np.linalg.norm(
        contributions[1].astype(np.float64)
    ) / denominator)
    corrected_error = float(np.linalg.norm(
        prediction.astype(np.float64) - contributions[1].astype(np.float64)
    ) / denominator)
    prototype_bytes = int(contributions[0].nbytes + sum(value.nbytes for value in secant_fields.values()))
    cost_fraction = prototype_bytes / ORIGINAL_EXPERT_BYTES
    training_router_unit = training_x / max(np.linalg.norm(training_x), 1e-30)
    training_ffn_unit = training_ffn / max(np.linalg.norm(training_ffn), 1e-30)
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.cartridge,
        schema=np.asarray("aion.gptoss-120b-local-c4-cartridge.v2" if secant_fields else "aion.gptoss-120b-local-c4-cartridge.v1"),
        layer=np.asarray(layer, dtype="<i4"),
        expert=np.asarray(expert, dtype="<i4"),
        training_gate=np.asarray(training["gates"][3], dtype="<f4"),
        minimum_joint_cosine=np.asarray(0.80, dtype="<f4"),
        router_unit=training_router_unit.astype("<f4"),
        ffn_unit=training_ffn_unit.astype("<f4"),
        contribution=contributions[0].astype("<f4"),
        **secant_fields,
    )
    acceptance = {
        "development_relative_l2_at_most_limit": (
            corrected_error <= args.maximum_relative_l2
        ),
        "prototype_storage_fraction_at_most_limit": (
            cost_fraction <= args.maximum_cost_fraction
        ),
    }
    report = {
        "schema": "aion.gptoss-120b-local-c4-prototype-gate.v1",
        "status": ("ADVANCE_LOCAL_C4_TO_DOWNSTREAM_GATE"
                   if all(acceptance.values()) else "STOP_LOCAL_C4_PROTOTYPE"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True,
        "development_used_for_fitting": args.fit_development_secant,
        "layer": layer,
        "expert": expert,
        "training_position": int(training["position"]),
        "development_position": int(development["position"]),
        "drop_e4_output_relative_l2": drop_error,
        "prototype_c4_output_relative_l2": corrected_error,
        "relative_error_reduction": 1.0 - corrected_error / drop_error,
        "exact_e4_compute_ms": exact_times[1],
        "prototype_compute_ms_p50": float(np.median(timings)),
        "prototype_compute_ms_p95": float(np.percentile(timings, 95)),
        "prototype_bytes": prototype_bytes,
        "original_expert_declared_bytes": ORIGINAL_EXPERT_BYTES,
        "prototype_storage_fraction": cost_fraction,
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_sha256": digest(args.cartridge),
        "minimum_joint_cosine": 0.80,
        "maximum_relative_l2": args.maximum_relative_l2,
        "maximum_cost_fraction": args.maximum_cost_fraction,
        "acceptance": acceptance,
        "manifest_sha256": digest(args.manifest),
        "training_metadata_sha256": digest(Path(f"{args.training_stem}.json")),
        "development_metadata_sha256": digest(Path(f"{args.development_stem}.json")),
        "exact_e4_fallback_required": True,
        "claim_boundary": (
            "One cross-family layer/expert/activation-region prototype only. The C4 value "
            "is the gate-scaled stored contribution from one authentic training activation. "
            "The development activation was not used to fit it. This passes a local output "
            "and storage gate only; downstream routes, logits, tokens, semantic quality, "
            "coverage and full-generation speed are not established."
        ),
    }
    if args.fit_development_secant:
        report["status"] = "FROZEN_SECANT_REQUIRES_UNTOUCHED_VALIDATION"
        report["claim_boundary"] = (
            "A two-anchor rank-one affine correction fitted on the original training and "
            "previous development activations. The reported local error is training reconstruction, "
            "not accuracy evidence. No downstream certification or speed promotion. "
            "Requires untouched local and downstream validation with true-E4 fallback."
        )
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "layer", "expert", "drop_e4_output_relative_l2",
        "prototype_c4_output_relative_l2", "relative_error_reduction",
        "exact_e4_compute_ms", "prototype_compute_ms_p50", "prototype_bytes",
        "prototype_storage_fraction", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
