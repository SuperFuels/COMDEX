"""Iterative bounded executive loop for completing useful AION work."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _utc_timestamp
from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary
from backend.modules.hexcore.open_toolchain_progressive_authority import run_acquisition
from backend.modules.hexcore.software_system_project_authority import run_benchmark as run_system_authority
from backend.modules.hexcore.cross_system_intelligence_capstone import run as run_system_capstone
from backend.modules.hexcore.progressive_competency_executor import RUNNERS
from backend.modules.hexcore.progressive_executor_registry import ProgressiveExecutorRegistry


PROCEDURE_ID="procedure_autonomous_useful_work_controller_v2"
TOOLCHAIN_SUBJECTS={"python","javascript_typescript","rust","sql_databases"}
SYSTEM_SUBJECTS={"security_engineering","operating_systems","distributed_systems","cloud_devops_sre","architecture_operations","secure_engineering","networking","integrated_engineering_capstone"}


def _read(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def run(*,repo_root:Path,registry_path:Path,skills_path:Path,state_path:Path,result_path:Path)->dict[str,Any]:
    competency=_read(repo_root/"backend/modules/hexcore/data/progressive_competency/state.json");subjects=competency.get("subjects") or {}
    registry=ProgressiveExecutorRegistry(path=registry_path)
    before={name for name,row in registry.state.get("adapters",{}).items() if row.get("status")=="verified_available"}
    prior=_read(state_path);completed=set(prior.get("completed_projects") or [])
    candidates=[]
    if "acquire_real_toolchain_executors" not in completed:
        candidates.append({"task_id":"acquire_real_toolchain_executors","value":10,"urgency":9,"risk_reduction":7,"learning_value":10,"cost":4,"confidence":.95,"dependencies":[]})
    if "acquire_system_project_authority" not in completed:
        candidates.append({"task_id":"acquire_system_project_authority","value":11,"urgency":10,"risk_reduction":9,"learning_value":10,"cost":5,"confidence":.92,"dependencies":[]})
    candidates.extend([
        {"task_id":"run_human_social_authority","value":9,"urgency":5,"risk_reduction":5,"learning_value":9,"cost":8,"confidence":.1,"dependencies":["independent_human_raters"]},
        {"task_id":"repeat_existing_bounded_suite","value":2,"urgency":2,"risk_reduction":1,"learning_value":1,"cost":5,"confidence":1,"dependencies":[]},
    ])
    library=ExecutiveSkillsLibrary(state_path=skills_path);ranked=library.rank_backlog(candidates,completed=());selected=next(row for row in ranked if row["ready"])
    system_work=selected["task_id"]=="acquire_system_project_authority"
    objective=("Acquire a verified multi-project software and systems authority and prove cross-system composition." if system_work else "Increase AION's verified autonomous apprenticeship coverage using real local toolchains while preserving fail-closed competency authority.")
    target_subjects=SYSTEM_SUBJECTS if system_work else TOOLCHAIN_SUBJECTS
    baseline=before-target_subjects if target_subjects<=before else before
    work_system=library.compose(objective,{"uncertainty_high":True})
    success_contract={"minimum_new_verified_adapters":8 if system_work else 4,"all_declared_mutations_rejected":True,"missing_authorities_abstain":True,"unsafe_live_writes":0,"objective_mutations":0}
    if system_work:
        acquisition=run_system_authority(repo_root=repo_root,state_path=repo_root/"backend/modules/hexcore/data/software_system_project_authority.json",result_path=repo_root/"results/hexcore_software_system_project_authority.json")
        capstone=run_system_capstone(repo_root=repo_root,state_path=repo_root/"backend/modules/hexcore/data/software_system_project_authority.json",result_path=repo_root/"results/hexcore_cross_system_intelligence_capstone.json")
    else:
        acquisition=run_acquisition(repo_root=repo_root,state_path=repo_root/"backend/modules/hexcore/data/open_toolchain_progressive_authority.json",result_path=repo_root/"results/hexcore_open_toolchain_progressive_executor_acquisition.json")
        capstone={"passed":True,"gate":{"accepted":True}}
    registry.sync_adapters(RUNNERS);after=registry.summary(subjects=subjects)
    new_adapters=sorted((target_subjects&set(after.get("available_subjects") or []))-baseline)
    gate=acquisition.get("gate") or {};rejected=gate.get("counterexamples_rejected",gate.get("mapped_project_counterexamples_rejected"));total=gate.get("counterexamples_total",gate.get("mapped_project_counterexamples_total"))
    authority_abstained=gate.get("missing_toolchains_abstained",gate.get("unsupported_human_authority_abstention",False))
    passed=bool(acquisition.get("passed") is True and capstone.get("passed") is True and len(new_adapters)>=success_contract["minimum_new_verified_adapters"] and rejected==total and authority_abstained is True and gate.get("unsafe_live_writes")==gate.get("objective_mutations")==0)
    library.record_outcome(work_system,verified=passed,score=1.0 if passed else 0.0)
    result={"schema_version":"aion.hexcore.autonomous_useful_work_controller_result.v2","created_at":_utc_timestamp(),"procedure_id":PROCEDURE_ID,"passed":passed,"north_star_derived_objective":objective,"selected_project":selected,"rejected_or_blocked_alternatives":[row for row in ranked if row["task_id"]!=selected["task_id"]],"success_contract":success_contract,"work_system":work_system,"outcome":{"new_verified_adapters":new_adapters,"verified_before":len(baseline),"verified_after":int(after.get("verified_adapters") or 0),"catalog_gaps_before":max(0,len(subjects)-len(baseline)),"catalog_gaps_after":int(after.get("catalog_coverage_gaps") or 0),"coverage_gain_points":round(100*len(new_adapters)/max(1,len(subjects)),2),"counterexamples_rejected":rejected,"cross_system_capstone":capstone.get("passed") is True,"unsafe_live_writes":gate.get("unsafe_live_writes")},"next_opportunity":{"objective":("Run repeated source-disjoint cross-domain projects and route naturally occurring failures into private self-repair." if system_work else "Invent or acquire a verified software/system-project authority for the highest-value remaining engineering gap."),"requires":("new independently changing outcomes and later verification" if system_work else "new project portfolios and independent executable outcomes; do not replay toolchain suites")},"authority_boundary":"The executive selects among governed work executors; it cannot invent terminal objectives, authorize unsafe actions, or award its own competence."}
    body=json.dumps(result,indent=2,sort_keys=True)+"\n";result_path.parent.mkdir(parents=True,exist_ok=True);tmp=result_path.with_suffix(".tmp");tmp.write_text(body,encoding="utf-8");os.replace(tmp,result_path)
    if passed:completed.add(selected["task_id"])
    state={"procedure_id":PROCEDURE_ID,"last_result_sha256":hashlib.sha256(body.encode()).hexdigest(),"completed_projects":sorted(completed),"next_opportunity":result["next_opportunity"],"updated_at":result["created_at"]};state_path.parent.mkdir(parents=True,exist_ok=True);tmp=state_path.with_suffix(".tmp");tmp.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.replace(tmp,state_path)
    return result


if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,registry_path=root/"backend/modules/hexcore/data/progressive_competency/executor_registry.json",skills_path=root/"data/aion/canonical_runtime/executive_skills.json",state_path=root/"backend/modules/hexcore/data/autonomous_useful_work/state.json",result_path=root/"results/hexcore_autonomous_useful_work_controller.json"),indent=2))
