from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def create_capability_receipt(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    step_id: str,
    tool_name: str,
    provider: str,
    action_type: str,
    requested_payload_hash: str,
    executed_payload_hash: str,
    before_state_hash: str,
    after_state_hash: str,
    evidence_hashes: list[str] | None = None,
    provider_response_hash: str = "sha256:none",
    rollback_available: bool = False,
    rollback_instructions: str | None = None,
    rollback_deadline: str | None = None,
    external_reference_id: str | None = None,
) -> dict[str, Any]:
    evidence = sorted(evidence_hashes or [])

    receipt = {
        "schema_version": "aion.capability_receipt.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "step_id": step_id,
        "tool_name": tool_name,
        "provider": provider,
        "action_type": action_type,
        "requested_payload_hash": requested_payload_hash,
        "executed_payload_hash": executed_payload_hash,
        "before_state_hash": before_state_hash,
        "after_state_hash": after_state_hash,
        "evidence_hashes": evidence,
        "provider_response_hash": provider_response_hash,
        "rollback_available": rollback_available,
        "rollback_instructions": rollback_instructions or "none",
        "rollback_deadline": rollback_deadline,
        "external_reference_id": external_reference_id,
        "receipt_hash": "",
    }

    receipt["receipt_hash"] = _hash({k: v for k, v in receipt.items() if k != "receipt_hash"})
    return receipt


def validate_capability_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    required = [
        "mission_id",
        "mission_run_id",
        "business_id",
        "step_id",
        "tool_name",
        "provider",
        "action_type",
        "requested_payload_hash",
        "executed_payload_hash",
        "before_state_hash",
        "after_state_hash",
        "provider_response_hash",
        "receipt_hash",
    ]

    for field in required:
        if not receipt.get(field):
            reasons.append(f"missing_{field}")

    hash_fields = [
        "requested_payload_hash",
        "executed_payload_hash",
        "before_state_hash",
        "after_state_hash",
        "provider_response_hash",
    ]

    for field in hash_fields:
        value = receipt.get(field, "")
        if not isinstance(value, str) or not value.startswith("sha256:"):
            reasons.append(f"invalid_{field}")

    for evidence_hash in receipt.get("evidence_hashes", []):
        if not isinstance(evidence_hash, str) or not evidence_hash.startswith("sha256:"):
            reasons.append("invalid_evidence_hash")

    expected_hash = _hash({k: v for k, v in receipt.items() if k != "receipt_hash"})
    if receipt.get("receipt_hash") != expected_hash:
        reasons.append("receipt_hash_mismatch")

    if receipt.get("rollback_available") is True:
        if receipt.get("rollback_instructions") in (None, "", "none"):
            reasons.append("rollback_available_without_instructions")

    valid = not reasons

    result = {
        "schema_version": "aion.capability_receipt_validation.v0",
        "mission_id": receipt.get("mission_id"),
        "mission_run_id": receipt.get("mission_run_id"),
        "business_id": receipt.get("business_id"),
        "step_id": receipt.get("step_id"),
        "receipt_hash": receipt.get("receipt_hash"),
        "valid": valid,
        "validation_state": "receipt_valid" if valid else "receipt_invalid",
        "reasons": reasons,
        "validation_hash": "",
    }
    result["validation_hash"] = _hash({k: v for k, v in result.items() if k != "validation_hash"})
    return result


def create_receipt_container_record(
    *,
    receipt: dict[str, Any],
    business_container_root: str,
) -> dict[str, Any]:
    if not business_container_root:
        raise ValueError("business_container_root is required")

    relative_path = (
        f"missions/{receipt['mission_id']}/runs/{receipt['mission_run_id']}/"
        f"receipts/{receipt['step_id']}_{receipt['action_type']}.json"
    )

    record = {
        "schema_version": "aion.receipt_container_record.v0",
        "business_id": receipt["business_id"],
        "mission_id": receipt["mission_id"],
        "mission_run_id": receipt["mission_run_id"],
        "step_id": receipt["step_id"],
        "receipt_hash": receipt["receipt_hash"],
        "business_container_root": business_container_root,
        "relative_path": relative_path,
        "contained_path": f"{business_container_root.rstrip('/')}/{relative_path}",
        "container_state": "business_container_bound",
        "container_record_hash": "",
    }
    record["container_record_hash"] = _hash(
        {k: v for k, v in record.items() if k != "container_record_hash"}
    )
    return record


def bind_receipt_to_mission_trace(
    *,
    receipt: dict[str, Any],
    trace_hash: str,
    proof_hash: str,
    replay_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    for name, value in {
        "trace_hash": trace_hash,
        "proof_hash": proof_hash,
        "replay_hash": replay_hash,
        "receipt_hash": receipt.get("receipt_hash"),
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            reasons.append(f"invalid_{name}")

    allowed = not reasons

    binding = {
        "schema_version": "aion.receipt_trace_binding.v0",
        "mission_id": receipt.get("mission_id"),
        "mission_run_id": receipt.get("mission_run_id"),
        "step_id": receipt.get("step_id"),
        "receipt_hash": receipt.get("receipt_hash"),
        "trace_hash": trace_hash,
        "proof_hash": proof_hash,
        "replay_hash": replay_hash,
        "allowed": allowed,
        "binding_state": "receipt_trace_bound" if allowed else "receipt_trace_binding_blocked",
        "reasons": reasons,
        "binding_hash": "",
    }
    binding["binding_hash"] = _hash({k: v for k, v in binding.items() if k != "binding_hash"})
    return binding


def summarize_capability_receipts(
    *,
    mission_id: str,
    mission_run_id: str,
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt_hashes = sorted(item["receipt_hash"] for item in receipts)
    rollback_count = sum(1 for item in receipts if item.get("rollback_available") is True)

    summary = {
        "schema_version": "aion.capability_receipt_summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "receipt_count": len(receipts),
        "rollback_available_count": rollback_count,
        "receipt_hashes": receipt_hashes,
        "summary_state": "capability_receipts_indexed",
        "summary_hash": "",
    }
    summary["summary_hash"] = _hash({k: v for k, v in summary.items() if k != "summary_hash"})
    return summary
