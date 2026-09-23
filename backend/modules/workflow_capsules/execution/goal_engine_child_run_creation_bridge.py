"""
Goal Engine Child-Run Creation Bridge v1

This module is the safe boundary between the Goal Engine
child_run_executor_bridge_packet and the Workflow Capsule runtime.

It does not execute external writes.
It does not mutate business state.
It does not grant permissions.
It only creates a Workflow Capsule dry-run preview from an approved bridge packet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)


SCHEMA_VERSION = "aion.goal_engine.child_workflow_run_creation_preview.v1"


def _blocked(reason: str, *, packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "trace_type": "child_workflow_run_creation_preview",
        "status": "blocked",
        "blocked_reasons": [reason],
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_business_state": False,
        "would_grant_permission": False,
        "child_workflow_run_created": False,
        "source_packet_trace_type": (packet or {}).get("trace_type"),
    }


def create_child_workflow_run_preview_from_bridge_packet(
    packet: Dict[str, Any],
    *,
    runner: Optional[WorkflowCapsuleRunner] = None,
    available_vault_requirements: Optional[list[str]] = None,
    rebuild_registry: bool = True,
) -> Dict[str, Any]:
    """
    Convert an approved Goal Engine child-run executor bridge packet into a
    Workflow Capsule dry-run preview.

    The trusted runtime inputs come only from packet["runtime_seed"].
    """

    if not isinstance(packet, dict):
        return _blocked("invalid_packet")

    if packet.get("trace_type") != "child_run_executor_bridge_packet":
        return _blocked("invalid_trace_type", packet=packet)

    if packet.get("status") != "ready_for_workflow_runtime":
        return _blocked("packet_not_ready_for_workflow_runtime", packet=packet)

    if packet.get("execution_allowed") is True:
        return _blocked("unexpected_execution_allowed_flag", packet=packet)

    seed = packet.get("runtime_seed")
    if not isinstance(seed, dict):
        return _blocked("missing_runtime_seed", packet=packet)

    workflow_id = str(seed.get("workflow_id") or "").strip()
    run_id = str(seed.get("run_id") or "").strip()

    if not workflow_id:
        return _blocked("missing_runtime_seed_workflow_id", packet=packet)

    if not run_id:
        return _blocked("missing_runtime_seed_run_id", packet=packet)

    if seed.get("external_writes_allowed") is True:
        return _blocked("runtime_seed_external_writes_not_allowed", packet=packet)

    if seed.get("business_mutation_allowed") is True:
        return _blocked("runtime_seed_business_mutation_not_allowed", packet=packet)

    runner = runner or WorkflowCapsuleRunner()

    result = runner.run_dry(
        workflow_id,
        inputs={
            "goal_engine_parent_goal_id": seed.get("parent_goal_id"),
            "goal_engine_child_goal_id": seed.get("child_goal_id"),
            "goal_engine_child_agent_id": seed.get("child_agent_id"),
            "goal_engine_child_glyph_id": seed.get("child_glyph_id"),
            "goal_engine_parent_run_id": packet.get("parent_run_id"),
            "goal_engine_child_run_id": run_id,
        },
        available_vault_requirements=available_vault_requirements or [],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "goal_engine_child_run_creation_bridge_review_only",
        },
        extra={
            "source": "GoalEngineChildRunCreationBridge",
            "source_packet_trace_type": packet.get("trace_type"),
            "source_packet_schema_version": packet.get("schema_version"),
            "runtime_seed": dict(seed),
            "dry_run_only": True,
            "visibility_only": True,
            "child_workflow_run_creation_preview": True,
        },
        rebuild_registry=rebuild_registry,
        create_approval=False,
    ).to_dict()

    return {
        "ok": bool(result.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "trace_type": "child_workflow_run_creation_preview",
        "status": "dry_run_created" if result.get("ok") else "dry_run_failed",
        "source_packet_trace_type": packet.get("trace_type"),
        "source_packet_schema_version": packet.get("schema_version"),
        "workflow_id": workflow_id,
        "requested_run_id": run_id,
        "workflow_capsule_run_id": result.get("run_id"),
        "canonical_key": result.get("canonical_key"),
        "display_name": result.get("display_name"),
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_business_state": False,
        "would_grant_permission": False,
        "child_workflow_run_created": False,
        "approval_created": False,
        "runtime_seed": dict(seed),
        "workflow_capsule_runner_result": result,
        "errors": list(result.get("errors") or []),
        "warnings": list(result.get("warnings") or []),
    }
