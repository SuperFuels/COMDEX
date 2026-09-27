#!/usr/bin/env python3
"""Gate Metal expert counting/grouping after exact PyTorch prefill routing."""

from __future__ import annotations

import argparse,gc,json,statistics,time
from pathlib import Path
import torch
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def _shader_source()->str:return r"""#include <metal_stdlib>
using namespace metal;
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
kernel void group_count_exact(device const long* ids [[buffer(0)]],device const half* gates [[buffer(1)]],
 device int* counts [[buffer(2)]],device int* batch_index [[buffer(3)]],
 device half* batch_gates [[buffer(4)]],constant uint& assignments [[buffer(5)]],
 uint expert [[thread_index_in_threadgroup]]){threadgroup uint local_counts[40];
 if(expert<40){uint count=0;for(uint a=0;a<assignments;a++)count+=ids[a]==long(expert);
  local_counts[expert]=count;counts[expert]=int(count);}threadgroup_barrier(mem_flags::mem_threadgroup);
 if(expert<40){uint position=0;for(uint e=0;e<expert;e++)position+=local_counts[e];
  for(uint a=0;a<assignments;a++)if(ids[a]==long(expert)){batch_index[position]=int(a/8);
   batch_gates[position]=gates[a];position++;}}}
"""


def _summary(v):return {"p50_seconds":statistics.median(v),"p95_seconds_nearest_rank":_p95(v),"mean_seconds":statistics.mean(v)}


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--storage-root",type=Path,required=True);p.add_argument("--model-path",type=Path,required=True)
 p.add_argument("--layer",type=int,default=16);p.add_argument("--tokens",type=int,default=96);p.add_argument("--accuracy-batches",type=int,default=32)
 p.add_argument("--timing-samples",type=int,default=500);p.add_argument("--warmups",type=int,default=20);p.add_argument("--seed",type=int,default=8091838)
 p.add_argument("--output",type=Path,required=True);a=p.parse_args();root=a.storage_root.resolve();model_path=a.model_path.resolve();output=a.output.resolve()
 if any(root not in x.parents for x in (model_path,output)) or output.exists():raise SystemExit("scope invalid or output exists")
 checkpoint=model_path/"model.safetensors.index.json";model,shared=_load_storage_first_model(model_path,json.loads(checkpoint.read_text()))
 router=model.model.layers[a.layer].block_sparse_moe.router;del model;gc.collect();lib=torch.mps.compile_shader(_shader_source());n=a.tokens*8
 counts=torch.empty(40,dtype=torch.int32,device="mps");batch_index=torch.empty(n,dtype=torch.int32,device="mps")
 batch_gates=torch.empty(n,dtype=torch.float16,device="mps");g=torch.Generator().manual_seed(a.seed)
 inputs=torch.randn((a.accuracy_batches,a.tokens,router.input_size),generator=g,dtype=torch.float16).to("mps")
 def candidate(value):
  logits=router.layer(value).float();top_logits,top_indices=logits.topk(8,dim=1);top_gates=torch.softmax(top_logits,dim=1).type_as(value)
  flat_ids=top_indices.flatten();flat_gates=top_gates.flatten();lib.group_count_exact(
    flat_ids,flat_gates,counts,batch_index,batch_gates,n,threads=(64,1,1),group_size=(64,1,1));return batch_index,batch_gates,counts.tolist()
 exact_i=exact_s=exact_g=0
 with torch.inference_mode():
  for value in inputs:
   _,ri,rg,rs,_=router(value);ci,cg,cs=candidate(value);torch.mps.synchronize();exact_i+=bool(torch.equal(ri.cpu(),ci.cpu().long()))
   exact_s+=rs==cs;exact_g+=bool(torch.equal(rg.cpu(),cg.cpu()))
  fixed=inputs[0]
  for _ in range(a.warmups):router(fixed);candidate(fixed)
  timings={"pytorch_router_chain":[],"exact_route_fused_grouping":[]}
  for sample in range(a.timing_samples):
   order=tuple(timings) if sample%2==0 else tuple(reversed(tuple(timings)))
   for condition in order:
    started=time.perf_counter();router(fixed) if condition=="pytorch_router_chain" else candidate(fixed)
    torch.mps.synchronize();timings[condition].append(time.perf_counter()-started)
 control=_summary(timings["pytorch_router_chain"]);cand=_summary(timings["exact_route_fused_grouping"])
 p50=100*(1-cand["p50_seconds"]/control["p50_seconds"]);p95=100*(1-cand["p95_seconds_nearest_rank"]/control["p95_seconds_nearest_rank"])
 fi=exact_i/a.accuracy_batches;fs=exact_s/a.accuracy_batches;fg=exact_g/a.accuracy_batches
 acceptance={"batch_index_exact_on_all_batches":fi==1,"expert_sizes_exact_on_all_batches":fs==1,"batch_gates_bit_exact_on_all_batches":fg==1,
             "p50_improved_at_least_10_percent":p50>=10,"p95_not_regressed":p95>=0}
 report={"schema_version":"aion.exact_prefill_grouping_gate.v3","track":"exact_route_and_gate_values","paths":{"model":str(model_path)},
  "hashes":{"checkpoint_index":_sha256(checkpoint)},"layer":a.layer,"tokens":a.tokens,"accuracy_batches":a.accuracy_batches,
  "timing_samples":a.timing_samples,"seed":a.seed,"batch_index_exact_fraction":fi,"expert_size_exact_fraction":fs,"batch_gates_bit_exact_fraction":fg,
  "control":control,"candidate":cand,"p50_improvement_percent":p50,"p95_improvement_percent":p95,"shared_load":shared,"acceptance":acceptance,
  "decision":("ADVANCE_EXACT_PREFILL_GROUPING_TO_MODEL_GATE" if all(acceptance.values()) else "STOP_EXACT_PREFILL_GROUPING_V1"),
  "claim_boundary":"One real Granite router and synthetic 96-token prefill batches. Original logits, top-k and softmax are retained; full-model prompt time remains unproved."}
 report["report_sha256"]=_canonical_sha256(report);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"output":str(output),"decision":report["decision"],"index":fi,"sizes":fs,"gates":fg,"control":control,"candidate":cand,
  "p50_improvement_percent":p50,"p95_improvement_percent":p95,"acceptance":acceptance,"report_sha256":report["report_sha256"]},indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
