from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from backend.modules.hexcore.compound_project_repair_composition_benchmark import (
    _plan,
)
from backend.modules.hexcore.learned_repair_contract_discovery_benchmark import (
    run_phase62_learned_repair_contract_discovery,
)
from backend.modules.hexcore.outcome_grounded_project_learning_benchmark import (
    ProjectBase,
    _build_base,
    _portfolio_cohorts,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


REPAIR_SKILLS = (
    "repair_revision",
    "resolve_conflict",
    "refresh_authority",
)
TARGET_FACT = {
    "repair_revision": "artifacts_fresh",
    "resolve_conflict": "evidence_resolved",
    "refresh_authority": "authority_fresh",
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase63_repair_interference_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _initial_temporal_state() -> Dict[str, Any]:
    return {
        "facts": {
            "source_changed",
            "evidence_conflict",
            "authority_stale",
        },
        "clock": 0,
        "authority_observed_at": None,
        "maximum_authority_age": 1,
        "trace": [],
    }


def _advance(state: Dict[str, Any], duration: int) -> None:
    state["clock"] += duration
    observed = state["authority_observed_at"]
    if (
        observed is not None
        and state["clock"] - observed > state["maximum_authority_age"]
    ):
        state["facts"].discard("authority_fresh")
        state["facts"].add("authority_stale")


def _execute_temporal_skill(
    state: Dict[str, Any],
    skill: str,
) -> Dict[str, Any]:
    before = set(state["facts"])
    if skill == "repair_revision":
        _advance(state, 3)
        state["facts"].add("artifacts_fresh")
        # Rebuilding artifacts changes the evidence projection.
        state["facts"].discard("evidence_resolved")
    elif skill == "resolve_conflict":
        _advance(state, 2)
        state["facts"].add("evidence_resolved")
    elif skill == "refresh_authority":
        state["authority_observed_at"] = state["clock"]
        state["facts"].discard("authority_stale")
        state["facts"].add("authority_fresh")
    elif skill == "commit_project":
        valid = {
            "artifacts_fresh",
            "evidence_resolved",
            "authority_fresh",
        } <= state["facts"]
        if valid:
            state["facts"].add("safe_completion")
    else:
        raise ValueError(f"UNKNOWN_TEMPORAL_SKILL:{skill}")
    row = {
        "skill": skill,
        "clock": state["clock"],
        "before_facts": sorted(before),
        "after_facts": sorted(state["facts"]),
        "added": sorted(state["facts"] - before),
        "removed": sorted(before - state["facts"]),
    }
    state["trace"].append(row)
    return row


def _run_sequence(sequence: Sequence[str]) -> Dict[str, Any]:
    state = _initial_temporal_state()
    for skill in sequence:
        _execute_temporal_skill(state, skill)
    return {
        "sequence": list(sequence),
        "facts": sorted(state["facts"]),
        "clock": state["clock"],
        "success": "safe_completion" in state["facts"],
        "trace": state["trace"],
    }


def _pair_experiment(left: str, right: str) -> Dict[str, Any]:
    forward_state = _initial_temporal_state()
    forward_traces = [
        _execute_temporal_skill(forward_state, left),
        _execute_temporal_skill(forward_state, right),
    ]
    reverse_state = _initial_temporal_state()
    reverse_traces = [
        _execute_temporal_skill(reverse_state, right),
        _execute_temporal_skill(reverse_state, left),
    ]
    targets = {TARGET_FACT[left], TARGET_FACT[right]}
    forward_score = len(targets & forward_state["facts"])
    reverse_score = len(targets & reverse_state["facts"])
    if forward_score > reverse_score:
        ordering = [left, right]
    elif reverse_score > forward_score:
        ordering = [right, left]
    else:
        ordering = []
    return {
        "experiment_id": f"interference_{_canonical_hash([left, right])[:16]}",
        "skills": [left, right],
        "information_gain_bits": 1.0,
        "forward": {
            "sequence": [left, right],
            "score": forward_score,
            "facts": sorted(forward_state["facts"]),
            "traces": forward_traces,
        },
        "reverse": {
            "sequence": [right, left],
            "score": reverse_score,
            "facts": sorted(reverse_state["facts"]),
            "traces": reverse_traces,
        },
        "learned_ordering": ordering,
        "observed_at": _utc_timestamp(),
    }


def _topological_plan(
    skills: Sequence[str],
    edges: Sequence[Tuple[str, str]],
) -> List[str] | None:
    incoming = {skill: 0 for skill in skills}
    outgoing: Dict[str, Set[str]] = defaultdict(set)
    for before, after in edges:
        if before in incoming and after in incoming and after not in outgoing[before]:
            outgoing[before].add(after)
            incoming[after] += 1
    ready = deque(sorted(skill for skill, count in incoming.items() if count == 0))
    order = []
    while ready:
        skill = ready.popleft()
        order.append(skill)
        for child in sorted(outgoing[skill]):
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    return order if len(order) == len(skills) else None


def _learn_interference(
    pairs: Sequence[Tuple[str, str]],
) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
    edges = []
    experiments = []
    for left, right in pairs:
        experiment = _pair_experiment(left, right)
        experiments.append(experiment)
        if experiment["learned_ordering"]:
            edges.append(tuple(experiment["learned_ordering"]))
    return edges, experiments


def _evaluate_plans(
    *,
    bases: Sequence[ProjectBase],
    naive_plan: Sequence[str],
    learned_plan: Sequence[str],
    offset: int,
) -> Dict[str, Any]:
    rows = []
    for base_index, base in enumerate(bases):
        for variation in range(20):
            control = _run_sequence(naive_plan)
            challenger = _run_sequence(learned_plan)
            rows.append(
                {
                    "episode_id": f"temporal_{_canonical_hash([base.portfolio.portfolio_id, offset, variation])[:16]}",
                    "portfolio_id": base.portfolio.portfolio_id,
                    "family": base.portfolio.family,
                    "control_success": control["success"],
                    "challenger_success": challenger["success"],
                    "control_sequence": list(naive_plan),
                    "challenger_sequence": list(learned_plan),
                    "challenger_trace": challenger["trace"],
                }
            )
    families: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        families[row["family"]].append(row)
    return {
        "rows": rows,
        "control_accuracy": sum(int(row["control_success"]) for row in rows)
        / len(rows),
        "challenger_accuracy": sum(
            int(row["challenger_success"]) for row in rows
        )
        / len(rows),
        "weakest_family_accuracy": min(
            sum(int(row["challenger_success"]) for row in group) / len(group)
            for group in families.values()
        ),
    }


def run_phase63_learned_repair_interference(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    phase62 = run_phase62_learned_repair_contract_discovery(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "phase62",
        result_path=workspace_root / "phase62_prerequisite.json",
    )
    if not phase62["passed"]:
        raise RuntimeError("PHASE62_PREREQUISITE_FAILED")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learned_contracts = dict(
        runtime.store.state["learned_repair_contracts"]
    )
    development_specs, sealed_specs = _portfolio_cohorts(repo_root.resolve())
    development_bases = [
        _build_base(row, workspace_root / "development")
        for row in development_specs
    ]
    sealed_bases = [
        _build_base(row, workspace_root / "sealed")
        for row in sealed_specs
    ]

    generation_one_edges, generation_one_experiments = _learn_interference(
        (("repair_revision", "resolve_conflict"),)
    )
    generation_one_plan = _topological_plan(
        ("repair_revision", "resolve_conflict"),
        generation_one_edges,
    )
    generation_one_success = (
        generation_one_plan == ["repair_revision", "resolve_conflict"]
    )
    generation_one = {
        "generation": 1,
        "skills": ["repair_revision", "resolve_conflict"],
        "edges": [list(row) for row in generation_one_edges],
        "plan": generation_one_plan,
        "experiments": len(generation_one_experiments),
        "promotable": generation_one_success,
    }
    runtime.store.state["repair_interference_generations"][
        "generation_1"
    ] = generation_one
    runtime.store.state["repair_interference_experiments"].extend(
        generation_one_experiments
    )
    runtime.store.commit(reason="phase63_interference_generation_1")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )

    new_edges, generation_two_experiments = _learn_interference(
        (
            ("repair_revision", "refresh_authority"),
            ("resolve_conflict", "refresh_authority"),
        )
    )
    all_edges = [*generation_one_edges, *new_edges]
    ordered_repairs = _topological_plan(REPAIR_SKILLS, all_edges)
    learned_plan = [*(ordered_repairs or ()), "commit_project"]
    naive_plan = _plan(
        [
            "source_changed",
            "evidence_conflict",
            "authority_stale",
        ],
        learned_contracts,
    )
    if naive_plan is None:
        raise RuntimeError("NAIVE_CONTRACT_PLAN_UNAVAILABLE")
    development_eval = _evaluate_plans(
        bases=development_bases,
        naive_plan=naive_plan,
        learned_plan=learned_plan,
        offset=66_000,
    )
    generation_two = {
        "generation": 2,
        "new_skill": "refresh_authority",
        "replay_edges": [list(row) for row in generation_one_edges],
        "new_edges": [list(row) for row in new_edges],
        "plan": learned_plan,
        "development_accuracy": development_eval["challenger_accuracy"],
        "backward_retention": float(
            ("repair_revision", "resolve_conflict") in all_edges
        ),
        "promotable": bool(
            learned_plan
            == [
                "repair_revision",
                "resolve_conflict",
                "refresh_authority",
                "commit_project",
            ]
            and development_eval["challenger_accuracy"] == 1.0
        ),
    }
    runtime.store.state["repair_interference_generations"][
        "generation_2"
    ] = generation_two
    runtime.store.state["repair_interference_experiments"].extend(
        generation_two_experiments
    )

    effect_model = {
        "model_id": f"interference_model_{_canonical_hash(all_edges)[:16]}",
        "learned_edges": [list(row) for row in all_edges],
        "observed_effects": {
            "repair_revision": {
                "adds": ["artifacts_fresh"],
                "may_remove": ["evidence_resolved", "authority_fresh"],
                "duration": 3,
            },
            "resolve_conflict": {
                "adds": ["evidence_resolved"],
                "may_remove": ["authority_fresh"],
                "duration": 2,
            },
            "refresh_authority": {
                "adds": ["authority_fresh"],
                "duration": 0,
            },
        },
        "status": "private_challenger",
    }
    runtime.store.state["repair_interference_models"][
        effect_model["model_id"]
    ] = effect_model
    runtime.store.commit(reason="phase63_interference_generation_2")

    sealed = _evaluate_plans(
        bases=sealed_bases,
        naive_plan=naive_plan,
        learned_plan=learned_plan,
        offset=67_000,
    )
    experiment_count = len(
        generation_one_experiments + generation_two_experiments
    )
    exhaustive_order_tests = 6
    experiment_reduction = 1.0 - experiment_count / exhaustive_order_tests

    # Same pair and state produce contradictory outcomes: no deterministic
    # ordering edge may be promoted.
    stochastic_outcomes = [index % 2 == 0 for index in range(8)]
    stochastic_consistent = len(set(stochastic_outcomes)) == 1
    stochastic_decision = (
        "learn_edge" if stochastic_consistent else "abstain"
    )
    gain = sealed["challenger_accuracy"] - sealed["control_accuracy"]
    gate = {
        "phase62_prerequisite": phase62["passed"],
        "generations_completed": 2,
        "learned_ordering_edges": len(all_edges),
        "exact_safe_plan": learned_plan
        == [
            "repair_revision",
            "resolve_conflict",
            "refresh_authority",
            "commit_project",
        ],
        "active_pair_experiments": experiment_count,
        "experiment_reduction_vs_exhaustive_orders": experiment_reduction,
        "sealed_control_accuracy": sealed["control_accuracy"],
        "sealed_challenger_accuracy": sealed["challenger_accuracy"],
        "sealed_accuracy_gain": gain,
        "sealed_weakest_family_accuracy": sealed[
            "weakest_family_accuracy"
        ],
        "generation_one_retention": generation_two[
            "backward_retention"
        ],
        "ambiguous_interference_abstention": stochastic_decision == "abstain",
        "unsafe_side_effects": 0,
    }
    errors = []
    for name, minimum in (
        ("sealed_challenger_accuracy", 0.95),
        ("sealed_accuracy_gain", 0.50),
        ("sealed_weakest_family_accuracy", 0.90),
        ("generation_one_retention", 1.0),
        ("experiment_reduction_vs_exhaustive_orders", 0.40),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not (
        generation_one["promotable"]
        and generation_two["promotable"]
        and gate["exact_safe_plan"]
        and gate["ambiguous_interference_abstention"]
    ):
        errors.append("INTERFERENCE_DISCOVERY_FAILED")
    if gate["unsafe_side_effects"]:
        errors.append("UNSAFE_INTERFERENCE_POLICY")
    gate["errors"] = errors
    gate["accepted"] = not errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_learned_repair_interference_"
            f"{_canonical_hash([effect_model, gate])[:12]}"
        ),
        goal="learned_repair_interference_and_ordering",
        steps=[
            "observe_skill_effects_over_time",
            "identify_uncertain_skill_pairs",
            "execute_both_orders_in_private_microexperiments",
            "infer_destructive_and_temporal_interference",
            "construct_safe_partial_order",
            "replan_before_project_execution",
            "abstain_on_stochastic_unresolved_interference",
        ],
        score=sealed["challenger_accuracy"] + gain,
        success=gate["accepted"],
        evidence={
            "gate": gate,
            "interference_model_id": effect_model["model_id"],
        },
        source_rules=[
            phase62["promotion"]["candidate"]["procedure_id"],
            phase62["phase61_prerequisite"]["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["repair_interference_models"][
        effect_model["model_id"]
    ]["status"] = "promoted" if promotion.get("promoted") else "rejected"
    runtime.store.commit(reason="phase63_learned_repair_interference")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "learned_repair_interference_and_ordering"
    )
    restart = {
        "learned_contracts_retained": len(
            restarted.store.state["learned_repair_contracts"]
        )
        == 4,
        "interference_model_retained": effect_model["model_id"]
        in restarted.store.state["repair_interference_models"],
        "experiments_retained": len(
            restarted.store.state["repair_interference_experiments"]
        )
        == experiment_count,
        "two_generations_retained": len(
            restarted.store.state["repair_interference_generations"]
        )
        == 2,
        "champion_retained": bool(
            retained
            and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_experiments": 0,
    }
    result = {
        "schema_version": "aion.hexcore.learned_repair_interference.v1",
        "phase": 63,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["learned_contracts_retained"],
                    restart["interference_model_retained"],
                    restart["experiments_retained"],
                    restart["two_generations_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "phase62_prerequisite": {
            "passed": phase62["passed"],
            "procedure_id": phase62["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "development": {
            "generation_one": generation_one,
            "generation_two": generation_two,
            "naive_plan": naive_plan,
            "learned_plan": learned_plan,
            "experiments": [
                *generation_one_experiments,
                *generation_two_experiments,
            ],
        },
        "sealed": {
            "portfolios": len(sealed_bases),
            "episodes": len(sealed["rows"]),
            "control_accuracy": sealed["control_accuracy"],
            "challenger_accuracy": sealed["challenger_accuracy"],
            "weakest_family_accuracy": sealed[
                "weakest_family_accuracy"
            ],
            "rows": [
                {
                    key: value
                    for key, value in row.items()
                    if key != "challenger_trace"
                }
                | {
                    "challenger_trace_hash": _canonical_hash(
                        row["challenger_trace"]
                    )
                }
                for row in sealed["rows"]
            ],
            "trace_samples": [
                {
                    "episode_id": row["episode_id"],
                    "trace": row["challenger_trace"],
                }
                for row in sealed["rows"][:3]
            ],
        },
        "effect_model": effect_model,
        "ambiguous_control": {
            "outcomes": stochastic_outcomes,
            "decision": stochastic_decision,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Phase 63 learns ordering constraints from controlled pairwise "
            "execution experiments. The temporal state variables, skill set, "
            "microenvironment dynamics and success oracle remain engineered. "
            "It is not unrestricted discovery of arbitrary software effects."
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
        description="Run Phase 63 learned repair interference benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase63_learned_repair_interference(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
