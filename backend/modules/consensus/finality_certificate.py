"""Portable verification for signed GlyphChain quorum-finality certificates.

The verifier is deliberately independent of the live consensus engine.  A
certificate is only trust-anchored when its validator-set root matches a root
supplied by the caller from a trusted checkpoint or genesis record.
"""

from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
from typing import Any, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CERTIFICATE_SCHEMA_V1 = "glyphchain.quorum-finality-certificate.v1"
CERTIFICATE_SCHEMA = "glyphchain.quorum-finality-certificate.v2"
VOTE_DOMAIN = "GLYPHCHAIN_FINALITY_PRECOMMIT_V1"
VOTE_DOMAIN_V2 = "GLYPHCHAIN_FINALITY_PRECOMMIT_V2"
MAX_VALIDATORS = 256
MAX_FINALITY_VOTES = MAX_VALIDATORS


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validator_set_root(validators: list[Mapping[str, Any]]) -> str:
    if len(validators) > MAX_VALIDATORS:
        raise ValueError("finality_validator_limit_exceeded")
    normalized = sorted([
        {
            "validator_id": str(item.get("validator_id") or "").strip(),
            "power": int(item.get("power") or 0),
            "public_key_base64": str(item.get("public_key_base64") or "").strip(),
        }
        for item in validators
    ], key=lambda item: item["validator_id"])
    return sha256(_canonical(normalized)).hexdigest()


def vote_sign_bytes(certificate: Mapping[str, Any], validator_id: str) -> bytes:
    message = {
        "domain": VOTE_DOMAIN_V2 if certificate.get("schema_version") == CERTIFICATE_SCHEMA else VOTE_DOMAIN,
        "chain_id": certificate.get("chain_id"),
        "network_id": certificate.get("network_id"),
        "height": int(certificate.get("height") or 0),
        "round": int(certificate.get("round") or 0),
        "block_id": certificate.get("block_id"),
        "vote_type": "PRECOMMIT",
        "validator_id": validator_id,
        "validator_set_root": certificate.get("validator_set_root"),
    }
    if certificate.get("schema_version") == CERTIFICATE_SCHEMA:
        message["ledger_commitment"] = certificate.get("ledger_commitment")
        message["txs_root"] = certificate.get("txs_root")
    return _canonical(message)


def verify_finality_vote(
    certificate_context: Mapping[str, Any],
    *,
    validator: Mapping[str, Any],
    signature_base64: str,
) -> bool:
    """Verify one certificate-domain vote against an anchored validator entry."""
    validator_id = str(validator.get("validator_id") or "").strip()
    public_key_base64 = str(validator.get("public_key_base64") or "").strip()
    if not validator_id or not public_key_base64 or not signature_base64:
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_base64, validate=True))
        key.verify(
            base64.b64decode(str(signature_base64), validate=True),
            vote_sign_bytes(certificate_context, validator_id),
        )
        return True
    except (ValueError, InvalidSignature):
        return False


def build_finality_certificate(
    *,
    chain_id: str,
    network_id: str,
    height: int,
    round: int,
    block_id: str,
    validator_set: Iterable[Mapping[str, Any]],
    votes: Iterable[Mapping[str, Any]],
    checkpoint_id: str | None = None,
    ledger_commitment: str | None = None,
    txs_root: str | None = None,
) -> dict[str, Any]:
    """Build the portable certificate shape from already signed PRECOMMIT votes.

    The returned object is not trusted merely because it is well formed.  Its
    ``validator_set_root`` must still be compared with a trusted genesis or
    checkpoint root by :func:`verify_finality_certificate`.
    """
    validator_items = list(validator_set)
    vote_items = list(votes)
    if len(validator_items) > MAX_VALIDATORS:
        raise ValueError("finality_validator_limit_exceeded")
    if len(vote_items) > MAX_FINALITY_VOTES:
        raise ValueError("finality_vote_limit_exceeded")
    validators = sorted(
        [
            {
                "validator_id": str(item.get("validator_id") or "").strip(),
                "power": int(item.get("power") or 0),
                "public_key_base64": str(item.get("public_key_base64") or "").strip(),
            }
            for item in validator_items
        ],
        key=lambda item: item["validator_id"],
    )
    total_power = sum(int(item["power"]) for item in validators)
    certificate: dict[str, Any] = {
        "schema_version": CERTIFICATE_SCHEMA if ledger_commitment and txs_root else CERTIFICATE_SCHEMA_V1,
        "chain_id": str(chain_id),
        "network_id": str(network_id),
        "height": int(height),
        "round": int(round),
        "block_id": str(block_id),
        "vote_type": "PRECOMMIT",
        "validator_set": validators,
        "validator_set_root": validator_set_root(validators),
        "quorum_power": (2 * total_power + 2) // 3 if total_power > 0 else 0,
        "votes": sorted(
            [
                {
                    "validator_id": str(item.get("validator_id") or "").strip(),
                    "signature_base64": str(item.get("signature_base64") or "").strip(),
                }
                for item in vote_items
            ],
            key=lambda item: item["validator_id"],
        ),
    }
    if checkpoint_id:
        certificate["validator_set_checkpoint_id"] = str(checkpoint_id)
    if ledger_commitment and txs_root:
        certificate["ledger_commitment"] = str(ledger_commitment)
        certificate["txs_root"] = str(txs_root)
    return certificate


