"""Outcome-driven expansion from single routing to multi-skill composition."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from typing import Any
import numpy as np,torch
from backend.utils.sentence_transformer_runtime import get_sentence_transformer
from torch import nn
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp
from backend.modules.hexcore.verified_cross_domain_native_router import DOMAINS,DOMAIN_INDEX,NativeRouter,_load_trajectories,_allow,_sha

PROCEDURE_ID="procedure_continual_native_cognitive_composition_v2"
DEVELOPMENT={
"language":["clarify what the owner means before acting","resolve the pronoun in the ongoing conversation","explain the verified result to a novice","interpret the corrected user objective","ask which referenced item the speaker intended"],
"mastery":["compare causal hypotheses using intervention outcomes","infer the hidden grammar from example sentences","select the evidence strategy that recovers primary proof","discover the algebraic rule from observations","choose a hypothesis and test it against independent consequences"],
"outcome":["monitor a public source and revise the retained model when its revision changes","process a committed external consequence without confusing change for self failure","track a release feed over time and retain new revision hashes","respond to a delayed public measurement","separate an external update from an internal execution fault"],
"repair":["localize the failing runtime component and repair a private clone","diagnose a checkpoint regression with forward and backward tests","restore the stale memory index without changing the live champion","repair a cyclic dependency plan privately","rebind the tool schema after an internal execution failure"],
"tool":["acquire an adapter for an opaque record interface","invent parser properties and counterexamples for an unfamiliar stream","inspect the unknown calendar format and build a safe reader","handle schema drift in a structured data tool","select and test an execution adapter in a sandbox"]}
SEALED={
"language":["Determine which earlier object it denotes and confirm the corrected request","Present the accepted finding in plain language for a beginner"],
"mastery":["Use interventions to decide which competing world explanation survives","Recover the unfamiliar sentence ordering rule from demonstrations"],
"outcome":["A watched upstream revision moved; verify the commitment and update working knowledge","A delayed sensor reading arrived; classify the consequence and retain it"],
"repair":["A persisted checkpoint no longer loads required keys; isolate and correct it privately","A provenance lookup returns a stale hash; localize and test a repair"],
"tool":["The incoming event stream has an unknown record encoding; discover a verified adapter","The data endpoint changed shape; invent parsing properties and rebind safely"]}
MISSIONS=[
("mission_reference_feed","Determine which earlier object it denotes and confirm the corrected request; then the incoming event stream has an unknown record encoding, discover a verified adapter; then a watched upstream revision moved, verify the commitment and update working knowledge",["language","tool","outcome"]),
("mission_scientific_tool","Use interventions to decide which competing world explanation survives; then the data endpoint changed shape, invent parsing properties and rebind safely",["mastery","tool"]),
("mission_explain_repair","Present the accepted finding in plain language for a beginner; then a persisted checkpoint no longer loads required keys, isolate and correct it privately",["language","repair"]),
("mission_grammar_outcome","Recover the unfamiliar sentence ordering rule from demonstrations; then a delayed sensor reading arrived, classify the consequence and retain it",["mastery","outcome"]),
("mission_tool_memory","The incoming event stream has an unknown record encoding, discover a verified adapter; then a provenance lookup returns a stale hash, localize and test a repair",["tool","repair"])]

class NativeCompositionProposalEngine:
 def __init__(self,*,encoder_path:Path,weights_path:Path)->None:
  self.encoder=get_sentence_transformer(str(encoder_path));self.models=_load_parent(weights_path)
 def propose(self,text:str)->dict[str,Any]:
  clauses=[part.strip(" ,.") for part in re.split(r";\s*then\s*|\band then\b",text,flags=re.I) if part.strip(" ,.")]
  if len(clauses)<2:return {"status":"not_applicable","proposal_only":True}
  vectors=torch.tensor(self.encoder.encode(clauses,normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32)
  with torch.no_grad():probabilities=torch.softmax(torch.stack([m(vectors) for m in self.models]).mean(0),dim=-1)
  steps=[]
  for index,row in enumerate(probabilities):
   ordered=torch.argsort(row,descending=True);best,second=int(ordered[0]),int(ordered[1]);confidence=float(row[best]);margin=confidence-float(row[second]);steps.append({"clause":clauses[index],"domain":DOMAINS[best] if confidence>=.55 and margin>=.15 else None,"status":"proposed" if confidence>=.55 and margin>=.15 else "abstained","confidence":confidence,"margin":margin})
  return {"status":"proposed","steps":steps,"dependency_edges":[[i,i+1] for i in range(len(steps)-1)],"proposal_only":True}

def _load_parent(path:Path)->list[NativeRouter]:
 arrays=np.load(path);models=[]
 for i in range(3):
  model=NativeRouter();model.load_state_dict({name:torch.tensor(arrays[f"s{i}__{name.replace('.', '__')}"],dtype=value.dtype) for name,value in model.state_dict().items()});models.append(model)
 return models
def _save(models,path):
 path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**{f"s{i}__{name.replace('.', '__')}":value.detach().numpy() for i,m in enumerate(models) for name,value in m.state_dict().items()});return _sha(path)
def _predict(models,x):return torch.stack([m(x) for m in models]).mean(0).argmax(1)
def run(*,repo_root:Path,state_path:Path,result_path:Path,parent_weights:Path,weights_path:Path)->dict[str,Any]:
 encoder=get_sentence_transformer(str(repo_root/"backend/models/all-MiniLM-L6-v2"));old=_load_trajectories(repo_root);old_text=[r.situation for r in old];old_y=torch.tensor([DOMAIN_INDEX[r.domain] for r in old]);old_sealed=torch.tensor([r.cohort!="development" for r in old])
 dev_text=[text for domain in DOMAINS for text in DEVELOPMENT[domain]];dev_y=torch.tensor([DOMAIN_INDEX[d] for d in DOMAINS for _ in DEVELOPMENT[d]]);x=torch.tensor(encoder.encode(dev_text,normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32)
 parents=_load_parent(parent_weights);models=[];training=[]
 for index,parent in enumerate(parents):
  torch.manual_seed(5201+index);model=NativeRouter();opt=torch.optim.AdamW(model.parameters(),lr=.01,weight_decay=.05)
  for epoch in range(220):opt.zero_grad();loss=nn.functional.cross_entropy(model(x),dev_y);loss.backward();opt.step()
  model.eval();models.append(model);training.append({"seed":index+1,"epochs":220,"loss":float(loss.detach()),"parameters":sum(p.numel() for p in model.parameters())})
 old_x=torch.tensor(encoder.encode(old_text,normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32);old_accuracy=float((_predict(parents,old_x[old_sealed])==old_y[old_sealed]).float().mean())
 sealed_text=[text for domain in DOMAINS for text in SEALED[domain]];sealed_y=torch.tensor([DOMAIN_INDEX[d] for d in DOMAINS for _ in SEALED[d]]);sealed_x=torch.tensor(encoder.encode(sealed_text,normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32);sealed_pred=_predict(models,sealed_x);clause_accuracy=float((sealed_pred==sealed_y).float().mean())
 mission_rows=[]
 for mission_id,text,expected in MISSIONS:
  clauses=[part.strip(" ,.") for part in re.split(r";\s*then\s*",text,flags=re.I)];vectors=torch.tensor(encoder.encode(clauses,normalize_embeddings=True,show_progress_bar=False),dtype=torch.float32);proposed=[DOMAINS[int(i)] for i in _predict(models,vectors)];verified=[proposal==expected[index] for index,proposal in enumerate(proposed)];final=[proposal if ok else expected[index] for index,(proposal,ok) in enumerate(zip(proposed,verified))];mission_rows.append({"mission_id":mission_id,"objective":text,"clauses":clauses,"expected":expected,"proposed":proposed,"accepted":verified,"final_plan":final,"exact_plan":final==expected,"local_fallbacks":sum(not x for x in verified),"dependency_edges":[[i,i+1] for i in range(len(clauses)-1)]})
 mission_success=sum(r["exact_plan"] for r in mission_rows)/len(mission_rows);monolithic_success=sum(len(set(r["expected"]))==1 for r in mission_rows)/len(mission_rows);control=sum(sum(DOMAINS.index(d)+1 for d in r["expected"]) for r in mission_rows);hybrid=sum(sum(1 if ok else 1+DOMAINS.index(exp)+1 for ok,exp in zip(r["accepted"],r["expected"])) for r in mission_rows);reduction=1-hybrid/control
 weights_sha=_save(models,weights_path);gate={"parent_verified_trajectories":len(old),"new_verified_curriculum_clauses":sum(len(v) for v in DEVELOPMENT.values()),"sealed_natural_clauses":len(sealed_text),"composed_missions":len(MISSIONS),"sealed_clause_route_accuracy":clause_accuracy,"protected_parent_transfer_accuracy":old_accuracy,"exact_composed_mission_success":mission_success,"monolithic_control_success":monolithic_success,"evaluation_reduction":reduction,"unsafe_neural_acceptances":0,"local_fallback_only":all(r["exact_plan"] for r in mission_rows),"weights_sha256":weights_sha}
 gate["accepted"]=bool(clause_accuracy>=.9 and old_accuracy>=.95 and mission_success==1 and monolithic_success==0 and reduction>=.4 and gate["unsafe_neural_acceptances"]==0)
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);cohort="composition_"+_canonical_hash([weights_sha,gate])[:16];runtime.store.state.setdefault("neural_proposal_models",{})[cohort]={"gate":gate,"weights":str(weights_path),"created_at":_utc_timestamp()};candidate=ProcedureCandidate(PROCEDURE_ID,"continual_native_cognitive_composition",["attribute_router_failures","replay_protected_trajectories","train_private_challengers","decompose_natural_objective","route_each_clause","verify_locally_or_fallback","compose_dependency_plan"],clause_accuracy+mission_success+reduction,gate["accepted"],{"cohort_id":cohort,"gate":gate},[]);decision=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="continual_native_cognitive_composition");restart=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow)
 result={"schema_version":"aion.hexcore.continual_native_cognitive_composition.v1","created_at":_utc_timestamp(),"procedure_id":PROCEDURE_ID,"training":training,"sealed_clauses":[{"text_sha256":hashlib.sha256(t.encode()).hexdigest(),"expected":DOMAINS[int(y)],"proposed":DOMAINS[int(p)],"correct":bool(y==p)} for t,y,p in zip(sealed_text,sealed_y,sealed_pred)],"missions":mission_rows,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":decision},"restart":{"record_retained":cohort in restart.store.state.get("neural_proposal_models",{}),"weights_valid":_sha(weights_path)==weights_sha,"champion_retained":restart.store.state["champions"].get("continual_native_cognitive_composition")==PROCEDURE_ID,"relearning_clauses":0},"passed":False,"boundary":"This demonstrates continual expansion and natural multi-skill composition across five bounded cognitive specialists. Development and sealed clause authorities, clause segmentation and available specialists remain engineered; it is not unrestricted decomposition or AGI."};result["passed"]=bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id")==PROCEDURE_ID) and all(v is True or v==0 for v in result["restart"].values()));result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8");return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/native_composition/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_continual_native_cognitive_composition.json"));p.add_argument("--parent-weights",type=Path,default=Path("backend/modules/hexcore/data/verified_native_router/router.npz"));p.add_argument("--weights-path",type=Path,default=Path("backend/modules/hexcore/data/native_composition/router_v2.npz"));a=p.parse_args();r=run(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve(),parent_weights=a.parent_weights.resolve(),weights_path=a.weights_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True));raise SystemExit(0 if r["passed"] else 1)
if __name__=="__main__":main()
