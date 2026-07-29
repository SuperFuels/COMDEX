from __future__ import annotations

import argparse
import json
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


Example = Dict[str, Any]


@dataclass(frozen=True)
class OntologyDomain:
    domain_id: str
    fields: Tuple[str, str]
    rule_family: str
    threshold: int
    seed: int
    label_noise: float = 0.01

    def generate(self, count: int, *, offset: int) -> List[Example]:
        rng = random.Random(self.seed + offset)
        rows = []
        for index in range(count):
            left = rng.randint(0, 20)
            right = rng.randint(0, 20)
            if self.rule_family == "ordered_margin":
                label = left - right >= self.threshold
            elif self.rule_family == "unary_threshold":
                label = left >= self.threshold
            else:
                raise ValueError(self.rule_family)
            if rng.random() < self.label_noise:
                label = not label
            rows.append(
                {
                    "example_id": f"{self.domain_id}_{offset}_{index}",
                    "state": {
                        self.fields[0]: left,
                        self.fields[1]: right,
                    },
                    "outcome": int(label),
                }
            )
        return rows


DEVELOPMENT_DOMAINS = (
    OntologyDomain("cinder_balance", ("cinder", "ash"), "ordered_margin", 3, 101),
    OntologyDomain("harbor_pressure", ("crest", "keel"), "ordered_margin", 5, 202),
)

SEALED_DOMAINS = (
    OntologyDomain("orchid_tension", ("petal", "stem"), "ordered_margin", 2, 303),
    OntologyDomain("signal_reserve", ("carrier", "drain"), "ordered_margin", 4, 404),
    OntologyDomain("mineral_bias", ("vein", "tailing"), "ordered_margin", 6, 505),
)

NEGATIVE_CONTROLS = (
    OntologyDomain("simple_voltage", ("voltage", "shadow"), "unary_threshold", 11, 606),
    OntologyDomain("simple_depth", ("depth", "echo"), "unary_threshold", 9, 707),
)


