import json

import pytest

from backend.modules.aion_inference import (
    execute_supplier_payment_review,
    render_supplier_payment_controls,
    verify_business_map_cartridge,
    verify_proof_receipt,
)
from backend.modules.aion_inference.business_map import (
    BUSINESS_MAP_TRUST_ANCHORS,
    SUPPLIER_PAYMENT_CARTRIDGE,
    SUPPLIER_PAYMENT_SIGNATURE,
)


CONTROL_IDS = (
    "independent_supplier_verification",
    "bank_detail_verification",
    "purchase_order_matching",
    "separation_of_duties",
    "payment_limits",
    "audit_record",
)


def test_signed_business_map_verifies_and_binds_provenance():
    result = verify_business_map_cartridge()
    assert result.passed
    assert result.reasons == ()
    assert result.glyph_address == f"glyph:sha256:{result.artifact_sha256}"


def test_business_map_tampering_fails_closed(tmp_path):
    cartridge = json.loads(SUPPLIER_PAYMENT_CARTRIDGE.read_text(encoding="utf-8"))
    cartridge["permissions"]["payment_execution_allowed"] = True
    target = tmp_path / SUPPLIER_PAYMENT_CARTRIDGE.name
    target.write_text(json.dumps(cartridge, indent=2) + "\n", encoding="utf-8")
    result = verify_business_map_cartridge(
        target, SUPPLIER_PAYMENT_SIGNATURE, BUSINESS_MAP_TRUST_ANCHORS
    )
    assert not result.passed
    assert "artifact_hash_mismatch" in result.reasons
    with pytest.raises(ValueError, match="failed closed"):
        execute_supplier_payment_review(
            actor_role="owner",
            cartridge_path=target,
            signature_path=SUPPLIER_PAYMENT_SIGNATURE,
            trust_anchors_path=BUSINESS_MAP_TRUST_ANCHORS,
        )


def test_business_map_never_grants_payment_execution_and_requires_evidence():
    incomplete = execute_supplier_payment_review(actor_role="finance_reviewer")
    assert not incomplete.model_call_required
    assert not incomplete.review_complete
    assert not incomplete.payment_execution_allowed
    assert incomplete.missing_evidence == CONTROL_IDS
    assert len(incomplete.controls) == 6
    assert verify_proof_receipt(incomplete.proof_receipt)

    references = {control_id: f"receipt:{control_id}" for control_id in CONTROL_IDS}
    complete = execute_supplier_payment_review(
        actor_role="finance_reviewer",
        evidence_references=references,
        variable_fields={
            "supplier_name": "Acme Components Ltd",
            "invoice_reference": "INV-2048",
            "payment_amount": "EUR 1250.00",
        },
        human_approved=True,
    )
    assert complete.review_complete
    assert complete.missing_evidence == ()
    assert not complete.payment_execution_allowed
    assert verify_proof_receipt(complete.proof_receipt)
    assert set(complete.proof_receipt["evidence_reference_sha256"]) == set(CONTROL_IDS)
    assert complete.proof_receipt["variable_fields"]["invoice_reference"] == "INV-2048"

    with pytest.raises(ValueError, match="not permitted"):
        execute_supplier_payment_review(
            actor_role="finance_reviewer",
            variable_fields={"payment_destination": "unverified"},
        )


def test_business_map_rejects_unauthorized_role():
    with pytest.raises(PermissionError, match="not permitted"):
        execute_supplier_payment_review(actor_role="model")


def test_signed_business_map_renders_six_informational_controls_without_model():
    result = render_supplier_payment_controls()
    lines = result.answer.splitlines()
    assert result.route == "verified_business_map_policy"
    assert not result.model_call_required
    assert not result.payment_execution_allowed
    assert len(lines) == 6
    assert all(line.startswith(f"{index}.") for index, line in enumerate(lines, start=1))
    assert all("Risk prevented:" in line for line in lines)
    assert all("human evidence required:" in line for line in lines)
    assert verify_proof_receipt(result.proof_receipt)
    assert result.proof_receipt["model_calls"] == 0
