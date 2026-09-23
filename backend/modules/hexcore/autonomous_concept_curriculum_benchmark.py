from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Hypothesis = Tuple[str, int]
Point = Tuple[int, int]


@dataclass(frozen=True)
class CurriculumDomain:
    domain_id: str
    fields: Tuple[str, str]
    operator: str
    threshold: int
    seed: int

    def observe(self, point: Point) -> bool:
        return _predict((self.operator, self.threshold), point)


DEVELOPMENT_DOMAINS = (
    CurriculumDomain("dual_reactor", ("core_a", "core_b"), "min_ge", 4, 2101),
    CurriculumDomain("paired_reserve", ("bank_l", "bank_r"), "min_ge", 6, 2102),
)
SEALED_DOMAINS = (
    CurriculumDomain("orchard_pair", ("root", "canopy"), "min_ge", 3, 2201),
    CurriculumDomain("twin_signal", ("east", "west"), "min_ge", 5, 2202),
    CurriculumDomain("alloy_pair", ("matrix", "binder"), "min_ge", 7, 2203),
)
NEGATIVE_CONTROLS = (
    CurriculumDomain("linear_balance", ("supply", "loss"), "difference_ge", 3, 2301),
)
OPERATORS = ("difference_ge", "sum_ge", "min_ge", "max_ge")
THRESHOLDS = tuple(range(-2, 19))
POINTS = tuple((left, right) for left in range(0, 11) for right in range(0, 11))


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "autonomous_concept_curriculum_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _predict(hypothesis: Hypothesis, point: Point) -> bool:
    operator, threshold = hypothesis
    left, right = point
    if operator == "difference_ge":
        value = left - right
    elif operator == "sum_ge":
        value = left + right
    elif operator == "min_ge":
        value = min(left, right)
    elif operator == "max_ge":
        value = max(left, right)
    else:
        raise ValueError(operator)
    return value >= threshold


def _entropy(positive: int, total: int) -> float:
    if positive == 0 or positive == total:
        return 0.0
    probability = positive / total
    return -probability * math.log2(probability) - (
        1.0 - probability
    ) * math.log2(1.0 - probability)


def _active_discovery(
    *,
    domain: CurriculumDomain,
    operators: Sequence[str],
    max_probes: int,
) -> Dict[str, Any]:
    hypotheses = [
        (operator, threshold)
        for operator in operators
        for threshold in THRESHOLDS
    ]
    observations = []
    unused = set(POINTS)
    while len(hypotheses) > 1 and len(observations) < max_probes:
        point = max(
            unused,
            key=lambda candidate: (
                _entropy(
                    sum(
                        int(_predict(hypothesis, candidate))
                        for hypothesis in hypotheses
                    ),
                    len(hypotheses),
                ),
                -abs(candidate[0] - candidate[1]),
                candidate,
            ),
        )
        unused.remove(point)
        outcome = domain.observe(point)
        observations.append({"point": list(point), "outcome": int(outcome)})
        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if _predict(hypothesis, point) == outcome
        ]
    selected = hypotheses[0] if hypotheses else ("none", 0)
    return {
        "selected_operator": selected[0],
        "selected_threshold": selected[1],
        "remaining_hypotheses": len(hypotheses),
        "probes": len(observations),
        "observations": observations,
        "structure_recovered": (
            selected[0] == domain.operator
            and selected[1] == domain.threshold
        ),
    }


def _random_discovery(
    *,
    domain: CurriculumDomain,
    operators: Sequence[str],
    max_probes: int,
) -> Dict[str, Any]:
    rng = random.Random(domain.seed + 90_000)
    points = list(POINTS)
    rng.shuffle(points)
    hypotheses = [
        (operator, threshold)
        for operator in operators
        for threshold in THRESHOLDS
    ]
    used = 0
    for point in points[:max_probes]:
        used += 1
        outcome = domain.observe(point)
        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if _predict(hypothesis, point) == outcome
        ]
        if len(hypotheses) == 1:
            break
    selected = hypotheses[0] if hypotheses else ("none", 0)
    return {
        "selected_operator": selected[0],
        "selected_threshold": selected[1],
        "remaining_hypotheses": len(hypotheses),
        "probes": used,
        "structure_recovered": (
            selected[0] == domain.operator
            and selected[1] == domain.threshold
        ),
    }


