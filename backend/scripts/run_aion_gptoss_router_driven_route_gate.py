#!/usr/bin/env python3
"""Route and execute four exact gpt-oss experts for one synthetic hidden state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--repetitions", type=int, default=8)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    tensor_names = {f"blk.{args.layer}.ffn_gate_inp.weight", f"blk.{args.layer}.ffn_gate_inp.bias"}
    tensors = {}
    reader_metrics = {}
    for source in manifest["verified_sources"]:
        reader = ExpertFrameGGUFReader(args.manifest, source["name"], 16 * 1024 * 1024)
        index = read_gguf_stream_index(reader, int(source["size"]))
        for tensor in index["tensors"]:
            if tensor["name"] in tensor_names:
                tensors[tensor["name"]] = reader.read_at(tensor["absolute_offset"], tensor["byte_length"])
        reader_metrics[source["name"]] = reader.metrics()
    if set(tensors) != tensor_names: raise RuntimeError("router tensors are incomplete")
    width, experts = 2880, 128
    hidden = np.sin(np.arange(width, dtype=np.float32) * np.float32(0.00390625))
    weights = np.frombuffer(tensors[f"blk.{args.layer}.ffn_gate_inp.weight"], dtype="<f4").reshape(experts, width)
    bias = np.frombuffer(tensors[f"blk.{args.layer}.ffn_gate_inp.bias"], dtype="<f4")
    logits = weights @ hidden + bias
    route = np.argsort(logits)[-4:][::-1].astype(int).tolist()
    selected = logits[route].astype(np.float64)
    selected -= selected.max()
    gates = np.exp(selected); gates /= gates.sum()
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    load_started = time.perf_counter(); values = store.get_layer_route(args.layer, route)
    load_seconds = time.perf_counter() - load_started
    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_packed_route_cpu_gate.cpp"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-route-") as temporary:
        root = Path(temporary); executable = root / "gate"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include", str(source),
                        "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl", "-o", str(executable)], check=True)
        for position, value in enumerate(values):
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    (root / f"{position}-{projection}-{kind}.bin").write_bytes(value[projection][kind])
        command = [str(executable), str(root), ",".join(map(str, route)),
                   ",".join(f"{value:.9g}" for value in gates),
                   str(args.repetitions), str(args.threads)]
        run_a = json.loads(subprocess.check_output(command, text=True))
        run_b = json.loads(subprocess.check_output(command, text=True))
    repeatable = run_a["finite"] and run_b["finite"] and run_a["checksum"] == run_b["checksum"]
    report = {"schema":"aion.gptoss-router-driven-route-gate.v1",
              "status":"PASSED" if repeatable else "FAILED",
              "created_at":datetime.now(timezone.utc).isoformat(), "layer":args.layer,
              "route":route, "router_logits":[float(logits[i]) for i in route],
              "normalized_gates":gates.tolist(), "expert_load_seconds":load_seconds,
              "expert_store_metrics":store.metrics(), "shared_reader_metrics":reader_metrics,
              "run_a":run_a, "run_b":run_b, "finite_and_checksum_repeatable":repeatable,
              "claim_boundary":"Real router tensors selected four real experts and their exact packed networks executed and combined for a synthetic hidden state. This excludes attention and residual/norm operations, so it is not yet a complete transformer layer or token."}
    report["canonical_sha256"] = hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report[k] for k in ("status","route","normalized_gates","expert_load_seconds","expert_store_metrics","run_a","run_b","canonical_sha256")},sort_keys=True))


if __name__ == "__main__": main()
