#!/usr/bin/env python3
"""Gate GPU-resident routing into a contiguous packed-INT8 expert bank."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import time

import torch

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def _shader_source() -> str:
    return """#include <metal_stdlib>
using namespace metal;
kernel void dyn_input(device const half* x [[buffer(0)]], device const char* w [[buffer(1)]],
 device const half* s [[buffer(2)]], device const int* experts [[buffer(3)]],
 device half* out [[buffer(4)]], constant uint& K [[buffer(5)]], constant uint& M [[buffer(6)]],
 uint2 g [[threadgroup_position_in_grid]], uint lane [[thread_index_in_threadgroup]]) {
 uint row=g.x, slot=g.y, e=uint(experts[slot]); float v=0; uint base=(e*M+row)*K;
 for(uint j=lane;j<K;j+=32) v+=float(x[j])*float(w[base+j]); v=simd_sum(v);
 if(lane==0) out[slot*M+row]=half(v*float(s[e*M+row])); }
kernel void dyn_input_silu(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const int* experts [[buffer(3)]], device half* out [[buffer(4)]],
 constant uint& K [[buffer(5)]], constant uint& M [[buffer(6)]],
 uint2 g [[threadgroup_position_in_grid]], uint lane [[thread_index_in_threadgroup]]) {
 uint row=g.x, slot=g.y, e=uint(experts[slot]), H=M/2; float gate=0, projected=0;
 uint gate_base=(e*M+row)*K, projected_base=(e*M+row+H)*K;
 for(uint j=lane;j<K;j+=32){ float value=float(x[j]);
   gate+=value*float(w[gate_base+j]); projected+=value*float(w[projected_base+j]); }
 gate=simd_sum(gate); projected=simd_sum(projected);
 if(lane==0){ half gate_h=half(gate*float(s[e*M+row]));
   half projected_h=half(projected*float(s[e*M+row+H]));
   float gate_f=float(gate_h);
   half silu_h=half(gate_f/(1.0f+fast::exp(-gate_f)));
   out[slot*H+row]=half(float(silu_h)*float(projected_h)); }
}
kernel void dyn_input_silu2(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const int* experts [[buffer(3)]], device half* out [[buffer(4)]],
 constant uint& K [[buffer(5)]], constant uint& M [[buffer(6)]],
 uint2 g [[threadgroup_position_in_grid]], uint tid [[thread_index_in_threadgroup]],
 uint lane [[thread_index_in_simdgroup]], uint projection [[simdgroup_index_in_threadgroup]]) {
 threadgroup half staged[2];uint row=g.x,slot=g.y,e=uint(experts[slot]),H=M/2;
 uint matrix_row=row+projection*H,base=(e*M+matrix_row)*K;float value=0;
 for(uint j=lane;j<K;j+=32)value+=float(x[j])*float(w[base+j]);
 value=simd_sum(value);if(lane==0)staged[projection]=half(value*float(s[e*M+matrix_row]));
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if(tid==0){float gate_f=float(staged[0]);
   half silu_h=half(gate_f/(1.0f+fast::exp(-gate_f)));
   out[slot*H+row]=half(float(silu_h)*float(staged[1]));}
}
kernel void prefill_input_silu(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const long* experts [[buffer(3)]], device half* out [[buffer(4)]],
 constant uint& K [[buffer(5)]], constant uint& M [[buffer(6)]],
 uint2 g [[threadgroup_position_in_grid]], uint lane [[thread_index_in_threadgroup]]) {
 uint row=g.x, assignment=g.y, token=assignment/8, e=uint(experts[assignment]), H=M/2;
 float gate=0, projected=0; uint xb=token*K;
 uint gate_base=(e*M+row)*K, projected_base=(e*M+row+H)*K;
 for(uint j=lane;j<K;j+=32){float value=float(x[xb+j]);
   gate+=value*float(w[gate_base+j]); projected+=value*float(w[projected_base+j]);}
 gate=simd_sum(gate); projected=simd_sum(projected);
 if(lane==0){half gate_h=half(gate*float(s[e*M+row]));
   half projected_h=half(projected*float(s[e*M+row+H]));float gate_f=float(gate_h);
   half silu_h=half(gate_f/(1.0f+fast::exp(-gate_f)));
   out[assignment*H+row]=half(float(silu_h)*float(projected_h));}
}
kernel void prefill_output(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const long* experts [[buffer(3)]], device const half* gates [[buffer(4)]],
 device half* out [[buffer(5)]], constant uint& K [[buffer(6)]],
 constant uint& M [[buffer(7)]], uint2 g [[threadgroup_position_in_grid]],
 uint lane [[thread_index_in_threadgroup]]) {
 uint row=g.x, token=g.y;float total=0;
 for(uint slot=0;slot<8;slot++){uint assignment=token*8+slot,e=uint(experts[assignment]);
   float v=0;uint base=(e*M+row)*K,xb=assignment*K;
   for(uint j=lane;j<K;j+=32)v+=float(x[xb+j])*float(w[base+j]);
   v=simd_sum(v);if(lane==0){half ev=half(v*float(s[e*M+row]));
     total+=float(ev)*float(gates[assignment]);}}
 if(lane==0)out[token*M+row]=half(total);
}
kernel void dyn_output(device const half* x [[buffer(0)]], device const char* w [[buffer(1)]],
 device const half* s [[buffer(2)]], device const int* experts [[buffer(3)]],
 device const half* gates [[buffer(4)]], device half* out [[buffer(5)]],
 constant uint& K [[buffer(6)]], constant uint& M [[buffer(7)]],
 uint row [[threadgroup_position_in_grid]], uint lane [[thread_index_in_threadgroup]]) {
 float total=0; for(uint slot=0;slot<8;slot++){ uint e=uint(experts[slot]); float v=0;
 uint base=(e*M+row)*K, xb=slot*K; for(uint j=lane;j<K;j+=32)
 v+=float(x[xb+j])*float(w[base+j]); v=simd_sum(v); if(lane==0){
 half ev=half(v*float(s[e*M+row])); total+=float(ev)*float(gates[slot]); }}
 if(lane==0) out[row]=half(total); }
