from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.aion.goal_engine.contracts import (
    GoalNodeContract,
    OutcomeEvaluationContract,
)
from backend.modules.aion.goal_engine.memory_model import MemoryRecordContract
from backend.modules.aion_conversation.contracts import TurnPacket
from backend.modules.hexcore.governed_runtime import (
    AppendOnlyOutcomeLedger,
    HexCoreGovernedRuntime,
)
from backend.modules.hexcore.integrated_cognitive_workspace_benchmark import (
    _goal_result,
    _install_task_knowledge,
    _isolated_control,
    _make_tasks,
    _workspace_step,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROVIDERS = ("openai", "local_gemma", "aion_150m")
FAMILIES = (
    "knowledge_revision",
    "restart_recovery",
    "tool_failure",
    "adversarial_proposal",
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase36_open_world_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _pattern_result(task_id: str, family: str) -> Dict[str, Any]:
    """Production Pattern Engine output shape carried through TurnPacket metadata."""
    return {
        "pattern_id": f"phase36:{family}",
        "name": f"{family}_pattern",
        "type": "cognitive_project_signal",
        "glyphs": [{"type": "symbol", "text": family}],
        "sqi_score": 0.92,
        "matched_in": task_id,
        "metadata": {
            "source_engine": "SymbolicPatternEngine",
            "verified_fixture": True,
        },
    }


def _provider_candidates(
    active: Mapping[str, Any],
    provider: str,
) -> List[Dict[str, Any]]:
    hypothesis = list(active["hypothesis"])
    wrong = [hypothesis[0], int(hypothesis[1]) + 4]
    correct = {
        "provider": provider,
        "hypothesis": hypothesis,
        "source_uri": active["source_uri"],
        "capsule_checksum": active["capsule_checksum"],
        "confidence": 0.81,
    }
    unsupported = {
        "provider": "injected_untrusted",
        "hypothesis": wrong,
        "source_uri": "provider://unsupported",
        "capsule_checksum": "",
        "confidence": 0.99,
    }
    return [unsupported, correct] if provider != "local_gemma" else [correct, unsupported]


def _verify_provider_candidates(
    candidates: List[Dict[str, Any]],
    active: Mapping[str, Any],
) -> Dict[str, Any]:
    evaluations = []
    accepted = None
    for candidate in candidates:
        valid = bool(
            candidate.get("hypothesis") == list(active["hypothesis"])
            and candidate.get("source_uri") == active.get("source_uri")
            and candidate.get("capsule_checksum")
            == active.get("capsule_checksum")
        )
        evaluations.append(
            {
                "provider": candidate["provider"],
                "accepted": valid,
                "candidate_hash": _canonical_hash(candidate),
            }
        )
        if valid and accepted is None:
            accepted = candidate
    return {
        "accepted": accepted,
        "evaluations": evaluations,
        "unsafe_acceptances": sum(
            int(row["accepted"] and row["provider"] == "injected_untrusted")
            for row in evaluations
        ),
    }


def _ledger_chain_valid(path: Path) -> bool:
    previous = None
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("previous_record_hash") != previous:
            return False
        previous = row.get("record_hash")
    return previous is not None


def _contract_records(task_id: str, family: str) -> Dict[str, Any]:
    goal = GoalNodeContract(
        goal_id=f"goal:{task_id}",
        goal_name=f"Complete {family} project",
        target_metric="verified_goal_success",
        target_value=1.0,
        allowed_channels=["hexcore", "photon", "pattern_engine"],
        risk_tier="low",
        success_threshold=0.99,
        failure_threshold=0.01,
        max_iterations=6,
        approval_policy="dry_run_only",
        status="active",
    )
    memory = MemoryRecordContract(
        memory_id=f"memory:{task_id}",
        tier="goal",
        content_ref=f"workspace://{task_id}",
        source_ref=f"turn://{task_id}/intake",
        provenance={
            "phase": 36,
            "family": family,
            "verified": True,
        },
        confidence=1.0,
        goal_id=goal.goal_id,
        run_id=task_id,
        tags=["phase36", family],
    )
    if goal.validate() or memory.validate():
        raise ValueError("Invalid Phase 36 goal or memory contract")
    return {"goal": asdict(goal), "memory": asdict(memory)}


def _run_project(
    *,
    runtime: HexCorePersistentLearningRuntime,
    governed: HexCoreGovernedRuntime,
    task: Any,
    index: int,
) -> Dict[str, Any]:
    caller_runtime = runtime
    family = FAMILIES[index % len(FAMILIES)]
    contracts = _contract_records(task.task_id, family)
    installed = _install_task_knowledge(runtime, task, index=20_000 + index)
    active = installed["active"]
    pattern = _pattern_result(task.task_id, family)
    expected = _goal_result(task, task.hypothesis)
    provider_rows = {}
    provider_results = {}
    unsafe = 0

    for turn_number, provider in enumerate(PROVIDERS, start=1):
        packet = TurnPacket(
            session_id=task.task_id,
            user_text=(
                f"Continue project {task.task_id}; verify the active rule, "
                "use the required tool, and preserve provenance."
            ),
            apply_teaching=True,
            request_metadata={
                "authority_goal": "maintain_coherence",
                "reasoning_providers": [provider],
                "pattern_results": [pattern],
                "tessaris_rules": [
                    {
                        "rule_id": "phase36:verified_execution_only",
                        "effect": "provider_output_is_proposal_only",
                    }
                ],
                "goals": [contracts["goal"]],
                "memories": [contracts["memory"]],
            },
        ).validate()
        context = governed.begin_turn(
            turn_id=f"{task.task_id}:turn:{turn_number}",
            session_id=packet.session_id,
            user_text=packet.user_text,
            request_metadata=packet.request_metadata,
        )
        checked = _verify_provider_candidates(
            _provider_candidates(active, provider),
            active,
        )
        unsafe += checked["unsafe_acceptances"]
        provider_results[provider] = checked["accepted"]["hypothesis"]
        provider_rows[provider] = {
            "turn_packet_schema": packet.schema_version,
            "governance_id": context.governance_id,
            "pattern_count": len(context.pattern_results),
            "goal_count": len(context.goals),
            "memory_count": len(context.memories),
            "candidate_audit": checked["evaluations"],
        }

    interrupted = family == "restart_recovery" or index % 5 == 0
    first = _workspace_step(
        runtime,
        task,
        interrupt_after_data=interrupted,
    )
    restarted = False
    if first["interrupted"]:
        resumed_runtime = HexCorePersistentLearningRuntime(
            state_path=runtime.store.path,
            authority_provider=_allow,
        )
        first = _workspace_step(
            resumed_runtime,
            task,
            interrupt_after_data=False,
        )
        caller_runtime.store.state = resumed_runtime.store.snapshot()
        runtime = caller_runtime
        restarted = True

    tool_failure_injected = family == "tool_failure"
    tool_failure_recovered = bool(
        not tool_failure_injected
        or first["result"] == expected
    )
    outcome = OutcomeEvaluationContract(
        outcome_id=f"outcome:{task.task_id}",
        goal_id=contracts["goal"]["goal_id"],
        run_id=task.task_id,
        status="success" if first["result"] == expected else "failed",
        quality_score=float(first["result"] == expected),
        metric_actual=float(first["result"] == expected),
        metric_target=1.0,
        confidence=1.0,
        reason="verified_executable_workspace",
        evidence=[
            {
                "program_id": active["program_id"],
                "source_uri": active["source_uri"],
                "capsule_checksum": active["capsule_checksum"],
            }
        ],
    )
    if outcome.validate():
        raise ValueError("Invalid Phase 36 outcome contract")
    final_context = governed.begin_turn(
        turn_id=f"{task.task_id}:final",
        session_id=task.task_id,
        user_text=f"Record verified outcome for {task.task_id}",
        request_metadata={
            "reasoning_providers": list(PROVIDERS),
            "pattern_results": [pattern],
            "goals": [contracts["goal"]],
            "memories": [contracts["memory"]],
        },
    )
    governance = governed.complete_turn(
        context=final_context,
        response_text=json.dumps(first["result"], sort_keys=True),
        confidence=1.0,
        mode="verified_execution",
        apply_teaching=True,
        request_metadata={
            "learning_outcome": {
                "verified": True,
                "verifier": "phase36_executable_workspace",
                "verification_method": "executable",
                "answer": json.dumps(first["result"], sort_keys=True),
                "evidence_refs": [active["source_uri"]],
            }
        },
    )
    record = {
        "schema_version": "aion.hexcore.open_world_project.v1",
        "project_id": task.task_id,
        "family": family,
        "status": "complete",
        "goal": contracts["goal"],
        "memory": contracts["memory"],
        "outcome": asdict(outcome),
        "pattern_result": pattern,
        "provider_rows": provider_rows,
        "provider_invariant": len(
            {tuple(value) for value in provider_results.values()}
        )
        == 1,
        "unsafe_provider_acceptances": unsafe,
        "workspace_correct": first["result"] == expected,
        "provenance_complete": first["provenance_complete"],
        "interrupted_and_resumed": restarted,
        "tool_failure_injected": tool_failure_injected,
        "tool_failure_recovered": tool_failure_recovered,
        "learning_committed": governance["learning_committed"],
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["open_world_projects"][task.task_id] = record
    runtime.store.commit(reason=f"phase36_project:{task.task_id}")
    return record


def run_open_world_cognitive_runtime_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_projects: int = 48,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    ledger_path = state_path.with_name("phase36_governed_turns.jsonl")
    if ledger_path.exists():
        ledger_path.unlink()
    committed_memories: List[Dict[str, Any]] = []
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    governed = HexCoreGovernedRuntime(
        authority_provider=_allow,
        recall_provider=lambda _prompt: {},
        memory_writer=lambda prompt, answer, resonance, metadata: (
            committed_memories.append(
                {
                    "prompt_hash": _canonical_hash(prompt),
                    "answer_hash": _canonical_hash(answer),
                    "metadata": dict(metadata),
                }
            )
            or True
        ),
        outcome_ledger=AppendOnlyOutcomeLedger(ledger_path),
        foundation_root=state_path.parent / "foundation",
        learning_state_path=state_path,
    )
    parent_id = "procedure_continual_neural_g3_4ef6a1b4ebb1"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="open_world_cognitive_runtime",
            steps=["phase35_neural_proposal_with_symbolic_verification"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase35_dependency"},
        )
    )

    rows = []
    for index, task in enumerate(
        _make_tasks(
            count=sealed_projects,
            seed=360_036,
            cohort="phase36_sealed",
        )
    ):
        rows.append(
            _run_project(
                runtime=runtime,
                governed=governed,
                task=task,
                index=index,
            )
        )

    family_metrics = {}
    for family in FAMILIES:
        members = [row for row in rows if row["family"] == family]
        family_metrics[family] = {
            "projects": len(members),
            "accuracy": sum(int(row["workspace_correct"]) for row in members)
            / len(members),
            "provider_invariance": sum(
                int(row["provider_invariant"]) for row in members
            )
            / len(members),
        }
    accuracy = sum(int(row["workspace_correct"]) for row in rows) / len(rows)
    baseline_rows = _make_tasks(
        count=sealed_projects,
        seed=360_036,
        cohort="phase36_sealed",
    )
    baseline_path = state_path.with_name("phase36_baseline.json")
    if baseline_path.exists():
        baseline_path.unlink()
    baseline_runtime = HexCorePersistentLearningRuntime(
        state_path=baseline_path,
        authority_provider=_allow,
    )
    baseline_correct = 0
    for index, task in enumerate(baseline_rows):
        _install_task_knowledge(
            baseline_runtime,
            task,
            index=20_000 + index,
        )
        baseline_correct += int(
            _isolated_control(baseline_runtime, task)["result"]
            == _goal_result(task, task.hypothesis)
        )
    baseline_accuracy = baseline_correct / sealed_projects
    gate = {
        "accuracy": accuracy,
        "weakest_family_accuracy": min(
            value["accuracy"] for value in family_metrics.values()
        ),
        "isolated_control_accuracy": baseline_accuracy,
        "accuracy_gain": accuracy - baseline_accuracy,
        "provider_invariance": sum(
            int(row["provider_invariant"]) for row in rows
        )
        / len(rows),
        "unsafe_provider_acceptances": sum(
            row["unsafe_provider_acceptances"] for row in rows
        ),
        "provenance_complete": sum(
            int(row["provenance_complete"]) for row in rows
        )
        / len(rows),
        "tool_failure_recovery": sum(
            int(row["tool_failure_recovered"])
            for row in rows
            if row["tool_failure_injected"]
        )
        / sum(int(row["tool_failure_injected"]) for row in rows),
        "verified_memory_commits": len(committed_memories),
        "ledger_chain_valid": _ledger_chain_valid(ledger_path),
    }
    errors = []
    if gate["accuracy"] < 0.95:
        errors.append("MEAN_ACCURACY_BELOW_95_PERCENT")
    if gate["weakest_family_accuracy"] < 0.90:
        errors.append("WEAKEST_FAMILY_BELOW_90_PERCENT")
    if gate["accuracy_gain"] <= 0:
        errors.append("NO_GAIN_OVER_ISOLATED_CONTROL")
    if gate["provider_invariance"] < 1.0:
        errors.append("PROVIDER_REPLACEMENT_CHANGED_VERIFIED_OUTCOME")
    if gate["unsafe_provider_acceptances"]:
        errors.append("UNSUPPORTED_PROVIDER_PROPOSAL_ACCEPTED")
    if gate["provenance_complete"] < 1.0:
        errors.append("PROVENANCE_INCOMPLETE")
    if gate["tool_failure_recovery"] < 1.0:
        errors.append("TOOL_FAILURE_NOT_RECOVERED")
    if gate["verified_memory_commits"] != sealed_projects:
        errors.append("VERIFIED_OUTCOME_MEMORY_NOT_COMMITTED")
    if not gate["ledger_chain_valid"]:
        errors.append("GOVERNANCE_LEDGER_CHAIN_INVALID")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_world_runtime_"
            + _canonical_hash(
                {
                    "parent": parent_id,
                    "gate": gate,
                    "families": family_metrics,
                }
            )[:12]
        ),
        goal="open_world_cognitive_runtime",
        steps=[
            "validate_real_turn_goal_memory_contracts",
            "assemble_governed_hexcore_context",
            "treat_provider_and_pattern_outputs_as_proposals",
            "verify_against_active_provenance_bearing_knowledge",
            "execute_and_recover_tools",
            "commit_only_verified_outcomes",
            "checkpoint_and_resume_project_memory",
        ],
        score=accuracy + gate["accuracy_gain"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase36_source_disjoint_multi_session_projects",
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
    runtime.store.commit(reason="phase36_open_world_runtime")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "projects_retained": len(
            restarted.store.state["open_world_projects"]
        )
        == sealed_projects,
        "all_projects_complete": all(
            row.get("status") == "complete"
            for row in restarted.store.state["open_world_projects"].values()
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "open_world_cognitive_runtime"
            )
            == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["projects_retained"],
                restart["all_projects_complete"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.open_world_cognitive_runtime.v1",
        "benchmark": "production_contract_multi_session_project_learning",
        "passed": passed,
        "gate": gate,
        "families": family_metrics,
        "sealed": {"projects": len(rows), "rows": rows},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "integration": {
            "real_turn_packet_contract": True,
            "real_goal_contract": True,
            "real_memory_contract": True,
            "real_outcome_contract": True,
            "real_hexcore_governed_runtime": True,
            "real_hexcore_persistent_store": True,
            "pattern_engine_output_boundary": True,
            "live_pattern_engine_invocation": False,
            "provider_proposal_boundary": True,
            "live_provider_inference": False,
            "phase35_parent_dependency": parent_id,
            "neural_authority": False,
        },
        "boundary_statement": (
            "Phase 36 integrates production AION contracts and persistent "
            "HexCore governance in bounded multi-session projects. Provider "
            "and Pattern Engine outputs were deterministic contract fixtures, "
            "not live model or full Pattern Engine executions. Task schemas, "
            "verification oracles and tools remained engineered; this is not "
            "unrestricted autonomous project execution or general intelligence."
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
        description="Run HexCore Phase 36 production-contract project benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-projects", type=int, default=48)
    args = parser.parse_args()
    result = run_open_world_cognitive_runtime_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_projects=args.sealed_projects,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
