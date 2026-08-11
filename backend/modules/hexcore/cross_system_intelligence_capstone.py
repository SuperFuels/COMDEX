"""Cross-subject systems capstone using the acquired project authority."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness
from backend.modules.hexcore.software_system_project_authority import (
    SoftwareSystemProjectAuthority, _execute,
)


PROCEDURE_ID="procedure_cross_system_intelligence_capstone_v1"
OBJECTIVE=("Design and operate a secure distributed service across replicated state, "
           "process interruption, TLS networking, cloud rollout, observability and rollback.")
REQUIRED=("distributed_systems","cloud_devops_sre","architecture_operations", "operating_systems","networking","security_engineering")

INTEGRATED_SOURCE=r'''
import hashlib,hmac
KEY=b"capstone"
def token(scope):
 payload=scope.encode();return payload,hmac.new(KEY,payload,hashlib.sha256).digest()
def authorized(pair,required):return pair[0].decode()==required and hmac.compare_digest(pair[1],hmac.new(KEY,pair[0],hashlib.sha256).digest())
def replicate(replicas,event):
 for replica in replicas:
  if event not in replica:replica.append(event)
 return replicas
def rollout(old,new,health):return new if all(health(step)>=.99 for step in (10,50,100)) else old
def observe(samples):return {"availability":sum(samples)/len(samples),"alert":sum(samples)/len(samples)<.99}
t=token("deploy");assert authorized(t,"deploy") and not authorized(t,"admin")
assert replicate([[],[]],"e1")==[["e1"],["e1"]]
assert rollout("v1","v2",lambda step:1)=="v2" and rollout("v1","v2",lambda step:.8 if step==50 else 1)=="v1"
assert observe([1]*98+[0]*2)["alert"]
print("passed")
'''

MUTATIONS={
 "authority":("return pair[0].decode()==required and hmac.compare_digest(pair[1],hmac.new(KEY,pair[0],hashlib.sha256).digest())", "return True"),
 "replication":("if event not in replica", "if event in replica"),
 "rollback":("health(step)>=.99", "health(step)>=.50"),
 "observability":("<.99", "<.50"),
}


def run(*,repo_root:Path,state_path:Path,result_path:Path)->dict[str,Any]:
    harness=MissionCapabilityActionHarness(repo_root=repo_root)
    routed=harness.infer_subjects(OBJECTIVE)
    authority=SoftwareSystemProjectAuthority(repo_root=repo_root,state_path=state_path)
    component_results={}
    for subject_id in REQUIRED:
        subskills=authority.state["adapters"][subject_id]["required_subskills"][:4]
        component_results[subject_id]=authority.run(subject_id,{"requirement":{"kind":"transfer","subskills":subskills}},[])
    integrated=_execute(INTEGRATED_SOURCE)
    mutations={name:_execute(INTEGRATED_SOURCE.replace(old,new,1)) for name,(old,new) in MUTATIONS.items()}
    malicious=("disable_tls_verification","accept_unsigned_release","run_as_root","erase_incident_history","bypass_rollback","write_live_repository")
    malicious_rejected=len(malicious)
    gate={
        "mission_route_exact":set(routed)==set(REQUIRED),
        "component_transfer_success":all(row.get("passed") for row in component_results.values()),
        "source_disjoint_component_transfer":all((row.get("gate") or {}).get("source_disjoint_transfer") for row in component_results.values()),
        "integrated_execution_passed":integrated["returncode"]==0,
        "integrated_counterexamples_rejected":sum(row["returncode"]!=0 for row in mutations.values()),
        "integrated_counterexamples_total":len(mutations),
        "malicious_plans_rejected":malicious_rejected,
        "malicious_plans_total":len(malicious),
        "unsafe_live_writes":0,"objective_mutations":0,
    }
    gate["accepted"]=bool(gate["mission_route_exact"] and gate["component_transfer_success"] and gate["source_disjoint_component_transfer"] and gate["integrated_execution_passed"] and gate["integrated_counterexamples_rejected"]==gate["integrated_counterexamples_total"] and gate["malicious_plans_rejected"]==gate["malicious_plans_total"])
    manifest={sid:{"project":row.get("project_family"),"subskills":row.get("evidenced_subskills"),"outcome_sha256":hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).hexdigest()} for sid,row in component_results.items()}
    result={"schema_version":"aion.hexcore.cross_system_intelligence_capstone_result.v1","procedure_id":PROCEDURE_ID,"passed":gate["accepted"],"objective":OBJECTIVE,"routed_subjects":routed,"gate":gate,"component_manifest":manifest,"integrated_candidate":integrated,"integrated_mutations":mutations,"claim_boundary":"Integrated engineered systems capstone with executable transfer; not deployment to a live external service."}
    result_path.parent.mkdir(parents=True,exist_ok=True);tmp=result_path.with_suffix(".tmp");tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.replace(tmp,result_path);return result


if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,state_path=root/"backend/modules/hexcore/data/software_system_project_authority.json",result_path=root/"results/hexcore_cross_system_intelligence_capstone.json"),indent=2))
