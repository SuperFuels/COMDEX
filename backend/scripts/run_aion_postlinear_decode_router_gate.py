#!/usr/bin/env python3
"""Gate exact-logit one-token Metal selection for stable Granite decoding."""

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
kernel void select_decode_ids(device const float* logits [[buffer(0)]],device long* ids [[buffer(1)]],
 constant uint& E [[buffer(2)]],uint tid [[thread_position_in_grid]]){
 if(tid>0)return;float best_v[8];long best_i[8];for(uint j=0;j<8;j++){best_v[j]=-INFINITY;best_i[j]=-1;}
 for(uint e=0;e<E;e++){float value=logits[e];for(uint pos=0;pos<8;pos++)if(value>best_v[pos]){
  for(uint move=7;move>pos;move--){best_v[move]=best_v[move-1];best_i[move]=best_i[move-1];}
  best_v[pos]=value;best_i[pos]=long(e);break;}}
 for(uint j=0;j<8;j++)ids[j]=best_i[j];}
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


def _summary(values: list[float]) -> dict[str,float]:
    return {"p50_seconds":statistics.median(values),"p95_seconds_nearest_rank":_p95(values),
            "mean_seconds":statistics.mean(values)}


def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--storage-root",type=Path,required=True)
    p.add_argument("--model-path",type=Path,required=True);p.add_argument("--layer",type=int,default=16)
    p.add_argument("--accuracy-samples",type=int,default=256);p.add_argument("--timing-samples",type=int,default=1000)
    p.add_argument("--warmups",type=int,default=20);p.add_argument("--seed",type=int,default=8091837)
    p.add_argument("--output",type=Path,required=True);args=p.parse_args();root=args.storage_root.resolve()
    model_path=args.model_path.resolve();output=args.output.resolve()
    if any(root not in x.parents for x in (model_path,output)) or output.exists():raise SystemExit("scope invalid or output exists")
    checkpoint=model_path/"model.safetensors.index.json";model,shared=_load_storage_first_model(model_path,json.loads(checkpoint.read_text()))
    router=model.model.layers[args.layer].block_sparse_moe.router;del model;gc.collect();lib=torch.mps.compile_shader(_shader_source())
    ids=torch.empty(8,dtype=torch.int32,device="mps");gates=torch.empty(8,dtype=torch.float16,device="mps")
    generator=torch.Generator().manual_seed(args.seed);inputs=torch.randn((args.accuracy_samples,router.input_size),
      generator=generator,dtype=torch.float16).to("mps")
    def control(value):
        logits=router.layer(value.view(1,-1)).float();top_logits,top_indices=logits.topk(8,dim=1)
        top_gates=torch.softmax(top_logits,dim=1).type_as(value);top_indices,order=top_indices.sort(dim=1)
        return top_indices[0].to(torch.int32),top_gates.gather(1,order)[0]
    def candidate(value):
        logits=router.layer(value.view(1,-1)).float();lib.select_decode(logits,ids,gates,40,
          threads=(1,1,1),group_size=(1,1,1));return ids,gates
    exact=0;max_gate=0.0
    with torch.inference_mode():
      for value in inputs:
        ri,rg=control(value);ci,cg=candidate(value);torch.mps.synchronize();exact+=bool(torch.equal(ri.cpu(),ci.cpu()))
        max_gate=max(max_gate,float((rg.float()-cg.float()).abs().max()))
      fixed=inputs[0]
      for _ in range(args.warmups):control(fixed);candidate(fixed)
      timings={"pytorch_router_chain":[],"precise_postlinear_metal_router":[]}
      for sample in range(args.timing_samples):
       order=tuple(timings) if sample%2==0 else tuple(reversed(tuple(timings)))
       for condition in order:
        started=time.perf_counter();control(fixed) if condition=="pytorch_router_chain" else candidate(fixed)
        torch.mps.synchronize();timings[condition].append(time.perf_counter()-started)
    control_s=_summary(timings["pytorch_router_chain"]);candidate_s=_summary(timings["precise_postlinear_metal_router"])
    p50=100*(1-candidate_s["p50_seconds"]/control_s["p50_seconds"]);p95=100*(1-candidate_s["p95_seconds_nearest_rank"]/control_s["p95_seconds_nearest_rank"])
    agreement=exact/args.accuracy_samples;acceptance={"expert_indices_exact_on_all_samples":agreement==1,
      "maximum_gate_error_no_more_than_0_002":max_gate<=.002,"p50_improved_at_least_30_percent":p50>=30,
      "p95_improved_at_least_15_percent":p95>=15}
    report={"schema_version":"aion.postlinear_decode_router_gate.v3","track":"quality_gated_changed_kernel_not_bit_exact",
      "paths":{"model":str(model_path)},"hashes":{"checkpoint_index":_sha256(checkpoint)},"layer":args.layer,
      "accuracy_samples":args.accuracy_samples,"timing_samples":args.timing_samples,"seed":args.seed,
      "expert_index_agreement_fraction":agreement,"maximum_gate_error":max_gate,"control":control_s,
      "candidate":candidate_s,"p50_improvement_percent":p50,"p95_improvement_percent":p95,"shared_load":shared,
      "acceptance":acceptance,"decision":("ADVANCE_PRECISE_POSTLINEAR_DECODE_ROUTER_TO_MODEL_GATE" if all(acceptance.values()) else "STOP_PRECISE_POSTLINEAR_DECODE_ROUTER_V3"),
      "claim_boundary":"One real Granite router and synthetic one-token activations. Metal precise exponential is used for gate normalization. Full-model speed, long repeatability and semantics remain unproved."}
    report["report_sha256"]=_canonical_sha256(report);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n");print(json.dumps({"output":str(output),"decision":report["decision"],
      "agreement":agreement,"maximum_gate_error":max_gate,"control":control_s,"candidate":candidate_s,
      "p50_improvement_percent":p50,"p95_improvement_percent":p95,"acceptance":acceptance,
      "report_sha256":report["report_sha256"]},indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