def verify_finality_certificate(
    certificate: Mapping[str, Any],
    *,
    trusted_validator_set_root: str | None = None,
    expected_chain_id: str | None = None,
    expected_height: int | None = None,
    expected_block_id: str | None = None,
    expected_ledger_commitment: str | None = None,
    expected_txs_root: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        schema_version = certificate.get("schema_version")
        chain_id = str(certificate.get("chain_id") or "")
        height = int(certificate.get("height") or 0)
        block_id = str(certificate.get("block_id") or "")
        if schema_version not in {CERTIFICATE_SCHEMA_V1, CERTIFICATE_SCHEMA}:
            errors.append("unsupported_finality_certificate_schema")
        if schema_version == CERTIFICATE_SCHEMA:
            for field in ("ledger_commitment", "txs_root"):
                value = str(certificate.get(field) or "")
                try:
                    if len(value) != 64:
                        raise ValueError
                    bytes.fromhex(value)
                except ValueError:
                    errors.append(f"finality_certificate_{field}_invalid")
            if not block_id.endswith(f"-C{str(certificate.get('ledger_commitment') or '')}"):
                errors.append("finality_certificate_block_commitment_mismatch")
        if certificate.get("vote_type") != "PRECOMMIT":
            errors.append("finality_certificate_vote_type_invalid")
        if expected_chain_id is not None and chain_id != expected_chain_id:
            errors.append("finality_certificate_chain_mismatch")
        if expected_height is not None and height != int(expected_height):
            errors.append("finality_certificate_height_mismatch")
        if expected_block_id is not None and block_id != expected_block_id:
            errors.append("finality_certificate_block_mismatch")
        if (
            expected_ledger_commitment is not None
            and str(certificate.get("ledger_commitment") or "") != str(expected_ledger_commitment)
        ):
            errors.append("finality_certificate_ledger_commitment_mismatch")
        if expected_txs_root is not None and str(certificate.get("txs_root") or "") != str(expected_txs_root):
            errors.append("finality_certificate_txs_root_mismatch")

        raw_validators = certificate.get("validator_set") or []
        raw_votes = certificate.get("votes") or []
        if not isinstance(raw_validators, list) or len(raw_validators) > MAX_VALIDATORS:
            raise ValueError("finality_validator_limit_exceeded")
        if not isinstance(raw_votes, list) or len(raw_votes) > MAX_FINALITY_VOTES:
            raise ValueError("finality_vote_limit_exceeded")
        validators = raw_validators
        supplied_root = str(certificate.get("validator_set_root") or "")
        computed_root = validator_set_root(validators)
        if not supplied_root or not hmac.compare_digest(supplied_root, computed_root):
            errors.append("validator_set_root_invalid")
        ids = [str(item.get("validator_id") or "").strip() for item in validators]
        if not ids or len(ids) != len(set(ids)) or any(not value for value in ids):
            errors.append("validator_set_membership_invalid")
        powers = {str(item.get("validator_id") or "").strip(): int(item.get("power") or 0) for item in validators}
        if any(power <= 0 for power in powers.values()):
            errors.append("validator_power_invalid")
        total_power = sum(powers.values())
        required_power = (2 * total_power + 2) // 3 if total_power > 0 else 0
        if int(certificate.get("quorum_power") or 0) != required_power:
            errors.append("quorum_power_invalid")

        public_keys = {
            str(item.get("validator_id") or "").strip(): str(item.get("public_key_base64") or "")
            for item in validators
        }
        seen: set[str] = set()
        signed_power = 0
        for vote in raw_votes:
            validator_id = str(vote.get("validator_id") or "").strip()
            if validator_id in seen:
                errors.append("duplicate_validator_vote")
                continue
            seen.add(validator_id)
            if validator_id not in powers:
                errors.append("vote_from_non_member")
                continue
            try:
                if not verify_finality_vote(
                    certificate,
                    validator={
                        "validator_id": validator_id,
                        "public_key_base64": public_keys[validator_id],
                    },
                    signature_base64=str(vote.get("signature_base64") or ""),
                ):
                    raise ValueError("invalid finality vote")
                signed_power += powers[validator_id]
            except ValueError:
                errors.append(f"validator_vote_signature_invalid:{validator_id}")
        if signed_power < required_power:
            errors.append("signed_quorum_not_reached")
    except (TypeError, ValueError, KeyError):
        errors.append("finality_certificate_malformed")
        supplied_root = str(certificate.get("validator_set_root") or "")
        computed_root = ""
        total_power = required_power = signed_power = 0

    trust_anchor_verified: bool | None = None
    if trusted_validator_set_root is not None:
        trust_anchor_verified = hmac.compare_digest(str(trusted_validator_set_root), supplied_root)
        if not trust_anchor_verified:
            errors.append("validator_set_trust_anchor_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "certificate_integrity_verified": not any(error != "validator_set_trust_anchor_mismatch" for error in errors),
        "validator_set_root": supplied_root,
        "computed_validator_set_root": computed_root,
        "trust_anchor_verified": trust_anchor_verified,
        "total_power": total_power,
        "required_power": required_power,
        "signed_power": signed_power,
    }
