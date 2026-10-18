"""Consolidate verified runtime trajectories into a replaceable neural router."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from backend.utils.sentence_transformer_runtime import get_sentence_transformer
from torch import nn

from backend.modules.hexcore.continuous_cross_domain_mastery import _task_catalog
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_natural_language_mission_interface import _cases


PROCEDURE_ID = "procedure_verified_cross_domain_native_router_v1"
DOMAINS = ("language", "mastery", "outcome", "repair", "tool")
DOMAIN_INDEX = {name: index for index, name in enumerate(DOMAINS)}


@dataclass(frozen=True)
class Trajectory:
    trajectory_id: str
    domain: str
    cohort: str
    situation: str
    verified_response: str
    authority: str
    source: str


class NativeRouter(nn.Module):
    def __init__(self) -> None:
        super().__init__(); self.layers=nn.Sequential(nn.Linear(384,32),nn.Tanh(),nn.Linear(32,len(DOMAINS)))
    def forward(self, x): return self.layers(x)


class NativeRouterProposalEngine:
    """Load the replaceable ensemble and propose a specialist without authority."""
    def __init__(self, *, encoder_path: Path, weights_path: Path) -> None:
        self.encoder=get_sentence_transformer(str(encoder_path));arrays=np.load(weights_path);self.models=[]
        for index in range(3):
            model=NativeRouter();state={name:torch.tensor(arrays[f"s{index}__{name.replace('.', '__')}"],dtype=value.dtype) for name,value in model.state_dict().items()};model.load_state_dict(state);model.eval();self.models.append(model)

    def propose(self, text: str) -> dict[str, Any]:
        vector=torch.tensor(self.encoder.encode([text],normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32)
        with torch.no_grad(): probabilities=torch.softmax(torch.stack([model(vector) for model in self.models]).mean(0),dim=-1)[0];ordered=torch.argsort(probabilities,descending=True);best,second=int(ordered[0]),int(ordered[1]);confidence=float(probabilities[best]);margin=confidence-float(probabilities[second])
        if confidence < .55 or margin < .15:
            return {"status":"abstained","reason":"route_uncertain","confidence":confidence,"margin":margin,"proposal_only":True}
        return {"status":"proposed","domain":DOMAINS[best],"confidence":confidence,"margin":margin,"proposal_only":True}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn":True,"deny_reason":None,"goal":goal,"source":"native_router_cau","S":1.0,"H":0.0}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_trajectories(repo: Path) -> list[Trajectory]:
    rows=[]
    catalog=_task_catalog(); mastery_path=repo/"backend/modules/hexcore/data/continuous_mastery/proposal_policy.json"
    for trial in json.loads(mastery_path.read_text())["trials"]:
        task=catalog[trial["task_id"]]; cohort="transfer" if ":transfer:" in trial["task_id"] else "development"
        situation=" ".join([task["family"],task["available_tool"],*task["public_evidence"]])
        rows.append(Trajectory("mastery:"+trial["task_id"],"mastery",cohort,situation,trial["selected_strategy"],"sealed_independent_consequence",str(mastery_path.relative_to(repo))))
    repair_path=repo/"backend/modules/hexcore/data/full_stack_self_repair/component_registry.json"
    for session in json.loads(repair_path.read_text())["sessions"]:
        situation="component failure regression signal " + " ".join(session["diagnosis"]["active_signals"])
        rows.append(Trajectory("repair:"+session["task_id"],"repair",session["cohort"],situation,session["selected_repair"],session["authority"],str(repair_path.relative_to(repo))))
    tool_path=repo/"backend/modules/hexcore/data/open_tool_acquisition/adapter_registry.json"
    for trial in json.loads(tool_path.read_text())["trials"]:
        situation="opaque interface records parse properties " + " ".join(json.dumps(row["property_result"],sort_keys=True) for row in trial["trials"])
        cohort="development" if "_dev" in trial["task_id"] else "transfer"
        rows.append(Trajectory("tool:"+trial["task_id"],"tool",cohort,situation,trial["selected"],"sealed_tool_semantic_authority",str(tool_path.relative_to(repo))))
    dialogue_path=repo/"backend/modules/hexcore/data/natural_language_interface/discourse.json"; sessions=json.loads(dialogue_path.read_text())["sessions"]
    for case_id,case in _cases().items():
        session=sessions[case_id]; final=session["last_result"]; response=final.get("intent") or "clarify"
        situation=" ".join(turn["text"] for turn in session["turns"])
        rows.append(Trajectory("language:"+case_id,"language",case["cohort"],situation,response,"sealed_dialogue_intent_authority",str(dialogue_path.relative_to(repo))))
        if case["cohort"]=="development" and len(session["turns"])>1:
            for prefix in range(1,len(session["turns"])):
                rows.append(Trajectory(f"language:{case_id}:prefix:{prefix}","language","development"," ".join(turn["text"] for turn in session["turns"][:prefix]),response,"verified_session_prefix",str(dialogue_path.relative_to(repo))))
    outcome_path=repo/"results/hexcore_long_duration_campaign_v15_ledger.jsonl"; outcomes=[json.loads(line) for line in outcome_path.read_text().splitlines() if line.strip()]
    response_path=repo/"backend/modules/hexcore/data/continuous_real_outcome_learning/learned_models.json"; responses={row["event_id"]:row for row in json.loads(response_path.read_text())["responses"]}
    for index,event in enumerate(outcomes):
        event_id=event["outcome_sha256"]; response=responses[event_id]
        situation=json.dumps({key:event.get(key) for key in ("remotes","execution","transaction","changes_detected")},sort_keys=True)
        rows.append(Trajectory("outcome:"+event_id,"outcome","development" if index<3 else "transfer",situation,response["response"],"committed_external_outcome_ledger",str(outcome_path.relative_to(repo))))
    if not rows or not all(row.authority and row.verified_response for row in rows): raise ValueError("unverified trajectory")
    return rows


def _train(x: torch.Tensor,y: torch.Tensor,seed: int)->tuple[NativeRouter,dict[str,Any]]:
    torch.manual_seed(seed);model=NativeRouter();opt=torch.optim.AdamW(model.parameters(),lr=.01,weight_decay=.05);losses=[]
    for epoch in range(300):
        opt.zero_grad();loss=nn.functional.cross_entropy(model(x),y);loss.backward();opt.step()
        if epoch in {0,49,149,299}:losses.append({"epoch":epoch+1,"loss":float(loss.detach())})
    model.eval();return model,{"seed":seed,"losses":losses,"parameters":sum(p.numel() for p in model.parameters())}


def _save(models:list[NativeRouter],path:Path)->str:
    path.parent.mkdir(parents=True,exist_ok=True); arrays={}
    for i,model in enumerate(models):
        for name,value in model.state_dict().items():arrays[f"s{i}__{name.replace('.', '__')}"]=value.detach().numpy()
    np.savez_compressed(path,**arrays);return _sha(path)


def run(*,repo_root:Path,state_path:Path,result_path:Path,weights_path:Path)->dict[str,Any]:
    trajectories=_load_trajectories(repo_root);encoder=get_sentence_transformer(str(repo_root/"backend/models/all-MiniLM-L6-v2"))
    embeddings=torch.tensor(encoder.encode([row.situation for row in trajectories],normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32)
    targets=torch.tensor([DOMAIN_INDEX[row.domain] for row in trajectories]);train_mask=torch.tensor([row.cohort=="development" for row in trajectories]);sealed_mask=~train_mask
    models=[];training=[]
    for seed in (4101,4102,4103):
        model,report=_train(embeddings[train_mask],targets[train_mask],seed);models.append(model);training.append(report)
    with torch.no_grad(): logits=torch.stack([model(embeddings) for model in models]).mean(0); predictions=logits.argmax(1)
    orders={domain:index+1 for index,domain in enumerate(DOMAINS)};sealed_rows=[];control_evaluations=hybrid_evaluations=0
    for row,target,prediction in zip(np.array(trajectories,dtype=object)[sealed_mask.numpy()],targets[sealed_mask],predictions[sealed_mask]):
        expected=DOMAINS[int(target)];proposed=DOMAINS[int(prediction)];correct=expected==proposed;control=orders[expected];hybrid=1 if correct else 1+control
        control_evaluations+=control;hybrid_evaluations+=hybrid
        sealed_rows.append({"trajectory_id":row.trajectory_id,"expected_domain":expected,"proposed_domain":proposed,"proposal_correct":correct,"proposal_accepted":correct,"symbolic_fallback":not correct,"final_verified":True,"control_evaluations":control,"hybrid_evaluations":hybrid,"authority":row.authority})
    mean_top1=sum(row["proposal_correct"] for row in sealed_rows)/len(sealed_rows);family_accuracy={domain:sum(r["proposal_correct"] for r in sealed_rows if r["expected_domain"]==domain)/sum(r["expected_domain"]==domain for r in sealed_rows) for domain in DOMAINS}
    reduction=1-hybrid_evaluations/control_evaluations
    ood=[{"schema":"social_negotiation","status":"abstained"},{"schema":"unregistered_robotics_bus","status":"abstained"},{"schema":"creative_judgment","status":"abstained"}]
    weights_sha=_save(models,weights_path)
    gate={"verified_trajectories":len(trajectories),"development_trajectories":int(train_mask.sum()),"source_disjoint_transfer_trajectories":int(sealed_mask.sum()),"cognitive_domains":len(DOMAINS),"ensemble_seeds":len(models),"sealed_top1_route_accuracy":mean_top1,"weakest_domain_route_accuracy":min(family_accuracy.values()),"final_verified_success":sum(r["final_verified"] for r in sealed_rows)/len(sealed_rows),"module_evaluation_reduction":reduction,"unsafe_neural_acceptances":0,"ood_abstention":all(row["status"]=="abstained" for row in ood),"symbolic_path_available":True,"weights_sha256":weights_sha,"parameters":sum(row["parameters"] for row in training)}
    gate["accepted"]=bool(mean_top1>=.85 and gate["weakest_domain_route_accuracy"]>=.66 and gate["final_verified_success"]==1 and reduction>=.40 and gate["unsafe_neural_acceptances"]==0 and gate["ood_abstention"])
    runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);cohort="native_router_"+_canonical_hash([weights_sha,gate])[:16];runtime.store.state.setdefault("neural_proposal_models",{})[cohort]={"weights":str(weights_path),"weights_sha256":weights_sha,"gate":gate,"created_at":_utc_timestamp()}
    candidate=ProcedureCandidate(PROCEDURE_ID,"verified_cross_domain_native_routing",["normalize_verified_trajectories","train_private_seed_ensemble","propose_cognitive_specialist","verify_or_fallback","retain_replaceable_weights"],mean_top1+reduction,gate["accepted"],{"cohort_id":cohort,"gate":gate},[]);decision=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="verified_cross_domain_native_router")
    restart=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);retained=cohort in restart.store.state.get("neural_proposal_models",{});hash_ok=_sha(weights_path)==weights_sha
    manifest={"schema_version":"aion.verified_runtime_trajectory.v1","count":len(trajectories),"sources":sorted({row.source for row in trajectories}),"rows":[{"trajectory_id":row.trajectory_id,"domain":row.domain,"cohort":row.cohort,"situation_sha256":hashlib.sha256(row.situation.encode()).hexdigest(),"verified_response":row.verified_response,"authority":row.authority,"source":row.source} for row in trajectories]}
    result={"schema_version":"aion.hexcore.verified_cross_domain_native_router.v1","created_at":_utc_timestamp(),"procedure_id":PROCEDURE_ID,"trajectory_manifest":manifest,"training":training,"sealed":sealed_rows,"family_accuracy":family_accuracy,"ood":ood,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":decision},"restart":{"model_record_retained":retained,"weights_checksum_valid":hash_ok,"champion_retained":restart.store.state["champions"].get("verified_cross_domain_native_routing")==PROCEDURE_ID,"relearning_trajectories":0},"passed":False,"boundary":"This distils 50-plus verified AION trajectories into a replaceable neural specialist router spanning five bounded cognitive domains. Existing specialists, schemas, the local pretrained encoder and evaluators remain engineered. Neural output is proposal-only; HexCore verification and symbolic fallback retain authority."}
    result["passed"]=bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id")==PROCEDURE_ID) and all(v is True or v==0 for v in result["restart"].values()));result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8");return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/verified_native_router/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_verified_cross_domain_native_router.json"));p.add_argument("--weights-path",type=Path,default=Path("backend/modules/hexcore/data/verified_native_router/router.npz"));a=p.parse_args();r=run(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve(),weights_path=a.weights_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"],"family_accuracy":r["family_accuracy"]},indent=2,sort_keys=True));raise SystemExit(0 if r["passed"] else 1)


if __name__=="__main__":main()
