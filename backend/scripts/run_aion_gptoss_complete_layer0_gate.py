#!/usr/bin/env python3
"""Execute a complete position-zero gpt-oss transformer block from the SD warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


TENSOR_FILES = {
    "blk.0.attn_norm.weight": "attn-norm-weight.bin",
    "blk.0.attn_q.weight": "q-weight.bin",
    "blk.0.attn_q.bias": "q-bias.bin",
    "blk.0.attn_k.weight": "k-weight.bin",
    "blk.0.attn_k.bias": "k-bias.bin",
    "blk.0.attn_v.weight": "v-weight.bin",
    "blk.0.attn_v.bias": "v-bias.bin",
    "blk.0.attn_sinks.weight": "attn-sinks-weight.bin",
    "blk.0.attn_output.weight": "output-weight.bin",
    "blk.0.attn_output.bias": "output-bias.bin",
    "blk.0.post_attention_norm.weight": "post-attention-norm-weight.bin",
    "blk.0.ffn_gate_inp.weight": "router-weight.bin",
    "blk.0.ffn_gate_inp.bias": "router-bias.bin",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_gate(source: Path, output: Path) -> None:
    subprocess.run(["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include", str(source),
                    "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl", "-o", str(output)],
                   check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    module_root = Path(__file__).parents[1] / "modules/aion_inference"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-complete-layer-") as temporary:
        root = Path(temporary)
        remaining = set(TENSOR_FILES)
        tensor_evidence = {}
        reader_metrics = {}
        for source in manifest["verified_sources"]:
            reader = ExpertFrameGGUFReader(args.manifest, source["name"], 64 * 1024 * 1024)
            index = read_gguf_stream_index(reader, int(source["size"]))
            for tensor in index["tensors"]:
                name = tensor["name"]
                if name not in remaining:
                    continue
                value = reader.read_at(int(tensor["absolute_offset"]), int(tensor["byte_length"]))
                destination = root / TENSOR_FILES[name]
                destination.write_bytes(value)
                tensor_evidence[name] = {
                    "ggml_type": int(tensor["ggml_type"]),
                    "dimensions": tensor["dimensions"],
                    "bytes": len(value),
                    "sha256": hashlib.sha256(value).hexdigest(),
                    "source_shard": source["name"],
                }
                remaining.remove(name)
            reader_metrics[source["name"]] = reader.metrics()
        if remaining:
            raise RuntimeError(f"missing layer tensors: {sorted(remaining)}")

        attention_exe = root / "attention-gate"
        finish_exe = root / "finish-gate"
        compile_gate(module_root / "native/gptoss_layer0_attention_cpu_gate.cpp", attention_exe)
        compile_gate(module_root / "native/gptoss_layer0_moe_finish_cpu_gate.cpp", finish_exe)
        attention_runs = []
        prefixes = [root / "run-a", root / "run-b"]
        attention_started = time.perf_counter()
        for prefix in prefixes:
            command = [str(attention_exe), str(root), str(prefix), "-", str(args.threads)]
            attention_runs.append(json.loads(subprocess.check_output(command, text=True)))
        attention_seconds = time.perf_counter() - attention_started
        attention_repeatable = all(
            sha(prefixes[0].with_name(prefixes[0].name + suffix)) ==
            sha(prefixes[1].with_name(prefixes[1].name + suffix))
            for suffix in ("-ffn-input.bin", "-router-input.bin")
        )
        router_input_path = prefixes[0].with_name(prefixes[0].name + "-router-input.bin")
        ffn_input_path = prefixes[0].with_name(prefixes[0].name + "-ffn-input.bin")
        router_input = np.fromfile(router_input_path, dtype="<f4")
        router_w = np.fromfile(root / "router-weight.bin", dtype="<f4").reshape(128, 2880)
        router_b = np.fromfile(root / "router-bias.bin", dtype="<f4")
        logits = router_w @ router_input + router_b
        route = np.argsort(logits, kind="stable")[-4:][::-1].astype(int).tolist()
        selected = logits[route].astype(np.float64)
        selected -= selected.max()
        gates = np.exp(selected)
        gates /= gates.sum()

        store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
        load_started = time.perf_counter()
        experts = store.get_layer_route_parallel(0, route, workers=4)
        expert_load_seconds = time.perf_counter() - load_started
        for position, value in enumerate(experts):
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    (root / f"{position}-{projection}-{kind}.bin").write_bytes(value[projection][kind])
        route_csv = ",".join(map(str, route))
        gate_csv = ",".join(f"{value:.9g}" for value in gates)
        finish_runs = []
        outputs = [root / "block-a.bin", root / "block-b.bin"]
        finish_started = time.perf_counter()
        for output in outputs:
            command = [str(finish_exe), str(root), route_csv, gate_csv,
                       str(ffn_input_path), str(router_input_path), str(output), str(args.threads)]
            finish_runs.append(json.loads(subprocess.check_output(command, text=True)))
        finish_seconds = time.perf_counter() - finish_started
        output_hashes = [sha(path) for path in outputs]
        block_repeatable = output_hashes[0] == output_hashes[1]
        finite = all(item["finite"] for item in attention_runs + finish_runs)
        passed = attention_repeatable and block_repeatable and finite
        report = {
            "schema": "aion.gptoss-complete-layer0-gate.v1",
            "status": "PASSED" if passed else "FAILED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": "GPT-OSS 120B Q4_K_M/MXFP4", "layer": 0, "token_position": 0,
            "input": "deterministic synthetic hidden state",
            "attention_semantics": "RMSNorm, real Q/K/V+bias, grouped-query one-token attention with per-head sinks, output projection+bias, residual, post-attention RMSNorm",
            "moe_semantics": "real router+bias, top-4 softmax gates, four real MXFP4 expert SwiGLU networks, weighted sum, residual",
            "route": route, "router_logits": [float(logits[i]) for i in route],
            "normalized_gates": gates.tolist(), "tensor_evidence": tensor_evidence,
            "shared_reader_metrics": reader_metrics, "expert_store_metrics": store.metrics(),
            "expert_load_seconds": expert_load_seconds,
            "attention_two_run_wall_seconds": attention_seconds,
            "moe_finish_two_run_wall_seconds": finish_seconds,
            "attention_runs": attention_runs, "finish_runs": finish_runs,
            "attention_state_repeatable": attention_repeatable,
            "block_output_sha256": output_hashes,
            "block_output_bitwise_repeatable": block_repeatable,
            "declared_native_arena_bytes_each_stage": 256 * 1024 * 1024,
            "claim_boundary": "A complete position-zero layer-0 transformer block executed from verified SD-backed weights under bounded native arenas. The input is synthetic and embedding/final-vocabulary stages are excluded, so this is not yet a generated token.",
        }
        report["canonical_sha256"] = hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "route", "normalized_gates", "expert_load_seconds",
        "attention_state_repeatable", "block_output_sha256",
        "block_output_bitwise_repeatable", "canonical_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
