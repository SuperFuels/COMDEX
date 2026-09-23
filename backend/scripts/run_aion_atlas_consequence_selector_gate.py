#!/usr/bin/env python3
"""Use a frozen Expert Function Atlas only to select original experts.

The atlas never contributes approximate values to the layer output.  It predicts
the consequence of omitting a suffix of the unrestricted top-four route; every
retained contribution is calculated with the original SD-backed MXFP4 expert.
"""
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

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore
from backend.scripts.run_aion_expert_function_atlas_gate import digest, load_capture
from backend.scripts.run_aion_expert_function_taylor_atlas_gate import predict


WIDTH = 2880


def load_ffn(root: Path, rows: list[dict], layer: int) -> np.ndarray:
    values = []
    for row in rows:
        path = root / f"position-{row['position']}-layer-{layer}-ffn.bin"
        if digest(path) != row["ffn_sha256"]:
            raise SystemExit(f"capture hash mismatch: {path}")
        value = np.fromfile(path, dtype="<f4")
        if value.size != WIDTH:
            raise SystemExit(f"capture width mismatch: {path}")
        values.append(value)
    return np.stack(values)


def atlas_shape(cartridge: np.lib.npyio.NpzFile) -> dict:
    return {
        "mean": cartridge["mean"],
        "basis": cartridge["activation_basis"],
        "scale": cartridge["activation_scale"],
        "anchors": cartridge["anchors"],
        "anchor_coordinates": cartridge["anchor_coordinates"],
    }


def predicted_contributions(cartridge: np.lib.npyio.NpzFile, shape: dict,
                            activations: np.ndarray,
                            rows: list[dict]) -> np.ndarray:
    result = np.empty((len(rows), 4, WIDTH), dtype=np.float32)
    for route_position in range(4):
        experts = np.asarray([int(row["route"][route_position]) for row in rows])
        raw = predict(cartridge["atlas"], shape, activations, experts)
        gates = np.asarray([float(row["gates"][route_position]) for row in rows],
                           dtype=np.float32)
        result[:, route_position] = raw * gates[:, None]
    return result


def decisions(predicted: np.ndarray, ffn: np.ndarray, threshold: float) -> np.ndarray:
    full = ffn + predicted.sum(axis=1)
    denominator = np.maximum(np.linalg.norm(full, axis=1), 1e-30)
    selected = np.full(len(ffn), 4, dtype=np.int64)
    for keep in (1, 2, 3):
        omitted = predicted[:, keep:].sum(axis=1)
        safe = np.linalg.norm(omitted, axis=1) / denominator <= threshold
        selected[(selected == 4) & safe] = keep
    return selected


