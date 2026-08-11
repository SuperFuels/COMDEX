from __future__ import annotations
import base64,copy
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from backend.modules.hexcore.external_human_judgment_protocol_v2 import CONTRACT,SCHEMA,_bytes,contract_sha256,verify

def packet():
 p={"schema_version":SCHEMA,"contract_sha256":contract_sha256(),"evaluator_id":"independent-panel","independent_of_aion_development":True,"preregistration":{k:"a"*64 for k in ("hidden_tasks_sha256","candidate_order_sha256","scoring_plan_sha256","rater_panel_sha256")},"audit":{"evaluator_authored_hidden_tasks":60,"minimum_tasks_per_family":20,"minimum_independent_raters_per_task":5,**{k:True for k in CONTRACT["required_flags"]}},"metrics":{"aion_mean_score":3.8,"aion_weakest_family_score":3.4,"aion_to_frontier_score_ratio":.93,"aion_unacceptable_rate":.03,"unsafe_or_coercive_responses":0},"logs":{k:"b"*64 for k in ("ratings_sha256","outputs_sha256","analysis_sha256","reproduction_bundle_sha256")}}
 key=Ed25519PrivateKey.generate();p["signature_ed25519_base64"]=base64.b64encode(key.sign(_bytes(p))).decode();public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo);return p,public
def test_complete_signed_external_packet_passes():
 p,key=packet();assert verify(p,key)["accepted"]
def test_internal_or_incomplete_claim_fails_closed():
 p,key=packet();p["independent_of_aion_development"]=False;assert not verify(p,key)["accepted"]
def test_legitimate_disagreement_and_blinding_are_mandatory():
 p,key=packet();p["audit"]["disagreement_preserved"]=False;assert not verify(p,key)["accepted"]
