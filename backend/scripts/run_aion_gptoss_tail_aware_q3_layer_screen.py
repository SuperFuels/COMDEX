#!/usr/bin/env python3
"""Screen tail-aware fourth-expert Q3 gate/up across selected real layers."""
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
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)


WIDTH = 2880
PADDED = 3072


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def load_rows(root: Path, layer: int) -> list[dict]:
    rows = []
    for path in sorted(root.glob(f"position-*-layer-{layer}.json"),
                       key=lambda item: int(item.name.split("-")[1])):
        metadata = json.loads(path.read_text())
        stem = path.with_suffix("")
        values = {name: np.fromfile(Path(str(stem) + f"-{name}.bin"), dtype="<f4")
                  for name in ("ffn", "router", "output")}
        if any(value.size != WIDTH for value in values.values()):
            raise SystemExit(f"capture width mismatch: {path}")
        rows.append({"path": path, "metadata": metadata, **values})
    if not rows:
        raise SystemExit(f"no layer {layer} rows in {root}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--capture", type=Path, action="append", required=True)
    parser.add_argument("--layers", default="0,6,12,18,24,30,35")
    parser.add_argument("--thresholds", default="0.10,0.15,0.20,0.25")
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    layers = sorted({int(value) for value in args.layers.split(",")})
    thresholds = sorted({float(value) for value in args.thresholds.split(",")})
    store = GptOssExpertFrameStore(args.manifest, 768 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    observations = []

    with tempfile.TemporaryDirectory(prefix="aion-tail-aware-q3-") as temporary:
        temporary_root = Path(temporary)
        converter = temporary_root / "convert"
        library_path = temporary_root / "moe.dylib"
        common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([*common, str(native / "gptoss_mxfp4_to_padded_k.cpp"),
                        *libraries, "-o", str(converter)], check=True)
        subprocess.run([*common, "-dynamiclib",
                        str(native / "gptoss_persistent_moe_library.cpp"),
                        *libraries, "-o", str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_moe_finish_top3_mxfp4_q3_k
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        converted: dict[tuple[int, int, str], bytes] = {}

        for layer in layers:
            for capture in args.capture:
                for row in load_rows(capture, layer):
                    metadata = row["metadata"]
                    experts = store.get_layer_route_parallel(layer, metadata["route"], workers=4)
                    blobs = []
                    original_bytes = 0
                    candidate_bytes = 0
                    for route_position, (expert_id, expert) in enumerate(
                            zip(metadata["route"], experts, strict=True)):
                        for projection in ("gate", "up", "down"):
                            weight = expert[projection]["weight"]
                            original_bytes += len(weight)
                            compact = route_position == 3 and projection in ("gate", "up")
                            if compact:
                                key = (layer, int(expert_id), projection)
                                if key not in converted:
                                    source = temporary_root / f"l{layer}-e{expert_id}-{projection}.mxfp4"
                                    destination = temporary_root / f"l{layer}-e{expert_id}-{projection}.q3k"
                                    source.write_bytes(weight)
                                    subprocess.run([
                                        str(converter), str(source), str(destination), "q3_k",
                                        str(WIDTH), str(args.threads),
                                    ], check=True, stdout=subprocess.DEVNULL)
                                    converted[key] = destination.read_bytes()
                                weight = converted[key]
                            candidate_bytes += len(weight)
                            bias = expert[projection]["bias"]
                            if compact:
                                bias = bytes(bias) + bytes((PADDED - WIDTH) * 4)
                            blobs.extend((weight, bias))
                    references, pointers = ctypes_component_pointer_array(blobs)
                    gates = np.asarray(metadata["gates"], dtype=np.float32)
                    destination = np.empty(WIDTH, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = function(
                        row["ffn"].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        row["router"].ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                        gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 3,
                        destination.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"Q3 route status {status}")
                    error = float(np.linalg.norm(destination.astype(np.float64)
                                                 - row["output"].astype(np.float64)) /
                                  max(np.linalg.norm(row["output"]), 1e-30))
                    observations.append({
                        "family": capture.name, "capture": row["path"].name,
                        "layer": layer, "expert": int(metadata["route"][3]),
                        "fourth_gate": float(gates[3]), "output_relative_l2": error,
                        "argmax_equal": int(np.argmax(destination)) == int(np.argmax(row["output"])),
                        "calculation_ms": elapsed.value * 1000.0,
                        "original_weight_bytes": original_bytes,
                        "candidate_weight_bytes": candidate_bytes,
                    })
                    _ = references
            print(f"layer {layer} complete", flush=True)

    threshold_rows = []
    for threshold in thresholds:
        admitted = [row for row in observations if row["fourth_gate"] <= threshold]
        errors = [row["output_relative_l2"] for row in admitted]
        threshold_rows.append({
            "threshold": threshold, "admitted": len(admitted),
            "coverage": len(admitted) / len(observations),
            "p50": float(np.median(errors)) if errors else None,
            "p95": float(np.percentile(errors, 95)) if errors else None,
            "maximum": max(errors) if errors else None,
            "all_argmax_equal": all(row["argmax_equal"] for row in admitted),
        })
    per_layer = {}
    for layer in layers:
        rows = [row for row in observations if row["layer"] == layer]
        errors = [row["output_relative_l2"] for row in rows]
        per_layer[str(layer)] = {
            "rows": len(rows), "p50": float(np.median(errors)),
            "p95": float(np.percentile(errors, 95)), "maximum": max(errors),
            "all_argmax_equal": all(row["argmax_equal"] for row in rows),
        }
    advancing = [row for row in threshold_rows if row["admitted"] >= 6
                 and row["p95"] is not None and row["p95"] <= .02
                 and row["all_argmax_equal"]]
    report = {
        "schema": "aion.gptoss-120b-tail-aware-q3-layer-screen.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ADVANCE_TAIL_AWARE_Q3" if advancing else "STOP_TAIL_AWARE_Q3",
        "model": "GPT-OSS 120B Q4_K_M", "quality_track": True,
        "layers": layers, "families": [str(path.resolve()) for path in args.capture],
        "rows": len(observations), "thresholds": threshold_rows,
        "per_layer": per_layer, "observations": observations,
        "advancing_thresholds": [row["threshold"] for row in advancing],
        "promotion_gate": {"minimum_admitted_rows": 6, "maximum_p95": .02,
                           "all_argmax_equal": True},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "Offline seven-layer screen on two public capture families. Only gate/up of the "
            "fourth selected expert uses Q3_K; all other weights, routes and gates remain "
            "original. Thresholds model exact fallback above the gate. Passing is only a "
            "local numerical admission signal, not full-model quality or token speed."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "thresholds": threshold_rows,
                      "canonical_sha256": report["canonical_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
