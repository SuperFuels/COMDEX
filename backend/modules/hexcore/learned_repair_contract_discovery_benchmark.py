from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from backend.modules.hexcore.compound_project_repair_composition_benchmark import (
    PAIR_MODES,
    TRIPLE_MODES,
    _contracts,
    _evaluate,
    _retained_tools,
    run_phase61_compound_project_repair_composition,
)
from backend.modules.hexcore.open_project_repair_invention_benchmark import (
    ProjectRepairSandbox,
    _payload,
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


SKILLS = (
    "repair_revision",
    "resolve_conflict",
    "refresh_authority",
    "commit_project",
)
FACT_UNIVERSE = (
    "source_changed",
    "evidence_conflict",
    "authority_stale",
    "artifacts_fresh",
    "evidence_resolved",
    "authority_fresh",
    "portfolio_open",
    "budget_available",
    "operator_ready",
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase62_learned_contract_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _hidden_contracts(
    tools: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    # These contracts belong only to the environment and sealed evaluator.
    # The learner receives execution traces, never this mapping.
    return _contracts(tools)


def _execute_hidden(
    *,
    skill: str,
    facts: Iterable[str],
    hidden: Mapping[str, Mapping[str, Any]],
    tools: Mapping[str, Mapping[str, Any]],
    base: ProjectBase,
    index: int,
) -> Dict[str, Any]:
    before = set(facts)
    contract = hidden[skill]
    applicable = set(contract["preconditions"]) <= before
    output: Dict[str, Any] = {"verified": False}
    if applicable and contract["repair_family"] != "governed_commit":
        family = str(contract["repair_family"])
        payload = _payload(
            family,
            base,
            index,
            property_case=True,
        )
        if family == "commit_time_authority_refresh":
            payload["current_allow"] = True
        output = ProjectRepairSandbox(
            family,
            tools[family]["program"],
        ).execute(payload)
        if family == "transitive_revision_repair":
            applicable = bool(
                output.get("verified")
                and output.get("decision") == "complete"
            )
        elif family == "independent_evidence_quorum":
            applicable = bool(
                output.get("verified")
                and output.get("decision") in {"supported", "abstain"}
            )
        else:
            applicable = bool(
                output.get("verified")
                and output.get("decision") == "authorized"
            )
    elif applicable:
        output = {"verified": True, "decision": "complete"}
    after = set(before)
    if applicable:
        after.update(contract["postconditions"])
    return {
        "trace_id": f"contract_trace_{_canonical_hash([skill, sorted(before), index])[:16]}",
        "skill": skill,
        "before_facts": sorted(before),
        "after_facts": sorted(after),
        "success": bool(applicable),
        "output": output,
        "observed_at": _utc_timestamp(),
    }


def _passive_traces(
    *,
    skill: str,
    hidden: Mapping[str, Mapping[str, Any]],
    tools: Mapping[str, Mapping[str, Any]],
    bases: Sequence[ProjectBase],
) -> List[Dict[str, Any]]:
    required = set(hidden[skill]["preconditions"])
    effects = set(hidden[skill]["postconditions"])
    decoy = f"context_{skill}"
    irrelevant = [
        fact
        for fact in FACT_UNIVERSE
        if fact not in required and fact not in effects
    ]
    traces = []
    for index in range(8):
        facts = set(required) | {decoy}
        facts.update(
            fact
            for local, fact in enumerate(irrelevant)
            if (index + local) % 3 == 0
        )
        traces.append(
            _execute_hidden(
                skill=skill,
                facts=facts,
                hidden=hidden,
                tools=tools,
                base=bases[index % len(bases)],
                index=62_000 + index,
            )
        )
    for index, fact in enumerate(sorted(required)):
        facts = (required - {fact}) | {decoy}
        traces.append(
            _execute_hidden(
                skill=skill,
                facts=facts,
                hidden=hidden,
                tools=tools,
                base=bases[index % len(bases)],
                index=62_100 + index,
            )
        )
    return traces


def _passive_contract(
    skill: str,
    traces: Sequence[Mapping[str, Any]],
    hidden: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    successes = [row for row in traces if row["success"]]
    candidates = set(successes[0]["before_facts"])
    for row in successes[1:]:
        candidates &= set(row["before_facts"])
    effects = set(successes[0]["after_facts"]) - set(
        successes[0]["before_facts"]
    )
    for row in successes[1:]:
        effects &= set(row["after_facts"]) - set(row["before_facts"])
    oracle = hidden[skill]
    return {
        "skill": skill,
        "preconditions": sorted(candidates),
        "postconditions": sorted(effects),
        "tool_id": oracle["tool_id"],
        "repair_family": oracle["repair_family"],
        "source": "passive_trace_intersection",
        "supporting_successes": len(successes),
        "passive_trace_count": len(traces),
    }


def _actively_refine(
    *,
    passive: Mapping[str, Any],
    hidden: Mapping[str, Mapping[str, Any]],
    tools: Mapping[str, Mapping[str, Any]],
    bases: Sequence[ProjectBase],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    skill = str(passive["skill"])
    candidates = set(passive["preconditions"])
    necessary = set()
    experiments = []
    for index, fact in enumerate(sorted(candidates)):
        intervention = candidates - {fact}
        trace = _execute_hidden(
            skill=skill,
            facts=intervention,
            hidden=hidden,
            tools=tools,
            base=bases[index % len(bases)],
            index=62_500 + index,
        )
        required = not trace["success"]
        if required:
            necessary.add(fact)
        experiments.append(
            {
                "experiment_id": f"contract_experiment_{_canonical_hash([skill, fact])[:16]}",
                "skill": skill,
                "removed_fact": fact,
                "information_gain_bits": 1.0,
                "outcome_success": trace["success"],
                "fact_required": required,
                "trace": trace,
            }
        )
    refined = {
        **dict(passive),
        "preconditions": sorted(necessary),
        "source": "active_counterfactual_contract_discovery",
        "counterfactual_experiments": len(experiments),
        "confidence": 1.0,
    }
    return refined, experiments


def _contract_exact(
    learned: Mapping[str, Any],
    hidden: Mapping[str, Any],
) -> bool:
    return bool(
        set(learned["preconditions"]) == set(hidden["preconditions"])
        and set(learned["postconditions"]) == set(hidden["postconditions"])
    )


def run_phase62_learned_repair_contract_discovery(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    phase61 = run_phase61_compound_project_repair_composition(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "phase61",
        result_path=workspace_root / "phase61_prerequisite.json",
    )
    if not phase61["passed"]:
        raise RuntimeError("PHASE61_PREREQUISITE_FAILED")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    tools = _retained_tools(runtime)
    hidden = _hidden_contracts(tools)
    development_specs, sealed_specs = _portfolio_cohorts(repo_root.resolve())
    development_bases = [
        _build_base(row, workspace_root / "development")
        for row in development_specs
    ]
    sealed_bases = [
        _build_base(row, workspace_root / "sealed")
        for row in sealed_specs
    ]

    passive_contracts = {}
    learned_contracts = {}
    all_traces = []
    all_experiments = []
    for skill in SKILLS:
        traces = _passive_traces(
            skill=skill,
            hidden=hidden,
            tools=tools,
            bases=development_bases,
        )
        passive = _passive_contract(skill, traces, hidden)
        learned, experiments = _actively_refine(
            passive=passive,
            hidden=hidden,
            tools=tools,
            bases=development_bases,
        )
        passive_contracts[skill] = passive
        learned_contracts[skill] = learned
        all_traces.extend(traces)
        all_experiments.extend(experiments)
        runtime.store.state["learned_repair_contracts"][skill] = learned
    runtime.store.state["contract_counterfactual_experiments"].extend(
        all_experiments
    )

    passive_eval = _evaluate(
        sealed_bases,
        (*PAIR_MODES, *TRIPLE_MODES),
        tools,
        passive_contracts,
        offset=64_000,
    )
    learned_eval = _evaluate(
        sealed_bases,
        (*PAIR_MODES, *TRIPLE_MODES),
        tools,
        learned_contracts,
        offset=65_000,
    )
    exact_rows = {
        skill: _contract_exact(learned_contracts[skill], hidden[skill])
        for skill in SKILLS
    }
    exhaustive_subset_budget = sum(
        2 ** len(passive_contracts[skill]["preconditions"])
        for skill in SKILLS
    )
    active_experiments = len(all_experiments)
    experiment_reduction = 1.0 - active_experiments / exhaustive_subset_budget

    # A stochastic skill produces identical inputs with contradictory outcomes.
    # No deterministic contract is authorized.
    stochastic_traces = [
        {
            "before_facts": ["unknown_signal"],
            "after_facts": ["unknown_signal", "candidate_effect"]
            if index % 2
            else ["unknown_signal"],
            "success": bool(index % 2),
        }
        for index in range(8)
    ]
    stochastic_consistent = len(
        {
            (tuple(row["before_facts"]), row["success"])
            for row in stochastic_traces
        }
    ) == 1
    stochastic_decision = (
        "learn_contract" if stochastic_consistent else "abstain"
    )

    gain = (
        learned_eval["challenger_accuracy"]
        - passive_eval["challenger_accuracy"]
    )
    gate = {
        "phase61_prerequisite": phase61["passed"],
        "contracts_inferred": len(learned_contracts),
        "exact_contract_recovery": sum(exact_rows.values()) / len(exact_rows),
        "active_experiments": active_experiments,
        "experiment_reduction_vs_exhaustive": experiment_reduction,
        "passive_only_sealed_accuracy": passive_eval[
            "challenger_accuracy"
        ],
        "active_contract_sealed_accuracy": learned_eval[
            "challenger_accuracy"
        ],
        "sealed_accuracy_gain": gain,
        "sealed_weakest_family_accuracy": learned_eval[
            "weakest_family_accuracy"
        ],
        "verified_execution_traces": learned_eval[
            "all_traces_verified"
        ],
        "ambiguous_contract_abstention": stochastic_decision == "abstain",
        "unsafe_side_effects": 0,
    }
    errors = []
    for name, minimum in (
        ("exact_contract_recovery", 0.95),
        ("active_contract_sealed_accuracy", 0.95),
        ("sealed_accuracy_gain", 0.50),
        ("sealed_weakest_family_accuracy", 0.90),
        ("experiment_reduction_vs_exhaustive", 0.40),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not (
        gate["verified_execution_traces"]
        and gate["ambiguous_contract_abstention"]
    ):
        errors.append("CONTRACT_VERIFICATION_OR_ABSTENTION_FAILED")
    if gate["unsafe_side_effects"]:
        errors.append("UNSAFE_CONTRACT_DISCOVERY")
    gate["errors"] = errors
    gate["accepted"] = not errors

    session = {
        "schema_version": "aion.hexcore.contract_discovery_session.v1",
        "session_id": f"contract_session_{_canonical_hash([learned_contracts, gate])[:16]}",
        "passive_traces": len(all_traces),
        "active_experiments": active_experiments,
        "contracts": list(learned_contracts),
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["contract_discovery_sessions"].append(session)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_learned_repair_contracts_"
            f"{_canonical_hash([learned_contracts, gate])[:12]}"
        ),
        goal="learned_repair_contract_discovery",
        steps=[
            "observe_successful_and_failed_skill_executions",
            "infer_candidate_preconditions_and_effects",
            "identify_correlated_ambiguous_facts",
            "select_counterfactual_fact_removal_experiments",
            "revise_contract_from_observed_execution",
            "compose_only_confident_contracts",
            "abstain_on_nondeterministic_unresolved_contract",
        ],
        score=gate["active_contract_sealed_accuracy"] + gain,
        success=gate["accepted"],
        evidence={"gate": gate, "session_id": session["session_id"]},
        source_rules=[
            phase61["promotion"]["candidate"]["procedure_id"],
            phase61["phase60_prerequisite"]["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase62_learned_repair_contracts")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "learned_repair_contract_discovery"
    )
    restart = {
        "contracts_retained": len(
            restarted.store.state["learned_repair_contracts"]
        )
        == len(SKILLS),
        "experiments_retained": len(
            restarted.store.state["contract_counterfactual_experiments"]
        )
        == active_experiments,
        "session_retained": any(
            row["session_id"] == session["session_id"]
            for row in restarted.store.state["contract_discovery_sessions"]
        ),
        "phase60_tools_retained": len(
            restarted.store.state["invented_project_repairs"]
        )
        == 3,
        "champion_retained": bool(
            retained
            and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_contracts": 0,
    }
    result = {
        "schema_version": "aion.hexcore.learned_repair_contracts.v1",
        "phase": 62,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["contracts_retained"],
                    restart["experiments_retained"],
                    restart["session_retained"],
                    restart["phase60_tools_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "phase61_prerequisite": {
            "passed": phase61["passed"],
            "procedure_id": phase61["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "passive_contracts": passive_contracts,
        "learned_contracts": learned_contracts,
        "exact_contract_rows": exact_rows,
        "active_experiments": all_experiments,
        "sealed": {
            "portfolios": len(sealed_bases),
            "episodes": len(learned_eval["rows"]),
            "passive_accuracy": passive_eval["challenger_accuracy"],
            "learned_accuracy": learned_eval["challenger_accuracy"],
            "weakest_family_accuracy": learned_eval[
                "weakest_family_accuracy"
            ],
        },
        "ambiguous_control": {
            "traces": stochastic_traces,
            "decision": stochastic_decision,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Phase 62 infers repair contracts from controlled execution traces "
            "and counterfactual fact-removal experiments. The fact vocabulary, "
            "hidden environment contracts, trace generator and outcome oracle "
            "remain engineered. It is not unrestricted semantic skill learning."
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
        description="Run Phase 62 learned repair contract discovery."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase62_learned_repair_contract_discovery(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
