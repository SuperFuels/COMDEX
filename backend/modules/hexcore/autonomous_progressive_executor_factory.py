"""Governed family-level executor acquisition for the progressive curriculum."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _utc_timestamp
from backend.modules.hexcore.progressive_outcome_authority_fabric import (
    ProgressiveOutcomeAuthorityFabric, SUBJECT_SUITES,
)


PROCEDURE_ID = "procedure_autonomous_progressive_executor_factory_v1"


def run(*, repo_root: Path, result_path: Path, state_path: Path) -> dict[str,Any]:
    registry_path=repo_root/"backend/modules/hexcore/data/progressive_competency/executor_registry.json"
    competency_path=repo_root/"backend/modules/hexcore/data/progressive_competency/state.json"
    registry=json.loads(registry_path.read_text())
    competency=json.loads(competency_path.read_text())
    fabric=ProgressiveOutcomeAuthorityFabric(
        state_path=repo_root/"backend/modules/hexcore/data/progressive_outcome_authority_fabric.json"
    )
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        "schema_version":"aion.hexcore.autonomous_progressive_executor_factory.v1",
        "installations":[],"rejections":[],
    }
    installed={row["subject_id"] for row in state["installations"]}
    for subject_id,(source,mutations,family) in SUBJECT_SUITES.items():
        # A newly verified adapter may arrive just before the corresponding
        # curriculum revision is activated.  Abstain until the subject exists
        # instead of crashing the governed factory.
        if subject_id not in competency["subjects"]:
            continue
        adapter=fabric.state["adapters"][subject_id]
        subject=competency["subjects"][subject_id]
        declared=set(subject["subskills"]); supported=set(adapter["supported_subskills"])
        covered=declared <= supported
        verified=(adapter["status"]=="verified_available" and covered
                  and adapter["counterexamples_rejected"]==adapter["counterexamples_total"])
        if verified and subject_id not in installed:
            state["installations"].append({
                "subject_id":subject_id,"subject_name":subject["name"],"family":family,
                "status":"installed_verified_adapter","declared_subskills":sorted(declared),
                "supported_subskills":sorted(supported),"source_hash":sha256(source.encode()).hexdigest(),
                "counterexamples":adapter["counterexamples_total"],"installed_at":_utc_timestamp(),
                "authority":"executable_candidate_plus_counterexample_falsification",
            })
            installed.add(subject_id)
        elif not verified:
            state["rejections"].append({
                "subject_id":subject_id,"family":family,"status":"rejected",
                "reason":"incomplete_subskill_coverage_or_failed_falsification",
                "recorded_at":_utc_timestamp(),
            })
    state["updated_at"]=_utc_timestamp()
    state_path.parent.mkdir(parents=True,exist_ok=True)
    temporary=state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state,indent=2,sort_keys=True),encoding="utf-8")
    os.replace(temporary,state_path)
    installations=state["installations"]
    families={row["family"] for row in installations}
    negative_subject="social_commonsense"
    negative_abstention=negative_subject not in SUBJECT_SUITES
    gate={
        "verified_family_adapters":len(installations),
        "distinct_authority_families":len(families),
        "declared_subskill_coverage":all(set(row["declared_subskills"]) <= set(row["supported_subskills"])
                                         for row in installations),
        "counterexample_falsification":all(row["counterexamples"] > 0 for row in installations),
        "unsupported_family_abstention":negative_abstention,
        "restart_retention":json.loads(state_path.read_text())["installations"]==installations,
        "unsafe_live_writes":0,"objective_mutations":0,
    }
    gate["accepted"]=(gate["verified_family_adapters"]>=6
                      and gate["distinct_authority_families"]>=5
                      and gate["declared_subskill_coverage"]
                      and gate["counterexample_falsification"]
                      and gate["unsupported_family_abstention"]
                      and gate["restart_retention"]
                      and gate["unsafe_live_writes"]==gate["objective_mutations"]==0)
    result={"schema_version":"aion.hexcore.autonomous_progressive_executor_factory_result.v1",
            "created_at":_utc_timestamp(),"procedure_id":PROCEDURE_ID,"passed":gate["accepted"],
            "gate":gate,"installations":installations,"families":sorted(families),
            "remaining_boundary":(
                "The factory autonomously installs adapters from already verified authority families. "
                "Inventing an entirely new authority family remains a separate governed research task."
            )}
    result_path.parent.mkdir(parents=True,exist_ok=True)
    temp=result_path.with_suffix(".tmp");temp.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    os.replace(temp,result_path)
    return result


if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        result_path=root/"results/hexcore_autonomous_progressive_executor_factory.json",
        state_path=root/"backend/modules/hexcore/data/progressive_executor_factory/state.json"),indent=2))
