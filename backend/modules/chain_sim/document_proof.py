"""Canonical, privacy-preserving document proofs for GlyphChain.

Only commitments are accepted.  Human-readable document content, names, email
addresses, signatures and other personal data must remain in the originating
Tessaris workspace.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping


DOCUMENT_PROOF_TX_TYPE = "DOCUMENT_PROOF_V1"
DOCUMENT_PROOF_SCHEMA = "glyphchain.document-proof.v1"
DOCUMENT_PROOF_VERIFICATION_VERSION = "sha256-merkle-ed25519-v1"

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")

# These fields are deliberately rejected even when nested.  A proof transaction
# must never become an accidental public document or identity store.
_FORBIDDEN_KEYS = {
    "content",
    "document_content",
    "document_text",
    "email",
    "name",
    "phone",
    "address",
    "signature",
    "signature_image",
    "typed_name",
    "identity_email",
    "token",
}


class DocumentProofValidationError(ValueError):
    pass


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hash(value: Any, field: str) -> str:
    result = _clean(value).lower()
    if not _HEX_64.fullmatch(result):
        raise DocumentProofValidationError(f"{field} must be 64 lowercase hex characters")
    return result


def _identifier(value: Any, field: str) -> str:
    result = _clean(value)
    if not _SAFE_ID.fullmatch(result):
        raise DocumentProofValidationError(f"{field} contains unsupported characters or length")
    return result


def _find_forbidden(value: Any, path: str = "payload") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().lower()
            child_path = f"{path}.{key_text}"
            if key_text in _FORBIDDEN_KEYS:
                return child_path
            found = _find_forbidden(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden(child, f"{path}[{index}]")
            if found:
                return found
    return None


def normalize_document_proof_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and return the only canonical DOCUMENT_PROOF_V1 payload shape."""
    if not isinstance(payload, Mapping):
        raise DocumentProofValidationError("payload must be an object")

    forbidden = _find_forbidden(payload)
    if forbidden:
        raise DocumentProofValidationError(f"private or human-readable field is forbidden: {forbidden}")

    allowed = {
        "schema_version",
        "proof_id",
        "document_id_commitment",
        "document_hash",
        "signed_copy_hash",
        "signatures_root",
        "audit_root",
        "issuer_key_id",
        "completed_at_ms",
        "policy_version",
        "verification_version",
    }
    unexpected = sorted(str(key) for key in payload.keys() if str(key) not in allowed)
    if unexpected:
        raise DocumentProofValidationError(f"unsupported payload fields: {', '.join(unexpected)}")

    schema = _clean(payload.get("schema_version"))
    if schema != DOCUMENT_PROOF_SCHEMA:
        raise DocumentProofValidationError(f"schema_version must be {DOCUMENT_PROOF_SCHEMA}")

    verification = _clean(payload.get("verification_version"))
    if verification != DOCUMENT_PROOF_VERIFICATION_VERSION:
        raise DocumentProofValidationError(
            f"verification_version must be {DOCUMENT_PROOF_VERIFICATION_VERSION}"
        )

    try:
        completed_at_ms = int(payload.get("completed_at_ms"))
    except (TypeError, ValueError):
        raise DocumentProofValidationError("completed_at_ms must be an integer") from None
    if completed_at_ms <= 0:
        raise DocumentProofValidationError("completed_at_ms must be greater than zero")

    return {
        "schema_version": DOCUMENT_PROOF_SCHEMA,
        "proof_id": _identifier(payload.get("proof_id"), "proof_id"),
        "document_id_commitment": _hash(payload.get("document_id_commitment"), "document_id_commitment"),
        "document_hash": _hash(payload.get("document_hash"), "document_hash"),
        "signed_copy_hash": _hash(payload.get("signed_copy_hash"), "signed_copy_hash"),
        "signatures_root": _hash(payload.get("signatures_root"), "signatures_root"),
        "audit_root": _hash(payload.get("audit_root"), "audit_root"),
        "issuer_key_id": _identifier(payload.get("issuer_key_id"), "issuer_key_id"),
        "completed_at_ms": completed_at_ms,
        "policy_version": _identifier(payload.get("policy_version"), "policy_version"),
        "verification_version": DOCUMENT_PROOF_VERIFICATION_VERSION,
    }


def document_proof_result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the deterministic, non-financial execution receipt."""
    normalized = normalize_document_proof_payload(payload)
    return {
        "op": DOCUMENT_PROOF_TX_TYPE,
        "proof_id": normalized["proof_id"],
        "document_hash": normalized["document_hash"],
        "proof_status": "RECORDED_PENDING_BLOCK_FINALITY",
        "would_move_money": False,
        "would_require_photon": False,
        "would_require_token": False,
        "would_require_wallet": False,
    }
