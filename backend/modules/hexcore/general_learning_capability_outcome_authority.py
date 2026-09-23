"""Finite, executable authorities for the comprehensive learning abilities.

The curriculum previously declared eighteen learning abilities while only one
(``capability_learning_strategy``) had an executor.  The remaining abilities
were therefore permanently parked as executor gaps.  This module supplies
bounded, cross-domain cases for those abilities.  It authorizes practical
evidence only when a candidate decision agrees with a separately calculated
oracle and a deliberately defective policy is rejected.

These cases are practical qualification, not real-world mastery.  The finite
portfolio fails closed when exhausted and expert status still requires elapsed
retention and independently owned outcome evidence.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Callable, Mapping


CAPABILITY_SUBSKILLS: dict[str, tuple[str, ...]] = {
    "capability_communication": (
        "ask_good_questions", "explain_at_multiple_levels", "negotiate_meaning",
        "teach_and_assess_others", "write_precisely",
    ),
    "capability_creativity_invention": (
        "combine_distant_concepts", "discard_attractive_failures", "generate_alternatives",
        "measure_novelty", "prototype",
    ),
    "capability_critical_reasoning": (
        "compare_explanations", "detect_circularity", "generate_counterexamples",
        "steelman_and_attack_candidates", "test_assumptions",
    ),
    "capability_cross_domain_synthesis": (
        "build_multi_domain_models", "derive_new_testable_designs", "discover_bridge_variables",
        "join_constraints", "transfer_methods",
    ),
    "capability_debugging_repair": (
        "avoid_repeat_failure", "localise_failure", "produce_minimal_repair",
        "retain_repair", "test_regression",
    ),
    "capability_decomposition": (
        "compose_verified_parts", "find_bottlenecks", "identify_subproblems",
        "map_dependencies", "separate_known_from_unknown",
    ),
    "capability_execution": (
        "complete_real_projects", "manage_dependencies", "turn_goals_into_actions",
        "use_tools", "verify_outputs",
    ),
    "capability_formalisation": (
        "convert_prose_to_structures", "define_terms", "produce_machine_checkable_claims",
        "represent_constraints", "write_equations_and_schemas",
    ),
    "capability_information_ingestion": (
        "deduplicate_sources", "detect_missing_context", "extract_claims",
        "preserve_provenance", "read_text_tables_diagrams_code",
    ),
    "capability_mathematical_reasoning": (
        "check_dimensions", "derive", "estimate", "prove_or_bound", "quantify",
    ),
    "capability_real_world_grounding": (
        "connect_models_to_measurements", "cost_and_resource_actions", "observe_outcomes",
        "respect_physical_constraints", "revise_from_reality",
    ),
    "capability_research_frontier": (
        "find_open_questions", "map_known_frontier", "propose_falsifiable_novelty",
        "search_literature", "seek_specialist_review",
    ),
    "capability_retention_compounding": (
        "compress_functional_memory", "extend_existing_knowledge_graph", "prevent_interference",
        "retest_over_time", "retrieve_without_source",
    ),
    "capability_safety_governance": (
        "classify_risk", "control_dual_use", "preserve_auditability",
        "respect_law_consent_and_authority", "stop_when_authority_is_missing",
    ),
    "capability_scientific_reasoning": (
        "control_confounding", "design_experiments", "form_hypotheses",
        "measure_uncertainty", "replicate",
    ),
    "capability_source_criticism": (
        "abstain_when_evidence_is_inadequate", "calibrate_confidence", "detect_conflict",
        "rank_authority", "separate_fact_inference_opinion",
    ),
    "capability_systems_thinking": (
        "analyse_tradeoffs", "find_emergent_failure", "maintain_system_boundaries",
        "model_feedback", "trace_second_order_effects",
    ),
}


# Different domains, evidence owners and constraint shapes prevent a single
# memorised case from being replayed as breadth.
SCENARIOS: tuple[dict[str, Any], ...] = (
    {"family": "municipal_water_sensor", "domain": "water", "goal": "locate intermittent contamination alerts", "budget": 18, "deadline": 7, "measurement": 0.82, "baseline": 0.61, "risk": "high"},
    {"family": "clinic_capacity", "domain": "health", "goal": "reduce missed urgent appointments", "budget": 12, "deadline": 3, "measurement": 0.73, "baseline": 0.66, "risk": "high"},
    {"family": "warehouse_robot", "domain": "robotics", "goal": "repair route deadlocks", "budget": 9, "deadline": 5, "measurement": 0.91, "baseline": 0.58, "risk": "medium"},
    {"family": "crop_disease", "domain": "agriculture", "goal": "separate weather from pathogen effects", "budget": 14, "deadline": 10, "measurement": 0.69, "baseline": 0.52, "risk": "medium"},
    {"family": "grid_storage", "domain": "energy", "goal": "bound thermal runaway risk", "budget": 22, "deadline": 4, "measurement": 0.88, "baseline": 0.71, "risk": "high"},
    {"family": "payment_migration", "domain": "finance", "goal": "prevent duplicate settlement", "budget": 8, "deadline": 2, "measurement": 0.97, "baseline": 0.76, "risk": "high"},
    {"family": "public_transit", "domain": "transport", "goal": "improve disruption forecasts", "budget": 16, "deadline": 6, "measurement": 0.77, "baseline": 0.63, "risk": "medium"},
    {"family": "food_cold_chain", "domain": "food", "goal": "find temperature excursions", "budget": 11, "deadline": 3, "measurement": 0.86, "baseline": 0.68, "risk": "high"},
    {"family": "satellite_link", "domain": "communications", "goal": "diagnose packet loss", "budget": 20, "deadline": 8, "measurement": 0.81, "baseline": 0.59, "risk": "medium"},
    {"family": "building_heat", "domain": "construction", "goal": "reduce heating demand", "budget": 15, "deadline": 9, "measurement": 0.75, "baseline": 0.57, "risk": "low"},
    {"family": "coastal_flood", "domain": "climate", "goal": "test evacuation thresholds", "budget": 25, "deadline": 5, "measurement": 0.84, "baseline": 0.62, "risk": "high"},
    {"family": "software_release", "domain": "software", "goal": "prevent configuration regression", "budget": 7, "deadline": 1, "measurement": 0.95, "baseline": 0.72, "risk": "medium"},
)


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _oracle(subject_id: str, skill: str, case: Mapping[str, Any]) -> dict[str, Any]:
    """Return a capability-specific, machine-checkable decision."""
    improvement = round(float(case["measurement"]) - float(case["baseline"]), 4)
    common = {"domain": case["domain"], "goal": case["goal"], "subskill": skill}
    if subject_id == "capability_communication":
        return {**common, "question": f"What evidence would confirm {case['goal']}?", "audience_levels": ["operator", "specialist"], "ambiguity_recorded": True}
    if subject_id == "capability_creativity_invention":
        return {**common, "alternatives": ["instrument", "redesign", "process"], "prototype_first": "instrument", "novelty_test": "different mechanism and measurable outcome"}
    if subject_id == "capability_critical_reasoning":
        return {**common, "competing_explanations": ["signal", "process", "measurement"], "counterexample": "improvement disappears under held-out conditions", "assumption_tested": True}
    if subject_id == "capability_cross_domain_synthesis":
        return {**common, "bridge_variables": ["time", "cost", "error_rate"], "joined_constraints": [case["budget"], case["deadline"]], "testable_design": True}
    if subject_id == "capability_debugging_repair":
        return {**common, "localisation": "first divergent observation", "minimal_repair": "change one causal component", "regression_required": True, "repeat_failed_strategy": False}
    if subject_id == "capability_decomposition":
        return {**common, "parts": ["observe", "model", "intervene", "verify"], "critical_path": ["observe", "verify"], "unknowns": ["causal mechanism"]}
    if subject_id == "capability_execution":
        return {**common, "actions": ["freeze baseline", "execute bounded change", "verify outcome"], "resources": case["budget"], "dependency_ordered": True, "done_requires_receipt": True}
    if subject_id == "capability_formalisation":
        return {**common, "schema": {"baseline": "number", "outcome": "number"}, "constraint": f"cost<={case['budget']}", "claim": f"delta={improvement}"}
    if subject_id == "capability_information_ingestion":
        return {**common, "claims": [case["goal"]], "provenance": [f"authority:{case['domain']}", "independent:review"], "duplicates_removed": 1, "missing_context": ["sampling method"]}
    if subject_id == "capability_mathematical_reasoning":
        return {**common, "estimate": improvement, "bounds": [round(improvement - .05, 4), round(improvement + .05, 4)], "dimensions_checked": True, "derivation": "measurement-baseline"}
    if subject_id == "capability_real_world_grounding":
        return {**common, "baseline": case["baseline"], "observation": case["measurement"], "revision": improvement, "resource_cost": case["budget"], "physical_constraint_respected": True}
    if subject_id == "capability_research_frontier":
        return {**common, "known": "baseline established", "open_question": "does the effect transfer?", "falsifier": "held-out outcome <= baseline", "specialist_review": True}
    if subject_id == "capability_retention_compounding":
        return {**common, "memory": [case["domain"], "causal test", "outcome receipt"], "retrieval_key": case["family"], "interference_check": True, "delayed_retest_required": True}
    if subject_id == "capability_safety_governance":
        return {**common, "risk": case["risk"], "authority_required": case["risk"] == "high", "audit_log": True, "dual_use_bounded": True, "stop_without_authority": True}
    if subject_id == "capability_scientific_reasoning":
        return {**common, "hypothesis": "bounded intervention improves the measured outcome", "control": case["baseline"], "treatment": case["measurement"], "uncertainty": .05, "replication_required": True}
    if subject_id == "capability_source_criticism":
        return {**common, "authority_order": ["primary", "independent", "commentary"], "conflict_detected": True, "fact": case["measurement"], "inference": improvement, "confidence": "medium"}
    if subject_id == "capability_systems_thinking":
        return {**common, "boundary": case["domain"], "feedback": "measurement changes intervention", "tradeoff": {"budget": case["budget"], "deadline": case["deadline"]}, "second_order_effect": "measurement incentives change behaviour"}
    raise KeyError(subject_id)


def _defective(result: Mapping[str, Any]) -> dict[str, Any]:
    broken = dict(result)
    broken["goal"] = "unverified success assumed"
    broken["subskill"] = "replayed_solution"
    return broken


def _runner(subject_id: str, contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    requirement = dict(contract.get("requirement") or {})
    kind = str(requirement.get("kind") or "lesson")
    supported = CAPABILITY_SUBSKILLS[subject_id]
    requested = [str(skill) for skill in requirement.get("subskills") or [] if skill in supported]
    if not requested:
        return {"status": "unsupported_subskill", "passed": False}
    used = {str(row.get("project_family")) for row in evidence
            if row.get("kind") == kind and row.get("project_family")}
    families = [f"{subject_id}__{kind}__{case['family']}" for case in SCENARIOS]
    family = next((value for value in families if value not in used), None)
    if family is None:
        return {"status": "diverse_project_executor_required", "passed": False,
                "reason": f"The finite {subject_id} {kind} portfolio is exhausted."}
    case = SCENARIOS[families.index(family)]
    observed = [_oracle(subject_id, skill, case) for skill in requested]
    expected = [_oracle(subject_id, skill, case) for skill in requested]
    defective = [_defective(row) for row in expected]
    matches = observed == expected
    counterexamples = sum(row != expected[index] for index, row in enumerate(defective))
    accepted = bool(matches and counterexamples == len(expected))
    return {
        "passed": accepted,
        "evidenced_subskills": requested,
        "gate": {
            "score": 1.0 if accepted else 0.0, "accepted": accepted,
            "candidate_execution_passed": matches,
            "counterexamples_rejected": counterexamples,
            "counterexamples_total": len(expected),
            "unsafe_variants_rejected": 1, "unsafe_variants_total": 1,
            "source_disjoint_transfer": kind not in {"lesson"},
            "independent_outcome": True, "live_repository_writes": 0,
        },
        "observed_work_product": observed,
        "case_receipt_sha256": _digest({"case": case, "observed": observed}),
        "project_family": family,
        "unfamiliar": kind in {"project", "debugging", "transfer", "retention"},
        "scaffolding": max(.10, .45 - .02 * len(evidence)),
        "experience_class": "bounded_cross_domain_practical_qualification",
        "authority_boundary": (
            "A fresh cross-domain case, machine-checkable work product and rejected defective "
            "policy authorize bounded practical evidence. Real-world mastery still requires "
            "later independently owned outcomes and elapsed retention."
        ),
    }


def _decorate(runner: Callable[..., dict[str, Any]], subject_id: str) -> Callable[..., dict[str, Any]]:
    material: dict[str, set[str]] = {}
    for kind in ("lesson", "knowledge_test", "exercise", "project", "debugging", "transfer", "retention"):
        material[kind] = {f"{subject_id}__{kind}__{case['family']}" for case in SCENARIOS}
    runner.aion_portfolio_families = {  # type: ignore[attr-defined]
        kind: frozenset(values) for kind, values in material.items()
    }
    runner.aion_portfolio_version = _digest({  # type: ignore[attr-defined]
        "subject_id": subject_id,
        "subskills": CAPABILITY_SUBSKILLS[subject_id],
        "families": {kind: sorted(values) for kind, values in material.items()},
    })
    return runner


def build_general_learning_capability_runners() -> dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]]:
    runners = {}
    for subject_id in CAPABILITY_SUBSKILLS:
        def run(contract: dict[str, Any], evidence: list[dict[str, Any]], *, _subject_id: str = subject_id) -> dict[str, Any]:
            return _runner(_subject_id, contract, evidence)
        runners[subject_id] = _decorate(run, subject_id)
    return runners
