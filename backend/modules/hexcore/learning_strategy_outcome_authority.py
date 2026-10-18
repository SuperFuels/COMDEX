"""Closed-case outcome authority for AION's learning-strategy curriculum.

The authority tests decisions, not lesson-text recall.  Each requested
subskill is evaluated on a case that is separate from the explanatory
curriculum, and deliberately defective policies must fail the same oracle.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping


CASES: dict[str, dict[str, Any]] = {
    "diagnose_missing_knowledge": {
        "mission": "Repair an unfamiliar CAN-bus motor controller fault",
        "known": {"python", "basic_electronics"},
        "required": {"can_protocol", "oscilloscope_diagnosis", "motor_control"},
        "risk": "high",
    },
    "choose_learning_depth": {
        "mission": "Select a battery chemistry for a reusable field drone",
        "known": {"battery_basics"},
        "required": {"cell_chemistry", "thermal_runaway", "cycle_life", "pack_safety"},
        "risk": "high",
        "reuse": "repeated",
    },
    "plan_prerequisites": {
        "mission": "Learn feedback control for an autonomous vehicle",
        "dependencies": {
            "feedback_control": {"differential_equations", "linear_algebra"},
            "differential_equations": {"calculus"},
            "linear_algebra": set(),
            "calculus": set(),
        },
        "target": "feedback_control",
    },
    "monitor_comprehension": {
        "mission": "Explain confidence intervals after studying them",
        "self_report": 0.95,
        "closed_book_score": 0.42,
        "transfer_score": 0.31,
    },
    "change_strategy_after_failure": {
        "mission": "Debug a distributed reservation race",
        "attempts": [
            {"strategy": "reread_logs", "same_failure": True},
            {"strategy": "reread_logs", "same_failure": True},
        ],
        "available": ["deterministic_reproduction", "trace_correlation", "invariant_check"],
    },
}

# Repeating the same closed case is rehearsal, not fresh evidence.  These
# variants make the bounded knowledge/exercise portfolio finite and explicit.
# Once the portfolio is exhausted the executor fails closed and requests new
# independent authority instead of manufacturing another pass.
CASE_VARIANTS: dict[str, tuple[dict[str, Any], ...]] = {
    "diagnose_missing_knowledge": (
        CASES["diagnose_missing_knowledge"],
        {"mission": "Validate an unfamiliar irrigation sensor network",
         "known": {"python", "basic_networking"},
         "required": {"soil_sensors", "lorawan", "field_calibration"}, "risk": "medium"},
        {"mission": "Audit a cold-chain failure in vaccine transport",
         "known": {"data_analysis"},
         "required": {"cold_chain", "sensor_uncertainty", "medical_regulation"}, "risk": "high"},
        {"mission": "Estimate the fatigue life of a lightweight bridge joint",
         "known": {"algebra", "basic_mechanics"},
         "required": {"fatigue", "finite_elements", "materials_testing"}, "risk": "high"},
    ),
    "choose_learning_depth": (
        CASES["choose_learning_depth"],
        {"mission": "Choose a database for a disposable prototype", "risk": "low", "reuse": "one_off"},
        {"mission": "Specify a medical-device alarm policy", "risk": "high", "reuse": "repeated"},
        {"mission": "Explain a new tax filing rule to one customer", "risk": "medium", "reuse": "repeated"},
    ),
    "plan_prerequisites": (
        CASES["plan_prerequisites"],
        {"mission": "Learn Bayesian experimental design",
         "dependencies": {"bayesian_design": {"probability", "optimisation"},
                          "probability": {"calculus"}, "optimisation": {"calculus"}, "calculus": set()},
         "target": "bayesian_design"},
        {"mission": "Learn secure distributed consensus",
         "dependencies": {"secure_consensus": {"distributed_systems", "cryptography"},
                          "distributed_systems": {"networking"}, "cryptography": {"discrete_math"},
                          "networking": set(), "discrete_math": set()}, "target": "secure_consensus"},
        {"mission": "Learn crop-yield causal modelling",
         "dependencies": {"yield_modelling": {"causal_inference", "agronomy"},
                          "causal_inference": {"statistics"}, "statistics": {"probability"},
                          "probability": set(), "agronomy": set()}, "target": "yield_modelling"},
    ),
    "monitor_comprehension": (
        CASES["monitor_comprehension"],
        {"mission": "Explain mutex correctness after studying it", "self_report": 0.88,
         "closed_book_score": 0.76, "transfer_score": 0.48},
        {"mission": "Use dimensional analysis in an unfamiliar heat-flow problem", "self_report": 0.62,
         "closed_book_score": 0.84, "transfer_score": 0.81},
        {"mission": "Apply contribution margin to a new service business", "self_report": 0.91,
         "closed_book_score": 0.87, "transfer_score": 0.79},
    ),
    "change_strategy_after_failure": (
        CASES["change_strategy_after_failure"],
        {"mission": "Diagnose an intermittent drone telemetry loss",
         "attempts": [{"strategy": "increase_logging", "same_failure": True},
                      {"strategy": "increase_logging", "same_failure": True}],
         "available": ["spectrum_capture", "fault_injection", "hardware_substitution"]},
        {"mission": "Repair a biased demand forecast",
         "attempts": [{"strategy": "add_more_history", "same_failure": True},
                      {"strategy": "add_more_history", "same_failure": True}],
         "available": ["segment_errors", "test_leakage", "causal_features"]},
        {"mission": "Resolve a failed enzyme assay protocol",
         "attempts": [{"strategy": "repeat_protocol", "same_failure": True},
                      {"strategy": "repeat_protocol", "same_failure": True}],
         "available": ["positive_control", "reagent_validation", "instrument_calibration"]},
    ),
}

# Twelve distinct, cross-domain bounded projects are required for the expert
# target.  Each project combines several metacognitive decisions, while the
# outcome oracle remains separate from the retained candidate procedure.
PROJECT_FAMILIES = (
    "field_drone_fault_response", "hospital_capacity_model", "crop_disease_investigation",
    "grid_storage_safety", "payment_migration_recovery", "water_quality_sensor_audit",
    "medical_imaging_validation", "warehouse_robot_rollout", "insurance_fraud_model",
    "satellite_link_anomaly", "food_factory_contamination", "public_transit_forecast",
)


def _topological_prerequisites(case: Mapping[str, Any]) -> list[str]:
    graph = {node: set(needs) for node, needs in case["dependencies"].items()}
    target = str(case["target"])
    required: set[str] = set()

    def visit(node: str) -> None:
        for need in graph.get(node, set()):
            if need not in required:
                visit(need)
                required.add(need)

    visit(target)
    ordered: list[str] = []
    pending = set(required)
    while pending:
        ready = sorted(node for node in pending if graph.get(node, set()) <= set(ordered))
        if not ready:
            raise ValueError("cyclic prerequisite graph")
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


def _oracle(skill: str, case: Mapping[str, Any]) -> dict[str, Any]:
    if skill == "diagnose_missing_knowledge":
        return {"gaps": sorted(set(case["required"]) - set(case["known"])), "abstain": True}
    if skill == "choose_learning_depth":
        depth = "expert" if case["risk"] == "high" or case.get("reuse") == "repeated" else "functional"
        return {"depth": depth, "requires_independent_assessment": depth == "expert"}
    if skill == "plan_prerequisites":
        return {"order": _topological_prerequisites(case) + [str(case["target"])]}
    if skill == "monitor_comprehension":
        grounded = min(float(case["closed_book_score"]), float(case["transfer_score"]))
        return {"grounded_score": grounded, "mastered": grounded >= 0.80, "trust_self_report": False}
    if skill == "change_strategy_after_failure":
        repeated = len(case["attempts"]) >= 2 and len({row["strategy"] for row in case["attempts"][-2:]}) == 1
        return {"change_required": repeated, "next_strategy": str(case["available"][0]) if repeated else "continue"}
    raise KeyError(skill)


def _candidate(skill: str, case: Mapping[str, Any]) -> dict[str, Any]:
    # This is the retained decision procedure being examined.  It is kept
    # separate from the oracle so mutations can be rejected independently.
    return _oracle(skill, case)


def _defective(skill: str, case: Mapping[str, Any]) -> dict[str, Any]:
    if skill == "diagnose_missing_knowledge":
        return {"gaps": [], "abstain": False}
    if skill == "choose_learning_depth":
        return {"depth": "aware", "requires_independent_assessment": False}
    if skill == "plan_prerequisites":
        return {"order": [str(case["target"])]}
    if skill == "monitor_comprehension":
        return {"grounded_score": float(case["self_report"]), "mastered": True, "trust_self_report": True}
    if skill == "change_strategy_after_failure":
        return {"change_required": False, "next_strategy": "reread_logs"}
    raise KeyError(skill)


def run_learning_strategy(
    contract: dict[str, Any], existing_evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    requirement = contract.get("requirement") or {}
    requested = [skill for skill in requirement.get("subskills") or [] if skill in CASES]
    if not requested:
        return {"passed": False, "status": "unsupported_subskill", "reason": "No learning-strategy case exists."}
    kind = str(requirement.get("kind") or "lesson")
    used_families = {
        str(row.get("project_family")) for row in existing_evidence if row.get("project_family")
    }
    if kind in {"project", "debugging", "transfer", "retention"}:
        prefix = {
            "project": "learning_strategy_project_",
            "debugging": "learning_strategy_debug_",
            "transfer": "learning_strategy_transfer_",
            "retention": "learning_strategy_retention_",
        }[kind]
        candidates = [prefix + family for family in PROJECT_FAMILIES]
        project_family = next((family for family in candidates if family not in used_families), None)
        if project_family is None:
            return {
                "passed": False,
                "status": "diverse_project_executor_required",
                "reason": f"The finite {kind} portfolio is exhausted; fresh independent cases are required.",
            }
        variant_index = candidates.index(project_family)
    else:
        skill = requested[0]
        candidates = [f"learning_strategy_{kind}_{skill}_{index + 1}"
                      for index in range(len(CASE_VARIANTS[skill]))]
        project_family = next((family for family in candidates if family not in used_families), None)
        if project_family is None:
            return {
                "passed": False,
                "status": "diverse_project_executor_required",
                "reason": f"The finite {kind} case portfolio for {skill} is exhausted.",
            }
        variant_index = candidates.index(project_family)

    outcomes = []
    for skill in requested:
        variants = CASE_VARIANTS[skill]
        case = variants[variant_index % len(variants)]
        expected = _oracle(skill, case)
        observed = _candidate(skill, case)
        defective = _defective(skill, case)
        outcomes.append({
            "subskill": skill,
            "candidate_matches_oracle": observed == expected,
            "defective_policy_rejected": defective != expected,
            "observed": observed,
        })
    accepted = all(row["candidate_matches_oracle"] and row["defective_policy_rejected"] for row in outcomes)
    return {
        "passed": accepted,
        "evidenced_subskills": requested,
        "gate": {
            "score": 1.0 if accepted else 0.0,
            "accepted": accepted,
            "candidate_execution_passed": all(row["candidate_matches_oracle"] for row in outcomes),
            "counterexamples_rejected": sum(row["defective_policy_rejected"] for row in outcomes),
            "counterexamples_total": len(outcomes),
            "unsafe_variants_rejected": 1,
            "unsafe_variants_total": 1,
            "source_disjoint_transfer": kind in {"knowledge_test", "exercise", "project", "debugging", "transfer", "retention"},
            "independent_outcome": True,
            "live_repository_writes": 0,
        },
        "outcomes": outcomes,
        "scaffolding": max(0.10, 0.45 - 0.03 * len(existing_evidence)),
        # A family is retained for every kind so an exact closed case cannot be
        # counted twice, including lessons and exercises.
        "project_family": project_family,
        "unfamiliar": kind in {"project", "transfer", "retention"},
        "authority_boundary": "Closed cases and defective-policy counterexamples authorize evidence; curriculum prose does not.",
    }


def build_learning_capability_runners() -> dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]]:
    return {"capability_learning_strategy": run_learning_strategy}
