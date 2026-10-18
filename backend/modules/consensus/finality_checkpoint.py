"""Trusted validator-set checkpoints for portable GlyphChain finality.

The checkpoint file is deployment configuration, not network input.  Its
expected hash or validator-set root must be pinned by the operator.  This
prevents a peer from replacing both the validator list and its alleged trust
anchor inside a receipt.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from hashlib import sha256
import hmac
from pathlib import Path
from typing import Any, Mapping

from .finality_certificate import validator_set_root


CHECKPOINT_SCHEMA = "glyphchain.validator-set-checkpoint.v1"
MAX_VALIDATORS = 256


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class FinalityCheckpointError(ValueError):
    pass


def normalize_checkpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FinalityCheckpointError("checkpoint_must_be_object")
    raw_validators = value.get("validator_set") or []
    if not isinstance(raw_validators, list) or len(raw_validators) > MAX_VALIDATORS:
        raise FinalityCheckpointError("checkpoint_validator_limit_exceeded")
    validators = sorted(
        [
            {
                "validator_id": str(item.get("validator_id") or "").strip(),
                "power": int(item.get("power") or 0),
                "public_key_base64": str(item.get("public_key_base64") or "").strip(),
            }
            for item in raw_validators
            if isinstance(item, Mapping)
        ],
        key=lambda item: item["validator_id"],
    )
    ids = [item["validator_id"] for item in validators]
    if not validators or any(not item for item in ids) or len(ids) != len(set(ids)):
        raise FinalityCheckpointError("checkpoint_validator_membership_invalid")
    if any(item["power"] <= 0 or not item["public_key_base64"] for item in validators):
        raise FinalityCheckpointError("checkpoint_validator_entry_invalid")
    if any(len(item["validator_id"]) > 240 or len(item["public_key_base64"]) > 1024 for item in validators):
        raise FinalityCheckpointError("checkpoint_validator_entry_too_large")
    normalized = {
        "schema_version": str(value.get("schema_version") or ""),
        "chain_id": str(value.get("chain_id") or "").strip(),
        "network_id": str(value.get("network_id") or "").strip(),
        "epoch": int(value.get("epoch") or 0),
        "effective_height": int(value.get("effective_height") or 1),
        "validator_set": validators,
        "validator_set_root": validator_set_root(validators),
    }
    if normalized["schema_version"] != CHECKPOINT_SCHEMA:
        raise FinalityCheckpointError("checkpoint_schema_unsupported")
    if not normalized["chain_id"] or not normalized["network_id"]:
        raise FinalityCheckpointError("checkpoint_network_identity_required")
    if len(normalized["chain_id"]) > 240 or len(normalized["network_id"]) > 240:
        raise FinalityCheckpointError("checkpoint_network_identity_too_large")
    if normalized["epoch"] < 0 or normalized["effective_height"] <= 0:
        raise FinalityCheckpointError("checkpoint_height_or_epoch_invalid")
    supplied_root = str(value.get("validator_set_root") or "").strip()
    if supplied_root and not hmac.compare_digest(supplied_root, normalized["validator_set_root"]):
        raise FinalityCheckpointError("checkpoint_validator_set_root_invalid")
    checkpoint_payload = dict(normalized)
    normalized["checkpoint_id"] = sha256(_canonical(checkpoint_payload)).hexdigest()
    supplied_id = str(value.get("checkpoint_id") or "").strip()
    if supplied_id and not hmac.compare_digest(supplied_id, normalized["checkpoint_id"]):
        raise FinalityCheckpointError("checkpoint_id_invalid")
    return normalized


@dataclass(frozen=True)
class TrustedFinalityCheckpoint:
    value: dict[str, Any]
    source: str

    @property
    def validator_set_root(self) -> str:
        return str(self.value["validator_set_root"])

    @property
    def checkpoint_id(self) -> str:
        return str(self.value["checkpoint_id"])

    def validator(self, validator_id: str) -> dict[str, Any] | None:
        wanted = str(validator_id or "").strip()
        for item in self.value["validator_set"]:
            if item["validator_id"] == wanted:
                return dict(item)
        return None


def write_public_checkpoint(value: Mapping[str, Any], output_path: str | Path) -> Path:
    """Write the normalized public checkpoint without any private key material."""
    checkpoint = normalize_checkpoint(value)
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)
    return path


def verify_public_checkpoint(
    checkpoint_path: str | Path,
    *,
    expected_checkpoint_id: str | None = None,
    expected_validator_set_root: str | None = None,
) -> dict[str, Any]:
    """Verify a downloaded checkpoint against an independently obtained pin."""
    path = Path(checkpoint_path).expanduser().resolve()
    checkpoint = normalize_checkpoint(json.loads(path.read_text(encoding="utf-8")))
    wanted_id = str(expected_checkpoint_id or "").strip()
    wanted_root = str(expected_validator_set_root or "").strip()
    if not wanted_id and not wanted_root:
        raise FinalityCheckpointError("checkpoint_verification_requires_independent_pin")
    if wanted_id and not hmac.compare_digest(wanted_id, checkpoint["checkpoint_id"]):
        raise FinalityCheckpointError("trusted_checkpoint_id_mismatch")
    if wanted_root and not hmac.compare_digest(wanted_root, checkpoint["validator_set_root"]):
        raise FinalityCheckpointError("trusted_validator_set_root_mismatch")
    return checkpoint


def load_trusted_checkpoint_from_env() -> TrustedFinalityCheckpoint | None:
    path_text = str(os.getenv("GLYPHCHAIN_FINALITY_CHECKPOINT_PATH", "") or "").strip()
    inline = str(os.getenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", "") or "").strip()
    if path_text and inline:
        raise FinalityCheckpointError("configure_checkpoint_path_or_json_not_both")
    if not path_text and not inline:
        return None
    if path_text:
        path = Path(path_text).expanduser().resolve()
        raw = json.loads(path.read_text(encoding="utf-8"))
        source = str(path)
    else:
        raw = json.loads(inline)
        source = "environment"
    checkpoint = normalize_checkpoint(raw)
    expected_id = str(os.getenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", "") or "").strip()
    expected_root = str(os.getenv("GLYPHCHAIN_TRUSTED_VALIDATOR_SET_ROOT", "") or "").strip()
    if not expected_id and not expected_root:
        raise FinalityCheckpointError("checkpoint_requires_pinned_id_or_validator_set_root")
    if expected_id and not hmac.compare_digest(expected_id, str(checkpoint["checkpoint_id"])):
        raise FinalityCheckpointError("trusted_checkpoint_id_mismatch")
    if expected_root and not hmac.compare_digest(expected_root, str(checkpoint["validator_set_root"])):
        raise FinalityCheckpointError("trusted_validator_set_root_mismatch")
    require_governance = str(os.getenv("GLYPHCHAIN_REQUIRE_VALIDATOR_GOVERNANCE", "0") or "0").strip().lower() in {"1", "true", "yes", "on"}
    if require_governance and int(checkpoint.get("epoch") or 0) > 0:
        proof_path = str(os.getenv("GLYPHCHAIN_VALIDATOR_GOVERNANCE_PROOF_PATH", "") or "").strip()
        previous_id = str(os.getenv("GLYPHCHAIN_PREVIOUS_TRUSTED_CHECKPOINT_ID", "") or "").strip()
        if not proof_path or not previous_id:
            raise FinalityCheckpointError("validator_governance_proof_and_previous_checkpoint_pin_required")
        try:
            from .validator_governance import verify_transition_proof
            proof = json.loads(Path(proof_path).expanduser().resolve().read_text(encoding="utf-8"))
            result = verify_transition_proof(
                proof,
                expected_previous_checkpoint_id=previous_id,
                expected_next_checkpoint_id=checkpoint["checkpoint_id"],
            )
        except Exception as exc:
            raise FinalityCheckpointError("validator_governance_proof_invalid") from exc
        if not result.get("valid"):
            raise FinalityCheckpointError("validator_governance_proof_invalid")
    return TrustedFinalityCheckpoint(value=checkpoint, source=source)
