from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import inspect

from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.aion.goal_engine.dry_run import build_goal_engine_dry_run_manifest
from backend.modules.aion.goal_engine.resume_revalidation import (
    ResumeRevalidationContract,
    build_resume_revalidation_preview,
)
from backend.modules.aion.goal_engine.experiment_policy import (
    ExperimentPolicyContract,
    build_experiment_policy_preview,
)
from backend.modules.aion.goal_engine.checkpointing import (
    CheckpointContract,
    StateDeltaContract,
    build_checkpoint_preview,
    build_state_delta_preview,
)
from backend.modules.aion.goal_engine.decomposition import (
    GoalDecompositionContract,
    build_goal_decomposition_preview,
)
from backend.modules.aion.goal_engine.orchestrator import (
    OrchestratorContract,
    build_orchestrator_parent_child_aggregation_preview,
    build_orchestrator_preview,
)
from backend.modules.aion.goal_engine.outcome_scoring import (
    OUTCOME_SUCCESS_REQUIRES_EVIDENCE as OUTCOME_EVIDENCE_REQUIRED_BLOCK_REASON,
    build_outcome_score_preview,
    summarize_outcome_evidence_state,
)
from backend.modules.aion.goal_engine.evidence_sources import (
    build_evidence_pointer_preview,
)

from backend.modules.aion.goal_engine.memory_model import (
    MemoryPolicyContract,
    MemoryRecordContract,
    build_memory_policy_preview,
    build_memory_record_preview,
)
from backend.modules.aion.goal_engine.reproducibility import (
    build_goal_engine_reproducibility_block,
)


GOAL_ENGINE_PREVIEW_BUNDLE_SCHEMA_VERSION = "aion.goal_engine.preview_bundle.v1"


