#!/usr/bin/env python3
"""Gate exact-logit Metal selection/grouping for Granite prefill routing."""

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
kernel void clear_counts(device atomic_int* counts [[buffer(0)]],uint i [[thread_position_in_grid]]){
 if(i<40)atomic_store_explicit(&counts[i],0,memory_order_relaxed);}
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
"""


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds":statistics.median(values),"p95_seconds_nearest_rank":_p95(values),
            "mean_seconds":statistics.mean(values)}


def main() -> int:
    p=argparse.ArgumentParser();p.add_argument("--storage-root",type=Path,required=True)
    p.add_argument("--model-path",type=Path,required=True);p.add_argument("--layer",type=int,default=16)
    p.add_argument("--tokens",type=int,default=96);p.add_argument("--accuracy-batches",type=int,default=32)
    p.add_argument("--timing-samples",type=int,default=500);p.add_argument("--warmups",type=int,default=20)
    p.add_argument("--seed",type=int,default=8091835);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();root=args.storage_root.resolve();model_path=args.model_path.resolve();output=args.output.resolve()
    if any(root not in x.parents for x in (model_path,output)) or output.exists():
        raise SystemExit("model/output scope invalid or evidence exists")
    checkpoint=model_path/"model.safetensors.index.json";model,shared=_load_storage_first_model(
        model_path,json.loads(checkpoint.read_text()));router=model.model.layers[args.layer].block_sparse_moe.router
    del model;gc.collect();lib=torch.mps.compile_shader(_shader_source());n=args.tokens*8
    ids=torch.empty(n,dtype=torch.int32,device="mps");gates=torch.empty(n,dtype=torch.float16,device="mps")
    counts=torch.empty(40,dtype=torch.int32,device="mps");batch_index=torch.empty(n,dtype=torch.int32,device="mps")
    batch_gates=torch.empty(n,dtype=torch.float16,device="mps");generator=torch.Generator().manual_seed(args.seed)
    inputs=torch.randn((args.accuracy_batches,args.tokens,router.input_size),generator=generator,
                       dtype=torch.float16).to("mps")

    def candidate(value):
        logits=router.layer(value).float();lib.clear_counts(counts,threads=(40,1,1),group_size=(32,1,1))
        lib.select_routes(logits,ids,gates,counts,40,threads=(args.tokens,1,1),group_size=(1,1,1))
        lib.group_assignments(ids,gates,counts,batch_index,batch_gates,n,
                              threads=(n,1,1),group_size=(32,1,1))
        return batch_index,batch_gates,counts.tolist()

    exact_index=0;exact_size=0;max_gate=0.0
    with torch.inference_mode():
        for value in inputs:
            _,ri,rg,rs,_=router(value);ci,cg,cs=candidate(value);torch.mps.synchronize()
            exact_index+=bool(torch.equal(ri.cpu(),ci.cpu().long()));exact_size+=rs==cs
            max_gate=max(max_gate,float((rg.float()-cg.float()).abs().max()))
        fixed=inputs[0]
        for _ in range(args.warmups):router(fixed);candidate(fixed)
        timings={"pytorch_router_chain":[],"fused_postlinear_router":[]}
        for sample in range(args.timing_samples):
            order=tuple(timings) if sample%2==0 else tuple(reversed(tuple(timings)))
            for condition in order:
                started=time.perf_counter();router(fixed) if condition=="pytorch_router_chain" else candidate(fixed)
                torch.mps.synchronize();timings[condition].append(time.perf_counter()-started)
    control=_summary(timings["pytorch_router_chain"]);cand=_summary(timings["fused_postlinear_router"])
    p50=100*(1-cand["p50_seconds"]/control["p50_seconds"]);p95=100*(1-cand["p95_seconds_nearest_rank"]/control["p95_seconds_nearest_rank"])
    index_fraction=exact_index/args.accuracy_batches;size_fraction=exact_size/args.accuracy_batches
    acceptance={"grouped_batch_index_exact_on_all_batches":index_fraction==1,
                "expert_size_exact_on_all_batches":size_fraction==1,
                "maximum_grouped_gate_error_no_more_than_0_002":max_gate<=.002,
                "p50_improved_at_least_20_percent":p50>=20,"p95_not_regressed":p95>=0}
    report={"schema_version":"aion.fused_postlinear_router_gate.v1",
            "track":"quality_gated_changed_kernel_not_bit_exact","paths":{"model":str(model_path)},
            "hashes":{"checkpoint_index":_sha256(checkpoint)},"layer":args.layer,"tokens":args.tokens,
            "accuracy_batches":args.accuracy_batches,"timing_samples":args.timing_samples,"seed":args.seed,
            "grouped_batch_index_agreement_fraction":index_fraction,"expert_size_agreement_fraction":size_fraction,
            "maximum_grouped_gate_error":max_gate,"control":control,"candidate":cand,
            "p50_improvement_percent":p50,"p95_improvement_percent":p95,"shared_load":shared,
            "acceptance":acceptance,"decision":("ADVANCE_FUSED_POSTLINEAR_ROUTER_TO_MODEL_GATE"
            if all(acceptance.values()) else "STOP_FUSED_POSTLINEAR_ROUTER_V1"),
            "claim_boundary":"One real Granite router, exact PyTorch logits and synthetic 96-token prefill batches. Full-model prompt time and semantics remain unproved."}
    report["report_sha256"]=_canonical_sha256(report);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n");print(json.dumps({"output":str(output),
      "decision":report["decision"],"index_fraction":index_fraction,"size_fraction":size_fraction,
      "maximum_gate_error":max_gate,"control":control,"candidate":cand,"p50_improvement_percent":p50,
      "p95_improvement_percent":p95,"acceptance":acceptance,"report_sha256":report["report_sha256"]},indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
