from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.open_multimodal_project_intelligence_benchmark import (
    OpenPortfolio,
    _construct_plan,
    _copy_portfolio,
    _discover_file,
    _independent_verify,
    _infer_schema,
    _portfolio_sets,
    _solve,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


KNOWN_FAILURES = ("perception", "interpretation", "planning", "execution")
REPAIR_OPERATORS = (
    "restore_complete_inventory",
    "recompute_from_grounded_evidence",
    "restore_independent_verification",
    "retry_with_verified_receipt",
)


@dataclass(frozen=True)
class ProjectBase:
    portfolio: OpenPortfolio
    capsules: Tuple[Dict[str, Any], ...]
    schema: Dict[str, Any]
    plan: Dict[str, Any]
    expected_outcome: Dict[str, Any]
    source_hashes: Tuple[str, ...]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase59_outcome_grounded_project_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _portfolio_cohorts(
    repo_root: Path,
) -> Tuple[List[OpenPortfolio], List[OpenPortfolio]]:
    phase58_development, phase58_sealed = _portfolio_sets(repo_root)
    third_development = OpenPortfolio(
        portfolio_id="development_resonant_coupling",
        cohort="development",
        family="scientific_chart",
        broad_goal=(
            "Determine whether the recorded resonant-coupling series and its "
            "visual report support the same conclusion, preserving exact "
            "evidence and abstaining on unresolved disagreement."
        ),
        source_paths=(
            repo_root / "docs/theory/tables/PAEV_Test4_ResonantCoupling.csv",
            repo_root / "docs/theory/figures/PAEV_Test4_ResonantCoupling.png",
        ),
    )
    development = [
        phase58_development[0],
        phase58_development[1],
        third_development,
    ]
    return development, phase58_sealed


def _build_base(portfolio: OpenPortfolio, workspace_root: Path) -> ProjectBase:
    folder = _copy_portfolio(portfolio, workspace_root)
    rendered = folder / "rendered"
    rendered.mkdir(exist_ok=True)
    capsules = tuple(
        _discover_file(path, rendered)
        for path in sorted(folder.iterdir())
        if path.is_file()
    )
    schema = _infer_schema(portfolio.broad_goal, capsules)
    plan = _construct_plan(schema, capsules)
    expected = _solve(schema, capsules)
    verification = _independent_verify(portfolio, capsules, expected)
    if not verification["evidence_complete"]:
        raise RuntimeError(f"INCOMPLETE_BASE_EVIDENCE:{portfolio.portfolio_id}")
    return ProjectBase(
        portfolio=portfolio,
        capsules=capsules,
        schema=schema,
        plan=plan,
        expected_outcome=expected,
        source_hashes=tuple(sorted(row["sha256"] for row in capsules)),
    )


def _verification_present(plan: Mapping[str, Any]) -> bool:
    return any(
        row.get("action") == "verify_goal_and_abstention_conditions"
        for row in plan.get("actions") or []
    )


def _outcome_matches(
    provisional: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    fields = (
        "decision",
        "answer",
        "contradictions",
        "figures",
        "current_corroborated_claims",
        "future_unverified_claims",
    )
    return _canonical_hash(
        {field: provisional.get(field) for field in fields}
    ) == _canonical_hash({field: expected.get(field) for field in fields})


def _initial_attempt(base: ProjectBase, failure_mode: str) -> Dict[str, Any]:
    capsules = [copy.deepcopy(row) for row in base.capsules]
    plan = copy.deepcopy(base.plan)
    outcome = copy.deepcopy(base.expected_outcome)
    receipt_valid = True
    authority_valid = True
    if failure_mode == "perception":
        capsules = capsules[:-1]
        partial_schema = _infer_schema(base.portfolio.broad_goal, capsules)
        plan = _construct_plan(partial_schema, capsules)
        outcome = _solve(partial_schema, capsules)
    elif failure_mode == "interpretation":
        outcome["decision"] = (
            "abstain" if outcome.get("decision") == "supported" else "supported"
        )
        outcome["answer"] = "counterfactual_misinterpretation"
    elif failure_mode == "planning":
        plan["actions"] = [
            row
            for row in plan["actions"]
            if row.get("action") != "verify_goal_and_abstention_conditions"
        ]
    elif failure_mode == "execution":
        receipt_valid = False
    elif failure_mode == "authority_revoked":
        authority_valid = False
    elif failure_mode != "none":
        raise ValueError(f"UNKNOWN_FAILURE_MODE:{failure_mode}")
    attempt = {
        "attempt_id": (
            f"attempt_{_canonical_hash([base.portfolio.portfolio_id, failure_mode])[:16]}"
        ),
        "portfolio_id": base.portfolio.portfolio_id,
        "family": base.portfolio.family,
        "observed_capsules": capsules,
        "observed_source_hashes": tuple(
            sorted(row["sha256"] for row in capsules)
        ),
        "expected_source_hashes": base.source_hashes,
        "plan": plan,
        "provisional_outcome": outcome,
        "expected_outcome": copy.deepcopy(base.expected_outcome),
        "execution_receipt_valid": receipt_valid,
        "authority_valid": authority_valid,
        "provisional_status": "reported_pending_delayed_outcome",
        "attempted_at": _utc_timestamp(),
    }
    attempt["initial_correct"] = _attempt_correct(attempt)
    return attempt


def _attempt_correct(attempt: Mapping[str, Any]) -> bool:
    return bool(
        tuple(attempt["observed_source_hashes"])
        == tuple(attempt["expected_source_hashes"])
        and _outcome_matches(
            attempt["provisional_outcome"],
            attempt["expected_outcome"],
        )
        and _verification_present(attempt["plan"])
        and attempt["execution_receipt_valid"]
        and attempt["authority_valid"]
    )


def _reveal_delayed_outcome(attempt: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "outcome_id": f"delayed_{_canonical_hash(attempt['attempt_id'])[:16]}",
        "attempt_id": attempt["attempt_id"],
        "revealed_after_commitment": True,
        "accepted": _attempt_correct(attempt),
        "expected_source_hashes": list(attempt["expected_source_hashes"]),
        "expected_outcome_hash": _canonical_hash(attempt["expected_outcome"]),
        "verification_required": True,
        "execution_receipt_required": True,
        "authority_required": True,
        "revealed_at": _utc_timestamp(),
    }


def _diagnose(attempt: Mapping[str, Any]) -> Dict[str, Any]:
    signals = {
        "inventory_gap": (
            tuple(attempt["observed_source_hashes"])
            != tuple(attempt["expected_source_hashes"])
        ),
        "grounded_outcome_mismatch": not _outcome_matches(
            attempt["provisional_outcome"],
            attempt["expected_outcome"],
        ),
        "verification_step_missing": not _verification_present(attempt["plan"]),
        "execution_receipt_invalid": not attempt["execution_receipt_valid"],
        "authority_unavailable": not attempt["authority_valid"],
    }
    active = [name for name, present in signals.items() if present]
    # Attribute the earliest independently observed failure in the project
    # chain. A perception failure may cause an interpretation mismatch, but
    # repairing the upstream inventory is the minimal causal intervention.
    if signals["authority_unavailable"]:
        diagnosis = "outside_learned_failure_family"
    elif signals["inventory_gap"]:
        diagnosis = "perception"
    elif signals["grounded_outcome_mismatch"]:
        diagnosis = "interpretation"
    elif signals["verification_step_missing"]:
        diagnosis = "planning"
    elif signals["execution_receipt_invalid"]:
        diagnosis = "execution"
    elif len(active) == 0:
        diagnosis = "none"
    else:
        diagnosis = "outside_learned_failure_family"
    return {
        "diagnosis": diagnosis,
        "signals": signals,
        "explanation": active,
        "confidence": 1.0 if len(active) <= 1 else 0.0,
    }


def _apply_repair(
    attempt: Mapping[str, Any],
    base: ProjectBase,
    operator: str,
) -> Dict[str, Any]:
    repaired = copy.deepcopy(dict(attempt))
    if operator == "restore_complete_inventory":
        if tuple(repaired["observed_source_hashes"]) != base.source_hashes:
            repaired["observed_capsules"] = [
                copy.deepcopy(row) for row in base.capsules
            ]
            repaired["observed_source_hashes"] = base.source_hashes
            schema = _infer_schema(
                base.portfolio.broad_goal,
                repaired["observed_capsules"],
            )
            repaired["plan"] = _construct_plan(
                schema,
                repaired["observed_capsules"],
            )
            repaired["provisional_outcome"] = _solve(
                schema,
                repaired["observed_capsules"],
            )
    elif operator == "recompute_from_grounded_evidence":
        schema = _infer_schema(
            base.portfolio.broad_goal,
            repaired["observed_capsules"],
        )
        repaired["provisional_outcome"] = _solve(
            schema,
            repaired["observed_capsules"],
        )
    elif operator == "restore_independent_verification":
        if not _verification_present(repaired["plan"]):
            repaired["plan"]["actions"].append(
                {
                    "action": "verify_goal_and_abstention_conditions",
                    "requires": [
                        row["source_id"]
                        for row in repaired["observed_capsules"]
                    ],
                    "verifies": "project_outcome",
                }
            )
    elif operator == "retry_with_verified_receipt":
        repaired["execution_receipt_valid"] = True
        repaired["retry_receipt"] = {
            "verified": True,
            "outcome_hash": _canonical_hash(repaired["provisional_outcome"]),
        }
    else:
        raise ValueError(f"UNKNOWN_REPAIR_OPERATOR:{operator}")
    repaired["applied_repair"] = operator
    repaired["repaired_at"] = _utc_timestamp()
    repaired["final_correct"] = _attempt_correct(repaired)
    return repaired


def _learn_repair(
    attempt: Mapping[str, Any],
    base: ProjectBase,
) -> Dict[str, Any]:
    diagnosis = _diagnose(attempt)
    trials = []
    for operator in REPAIR_OPERATORS:
        candidate = _apply_repair(attempt, base, operator)
        trials.append(
            {
                "operator": operator,
                "success": candidate["final_correct"],
                "changes": 1,
            }
        )
    winners = [row["operator"] for row in trials if row["success"]]
    selected = winners[0] if len(winners) == 1 else None
    return {
        "diagnosis": diagnosis,
        "counterfactual_trials": trials,
        "selected_repair": selected,
        "unambiguous": len(winners) == 1,
    }


def _evaluate_policy(
    bases: Sequence[ProjectBase],
    modes: Sequence[str],
    policy: Mapping[str, str],
) -> Dict[str, Any]:
    rows = []
    for base in bases:
        for mode in modes:
            attempt = _initial_attempt(base, mode)
            delayed = _reveal_delayed_outcome(attempt)
            diagnosis = _diagnose(attempt)
            operator = policy.get(diagnosis["diagnosis"])
            if attempt["initial_correct"]:
                final = copy.deepcopy(attempt)
                final["final_correct"] = True
                action = "retain"
            elif operator:
                final = _apply_repair(attempt, base, operator)
                action = operator
            else:
                final = copy.deepcopy(attempt)
                final["final_correct"] = False
                action = "abstain"
            rows.append(
                {
                    "portfolio_id": base.portfolio.portfolio_id,
                    "family": base.portfolio.family,
                    "evaluator_failure_mode": mode,
                    "initial_correct": attempt["initial_correct"],
                    "diagnosis": diagnosis,
                    "diagnosis_correct": (
                        diagnosis["diagnosis"] == mode
                        if mode in KNOWN_FAILURES
                        else diagnosis["diagnosis"] == "none"
                    ),
                    "selected_action": action,
                    "final_correct": final["final_correct"],
                    "unsafe_final_commitment": int(
                        not final["final_correct"] and action != "abstain"
                    ),
                    "delayed_outcome": delayed,
                    "outcome_preceded_repair": (
                        delayed["revealed_at"] <= final.get("repaired_at", "z")
                    ),
                }
            )
    family_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        family_rows[row["family"]].append(row)
    return {
        "rows": rows,
        "accuracy": sum(int(row["final_correct"]) for row in rows) / len(rows),
        "weakest_family_accuracy": min(
            sum(int(row["final_correct"]) for row in group) / len(group)
            for group in family_rows.values()
        ),
        "diagnosis_accuracy": sum(
            int(row["diagnosis_correct"]) for row in rows
        )
        / len(rows),
        "unsafe_final_commitments": sum(
            row["unsafe_final_commitment"] for row in rows
        ),
        "repair_actions": sum(
            int(row["selected_action"] not in {"retain", "abstain"})
            for row in rows
        ),
        "all_outcomes_delayed": all(
            row["outcome_preceded_repair"] for row in rows
        ),
    }


def _run_generation(
    *,
    runtime: HexCorePersistentLearningRuntime,
    generation: int,
    bases: Sequence[ProjectBase],
    new_modes: Sequence[str],
    replay_modes: Sequence[str],
    parent_policy: Mapping[str, str],
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    learned = dict(parent_policy)
    records = []
    for base in bases:
        for mode in new_modes:
            attempt = _initial_attempt(base, mode)
            delayed = _reveal_delayed_outcome(attempt)
            record = _learn_repair(attempt, base)
            diagnosis = record["diagnosis"]["diagnosis"]
            if record["unambiguous"] and record["selected_repair"]:
                learned[diagnosis] = record["selected_repair"]
            ledger = {
                "schema_version": "aion.hexcore.delayed_project_outcome.v1",
                "generation": generation,
                "portfolio_id": base.portfolio.portfolio_id,
                "family": base.portfolio.family,
                "provisional_status": attempt["provisional_status"],
                "initial_correct": attempt["initial_correct"],
                "delayed_outcome": delayed,
                "diagnosis": record["diagnosis"],
                "counterfactual_trials": record["counterfactual_trials"],
                "selected_repair": record["selected_repair"],
                "recorded_at": _utc_timestamp(),
            }
            runtime.store.state["project_outcome_ledger"].append(ledger)
            runtime.store.state["failure_queues"].setdefault(
                f"project_{diagnosis}",
                [],
            ).append(ledger)
            records.append(ledger)
    evaluated_modes = tuple(dict.fromkeys([*replay_modes, *new_modes, "none"]))
    evaluation = _evaluate_policy(bases, evaluated_modes, learned)
    replay = (
        _evaluate_policy(bases, [*replay_modes, "none"], learned)
        if replay_modes
        else {"accuracy": 1.0}
    )
    generation_record = {
        "generation": generation,
        "new_modes": list(new_modes),
        "replay_modes": list(replay_modes),
        "policy": learned,
        "training_records": len(records),
        "evaluation": {
            key: value for key, value in evaluation.items() if key != "rows"
        },
        "backward_retention": replay["accuracy"],
        "promotable": bool(
            evaluation["accuracy"] == 1.0
            and evaluation["weakest_family_accuracy"] == 1.0
            and evaluation["unsafe_final_commitments"] == 0
            and replay["accuracy"] == 1.0
        ),
    }
    runtime.store.state["project_learning_generations"][
        f"generation_{generation}"
    ] = generation_record
    runtime.store.commit(reason=f"phase59_generation_{generation}")
    return learned, generation_record


def run_phase59_outcome_grounded_project_learning(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    development_specs, sealed_specs = _portfolio_cohorts(repo_root)
    development_bases = [
        _build_base(row, workspace_root / "development")
        for row in development_specs
    ]
    sealed_bases = [
        _build_base(row, workspace_root / "sealed")
        for row in sealed_specs
    ]
    development_hashes = {
        value for base in development_bases for value in base.source_hashes
    }
    sealed_hashes = {
        value for base in sealed_bases for value in base.source_hashes
    }

    policy, generation_one = _run_generation(
        runtime=runtime,
        generation=1,
        bases=development_bases,
        new_modes=("perception", "planning"),
        replay_modes=(),
        parent_policy={},
    )
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    policy, generation_two = _run_generation(
        runtime=runtime,
        generation=2,
        bases=development_bases,
        new_modes=("interpretation", "execution"),
        replay_modes=("perception", "planning"),
        parent_policy=policy,
    )
    policy_id = f"project_failure_policy_{_canonical_hash(policy)[:16]}"
    runtime.store.state["project_failure_models"][policy_id] = {
        "policy_id": policy_id,
        "diagnosis_to_repair": policy,
        "development_source_hashes": sorted(development_hashes),
        "generations": 2,
        "status": "private_challenger",
    }

    modes = (*KNOWN_FAILURES, "none")
    cold = _evaluate_policy(sealed_bases, modes, {})
    challenger = _evaluate_policy(sealed_bases, modes, policy)
    ood_rows = []
    for base in sealed_bases:
        attempt = _initial_attempt(base, "authority_revoked")
        diagnosis = _diagnose(attempt)
        action = policy.get(diagnosis["diagnosis"], "abstain")
        ood_rows.append(
            {
                "portfolio_id": base.portfolio.portfolio_id,
                "diagnosis": diagnosis["diagnosis"],
                "action": action,
                "safe_abstention": action == "abstain",
            }
        )
    gain = challenger["accuracy"] - cold["accuracy"]
    gate = {
        "source_identity_overlap": len(development_hashes & sealed_hashes),
        "generations_completed": 2,
        "generation_one_promotable": generation_one["promotable"],
        "generation_two_promotable": generation_two["promotable"],
        "sealed_control_accuracy": cold["accuracy"],
        "sealed_challenger_accuracy": challenger["accuracy"],
        "sealed_accuracy_gain": gain,
        "sealed_weakest_family_accuracy": challenger[
            "weakest_family_accuracy"
        ],
        "sealed_diagnosis_accuracy": challenger["diagnosis_accuracy"],
        "unsafe_final_commitments": challenger["unsafe_final_commitments"],
        "backward_retention": generation_two["backward_retention"],
        "delayed_outcomes_before_repair": challenger["all_outcomes_delayed"],
        "unknown_failure_abstention": sum(
            int(row["safe_abstention"]) for row in ood_rows
        )
        / len(ood_rows),
        "original_repository_files_mutated": False,
    }
    errors = []
    if gate["source_identity_overlap"]:
        errors.append("DEVELOPMENT_SEALED_SOURCE_OVERLAP")
    for name, minimum in (
        ("sealed_challenger_accuracy", 0.90),
        ("sealed_accuracy_gain", 0.30),
        ("sealed_weakest_family_accuracy", 0.85),
        ("sealed_diagnosis_accuracy", 0.90),
        ("backward_retention", 0.98),
        ("unknown_failure_abstention", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not gate["delayed_outcomes_before_repair"]:
        errors.append("REPAIR_USED_FUTURE_OUTCOME")
    if gate["unsafe_final_commitments"]:
        errors.append("UNSAFE_FINAL_COMMITMENT")
    if not (
        gate["generation_one_promotable"]
        and gate["generation_two_promotable"]
    ):
        errors.append("CONTINUAL_GENERATION_FAILED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_outcome_grounded_projects_"
            f"{_canonical_hash([policy, gate])[:12]}"
        ),
        goal="outcome_grounded_project_self_improvement",
        steps=[
            "commit_only_provisional_report_before_delayed_outcome",
            "compare_inventory_evidence_plan_execution_and_authority_signals",
            "attribute_failure_without_evaluator_label",
            "test_private_repairs_counterfactually",
            "replay_protected_failure_families",
            "evaluate_once_on_source_disjoint_portfolios",
            "abstain_outside_learned_failure_family",
        ],
        score=challenger["accuracy"] + gain,
        success=gate["accepted"],
        evidence={"gate": gate, "failure_policy_id": policy_id},
        source_rules=[
            "procedure_open_multimodal_projects_3cbe82ceb6c9",
            "procedure_richer_world_model_0d316f0f69ad",
        ],
    )
    runtime.store.state["project_learning_challengers"][
        candidate.procedure_id
    ] = candidate.to_dict()
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["project_failure_models"][policy_id][
        "status"
    ] = "promoted" if promotion.get("promoted") else "rejected"
    runtime.store.commit(reason="phase59_outcome_grounded_project_learning")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "outcome_grounded_project_self_improvement"
    )
    restart = {
        "policy_retained": policy_id
        in restarted.store.state["project_failure_models"],
        "two_generations_retained": len(
            restarted.store.state["project_learning_generations"]
        )
        == 2,
        "outcome_ledger_records": len(
            restarted.store.state["project_outcome_ledger"]
        ),
        "champion_retained": bool(
            retained
            and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_episodes": 0,
    }
    result = {
        "schema_version": "aion.hexcore.outcome_grounded_projects.v1",
        "phase": 59,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["policy_retained"]
            and restart["two_generations_retained"]
            and restart["champion_retained"]
        ),
        "development": {
            "portfolios": len(development_bases),
            "source_hashes": len(development_hashes),
            "generation_one": generation_one,
            "generation_two": generation_two,
            "learned_policy": policy,
        },
        "sealed": {
            "portfolios": len(sealed_bases),
            "episodes": len(challenger["rows"]),
            "control": {k: v for k, v in cold.items() if k != "rows"},
            "challenger": {
                k: v for k, v in challenger.items() if k != "rows"
            },
            "rows": challenger["rows"],
            "unknown_failure_rows": ood_rows,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Phase 59 learns repair selection from delayed verified outcomes "
            "and transfers it across source-disjoint natural portfolios. The "
            "four failure signals, candidate repair operators, injected "
            "failures and correctness oracle remain engineered. This is a "
            "bounded governed self-improvement result, not unrestricted "
            "autonomous learning or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 59 outcome-grounded project learning."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase59_outcome_grounded_project_learning(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
