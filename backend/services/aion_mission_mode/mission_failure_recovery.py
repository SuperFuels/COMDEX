"""
AION Phase 20Q — Mission Failure Recovery Protocol

Contract:
- Define recovery states.
- Preserve useful partial outputs.
- Emit failure receipt and recovery summary.
- Propose revised safe mission plan after failure.
- Never lose trace, proof, receipts, or partial outputs after failure.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Literal


RecoveryState = Literal[
    "failed_recoverable",
    "failed_final",
    "partial_success",
    "blocked_for_safety",
]


@dataclass(frozen=True)
class PreservedOutput:
    output_id: str
    step_id: str
    artifact_type: str
    business_container_path: str
    output_hash: str
    usable: bool = True


@dataclass(frozen=True)
class FailureReceipt:
    mission_id: str
    mission_run_id: str
    failure_state: RecoveryState
    failure_reason: str
    stopped_step_id: str
    trace_hash: str
    proof_hash: str
    partial_output_hashes: list[str]
    receipt_hashes: list[str]
    blocked_actions: list[str]
    failure_receipt_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def classify_failure_state(
    *,
    blocked_for_safety: bool = False,
    partial_outputs_available: bool = False,
    recoverable: bool = True,
) -> RecoveryState:
    if blocked_for_safety:
        return "blocked_for_safety"

    if partial_outputs_available and recoverable:
        return "partial_success"

    if recoverable:
        return "failed_recoverable"

    return "failed_final"


def preserve_partial_outputs(
    *,
    mission_id: str,
    mission_run_id: str,
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    preserved: list[dict[str, Any]] = []

    for index, output in enumerate(outputs, start=1):
        output_payload = {
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "output": output,
        }
        output_hash = _hash(output_payload)

        preserved_output = PreservedOutput(
            output_id=str(output.get("output_id") or f"partial_output_{index:02d}"),
            step_id=str(output.get("step_id") or ""),
            artifact_type=str(output.get("artifact_type") or "unknown"),
            business_container_path=str(output.get("business_container_path") or ""),
            output_hash=output_hash,
            usable=bool(output.get("usable", True)),
        )
        preserved.append(asdict(preserved_output))

    result = {
        "schema_version": "aion.failure_recovery.partial_outputs.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "preserved_outputs": preserved,
        "preserved_count": len(preserved),
        "partial_outputs_hash": "",
    }
    result["partial_outputs_hash"] = _hash({k: v for k, v in result.items() if k != "partial_outputs_hash"})
    return result


def create_failure_receipt(
    *,
    mission_id: str,
    mission_run_id: str,
    failure_state: RecoveryState,
    failure_reason: str,
    stopped_step_id: str,
    trace_hash: str,
    proof_hash: str,
    partial_output_hashes: list[str],
    receipt_hashes: list[str],
    blocked_actions: list[str],
) -> dict[str, Any]:
    receipt = FailureReceipt(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        failure_state=failure_state,
        failure_reason=failure_reason,
        stopped_step_id=stopped_step_id,
        trace_hash=trace_hash,
        proof_hash=proof_hash,
        partial_output_hashes=sorted(partial_output_hashes),
        receipt_hashes=sorted(receipt_hashes),
        blocked_actions=sorted(blocked_actions),
    )
    data = asdict(receipt)
    data["failure_receipt_hash"] = _hash({k: v for k, v in data.items() if k != "failure_receipt_hash"})
    return data


def create_recovery_summary(
    *,
    mission_id: str,
    mission_run_id: str,
    failure_receipt: dict[str, Any],
    preserved_outputs: dict[str, Any],
) -> dict[str, Any]:
    summary = {
        "schema_version": "aion.failure_recovery.summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "failure_state": failure_receipt["failure_state"],
        "failure_reason": failure_receipt["failure_reason"],
        "stopped_step_id": failure_receipt["stopped_step_id"],
        "preserved_count": preserved_outputs["preserved_count"],
        "preserved_outputs": preserved_outputs["preserved_outputs"],
        "blocked_actions": failure_receipt["blocked_actions"],
        "user_message": (
            "AION stopped the mission before a risky action. "
            "Useful partial outputs were preserved and a safer revised plan can be generated."
        ),
        "summary_hash": "",
    }
    summary["summary_hash"] = _hash({k: v for k, v in summary.items() if k != "summary_hash"})
    return summary


def propose_revised_safe_plan(
    *,
    mission_id: str,
    mission_run_id: str,
    original_steps: list[dict[str, Any]],
    blocked_actions: list[str],
) -> dict[str, Any]:
    blocked = {str(action) for action in blocked_actions}
    revised_steps: list[dict[str, Any]] = []

    for step in original_steps:
        action_type = str(step.get("action_type") or "")
        lane = str(step.get("lane") or "")

        if action_type in blocked or lane in {
            "external_action",
            "financial_action",
            "legal_action",
            "deployment_action",
            "memory_mutation",
        }:
            revised_steps.append(
                {
                    **step,
                    "decision": "checkpoint_required",
                    "requires_human_review": True,
                    "live_execution_allowed": False,
                    "revised_reason": "unsafe_or_blocked_action_replaced_with_checkpoint",
                }
            )
        else:
            revised_steps.append(
                {
                    **step,
                    "decision": step.get("decision", "safe_autonomous"),
                    "requires_human_review": bool(step.get("requires_human_review", False)),
                    "live_execution_allowed": False,
                }
            )

    revised_plan = {
        "schema_version": "aion.failure_recovery.revised_plan.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "revised_steps": revised_steps,
        "blocked_actions": sorted(blocked_actions),
        "live_side_effects_enabled": False,
        "revised_plan_hash": "",
    }
    revised_plan["revised_plan_hash"] = _hash({k: v for k, v in revised_plan.items() if k != "revised_plan_hash"})
    return revised_plan


def recover_failed_mission(
    *,
    mission_id: str,
    mission_run_id: str,
    failure_reason: str,
    stopped_step_id: str,
    trace_hash: str,
    proof_hash: str,
    outputs: list[dict[str, Any]],
    receipt_hashes: list[str],
    blocked_actions: list[str],
    original_steps: list[dict[str, Any]],
    blocked_for_safety: bool = False,
    recoverable: bool = True,
) -> dict[str, Any]:
    preserved = preserve_partial_outputs(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        outputs=outputs,
    )
    state = classify_failure_state(
        blocked_for_safety=blocked_for_safety,
        partial_outputs_available=bool(outputs),
        recoverable=recoverable,
    )
    failure_receipt = create_failure_receipt(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        failure_state=state,
        failure_reason=failure_reason,
        stopped_step_id=stopped_step_id,
        trace_hash=trace_hash,
        proof_hash=proof_hash,
        partial_output_hashes=[item["output_hash"] for item in preserved["preserved_outputs"]],
        receipt_hashes=receipt_hashes,
        blocked_actions=blocked_actions,
    )
    summary = create_recovery_summary(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        failure_receipt=failure_receipt,
        preserved_outputs=preserved,
    )
    revised_plan = propose_revised_safe_plan(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        original_steps=original_steps,
        blocked_actions=blocked_actions,
    )

    result = {
        "schema_version": "aion.failure_recovery.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "failure_state": state,
        "preserved_outputs": preserved,
        "failure_receipt": failure_receipt,
        "recovery_summary": summary,
        "revised_plan": revised_plan,
        "trace_hash": trace_hash,
        "proof_hash": proof_hash,
        "recovery_hash": "",
    }
    result["recovery_hash"] = _hash({k: v for k, v in result.items() if k != "recovery_hash"})
    return result


def atomic_recovery_transition(
    *,
    current_state: str,
    error_type: str,
    safety_violation_found: bool = False,
    partial_outputs_available: bool = False,
    recoverable: bool = True,
) -> dict[str, Any]:
    """
    Atomic recovery transition.

    This is the hard boundary used when runtime execution enters a fault,
    safety block, or intercepted policy violation.
    """
    target_state = classify_failure_state(
        blocked_for_safety=safety_violation_found,
        partial_outputs_available=partial_outputs_available,
        recoverable=recoverable,
    )

    transition = {
        "schema_version": "aion.failure_recovery.transition.v0",
        "current_state": current_state,
        "error_type": error_type,
        "target_state": target_state,
        "execution_threads_frozen": True,
        "active_vfs_handle_suspended": True,
        "snapshot_buffer_required": True,
        "process_permissions_dropped": True,
    }
    transition["transition_hash"] = _hash(transition)
    return transition


def recovery_cryptographic_closure_hash(
    *,
    failure_receipt_hash: str,
    trace_hash: str,
    proof_hash: str,
    partial_output_hashes: list[str],
    target_state: str,
) -> str:
    """
    Recovery closure hash:
    SHA256(receipt || trace || proof || partial outputs || target state)
    """
    return _hash(
        {
            "failure_receipt_hash": failure_receipt_hash,
            "trace_hash": trace_hash,
            "proof_hash": proof_hash,
            "partial_output_hashes": sorted(partial_output_hashes),
            "target_state": target_state,
        }
    )


def recover_failed_mission_with_atomic_transition(
    *,
    mission_id: str,
    mission_run_id: str,
    current_state: str,
    error_type: str,
    failure_reason: str,
    stopped_step_id: str,
    trace_hash: str,
    proof_hash: str,
    outputs: list[dict[str, Any]],
    receipt_hashes: list[str],
    blocked_actions: list[str],
    original_steps: list[dict[str, Any]],
    safety_violation_found: bool = False,
    recoverable: bool = True,
) -> dict[str, Any]:
    transition = atomic_recovery_transition(
        current_state=current_state,
        error_type=error_type,
        safety_violation_found=safety_violation_found,
        partial_outputs_available=bool(outputs),
        recoverable=recoverable,
    )

    recovery = recover_failed_mission(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        failure_reason=failure_reason,
        stopped_step_id=stopped_step_id,
        trace_hash=trace_hash,
        proof_hash=proof_hash,
        outputs=outputs,
        receipt_hashes=receipt_hashes,
        blocked_actions=blocked_actions,
        original_steps=original_steps,
        blocked_for_safety=safety_violation_found,
        recoverable=recoverable,
    )

    closure_hash = recovery_cryptographic_closure_hash(
        failure_receipt_hash=recovery["failure_receipt"]["failure_receipt_hash"],
        trace_hash=trace_hash,
        proof_hash=proof_hash,
        partial_output_hashes=recovery["failure_receipt"]["partial_output_hashes"],
        target_state=transition["target_state"],
    )

    result = {
        **recovery,
        "atomic_recovery_transition": transition,
        "recovery_closure_hash": closure_hash,
    }
    result["recovery_hash"] = _hash({k: v for k, v in result.items() if k != "recovery_hash"})
    return result
