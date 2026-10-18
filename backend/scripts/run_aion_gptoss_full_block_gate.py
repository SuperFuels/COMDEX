#!/usr/bin/env python3
"""AB/BA gate for exact layer-major GPT-OSS 120B block execution.

The input IDs are taken from an already-verified teacher trace.  Positions are
advanced together through each transformer layer.  Attention remains causal;
only the exact MoE expert loads are unioned across positions.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880
EXPERTS = 128
LAYERS = 36
VOCABULARY = 201088


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: dict) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def union_schedule(routes: list[list[int]]) -> list[int]:
    return sorted({expert for route in routes for expert in route})


def compile_native(native: Path, root: Path) -> tuple[Path, Path, Path]:
    attention = root / "attention.dylib"
    moe = root / "moe.dylib"
    output = root / "output.dylib"
    common = ["clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include"]
    tail = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
    for source, target in (
        ("gptoss_persistent_attention_library.cpp", attention),
        ("gptoss_persistent_moe_library.cpp", moe),
        ("gptoss_persistent_output_library.cpp", output),
    ):
        subprocess.run(common + [str(native / source)] + tail + ["-o", str(target)], check=True)
    return attention, moe, output


def layer_names(layer: int) -> tuple[str, ...]:
    prefix = f"blk.{layer}."
    return tuple(prefix + suffix for suffix in (
        "attn_norm.weight", "attn_q.weight", "attn_q.bias", "attn_k.weight",
        "attn_k.bias", "attn_v.weight", "attn_v.bias", "attn_sinks.weight",
        "attn_output.weight", "attn_output.bias", "post_attention_norm.weight",
        "ffn_gate_inp.weight", "ffn_gate_inp.bias",
    ))


def bind_functions(attention_path: Path, moe_path: Path, output_path: Path):
    attention_lib = ctypes.CDLL(str(attention_path))
    attention = attention_lib.aion_gptoss_attention
    attention.argtypes = [
        ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p), ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
    ]
    attention.restype = ctypes.c_int
    reset = attention_lib.aion_gptoss_attention_reset_kv
    reset.argtypes = []
    reset.restype = None

    moe_lib = ctypes.CDLL(str(moe_path))
    moe = moe_lib.aion_gptoss_moe_finish
    moe.argtypes = [
        ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
    ]
    moe.restype = ctypes.c_int

    output_lib = ctypes.CDLL(str(output_path))
    output = output_lib.aion_gptoss_output
    output.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
    ]
    output.restype = ctypes.c_int
    return (attention_lib, moe_lib, output_lib), attention, reset, moe, output


def expert_pointers(values: list[dict]):
    blobs = [value[projection][kind] for value in values
             for projection in ("gate", "up", "down") for kind in ("weight", "bias")]
    references = [ctypes.c_char_p(blob) for blob in blobs]
    pointers = (ctypes.c_void_p * len(references))(*[
        ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
    return references, pointers


def execute_mode(
    mode: str,
    manifest: Path,
    token_records: list[dict],
    initial_states: list[np.ndarray],
    shared: list[list[bytes]],
    output_weight: np.memmap,
    output_norm: np.ndarray,
    attention,
    reset,
    moe,
    output,
    threads: int,
    union_workers: int,
) -> dict:
    reset()
    store = GptOssExpertFrameStore(manifest, 0)
    hidden = [value.copy() for value in initial_states]
    layer_records = []
    peak_live = 0
    started = time.perf_counter()
    for layer in range(LAYERS):
        attention_values = shared[layer][:-2]
        router_weight = np.frombuffer(shared[layer][-2], dtype="<f4").reshape(EXPERTS, WIDTH)
        router_bias = np.frombuffer(shared[layer][-1], dtype="<f4")
        component_refs = [ctypes.c_char_p(value) for value in attention_values]
        component_ptrs = (ctypes.c_void_p * len(component_refs))(*[
            ctypes.cast(reference, ctypes.c_void_p).value for reference in component_refs])
        ffn_inputs: list[np.ndarray] = []
        router_inputs: list[np.ndarray] = []
        routes: list[list[int]] = []
        gates: list[np.ndarray] = []
        attention_ms = []
        for position, state in enumerate(hidden):
            ffn = np.empty(WIDTH, dtype=np.float32)
            router = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            value_is_q5 = int(len(attention_values[5]) == 1013760)
            status = attention(
                state.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), component_ptrs,
                value_is_q5, layer, position,
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), threads,
                ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"attention failed at layer {layer}, position {position}: {status}")
            logits = router_weight @ router + router_bias
            route = np.argsort(logits, kind="stable")[-4:][::-1].astype(int).tolist()
            selected = logits[route].astype(np.float64)
            selected -= selected.max()
            gate = np.exp(selected)
            gate /= gate.sum()
            expected = token_records[position]["layers"][layer]
            if route != expected["route"]:
                raise RuntimeError(f"route mismatch at layer {layer}, position {position}")
            ffn_inputs.append(ffn)
            router_inputs.append(router)
            routes.append(route)
            gates.append(np.asarray([float(f"{value:.9g}") for value in gate], dtype=np.float32))
            attention_ms.append(elapsed.value)

        load_started = time.perf_counter()
        bank = None
        if mode == "union":
            experts = union_schedule(routes)
            loaded = store.get_layer_route_parallel(layer, experts, workers=union_workers)
            bank = dict(zip(experts, loaded, strict=True))
            peak_live = max(peak_live, sum(store._value_size(value) for value in loaded))
        load_seconds = time.perf_counter() - load_started

        next_hidden = []
        moe_ms = []
        for position, route in enumerate(routes):
            demand_started = time.perf_counter()
            values = ([bank[expert] for expert in route] if bank is not None else
                      store.get_layer_route_parallel(layer, route, workers=4))
            load_seconds += time.perf_counter() - demand_started
            if bank is None:
                peak_live = max(peak_live, sum(store._value_size(value) for value in values))
            references, pointers = expert_pointers(values)
            result = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = moe(
                ffn_inputs[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router_inputs[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                gates[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                result.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), threads,
                ctypes.byref(elapsed),
            )
            _ = references
            if status:
                raise RuntimeError(f"MoE failed at layer {layer}, position {position}: {status}")
            next_hidden.append(result)
            moe_ms.append(elapsed.value)
        hidden = next_hidden
        layer_records.append({
            "layer": layer,
            "unique_experts": len(union_schedule(routes)),
            "routes": routes,
            "expert_load_seconds": load_seconds,
            "attention_ms_total": sum(attention_ms),
            "moe_ms_total": sum(moe_ms),
        })

    results = []
    for position, state in enumerate(hidden):
        logits = np.empty(VOCABULARY, dtype=np.float32)
        token = ctypes.c_int()
        checksum = ctypes.c_double()
        elapsed = ctypes.c_double()
        status = output(
            ctypes.c_void_p(output_weight.ctypes.data),
            output_norm.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            state.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            logits.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), threads,
            ctypes.byref(token), ctypes.byref(checksum), ctypes.byref(elapsed),
        )
        if status:
            raise RuntimeError(f"output failed at position {position}: {status}")
        expected = token_records[position]
        results.append({
            "position": position,
            "input_token_id": expected["input_token_id"],
            "generated_token_id": token.value,
            "expected_generated_token_id": expected["generated_token_id"],
            "hidden_sha256": sha256_bytes(state.tobytes()),
            "expected_hidden_sha256": expected["final_hidden_sha256"],
            "logits_sha256": sha256_bytes(logits.tobytes()),
            "expected_logits_sha256": expected["logits_sha256"],
            "output_ms": elapsed.value,
            "exact": (token.value == expected["generated_token_id"] and
                      sha256_bytes(state.tobytes()) == expected["final_hidden_sha256"] and
                      sha256_bytes(logits.tobytes()) == expected["logits_sha256"]),
        })
    return {
        "mode": mode,
        "wall_seconds": time.perf_counter() - started,
        "positions": results,
        "all_positions_bitwise_exact": all(item["exact"] for item in results),
        "layers": layer_records,
        "peak_live_expert_bytes": peak_live,
        "store_metrics": store.metrics(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--positions", type=int, default=2)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--union-workers", type=int, default=8)
    parser.add_argument("--pair-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.positions not in (2, 4, 8):
        raise SystemExit("positions must be 2, 4, or 8")
    if args.union_workers < 1 or args.union_workers > 16:
        raise SystemExit("union-workers must be between 1 and 16")
    trace = json.loads(args.trace.read_text())
    if (trace.get("status") != "PASSED" or not trace.get("routes_repeatable") or
            not trace.get("final_hidden_and_logits_bitwise_repeatable")):
        raise SystemExit("trace must be a passed repeatable exact teacher trace")
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
        return readers[source].read_at(int(tensor["absolute_offset"]), int(tensor["byte_length"]))

    shared_started = time.perf_counter()
    shared = [[read_tensor(name) for name in layer_names(layer)] for layer in range(LAYERS)]
    shared_stage_seconds = time.perf_counter() - shared_started

    embedding_source, embedding_tensor = tensor_index["token_embd.weight"]
    embedding_row_bytes = int(embedding_tensor["byte_length"]) // int(embedding_tensor["dimensions"][1])
    initial_states = []
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-full-block-") as temporary:
        root = Path(temporary)
        embed_exe = root / "embed"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(native / "gptoss_embedding_cpu_gate.cpp"), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(embed_exe),
        ], check=True)
        for position, record in enumerate(token_records):
            token_id = int(record["input_token_id"])
            row = readers[embedding_source].read_at(
                int(embedding_tensor["absolute_offset"]) + token_id * embedding_row_bytes,
                embedding_row_bytes,
            )
            row_path = root / f"embedding-{position}.bin"
            hidden_path = root / f"hidden-{position}.bin"
            row_path.write_bytes(row)
            subprocess.run([str(embed_exe), str(row_path), str(hidden_path), str(args.threads)],
                           check=True, stdout=subprocess.DEVNULL)
            initial_states.append(np.fromfile(hidden_path, dtype="<f4"))

        output_weight_path = root / "output-weight.bin"
        output_weight_path.write_bytes(read_tensor("output.weight"))
        output_weight = np.memmap(output_weight_path, dtype=np.uint8, mode="r")
        output_norm = np.frombuffer(read_tensor("output_norm.weight"), dtype="<f4")
        attention_path, moe_path, output_path = compile_native(native, root)
        libraries, attention, reset, moe, output = bind_functions(
            attention_path, moe_path, output_path)
        order = (("sequential", "union") if args.pair_only else
                 ("sequential", "union", "union", "sequential"))
        runs = [execute_mode(
            mode, args.manifest, token_records, initial_states, shared, output_weight,
            output_norm, attention, reset, moe, output, args.threads, args.union_workers,
        ) for mode in order]
        _ = libraries

    sequential = [run for run in runs if run["mode"] == "sequential"]
    union = [run for run in runs if run["mode"] == "union"]
    exact = all(run["all_positions_bitwise_exact"] for run in runs)
    sequential_seconds = [run["wall_seconds"] for run in sequential]
    union_seconds = [run["wall_seconds"] for run in union]
    sequential_bytes = [run["store_metrics"]["compressed_bytes_read"] for run in sequential]
    union_bytes = [run["store_metrics"]["compressed_bytes_read"] for run in union]
    report = {
        "schema": "aion.gptoss-120b-full-causal-block-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "track": "exact_teacher_forced_full_model_block",
        "positions": args.positions,
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": sha256_file(args.trace),
        "manifest_path": str(args.manifest.resolve()),
        "manifest_file_sha256": sha256_file(args.manifest),
        "execution_order": list(order),
        "exploratory_pair_only": args.pair_only,
        "sequential_workers": 4,
        "union_workers": args.union_workers,
        "runs": runs,
        "all_positions_all_runs_bitwise_exact": exact,
        "wall_speedup_p50": statistics.median(sequential_seconds) / statistics.median(union_seconds),
        "compressed_traffic_reduction_p50": statistics.median(sequential_bytes) / statistics.median(union_bytes),
        "sequential_wall_p50_seconds": statistics.median(sequential_seconds),
        "sequential_wall_p95_seconds": percentile(sequential_seconds, .95),
        "union_wall_p50_seconds": statistics.median(union_seconds),
        "union_wall_p95_seconds": percentile(union_seconds, .95),
        "peak_live_expert_bytes": max(run["peak_live_expert_bytes"] for run in union),
        "shared_one_time_stage_seconds": shared_stage_seconds,
        "declared_streaming_ceiling_bytes": 3 * 1024 * 1024 * 1024,
        "acceptance": {
            "all_positions_bitwise_exact": exact,
            "traffic_reduction_above_1_10x": statistics.median(sequential_bytes) / statistics.median(union_bytes) > 1.10,
            "wall_speedup_above_1_10x": statistics.median(sequential_seconds) / statistics.median(union_seconds) > 1.10,
            "peak_live_below_3GiB": max(run["peak_live_expert_bytes"] for run in union) < 3 * 1024 * 1024 * 1024,
        },
        "claim_boundary": (
            "All 36 causal attention and exact MoE layers plus the full vocabulary head were "
            "executed for a frozen teacher-forced block. Exact original expert weights and the "
            "unrestricted router were retained. This measures verification of known candidate "
            "positions; draft cost, acceptance rate, rejection recovery and free-running "
            "generated-token throughput are not included."
        ),
    }
    report["status"] = ("REPLICATE_CANDIDATE" if args.pair_only and all(report["acceptance"].values())
                        else "STOP_EXPLORATORY_BLOCK" if args.pair_only
                        else "ADVANCE_4_POSITION_BLOCK" if args.positions == 2 and all(report["acceptance"].values())
                        else "ADVANCE_8_POSITION_BLOCK" if args.positions == 4 and all(report["acceptance"].values())
                        else "ADVANCE_SPECULATIVE_INTEGRATION" if args.positions == 8 and all(report["acceptance"].values())
                        else "STOP_FULL_BLOCK")
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "positions", "all_positions_all_runs_bitwise_exact",
        "wall_speedup_p50", "compressed_traffic_reduction_p50",
        "peak_live_expert_bytes", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
