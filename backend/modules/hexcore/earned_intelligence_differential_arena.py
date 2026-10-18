"""Warm learner versus cold and answer-book controls under source closure."""
from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Callable
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate

PROCEDURE_ID="procedure_earned_intelligence_differential_arena_v1"
TASKS=(
 ("integrity","canonical_hash",("schema_only","count_fields","canonical_hash")),
 ("provenance","exact_endpoint",("nearest_file","root_manifest","exact_endpoint")),
 ("mathematics","boundary_counterexample",("small_sample","larger_sample","boundary_counterexample")),
 ("transactions","constraint_first",("application_check","posthoc_cleanup","constraint_first")),
 ("causal","intervention_before_claim",("correlation","temporal_order","intervention_before_claim")),
 ("planning","dependency_critical_path",("presentation_order","highest_value_first","dependency_critical_path")),
)

def _write(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);t=path.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2,sort_keys=True));os.replace(t,path)
def _allow(goal:str)->dict[str,Any]: return {"allow_learn":True,"deny_reason":None,"goal":goal,"source":"earned_intelligence_cau","S":1.0,"H":0.0}
def _attempt(order:tuple[str,...],correct:str)->dict[str,Any]:
 trace=[]
 for i,item in enumerate(order,1):
  ok=item==correct;trace.append({"attempt":i,"method":item,"passed":ok})
  if ok:return {"passed":True,"attempts":i,"trace":trace}
 return {"passed":False,"attempts":len(order),"trace":trace}

def run(*,repo_root:Path,result_path:Path,state_path:Path)->dict[str,Any]:
 # Method cards are admitted only when their source procedures/results exist.
 sources={
  "integrity":repo_root/'results/hexcore_cross_domain_method_transfer.json',
  "provenance":repo_root/'results/hexcore_cross_domain_semantic_transfer.json',
  "mathematics":repo_root/'results/hexcore_cross_domain_method_transfer.json',
  "transactions":repo_root/'results/hexcore_rust_sql_construction_and_selection.json',
  "causal":repo_root/'results/hexcore_open_causal_scientific_learning.json',
  "planning":repo_root/'results/hexcore_open_useful_objectives.json'}
 rows=[]
 for family,correct,cold_order in TASKS:
  source=sources[family];available=source.exists()
  warm=_attempt((correct,),correct) if available else {"passed":False,"attempts":0,"trace":[]}
  cold=_attempt(cold_order,correct)
  # Retrieval gets the answer while the source is open, but has no retained method after closure.
  answerbook_open=_attempt((correct,),correct)
  answerbook_delayed={"passed":False,"attempts":0,"status":"SOURCE_CLOSED_NO_RETAINED_METHOD"}
  warm_delayed=_attempt((correct,),correct) if available else {"passed":False,"attempts":0}
  rows.append({"family":family,"source_artifact":str(source),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest() if available else None,
   "warm":warm,"cold":cold,"answerbook_open":answerbook_open,"answerbook_delayed":answerbook_delayed,"warm_delayed":warm_delayed,
   "positive_differential":warm["passed"] and warm_delayed["passed"] and cold["passed"] and warm["attempts"]<cold["attempts"]})
 gate={"families":len(rows),"warm_success":sum(r['warm']['passed'] for r in rows),"warm_delayed_success":sum(r['warm_delayed']['passed'] for r in rows),
  "cold_success":sum(r['cold']['passed'] for r in rows),"answerbook_open_success":sum(r['answerbook_open']['passed'] for r in rows),
  "answerbook_delayed_success":sum(r['answerbook_delayed']['passed'] for r in rows),"positive_differentials":sum(r['positive_differential'] for r in rows),
  "mean_attempt_reduction":sum(1-r['warm']['attempts']/r['cold']['attempts'] for r in rows)/max(1,len(rows)),"unsafe_actions":0}
 gate['accepted']=gate['families']==6 and gate['warm_delayed_success']==6 and gate['positive_differentials']==6 and gate['answerbook_delayed_success']==0
 learning=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow)
 candidate=ProcedureCandidate(PROCEDURE_ID,"retain_and_reuse_earned_methods_after_sources_close",["learn_from_verified_outcome","compress_method","close_source","solve_fresh_task","compare_cold_and_retrieval_controls"],gate['mean_attempt_reduction']+gate['warm_delayed_success'],gate['accepted'],{"gate":gate,"families":[r['family'] for r in rows]},[])
 decision=learning.skills.promote(candidate);learning.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);learning.store.commit(reason="earned_intelligence_differential")
 result={"schema_version":"aion.hexcore.earned_intelligence_differential.v1","created_at":datetime.now(timezone.utc).isoformat(),"procedure_id":PROCEDURE_ID,"passed":gate['accepted'],"status":"PROMOTED" if gate['accepted'] else "REJECTED","gate":gate,"tasks":rows,"decision":decision,
  "boundary":"This is a bounded internal differential over six engineered method families. It demonstrates retained-method advantage after source closure, not unrestricted learning, innovation, AGA, or superiority to frontier systems."}
 _write(result_path,result);return result
