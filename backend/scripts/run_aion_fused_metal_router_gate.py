#!/usr/bin/env python3
"""Gate a one-launch BF16 Metal router for the Granite dynamic expert bank."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import time

import torch

from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def _shader_source() -> str:
    return r"""#include <metal_stdlib>
using namespace metal;
kernel void fused_route(device const half* x [[buffer(0)]],
 device const half* w [[buffer(1)]], device int* out_ids [[buffer(2)]],
 device half* out_gates [[buffer(3)]], constant uint& K [[buffer(4)]],
 constant uint& E [[buffer(5)]], uint tid [[thread_index_in_threadgroup]],
 uint lane [[thread_index_in_simdgroup]],
 uint sg [[simdgroup_index_in_threadgroup]]) {
 threadgroup float logits[40];
 for (uint e=sg; e<E; e+=8) {
   float value=0.0f; uint base=e*K;
   for (uint j=lane; j<K; j+=32) value += float(x[j])*float(w[base+j]);
   value=simd_sum(value); if (lane==0) logits[e]=value;
 }
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if (tid==0) {
   float best_v[8]; int best_i[8];
   for (uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
   for (uint e=0;e<E;e++) {
     float value=logits[e];
     for (uint pos=0;pos<8;pos++) if (value>best_v[pos]) {
       for (uint move=7;move>pos;move--){best_v[move]=best_v[move-1];best_i[move]=best_i[move-1];}
       best_v[pos]=value;best_i[pos]=int(e);break;
     }
   }
   float maximum=best_v[0], denominator=0.0f, probabilities[8];
   for (uint j=0;j<8;j++){probabilities[j]=exp(best_v[j]-maximum);denominator+=probabilities[j];}
   for (uint left=0;left<8;left++) for (uint right=left+1;right<8;right++)
     if(best_i[right]<best_i[left]){
       int ti=best_i[left];best_i[left]=best_i[right];best_i[right]=ti;
       float tv=probabilities[left];probabilities[left]=probabilities[right];probabilities[right]=tv;
     }
   for (uint j=0;j<8;j++){out_ids[j]=best_i[j];out_gates[j]=half(probabilities[j]/denominator);}
 }
}
"""


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--accuracy-samples", type=int, default=256)
    parser.add_argument("--timing-samples", type=int, default=1000)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091830)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve(); model_path = args.model_path.resolve()
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (model_path, output_path)):
        raise SystemExit("model and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    checkpoint_index = model_path / "model.safetensors.index.json"
    model, shared_load = _load_storage_first_model(
        model_path, json.loads(checkpoint_index.read_text()))
    router = model.model.layers[args.layer].block_sparse_moe.router.layer
    weight = router.weight
    if weight.dtype != torch.float16 or weight.shape[0] != 40:
        raise RuntimeError(f"unexpected router weight: {weight.dtype} {tuple(weight.shape)}")
    del model
    gc.collect()
    library = torch.mps.compile_shader(_shader_source())
    output_ids = torch.empty((8,), dtype=torch.int32, device="mps")
    output_gates = torch.empty((8,), dtype=torch.float16, device="mps")
    generator = torch.Generator().manual_seed(args.seed)
    inputs = torch.randn((args.accuracy_samples, weight.shape[1]), generator=generator,
                         dtype=torch.float16).to("mps")

    def control(value):
        logits = router(value.view(1, -1)).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        gates = torch.softmax(top_logits, dim=1).type_as(value)
        top_indices, order = top_indices.sort(dim=1)
        return top_indices[0].to(torch.int32), gates.gather(1, order)[0]

    def candidate(value):
        library.fused_route(value, weight, output_ids, output_gates, weight.shape[1],
                            weight.shape[0], threads=(256, 1, 1), group_size=(256, 1, 1))
        return output_ids, output_gates

    exact_sets = 0; maximum_gate_error = 0.0; mean_gate_errors = []
    with torch.inference_mode():
        for value in inputs:
            reference_ids, reference_gates = control(value)
            candidate_ids, candidate_gates = candidate(value)
            torch.mps.synchronize()
            reference_ids = reference_ids.cpu(); reference_gates = reference_gates.cpu()
            observed_ids = candidate_ids.cpu(); observed_gates = candidate_gates.cpu()
            exact_sets += bool(torch.equal(reference_ids, observed_ids))
            if torch.equal(reference_ids, observed_ids):
                errors = (reference_gates.float() - observed_gates.float()).abs()
                maximum_gate_error = max(maximum_gate_error, float(errors.max()))
                mean_gate_errors.append(float(errors.mean()))
        fixed = inputs[0]
        for _ in range(args.warmups): control(fixed); candidate(fixed)
        torch.mps.synchronize()
        timings = {"pytorch_router_chain": [], "fused_metal_router": []}
        for sample in range(args.timing_samples):
            order = tuple(timings) if sample % 2 == 0 else tuple(reversed(tuple(timings)))
            for condition in order:
                started = time.perf_counter()
                control(fixed) if condition == "pytorch_router_chain" else candidate(fixed)
                torch.mps.synchronize()
                timings[condition].append(time.perf_counter() - started)
    control_summary = _summary(timings["pytorch_router_chain"])
    candidate_summary = _summary(timings["fused_metal_router"])
    p50_gain = 100 * (1 - candidate_summary["p50_seconds"] /
                      control_summary["p50_seconds"])
    p95_gain = 100 * (1 - candidate_summary["p95_seconds_nearest_rank"] /
                      control_summary["p95_seconds_nearest_rank"])
    route_fraction = exact_sets / args.accuracy_samples
    acceptance = {
        "expert_index_agreement_at_least_99_percent": route_fraction >= 0.99,
        "maximum_gate_error_no_more_than_0_002": maximum_gate_error <= 0.002,
        "p50_improved_at_least_40_percent": p50_gain >= 40,
        "p95_improved_at_least_20_percent": p95_gain >= 20,
        "no_duplicate_router_weight_bytes": True,
    }
    report = {
        "schema_version": "aion.fused_metal_router_gate.v1",
        "track": "quality_gated_changed_kernel_not_bit_exact",
        "paths": {"model": str(model_path)},
        "hashes": {"checkpoint_index": _sha256(checkpoint_index)},
        "layer": args.layer, "accuracy_samples": args.accuracy_samples,
        "timing_samples": args.timing_samples, "warmups": args.warmups,
        "seed": args.seed, "router_weight_shape": list(weight.shape),
        "router_weight_dtype": str(weight.dtype), "duplicate_router_weight_bytes": 0,
        "expert_index_agreement_fraction": route_fraction,
        "maximum_gate_error_on_matching_routes": maximum_gate_error,
        "mean_gate_error_on_matching_routes": statistics.mean(mean_gate_errors),
        "control": control_summary, "candidate": candidate_summary,
        "p50_improvement_percent": p50_gain, "p95_improvement_percent": p95_gain,
        "shared_load": shared_load, "acceptance": acceptance,
        "decision": ("ADVANCE_FUSED_METAL_ROUTER_TO_FULL_MODEL_GATE"
                     if all(acceptance.values()) else "STOP_FUSED_METAL_ROUTER_V1"),
        "claim_boundary": (
            "One real BF16 Granite router, synthetic one-token activations and synchronized "
            "latency. Full-model speed, recurrent output quality and semantic preservation are "
            "not established by this narrow gate."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "expert_index_agreement_fraction": route_fraction,
                      "maximum_gate_error": maximum_gate_error,
                      "control": control_summary, "candidate": candidate_summary,
                      "p50_improvement_percent": p50_gain,
                      "p95_improvement_percent": p95_gain,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