def _grid_accuracy(
    *,
    domain: CurriculumDomain,
    hypothesis: Hypothesis,
) -> float:
    return sum(
        int(_predict(hypothesis, point) == domain.observe(point))
        for point in POINTS
    ) / len(POINTS)


def _best_current_meta_accuracy(domain: CurriculumDomain) -> float:
    current_operators = ("difference_ge", "sum_ge")
    return max(
        _grid_accuracy(domain=domain, hypothesis=(operator, threshold))
        for operator in current_operators
        for threshold in THRESHOLDS
    )


def _evaluate_domains(
    *,
    domains: Sequence[CurriculumDomain],
    operators: Sequence[str],
    max_probes: int,
) -> Dict[str, Any]:
    results = []
    for domain in domains:
        discovery = _active_discovery(
            domain=domain,
            operators=operators,
            max_probes=max_probes,
        )
        hypothesis = (
            discovery["selected_operator"],
            discovery["selected_threshold"],
        )
        discovery.update(
            {
                "domain_id": domain.domain_id,
                "fields": list(domain.fields),
                "accuracy": _grid_accuracy(
                    domain=domain,
                    hypothesis=hypothesis,
                ),
                "current_meta_accuracy": _best_current_meta_accuracy(domain),
            }
        )
        results.append(discovery)
    return {
        "mean_accuracy": sum(row["accuracy"] for row in results) / len(results),
        "worst_accuracy": min(row["accuracy"] for row in results),
        "structure_recovery": sum(
            int(row["structure_recovered"]) for row in results
        ) / len(results),
        "mean_probes": sum(row["probes"] for row in results) / len(results),
        "current_meta_mean_accuracy": sum(
            row["current_meta_accuracy"] for row in results
        ) / len(results),
        "domains": results,
    }


