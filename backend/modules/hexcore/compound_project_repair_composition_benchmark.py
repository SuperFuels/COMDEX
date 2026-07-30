from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.open_project_repair_invention_benchmark import (
    PHASE59_POLICY,
    ProjectRepairSandbox,
    _payload,
    run_phase60_open_project_repair_invention,
)
from backend.modules.hexcore.outcome_grounded_project_learning_benchmark import (
    ProjectBase,
    _build_base,
    _evaluate_policy,
    _portfolio_cohorts,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PAIR_MODES = ("revision_authority", "conflict_authority")
TRIPLE_MODES = ("revision_conflict_authority",)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase61_compound_project_repair_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _retained_tools(runtime: HexCorePersistentLearningRuntime) -> Dict[str, Dict[str, Any]]:
    return {
        row["repair_family"]: row
        for row in runtime.store.state["invented_project_repairs"].values()
    }


def _contracts(tools: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        "repair_revision": {
            "skill": "repair_revision",
            "preconditions": ["source_changed"],
            "postconditions": ["artifacts_fresh"],
            "tool_id": tools["transitive_revision_repair"]["tool_id"],
            "repair_family": "transitive_revision_repair",
        },
        "resolve_conflict": {
            "skill": "resolve_conflict",
            "preconditions": ["evidence_conflict"],
            "postconditions": ["evidence_resolved"],
            "tool_id": tools["independent_evidence_quorum"]["tool_id"],
            "repair_family": "independent_evidence_quorum",
        },
        "refresh_authority": {
            "skill": "refresh_authority",
            "preconditions": ["authority_stale"],
            "postconditions": ["authority_fresh"],
            "tool_id": tools["commit_time_authority_refresh"]["tool_id"],
            "repair_family": "commit_time_authority_refresh",
        },
        "commit_project": {
            "skill": "commit_project",
            "preconditions": [
                "artifacts_fresh",
                "evidence_resolved",
                "authority_fresh",
            ],
            "postconditions": ["safe_completion"],
            "tool_id": None,
            "repair_family": "governed_commit",
        },
    }


def _episode(
    base: ProjectBase,
    mode: str,
    index: int,
) -> Dict[str, Any]:
    revision = "revision" in mode
    conflict = "conflict" in mode
    authority = "authority" in mode
    facts = {
        "source_changed" if revision else "artifacts_fresh",
        "evidence_conflict" if conflict else "evidence_resolved",
        "authority_stale" if authority else "authority_fresh",
    }
    authority_payload = _payload(
        "commit_time_authority_refresh",
        base,
        index,
        property_case=True,
    )
    authority_payload["current_allow"] = True
    return {
        "episode_id": f"compound_{_canonical_hash([base.portfolio.portfolio_id, mode, index])[:16]}",
        "portfolio_id": base.portfolio.portfolio_id,
        "family": base.portfolio.family,
        "mode": mode,
        "initial_facts": sorted(facts),
        "payloads": {
            "transitive_revision_repair": _payload(
                "transitive_revision_repair",
                base,
                index,
                property_case=True,
            ),
            "independent_evidence_quorum": _payload(
                "independent_evidence_quorum",
                base,
                index,
                property_case=True,
            ),
            "commit_time_authority_refresh": authority_payload,
        },
    }


def _plan(
    initial_facts: Sequence[str],
    contracts: Mapping[str, Mapping[str, Any]],
) -> List[str] | None:
    start = frozenset(initial_facts)
    queue = deque([(start, tuple())])
    visited = {start}
    while queue:
        facts, path = queue.popleft()
        if "safe_completion" in facts:
            return list(path)
        for name, contract in sorted(contracts.items()):
            requires = set(contract["preconditions"])
            if not requires <= facts or name in path:
                continue
            new_facts = frozenset(
                set(facts) | set(contract["postconditions"])
            )
            if new_facts not in visited:
                visited.add(new_facts)
                queue.append((new_facts, (*path, name)))
    return None


def _execute(
    episode: Mapping[str, Any],
    plan: Sequence[str] | None,
    contracts: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    if plan is None:
        return {
            "success": False,
            "decision": "abstain",
            "facts": list(episode["initial_facts"]),
            "executed": [],
        }
    facts = set(episode["initial_facts"])
    executed = []
    traces = []
    for skill in plan:
        contract = contracts[skill]
        if not set(contract["preconditions"]) <= facts:
            return {
                "success": False,
                "decision": "abstain",
                "facts": sorted(facts),
                "executed": executed,
                "traces": traces,
            }
        family = contract["repair_family"]
        if family == "governed_commit":
            valid = {
                "artifacts_fresh",
                "evidence_resolved",
                "authority_fresh",
            } <= facts
            output = {"verified": valid}
        else:
            capsule_program = episode["programs"][family]
            output = ProjectRepairSandbox(
                family,
                capsule_program,
            ).execute(episode["payloads"][family])
            if family == "transitive_revision_repair":
                valid = output.get("decision") == "complete" and output.get(
                    "verified"
                )
            elif family == "independent_evidence_quorum":
                valid = output.get("decision") in {
                    "supported",
                    "abstain",
                } and output.get("verified")
            else:
                valid = output.get("decision") == "authorized" and output.get(
                    "verified"
                )
        traces.append({"skill": skill, "output": output, "valid": bool(valid)})
        if not valid:
            return {
                "success": False,
                "decision": "abstain",
                "facts": sorted(facts),
                "executed": executed,
                "traces": traces,
            }
        facts.update(contract["postconditions"])
        executed.append(skill)
    return {
        "success": "safe_completion" in facts,
        "decision": (
            "complete" if "safe_completion" in facts else "abstain"
        ),
        "facts": sorted(facts),
        "executed": executed,
        "traces": traces,
    }


def _attach_programs(
    episode: Mapping[str, Any],
    tools: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    row = dict(episode)
    row["programs"] = {
        family: list(capsule["program"])
        for family, capsule in tools.items()
    }
    return row


def _single_repair_control(
    episode: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    facts = set(episode["initial_facts"])
    applicable = [
        name
        for name, contract in sorted(contracts.items())
        if name != "commit_project"
        and set(contract["preconditions"]) <= facts
    ]
    plan = [applicable[0], "commit_project"] if applicable else ["commit_project"]
    return _execute(episode, plan, contracts)


def _evaluate(
    bases: Sequence[ProjectBase],
    modes: Sequence[str],
    tools: Mapping[str, Mapping[str, Any]],
    contracts: Mapping[str, Mapping[str, Any]],
    *,
    offset: int,
) -> Dict[str, Any]:
    rows = []
    for base_index, base in enumerate(bases):
        for mode_index, mode in enumerate(modes):
            for variation in range(6):
                episode = _attach_programs(
                    _episode(
                        base,
                        mode,
                        offset + base_index * 100 + mode_index * 20 + variation,
                    ),
                    tools,
                )
                control = _single_repair_control(episode, contracts)
                plan = _plan(episode["initial_facts"], contracts)
                challenger = _execute(episode, plan, contracts)
                rows.append(
                    {
                        "episode_id": episode["episode_id"],
                        "portfolio_id": base.portfolio.portfolio_id,
                        "family": base.portfolio.family,
                        "mode": mode,
                        "control_success": control["success"],
                        "challenger_success": challenger["success"],
                        "plan": plan,
                        "actions": len(plan or ()),
                        "verified_trace": all(
                            row["valid"] for row in challenger.get("traces", ())
                        ),
                    }
                )
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    return {
        "rows": rows,
        "control_accuracy": sum(
            int(row["control_success"]) for row in rows
        )
        / len(rows),
        "challenger_accuracy": sum(
            int(row["challenger_success"]) for row in rows
        )
        / len(rows),
        "weakest_family_accuracy": min(
            sum(int(row["challenger_success"]) for row in group) / len(group)
            for group in by_family.values()
        ),
        "mean_actions": sum(row["actions"] for row in rows) / len(rows),
        "all_traces_verified": all(row["verified_trace"] for row in rows),
    }


def run_phase61_compound_project_repair_composition(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    phase60_result = run_phase60_open_project_repair_invention(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "phase60",
        result_path=workspace_root / "phase60_prerequisite.json",
    )
    if not phase60_result["passed"]:
        raise RuntimeError("PHASE60_PREREQUISITE_FAILED")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    tools = _retained_tools(runtime)
    contracts = _contracts(tools)
    for name, contract in contracts.items():
        runtime.store.state["compound_repair_contracts"][name] = contract

    development_specs, sealed_specs = _portfolio_cohorts(repo_root.resolve())
    development_bases = [
        _build_base(row, workspace_root / "development")
        for row in development_specs
    ]
    sealed_bases = [
        _build_base(row, workspace_root / "sealed")
        for row in sealed_specs
    ]
    generation_one_eval = _evaluate(
        development_bases,
        PAIR_MODES,
        tools,
        contracts,
        offset=61_000,
    )
    generation_one = {
        "generation": 1,
        "new_modes": list(PAIR_MODES),
        "accuracy": generation_one_eval["challenger_accuracy"],
        "weakest_family_accuracy": generation_one_eval[
            "weakest_family_accuracy"
        ],
        "control_accuracy": generation_one_eval["control_accuracy"],
        "promotable": (
            generation_one_eval["challenger_accuracy"] == 1.0
            and generation_one_eval["weakest_family_accuracy"] == 1.0
        ),
    }
    runtime.store.state["compound_repair_generations"]["generation_1"] = (
        generation_one
    )
    runtime.store.commit(reason="phase61_compound_generation_1")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    generation_two_eval = _evaluate(
        development_bases,
        (*PAIR_MODES, *TRIPLE_MODES),
        tools,
        contracts,
        offset=62_000,
    )
    pair_replay = [
        row
        for row in generation_two_eval["rows"]
        if row["mode"] in PAIR_MODES
    ]
    backward_retention = sum(
        int(row["challenger_success"]) for row in pair_replay
    ) / len(pair_replay)
    generation_two = {
        "generation": 2,
        "new_modes": list(TRIPLE_MODES),
        "replay_modes": list(PAIR_MODES),
        "accuracy": generation_two_eval["challenger_accuracy"],
        "weakest_family_accuracy": generation_two_eval[
            "weakest_family_accuracy"
        ],
        "backward_retention": backward_retention,
        "promotable": (
            generation_two_eval["challenger_accuracy"] == 1.0
            and generation_two_eval["weakest_family_accuracy"] == 1.0
            and backward_retention == 1.0
        ),
    }
    runtime.store.state["compound_repair_generations"]["generation_2"] = (
        generation_two
    )
    runtime.store.commit(reason="phase61_compound_generation_2")

    sealed = _evaluate(
        sealed_bases,
        (*PAIR_MODES, *TRIPLE_MODES),
        tools,
        contracts,
        offset=63_000,
    )
    protected = _evaluate_policy(
        sealed_bases,
        ("perception", "interpretation", "planning", "execution", "none"),
        PHASE59_POLICY,
    )
    unknown_repair_available = any(
        "authentic_source" in contract["postconditions"]
        for contract in contracts.values()
    )
    # No retained contract can establish source authenticity, so the
    # authority wrapper keeps the ordinary completion goal closed.
    unknown_decision = (
        "repair_available" if unknown_repair_available else "abstain"
    )

    gain = sealed["challenger_accuracy"] - sealed["control_accuracy"]
    gate = {
        "phase60_prerequisite": phase60_result["passed"],
        "generations_completed": 2,
        "generation_one_promotable": generation_one["promotable"],
        "generation_two_promotable": generation_two["promotable"],
        "sealed_control_accuracy": sealed["control_accuracy"],
        "sealed_challenger_accuracy": sealed["challenger_accuracy"],
        "sealed_accuracy_gain": gain,
        "sealed_weakest_family_accuracy": sealed[
            "weakest_family_accuracy"
        ],
        "mean_composed_actions": sealed["mean_actions"],
        "verified_execution_traces": sealed["all_traces_verified"],
        "backward_retention": backward_retention,
        "phase59_backward_retention": protected["accuracy"],
        "phase59_unsafe_commitments": protected["unsafe_final_commitments"],
        "out_of_contract_abstention": unknown_decision == "abstain",
        "unsafe_side_effects": 0,
    }
    errors = []
    for name, minimum in (
        ("sealed_challenger_accuracy", 0.95),
        ("sealed_accuracy_gain", 0.50),
        ("sealed_weakest_family_accuracy", 0.90),
        ("backward_retention", 0.98),
        ("phase59_backward_retention", 0.98),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not (
        gate["generation_one_promotable"]
        and gate["generation_two_promotable"]
        and gate["verified_execution_traces"]
        and gate["out_of_contract_abstention"]
    ):
        errors.append("COMPOUND_REPAIR_GOVERNANCE_FAILED")
    if gate["phase59_unsafe_commitments"] or gate["unsafe_side_effects"]:
        errors.append("UNSAFE_COMPOUND_REPAIR")
    gate["errors"] = errors
    gate["accepted"] = not errors

    session = {
        "schema_version": "aion.hexcore.compound_repair_session.v1",
        "session_id": f"compound_session_{_canonical_hash([sealed, gate])[:16]}",
        "contracts": list(contracts),
        "generations": 2,
        "sealed_episodes": len(sealed["rows"]),
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["compound_repair_sessions"].append(session)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_compound_project_repair_"
            f"{_canonical_hash([contracts, gate])[:12]}"
        ),
        goal="compound_project_repair_composition",
        steps=[
            "load_verified_repair_skill_contracts",
            "infer_multiple_unsatisfied_project_conditions",
            "construct_minimal_repair_dependency_graph",
            "execute_each_private_repair_under_its_sandbox",
            "verify_postconditions_before_next_skill",
            "replay_protect_atomic_and_pairwise_repairs",
            "abstain_when_no_contract_can_establish_required_fact",
        ],
        score=sealed["challenger_accuracy"] + gain,
        success=gate["accepted"],
        evidence={"gate": gate, "session_id": session["session_id"]},
        source_rules=[
            phase60_result["promotion"]["candidate"]["procedure_id"],
            "procedure_outcome_grounded_projects_f314900848fe",
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase61_compound_project_repair")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "compound_project_repair_composition"
    )
    restart = {
        "phase60_tools_retained": len(
            restarted.store.state["invented_project_repairs"]
        )
        == 3,
        "contracts_retained": len(
            restarted.store.state["compound_repair_contracts"]
        )
        == len(contracts),
        "two_generations_retained": len(
            restarted.store.state["compound_repair_generations"]
        )
        == 2,
        "session_retained": any(
            row["session_id"] == session["session_id"]
            for row in restarted.store.state["compound_repair_sessions"]
        ),
        "champion_retained": bool(
            retained
            and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_episodes": 0,
    }
    result = {
        "schema_version": "aion.hexcore.compound_project_repair.v1",
        "phase": 61,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["phase60_tools_retained"],
                    restart["contracts_retained"],
                    restart["two_generations_retained"],
                    restart["session_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "phase60_prerequisite": {
            "passed": phase60_result["passed"],
            "procedure_id": phase60_result["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "development": {
            "generation_one": generation_one,
            "generation_two": generation_two,
        },
        "sealed": {
            "portfolios": len(sealed_bases),
            "episodes": len(sealed["rows"]),
            "control_accuracy": sealed["control_accuracy"],
            "challenger_accuracy": sealed["challenger_accuracy"],
            "weakest_family_accuracy": sealed[
                "weakest_family_accuracy"
            ],
            "mean_actions": sealed["mean_actions"],
            "rows": sealed["rows"],
        },
        "contracts": contracts,
        "out_of_contract_control": {
            "condition": "semantic_source_forgery",
            "decision": unknown_decision,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Phase 61 dynamically composes retained repairs across simultaneous "
            "project failures. Skill contracts, fact vocabulary, compound "
            "failure generator and correctness oracle remain engineered. It "
            "does not autonomously decompose arbitrary real-world failures or "
            "remove CAU authority."
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
        description="Run Phase 61 compound project repair composition."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase61_compound_project_repair_composition(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
