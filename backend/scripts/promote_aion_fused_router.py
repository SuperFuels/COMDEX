#!/usr/bin/env python3
"""Bind fused decode/prefill router evidence into a final promotion decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text());claimed=value.get("report_sha256")
    canonical={key:item for key,item in value.items() if key!="report_sha256"}
    if claimed!=_canonical_sha256(canonical):raise ValueError(f"canonical hash failed: {path}")
    return value


def _repeatability(report: dict[str, Any], condition: str) -> float:
    exact=0;families=report["prompt_families"]
    for family in families:
        runs=sorted((item for item in report["runs"] if item["family"]==family and
                     item["condition"]==condition),key=lambda item:item["sequence"])
        if len(runs)!=2:raise ValueError(f"expected two {condition} runs for {family}")
        exact+=runs[0]["token_ids"]==runs[1]["token_ids"]
    return exact/len(families)


def _generation(report: dict[str, Any]) -> dict[str, Any]:
    return {"tokens_per_run":report["generated_tokens_per_run"],
            "family_count":len(report["prompt_families"]),
            "total_measured_tokens":sum(len(item["token_ids"]) for item in report["runs"]),
            "control_tokens_per_second":report["control"]["median_tokens_per_second"],
            "candidate_tokens_per_second":report["candidate"]["median_tokens_per_second"],
            "throughput_improvement_percent":report["aggregate"]["median_throughput_improvement_percent"],
            "p95_time_improvement_percent":report["aggregate"]["p95_generation_time_improvement_percent"],
            "control_repeatability_fraction":_repeatability(report,"dynamic_bank_pytorch_router"),
            "candidate_repeatability_fraction":_repeatability(report,"dynamic_bank_fused_router")}


def main() -> int:
    p=argparse.ArgumentParser();p.add_argument("--storage-root",type=Path,required=True)
    for name in ("decode_gate","prefill_gate","generation_64","generation_128","generation_256",
                 "teacher_quality","semantic_quality"):
        p.add_argument("--"+name.replace("_","-"),dest=name,type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);args=p.parse_args();root=args.storage_root.resolve()
    paths={name:getattr(args,name).resolve() for name in ("decode_gate","prefill_gate","generation_64",
           "generation_128","generation_256","teacher_quality","semantic_quality")}
    output=args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(),output)) or output.exists():
        raise SystemExit("evidence scope invalid or output exists")
    reports={name:_load(path) for name,path in paths.items()};g64=_generation(reports["generation_64"])
    g128=_generation(reports["generation_128"]);g256=_generation(reports["generation_256"])
    rate_drop=100*(1-g256["candidate_tokens_per_second"]/g128["candidate_tokens_per_second"])
    teacher=reports["teacher_quality"];semantic=reports["semantic_quality"]
    acceptance={
      "decode_router_narrow_gate_passed":reports["decode_gate"]["decision"]=="ADVANCE_FUSED_METAL_ROUTER_TO_FULL_MODEL_GATE" and all(reports["decode_gate"]["acceptance"].values()),
      "prefill_router_narrow_gate_passed":reports["prefill_gate"]["decision"]=="ADVANCE_FUSED_POSTLINEAR_ROUTER_TO_MODEL_GATE" and all(reports["prefill_gate"]["acceptance"].values()),
      "all_generation_mechanism_gates_passed":all(all(reports[name]["acceptance"].values()) for name in ("generation_64","generation_128","generation_256")),
      "all_generation_lengths_exceed_30_tokens_per_second":all(item["candidate_tokens_per_second"]>=30 for item in (g64,g128,g256)),
      "256_rate_drop_from_128_no_more_than_10_percent":rate_drop<=10,
      "candidate_repeatability_not_below_control_at_128_and_256":all(item["candidate_repeatability_fraction"]>=item["control_repeatability_fraction"] for item in (g128,g256)),
      "teacher_quality_gate_passed":teacher["decision"]=="ADVANCE_FUSED_ROUTER_TO_FROZEN_SEMANTIC_GATE" and all(teacher["acceptance"].values()),
      "unchanged_semantic_gate_passed":semantic["decision"]=="PROMOTE_FUSED_ROUTER_WITHIN_VALIDATED_BOUNDARY" and all(semantic["acceptance"].values())}
    report={"schema_version":"aion.fused_router_promotion.v1","track":"quality_gated_changed_kernel_not_bit_exact",
      "paths":{name:str(path) for name,path in paths.items()},
      "hashes":{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()},
      "generation_64":g64,"generation_128":g128,"generation_256":g256,
      "candidate_rate_drop_128_to_256_percent":rate_drop,
      "teacher":{"positions":teacher["forced_positions"],"dynamic":teacher["dynamic_aggregate"],
                 "fused":teacher["fused_aggregate"],"speed_improvement_percent":teacher["fused_vs_dynamic_teacher_time_improvement_percent"]},
      "semantic":{"answer_agreement_fraction":semantic["answer_agreement_fraction"],
                  "dynamic":semantic["dynamic"],"fused":semantic["fused"],
                  "throughput_improvement_percent":semantic["throughput_improvement_percent"]},
      "acceptance":acceptance,"decision":("PROMOTE_FUSED_ROUTER_30_PLUS_TPS_BOUNDARY" if all(acceptance.values()) else "DO_NOT_PROMOTE_FUSED_ROUTER"),
      "claim_boundary":"Promotion covers Granite MoE on the measured 18 GB M3 Pro with the resident 2.8196 GiB SD-native expert bank, fused one-token routing, bounded fused post-linear prefill routing through 512 tokens, frozen 64/128/256-token generation cohorts, 256 teacher-forced positions and the unchanged twelve-case semantic gate. It does not claim bit-exact logits, identical free-running wording, arbitrary models, prompts beyond the fallback boundary, or continuous SD streaming at this rate."}
    report["report_sha256"]=_canonical_sha256(report);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n");print(json.dumps({"output":str(output),
      "decision":report["decision"],"generation_64":g64,"generation_128":g128,"generation_256":g256,
      "rate_drop_percent":rate_drop,"teacher":report["teacher"],"semantic":report["semantic"],
      "acceptance":acceptance,"report_sha256":report["report_sha256"]},indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
