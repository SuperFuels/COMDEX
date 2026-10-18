from __future__ import annotations

import argparse
import json
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


@dataclass(frozen=True)
class RelationDomain:
    domain_id: str
    fields: Tuple[str, str]
    weights: Tuple[int, int]
    threshold: int
    seed: int
    nonlinear: bool = False

    def generate(self, count: int, *, offset: int) -> List[Dict[str, Any]]:
        rng = random.Random(self.seed + offset)
        rows = []
        for index in range(count):
            left = rng.randint(-10, 20)
            right = rng.randint(-10, 20)
            if self.nonlinear:
                outcome = (left >= 5) != (right >= 5)
            else:
                outcome = (
                    self.weights[0] * left + self.weights[1] * right
                    >= self.threshold
                )
            rows.append(
                {
                    "example_id": f"{self.domain_id}_{offset}_{index}",
                    "state": {self.fields[0]: left, self.fields[1]: right},
                    "outcome": int(outcome),
                }
            )
        return rows


DEVELOPMENT_DOMAINS = (
    RelationDomain("thermal_margin", ("heat", "loss"), (1, -1), 3, 1101),
    RelationDomain("buoyancy_load", ("lift", "mass"), (1, -1), 5, 1102),
    RelationDomain("reserve_sum", ("alpha", "beta"), (1, 1), 12, 1103),
    RelationDomain("inverse_bias", ("north", "south"), (-1, 1), 2, 1104),
)
SEALED_DOMAINS = (
    RelationDomain("lumen_balance", ("flare", "shade"), (1, -1), 4, 1201),
    RelationDomain("alloy_total", ("nickel", "cobalt"), (1, 1), 10, 1202),
    RelationDomain("reverse_current", ("sink", "source"), (-1, 1), 1, 1203),
    RelationDomain("containment", ("leak", "barrier"), (-1, -1), -8, 1204),
)
NEGATIVE_CONTROLS = (
    RelationDomain(
        "exclusive_channels",
        ("channel_a", "channel_b"),
        (0, 0),
        0,
        1301,
        nonlinear=True,
    ),
)
WEIGHT_CANDIDATES = tuple(
    (left, right)
    for left in (-1, 0, 1)
    for right in (-1, 0, 1)
    if (left, right) != (0, 0)
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "meta_abstraction_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _score(
    weights: Tuple[int, int],
    state: Mapping[str, int],
    fields: Sequence[str],
) -> int:
    return (
        weights[0] * int(state[fields[0]])
        + weights[1] * int(state[fields[1]])
    )


