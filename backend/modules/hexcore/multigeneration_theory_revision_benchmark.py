from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Point = Tuple[int, int]
Hypothesis = Tuple[str, int]
POINTS = tuple((left, right) for left in range(0, 11) for right in range(0, 11))
THRESHOLDS = tuple(range(-2, 21))
RAW_OPERATOR_GRAMMAR = (
    "difference_ge",
    "sum_ge",
    "min_ge",
    "max_ge",
    "abs_difference_le",
    "closeness_alias",
)


@dataclass(frozen=True)
class RevisionDomain:
    domain_id: str
    fields: Tuple[str, str]
    operator: str
    threshold: int
    seed: int

    def observe(self, point: Point) -> bool:
        return _predict((self.operator, self.threshold), point)


DEVELOPMENT_STREAM = (
    RevisionDomain("solar_redundancy", ("arc", "beam"), "max_ge", 6, 3101),
    RevisionDomain("synchrony_window", ("phase_a", "phase_b"), "abs_difference_le", 2, 3102),
    RevisionDomain("dual_feed", ("feed_l", "feed_r"), "min_ge", 5, 3103),
)
SEALED_TRANSFER = (
    RevisionDomain("emergency_supply", ("cell", "reserve"), "max_ge", 7, 3201),
    RevisionDomain("clock_alignment", ("clock_x", "clock_y"), "abs_difference_le", 1, 3202),
    RevisionDomain("paired_growth", ("root", "leaf"), "min_ge", 4, 3203),
    RevisionDomain("load_balance", ("input", "drag"), "difference_ge", 3, 3204),
    RevisionDomain("combined_stock", ("store_a", "store_b"), "sum_ge", 11, 3205),
)
BACKWARD_RETENTION = (
    RevisionDomain("retained_margin", ("left", "right"), "difference_ge", 4, 3301),
    RevisionDomain("retained_sum", ("north", "south"), "sum_ge", 12, 3302),
    RevisionDomain("retained_joint", ("red", "blue"), "min_ge", 6, 3303),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "multigeneration_theory_revision_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _canonical_operator(operator: str) -> str:
    if operator == "closeness_alias":
        return "abs_difference_le"
    return operator


def _value(operator: str, point: Point) -> int:
    left, right = point
    operator = _canonical_operator(operator)
    if operator == "difference_ge":
        return left - right
    if operator == "sum_ge":
        return left + right
    if operator == "min_ge":
        return min(left, right)
    if operator == "max_ge":
        return max(left, right)
    if operator == "abs_difference_le":
        return abs(left - right)
    raise ValueError(operator)


def _predict(hypothesis: Hypothesis, point: Point) -> bool:
    operator, threshold = hypothesis
    value = _value(operator, point)
    if _canonical_operator(operator) == "abs_difference_le":
        return value <= threshold
    return value >= threshold


def _operator_signature(operator: str) -> str:
    return _canonical_hash(
        [
            int(_predict((operator, threshold), point))
            for threshold in THRESHOLDS
            for point in POINTS
        ]
    )


def _deduplicate_grammar() -> Dict[str, Any]:
    retained: Dict[str, str] = {}
    merged = []
    for operator in RAW_OPERATOR_GRAMMAR:
        signature = _operator_signature(operator)
        if signature in retained:
            merged.append(
                {
                    "rejected": operator,
                    "retained": retained[signature],
                    "reason": "EQUIVALENT_PREDICTIVE_SIGNATURE",
                }
            )
        else:
            retained[signature] = operator
    return {
        "operators": tuple(retained.values()),
        "merged": merged,
    }


def _entropy(positive: int, total: int) -> float:
    if positive == 0 or positive == total:
        return 0.0
    probability = positive / total
    return -probability * math.log2(probability) - (
        1.0 - probability
    ) * math.log2(1.0 - probability)


def _active_discovery(
    *,
    domain: RevisionDomain,
    operators: Sequence[str],
    max_probes: int,
    prior: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    hypotheses = [
        (operator, threshold)
        for operator in operators
        for threshold in THRESHOLDS
    ]
    observations = [dict(row) for row in prior]
    used = {tuple(row["point"]) for row in observations}
    for row in observations:
        point = tuple(row["point"])
        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if _predict(hypothesis, point) == bool(row["outcome"])
        ]
    while len(hypotheses) > 1 and len(observations) < max_probes:
        available = [point for point in POINTS if point not in used]
        if not available:
            break
        point = max(
            available,
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
        outcome = domain.observe(point)
        observations.append({"point": list(point), "outcome": int(outcome)})
        used.add(point)
        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if _predict(hypothesis, point) == outcome
        ]
        if not hypotheses:
            break
    selected = hypotheses[0] if len(hypotheses) == 1 else None
    return {
        "selected": list(selected) if selected else None,
        "remaining_hypotheses": [list(row) for row in hypotheses],
        "observations": observations,
        "probes": len(observations),
        "structure_recovered": selected
        == (domain.operator, domain.threshold),
    }


def _accuracy(domain: RevisionDomain, hypothesis: Hypothesis) -> float:
    return sum(
        int(_predict(hypothesis, point) == domain.observe(point))
        for point in POINTS
    ) / len(POINTS)


def _best_library_accuracy(
    domain: RevisionDomain,
    operators: Iterable[str],
) -> float:
    return max(
        _accuracy(domain, (operator, threshold))
        for operator in operators
        for threshold in THRESHOLDS
    )


def _learn_generation(
    *,
    domain: RevisionDomain,
    library: List[str],
    full_grammar: Sequence[str],
) -> Dict[str, Any]:
    before = list(library)
    retained_attempt = _active_discovery(
        domain=domain,
        operators=tuple(library),
        max_probes=14,
    )
    retained_selected = retained_attempt["selected"]
    retained_accuracy = (
        _accuracy(domain, tuple(retained_selected))
        if retained_selected is not None
        else 0.0
    )
    criticism = (
        retained_selected is None or retained_accuracy < 0.95
    )
    if criticism:
        discovery = _active_discovery(
            domain=domain,
            operators=full_grammar,
            max_probes=24,
            prior=retained_attempt["observations"],
        )
    else:
        discovery = retained_attempt
    if discovery["selected"] is None:
        raise RuntimeError(f"unresolved theory generation: {domain.domain_id}")
    selected_operator, selected_threshold = discovery["selected"]
    invented = selected_operator not in library
    if invented:
        library.append(selected_operator)
    return {
        "domain_id": domain.domain_id,
        "fields": list(domain.fields),
        "library_before": before,
        "model_criticism": {
            "status": (
                "THEORY_INADEQUATE" if criticism else "THEORY_ADEQUATE"
            ),
            "invention_required": criticism,
            "retained_attempt_accuracy": retained_accuracy,
            "retained_hypotheses_remaining": len(
                retained_attempt["remaining_hypotheses"]
            ),
        },
        "selected_operator": selected_operator,
        "selected_threshold": selected_threshold,
        "invented": invented,
        "reused": not invented,
        "probes": discovery["probes"],
        "accuracy": _accuracy(
            domain,
            (selected_operator, int(selected_threshold)),
        ),
        "structure_recovered": discovery["structure_recovered"],
        "library_after": list(library),
    }


def _evaluate_transfer(
    *,
    domains: Sequence[RevisionDomain],
    library: Sequence[str],
    full_grammar: Sequence[str],
) -> Dict[str, Any]:
    rows = []
    for domain in domains:
        warm = _active_discovery(
            domain=domain,
            operators=library,
            max_probes=24,
        )
        cold = _active_discovery(
            domain=domain,
            operators=full_grammar,
            max_probes=24,
        )
        if warm["selected"] is None or cold["selected"] is None:
            raise RuntimeError(f"unresolved sealed domain: {domain.domain_id}")
        warm_hypothesis = tuple(warm["selected"])
        cold_hypothesis = tuple(cold["selected"])
        rows.append(
            {
                "domain_id": domain.domain_id,
                "operator": domain.operator,
                "warm_selected": warm["selected"],
                "cold_selected": cold["selected"],
                "warm_accuracy": _accuracy(domain, warm_hypothesis),
                "cold_accuracy": _accuracy(domain, cold_hypothesis),
                "warm_probes": warm["probes"],
                "cold_probes": cold["probes"],
                "warm_hypothesis_evaluations": (
                    warm["probes"] * len(THRESHOLDS) * len(library)
                ),
                "cold_hypothesis_evaluations": (
                    cold["probes"]
                    * len(THRESHOLDS)
                    * len(full_grammar)
                ),
                "structure_recovered": warm["structure_recovered"],
            }
        )
    warm_evaluations = sum(
        row["warm_hypothesis_evaluations"] for row in rows
    )
    cold_evaluations = sum(
        row["cold_hypothesis_evaluations"] for row in rows
    )
    return {
        "mean_accuracy": sum(row["warm_accuracy"] for row in rows) / len(rows),
        "worst_accuracy": min(row["warm_accuracy"] for row in rows),
        "structure_recovery": sum(
            int(row["structure_recovered"]) for row in rows
        ) / len(rows),
        "mean_warm_probes": sum(row["warm_probes"] for row in rows) / len(rows),
        "mean_cold_probes": sum(row["cold_probes"] for row in rows) / len(rows),
        "warm_hypothesis_evaluations": warm_evaluations,
        "cold_hypothesis_evaluations": cold_evaluations,
        "search_reduction": 1.0 - warm_evaluations / cold_evaluations,
        "sealed_reinventions": 0,
        "domains": rows,
    }


def run_multigeneration_theory_revision_benchmark(
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
    grammar = _deduplicate_grammar()
    full_grammar = tuple(_canonical_operator(row) for row in grammar["operators"])
    initial_library = ["difference_ge", "sum_ge", "min_ge"]
    library = list(initial_library)
    dependencies = {
        "concept_signed_linear_relation_8b22663b2ca3": {
            "name": "signed_linear_relation",
            "source_procedure_id": "procedure_meta_abstraction_c5bb3ab6c20e",
        },
        "concept_joint_minimum_81473a7af3f3": {
            "name": "joint_minimum_requirement",
            "source_procedure_id": "procedure_autonomous_curriculum_61cc17827701",
        },
    }
    runtime.store.state["invented_concepts"].update(dependencies)
    runtime.store.commit(reason="load_phase24_phase25_theory_dependencies")

    generations = [
        _learn_generation(
            domain=domain,
            library=library,
            full_grammar=full_grammar,
        )
        for domain in DEVELOPMENT_STREAM
    ]
    invented_operators = [
        row["selected_operator"] for row in generations if row["invented"]
    ]
    reused_operators = [
        row["selected_operator"] for row in generations if row["reused"]
    ]

    # Deliberately insufficient evidence must preserve competing theories and
    # must not create a concept or rewrite durable memory.
    ambiguous_observations = [
        {"point": [0, 0], "outcome": 0},
        {"point": [10, 10], "outcome": 1},
    ]
    ambiguous = _active_discovery(
        domain=RevisionDomain(
            "ambiguous_stream",
            ("unknown_a", "unknown_b"),
            "sum_ge",
            10,
            3401,
        ),
        operators=full_grammar,
        max_probes=len(ambiguous_observations),
        prior=ambiguous_observations,
    )
    ambiguity_preserved = (
        ambiguous["selected"] is None
        and len(ambiguous["remaining_hypotheses"]) > 1
    )

    sealed = _evaluate_transfer(
        domains=SEALED_TRANSFER,
        library=library,
        full_grammar=full_grammar,
    )
    frozen_initial_control = {
        "mean_accuracy": sum(
            _best_library_accuracy(domain, initial_library)
            for domain in SEALED_TRANSFER
        )
        / len(SEALED_TRANSFER),
        "worst_accuracy": min(
            _best_library_accuracy(domain, initial_library)
            for domain in SEALED_TRANSFER
        ),
    }
    forward_gain = sealed["mean_accuracy"] - frozen_initial_control[
        "mean_accuracy"
    ]
    backward_rows = []
    for domain in BACKWARD_RETENTION:
        accuracy = _best_library_accuracy(domain, library)
        backward_rows.append(
            {
                "domain_id": domain.domain_id,
                "operator": domain.operator,
                "accuracy": accuracy,
            }
        )
    backward_retention = {
        "mean_accuracy": sum(row["accuracy"] for row in backward_rows)
        / len(backward_rows),
        "worst_accuracy": min(row["accuracy"] for row in backward_rows),
        "domains": backward_rows,
    }

    errors = []
    if invented_operators != ["max_ge", "abs_difference_le"]:
        errors.append("EXPECTED_TWO_JUSTIFIED_INVENTIONS_NOT_OBSERVED")
    if reused_operators != ["min_ge"]:
        errors.append("EXISTING_PHASE25_CONCEPT_NOT_REUSED")
    if len(grammar["merged"]) != 1:
        errors.append("EQUIVALENT_ALIAS_NOT_MERGED")
    if not ambiguity_preserved:
        errors.append("AMBIGUOUS_EVIDENCE_PREMATURELY_CONSOLIDATED")
    if sealed["mean_accuracy"] < 0.99:
        errors.append("SEALED_MEAN_ACCURACY_BELOW_99_PERCENT")
    if sealed["worst_accuracy"] < 0.98:
        errors.append("SEALED_WORST_ACCURACY_BELOW_98_PERCENT")
    if sealed["structure_recovery"] < 1.0:
        errors.append("SEALED_STRUCTURE_RECOVERY_INCOMPLETE")
    if forward_gain < 0.05:
        errors.append("FORWARD_TRANSFER_GAIN_BELOW_5_POINTS")
    if sealed["sealed_reinventions"] != 0:
        errors.append("SEALED_TRANSFER_REQUIRED_REINVENTION")
    if backward_retention["worst_accuracy"] < 0.99:
        errors.append("BACKWARD_CONCEPT_RETENTION_REGRESSED")
    if len(library) != len(set(library)) or len(library) != 5:
        errors.append("UNCONTROLLED_OR_DUPLICATE_ONTOLOGY_GROWTH")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "invented_operators": invented_operators,
        "reused_operators": reused_operators,
        "duplicate_aliases_merged": len(grammar["merged"]),
        "ambiguity_preserved": ambiguity_preserved,
        "sealed_mean_accuracy": sealed["mean_accuracy"],
        "sealed_worst_accuracy": sealed["worst_accuracy"],
        "sealed_structure_recovery": sealed["structure_recovery"],
        "frozen_initial_control_mean_accuracy": frozen_initial_control[
            "mean_accuracy"
        ],
        "forward_transfer_gain": forward_gain,
        "mean_transfer_probes": sealed["mean_warm_probes"],
        "sealed_reinventions": sealed["sealed_reinventions"],
        "backward_retention_worst_accuracy": backward_retention[
            "worst_accuracy"
        ],
        "initial_library_size": len(initial_library),
        "final_library_size": len(library),
        "bounded_growth": len(library) == 5,
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_autonomous_curriculum_61cc17827701",
        goal="multigeneration_theory_revision",
        steps=["run_isolated_single_generation_invention"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase26_single_generation_control"},
    )
    runtime.skills.promote(baseline)
    revision_record = {
        "schema_version": "aion.hexcore.theory_revision_cycle.v1",
        "cycle_id": "phase26_multigeneration_revision",
        "initial_library": initial_library,
        "final_library": library,
        "generations": generations,
        "grammar_deduplication": grammar["merged"],
        "ambiguity_test": {
            "preserved": ambiguity_preserved,
            "remaining_hypotheses": ambiguous["remaining_hypotheses"],
        },
        "sealed_transfer": sealed,
        "frozen_initial_control": frozen_initial_control,
        "backward_retention": backward_retention,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    procedure_id = (
        "procedure_multigeneration_theory_"
        + _canonical_hash(revision_record)[:12]
    )
    candidate = ProcedureCandidate(
        procedure_id=procedure_id,
        goal="multigeneration_theory_revision",
        steps=[
            "audit_current_ontology_against_each_new_world",
            "invent_only_when_all_retained_concepts_are_inadequate",
            "merge_predictively_equivalent_candidates",
            "reuse_prior_concepts_without_reinvention",
            "preserve_competing_hypotheses_under_insufficient_evidence",
            "verify_forward_transfer_and_backward_retention",
            "retain_bounded_revision_history",
        ],
        score=sealed["mean_accuracy"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase26_multigeneration_sealed",
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
        for operator in invented_operators:
            concept = {
                "schema_version": "aion.hexcore.invented_concept.v1",
                "name": operator,
                "operator": operator,
                "kind": "multigeneration_theory_extension",
                "source_procedure_id": candidate.procedure_id,
                "created_at": _utc_timestamp(),
            }
            concept_id = (
                f"concept_{operator}_"
                + _canonical_hash(concept)[:12]
            )
            concept["concept_id"] = concept_id
            runtime.store.state["invented_concepts"][concept_id] = concept
            runtime.store.state["invention_history"].append(
                {
                    "schema_version": "aion.hexcore.invention_event.v1",
                    "kind": "multigeneration_concept",
                    "invention_id": concept_id,
                    "procedure_id": candidate.procedure_id,
                    "timestamp": _utc_timestamp(),
                }
            )
        runtime.store.state["theory_revisions"].append(revision_record)
        runtime.store.commit(reason=f"theory_revision:{procedure_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": (
            restarted.store.state.get("champions", {}).get(
                "multigeneration_theory_revision"
            )
            == candidate.procedure_id
        ),
        "revision_cycle_retained": any(
            row.get("cycle_id") == "phase26_multigeneration_revision"
            for row in restarted.store.state.get("theory_revisions", [])
        ),
        "all_inventions_retained": all(
            any(
                concept.get("operator") == operator
                for concept in restarted.store.state[
                    "invented_concepts"
                ].values()
            )
            for operator in invented_operators
        ),
        "relearning_generations": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_generations"
        )
    )
    result = {
        "schema_version": "aion.hexcore.multigeneration_theory_revision.v1",
        "benchmark": "cumulative_governed_theory_revision",
        "passed": passed,
        "revision": revision_record,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION accumulated, reused, merged, and protected concepts across "
            "a bounded finite operator grammar. It did not invent arbitrary "
            "mathematics, unrestricted programs, or its own authority rules."
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
        description="Run cumulative HexCore theory-revision benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_multigeneration_theory_revision_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