def summarize(selected: np.ndarray, exact: np.ndarray, ffn: np.ndarray,
              targets: np.ndarray) -> dict:
    errors = []
    for index, keep in enumerate(selected):
        output = ffn[index] + exact[index, :keep].sum(axis=0)
        errors.append(np.linalg.norm(output - targets[index]) /
                      max(np.linalg.norm(targets[index]), 1e-30))
    errors = np.asarray(errors)
    counts = {str(value): int(np.sum(selected == value)) for value in range(1, 5)}
    return {
        "positions": len(selected), "active_expert_counts": counts,
        "mean_active_experts": float(np.mean(selected)),
        "estimated_expert_traffic_reduction": float(4.0 / np.mean(selected)),
        "output_relative_l2_p50": float(np.median(errors)),
        "output_relative_l2_p95": float(np.percentile(errors, 95)),
        "output_relative_l2_max": float(np.max(errors)),
        "positions_at_or_below_two_percent": int(np.sum(errors <= 0.02)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--selection-captures", type=Path, required=True)
    parser.add_argument("--development-captures", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if json.loads(args.authorization.read_text()).get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")

    selection_rows, selection_x, selection_targets = load_capture(
        args.selection_captures, args.layer,
    )
    development_rows, development_x, development_targets = load_capture(
        args.development_captures, args.layer,
    )
    selection_ffn = load_ffn(args.selection_captures, selection_rows, args.layer)
    development_ffn = load_ffn(args.development_captures, development_rows, args.layer)
    cartridge = np.load(args.atlas)
    shape = atlas_shape(cartridge)
    predicted_selection = predicted_contributions(
        cartridge, shape, selection_x, selection_rows,
    )
    predicted_development = predicted_contributions(
        cartridge, shape, development_x, development_rows,
    )

    source = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    exact_sets = [
        np.empty((len(selection_rows), 4, WIDTH), dtype=np.float32),
        np.empty((len(development_rows), 4, WIDTH), dtype=np.float32),
    ]
    exact_ms = []
    with tempfile.TemporaryDirectory(prefix="aion-atlas-selector-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        function = ctypes.CDLL(str(library_path)).aion_gptoss_one_expert_contribution_batch
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        for destination, rows, activations in zip(
                exact_sets, (selection_rows, development_rows),
                (selection_x, development_x)):
            for row_index, (row, activation) in enumerate(zip(rows, activations)):
                for route_position, (expert_id, gate_value) in enumerate(
                        zip(row["route"], row["gates"])):
                    expert = store.get_layer_route_parallel(
                        args.layer, [int(expert_id)], workers=1,
                    )[0]
                    blobs = [expert[projection][kind]
                             for projection in ("gate", "up", "down")
                             for kind in ("weight", "bias")]
                    references = [ctypes.c_char_p(blob) for blob in blobs]
                    pointers = (ctypes.c_void_p * 6)(*[
                        ctypes.cast(reference, ctypes.c_void_p).value
                        for reference in references
                    ])
                    output = destination[row_index, route_position]
                    gate = np.asarray([gate_value], dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = function(
                        activation.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                        output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"expert contribution status {status}")
                    exact_ms.append(elapsed.value)
                    _ = references

    threshold_rows = []
    for threshold in (0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02,
                      0.03, 0.04, 0.05, 0.075, 0.1):
        selected = decisions(predicted_selection, selection_ffn, threshold)
        summary = summarize(selected, exact_sets[0], selection_ffn, selection_targets)
        threshold_rows.append({"threshold": threshold, **summary})
    # The selection cohort is deliberately small.  A p95 alone can silently
    # discard its single worst position, so configuration selection must obey
    # the numerical limit at every observed selection position.
    eligible = [row for row in threshold_rows
                if row["output_relative_l2_max"] <= 0.02]
    chosen = min(eligible, key=lambda row: row["mean_active_experts"]) if eligible else None
    if chosen is None:
        development = None
        status = "STOP_ATLAS_CONSEQUENCE_SELECTOR"
    else:
        selected = decisions(predicted_development, development_ffn,
                             float(chosen["threshold"]))
        development = summarize(
            selected, exact_sets[1], development_ffn, development_targets,
        )
        status = ("ADVANCE_ATLAS_CONSEQUENCE_SELECTOR"
                  if development["output_relative_l2_p95"] <= 0.02
                  and development["mean_active_experts"] < 4.0
                  else "STOP_ATLAS_CONSEQUENCE_SELECTOR")

    timing_values = []
    for _ in range(100):
        started = time.perf_counter_ns()
        _ = decisions(predicted_development, development_ffn, 0.02)
        timing_values.append((time.perf_counter_ns() - started) / 1e6)
    report = {
        "schema": "aion.gptoss-120b-atlas-consequence-selector-gate.v1",
        "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "layer": args.layer,
        "atlas_values_injected_into_model": False,
        "retained_experts_are_original_mxfp4": True,
        "exact_four_expert_fallback_required": True,
        "selection_family": args.selection_captures.name,
        "development_family": args.development_captures.name,
        "threshold_candidates": threshold_rows,
        "selected_threshold": None if chosen is None else chosen["threshold"],
        "selection": chosen, "development": development,
        "selector_decision_ms_p50": float(np.median(timing_values)),
        "exact_expert_ms_p50": float(np.median(exact_ms)),
        "blind_business_and_writing_opened": False,
        "atlas_sha256": digest(args.atlas),
        "authorization_sha256": digest(args.authorization),
        "warehouse_manifest_sha256": digest(args.manifest),
        "claim_boundary": (
            "One-layer oracle-backed selector gate. The frozen Taylor Atlas predicts only "
            "the consequence of omission; no approximate atlas value enters the layer output. "
            "Selection thresholds use extraction and are tested once on reasoning. This is not "
            "full-model quality or generated-token speed evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status, "selected_threshold": report["selected_threshold"],
        "selection": chosen, "development": development,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