def _accuracy(
    *,
    weights: Tuple[int, int],
    threshold: int,
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> float:
    return sum(
        int(
            (_score(weights, row["state"], fields) >= threshold)
            == bool(row["outcome"])
        )
        for row in rows
    ) / len(rows)


def _fit_weights(
    *,
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
    candidates: Sequence[Tuple[int, int]],
) -> Dict[str, Any]:
    fitted = []
    for weights in candidates:
        values = sorted({_score(weights, row["state"], fields) for row in rows})
        thresholds = [values[0] - 1] + values + [values[-1] + 1]
        threshold = max(
            thresholds,
            key=lambda value: (
                _accuracy(
                    weights=weights,
                    threshold=value,
                    rows=rows,
                    fields=fields,
                ),
                -abs(value),
            ),
        )
        fitted.append(
            {
                "weights": list(weights),
                "threshold": threshold,
                "training_accuracy": _accuracy(
                    weights=weights,
                    threshold=threshold,
                    rows=rows,
                    fields=fields,
                ),
            }
        )
    return max(
        fitted,
        key=lambda row: (
            row["training_accuracy"],
            -sum(abs(value) for value in row["weights"]),
            row["weights"],
        ),
    )


def _evaluate(
    *,
    domains: Sequence[RelationDomain],
    train_count: int,
    evaluation_count: int,
    candidates: Sequence[Tuple[int, int]],
) -> Dict[str, Any]:
    domain_results = []
    for domain in domains:
        train = domain.generate(train_count, offset=20_000)
        evaluation = domain.generate(evaluation_count, offset=30_000)
        fit = _fit_weights(
            rows=train,
            fields=domain.fields,
            candidates=candidates,
        )
        domain_results.append(
            {
                "domain_id": domain.domain_id,
                "fields": list(domain.fields),
                "true_weights": list(domain.weights),
                "learned_weights": fit["weights"],
                "learned_threshold": fit["threshold"],
                "training_examples": train_count,
                "accuracy": _accuracy(
                    weights=tuple(fit["weights"]),
                    threshold=int(fit["threshold"]),
                    rows=evaluation,
                    fields=domain.fields,
                ),
                "structure_recovered": tuple(fit["weights"]) == domain.weights,
            }
        )
    return {
        "mean_accuracy": sum(row["accuracy"] for row in domain_results)
        / len(domain_results),
        "worst_accuracy": min(row["accuracy"] for row in domain_results),
        "structure_recovery": sum(
            int(row["structure_recovered"]) for row in domain_results
        )
        / len(domain_results),
        "domains": domain_results,
    }


def run_meta_abstraction_invention_benchmark(
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
    ordered_margin_id = "concept_ordered_margin_2d5a04f6994e"
    runtime.store.state["invented_concepts"][ordered_margin_id] = {
        "concept_id": ordered_margin_id,
        "name": "ordered_margin",
        "operator": "difference_ge",
        "status": "phase22_promoted_dependency",
        "source_procedure_id": "procedure_ontology_invention_0e9d9c5eafb8",
    }
    runtime.store.commit(reason="load_phase22_concept_for_meta_abstraction")

    concrete_control = _evaluate(
        domains=SEALED_DOMAINS,
        train_count=180,
        evaluation_count=500,
        candidates=((1, -1),),
    )
    development = _evaluate(
        domains=DEVELOPMENT_DOMAINS,
        train_count=60,
        evaluation_count=400,
        candidates=WEIGHT_CANDIDATES,
    )
    sealed_transfer = _evaluate(
        domains=SEALED_DOMAINS,
        train_count=36,
        evaluation_count=500,
        candidates=WEIGHT_CANDIDATES,
    )
    sealed_cold = _evaluate(
        domains=SEALED_DOMAINS,
        train_count=180,
        evaluation_count=500,
        candidates=WEIGHT_CANDIDATES,
    )
    negative_controls = []
    for domain in NEGATIVE_CONTROLS:
        result = _evaluate(
            domains=(domain,),
            train_count=180,
            evaluation_count=500,
            candidates=WEIGHT_CANDIDATES,
        )
        negative_controls.append(
            {
                "domain_id": domain.domain_id,
                "best_linear_accuracy": result["mean_accuracy"],
                "unnecessary_generalisation_rejected": (
                    result["mean_accuracy"] < 0.90
                ),
            }
        )

    errors = []
    if development["mean_accuracy"] < 0.98:
        errors.append("DEVELOPMENT_META_ABSTRACTION_BELOW_98_PERCENT")
    if sealed_transfer["mean_accuracy"] < 0.97:
        errors.append("SEALED_MEAN_BELOW_97_PERCENT")
    if sealed_transfer["worst_accuracy"] < 0.95:
        errors.append("SEALED_WORST_BELOW_95_PERCENT")
    if sealed_transfer["structure_recovery"] < 1.0:
        errors.append("SEALED_STRUCTURE_NOT_FULLY_RECOVERED")
    if (
        sealed_transfer["mean_accuracy"]
        < concrete_control["mean_accuracy"] + 0.15
    ):
        errors.append("GAIN_OVER_CONCRETE_ONTOLOGY_BELOW_15_POINTS")
    if (
        sealed_transfer["mean_accuracy"]
        < sealed_cold["mean_accuracy"] - 0.02
    ):
        errors.append("FEW_SHOT_TRANSFER_BELOW_COLD_PROTECTION_BAND")
    if not all(
        row["unnecessary_generalisation_rejected"]
        for row in negative_controls
    ):
        errors.append("NONLINEAR_NEGATIVE_CONTROL_NOT_REJECTED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "development_mean_accuracy": development["mean_accuracy"],
        "sealed_mean_accuracy": sealed_transfer["mean_accuracy"],
        "sealed_worst_accuracy": sealed_transfer["worst_accuracy"],
        "sealed_structure_recovery": sealed_transfer["structure_recovery"],
        "concrete_control_mean_accuracy": concrete_control["mean_accuracy"],
        "gain_over_concrete_ontology": (
            sealed_transfer["mean_accuracy"]
            - concrete_control["mean_accuracy"]
        ),
        "transfer_examples_per_domain": 36,
        "cold_examples_per_domain": 180,
        "example_reduction": 0.80,
        "cold_mean_accuracy": sealed_cold["mean_accuracy"],
        "nonlinear_controls_rejected": all(
            row["unnecessary_generalisation_rejected"]
            for row in negative_controls
        ),
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_ontology_invention_0e9d9c5eafb8",
        goal="hierarchical_meta_abstraction",
        steps=["reuse_ordered_margin_as_fixed_concrete_predicate"],
        score=concrete_control["mean_accuracy"],
        success=True,
        evidence={"evaluation": "phase24_concrete_ontology_control"},
    )
    runtime.skills.promote(baseline)
    meta_concept = {
        "schema_version": "aion.hexcore.invented_concept.v1",
        "name": "signed_linear_relation",
        "kind": "parameterised_meta_predicate",
        "operator": "weighted_sum_ge",
        "parameters": ["left_weight", "right_weight", "threshold"],
        "parameter_domain": {
            "left_weight": [-1, 0, 1],
            "right_weight": [-1, 0, 1],
        },
        "subsumes": [
            "ordered_margin",
            "reverse_margin",
            "additive_mass",
            "negative_mass",
        ],
        "parent_concepts": [ordered_margin_id],
        "complexity": 3,
        "development": development,
        "sealed": sealed_transfer,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    concept_id = (
        "concept_signed_linear_relation_"
        + _canonical_hash(meta_concept)[:12]
    )
    meta_concept["concept_id"] = concept_id
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_meta_abstraction_"
            + _canonical_hash(meta_concept)[:12]
        ),
        goal="hierarchical_meta_abstraction",
        steps=[
            "compare_concrete_concepts_by_operator_signature",
            "propose_parameterised_relational_meta_predicate",
            "fit_domain_parameters_from_sparse_examples",
            "verify_on_renamed_held_out_relation_families",
            "reject_non_linear_overgeneralisation",
            "retain_hierarchy_with_provenance",
        ],
        score=sealed_transfer["mean_accuracy"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase24_meta_abstraction_sealed",
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
        runtime.store.state["invented_concepts"][concept_id] = meta_concept
        runtime.store.state["invented_concepts"][ordered_margin_id][
            "abstracted_by"
        ] = concept_id
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "meta_concept",
                "invention_id": concept_id,
                "procedure_id": candidate.procedure_id,
                "gate": gate,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"meta_concept_invention:{concept_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "meta_concept_retained": (
            concept_id in restarted.store.state["invented_concepts"]
        ),
        "parent_link_retained": (
            restarted.store.state["invented_concepts"]
            .get(ordered_margin_id, {})
            .get("abstracted_by")
            == concept_id
        ),
        "champion_retained": (
            restarted.store.state
            .get("champions", {})
            .get("hierarchical_meta_abstraction")
            == candidate.procedure_id
        ),
        "relearning_examples": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_examples"
        )
    )
    result = {
        "schema_version": "aion.hexcore.meta_abstraction.v1",
        "benchmark": "hierarchical_relational_meta_abstraction",
        "passed": passed,
        "development": development,
        "concrete_control": concrete_control,
        "sealed_transfer": sealed_transfer,
        "sealed_cold": sealed_cold,
        "negative_controls": negative_controls,
        "gate": gate,
        "invented_meta_concept": meta_concept,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION compressed a bounded finite family of signed linear "
            "relations into a parameterised meta-predicate. It did not "
            "invent unrestricted mathematics, arbitrary programs, or "
            "authority rules."
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
        description="Run HexCore hierarchical meta-abstraction benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_meta_abstraction_invention_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