CANONICAL_GOAL_ENGINE_SAFETY_CONTRACT: dict[str, Any] = {
    "goals_grant_permission": False,
    "experiments_grant_permission": False,
    "loops_grant_permission": False,
    "learning_grants_permission": False,
    "external_writes_require_approval": True,
    "unbounded_loops_allowed": False,
    "resume_requires_environment_revalidation": True,
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _increment_count(counts: dict[str, int], key: Any) -> None:
    normalized = str(key or "unknown").strip() or "unknown"
    counts[normalized] = int(counts.get(normalized, 0)) + 1


def _call_orchestrator_parent_child_aggregation_preview_safely(**kwargs: Any) -> dict[str, Any]:
    """
    Call the canonical parent-child aggregation preview builder using only the
    keyword arguments supported by its current contract.

    This keeps preview_bundle stable while the standalone aggregation helper
    remains the source of truth for the exact public signature.
    """
    accepted = set(inspect.signature(build_orchestrator_parent_child_aggregation_preview).parameters)
    filtered = {key: value for key, value in kwargs.items() if key in accepted}
    return build_orchestrator_parent_child_aggregation_preview(**filtered)



def _build_step_trace_from_manifest(
    manifest: dict[str, Any],
    *,
    run_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for index, step in enumerate(_as_list(manifest.get("steps"))):
        step = _as_dict(step)
        contract = _as_dict(step.get("contract"))

        node_kind = str(
            step.get("step_type")
            or contract.get("node_kind")
            or contract.get("kind")
            or "goal_engine"
        )

        node_id = str(
            contract.get("goal_id")
            or contract.get("experiment_id")
            or contract.get("loop_id")
            or contract.get("outcome_id")
            or contract.get("reflection_id")
            or contract.get("accumulator_id")
            or contract.get("revalidation_id")
            or step.get("contract_id")
            or f"goal_engine_node_{index + 1}"
        )

        rows.append(
            {
                "trace_schema_version": "aion.goal_engine.step_trace.v1",
                "runtime": "aion_goal_engine",
                "run_id": run_id,
                "step_index": index,
                "node_id": node_id,
                "node_kind": node_kind,
                "contract_type": step.get("contract_type") or contract.get("contract_type") or "",
                "status": "dry_run_simulated",
                "dry_run_only": True,
                "external_write_performed": False,
                "grants_permission": False,
                "would_grant_permission": False,
                "would_execute": False,
                "would_write_external": False,
                "requires_approval_before_external_write": True,
                "bounded_execution": True,
                "validation_errors": list(step.get("validation_errors") or contract.get("validation_errors") or []),
                "summary": (
                    f"Goal Engine {node_kind} node was simulated only. "
                    "No permission was granted and no external write was performed."
                ),
            }
        )

    return rows


def _build_machine_trace(
    *,
    run_id: str,
    workflow_id: str,
    manifest: dict[str, Any],
    step_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    reproducibility = build_goal_engine_reproducibility_block(
        source_capsule={"workflow_id": workflow_id, "manifest": manifest},
        goal_contract=manifest,
        child_glyph_versions=[],
    )

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "goal_engine_preview",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "schema_version": GOAL_ENGINE_PREVIEW_BUNDLE_SCHEMA_VERSION,
        "reproducibility": reproducibility,
        "goal_engine_reproducibility": reproducibility,
        "agent_ready": False,
        "a2a_deferred": True,
        "commercial_interface_ready": False,
        "reason": "A2A is deferred until Goal Engine Sprint 1 is stable.",
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "step_count": len(step_trace),
        "manifest_valid": manifest.get("valid") is not False,
    }



def _build_orchestrator_parent_child_aggregation_runtime_summary(
    *,
    run_id: str,
    workflow_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    Build UI/dry-run visible parent-child aggregation previews for orchestrator nodes.

    This does not execute child runs, mutate parent goals, grant permission,
    write externally, or choose winners. It only makes aggregation intent visible
    in the normal Goal Engine preview bundle path.
    """
    steps = _as_list(manifest.get("steps"))
    previews: list[dict[str, Any]] = []

    for step in steps:
        step = _as_dict(step)
        contract = _as_dict(step.get("contract"))
        step_type = str(step.get("step_type") or contract.get("node_kind") or "").strip()

        if step_type not in {"orchestrator", "agent_orchestrator", "multi_agent_orchestrator"}:
            continue

        orchestrator_id = str(
            contract.get("orchestrator_id")
            or contract.get("node_id")
            or step.get("contract_id")
            or f"orchestrator_{len(previews) + 1}"
        ).strip()

        child_runs = _as_list(
            contract.get("child_runs")
            or contract.get("child_run_summaries")
            or contract.get("children")
            or []
        )

        child_glyphs = _as_list(
            contract.get("child_glyphs")
            or contract.get("glyphs")
            or contract.get("glyph_codes")
            or []
        )

        agent_assignments = _as_list(
            contract.get("agent_assignments")
            or contract.get("agents")
            or []
        )

        parent_goal_id = str(contract.get("parent_goal_id") or contract.get("goal_id") or "").strip()

        child_agents = _as_list(
            contract.get("child_agents")
            or contract.get("agent_children")
            or agent_assignments
            or child_runs
            or []
        )

        preview = _call_orchestrator_parent_child_aggregation_preview_safely(
            orchestrator_id=orchestrator_id,
            parent_goal_id=parent_goal_id,
            child_agents=child_agents,
            child_glyphs=child_glyphs,
            parent_goal_status=str(contract.get("parent_goal_status") or contract.get("status") or "derived_preview"),
            aggregation_policy=str(contract.get("aggregation_policy") or "visibility_only"),
            conflict_policy=str(contract.get("conflict_policy") or "human_review"),
        )

        preview.setdefault("orchestrator_id", orchestrator_id)
        preview.setdefault("run_id", run_id)
        preview.setdefault("workflow_id", workflow_id)
        previews.append(preview)

    blocked_reasons: list[str] = []
    for preview in previews:
        for reason in _as_list(preview.get("blocked_reasons")):
            if reason not in blocked_reasons:
                blocked_reasons.append(str(reason))

    return {
        "schema_version": "aion.goal_engine.orchestrator_parent_child_aggregation_runtime_summary.v1",
        "runtime": "aion_goal_engine",
        "trace_type": "orchestrator_parent_child_aggregation_runtime_summary",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "aggregation_count": len(previews),
        "parent_child_aggregation_previews": previews,
        "orchestrator_parent_child_aggregation_previews": previews,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "would_mutate_parent_goal": False,
    }



def _build_goal_runtime_summary(
    *,
    run_id: str,
    workflow_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the Sprint 2 goal-aware dry-run runtime summary.

    This is the first compact runtime view above raw contracts. It does not
    execute, write externally, grant permission, or mark outcomes successful
    without evidence.
    """
    steps = _as_list(manifest.get("steps"))

    goal_ids: list[str] = []
    experiment_ids: list[str] = []
    loop_ids: list[str] = []
    outcome_ids: list[str] = []

    goal_count = 0
    experiment_count = 0
    loop_count = 0
    outcome_evaluation_count = 0

    variant_count = 0
    exploration_factors: list[float] = []
    exploration_floors: list[float] = []
    confidence_thresholds: list[float] = []

    bounded_loop_count = 0
    unbounded_loop_count = 0
    max_total_iterations = 0
    max_total_external_writes = 0
    human_approval_required = False

    has_outcome_evidence = False
    successful_outcome_count = 0
    blocked_reasons: list[str] = []
    outcome_score_previews: list[dict[str, Any]] = []

    for step in steps:
        step = _as_dict(step)
        contract = _as_dict(step.get("contract"))
        step_type = str(step.get("step_type") or "").strip()

        if step_type == "goal":
            goal_count += 1
            goal_id = str(contract.get("goal_id") or step.get("contract_id") or "").strip()
            if goal_id:
                goal_ids.append(goal_id)

        elif step_type == "experiment":
            experiment_count += 1
            experiment_id = str(contract.get("experiment_id") or step.get("contract_id") or "").strip()
            if experiment_id:
                experiment_ids.append(experiment_id)

            variants = _as_list(contract.get("variants"))
            variant_count += len(variants)

            try:
                exploration_factors.append(float(contract.get("exploration_factor") or 0))
            except Exception:
                pass

            try:
                exploration_floors.append(float(contract.get("min_exploration_floor") or 0))
            except Exception:
                pass

            try:
                confidence_thresholds.append(float(contract.get("confidence_threshold") or 0))
            except Exception:
                pass

        elif step_type == "loop":
            loop_count += 1
            loop_id = str(contract.get("loop_id") or step.get("contract_id") or "").strip()
            if loop_id:
                loop_ids.append(loop_id)

            max_iterations = int(contract.get("max_iterations") or 0)
            max_external_writes = int(contract.get("max_external_writes") or 0)
            max_runtime_minutes = int(contract.get("max_runtime_minutes") or 0)

            max_total_iterations += max_iterations
            max_total_external_writes += max_external_writes

            if bool(contract.get("requires_human_approval")):
                human_approval_required = True

            if max_iterations > 0 and max_runtime_minutes > 0 and max_external_writes >= 0:
                bounded_loop_count += 1
            else:
                unbounded_loop_count += 1
                blocked_reasons.append("unbounded_loop_blocked")

        elif step_type == "outcome_evaluation":
            outcome_evaluation_count += 1
            outcome_id = str(contract.get("outcome_id") or step.get("contract_id") or "").strip()
            if outcome_id:
                outcome_ids.append(outcome_id)

            outcome_preview = build_outcome_score_preview(contract)
            outcome_score_previews.append(outcome_preview)

            evidence = _as_list(contract.get("evidence"))
            if evidence:
                has_outcome_evidence = True

            status = str(contract.get("status") or "").strip()
            if status == "success" and evidence:
                successful_outcome_count += 1
            elif status == "success" and not evidence:
                blocked_reasons.append(OUTCOME_EVIDENCE_REQUIRED_BLOCK_REASON)

    outcome_evidence_summary = summarize_outcome_evidence_state(outcome_score_previews)

    for reason in outcome_evidence_summary.get("blocked_reasons") or []:
        reason_text = str(reason or "").strip()
        if reason_text and reason_text not in blocked_reasons:
            blocked_reasons.append(reason_text)

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "goal_runtime_summary",
        "outcome_evidence_summary": outcome_evidence_summary,
        "run_id": run_id,
        "workflow_id": workflow_id,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "goal_count": goal_count,
        "experiment_count": experiment_count,
        "loop_count": loop_count,
        "outcome_evaluation_count": outcome_evaluation_count,
        "active_goal_ids": goal_ids,
        "experiment_ids": experiment_ids,
        "loop_ids": loop_ids,
        "outcome_ids": outcome_ids,
        "variant_count": variant_count,
        "min_exploration_floor": min(exploration_floors) if exploration_floors else 0,
        "max_exploration_factor": max(exploration_factors) if exploration_factors else 0,
        "max_confidence_threshold": max(confidence_thresholds) if confidence_thresholds else 0,
        "premature_convergence_blocked": experiment_count > 0,
        "bounded_loop_count": bounded_loop_count,
        "unbounded_loop_count": unbounded_loop_count,
        "max_total_iterations": max_total_iterations,
        "max_total_external_writes": max_total_external_writes,
        "human_approval_required": human_approval_required,
        "has_outcome_evidence": has_outcome_evidence,
        "evidence_required_for_success": True,
        "successful_outcome_count": successful_outcome_count,
        "blocked_reasons": sorted(set(blocked_reasons)),
    }




def _build_resume_revalidation_summary(
    *,
    contracts: list[Any],
) -> dict[str, Any]:
    previews: list[dict[str, Any]] = []

    for contract in contracts or []:
        if isinstance(contract, ResumeRevalidationContract):
            previews.append(build_resume_revalidation_preview(contract))

    blocked_reasons: list[str] = []
    for preview in previews:
        for reason in preview.get("blocked_reasons") or []:
            reason_text = str(reason or "").strip()
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "resume_revalidation_summary",
        "revalidation_count": len(previews),
        "resume_allowed_count": len([
            preview for preview in previews
            if preview.get("resume_allowed") is True
        ]),
        "resume_blocked_count": len([
            preview for preview in previews
            if preview.get("resume_blocked") is True
        ]),
        "safe_stop_required_count": len([
            preview for preview in previews
            if preview.get("safe_stop_required") is True
        ]),
        "blocked_reasons": blocked_reasons,
        "revalidation_previews": previews,
        "dry_run_only": True,
        "would_resume": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

def _build_checkpoint_runtime_summary(
    *,
    run_id: str,
    workflow_id: str,
    contracts: list[Any],
) -> dict[str, Any]:
    checkpoint_previews: list[dict[str, Any]] = []
    state_delta_previews: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for contract in contracts or []:
        if isinstance(contract, CheckpointContract):
            preview = build_checkpoint_preview(contract)
            checkpoint_previews.append(preview)
            for reason in preview.get("blocked_reasons") or []:
                reason_text = str(reason or "").strip()
                if reason_text and reason_text not in blocked_reasons:
                    blocked_reasons.append(reason_text)

        if isinstance(contract, StateDeltaContract):
            preview = build_state_delta_preview(contract)
            state_delta_previews.append(preview)
            for reason in preview.get("blocked_reasons") or []:
                reason_text = str(reason or "").strip()
                if reason_text and reason_text not in blocked_reasons:
                    blocked_reasons.append(reason_text)

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "checkpoint_runtime_summary",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "checkpoint_count": len(checkpoint_previews),
        "state_delta_count": len(state_delta_previews),
        "resume_blocked_count": len([
            item for item in checkpoint_previews
            if item.get("resume_blocked_until_revalidated") is True
        ]),
        "full_payload_blocked_count": len([
            item for item in state_delta_previews
            if item.get("full_payload_blocked") is True
        ]),
        "blocked_reasons": blocked_reasons,
        "checkpoint_previews": checkpoint_previews,
        "state_delta_previews": state_delta_previews,
        "dry_run_only": True,
        "would_resume": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }



def _build_experiment_runtime_summary(*, contracts: list[Any]) -> dict[str, Any]:
    experiment_policy_previews: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for contract in contracts:
        if isinstance(contract, ExperimentPolicyContract):
            preview = build_experiment_policy_preview(contract)
            experiment_policy_previews.append(preview)

            for reason in preview.get("blocked_reasons") or []:
                reason_text = str(reason or "").strip()
                if reason_text and reason_text not in blocked_reasons:
                    blocked_reasons.append(reason_text)

    bounded_count = len([
        item for item in experiment_policy_previews
        if item.get("bounded") is True and item.get("valid") is True
    ])

    unbounded_count = len([
        item for item in experiment_policy_previews
        if item.get("bounded") is not True
    ])

    metrics = [
        str(item.get("metric") or "").strip()
        for item in experiment_policy_previews
        if str(item.get("metric") or "").strip()
    ]

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "experiment_runtime_summary",
        "experiment_count": len(experiment_policy_previews),
        "bounded_experiment_count": bounded_count,
        "unbounded_experiment_count": unbounded_count,
        "variant_count": sum(int(item.get("variant_count") or 0) for item in experiment_policy_previews),
        "metric_count": len(set(metrics)),
        "premature_convergence_blocked": bool(experiment_policy_previews),
        "blocked_reasons": blocked_reasons,
        "experiment_policy_previews": experiment_policy_previews,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def _build_orchestrator_runtime_summary(*, contracts: list[Any]) -> dict[str, Any]:
    orchestrator_previews: list[dict[str, Any]] = []

    for contract in contracts:
        if isinstance(contract, OrchestratorContract):
            preview = build_orchestrator_preview(contract)
            orchestrator_previews.append(preview)

    blocked_reasons: list[str] = []
    for preview in orchestrator_previews:
        for reason in preview.get("blocked_reasons") or []:
            reason_text = str(reason or "").strip()
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

    coordination_modes: list[str] = []
    conflict_policies: list[str] = []

    for preview in orchestrator_previews:
        mode = str(preview.get("coordination_mode") or "").strip()
        if mode and mode not in coordination_modes:
            coordination_modes.append(mode)

        policy = str(preview.get("conflict_policy") or "").strip()
        if policy and policy not in conflict_policies:
            conflict_policies.append(policy)

    return {
        "runtime": "aion_goal_engine",
        "trace_type": "orchestrator_runtime_summary",
        "orchestrator_count": len(orchestrator_previews),
        "agent_count": sum(int(item.get("agent_count") or 0) for item in orchestrator_previews),
        "bounded_orchestrator_count": len([
            item for item in orchestrator_previews
            if item.get("bounded") is True
        ]),
        "unbounded_orchestrator_count": len([
            item for item in orchestrator_previews
            if item.get("bounded") is not True
        ]),
        "coordination_modes": coordination_modes,
        "conflict_policies": conflict_policies,
        "blocked_reasons": blocked_reasons,
        "orchestrator_previews": orchestrator_previews,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }



def _build_goal_decomposition_runtime_summary(*, contracts: list[Any]) -> dict[str, Any]:
    previews: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for contract in contracts:
        if isinstance(contract, GoalDecompositionContract):
            preview = build_goal_decomposition_preview(contract)

            # Visibility-only attachment. This path is allowed to describe
            # decomposition intent, but must not create child goals, mutate
            # parent goals, execute workflows, write externally, or grant
            # permission.
            preview.setdefault("dry_run_only", True)
            preview.setdefault("would_create_child_goals", False)
            preview.setdefault("would_mutate_parent_goal", False)
            preview.setdefault("would_execute", False)
            preview.setdefault("would_write_external", False)
            preview.setdefault("would_grant_permission", False)

            previews.append(preview)
            for reason in _as_list(preview.get("blocked_reasons")):
                reason = str(reason)
                if reason not in blocked_reasons:
                    blocked_reasons.append(reason)

    bounded_count = sum(1 for item in previews if item.get("bounded") is True)
    human_review_count = sum(
        1 for item in previews if item.get("approval_required_before_expansion") is True
    )

    return {
        "schema_version": "aion.goal_engine.goal_decomposition_runtime_summary.v1",
        "runtime": "aion_goal_engine",
        "trace_type": "goal_decomposition_runtime_summary",
        "decomposition_count": len(previews),
        "sub_goal_count": sum(len(_as_list(item.get("sub_goal_previews"))) for item in previews),

        # Canonical + legacy mirror count names.
        "bounded_count": bounded_count,
        "bounded_decomposition_count": bounded_count,
        "unbounded_decomposition_count": len(previews) - bounded_count,
        "human_review_count": human_review_count,
        "human_review_required_count": human_review_count,

        "blocked_reasons": blocked_reasons,
        "decomposition_previews": previews,
        "goal_decomposition_previews": previews,
        "child_goal_previews": previews,
        "dry_run_only": True,
        "would_create_child_goals": False,
        "would_mutate_parent_goal": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def _build_evidence_source_runtime_summary(*, contracts: list[Any]) -> dict[str, Any]:
    """
    Build typed evidence source previews for Boardroom and dry-run visibility.

    This is pointer-only. It does not fetch Gmail, CRM, analytics, booking,
    payment, screenshot, or file systems. It also does not mark outcomes
    successful or mutate business state.
    """
    evidence_source_previews: list[dict[str, Any]] = []

    for contract in contracts:
        if not isinstance(contract, dict):
            continue

        raw_items: list[Any] = []

        raw_items.extend(_as_list(contract.get("evidence_sources")))
        raw_items.extend(_as_list(contract.get("evidence_pointers")))
        raw_items.extend(_as_list(contract.get("evidence")))

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            pointer_type = str(
                item.get("pointer_type")
                or item.get("evidence_type")
                or item.get("source_type")
                or item.get("type")
                or ""
            )
            source_ref = str(item.get("source_ref") or item.get("ref") or "")
            goal_id = str(item.get("goal_id") or contract.get("goal_id") or "")
            outcome_id = str(item.get("outcome_id") or contract.get("outcome_id") or "")
            metadata = dict(item.get("metadata") or {})

            accepted = set(inspect.signature(build_evidence_pointer_preview).parameters)
            kwargs = {
                # Current canonical evidence pointer signature.
                "evidence_type": pointer_type,
                "reference_pointer": source_ref,
                "source": str(item.get("source") or item.get("provider") or pointer_type),
                "payload": {
                    "goal_id": goal_id,
                    "outcome_id": outcome_id,
                    "source_ref": source_ref,
                    "metadata": metadata,
                },
                "confidence": float(item.get("confidence") or item.get("score") or 0.0),

                # Compatibility aliases for older/future signatures.
                "pointer_type": pointer_type,
                "source_type": pointer_type,
                "source_ref": source_ref,
                "goal_id": goal_id,
                "linked_goal_id": goal_id,
                "outcome_id": outcome_id,
                "linked_outcome_id": outcome_id,
                "metadata": metadata,
            }

            preview = build_evidence_pointer_preview(
                **{key: value for key, value in kwargs.items() if key in accepted}
            )

            preview.setdefault("pointer_type", pointer_type)
            preview.setdefault("evidence_type", pointer_type)
            preview.setdefault("source_type", pointer_type)
            preview.setdefault("source_ref", source_ref)
            preview.setdefault("reference_pointer", source_ref)
            preview.setdefault("goal_id", goal_id)
            preview.setdefault("outcome_id", outcome_id)
            preview.setdefault("metadata", metadata)
            preview.setdefault("dry_run_only", True)
            preview.setdefault("would_read_external", False)
            preview.setdefault("would_write_external", False)
            preview.setdefault("would_grant_permission", False)
            preview.setdefault("would_fetch_external", False)
            preview.setdefault("would_mutate_business_state", False)
            preview.setdefault("would_mark_outcome_success", False)
            preview.setdefault("would_grant_permission", False)
            preview.setdefault("requires_human_review", True)
            evidence_source_previews.append(preview)

    type_counts: dict[str, int] = {}
    blocked_reasons: list[str] = []

    for preview in evidence_source_previews:
        _increment_count(type_counts, preview.get("pointer_type") or preview.get("evidence_type"))
        for reason in _as_list(preview.get("blocked_reasons")):
            reason = str(reason)
            if reason and reason not in blocked_reasons:
                blocked_reasons.append(reason)

    return {
        "schema_version": "aion.goal_engine.evidence_source_runtime_summary.v1",
        "runtime": "aion_goal_engine",
        "trace_type": "evidence_source_runtime_summary",
        "evidence_source_count": len(evidence_source_previews),
        "type_counts": type_counts,
        "blocked_reasons": blocked_reasons,
        "evidence_source_previews": evidence_source_previews,
        "evidence_pointer_previews": evidence_source_previews,
        "dry_run_only": True,
        "would_fetch_external": False,
        "would_mutate_business_state": False,
        "would_mark_outcome_success": False,
        "would_grant_permission": False,
        "requires_human_review": True,
    }



def _iter_manifest_contracts_by_trace_type(
    *,
    manifest: dict[str, Any] | None,
    trace_type: str,
) -> list[dict[str, Any]]:
    source = manifest if isinstance(manifest, dict) else {}
    records: list[dict[str, Any]] = []

    for step in _as_list(source.get("steps")):
        if not isinstance(step, dict):
            continue

        candidates = [
            step.get("contract"),
            step.get("payload"),
            step.get("preview"),
            step,
        ]

        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("trace_type") == trace_type:
                records.append(dict(candidate))
                break

    return records


def _build_child_run_executor_bridge_runtime_summary(
    *,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest = dict(manifest or {})

    packets = list(
        manifest.get("child_run_executor_bridge_packets")
        or manifest.get("workflow_run_creation_bridge_packets")
        or []
    )

    if not packets:
        packets = _iter_manifest_contracts_by_trace_type(
            manifest=manifest,
            trace_type="child_run_executor_bridge_packet",
        )

    allowed_count = sum(
        1 for packet in packets if dict(packet or {}).get("workflow_run_creation_allowed") is True
    )
    blocked_count = len(packets) - allowed_count

    return {
        "schema_version": "aion.goal_engine.child_run_executor_bridge_runtime_summary.v1",
        "trace_type": "child_run_executor_bridge_runtime_summary",
        "bridge_packet_count": len(packets),
        "workflow_run_creation_allowed_count": allowed_count,
        "blocked_bridge_packet_count": blocked_count,
        "child_run_executor_bridge_packets": packets,
        "workflow_run_creation_bridge_packets": packets,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "would_mutate_business_state": False,
        "requires_existing_workflow_runtime": bool(packets),
    }


def _build_memory_runtime_summary(*, contracts: list[Any]) -> dict[str, Any]:
    memory_record_previews: list[dict[str, Any]] = []
    memory_policy_previews: list[dict[str, Any]] = []

    for contract in contracts:
        if isinstance(contract, MemoryRecordContract):
            memory_record_previews.append(build_memory_record_preview(contract))
        elif isinstance(contract, MemoryPolicyContract):
            memory_policy_previews.append(build_memory_policy_preview(contract))
        elif isinstance(contract, dict):
            trace_type = str(contract.get("trace_type") or contract.get("kind") or contract.get("type") or "")
            if trace_type in {"memory_record", "memory_record_preview"} or "memory_id" in contract:
                memory_record_previews.append(build_memory_record_preview(contract))
            elif trace_type in {"memory_policy", "memory_policy_preview"} or "policy_id" in contract:
                memory_policy_previews.append(build_memory_policy_preview(contract))

    tier_counts: dict[str, int] = {}
    write_guard_counts: dict[str, int] = {}
    read_guard_counts: dict[str, int] = {}
    retention_policy_counts: dict[str, int] = {}
    blocked_reasons: list[str] = []

    for preview in memory_record_previews:
        _increment_count(tier_counts, preview.get("tier"))
        for reason in preview.get("blocked_reasons") or []:
            reason = str(reason or "").strip()
            if reason and reason not in blocked_reasons:
                blocked_reasons.append(reason)

    for preview in memory_policy_previews:
        _increment_count(write_guard_counts, preview.get("write_guard"))
        _increment_count(read_guard_counts, preview.get("read_guard"))
        _increment_count(retention_policy_counts, preview.get("retention_policy"))
        for reason in preview.get("blocked_reasons") or []:
            reason = str(reason or "").strip()
            if reason and reason not in blocked_reasons:
                blocked_reasons.append(reason)

    valid_record_count = len([item for item in memory_record_previews if item.get("valid") is True])
    valid_policy_count = len([item for item in memory_policy_previews if item.get("valid") is True])

    return {
        "schema_version": "aion.goal_engine.memory_runtime_summary.v1",
        "trace_type": "memory_runtime_summary",
        "memory_record_count": len(memory_record_previews),
        "memory_policy_count": len(memory_policy_previews),
        "valid_record_count": valid_record_count,
        "blocked_record_count": len(memory_record_previews) - valid_record_count,
        "valid_policy_count": valid_policy_count,
        "blocked_policy_count": len(memory_policy_previews) - valid_policy_count,
        "tier_counts": tier_counts,
        "write_guard_counts": write_guard_counts,
        "read_guard_counts": read_guard_counts,
        "retention_policy_counts": retention_policy_counts,
        "blocked_reasons": blocked_reasons,
        "memory_record_previews": memory_record_previews,
        "memory_policy_previews": memory_policy_previews,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "would_write_memory": False,
    }


@dataclass(frozen=True)
class GoalEnginePreviewBundle:
    run_id: str
    workflow_id: str
    manifest: dict[str, Any]
    step_trace: list[dict[str, Any]]
    boardroom_trace: dict[str, Any]
    safety_contract: dict[str, Any]
    machine_trace: dict[str, Any]
    goal_runtime_summary: dict[str, Any]
    evidence_source_runtime_summary: dict[str, Any]
    evidence_source_previews: list[dict[str, Any]]
    evidence_pointer_previews: list[dict[str, Any]]
    checkpoint_runtime_summary: dict[str, Any]
    resume_revalidation_summary: dict[str, Any]
    experiment_runtime_summary: dict[str, Any]
    orchestrator_runtime_summary: dict[str, Any]
    goal_decomposition_runtime_summary: dict[str, Any]
    goal_decomposition_previews: list[dict[str, Any]]
    memory_runtime_summary: dict[str, Any]
    memory_record_previews: list[dict[str, Any]]
    memory_policy_previews: list[dict[str, Any]]
    parent_child_aggregation_runtime_summary: dict[str, Any]
    parent_child_aggregation_previews: list[dict[str, Any]]
    child_run_executor_bridge_runtime_summary: dict[str, Any]
    child_run_executor_bridge_packets: list[dict[str, Any]]

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GOAL_ENGINE_PREVIEW_BUNDLE_SCHEMA_VERSION,
            "runtime": "aion_goal_engine",
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "dry_run_only": True,
            "would_execute": False,
            "would_write_external": False,
            "would_grant_permission": False,
            "grants_permission": False,
            "manifest": dict(self.manifest),
            "step_trace": list(self.step_trace),
            "boardroom_trace": dict(self.boardroom_trace),
            "safety_contract": dict(self.safety_contract),
            "machine_trace": dict(self.machine_trace),
            "goal_runtime_summary": dict(self.goal_runtime_summary),
            "evidence_source_runtime_summary": dict(self.evidence_source_runtime_summary),
            "goal_engine_evidence_source_runtime_summary": dict(self.evidence_source_runtime_summary),
            "evidence_source_previews": list(self.evidence_source_previews),
            "evidence_pointer_previews": list(self.evidence_pointer_previews),
            "goal_engine_evidence_source_previews": list(self.evidence_source_previews),
            "goal_engine_evidence_pointer_previews": list(self.evidence_pointer_previews),
            "checkpoint_runtime_summary": dict(self.checkpoint_runtime_summary),
            "resume_revalidation_summary": dict(self.resume_revalidation_summary),
            "experiment_runtime_summary": dict(self.experiment_runtime_summary),
            "orchestrator_runtime_summary": dict(self.orchestrator_runtime_summary),
            "goal_decomposition_runtime_summary": dict(self.goal_decomposition_runtime_summary),
            "goal_engine_decomposition_runtime_summary": dict(self.goal_decomposition_runtime_summary),
            "goal_decomposition_previews": list(self.goal_decomposition_previews),
            "decomposition_previews": list(self.goal_decomposition_previews),
            "child_goal_previews": list(self.goal_decomposition_previews),
            "memory_runtime_summary": dict(self.memory_runtime_summary),
            "goal_engine_memory_runtime_summary": dict(self.memory_runtime_summary),
            "memory_record_previews": list(self.memory_record_previews),
            "memory_policy_previews": list(self.memory_policy_previews),
            "goal_engine_memory_record_previews": list(self.memory_record_previews),
            "goal_engine_memory_policy_previews": list(self.memory_policy_previews),
            "parent_child_aggregation_runtime_summary": dict(self.parent_child_aggregation_runtime_summary),
            "orchestrator_parent_child_aggregation_runtime_summary": dict(self.parent_child_aggregation_runtime_summary),
            "parent_child_aggregation_previews": list(self.parent_child_aggregation_previews),
            "orchestrator_parent_child_aggregation_previews": list(self.parent_child_aggregation_previews),
            "child_run_executor_bridge_runtime_summary": dict(self.child_run_executor_bridge_runtime_summary),
            "workflow_run_creation_bridge_runtime_summary": dict(self.child_run_executor_bridge_runtime_summary),
            "child_run_executor_bridge_packets": list(self.child_run_executor_bridge_packets),
            "workflow_run_creation_bridge_packets": list(self.child_run_executor_bridge_packets),
        }


def build_goal_engine_preview_bundle(
    *,
    run_id: str,
    workflow_id: str,
    contracts: list[Any] | None = None,
    manifest: dict[str, Any] | None = None,
    goal_engine_manifest: dict[str, Any] | None = None,
) -> GoalEnginePreviewBundle:
    contracts = list(contracts or [])

    if manifest is not None and goal_engine_manifest is None:
        goal_engine_manifest = manifest

    if goal_engine_manifest is not None:
        manifest = dict(goal_engine_manifest)
    else:
        manifest = build_goal_engine_dry_run_manifest(
            run_id=run_id,
            workflow_id=workflow_id,
            contracts=contracts,
        )

    safety_contract = {
        **CANONICAL_GOAL_ENGINE_SAFETY_CONTRACT,
        **_as_dict(manifest.get("safety_contract")),
    }

    manifest["safety_contract"] = safety_contract
    manifest["runtime"] = "aion_goal_engine"

    step_trace = _build_step_trace_from_manifest(manifest, run_id=run_id)
    boardroom_trace = build_goal_engine_boardroom_trace(manifest)

    parent_child_aggregation_runtime_summary = _build_orchestrator_parent_child_aggregation_runtime_summary(
        run_id=run_id,
        workflow_id=workflow_id,
        manifest=manifest,
    )

    machine_trace = _build_machine_trace(
        run_id=run_id,
        workflow_id=workflow_id,
        manifest=manifest,
        step_trace=step_trace,
    )

    machine_trace["parent_child_aggregation_runtime_summary"] = parent_child_aggregation_runtime_summary
    machine_trace["orchestrator_parent_child_aggregation_runtime_summary"] = parent_child_aggregation_runtime_summary
    machine_trace["parent_child_aggregation_previews"] = parent_child_aggregation_runtime_summary.get("parent_child_aggregation_previews", [])
    machine_trace["orchestrator_parent_child_aggregation_previews"] = parent_child_aggregation_runtime_summary.get("orchestrator_parent_child_aggregation_previews", [])

    goal_runtime_summary = _build_goal_runtime_summary(
        run_id=run_id,
        workflow_id=workflow_id,
        manifest=manifest,
    )

    evidence_source_runtime_summary = _build_evidence_source_runtime_summary(
        contracts=contracts,
    )
    evidence_source_previews = list(
        evidence_source_runtime_summary.get("evidence_source_previews")
        or evidence_source_runtime_summary.get("evidence_pointer_previews")
        or []
    )
    evidence_pointer_previews = list(
        evidence_source_runtime_summary.get("evidence_pointer_previews")
        or evidence_source_previews
        or []
    )

    machine_trace["evidence_source_runtime_summary"] = evidence_source_runtime_summary
    machine_trace["goal_engine_evidence_source_runtime_summary"] = evidence_source_runtime_summary
    machine_trace["evidence_source_previews"] = evidence_source_previews
    machine_trace["evidence_pointer_previews"] = evidence_source_previews
    machine_trace["goal_engine_evidence_source_previews"] = evidence_source_previews
    machine_trace["goal_engine_evidence_pointer_previews"] = evidence_pointer_previews

    checkpoint_runtime_summary = _build_checkpoint_runtime_summary(
        run_id=run_id,
        workflow_id=workflow_id,
        contracts=contracts,
    )

    resume_revalidation_summary = _build_resume_revalidation_summary(
        contracts=contracts,
    )

    experiment_runtime_summary = _build_experiment_runtime_summary(
        contracts=contracts,
    )

    orchestrator_runtime_summary = _build_orchestrator_runtime_summary(
        contracts=contracts,
    )

    goal_decomposition_runtime_summary = _build_goal_decomposition_runtime_summary(
        contracts=contracts,
    )

    goal_decomposition_previews = list(
        goal_decomposition_runtime_summary.get("goal_decomposition_previews")
        or goal_decomposition_runtime_summary.get("decomposition_previews")
        or []
    )

    machine_trace["goal_decomposition_runtime_summary"] = goal_decomposition_runtime_summary
    machine_trace["goal_engine_decomposition_runtime_summary"] = goal_decomposition_runtime_summary
    machine_trace["goal_decomposition_previews"] = goal_decomposition_previews
    machine_trace["decomposition_previews"] = goal_decomposition_previews
    machine_trace["child_goal_previews"] = goal_decomposition_previews

    memory_runtime_summary = _build_memory_runtime_summary(
        contracts=contracts,
    )

    memory_record_previews = list(memory_runtime_summary.get("memory_record_previews") or [])
    memory_policy_previews = list(memory_runtime_summary.get("memory_policy_previews") or [])

    machine_trace["memory_runtime_summary"] = memory_runtime_summary
    machine_trace["goal_engine_memory_runtime_summary"] = memory_runtime_summary
    machine_trace["memory_record_previews"] = memory_record_previews
    machine_trace["memory_policy_previews"] = memory_policy_previews
    machine_trace["goal_engine_memory_record_previews"] = memory_record_previews
    machine_trace["goal_engine_memory_policy_previews"] = memory_policy_previews

    child_run_executor_bridge_runtime_summary = _build_child_run_executor_bridge_runtime_summary(
        manifest=manifest,
    )
    child_run_executor_bridge_packets = list(
        child_run_executor_bridge_runtime_summary.get("child_run_executor_bridge_packets") or []
    )

    machine_trace["child_run_executor_bridge_runtime_summary"] = child_run_executor_bridge_runtime_summary
    machine_trace["workflow_run_creation_bridge_runtime_summary"] = child_run_executor_bridge_runtime_summary
    machine_trace["child_run_executor_bridge_packets"] = child_run_executor_bridge_packets
    machine_trace["workflow_run_creation_bridge_packets"] = child_run_executor_bridge_packets

    return GoalEnginePreviewBundle(
        run_id=run_id,
        workflow_id=workflow_id,
        manifest=manifest,
        step_trace=step_trace,
        boardroom_trace=boardroom_trace,
        safety_contract=safety_contract,
        machine_trace=machine_trace,
        goal_runtime_summary=goal_runtime_summary,
        evidence_source_runtime_summary=evidence_source_runtime_summary,
        evidence_source_previews=evidence_source_previews,
        evidence_pointer_previews=evidence_pointer_previews,
        checkpoint_runtime_summary=checkpoint_runtime_summary,
        resume_revalidation_summary=resume_revalidation_summary,
        experiment_runtime_summary=experiment_runtime_summary,
        orchestrator_runtime_summary=orchestrator_runtime_summary,
        goal_decomposition_runtime_summary=goal_decomposition_runtime_summary,
        goal_decomposition_previews=goal_decomposition_previews,
        memory_runtime_summary=memory_runtime_summary,
        memory_record_previews=memory_record_previews,
        memory_policy_previews=memory_policy_previews,
        parent_child_aggregation_runtime_summary=parent_child_aggregation_runtime_summary,
        parent_child_aggregation_previews=list(
            parent_child_aggregation_runtime_summary.get("parent_child_aggregation_previews", [])
        ),
        child_run_executor_bridge_runtime_summary=child_run_executor_bridge_runtime_summary,
        child_run_executor_bridge_packets=child_run_executor_bridge_packets,
    )
