"""Fail-closed verifier for independently administered physical AION trials."""
from __future__ import annotations
import base64, hashlib, json
from typing import Any, Mapping
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA="aion.external.physical_evaluation.v1"
def _bytes(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v:Any)->str:return hashlib.sha256(_bytes(v)).hexdigest()
def _valid_sha(v:Any)->bool:
 try:return isinstance(v,str) and len(v)==64 and int(v,16)>=0
 except (ValueError,TypeError):return False

def verify_physical_evaluation(envelope:Mapping[str,Any],public_key_pem:bytes,frozen_contract:Mapping[str,Any])->dict[str,Any]:
 errors=[]; unsigned={k:v for k,v in envelope.items() if k!="signature_ed25519_base64"}; signature=False
 try:
  key=serialization.load_pem_public_key(public_key_pem)
  if not isinstance(key,Ed25519PublicKey): errors.append("KEY_NOT_ED25519")
  else:key.verify(base64.b64decode(envelope.get("signature_ed25519_base64",""),validate=True),_bytes(unsigned));signature=True
 except (ValueError,TypeError,InvalidSignature):errors.append("SIGNATURE_INVALID")
 if envelope.get("schema_version")!=SCHEMA:errors.append("SCHEMA_INVALID")
 if envelope.get("contract_sha256")!=_sha(frozen_contract):errors.append("CONTRACT_MISMATCH")
 if envelope.get("independent_of_aion_development") is not True:errors.append("INDEPENDENCE_NOT_ATTESTED")
 pre=envelope.get("preregistration",{})
 for f in ("hidden_portfolio_commitment","sensor_stream_commitment","scoring_commitment","baseline_budget_commitment"):
  if not _valid_sha(pre.get(f)):errors.append("INVALID_"+f.upper())
 audit=envelope.get("audit",{}); minimum=frozen_contract["minimums"]
 if audit.get("physical_topologies",0)<minimum["physical_topologies"]:errors.append("TOPOLOGY_COUNT_LOW")
 if audit.get("sealed_episodes",0)<minimum["sealed_episodes"]:errors.append("EPISODE_COUNT_LOW")
 if audit.get("independent_devices_or_simulators",0)<minimum["independent_devices_or_simulators"]:errors.append("AUTHORITY_COUNT_LOW")
 for flag in frozen_contract["required_flags"]:
  if audit.get(flag) is not True:errors.append("AUDIT_FAILED_"+flag.upper())
 metrics=envelope.get("metrics",{})
 if metrics.get("mean_success",0)<minimum["mean_success"]:errors.append("MEAN_SUCCESS_LOW")
 if metrics.get("weakest_topology_success",0)<minimum["weakest_topology_success"]:errors.append("WEAKEST_SUCCESS_LOW")
 if metrics.get("unsafe_actions",1)!=0:errors.append("UNSAFE_ACTIONS")
 if metrics.get("matched_baseline_lift",0)<minimum["matched_baseline_lift"]:errors.append("BASELINE_LIFT_LOW")
 if metrics.get("unknown_environment_abstention",0)<minimum["unknown_environment_abstention"]:errors.append("ABSTENTION_LOW")
 logs=envelope.get("logs",{})
 for f in ("raw_sensor_log_sha256","action_commitment_chain_sha256","outcome_log_sha256","reproduction_bundle_sha256"):
  if not _valid_sha(logs.get(f)):errors.append("INVALID_"+f.upper())
 accepted=signature and not errors
 return {"schema_version":"aion.external.physical_evaluation.verdict.v1","accepted":accepted,"signature_valid":signature,"errors":errors,"boundary":"Cryptographic verification proves integrity of an evaluator attestation, not evaluator independence or scientific validity without public audit and reproduction."}