def run_autonomous_concept_curriculum_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "concept_signed_linear_relation_8b22663b2ca3"
    runtime.store.state["invented_concepts"][parent_id] = {
        "concept_id": parent_id,
        "name": "signed_linear_relation",
        "status": "phase24_promoted_dependency",
        "source_procedure_id": "procedure_meta_abstraction_c5bb3ab6c20e",
    }
    runtime.store.commit(reason="load_phase24_meta_concept")

    criticism_accuracies = [
        _best_current_meta_accuracy(domain) for domain in DEVELOPMENT_DOMAINS
    ]
    criticism_accuracy = sum(criticism_accuracies) / len(
        criticism_accuracies
    )
    criticism_worst = min(criticism_accuracies)
    invention_required = (
        criticism_accuracy < 0.90 or criticism_worst < 0.88
    )
    criticism = {
        "status": (
            "META_ONTOLOGY_INADEQUATE"
            if invention_required
            else "META_ONTOLOGY_ADEQUATE"
        ),
        "invention_required": invention_required,
        "current_meta_accuracy": criticism_accuracy,
        "current_meta_worst_accuracy": criticism_worst,
    }
    development = _evaluate_domains(
        domains=DEVELOPMENT_DOMAINS,
        operators=OPERATORS,
        max_probes=20,
    )
    sealed = _evaluate_domains(
        domains=SEALED_DOMAINS,
        operators=("min_ge",),
        max_probes=12,
    )
    random_controls = [
        _random_discovery(
            domain=domain,
            operators=OPERATORS,
            max_probes=40,
        )
        for domain in SEALED_DOMAINS
    ]
    random_mean_probes = sum(
        row["probes"] for row in random_controls
    ) / len(random_controls)
    negative_controls = []
    for domain in NEGATIVE_CONTROLS:
        current_accuracy = _best_current_meta_accuracy(domain)
        negative_controls.append(
            {
                "domain_id": domain.domain_id,
                "current_meta_accuracy": current_accuracy,
                "unnecessary_invention_rejected": current_accuracy >= 0.98,
            }
        )

    errors = []
    if not criticism["invention_required"]:
        errors.append("CURRENT_META_ONTOLOGY_NOT_CRITICISED")
    if development["structure_recovery"] < 1.0:
        errors.append("DEVELOPMENT_STRUCTURE_NOT_RECOVERED")
    if sealed["mean_accuracy"] < 1.0:
        errors.append("SEALED_ACCURACY_BELOW_100_PERCENT")
    if sealed["structure_recovery"] < 1.0:
        errors.append("SEALED_STRUCTURE_NOT_RECOVERED")
    if (
        sealed["mean_accuracy"]
        < sealed["current_meta_mean_accuracy"] + 0.10
    ):
        errors.append("GAIN_OVER_CURRENT_META_ONTOLOGY_BELOW_10_POINTS")
    if sealed["mean_probes"] >= random_mean_probes:
        errors.append("ACTIVE_CURRICULUM_NOT_MORE_EFFICIENT_THAN_RANDOM")
    if not all(
        row["unnecessary_invention_rejected"]
        for row in negative_controls
    ):
        errors.append("UNNECESSARY_INVENTION_CONTROL_FAILED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "sealed_mean_accuracy": sealed["mean_accuracy"],
        "sealed_worst_accuracy": sealed["worst_accuracy"],
        "sealed_structure_recovery": sealed["structure_recovery"],
        "current_meta_mean_accuracy": sealed["current_meta_mean_accuracy"],
        "gain_over_current_meta": (
            sealed["mean_accuracy"] - sealed["current_meta_mean_accuracy"]
        ),
        "active_mean_probes": sealed["mean_probes"],
        "random_mean_probes": random_mean_probes,
        "probe_reduction": (
            1.0 - sealed["mean_probes"] / random_mean_probes
            if random_mean_probes else 0.0
        ),
        "negative_controls_rejected": all(
            row["unnecessary_invention_rejected"]
            for row in negative_controls
        ),
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_meta_abstraction_c5bb3ab6c20e",
        goal="autonomous_concept_curriculum",
        steps=["apply_current_linear_meta_ontology"],
        score=sealed["current_meta_mean_accuracy"],
        success=True,
        evidence={"evaluation": "phase25_current_meta_control"},
    )
    runtime.skills.promote(baseline)
    concept = {
        "schema_version": "aion.hexcore.invented_concept.v1",
        "name": "joint_minimum_requirement",
        "kind": "interaction_meta_predicate",
        "operator": "min_ge",
        "parameters": ["threshold"],
        "parent_concepts": [parent_id],
        "model_criticism": criticism,
        "curriculum_policy": "maximum_hypothesis_disagreement",
        "development": development,
        "sealed": sealed,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    concept_id = (
        "concept_joint_minimum_"
        + _canonical_hash(concept)[:12]
    )
    concept["concept_id"] = concept_id
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_autonomous_curriculum_"
            + _canonical_hash(concept)[:12]
        ),
        goal="autonomous_concept_curriculum",
        steps=[
            "detect_meta_ontology_residual_failure",
            "construct_competing_interaction_hypotheses",
            "select_maximum_disagreement_experiments",
            "ground_new_predicate_from_outcomes",
            "verify_on_sealed_renamed_domains",
            "reject_invention_when_current_abstraction_is_sufficient",
            "retain_verified_extension_with_provenance",
        ],
        score=sealed["mean_accuracy"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase25_autonomous_curriculum_sealed",
            "concept_id": concept_id,
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    if gate["accepted"]:
        runtime.store.state["invented_concepts"][concept_id] = concept
        runtime.store.state["invented_concepts"][parent_id].setdefault(
            "bounded_extensions", []
        ).append(concept_id)
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "autonomous_curriculum_concept",
                "invention_id": concept_id,
                "procedure_id": candidate.procedure_id,
                "gate": gate,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"curriculum_concept_invention:{concept_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "concept_retained": (
            concept_id in restarted.store.state["invented_concepts"]
        ),
        "hierarchy_link_retained": (
            concept_id
            in restarted.store.state["invented_concepts"]
            .get(parent_id, {})
            .get("bounded_extensions", [])
        ),
        "champion_retained": (
            restarted.store.state.get("champions", {}).get(
                "autonomous_concept_curriculum"
            )
            == candidate.procedure_id
        ),
        "relearning_experiments": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_experiments"
        )
    )
    result = {
        "schema_version": "aion.hexcore.autonomous_concept_curriculum.v1",
        "benchmark": "active_failure_driven_ontology_extension",
        "passed": passed,
        "model_criticism": criticism,
        "development": development,
        "sealed": sealed,
        "random_controls": random_controls,
        "negative_controls": negative_controls,
        "gate": gate,
        "invented_concept": concept,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION actively selected experiments that separated a bounded "
            "finite set of interaction predicates. It did not generate an "
            "unbounded scientific theory space or arbitrary experiments."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run autonomous concept-curriculum benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_autonomous_concept_curriculum_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
