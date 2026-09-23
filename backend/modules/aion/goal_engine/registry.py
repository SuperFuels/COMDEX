from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from backend.modules.aion.goal_engine.contracts import (
    EnvironmentRevalidationContract,
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
    ReflectionLearningContract,
    StateDeltaAccumulatorContract,
)


GOAL_ENGINE_NODE_TYPES: dict[str, dict[str, Any]] = {
    "goal": {
        "label": "Goal",
        "description": "Defines the business outcome the workflow is trying to achieve.",
        "contract": GoalNodeContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": True,
    },
    "experiment": {
        "label": "Experiment",
        "description": "Tests two or more variants against a goal metric.",
        "contract": ExperimentNodeContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": True,
    },
    "loop": {
        "label": "Loop",
        "description": "Repeats bounded work until count, goal, failure, or improvement limit.",
        "contract": LoopNodeContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": True,
    },
    "outcome_evaluation": {
        "label": "Outcome Evaluation",
        "description": "Scores whether the workflow achieved the intended business result.",
        "contract": OutcomeEvaluationContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": False,
    },
    "reflect_learn": {
        "label": "Reflect / Learn",
        "description": "Extracts advisory learning from completed runs without granting permission.",
        "contract": ReflectionLearningContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": False,
    },
    "state_delta_accumulator": {
        "label": "State Delta Accumulator",
        "description": "Stores bounded loop/session state deltas for long-running runs.",
        "contract": StateDeltaAccumulatorContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": True,
    },
    "environment_revalidation": {
        "label": "Environment Revalidation",
        "description": "Rechecks approvals, vaults, connectors, and parent goal state before resume.",
        "contract": EnvironmentRevalidationContract,
        "dry_run_only_default": True,
        "grants_permission": False,
        "requires_bounds": False,
    },
}


def list_goal_engine_node_types() -> list[str]:
    return list(GOAL_ENGINE_NODE_TYPES.keys())


def get_goal_engine_node_spec(node_type: str) -> dict[str, Any]:
    if node_type not in GOAL_ENGINE_NODE_TYPES:
        raise KeyError(f"Unknown goal engine node type: {node_type}")
    spec = GOAL_ENGINE_NODE_TYPES[node_type]
    return {key: value for key, value in spec.items() if key != "contract"}


def serialize_contract(contract: Any) -> dict[str, Any]:
    if not is_dataclass(contract):
        raise TypeError("serialize_contract expects a dataclass contract instance")

    payload = asdict(contract)
    payload["contract_type"] = contract.__class__.__name__
    payload["validation_errors"] = contract.validate()
    return payload


def registry_manifest() -> dict[str, Any]:
    return {
        "runtime": "aion_goal_engine",
        "version": "0.1.0",
        "node_types": {
            key: get_goal_engine_node_spec(key)
            for key in list_goal_engine_node_types()
        },
        "safety_contract": {
            "goals_grant_permission": False,
            "experiments_grant_permission": False,
            "loops_grant_permission": False,
            "learning_grants_permission": False,
            "external_writes_require_approval": True,
            "unbounded_loops_allowed": False,
            "resume_requires_environment_revalidation": True,
        },
    }
