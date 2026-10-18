from __future__ import annotations
import base64,json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from backend.modules.hexcore.external_physical_evaluation_protocol import SCHEMA,_bytes,_sha,verify_physical_evaluation

ROOT=Path(__file__).resolve().parents[2]
def fixture():
 c=json.loads((ROOT/"results/aion_external_physical_evaluation_contract_v1.json").read_text()); k=Ed25519PrivateKey.generate(); pre={x:"a"*64 for x in ("hidden_portfolio_commitment","sensor_stream_commitment","scoring_commitment","baseline_budget_commitment")}; audit={"physical_topologies":3,"sealed_episodes":30,"independent_devices_or_simulators":2,**{x:True for x in c["required_flags"]}}; logs={x:"b"*64 for x in ("raw_sensor_log_sha256","action_commitment_chain_sha256","outcome_log_sha256","reproduction_bundle_sha256")}; e={"schema_version":SCHEMA,"contract_sha256":_sha(c),"evaluator_id":"independent_lab","independent_of_aion_development":True,"preregistration":pre,"audit":audit,"metrics":{"mean_success":.85,"weakest_topology_success":.7,"matched_baseline_lift":.15,"unknown_environment_abstention":.95,"unsafe_actions":0},"logs":logs}; e["signature_ed25519_base64"]=base64.b64encode(k.sign(_bytes(e))).decode(); pub=k.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo);return c,e,pub
def test_valid_signed_external_physical_result():
 c,e,p=fixture();assert verify_physical_evaluation(e,p,c)["accepted"]
def test_tampering_and_unsafe_action_fail_closed():
 c,e,p=fixture();e["metrics"]["unsafe_actions"]=1;v=verify_physical_evaluation(e,p,c);assert not v["accepted"];assert "SIGNATURE_INVALID" in v["errors"]
def test_missing_consent_fails_even_with_valid_signature():
 c,e,_=fixture();k=Ed25519PrivateKey.generate();e["audit"]["camera_microphone_and_device_consent_recorded"]=False;e["signature_ed25519_base64"]=base64.b64encode(k.sign(_bytes({x:y for x,y in e.items() if x!="signature_ed25519_base64"}))).decode();p=k.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo);v=verify_physical_evaluation(e,p,c);assert not v["accepted"]
