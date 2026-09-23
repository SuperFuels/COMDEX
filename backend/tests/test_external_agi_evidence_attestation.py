from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.hexcore.external_agi_evidence_attestation import (
    SCHEMA_VERSION,
    _canonical_bytes,
    verify_external_attestation,
)


HANDOFF_PATH = Path(__file__).resolve().parents[2] / "results/aion_external_agi_evidence_handoff.json"
GATES = [
    "broad_domain_transfer",
    "autonomous_long_project_decomposition",
    "independently_owned_consequence_learning",
    "continual_improvement_without_forgetting",
    "natural_multimodal_physical_grounding",
    "social_commonsense_creative_judgment",
    "tool_and_representation_invention",
    "safe_abstention_and_human_escalation",
    "matched_frontier_and_human_comparison",
    "independent_reproducibility",
]


def _signed_envelope() -> tuple[dict, dict, bytes]:
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = "a" * 64
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "evaluator_id": "test-only-independent-evaluator",
        "independent_of_aion_development": True,
        "registry_commitment": handoff["registry_commitment"],
        "artifact_manifest_commitment": handoff["artifact_manifest_commitment"],
        "preregistration": {
            "sealed_portfolio_commitment": digest,
            "delayed_outcome_commitment": digest,
            "human_rater_panel_commitment": digest,
            "matched_budget_commitment": digest,
            "answer_reveal_commitment": digest,
        },
        "audit": {
            "portfolio_families": handoff["required_portfolio_families"],
            "matched_systems": handoff["required_matched_systems"],
            "audit_flags": {field: True for field in handoff["required_audit_fields"]},
        },
        "gate_results": [
            {"gate_id": gate_id, "passed": True, "evidence_commitment": digest}
            for gate_id in GATES
        ],
        "reproduction": {
            "independent_runs": 1,
            "artifact_hashes_verified": True,
            "complete_logs_published": True,
        },
    }
    envelope["signature_ed25519_base64"] = base64.b64encode(
        private_key.sign(_canonical_bytes(envelope))
    ).decode("ascii")
    return envelope, handoff, public_key


def test_complete_external_attestation_can_be_cryptographically_verified() -> None:
    envelope, handoff, public_key = _signed_envelope()
    verdict = verify_external_attestation(
        envelope=envelope,
        handoff=handoff,
        evaluator_public_key_pem=public_key,
    )
    assert verdict["signature_valid"] is True
    assert verdict["all_ten_gates_externally_attested"] is True
    assert verdict["external_certification_accepted"] is True
    assert verdict["errors"] == []


def test_any_post_signature_result_change_fails_closed() -> None:
    envelope, handoff, public_key = _signed_envelope()
    envelope["gate_results"][0]["passed"] = False
    verdict = verify_external_attestation(
        envelope=envelope,
        handoff=handoff,
        evaluator_public_key_pem=public_key,
    )
    assert verdict["signature_valid"] is False
    assert verdict["external_certification_accepted"] is False
    assert "SIGNATURE_INVALID" in verdict["errors"]
    assert "GATE_NOT_PASSED_BROAD_DOMAIN_TRANSFER" in verdict["errors"]


def test_incomplete_external_scope_is_rejected_even_with_valid_signature() -> None:
    envelope, handoff, _ = _signed_envelope()
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    envelope["audit"]["portfolio_families"] = envelope["audit"]["portfolio_families"][:-1]
    envelope.pop("signature_ed25519_base64")
    envelope["signature_ed25519_base64"] = base64.b64encode(
        private_key.sign(_canonical_bytes(envelope))
    ).decode("ascii")
    verdict = verify_external_attestation(
        envelope=envelope,
        handoff=handoff,
        evaluator_public_key_pem=public_key,
    )
    assert verdict["signature_valid"] is True
    assert verdict["external_certification_accepted"] is False
    assert "PORTFOLIO_FAMILIES_INCOMPLETE" in verdict["errors"]