kernel void dyn_output_parallel(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const int* experts [[buffer(3)]], device const half* gates [[buffer(4)]],
 device half* out [[buffer(5)]], constant uint& K [[buffer(6)]],
 constant uint& M [[buffer(7)]], uint row [[threadgroup_position_in_grid]],
 uint tid [[thread_index_in_threadgroup]], uint lane [[thread_index_in_simdgroup]],
 uint slot [[simdgroup_index_in_threadgroup]]) {
 threadgroup float contributions[8]; uint e=uint(experts[slot]); float v=0;
 uint base=(e*M+row)*K, xb=slot*K;
 for(uint j=lane;j<K;j+=32) v+=float(x[xb+j])*float(w[base+j]);
 v=simd_sum(v); if(lane==0){ half ev=half(v*float(s[e*M+row]));
   contributions[slot]=float(ev)*float(gates[slot]); }
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if(tid==0){ float total=0; for(uint j=0;j<8;j++)total+=contributions[j];
   out[row]=half(total); }
}
kernel void dyn_output_parallel4(device const half* x [[buffer(0)]],
 device const char* w [[buffer(1)]], device const half* s [[buffer(2)]],
 device const int* experts [[buffer(3)]], device const half* gates [[buffer(4)]],
 device half* out [[buffer(5)]], constant uint& K [[buffer(6)]],
 constant uint& M [[buffer(7)]], uint row [[threadgroup_position_in_grid]],
 uint tid [[thread_index_in_threadgroup]], uint lane [[thread_index_in_simdgroup]],
 uint subgroup [[simdgroup_index_in_threadgroup]]) {
 threadgroup float contributions[8];
 for(uint pair=0;pair<2;pair++){ uint slot=subgroup+pair*4, e=uint(experts[slot]);
   float v=0; uint base=(e*M+row)*K, xb=slot*K;
   for(uint j=lane;j<K;j+=32)v+=float(x[xb+j])*float(w[base+j]);
   v=simd_sum(v); if(lane==0){half ev=half(v*float(s[e*M+row]));
     contributions[slot]=float(ev)*float(gates[slot]);}}
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if(tid==0){float total=0;for(uint j=0;j<8;j++)total+=contributions[j];
   out[row]=half(total);}
}
kernel void fused_route(device const half* x [[buffer(0)]],
 device const half* w [[buffer(1)]], device int* out_ids [[buffer(2)]],
 device half* out_gates [[buffer(3)]], constant uint& K [[buffer(4)]],
 constant uint& E [[buffer(5)]], uint tid [[thread_index_in_threadgroup]],
 uint lane [[thread_index_in_simdgroup]], uint sg [[simdgroup_index_in_threadgroup]]) {
 threadgroup float logits[40];
 for (uint e=sg; e<E; e+=8) { float value=0.0f; uint base=e*K;
   for (uint j=lane; j<K; j+=32) value += float(x[j])*float(w[base+j]);
   value=simd_sum(value); if (lane==0) logits[e]=value; }
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if (tid==0) { float best_v[8]; int best_i[8];
   for (uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
   for (uint e=0;e<E;e++) { float value=logits[e];
     for (uint pos=0;pos<8;pos++) if (value>best_v[pos]) {
       for (uint move=7;move>pos;move--){best_v[move]=best_v[move-1];best_i[move]=best_i[move-1];}
       best_v[pos]=value;best_i[pos]=int(e);break; } }
   float maximum=best_v[0], denominator=0.0f, probabilities[8];
   for (uint j=0;j<8;j++){probabilities[j]=exp(best_v[j]-maximum);denominator+=probabilities[j];}
   for (uint left=0;left<8;left++) for (uint right=left+1;right<8;right++)
     if(best_i[right]<best_i[left]){ int ti=best_i[left];best_i[left]=best_i[right];best_i[right]=ti;
       float tv=probabilities[left];probabilities[left]=probabilities[right];probabilities[right]=tv; }
   for (uint j=0;j<8;j++){out_ids[j]=best_i[j];out_gates[j]=half(probabilities[j]/denominator);} }
}
kernel void clear_counts(device atomic_int* counts [[buffer(0)]],uint i [[thread_position_in_grid]]){
 if(i<40)atomic_store_explicit(&counts[i],0,memory_order_relaxed);}
kernel void count_routes(device const long* ids [[buffer(0)]],device atomic_int* counts [[buffer(1)]],
 constant uint& assignments [[buffer(2)]],uint a [[thread_position_in_grid]]){
 if(a<assignments)atomic_fetch_add_explicit(&counts[int(ids[a])],1,memory_order_relaxed);}
kernel void group_exact_by_expert(device const long* ids [[buffer(0)]],device const half* gates [[buffer(1)]],
 device const atomic_int* counts [[buffer(2)]],device int* batch_index [[buffer(3)]],
 device half* batch_gates [[buffer(4)]],constant uint& assignments [[buffer(5)]],
 uint expert [[thread_position_in_grid]]){if(expert>=40)return;uint position=0;
 for(uint e=0;e<expert;e++)position+=uint(atomic_load_explicit(&counts[e],memory_order_relaxed));
 for(uint a=0;a<assignments;a++)if(ids[a]==long(expert)){
  batch_index[position]=int(a/8);batch_gates[position]=gates[a];position++;}}
kernel void group_count_exact(device const long* ids [[buffer(0)]],
 device const half* gates [[buffer(1)]], device int* counts [[buffer(2)]],
 device int* batch_index [[buffer(3)]], device half* batch_gates [[buffer(4)]],
 constant uint& assignments [[buffer(5)]], uint expert [[thread_index_in_threadgroup]]) {
 threadgroup uint local_counts[40];
 if(expert<40){uint count=0;for(uint a=0;a<assignments;a++)count+=ids[a]==long(expert);
   local_counts[expert]=count;counts[expert]=int(count);}
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if(expert<40){uint position=0;for(uint e=0;e<expert;e++)position+=local_counts[e];
   for(uint a=0;a<assignments;a++)if(ids[a]==long(expert)){
     batch_index[position]=int(a/8);batch_gates[position]=gates[a];position++;}}
}
kernel void select_routes(device const float* logits [[buffer(0)]],device int* ids [[buffer(1)]],
 device half* gates [[buffer(2)]],device atomic_int* counts [[buffer(3)]],
 constant uint& E [[buffer(4)]],uint token [[thread_position_in_grid]]){
 float best_v[8];int best_i[8];for(uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
 uint lb=token*E;for(uint e=0;e<E;e++){float value=logits[lb+e];
  for(uint pos=0;pos<8;pos++)if(value>best_v[pos]){
   for(uint move=7;move>pos;move--){best_v[move]=best_v[move-1];best_i[move]=best_i[move-1];}
   best_v[pos]=value;best_i[pos]=int(e);break;}}
 float maximum=best_v[0],denominator=0.0f,probabilities[8];
 for(uint j=0;j<8;j++){probabilities[j]=exp(best_v[j]-maximum);denominator+=probabilities[j];}
 for(uint left=0;left<8;left++)for(uint right=left+1;right<8;right++)if(best_i[right]<best_i[left]){
  int ti=best_i[left];best_i[left]=best_i[right];best_i[right]=ti;
  float tv=probabilities[left];probabilities[left]=probabilities[right];probabilities[right]=tv;}
 uint base=token*8;for(uint j=0;j<8;j++){ids[base+j]=best_i[j];
  gates[base+j]=half(probabilities[j]/denominator);
  atomic_fetch_add_explicit(&counts[best_i[j]],1,memory_order_relaxed);}}
kernel void group_assignments(device const int* ids [[buffer(0)]],device const half* gates [[buffer(1)]],
 device const atomic_int* counts [[buffer(2)]],device int* batch_index [[buffer(3)]],
 device half* batch_gates [[buffer(4)]],constant uint& assignments [[buffer(5)]],
 uint a [[thread_position_in_grid]]){if(a>=assignments)return;int expert=ids[a];uint position=0;
 for(int e=0;e<expert;e++)position+=uint(atomic_load_explicit(&counts[e],memory_order_relaxed));
 for(uint prior=0;prior<a;prior++)if(ids[prior]==expert)position++;
 batch_index[position]=int(a/8);batch_gates[position]=gates[a];}
kernel void select_decode(device const float* logits [[buffer(0)]],device int* ids [[buffer(1)]],
 device half* gates [[buffer(2)]],constant uint& E [[buffer(3)]],uint tid [[thread_position_in_grid]]){
 if(tid>0)return;float best_v[8];int best_i[8];for(uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
 for(uint e=0;e<E;e++){float value=logits[e];for(uint pos=0;pos<8;pos++)if(value>best_v[pos]){
  for(uint move=7;move>pos;move--){best_v[move]=best_v[move-1];best_i[move]=best_i[move-1];}
  best_v[pos]=value;best_i[pos]=int(e);break;}}
 float maximum=best_v[0],denominator=0.0f,probabilities[8];
 for(uint j=0;j<8;j++){probabilities[j]=precise::exp(best_v[j]-maximum);denominator+=probabilities[j];}
 for(uint left=0;left<8;left++)for(uint right=left+1;right<8;right++)if(best_i[right]<best_i[left]){
  int ti=best_i[left];best_i[left]=best_i[right];best_i[right]=ti;
  float tv=probabilities[left];probabilities[left]=probabilities[right];probabilities[right]=tv;}
 for(uint j=0;j<8;j++){ids[j]=best_i[j];gates[j]=half(probabilities[j]/denominator);}}
"""


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091657)
    parser.add_argument("--maximum-extra-error", type=float, default=0.00075)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    glyph_path = args.glyph_manifest.resolve()
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (model_path, glyph_path, output_path)):
        raise SystemExit("model, weights and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    glyph = json.loads(glyph_path.read_text())
    checkpoint_index_path = model_path / "model.safetensors.index.json"
    checkpoint_index = json.loads(checkpoint_index_path.read_text())
    model, _ = _load_storage_first_model(model_path, checkpoint_index)
    source_moe = model.model.layers[args.layer].block_sparse_moe
    entries = load_layer_entries(glyph, args.layer, root, _sha256)
    moe = Int8GlyphMoE(source_moe, entries, root, _sha256, "mps",
                       skip_empty_experts=True).eval()
    del model
    gc.collect()
    inputs = []; input_scales = []; outputs = []; output_scales = []
    for index in range(40):
        weight_in, scale_in, weight_out, scale_out = moe.experts._weights(index)
        inputs.append(weight_in); input_scales.append(scale_in)
        outputs.append(weight_out); output_scales.append(scale_out)
    input_bank = torch.stack(inputs); input_scale_bank = torch.stack(input_scales)
    output_bank = torch.stack(outputs); output_scale_bank = torch.stack(output_scales)
    logical_source_bytes = sum(t.numel() * t.element_size() for group in
                               (inputs, input_scales, outputs, output_scales) for t in group)
    logical_bank_bytes = sum(t.numel() * t.element_size() for t in
                             (input_bank, input_scale_bank, output_bank, output_scale_bank))
    generator = torch.Generator().manual_seed(args.seed)
    values = torch.randn((1, 1, input_bank.shape[2]), generator=generator,
                         dtype=torch.float16).to("mps")
    hidden = torch.empty((8, input_bank.shape[1]), dtype=torch.float16, device="mps")
    final = torch.empty((output_bank.shape[1],), dtype=torch.float16, device="mps")
    library = torch.mps.compile_shader(_shader_source())

    @torch.inference_mode()
    def candidate():
        flat = values.reshape(-1, values.shape[-1])
        logits = moe.router.layer(flat).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        gates = torch.softmax(top_logits, dim=1).type_as(flat)
        top_indices, order = top_indices.sort(dim=1)
        gates = gates.gather(1, order)
        expert_indices = top_indices[0].to(torch.int32)
        library.dyn_input(flat, input_bank, input_scale_bank, expert_indices, hidden,
                          input_bank.shape[2], input_bank.shape[1],
                          threads=(input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1))
        gate, projected = hidden.chunk(2, dim=-1)
        activated = moe.activation(gate) * projected
        library.dyn_output(activated, output_bank, output_scale_bank, expert_indices,
                           gates[0], final, output_bank.shape[2], output_bank.shape[1],
                           threads=(output_bank.shape[1] * 32, 1, 1), group_size=(32, 1, 1))
        return final.view(1, 1, -1)

    with torch.inference_mode():
        for _ in range(args.warmups):
            moe(values); candidate()
        torch.mps.synchronize()
        timings = {"python_routed_sparse_int8": [], "gpu_dynamic_bank": []}
        observed = {}
        conditions = tuple(timings)
        for sample in range(args.samples):
            order = conditions if sample % 2 == 0 else tuple(reversed(conditions))
            for condition in order:
                started = time.perf_counter()
                result = moe(values) if condition == "python_routed_sparse_int8" else candidate()
                torch.mps.synchronize()
                timings[condition].append(time.perf_counter() - started)
                observed[condition] = result.detach().clone().cpu()
    control = _summary(timings["python_routed_sparse_int8"])
    candidate_summary = _summary(timings["gpu_dynamic_bank"])
    p50_gain = 100 * (1 - candidate_summary["p50_seconds"] / control["p50_seconds"])
    p95_gain = 100 * (1 - candidate_summary["p95_seconds_nearest_rank"] /
                      control["p95_seconds_nearest_rank"])
    difference = (observed["python_routed_sparse_int8"].float() -
                  observed["gpu_dynamic_bank"].float()).abs()
    maximum_error = float(difference.max())
    acceptance = {"p50_improved_at_least_20_percent": p50_gain >= 20,
                  "p95_improved_at_least_10_percent": p95_gain >= 10,
                  "extra_maximum_error_within_ceiling": maximum_error <= args.maximum_extra_error,
                  "bank_logical_weight_bytes_equal_source": logical_bank_bytes == logical_source_bytes,
                  "router_indices_remain_gpu_resident": True}
    report = {"schema_version": "aion.int8_dynamic_bank_moe_gate.v1",
              "track": "quality_gated_changed_kernel_not_bit_exact",
              "paths": {"model": str(model_path), "glyph_manifest": str(glyph_path)},
              "hashes": {"glyph_manifest": _sha256(glyph_path),
                         "checkpoint_index": _sha256(checkpoint_index_path)},
              "layer": args.layer, "samples": args.samples, "warmups": args.warmups,
              "seed": args.seed, "logical_source_weight_bytes": logical_source_bytes,
              "logical_bank_weight_bytes": logical_bank_bytes,
              "prototype_temporary_duplicate_bank_bytes": logical_bank_bytes,
              "deployable_steady_state_duplicate_weight_bytes": 0,
              "control": control, "candidate": candidate_summary,
              "aggregate": {"p50_improvement_percent": p50_gain,
                            "p95_improvement_percent": p95_gain,
                            "maximum_output_error": maximum_error,
                            "output_rmse": float(torch.sqrt(torch.mean(difference.square())))},
              "acceptance": acceptance,
              "decision": ("ADVANCE_DYNAMIC_BANK_TO_STORAGE_LAYOUT_BUILD"
                           if all(acceptance.values()) else "STOP_DYNAMIC_BANK_MOE_V1"),
              "claim_boundary": ("One real Granite layer with synthetic one-token activation. "
                                 "The prototype temporarily duplicates one layer bank; full storage "
                                 "layout, model throughput and semantic quality are not established.")}
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "control": control, "candidate": candidate_summary,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
