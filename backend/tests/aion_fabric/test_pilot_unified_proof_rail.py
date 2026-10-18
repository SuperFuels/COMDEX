from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.canonical import canonical_hash
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.proof_rail import (
    ExistingGlyphChainProofPublisher,
    SelectiveProofRail,
)


def _rail(tmp_path, publisher=None) -> SelectiveProofRail:
    return SelectiveProofRail(
        tmp_path,
        mother_identity=DeviceIdentity(Ed25519PrivateKey.generate()),
        publisher=publisher,
    )


def _commit(rail: SelectiveProofRail, **overrides):
    values = {
        "event": "authorization",
        "object_id": "task_123",
        "scope_hash": canonical_hash({"title": "Collect the dry cleaning", "recipient": "Becca"}),
        "policy_version": "pilot-policy-v1",
        "outcome": "approved",
        "private_record": {"title": "Collect the dry cleaning", "recipient": "becca@example.test"},
        "idempotency_key": "proof-request-1",
    }
    values.update(overrides)
    return rail.commit(**values)


def test_commitment_contains_only_allowlisted_proof_data(tmp_path):
    rail = _rail(tmp_path)
    record = _commit(rail)
    rendered = json.dumps(record, sort_keys=True)

    assert record["event"] == "authorization"
    assert record["object_ref"].startswith("object_")
    assert record["private_record_stored"] is False
    assert "Collect the dry cleaning" not in rendered
    assert "becca@example.test" not in rendered
    assert record["would_move_money"] is False
    assert record["would_require_pho"] is False
    assert record["would_require_token"] is False
    assert record["would_require_wallet"] is False


def test_commit_is_idempotent_and_rejects_key_reuse(tmp_path):
    rail = _rail(tmp_path)
    first = _commit(rail)
    second = _commit(rail)
    assert second["commitment_id"] == first["commitment_id"]

    with pytest.raises(PermissionError):
        _commit(rail, outcome="declined")


def test_private_source_record_detects_tampering(tmp_path):
    rail = _rail(tmp_path)
    private = {"receipt_id": "receipt_1", "state": "accepted", "content": "private"}
    record = _commit(rail, event="acceptance", private_record=private)

    assert rail.verify(record["commitment_id"], private_record=private)["verified"] is True
    changed = {**private, "state": "declined"}
    verification = rail.verify(record["commitment_id"], private_record=changed)
    assert verification["verified"] is False
    assert verification["source_record_verified"] is False


def test_altered_local_commitment_signature_is_detected(tmp_path):
    rail = _rail(tmp_path)
    record = _commit(rail)
    state = json.loads(rail.path.read_text(encoding="utf-8"))
    state["commitments"][0]["outcome"] = "declined"
    rail.path.write_text(json.dumps(state), encoding="utf-8")

    result = rail.verify(record["commitment_id"])
    assert result["verified"] is False
    assert result["signature_verified"] is False


def test_correction_and_deletion_append_without_rewriting_original(tmp_path):
    rail = _rail(tmp_path)
    original = _commit(rail)
    correction = rail.correct(
        commitment_id=original["commitment_id"],
        private_record={"state": "completed", "corrected": True},
        scope_hash=canonical_hash({"corrected": True}),
        policy_version="pilot-policy-v1",
        outcome="completed",
        idempotency_key="proof-correction-1",
    )
    deletion = rail.record_private_deletion(
        commitment_id=original["commitment_id"],
        deletion_receipt={"record_id": "private_1", "deleted": True},
        scope_hash=canonical_hash({"record_id": "private_1"}),
        policy_version="pilot-policy-v1",
        idempotency_key="proof-deletion-1",
    )

    assert correction["correction_of"] == original["commitment_id"]
    assert deletion["previous_commitment_id"] == original["commitment_id"]
    assert deletion["outcome"] == "private_record_deleted"
    assert rail.verify(original["commitment_id"])["verified"] is True
    assert rail.health()["commitment_count"] == 3


def test_chain_outage_does_not_break_best_effort_app_flow(tmp_path):
    def offline(_commitment):
        raise ConnectionError("offline")

    rail = _rail(tmp_path, publisher=offline)
    record = _commit(rail)
    assert record["publication"] == {"status": "pending", "error": "ConnectionError"}
    health = rail.health()
    assert health["application_available"] is True
    assert health["chain_available"] is False
    assert health["pending_publications"] == 1


def test_required_chain_policy_fails_closed_without_false_claim(tmp_path):
    rail = _rail(tmp_path)
    with pytest.raises(RuntimeError, match="unavailable"):
        _commit(rail, publication_policy="required")
    assert rail.health()["commitment_count"] == 0


def test_existing_glyphchain_adapter_commits_privacy_safe_payload(tmp_path):
    rail = _rail(tmp_path, publisher=ExistingGlyphChainProofPublisher())
    record = _commit(rail)
    assert record["publication"]["status"] == "committed"
    assert record["publication"]["proof_commitment_id"].startswith("aion_proof_")
    assert rail.health()["chain_available"] is True