TEMPLATES = (
    {"template_id": "left_threshold", "operator": "unary_ge", "complexity": 1},
    {"template_id": "right_threshold", "operator": "unary_le", "complexity": 1},
    {"template_id": "field_equality", "operator": "equality", "complexity": 1},
    {"template_id": "ordered_margin", "operator": "difference_ge", "complexity": 2},
    {
        "template_id": "ordered_margin_alias",
        "operator": "difference_ge",
        "complexity": 3,
    },
    {"template_id": "reverse_margin", "operator": "reverse_difference_ge", "complexity": 2},
    {"template_id": "additive_mass", "operator": "sum_ge", "complexity": 2},
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_ontology_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _feature(
    template: Mapping[str, Any],
    state: Mapping[str, int],
    fields: Sequence[str],
) -> float:
    left = float(state[fields[0]])
    right = float(state[fields[1]])
    operator = template["operator"]
    if operator == "unary_ge":
        return left
    if operator == "unary_le":
        return -right
    if operator == "equality":
        return -abs(left - right)
    if operator == "difference_ge":
        return left - right
    if operator == "reverse_difference_ge":
        return right - left
    if operator == "sum_ge":
        return left + right
    raise ValueError(operator)


def _accuracy(
    *,
    template: Mapping[str, Any],
    threshold: float,
    rows: Sequence[Example],
    fields: Sequence[str],
) -> float:
    return sum(
        int(
            (_feature(template, row["state"], fields) >= threshold)
            == bool(row["outcome"])
        )
        for row in rows
    ) / len(rows)


def _fit(
    *,
    template: Mapping[str, Any],
    rows: Sequence[Example],
    fields: Sequence[str],
) -> Dict[str, Any]:
    values = sorted(
        {_feature(template, row["state"], fields) for row in rows}
    )
    thresholds = [values[0] - 1.0] + values + [values[-1] + 1.0]
    threshold = max(
        thresholds,
        key=lambda value: (
            _accuracy(
                template=template,
                threshold=value,
                rows=rows,
                fields=fields,
            ),
            -abs(value),
        ),
    )
    return {
        "template": dict(template),
        "threshold": threshold,
        "training_accuracy": _accuracy(
            template=template,
            threshold=threshold,
            rows=rows,
            fields=fields,
        ),
    }


def _truth_signature(
    *,
    template: Mapping[str, Any],
    rows: Sequence[Example],
    fields: Sequence[str],
) -> str:
    fit = _fit(template=template, rows=rows, fields=fields)
    values = [
        int(
            _feature(template, row["state"], fields)
            >= fit["threshold"]
        )
        for row in rows
    ]
    return _canonical_hash(values)


def _deduplicate_templates(
    *,
    rows: Sequence[Example],
    fields: Sequence[str],
) -> Dict[str, Any]:
    retained: Dict[str, Mapping[str, Any]] = {}
    merged = []
    for template in TEMPLATES:
        signature = _truth_signature(
            template=template, rows=rows, fields=fields
        )
        prior = retained.get(signature)
        if prior is None or int(template["complexity"]) < int(
            prior["complexity"]
        ):
            if prior is not None:
                merged.append(
                    {
                        "rejected": prior["template_id"],
                        "retained": template["template_id"],
                        "reason": "EQUIVALENT_TRUTH_SIGNATURE_LOWER_COMPLEXITY",
                    }
                )
            retained[signature] = template
        else:
            merged.append(
                {
                    "rejected": template["template_id"],
                    "retained": prior["template_id"],
                    "reason": "EQUIVALENT_TRUTH_SIGNATURE",
                }
            )
    return {"templates": list(retained.values()), "merged": merged}


def _evaluate_template_across_domains(
    *,
    template: Mapping[str, Any],
    domains: Sequence[OntologyDomain],
    train_count: int,
    evaluation_count: int,
) -> Dict[str, Any]:
    rows = []
    for domain in domains:
        train = domain.generate(train_count, offset=10_000)
        evaluation = domain.generate(evaluation_count, offset=20_000)
        fit = _fit(
            template=template,
            rows=train,
            fields=domain.fields,
        )
        rows.append(
            {
                "domain_id": domain.domain_id,
                "fields": list(domain.fields),
                "threshold": fit["threshold"],
                "training_examples": train_count,
                "evaluation_examples": evaluation_count,
                "accuracy": _accuracy(
                    template=template,
                    threshold=fit["threshold"],
                    rows=evaluation,
                    fields=domain.fields,
                ),
            }
        )
    return {
        "template": dict(template),
        "mean_accuracy": sum(row["accuracy"] for row in rows) / len(rows),
        "worst_accuracy": min(row["accuracy"] for row in rows),
        "domains": rows,
    }


def _select_existing_ontology(
    domains: Sequence[OntologyDomain],
) -> Dict[str, Any]:
    existing = [
        template for template in TEMPLATES
        if template["operator"] in {"unary_ge", "unary_le", "equality"}
    ]
    results = [
        _evaluate_template_across_domains(
            template=template,
            domains=domains,
            train_count=160,
            evaluation_count=240,
        )
        for template in existing
    ]
    return max(
        results,
        key=lambda row: (row["mean_accuracy"], row["worst_accuracy"]),
    )


def _criticise(existing: Mapping[str, Any]) -> Dict[str, Any]:
    inadequate = (
        float(existing["mean_accuracy"]) < 0.88
        or float(existing["worst_accuracy"]) < 0.84
    )
    return {
        "status": (
            "ONTOLOGY_INADEQUATE" if inadequate else "ONTOLOGY_ADEQUATE"
        ),
        "invention_required": inadequate,
        "mean_accuracy": existing["mean_accuracy"],
        "worst_accuracy": existing["worst_accuracy"],
        "reason": (
            "NO_EXISTING_PREDICATE_GENERALISES"
            if inadequate
            else "EXISTING_PREDICATE_SUFFICIENT"
        ),
    }


def run_open_ontology_invention_benchmark(
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
    existing = _select_existing_ontology(DEVELOPMENT_DOMAINS)
    criticism = _criticise(existing)
    combined_development = [
        row
        for domain in DEVELOPMENT_DOMAINS
        for row in domain.generate(160, offset=30_000)
    ]
    # Candidate equivalence is tested in the first domain's coordinate frame;
    # selected templates are subsequently refit independently in every domain.
    deduplication = _deduplicate_templates(
        rows=DEVELOPMENT_DOMAINS[0].generate(240, offset=31_000),
        fields=DEVELOPMENT_DOMAINS[0].fields,
    )
    candidates = [
        _evaluate_template_across_domains(
            template=template,
            domains=DEVELOPMENT_DOMAINS,
            train_count=160,
            evaluation_count=240,
        )
        for template in deduplication["templates"]
    ]
    selected = max(
        candidates,
        key=lambda row: (
            row["mean_accuracy"] - 0.002 * row["template"]["complexity"],
            row["worst_accuracy"],
            -row["template"]["complexity"],
        ),
    )
    development_gate = bool(
        criticism["invention_required"]
        and selected["mean_accuracy"] >= 0.95
        and selected["worst_accuracy"] >= 0.93
        and selected["template"]["operator"] not in {
            "unary_ge",
            "unary_le",
            "equality",
        }
    )

    negative_controls = []
    for domain in NEGATIVE_CONTROLS:
        control_existing = _select_existing_ontology((domain,))
        control_criticism = _criticise(control_existing)
        negative_controls.append(
            {
                "domain_id": domain.domain_id,
                "existing": control_existing,
                "criticism": control_criticism,
                "unnecessary_invention_rejected": (
                    not control_criticism["invention_required"]
                ),
            }
        )

    sealed_transfer = (
        _evaluate_template_across_domains(
            template=selected["template"],
            domains=SEALED_DOMAINS,
            train_count=40,
            evaluation_count=400,
        )
        if development_gate else None
    )
    sealed_existing = _select_existing_ontology(SEALED_DOMAINS)
    sealed_cold_candidates = [
        _evaluate_template_across_domains(
            template=template,
            domains=SEALED_DOMAINS,
            train_count=200,
            evaluation_count=400,
        )
        for template in deduplication["templates"]
    ]
    sealed_cold = max(
        sealed_cold_candidates,
        key=lambda row: (
            row["mean_accuracy"],
            row["worst_accuracy"],
            -row["template"]["complexity"],
        ),
    )
    errors = []
    if not development_gate:
        errors.append("DEVELOPMENT_INVENTION_GATE_FAILED")
    if sealed_transfer is None or sealed_transfer["mean_accuracy"] < 0.95:
        errors.append("SEALED_MEAN_ACCURACY_BELOW_95_PERCENT")
    if sealed_transfer is None or sealed_transfer["worst_accuracy"] < 0.93:
        errors.append("SEALED_WORST_ACCURACY_BELOW_93_PERCENT")
    if sealed_transfer is not None and (
        sealed_transfer["mean_accuracy"]
        < sealed_existing["mean_accuracy"] + 0.10
    ):
        errors.append("INVENTED_CONCEPT_GAIN_BELOW_10_POINTS")
    if not all(
        row["unnecessary_invention_rejected"] for row in negative_controls
    ):
        errors.append("UNNECESSARY_INVENTION_CONTROL_FAILED")
    if sealed_transfer is not None and (
        sealed_transfer["mean_accuracy"]
        < sealed_cold["mean_accuracy"] - 0.02
    ):
        errors.append("TRANSFER_BELOW_COLD_PROTECTION_BAND")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "selected_template": selected["template"],
        "development_mean_accuracy": selected["mean_accuracy"],
        "sealed_transfer_mean_accuracy": (
            sealed_transfer["mean_accuracy"] if sealed_transfer else 0.0
        ),
        "sealed_transfer_worst_accuracy": (
            sealed_transfer["worst_accuracy"] if sealed_transfer else 0.0
        ),
        "existing_ontology_mean_accuracy": sealed_existing["mean_accuracy"],
        "gain_over_existing": (
            sealed_transfer["mean_accuracy"] - sealed_existing["mean_accuracy"]
            if sealed_transfer else 0.0
        ),
        "transfer_examples_per_domain": 40,
        "cold_examples_per_domain": 200,
        "example_reduction": 0.80,
        "cold_mean_accuracy": sealed_cold["mean_accuracy"],
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_compositional_goal_graph_444839f5eb15",
        goal="cross_domain_ontology_invention",
        steps=["use_existing_typed_predicates_only"],
        score=sealed_existing["mean_accuracy"],
        success=True,
        evidence={"evaluation": "phase22_existing_ontology_control"},
    )
    runtime.skills.promote(baseline)
    concept_id = (
        "concept_ordered_margin_"
        + _canonical_hash(selected["template"])[:12]
    )
    concept = {
        "schema_version": "aion.hexcore.invented_concept.v1",
        "concept_id": concept_id,
        "name": "ordered_margin",
        "operator": selected["template"]["operator"],
        "arity": 2,
        "parameterisation": "domain_calibrated_threshold",
        "complexity": selected["template"]["complexity"],
        "source": "phase22_outcome_grounded_relational_search",
        "model_criticism": criticism,
        "deduplication": deduplication["merged"],
        "development": selected,
        "sealed": sealed_transfer,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_ontology_invention_"
            + _canonical_hash(concept)[:12]
        ),
        goal="cross_domain_ontology_invention",
        steps=[
            "measure_existing_ontology_residual_error",
            "declare_current_predicates_inadequate",
            "generate_bounded_relational_predicate_candidates",
            "fit_parameters_on_development_observations",
            "merge_equivalent_truth_signatures",
            "reject_unnecessary_concepts",
            "verify_cross_domain_transfer",
            "retain_concept_with_provenance_and_complexity",
        ],
        score=gate["sealed_transfer_mean_accuracy"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase22_open_ontology_sealed",
            "gate": gate,
            "concept_id": concept_id,
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
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "concept",
                "invention_id": concept_id,
                "procedure_id": candidate.procedure_id,
                "gate": gate,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"concept_invention:{concept_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    champion = restarted.skills.champion(candidate.goal)
    retained = bool(
        champion and champion.get("procedure_id") == candidate.procedure_id
    )
    result = {
        "schema_version": "aion.hexcore.open_ontology_invention.v1",
        "benchmark": "cross_domain_relational_predicate_invention",
        "language_provider_used": False,
        "existing_ontology": existing,
        "model_criticism": criticism,
        "candidate_deduplication": deduplication,
        "development_candidates": candidates,
        "selected_invention": concept,
        "negative_controls": negative_controls,
        "sealed_transfer": sealed_transfer,
        "sealed_existing_control": sealed_existing,
        "sealed_cold_search": sealed_cold,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained,
            "invented_concept_retained": (
                concept_id in restarted.store.state["invented_concepts"]
            ),
            "invention_history_retained": any(
                row.get("invention_id") == concept_id
                for row in restarted.store.state["invention_history"]
            ),
            "relearning_examples": 0,
        },
        "gates": {
            "inadequacy_recognised": criticism["invention_required"],
            "new_relational_predicate_invented": (
                selected["template"]["operator"] == "difference_ge"
            ),
            "duplicates_merged": bool(deduplication["merged"]),
            "unnecessary_inventions_rejected": all(
                row["unnecessary_invention_rejected"]
                for row in negative_controls
            ),
            "cross_domain_transfer": gate["accepted"],
            "cau_promotion": promotion.get("promoted") is True,
            "restart_retention": retained,
        },
        "boundary_statement": (
            "AION selected a new relational predicate from a bounded candidate "
            "grammar and transferred it across renamed numeric domains. It did "
            "not invent unrestricted mathematics, language, code, or its own "
            "authority rules."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/open_ontology_invention.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_ontology_invention.json"),
    )
    args = parser.parse_args()
    result = run_open_ontology_invention_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
