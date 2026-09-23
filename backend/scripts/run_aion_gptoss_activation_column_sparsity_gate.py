#!/usr/bin/env python3
"""Oracle gate for activation-addressed columnar GPT-OSS expert weights.

This changed-arithmetic probe asks whether retaining only weight columns selected
by the live gate/up and down activations can preserve a real layer output.  It
does not claim runtime speed: a physical column-addressed warehouse is required
before the projected traffic reduction can be measured.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore,
)


WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def retain_largest(values: np.ndarray, fraction: float,
                   block_size: int = 1) -> tuple[np.ndarray, float, np.ndarray]:
    if len(values) % block_size:
        raise ValueError("activation width must be divisible by block size")
    blocks = values.reshape(-1, block_size)
    scores = np.square(blocks.astype(np.float64)).sum(axis=1)
    retained = max(1, min(len(blocks), int(np.ceil(len(blocks) * fraction))))
    chosen = np.argpartition(scores, -retained)[-retained:]
    masked = np.zeros_like(values)
    masked.reshape(-1, block_size)[chosen] = blocks[chosen]
    total = float(np.dot(values.astype(np.float64), values.astype(np.float64)))
    kept = float(np.dot(masked.astype(np.float64), masked.astype(np.float64)))
    coordinates = np.concatenate([
        np.arange(index * block_size, (index + 1) * block_size) for index in chosen
    ])
    return masked, kept / max(total, 1e-30), coordinates


def coordinate_plane_pages(coordinates: np.ndarray, width: int = WIDTH,
                           page_size: int = 4096) -> tuple[int, int]:
    """Pages touched when each input coordinate is a packed output-row plane."""
    plane_bytes = (width + 1) // 2  # one four-bit code per output row
    touched = set()
    for coordinate in coordinates:
        begin = int(coordinate) * plane_bytes
        end = begin + plane_bytes - 1
        touched.update(range(begin // page_size, end // page_size + 1))
    total = math.ceil(width * plane_bytes / page_size)
    return len(touched), total


def pointers(blobs: list[bytes]) -> tuple[list[ctypes.c_char_p], ctypes.Array]:
    references = [ctypes.c_char_p(blob) for blob in blobs]
    array = (ctypes.c_void_p * len(references))(*[
        ctypes.cast(reference, ctypes.c_void_p).value for reference in references
    ])
    return references, array


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, action="append", required=True)
    parser.add_argument("--layer", default="12",
                        help="one layer number or 'all'")
    parser.add_argument("--fractions", default="0.125,0.25,0.5,0.75")
    parser.add_argument("--down-fractions",
                        help="optional down-input fractions; defaults to --fractions pairwise")
    parser.add_argument("--maximum-per-family", type=int, default=6)
    parser.add_argument("--minimum-traffic-reduction", type=float, default=2.0)
    parser.add_argument("--minimum-page-traffic-reduction", type=float, default=1.05)
    parser.add_argument("--selection-granularity", choices=("element", "block32"),
                        default="element")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    fractions = sorted({float(value) for value in args.fractions.split(",")})
    down_fractions = (sorted({float(value) for value in args.down_fractions.split(",")})
                      if args.down_fractions else None)
    if (not fractions or fractions[0] <= 0 or fractions[-1] > 1
            or (down_fractions and (down_fractions[0] <= 0 or down_fractions[-1] > 1))):
        raise SystemExit("fractions must be within (0, 1]")
    candidate_specs = ([(fraction, fraction) for fraction in fractions]
                       if down_fractions is None else
                       [(router, down) for router in fractions for down in down_fractions])
    candidate_key = lambda router, down: f"router_{router:g}_down_{down:g}"
    block_size = 32 if args.selection_granularity == "block32" else 1
    requested_layer = None if args.layer == "all" else int(args.layer)
    captures = []
    for root in args.activations:
        if requested_layer is not None:
            paths = sorted(root.glob(f"position-*-layer-{requested_layer}.json"))
            captures.extend((root.name, path) for path in paths[:args.maximum_per_family])
        else:
            for layer in range(36):
                paths = sorted(root.glob(f"position-*-layer-{layer}.json"))
                captures.extend((root.name, path)
                                for path in paths[:args.maximum_per_family])
    if not captures:
        raise SystemExit("no matching captures")

    native = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    observations = {candidate_key(router, down): []
                    for router, down in candidate_specs}
    with tempfile.TemporaryDirectory(prefix="aion-column-sparsity-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        original_fn = library.aion_gptoss_one_expert_contribution_reuse_graph
        original_fn.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p), ctypes.c_float,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
        ]
        original_fn.restype = ctypes.c_int
        gate_up_fn = library.aion_gptoss_expert_gate_up
        gate_up_fn.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
        ]
        gate_up_fn.restype = ctypes.c_int
        down_fn = library.aion_gptoss_expert_down_contribution
        down_fn.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p), ctypes.c_float,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
        ]
        down_fn.restype = ctypes.c_int

        for family, capture_path in captures:
            capture = json.loads(capture_path.read_text())
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            experts = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            originals = []
            blob_sets = []
            for gate, expert in zip(capture["gates"], experts, strict=True):
                blobs = [expert[projection][kind] for projection in ("gate", "up", "down")
                         for kind in ("weight", "bias")]
                blob_sets.append(blobs)
                references, ptrs = pointers(blobs)
                output = np.empty(WIDTH, dtype=np.float32)
                elapsed = ctypes.c_double()
                status = original_fn(
                    router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ptrs,
                    ctypes.c_float(gate),
                    output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                    ctypes.byref(elapsed),
                )
                if status:
                    raise RuntimeError(f"original contribution status {status}")
                _ = references
                originals.append(output.astype(np.float64))
            full_contribution = sum(originals, np.zeros(WIDTH, dtype=np.float64))
            full_output = ffn.astype(np.float64) + full_contribution

            for router_fraction, down_fraction in candidate_specs:
                masked_router, router_energy, router_coordinates = retain_largest(
                    router, router_fraction, block_size)
                router_pages, total_value_pages = coordinate_plane_pages(router_coordinates)
                candidates = []
                hidden_energies = []
                hidden_page_counts = []
                for gate, blobs in zip(capture["gates"], blob_sets, strict=True):
                    gate_references, gate_ptrs = pointers(blobs[:4])
                    hidden = np.empty(WIDTH, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = gate_up_fn(
                        masked_router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        gate_ptrs, hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"gate/up status {status}")
                    masked_hidden, hidden_energy, hidden_coordinates = retain_largest(
                        hidden, down_fraction, block_size)
                    hidden_energies.append(hidden_energy)
                    hidden_pages, _ = coordinate_plane_pages(hidden_coordinates)
                    hidden_page_counts.append(hidden_pages)
                    down_references, down_ptrs = pointers(blobs[4:])
                    contribution = np.empty(WIDTH, dtype=np.float32)
                    status = down_fn(
                        masked_hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        down_ptrs, ctypes.c_float(gate),
                        contribution.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"down status {status}")
                    _ = gate_references, down_references
                    candidates.append(contribution.astype(np.float64))
                candidate_contribution = sum(candidates, np.zeros(WIDTH, dtype=np.float64))
                candidate_output = ffn.astype(np.float64) + candidate_contribution
                delta = candidate_output - full_output
                observations[candidate_key(router_fraction, down_fraction)].append({
                    "family": family,
                    "capture": capture_path.name,
                    "router_energy_retained": router_energy,
                    "hidden_energy_retained_mean": float(np.mean(hidden_energies)),
                    "router_value_page_fraction": router_pages / total_value_pages,
                    "hidden_value_page_fraction_mean": float(
                        np.mean(hidden_page_counts) / total_value_pages),
                    "projected_page_traffic_reduction": float(
                        (4 * 3 * (math.ceil((WIDTH * (WIDTH // 32) * 17) / 4096)
                                  + math.ceil(WIDTH * 4 / 4096))) /
                        (4 * (2 * (router_pages + math.ceil(WIDTH * (WIDTH // 32) / 4096)
                                   + math.ceil(WIDTH * 4 / 4096))
                              + np.mean(hidden_page_counts)
                              + math.ceil(WIDTH * (WIDTH // 32) / 4096)
                              + math.ceil(WIDTH * 4 / 4096)))),
                    "output_relative_l2": float(
                        np.linalg.norm(delta) / max(np.linalg.norm(full_output), 1e-30)),
                    "contribution_relative_l2": float(
                        np.linalg.norm(delta) / max(np.linalg.norm(full_contribution), 1e-30)),
                    "argmax_equal": int(np.argmax(candidate_output)) == int(np.argmax(full_output)),
                })
            print(f"measured {family}/{capture_path.name}", flush=True)

    summaries = {}
    advancing = []
    for router_fraction, down_fraction in candidate_specs:
        key = candidate_key(router_fraction, down_fraction)
        rows = observations[key]
        output_errors = [row["output_relative_l2"] for row in rows]
        contribution_errors = [row["contribution_relative_l2"] for row in rows]
        summary = {
            "router_retained_column_fraction": router_fraction,
            "down_retained_column_fraction": down_fraction,
            # Each original MXFP4 block has one mandatory scale byte and 16
            # code bytes.  A coordinate-plane warehouse can omit selected code
            # nibbles but must still deliver all scales for touched rows.
            "projected_weight_traffic_reduction": 51.0 / (
                3.0 + 16.0 * (2.0 * router_fraction + down_fraction)),
            "samples": len(rows),
            "families": sorted({row["family"] for row in rows}),
            "router_energy_retained_p50": float(np.median([
                row["router_energy_retained"] for row in rows])),
            "hidden_energy_retained_p50": float(np.median([
                row["hidden_energy_retained_mean"] for row in rows])),
            "router_value_page_fraction_p50": float(np.median([
                row["router_value_page_fraction"] for row in rows])),
            "hidden_value_page_fraction_p50": float(np.median([
                row["hidden_value_page_fraction_mean"] for row in rows])),
            "projected_page_traffic_reduction_p50": float(np.median([
                row["projected_page_traffic_reduction"] for row in rows])),
            "projected_page_traffic_reduction_min": min(
                row["projected_page_traffic_reduction"] for row in rows),
            "output_relative_l2_p50": float(np.median(output_errors)),
            "output_relative_l2_p95": percentile(output_errors, .95),
            "output_relative_l2_max": max(output_errors),
            "contribution_relative_l2_p95": percentile(contribution_errors, .95),
            "all_argmax_equal": all(row["argmax_equal"] for row in rows),
        }
        summaries[key] = summary
        if (summary["projected_weight_traffic_reduction"] >= args.minimum_traffic_reduction
                and summary["projected_page_traffic_reduction_min"] >=
                    args.minimum_page_traffic_reduction
                and summary["output_relative_l2_p95"] <= .02
                and summary["output_relative_l2_max"] <= .025
                and summary["contribution_relative_l2_p95"] <= .15
                and summary["all_argmax_equal"]):
            advancing.append(key)

    report = {
        "schema": "aion.gptoss-120b-activation-column-sparsity.v1",
        "status": ("ADVANCE_COLUMN_ADDRESSED_WAREHOUSE" if advancing else
                   "STOP_ACTIVATION_COLUMN_SPARSITY"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True,
        "oracle_bound": True,
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": requested_layer if requested_layer is not None else "all",
        "fractions": fractions,
        "down_fractions": down_fractions,
        "selection_granularity": args.selection_granularity,
        "capture_roots": [str(path.resolve()) for path in args.activations],
        "observations": observations,
        "summaries": summaries,
        "advancing_fractions": advancing,
        "warehouse_metrics": store.metrics(),
        "promotion_gate": {
            "minimum_projected_weight_traffic_reduction": args.minimum_traffic_reduction,
            "minimum_projected_page_traffic_reduction":
                args.minimum_page_traffic_reduction,
            "maximum_output_relative_l2_p95": .02,
            "maximum_output_relative_l2_max": .025,
            "maximum_contribution_relative_l2_p95": .15,
            "all_argmax_equal": True,
        },
        "claim_boundary": (
            "Changed-arithmetic activation-column oracle. The current kernel still reads every "
            "original weight; traffic reduction is projected for a future hash-bound "
            "column-addressed warehouse. This is not a token-speed or semantic-quality "
            "result. Any advancing fraction requires multi-layer generation and exact "
            "fallback gates before deployment."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "summaries": summaries,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
