from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

from backend.modules.aion.goal_engine.registry import serialize_contract


def _safe_contract_id(payload: dict[str, Any]) -> str:
    for key in (
        "goal_id",
        "experiment_id",
        "loop_id",
        "outcome_id",
        "reflection_id",
        "accumulator_id",
        "revalidation_id",
        "session_id",
        "checkpoint_id",
    ):
        value = payload.get(key)
        if value:
            return str(value)
    return "unknown_contract"


def _infer_manifest_step_type(payload: dict[str, Any]) -> str:
    contract_type = str(payload.get("contract_type") or "")

    mapping = {
        "GoalNodeContract": "goal",
        "ExperimentNodeContract": "experiment",
        "LoopNodeContract": "loop",
        "OutcomeEvaluationContract": "outcome_evaluation",
        "ReflectionLearningContract": "reflect_learn",
        "StateDeltaAccumulatorContract": "state_delta_accumulator",
        "EnvironmentRevalidationContract": "environment_revalidation",
        "LongRunningSessionContract": "long_running_session",
        "CheckpointContract": "checkpoint",
    }

    return mapping.get(contract_type, "unknown")


def build_goal_engine_dry_run_manifest(
    *,
    run_id: str,
    workflow_id: str,
    contracts: list[Any],
) -> dict[str, Any]:
    """
    Build a safe dry-run manifest for Goal Engine contracts.

    This function does not execute workflows, does not call providers, does not
    mutate memory, and does not perform external writes.
    """

    if not run_id:
        raise ValueError("run_id is required")

    if not workflow_id:
        raise ValueError("workflow_id is required")

    steps: list[dict[str, Any]] = []
    all_errors: list[str] = []

    for index, contract in enumerate(contracts or []):
        if not is_dataclass(contract):
            raise TypeError("all contracts must be dataclass contract instances")

        payload = serialize_contract(contract)
        errors = list(payload.get("validation_errors") or [])
        all_errors.extend(errors)

        step_type = _infer_manifest_step_type(payload)

        steps.append(
            {
                "index": index,
                "step_type": step_type,
                "contract_type": payload.get("contract_type"),
                "contract_id": _safe_contract_id(payload),
                "dry_run_only": True,
                "would_execute": False,
                "would_write_external": False,
                "would_grant_permission": False,
                "requires_approval_before_live_write": True,
                "validation_errors": errors,
                "contract": payload,
            }
        )

    return {
        "manifest_type": "aion_goal_engine_dry_run",
        "schema_version": "0.1.0",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_learning_memory": False,
        "would_grant_permission": False,
        "requires_approval_before_live_write": True,
        "valid": len(all_errors) == 0,
        "validation_errors": all_errors,
        "step_count": len(steps),
        "steps": steps,
        "safety_notes": [
            "Goal Engine dry-run manifests are advisory only.",
            "Goals do not grant permission.",
            "Experiments do not grant permission.",
            "Loops do not grant permission.",
            "Learning does not grant permission.",
            "External writes require explicit approval.",
        ],
    }
