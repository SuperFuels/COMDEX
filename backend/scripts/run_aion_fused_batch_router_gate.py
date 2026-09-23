#!/usr/bin/env python3
"""Gate a fused Metal router for multi-token Granite prefill."""

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
kernel void clear_counts(device atomic_int* counts [[buffer(0)]],
 uint i [[thread_position_in_grid]]) { if(i<40) atomic_store_explicit(&counts[i],0,memory_order_relaxed); }
kernel void batch_route(device const half* x [[buffer(0)]], device const half* w [[buffer(1)]],
 device int* ids [[buffer(2)]], device half* gates [[buffer(3)]],
 device atomic_int* counts [[buffer(4)]], constant uint& K [[buffer(5)]],
 constant uint& E [[buffer(6)]], uint token [[threadgroup_position_in_grid]],
 uint tid [[thread_index_in_threadgroup]], uint lane [[thread_index_in_simdgroup]],
 uint sg [[simdgroup_index_in_threadgroup]]) {
 threadgroup float logits[40]; uint xb=token*K;
 for(uint e=sg;e<E;e+=8){float value=0.0f;uint wb=e*K;
   for(uint j=lane;j<K;j+=32)value+=float(x[xb+j])*float(w[wb+j]);
   value=simd_sum(value);if(lane==0)logits[e]=value;}
 threadgroup_barrier(mem_flags::mem_threadgroup);
 if(tid==0){float best_v[8];int best_i[8];
   for(uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
   for(uint e=0;e<E;e++){float value=logits[e];for(uint pos=0;pos<8;pos++)if(value>best_v[pos]){
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
}
kernel void group_assignments(device const int* ids [[buffer(0)]],
 device const half* gates [[buffer(1)]], device const atomic_int* counts [[buffer(2)]],
 device int* batch_index [[buffer(3)]], device half* batch_gates [[buffer(4)]],
 constant uint& assignments [[buffer(5)]], uint a [[thread_position_in_grid]]) {
 if(a>=assignments)return;int expert=ids[a];uint position=0;
 for(int e=0;e<expert;e++)position+=uint(atomic_load_explicit(&counts[e],memory_order_relaxed));
 for(uint prior=0;prior<a;prior++)if(ids[prior]==expert)position++;
 batch_index[position]=int(a/8);batch_gates[position]=gates[a];
}
"""


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values), "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--tokens", type=int, default=96)
    parser.add_argument("--accuracy-batches", type=int, default=32)
    parser.add_argument("--timing-samples", type=int, default=500)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091834)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root=args.storage_root.resolve(); model_path=args.model_path.resolve(); output=args.output.resolve()
    if any(root not in path.parents for path in (model_path,output)) or output.exists():
        raise SystemExit("model/output scope invalid or evidence already exists")
    checkpoint=model_path/"model.safetensors.index.json"
    model,shared_load=_load_storage_first_model(model_path,json.loads(checkpoint.read_text()))
    router=model.model.layers[args.layer].block_sparse_moe.router
    weight=router.layer.weight; del model; gc.collect()
    lib=torch.mps.compile_shader(_shader_source())
    assignments=args.tokens*8
    ids=torch.empty((assignments,),dtype=torch.int32,device="mps")
    gates=torch.empty((assignments,),dtype=torch.float16,device="mps")
    counts=torch.empty((40,),dtype=torch.int32,device="mps")
    batch_index=torch.empty((assignments,),dtype=torch.int32,device="mps")
    batch_gates=torch.empty((assignments,),dtype=torch.float16,device="mps")
    generator=torch.Generator().manual_seed(args.seed)
    inputs=torch.randn((args.accuracy_batches,args.tokens,weight.shape[1]),generator=generator,
                       dtype=torch.float16).to("mps")

    def candidate(value):
        lib.clear_counts(counts,threads=(40,1,1),group_size=(32,1,1))
        lib.batch_route(value,weight,ids,gates,counts,weight.shape[1],40,
                        threads=(args.tokens*256,1,1),group_size=(256,1,1))
        lib.group_assignments(ids,gates,counts,batch_index,batch_gates,assignments,
                              threads=(assignments,1,1),group_size=(32,1,1))
        sizes=counts.tolist()
        return batch_index,batch_gates,sizes

    exact_index_batches=0; exact_size_batches=0; maximum_gate_error=0.0
    with torch.inference_mode():
        for value in inputs:
            _,reference_index,reference_gates,reference_sizes,_=router(value)
            observed_index,observed_gates,observed_sizes=candidate(value)
            torch.mps.synchronize()
            exact_index_batches+=bool(torch.equal(reference_index.cpu(),observed_index.cpu().long()))
            exact_size_batches+=reference_sizes==observed_sizes
            maximum_gate_error=max(maximum_gate_error,float(
                (reference_gates.float()-observed_gates.float()).abs().max()))
        fixed=inputs[0]
        for _ in range(args.warmups):router(fixed);candidate(fixed)
        timings={"pytorch_prefill_router":[],"fused_metal_prefill_router":[]}
        for sample in range(args.timing_samples):
            order=tuple(timings) if sample%2==0 else tuple(reversed(tuple(timings)))
            for condition in order:
                started=time.perf_counter()
                router(fixed) if condition=="pytorch_prefill_router" else candidate(fixed)
                torch.mps.synchronize();timings[condition].append(time.perf_counter()-started)
    control=_summary(timings["pytorch_prefill_router"]); cand=_summary(timings["fused_metal_prefill_router"])
    p50=100*(1-cand["p50_seconds"]/control["p50_seconds"])
    p95=100*(1-cand["p95_seconds_nearest_rank"]/control["p95_seconds_nearest_rank"])
    index_fraction=exact_index_batches/args.accuracy_batches
    size_fraction=exact_size_batches/args.accuracy_batches
    acceptance={"grouped_batch_index_agreement_at_least_95_percent":index_fraction>=.95,
                "expert_size_agreement_at_least_99_percent":size_fraction>=.99,
                "maximum_grouped_gate_error_no_more_than_0_005":maximum_gate_error<=.005,
                "p50_improved_at_least_20_percent":p50>=20,
                "p95_not_regressed":p95>=0}
    report={"schema_version":"aion.fused_batch_router_gate.v1",
            "track":"quality_gated_changed_kernel_not_bit_exact","paths":{"model":str(model_path)},
            "hashes":{"checkpoint_index":_sha256(checkpoint)},"layer":args.layer,"tokens":args.tokens,
            "accuracy_batches":args.accuracy_batches,"timing_samples":args.timing_samples,
            "seed":args.seed,"grouped_batch_index_agreement_fraction":index_fraction,
            "expert_size_agreement_fraction":size_fraction,"maximum_grouped_gate_error":maximum_gate_error,
            "control":control,"candidate":cand,"p50_improvement_percent":p50,
            "p95_improvement_percent":p95,"shared_load":shared_load,"acceptance":acceptance,
            "decision":("ADVANCE_FUSED_BATCH_ROUTER_TO_MODEL_GATE" if all(acceptance.values())
                        else "STOP_FUSED_BATCH_ROUTER_V1"),
            "claim_boundary":"One real Granite router and synthetic 96-token prefill batches. Full-model prompt time and semantic preservation remain unproved."}
    report["report_sha256"]=_canonical_sha256(report);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"output":str(output),"decision":report["decision"],"index_fraction":index_fraction,
                      "size_fraction":size_fraction,"maximum_gate_error":maximum_gate_error,
                      "control":control,"candidate":cand,"p50_improvement_percent":p50,
                      "p95_improvement_percent":p95,"acceptance":acceptance,
                      "report_sha256":report["report_sha256"]},indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
