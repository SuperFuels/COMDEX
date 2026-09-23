"""Fail-closed verification and execution for Boardroom Business Map cartridges."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


BUSINESS_MAP_ROOT = Path(__file__).with_name("business_maps")
SUPPLIER_PAYMENT_CARTRIDGE = BUSINESS_MAP_ROOT / "supplier_payment_controls.v1.json"
SUPPLIER_PAYMENT_SIGNATURE = BUSINESS_MAP_ROOT / "supplier_payment_controls.v1.sig.json"
BUSINESS_MAP_TRUST_ANCHORS = BUSINESS_MAP_ROOT / "trust_anchors.v1.json"


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _content_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BusinessMapVerification:
    passed: bool
    reasons: tuple[str, ...]
    artifact_sha256: str
    key_id: str | None
    glyph_address: str | None


@dataclass(frozen=True)
class BusinessMapExecution:
    route: str
    review_complete: bool
    model_call_required: bool
    payment_execution_allowed: bool
    controls: tuple[Mapping[str, str], ...]
    missing_evidence: tuple[str, ...]
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BusinessMapPolicyAnswer:
    route: str
    answer: str
    model_call_required: bool
    payment_execution_allowed: bool
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_business_map_cartridge(
    cartridge_path: Path = SUPPLIER_PAYMENT_CARTRIDGE,
    signature_path: Path = SUPPLIER_PAYMENT_SIGNATURE,
    trust_anchors_path: Path = BUSINESS_MAP_TRUST_ANCHORS,
) -> BusinessMapVerification:
    raw = cartridge_path.read_bytes()
    artifact_sha256 = hashlib.sha256(raw).hexdigest()
    reasons: list[str] = []
    try:
        cartridge = json.loads(raw)
        signature = json.loads(signature_path.read_text(encoding="utf-8"))
        trust = json.loads(trust_anchors_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return BusinessMapVerification(False, (f"artifact_load_failed:{type(exc).__name__}",), artifact_sha256, None, None)

    key_id = signature.get("key_id")
    anchors = {item.get("key_id"): item for item in trust.get("anchors", ())}
    anchor = anchors.get(key_id)
    if signature.get("artifact") != cartridge_path.name:
        reasons.append("signature_artifact_name_mismatch")
    if signature.get("artifact_sha256") != artifact_sha256:
        reasons.append("artifact_hash_mismatch")
    if signature.get("algorithm") != "Ed25519" or not anchor or anchor.get("algorithm") != "Ed25519":
        reasons.append("untrusted_signature_key")
    elif not reasons:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(anchor["public_key_base64"]))
            public_key.verify(base64.b64decode(signature["signature_base64"]), raw)
        except (InvalidSignature, ValueError, KeyError):
            reasons.append("signature_verification_failed")

    if cartridge.get("schema_version") != "aion.boardroom_business_map.v1":
        reasons.append("unsupported_cartridge_schema")
    controls = cartridge.get("atomsheet", {}).get("controls", ())
    expected_controls = {
        "independent_supplier_verification", "bank_detail_verification",
        "purchase_order_matching", "separation_of_duties", "payment_limits", "audit_record",
    }
    control_ids = {item.get("control_id") for item in controls if isinstance(item, dict)}
    if len(controls) != 6 or control_ids != expected_controls:
        reasons.append("required_controls_incomplete")
    if any(
        not item.get("risk_prevented") or not item.get("human_evidence_required")
        for item in controls if isinstance(item, dict)
    ):
        reasons.append("control_contract_incomplete")

    sources = {item.get("source_id"): item for item in cartridge.get("provenance", {}).get("rag_sources", ())}
    source_refs = set(cartridge.get("atomsheet", {}).get("source_refs", ()))
    if not source_refs or not source_refs.issubset(sources):
        reasons.append("provenance_reference_missing")
    if any(_content_sha256(str(item.get("content", ""))) != item.get("content_sha256") for item in sources.values()):
        reasons.append("provenance_content_hash_mismatch")

    permissions = cartridge.get("permissions", {})
    if not permissions.get("human_approval_required") or permissions.get("payment_execution_allowed"):
        reasons.append("unsafe_permission_boundary")
    if cartridge.get("adapter_interface", {}).get("enabled"):
        reasons.append("adapter_must_remain_disabled")
    personal = cartridge.get("personal_map_boundary", {})
    if personal.get("personal_data_ingestion_allowed") or personal.get("neural_weight_training_allowed"):
        reasons.append("personal_map_boundary_violated")

    glyph_address = f"glyph:sha256:{artifact_sha256}" if not reasons else None
    return BusinessMapVerification(not reasons, tuple(reasons), artifact_sha256, key_id, glyph_address)


def execute_supplier_payment_review(
    *,
    actor_role: str,
    evidence_references: Mapping[str, str] | None = None,
    variable_fields: Mapping[str, str] | None = None,
    human_approved: bool = False,
    cartridge_path: Path = SUPPLIER_PAYMENT_CARTRIDGE,
    signature_path: Path = SUPPLIER_PAYMENT_SIGNATURE,
    trust_anchors_path: Path = BUSINESS_MAP_TRUST_ANCHORS,
) -> BusinessMapExecution:
    verification = verify_business_map_cartridge(cartridge_path, signature_path, trust_anchors_path)
    if not verification.passed:
        raise ValueError(f"business map verification failed closed: {','.join(verification.reasons)}")
    cartridge = json.loads(cartridge_path.read_text(encoding="utf-8"))
    allowed_roles = set(cartridge["permissions"]["allowed_roles"])
    if actor_role not in allowed_roles:
        raise PermissionError("actor role is not permitted by the business map")

    controls = tuple(cartridge["atomsheet"]["controls"])
    supplied = {key: value.strip() for key, value in (evidence_references or {}).items() if value.strip()}
    allowed_variable_fields = set(cartridge["reusable_context"]["model_may_fill"])
    supplied_variable_fields = {
        key: str(value).strip() for key, value in (variable_fields or {}).items() if str(value).strip()
    }
    unknown_variable_fields = set(supplied_variable_fields) - allowed_variable_fields
    if unknown_variable_fields:
        raise ValueError(
            f"variable fields are not permitted by the business map: {','.join(sorted(unknown_variable_fields))}"
        )
    required = tuple(item["control_id"] for item in controls)
    missing = tuple(control_id for control_id in required if control_id not in supplied)
    review_complete = not missing and human_approved
    payload = {
        "schema_version": "aion.business_map_execution_receipt.v1",
        "cartridge_id": cartridge["cartridge_id"],
        "cartridge_sha256": verification.artifact_sha256,
        "signature_key_id": verification.key_id,
        "glyph_address": verification.glyph_address,
        "actor_role": actor_role,
        "control_ids": required,
        "evidence_reference_sha256": {
            key: hashlib.sha256(value.encode()).hexdigest() for key, value in sorted(supplied.items())
        },
        "variable_fields": dict(sorted(supplied_variable_fields.items())),
        "missing_evidence": missing,
        "human_approved": human_approved,
        "review_complete": review_complete,
        "payment_execution_allowed": False,
        "model_calls": 0,
    }
    receipt = {**payload, "proof_receipt_sha256": _canonical_sha256(payload)}
    return BusinessMapExecution(
        route="verified_business_map",
        review_complete=review_complete,
        model_call_required=False,
        payment_execution_allowed=False,
        controls=controls,
        missing_evidence=missing,
        proof_receipt=receipt,
    )


def render_supplier_payment_controls(
    *,
    cartridge_path: Path = SUPPLIER_PAYMENT_CARTRIDGE,
    signature_path: Path = SUPPLIER_PAYMENT_SIGNATURE,
    trust_anchors_path: Path = BUSINESS_MAP_TRUST_ANCHORS,
) -> BusinessMapPolicyAnswer:
    """Render the signed informational policy without model or action authority."""
    verification = verify_business_map_cartridge(
        cartridge_path, signature_path, trust_anchors_path
    )
    if not verification.passed:
        raise ValueError(
            f"business map verification failed closed: {','.join(verification.reasons)}"
        )
    cartridge = json.loads(cartridge_path.read_text(encoding="utf-8"))
    controls = tuple(cartridge["atomsheet"]["controls"])
    lines = []
    for number, control in enumerate(controls, start=1):
        label = str(control["control_id"]).replace("_", " ").title()
        risk = str(control["risk_prevented"]).rstrip(". ")
        evidence = str(control["human_evidence_required"]).rstrip(". ")
        lines.append(
            f"{number}. {label} — Risk prevented: {risk}; "
            f"human evidence required: {evidence}."
        )
    answer = "\n".join(lines)
    payload = {
        "schema_version": "aion.business_map_policy_answer_receipt.v1",
        "cartridge_id": cartridge["cartridge_id"],
        "cartridge_sha256": verification.artifact_sha256,
        "signature_key_id": verification.key_id,
        "glyph_address": verification.glyph_address,
        "control_ids": [control["control_id"] for control in controls],
        "source_refs": list(cartridge["atomsheet"]["source_refs"]),
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "informational_only": True,
        "human_approval_still_required_before_payment": True,
        "payment_execution_allowed": False,
        "model_calls": 0,
    }
    receipt = {**payload, "proof_receipt_sha256": _canonical_sha256(payload)}
    return BusinessMapPolicyAnswer(
        route="verified_business_map_policy",
        answer=answer,
        model_call_required=False,
        payment_execution_allowed=False,
        proof_receipt=receipt,
    )
