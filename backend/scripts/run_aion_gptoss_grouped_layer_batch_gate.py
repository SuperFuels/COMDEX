#!/usr/bin/env python3
"""ABBA-test exact expert-grouped batching on one real eight-position layer."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore
from backend.scripts.run_aion_gptoss_full_block_gate import (
    EXPERTS,
    WIDTH,
    bind_functions,
    compile_native,
    expert_pointers,
    layer_names,
    percentile,
    sha256_file,
    union_schedule,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--positions", type=int, default=8)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if not 2 <= args.positions <= 32:
        raise SystemExit("positions must be between 2 and 32")
    trace = json.loads(args.trace.read_text())
    if (trace.get("status") != "PASSED" or not trace.get("routes_repeatable")
            or not trace.get("final_hidden_and_logits_bitwise_repeatable")):
        raise SystemExit("trace must be exact, passed and repeatable")
    token_records = trace["run_a"]["tokens"][:args.positions]
    if len(token_records) != args.positions:
        raise SystemExit("trace does not contain enough positions")

    manifest = json.loads(args.manifest.read_text())
    readers = {}
    tensor_index = {}
    for source in manifest["verified_sources"]:
        reader = ExpertFrameGGUFReader(args.manifest, source["name"], 64 * 1024 * 1024)
        readers[source["name"]] = reader
        index = read_gguf_stream_index(reader, int(source["size"]))
        for tensor in index["tensors"]:
            tensor_index[tensor["name"]] = (source["name"], tensor)

    def read_tensor(name: str) -> bytes:
        source, tensor = tensor_index[name]
        return readers[source].read_at(int(tensor["absolute_offset"]),
                                       int(tensor["byte_length"]))

    layer = 0
    shared = [read_tensor(name) for name in layer_names(layer)]
    attention_values = shared[:-2]
    router_weight = np.frombuffer(shared[-2], dtype="<f4").reshape(EXPERTS, WIDTH)
    router_bias = np.frombuffer(shared[-1], dtype="<f4")
    embedding_source, embedding_tensor = tensor_index["token_embd.weight"]
    row_bytes = int(embedding_tensor["byte_length"]) // int(
        embedding_tensor["dimensions"][1])

    with tempfile.TemporaryDirectory(prefix="aion-gptoss-grouped-layer-") as temporary:
        root = Path(temporary)
        native = Path(__file__).parents[1] / "modules/aion_inference/native"
        embed_exe = root / "embed"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(native / "gptoss_embedding_cpu_gate.cpp"), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(embed_exe),
        ], check=True)
        hidden = []
        for position, record in enumerate(token_records):
            token_id = int(record["input_token_id"])
            row = readers[embedding_source].read_at(
                int(embedding_tensor["absolute_offset"]) + token_id * row_bytes, row_bytes)
            row_path = root / f"row-{position}.bin"
            output_path = root / f"hidden-{position}.bin"
            row_path.write_bytes(row)
            subprocess.run([str(embed_exe), str(row_path), str(output_path), str(args.threads)],
                           check=True, stdout=subprocess.DEVNULL)
            hidden.append(np.fromfile(output_path, dtype="<f4"))

        attention_path, moe_path, output_path = compile_native(native, root)
        libraries, attention, reset, scalar_moe, _ = bind_functions(
            attention_path, moe_path, output_path)
        moe_library = libraries[1]
        grouped = moe_library.aion_gptoss_one_expert_contribution_batch
        grouped.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        grouped.restype = ctypes.c_int
        heterogeneous = moe_library.aion_gptoss_moe_finish_heterogeneous_batch
        heterogeneous.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        heterogeneous.restype = ctypes.c_int
        combine = moe_library.aion_gptoss_combine_four_contributions
        combine.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.c_int, ctypes.POINTER(ctypes.c_float),
        ]
        combine.restype = ctypes.c_int

        reset()
        component_refs = [ctypes.c_char_p(value) for value in attention_values]
        component_ptrs = (ctypes.c_void_p * len(component_refs))(*[
            ctypes.cast(reference, ctypes.c_void_p).value for reference in component_refs])
        ffn_inputs = []
        router_inputs = []
        routes = []
        gates = []
        for position, state in enumerate(hidden):
            ffn = np.empty(WIDTH, dtype=np.float32)
            router = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = attention(
                state.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), component_ptrs,
                int(len(attention_values[5]) == 1013760), layer, position,
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"attention failed at position {position}: {status}")
            logits = router_weight @ router + router_bias
            route = np.argsort(logits, kind="stable")[-4:][::-1].astype(int).tolist()
            selected = logits[route].astype(np.float64)
            selected -= selected.max()
            gate = np.exp(selected)
            gate /= gate.sum()
            if route != token_records[position]["layers"][layer]["route"]:
                raise RuntimeError(f"route mismatch at position {position}")
            ffn_inputs.append(ffn)
            router_inputs.append(router)
            routes.append(route)
            gates.append(np.asarray([float(f"{value:.9g}") for value in gate],
                                    dtype=np.float32))

        store = GptOssExpertFrameStore(args.manifest, 0)
        experts = union_schedule(routes)
        values = store.get_layer_route_parallel(layer, experts, workers=8)
        bank = dict(zip(experts, values, strict=True))
        bank_pointers = {expert: expert_pointers([value]) for expert, value in bank.items()}
        full_pointers = {}
        for position, route in enumerate(routes):
            full_pointers[position] = expert_pointers([bank[expert] for expert in route])

        ffn_matrix = np.ascontiguousarray(np.stack(ffn_inputs))
        router_matrix = np.ascontiguousarray(np.stack(router_inputs))
        gate_matrix = np.ascontiguousarray(np.stack(gates))
        heterogeneous_blobs = [
            bank[expert][projection][kind]
            for route in routes for expert in route
            for projection in ("gate", "up", "down") for kind in ("weight", "bias")
        ]
        heterogeneous_references = [ctypes.c_char_p(blob) for blob in heterogeneous_blobs]
        heterogeneous_pointers = (ctypes.c_void_p * len(heterogeneous_references))(*[
            ctypes.cast(reference, ctypes.c_void_p).value
            for reference in heterogeneous_references])
        groups: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for position, route in enumerate(routes):
            for slot, expert in enumerate(route):
                groups[expert].append((position, slot))

        def run_scalar() -> tuple[np.ndarray, float]:
            outputs = np.empty((args.positions, WIDTH), dtype=np.float32)
            started = time.perf_counter_ns()
            for position in range(args.positions):
                elapsed = ctypes.c_double()
                references, pointers = full_pointers[position]
                status = scalar_moe(
                    ffn_inputs[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    router_inputs[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    pointers, gates[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    outputs[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    args.threads, ctypes.byref(elapsed),
                )
                _ = references
                if status:
                    raise RuntimeError(f"scalar MoE failed: {status}")
            return outputs, (time.perf_counter_ns() - started) / 1_000_000

        def run_grouped() -> tuple[np.ndarray, float]:
            contributions = np.empty((args.positions, 4, WIDTH), dtype=np.float32)
            started = time.perf_counter_ns()
            for expert, occurrences in groups.items():
                inputs = np.ascontiguousarray(np.stack(
                    [router_inputs[position] for position, _ in occurrences]))
                weights = np.asarray([gates[position][slot]
                                      for position, slot in occurrences], dtype=np.float32)
                outputs = np.empty((len(occurrences), WIDTH), dtype=np.float32)
                elapsed = ctypes.c_double()
                references, pointers = bank_pointers[expert]
                status = grouped(
                    inputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                    weights.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), len(occurrences),
                    outputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                    ctypes.byref(elapsed),
                )
                _ = references
                if status:
                    raise RuntimeError(f"grouped expert failed: {status}")
                for row, (position, slot) in enumerate(occurrences):
                    contributions[position, slot] = outputs[row]
            outputs = np.empty((args.positions, WIDTH), dtype=np.float32)
            status = combine(
                ffn_matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                contributions.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.positions, outputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            )
            if status:
                raise RuntimeError(f"combine failed: {status}")
            return outputs, (time.perf_counter_ns() - started) / 1_000_000

        def run_heterogeneous() -> tuple[np.ndarray, float]:
            outputs = np.empty((args.positions, WIDTH), dtype=np.float32)
            elapsed = ctypes.c_double()
            started = time.perf_counter_ns()
            status = heterogeneous(
                ffn_matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router_matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                heterogeneous_pointers,
                gate_matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.positions,
                outputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"heterogeneous batch failed: {status}")
            return outputs, (time.perf_counter_ns() - started) / 1_000_000

        timings = {"scalar": [], "grouped": [], "heterogeneous": []}
        hashes = {mode: [] for mode in timings}
        for _ in range(args.rounds):
            for mode in ("scalar", "heterogeneous", "grouped", "grouped",
                         "heterogeneous", "scalar"):
                outputs, elapsed = {
                    "scalar": run_scalar,
                    "grouped": run_grouped,
                    "heterogeneous": run_heterogeneous,
                }[mode]()
                timings[mode].append(elapsed)
                hashes[mode].append(hashlib.sha256(outputs.tobytes()).hexdigest())
        _ = component_refs, libraries, heterogeneous_references

    summaries = {name: {
        "samples": len(values),
        "wall_p50_ms": statistics.median(values),
        "wall_p95_ms": percentile(values, 0.95),
    } for name, values in timings.items()}
    exact = len({digest for values in hashes.values() for digest in values}) == 1
    speedup = summaries["scalar"]["wall_p50_ms"] / summaries["grouped"]["wall_p50_ms"]
    heterogeneous_speedup = (summaries["scalar"]["wall_p50_ms"] /
                             summaries["heterogeneous"]["wall_p50_ms"])
    group_sizes = [len(occurrences) for occurrences in groups.values()]
    result = {
        "schema": "aion.gptoss-120b-exact-grouped-layer-batch-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": layer,
        "positions": args.positions,
        "threads": args.threads,
        "rounds": args.rounds,
        "unique_experts": len(groups),
        "expert_occurrences": sum(group_sizes),
        "mean_group_size": statistics.fmean(group_sizes),
        "maximum_group_size": max(group_sizes),
        "group_size_histogram": {str(size): group_sizes.count(size)
                                 for size in sorted(set(group_sizes))},
        "summaries": summaries,
        "wall_speedup": speedup,
        "heterogeneous_wall_speedup": heterogeneous_speedup,
        "all_outputs_bitwise_equal": exact,
        "status": ("ADVANCE_HETEROGENEOUS_BLOCK_VERIFIER"
                   if exact and heterogeneous_speedup >= 1.50
                   else "NOT_PROMOTED"),
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": sha256_file(args.trace),
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "One real causal layer and eight teacher positions were evaluated after loading "
            "their exact expert union. The heterogeneous candidate points one graph at "
            "the existing verified expert frames without copying a route slab. This is "
            "a packed-arithmetic gate; it is not a "
            "full transformer block, draft acceptance or generated-token measurement."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "all_outputs_bitwise_equal", "wall_speedup",
        "heterogeneous_wall_speedup", "mean_group_size",
        "group_size_histogram", "summaries", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
