#!/usr/bin/env python3
"""Gate GHX-addressed reuse of original expert functions on unseen activations."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore
from backend.scripts.run_aion_expert_function_atlas_gate import digest, load_capture


WIDTH = 2880


def load_ffn(root: Path, rows: list[dict], layer: int) -> np.ndarray:
    values = []
    for row in rows:
        path = root / f"position-{row['position']}-layer-{layer}-ffn.bin"
        if digest(path) != row["ffn_sha256"]:
            raise SystemExit(f"capture hash mismatch: {path}")
        values.append(np.fromfile(path, dtype="<f4"))
    return np.stack(values)


def normalize(values: np.ndarray) -> np.ndarray:
    return values / np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-30)


def evaluate_family(rows: list[dict], activations: np.ndarray, ffn: np.ndarray,
                    targets: np.ndarray, exact_raw: np.ndarray,
                    bank: dict[int, list[tuple[np.ndarray, np.ndarray]]],
                    threshold: float) -> dict:
    errors = []
    reused = 0
    similarities = []
    exact_addresses = 0
    for row_index, row in enumerate(rows):
        contributions = []
        for route_position, (expert_id, gate) in enumerate(zip(row["route"], row["gates"])):
            activation = activations[row_index]
            candidates = bank.get(int(expert_id), ())
            chosen = exact_raw[row_index, route_position]
            if candidates:
                query = normalize(activation[None, :])[0]
                scores = np.asarray([float(np.dot(query, item[0])) for item in candidates])
                nearest = int(np.argmax(scores))
                similarity = float(scores[nearest])
                similarities.append(similarity)
                if np.array_equal(query, candidates[nearest][0]):
                    exact_addresses += 1
                if similarity >= threshold:
                    chosen = candidates[nearest][1]
                    reused += 1
            contributions.append(float(gate) * chosen)
        output = ffn[row_index] + np.stack(contributions).sum(axis=0)
        errors.append(np.linalg.norm(output - targets[row_index]) /
                      max(np.linalg.norm(targets[row_index]), 1e-30))
    errors = np.asarray(errors)
    total = 4 * len(rows)
    return {
        "positions": len(rows), "expert_calls": total,
        "reused_expert_calls": reused, "exact_activation_addresses": exact_addresses,
        "reuse_fraction": reused / total,
        "estimated_expert_traffic_reduction": total / max(total - reused, 1),
        "nearest_similarity_p50": (None if not similarities
                                    else float(np.median(similarities))),
        "nearest_similarity_p95": (None if not similarities
                                    else float(np.percentile(similarities, 95))),
        "output_relative_l2_p50": float(np.median(errors)),
        "output_relative_l2_p95": float(np.percentile(errors, 95)),
        "output_relative_l2_max": float(np.max(errors)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--fit-captures", type=Path, required=True)
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

    roots = (args.fit_captures, args.selection_captures, args.development_captures)
    loaded = [load_capture(root, args.layer) for root in roots]
    rows = [item[0] for item in loaded]
    activations = [item[1] for item in loaded]
    targets = [item[2] for item in loaded]
    ffn = [load_ffn(root, family_rows, args.layer)
           for root, family_rows in zip(roots, rows)]
    exact_raw = [np.empty((len(family_rows), 4, WIDTH), dtype=np.float32)
                 for family_rows in rows]

    source = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    exact_ms = []
    with tempfile.TemporaryDirectory(prefix="aion-ghx-address-") as temporary:
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
        for family_index, family_rows in enumerate(rows):
            for row_index, row in enumerate(family_rows):
                for route_position, expert_id in enumerate(row["route"]):
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
                    output = exact_raw[family_index][row_index, route_position]
                    gate = np.ones(1, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = function(
                        activations[family_index][row_index].ctypes.data_as(
                            ctypes.POINTER(ctypes.c_float)),
                        pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                        output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"expert contribution status {status}")
                    exact_ms.append(elapsed.value)
                    _ = references

    fit_bank: dict[int, list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
    for row_index, row in enumerate(rows[0]):
        address = normalize(activations[0][row_index:row_index + 1])[0]
        for route_position, expert_id in enumerate(row["route"]):
            fit_bank[int(expert_id)].append((address.copy(),
                                             exact_raw[0][row_index, route_position].copy()))

    thresholds = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.925, 0.95,
                  0.975, 0.99, 0.995, 0.999)
    selection = []
    for threshold in thresholds:
        selection.append({
            "threshold": threshold,
            **evaluate_family(rows[1], activations[1], ffn[1], targets[1],
                              exact_raw[1], fit_bank, threshold),
        })
    eligible = [item for item in selection
                if item["output_relative_l2_max"] <= 0.02]
    chosen = (max(eligible, key=lambda item: item["reuse_fraction"])
              if eligible else None)

    development_bank = defaultdict(list)
    for expert_id, values in fit_bank.items():
        development_bank[expert_id].extend(values)
    for row_index, row in enumerate(rows[1]):
        address = normalize(activations[1][row_index:row_index + 1])[0]
        for route_position, expert_id in enumerate(row["route"]):
            development_bank[int(expert_id)].append((
                address.copy(), exact_raw[1][row_index, route_position].copy(),
            ))
    development = None
    if chosen is not None:
        development = evaluate_family(
            rows[2], activations[2], ffn[2], targets[2], exact_raw[2],
            development_bank, float(chosen["threshold"]),
        )
    advance = bool(development and development["output_relative_l2_max"] <= 0.02
                   and development["reuse_fraction"] > 0.0)
    report = {
        "schema": "aion.gptoss-120b-ghx-activation-address-gate.v1",
        "status": "ADVANCE_GHX_ACTIVATION_ADDRESS" if advance
                  else "STOP_GHX_ACTIVATION_ADDRESS",
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "layer": args.layer, "fit_family": roots[0].name,
        "selection_family": roots[1].name, "development_family": roots[2].name,
        "selection_candidates": selection, "selected": chosen,
        "development": development,
        "exact_expert_ms_p50": float(np.median(exact_ms)),
        "exact_four_expert_fallback": True,
        "current_router_gates_preserved": True,
        "blind_business_and_writing_opened": False,
        "authorization_sha256": digest(args.authorization),
        "warehouse_manifest_sha256": digest(args.manifest),
        "claim_boundary": (
            "Layer-12 GHX nearest-activation microgate. Reuse requires the same original "
            "expert ID; current gates are retained; every miss uses the original expert. "
            "Extraction selects the similarity boundary and reasoning is unseen development. "
            "This is not full-model quality or generated-token speed evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "selected": chosen,
        "development": development,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
