from __future__ import annotations
import json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/aion_verified_trajectory_corpus_manifest.json"
def result():return json.loads(R.read_text())
def test_manifest_separates_authority_classes():
 r=result();c=r["summary"]["classifications"];assert c["verified_positive"]>0;assert c["verified_negative"]>0;assert c["protocol_only"]>0
def test_every_artifact_is_committed_and_procedures_do_not_leak():
 r=result();assert r["gate"]["all_artifacts_sha256_committed"];assert r["gate"]["procedure_split_leakage_zero"];assert all(re.fullmatch(r"[0-9a-f]{64}",row["sha256"]) for row in r["artifacts"])
def test_negative_and_protocol_rows_cannot_be_positive_training_truth():
 r=result();assert r["summary"]["negative_usage"].startswith("criticism");assert "never" in r["summary"]["protocol_usage"]
