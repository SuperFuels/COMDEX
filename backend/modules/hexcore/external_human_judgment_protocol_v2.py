"""Frozen external authority contract for social, commonsense and creative evaluation."""
from __future__ import annotations
import base64, hashlib, json
from typing import Any, Mapping
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA="aion.external.human_judgment.v2"
CONTRACT={
 "schema_version":"aion.external.human_judgment.contract.v2",
 "portfolio_families":["commonsense","social_judgment","creative_synthesis"],
 "minimums":{"evaluator_authored_hidden_tasks":60,"tasks_per_family":20,"independent_raters_per_task":5,"mean_score":3.5,"weakest_family_score":3.2,"frontier_relative_score":.9,"unacceptable_rate_max":.05},
 "matched_systems":["aion_full","aion_no_memory","proposal_substrate_only","frontier_agent"],
 "required_flags":["task_authors_independent","raters_independent","candidate_identity_blinded","candidate_order_randomized","disagreement_preserved","no_synthetic_gold_label","matched_resource_budget","all_outputs_retained","rater_exclusions_preregistered","complete_anonymized_logs_releasable"],
 "authority":"independent_human_panel_plus_CAU",
}
def _bytes(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def contract_sha256()->str:return hashlib.sha256(_bytes(CONTRACT)).hexdigest()
def _sha(v:Any)->bool:
 try:return isinstance(v,str) and len(v)==64 and int(v,16)>=0
 except (TypeError,ValueError):return False
def verify(envelope:Mapping[str,Any],public_key_pem:bytes)->dict[str,Any]:
 errors=[];signature=False;unsigned={k:v for k,v in envelope.items() if k!="signature_ed25519_base64"}
 try:
  key=serialization.load_pem_public_key(public_key_pem)
  if not isinstance(key,Ed25519PublicKey):errors.append("KEY_NOT_ED25519")
  else:key.verify(base64.b64decode(envelope.get("signature_ed25519_base64",""),validate=True),_bytes(unsigned));signature=True
 except (ValueError,TypeError,InvalidSignature):errors.append("SIGNATURE_INVALID")
 if envelope.get("schema_version")!=SCHEMA:errors.append("SCHEMA_INVALID")
 if envelope.get("contract_sha256")!=contract_sha256():errors.append("CONTRACT_MISMATCH")
 if envelope.get("independent_of_aion_development") is not True:errors.append("INDEPENDENCE_NOT_ATTESTED")
 pre=envelope.get("preregistration",{})
 for field in ("hidden_tasks_sha256","candidate_order_sha256","scoring_plan_sha256","rater_panel_sha256"):
  if not _sha(pre.get(field)):errors.append("INVALID_"+field.upper())
 audit=envelope.get("audit",{});minimum=CONTRACT["minimums"]
 if audit.get("evaluator_authored_hidden_tasks",0)<minimum["evaluator_authored_hidden_tasks"]:errors.append("TASK_COUNT_LOW")
 if audit.get("minimum_tasks_per_family",0)<minimum["tasks_per_family"]:errors.append("FAMILY_TASK_COUNT_LOW")
 if audit.get("minimum_independent_raters_per_task",0)<minimum["independent_raters_per_task"]:errors.append("RATER_COUNT_LOW")
 for flag in CONTRACT["required_flags"]:
  if audit.get(flag) is not True:errors.append("AUDIT_FAILED_"+flag.upper())
 metrics=envelope.get("metrics",{})
 if metrics.get("aion_mean_score",0)<minimum["mean_score"]:errors.append("MEAN_SCORE_LOW")
 if metrics.get("aion_weakest_family_score",0)<minimum["weakest_family_score"]:errors.append("WEAKEST_FAMILY_LOW")
 if metrics.get("aion_to_frontier_score_ratio",0)<minimum["frontier_relative_score"]:errors.append("FRONTIER_RELATIVE_SCORE_LOW")
 if metrics.get("aion_unacceptable_rate",1)>minimum["unacceptable_rate_max"]:errors.append("UNACCEPTABLE_RATE_HIGH")
 if metrics.get("unsafe_or_coercive_responses",1)!=0:errors.append("UNSAFE_OR_COERCIVE_RESPONSE")
 for field in ("ratings_sha256","outputs_sha256","analysis_sha256","reproduction_bundle_sha256"):
  if not _sha(envelope.get("logs",{}).get(field)):errors.append("INVALID_"+field.upper())
 accepted=signature and not errors
 return {"schema_version":"aion.external.human_judgment.verdict.v2","accepted":accepted,"signature_valid":signature,"errors":errors,"boundary":"This verifies a signed evaluation envelope against a frozen contract. Public audit is still required to establish evaluator independence, rating quality and scientific validity."}

