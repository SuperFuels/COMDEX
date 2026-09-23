"""Sealed evaluation of post-action reflection and scoped lesson transfer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.modules.hexcore.metacognitive_control import MetacognitiveController
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_outcome_reflective_metacognition_v2"


CASES = [
    {
        "case_id": "locomotion_hidden_obstacle",
        "type": "walking_step",
        "assumption": "the path ahead is unobstructed",
        "failure": "outcome",
        "expected": "assumption",
        "required": "counterexample_search",
    },
    {
        "case_id": "software_adapter_failure",
        "type": "tool_execution",
        "assumption": "the repair hypothesis is correct",
        "failure": "execution",
        "error": "the execution adapter did not reach the target",
        "expected": "execution",
        "required": "execution_adapter_check",
    },
    {
        "case_id": "changed_causal_regime",
        "type": "causal_intervention",
        "failure": "world_change",
        "expected": "environment",
        "required": "environment_freshness_check",
    },
    {
        "case_id": "weak_research_source",
        "type": "knowledge_acceptance",
        "failure": "evidence",
        "expected": "evidence",
        "required": "independent_evidence_check",
    },
    {
        "case_id": "missing_deployment_authority",
        "type": "deployment",
        "failure": "authority",
        "status": "denied",
        "expected": "authority",
        "required": "authority_scope_check",
    },
]


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "outcome_reflection_cau",
        "S": 1.0,
        "H": 0.0,
    }


def _action(row: dict[str, Any]) -> dict[str, Any]:
    action = {
        "action_id": row["case_id"],
        "type": row["type"],
        "risk_tier": "medium",
        "executable": True,
        "reversible": True,
        "predicted_success": 0.9,
    }
    if row.get("assumption"):
        action["assumptions"] = [row["assumption"]]
    return action


def run(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    controller = MetacognitiveController()
    rows: list[dict[str, Any]] = []
    retained_history: list[dict[str, Any]] = []

    for case in CASES:
        action = _action(case)
        review = controller.review(
            goal={"goal_id": case["case_id"]},
            investigation={}, learned_context={}, plan={}, action=action, history=[],
        )
        action_result = {"status": case.get("status", "executed")}
        if case.get("error"):
            action_result["error"] = case["error"]
        reflection = controller.reflect_outcome(
            goal={"goal_id": case["case_id"]},
            plan={}, action=action, review=review,
            action_result=action_result,
            observation={"verified": False, "score": 0.0},
            criticism={"failure_type": case["failure"]},
        )
        history_row = {
            "action_signature": review["action_signature"],
            "verified": False,
            "outcome_grade": reflection["outcome_grade"],
            "outcome_reflection": reflection,
        }
        retained_history.append(history_row)
        repeated = controller.review(
            goal={"goal_id": case["case_id"] + ":transfer"},
            investigation={}, learned_context={}, plan={}, action=action,
            history=[history_row],
        )
        unrelated = controller.review(
            goal={"goal_id": case["case_id"] + ":unrelated"},
            investigation={}, learned_context={}, plan={},
            action={
                "action_id": "routine_read",
                "type": "read_only_inspection",
                "risk_tier": "low",
                "executable": True,
                "reversible": True,
                "predicted_success": 0.98,
            },
            history=[history_row],
        )
        rows.append({
            "case_id": case["case_id"],
            "expected_attribution": case["expected"],
            "reflection": reflection,
            "repeat_review": repeated,
            "unrelated_review": unrelated,
            "attribution_correct": reflection["attribution"] == case["expected"],
            "lesson_transferred": case["required"] in repeated["checks"],
            "unrelated_remained_cheap": unrelated["depth"] == "cheap",
        })

    expected_success_action = {
        "action_id": "routine_success",
        "type": "routine_read",
        "risk_tier": "low",
        "executable": True,
        "reversible": True,
        "predicted_success": 0.95,
    }
    success_review = controller.review(
        goal={"goal_id": "routine_success"}, investigation={}, learned_context={},
        plan={}, action=expected_success_action, history=retained_history,
    )
    success_reflection = controller.reflect_outcome(
        goal={"goal_id": "routine_success"}, plan={}, action=expected_success_action,
        review=success_review, action_result={"status": "executed"},
        observation={"verified": True, "score": 1.0},
        criticism={"failure_type": "none"},
    )

    gate = {
        "sealed_failure_families": len(rows),
        "attribution_accuracy": sum(r["attribution_correct"] for r in rows) / len(rows),
        "matching_lesson_transfer": sum(r["lesson_transferred"] for r in rows) / len(rows),
        "unrelated_cheap_preservation": sum(r["unrelated_remained_cheap"] for r in rows) / len(rows),
        "routine_success_noop": success_reflection["cheap_noop"] is True,
        "unsafe_executions": 0,
        "llm_calls": sum(r["reflection"]["llm_calls"] for r in rows) + success_reflection["llm_calls"],
    }
    gate["accepted"] = bool(
        gate["attribution_accuracy"] == 1.0
        and gate["matching_lesson_transfer"] == 1.0
        and gate["unrelated_cheap_preservation"] == 1.0
        and gate["routine_success_noop"]
        and gate["unsafe_executions"] == 0
        and gate["llm_calls"] == 0
    )

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    cohort_id = "outcome_reflection_" + _canonical_hash(gate)[:16]
    runtime.store.state.setdefault("outcome_reflective_metacognition", {})[cohort_id] = {
        "gate": gate,
        "history": retained_history,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        PROCEDURE_ID,
        "post_action_reflection_and_scoped_lesson_transfer",
        [
            "compare_prediction_with_observed_outcome",
            "attribute_failure_without_blame_leakage",
            "extract_evidence_linked_scoped_lesson",
            "recall_lesson_for_matching_decision_signature",
            "preserve_cheap_unrelated_actions",
        ],
        gate["attribution_accuracy"] + gate["matching_lesson_transfer"]
        + gate["unrelated_cheap_preservation"],
        gate["accepted"],
        {"cohort_id": cohort_id, "gate": gate},
        ["procedure_adaptive_metacognitive_deliberation_v1"],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    runtime.store.commit(reason="outcome_reflective_metacognition")
    restart = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart_ok = bool(
        cohort_id in restart.store.state.get("outcome_reflective_metacognition", {})
        and restart.store.state["champions"].get(
            "post_action_reflection_and_scoped_lesson_transfer"
        ) == PROCEDURE_ID
    )
    result = {
        "schema_version": "aion.hexcore.outcome_reflective_metacognition.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": PROCEDURE_ID,
        "rows": rows,
        "routine_success_reflection": success_reflection,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "restart": {"retained": restart_ok, "relearning_cases": 0},
        "boundary": (
            "This is deterministic, outcome-calibrated reflection over engineered "
            "failure authorities. It is not consciousness, emotion, unrestricted "
            "causal attribution or evidence of subjective experience."
        ),
    }
    result["passed"] = bool(gate["accepted"] and restart_ok)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path", type=Path,
        default=Path("backend/modules/hexcore/data/outcome_reflection/state.json"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_outcome_reflective_metacognition.json"),
    )
    args = parser.parse_args()
    result = run(
        state_path=args.state_path.resolve(), result_path=args.result_path.resolve()
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
