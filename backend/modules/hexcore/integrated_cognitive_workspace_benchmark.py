from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from backend.modules.hexcore.executable_knowledge_grounding_benchmark import (
    ManualDocument,
    _active_program,
    _ground_document,
    _render,
    _verification_cases,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.relational_program_induction_benchmark import (
    ProgramHypothesis,
    State,
    _predict,
)
from backend.modules.hexcore.tool_grounded_task_learning_benchmark import (
    ToolTask,
    _cold_attempt,
    _learned_attempt,
)


TOOL_CONTRACTS = {
    "numeric_expression": "arithmetic",
    "logical_clauses": "logic",
    "statistical_series": "data",
    "photon_ir": "photon",
}


@dataclass(frozen=True)
class WorkspaceTask:
    task_id: str
    domain: str
    hypothesis: ProgramHypothesis
    leading_state: Tuple[int, int]
    data_series: Tuple[int, ...]
    summary: str
    photon_expression: Dict[str, Any]
    stale_conflict: bool


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "integrated_workspace_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _summary(task: WorkspaceTask) -> int | float:
    if task.summary == "range":
        return max(task.data_series) - min(task.data_series)
    values = sorted(task.data_series)
    return values[len(values) // 2]


def _goal_result(
    task: WorkspaceTask,
    hypothesis: ProgramHypothesis,
) -> Dict[str, Any]:
    terminal = int(_summary(task))
    state: State = (*task.leading_state, terminal)
    authorized = _predict(hypothesis, state)
    if not authorized:
        return {
            "authorized": False,
            "state": list(state),
            "receipt": "withheld",
        }
    photon_task = ToolTask(
        task_id=f"{task.task_id}:photon",
        family="photon",
        instruction="Canonicalize authorized receipt.",
        payload={"photon_expression": task.photon_expression},
        expected=None,
    )
    receipt = _learned_attempt(photon_task, TOOL_CONTRACTS)["value"]
    return {
        "authorized": True,
        "state": list(state),
        "receipt": receipt,
    }


def _make_tasks(
    *,
    count: int,
    seed: int,
    cohort: str,
) -> List[WorkspaceTask]:
    rng = random.Random(seed)
    programs = (
        "sum_minus_tail_ge",
        "range_plus_tail_ge",
        "max_plus_tail_ge",
        "min_plus_tail_ge",
    )
    tasks = []
    for index in range(count):
        stale = index % 4 == 0
        if stale:
            program = "max_plus_tail_ge"
            threshold = 10
            leading = (5, 4)
            series = (0, 7, 3, 6, 1)
            summary = "range"
        else:
            program = programs[index % len(programs)]
            threshold = rng.randint(7, 14)
            leading = (rng.randint(1, 10), rng.randint(1, 10))
            series = tuple(rng.randint(0, 10) for _ in range(5))
            summary = "range" if index % 2 == 0 else "median"
        atom_a = f"{cohort}_signal_{index}"
        atom_b = f"{cohort}_proof_{index}"
        tasks.append(
            WorkspaceTask(
                task_id=f"{cohort}_workspace_{index:03d}",
                domain=f"{cohort}_domain_{index:03d}",
                hypothesis=(program, threshold),
                leading_state=leading,
                data_series=series,
                summary=summary,
                photon_expression={
                    "op": "⊕",
                    "states": [
                        atom_b,
                        {"op": "∅"},
                        {"op": "⊕", "states": [atom_a, atom_b]},
                        atom_a,
                    ],
                },
                stale_conflict=stale,
            )
        )
    return tasks


def _install_task_knowledge(
    runtime: HexCorePersistentLearningRuntime,
    task: WorkspaceTask,
    *,
    index: int,
) -> Dict[str, Any]:
    program, threshold = task.hypothesis
    if task.stale_conflict:
        old_hypothesis = (program, threshold + 4)
        old = ManualDocument(
            document_id=f"{task.task_id}_manual_v1",
            domain=task.domain,
            source_uri=f"manual://workspace/{task.task_id}/v1",
            revision=1,
            text=_render(program, threshold + 4, index),
            true_hypothesis=old_hypothesis,
            verification_cases=_verification_cases(
                old_hypothesis,
                arity=3,
                seed=201_000 + index,
            ),
        )
        _ground_document(runtime, old)
    current = ManualDocument(
        document_id=f"{task.task_id}_manual_v2",
        domain=task.domain,
        source_uri=f"manual://workspace/{task.task_id}/v2",
        revision=2,
        text=_render(program, threshold, index + 1),
        true_hypothesis=task.hypothesis,
        verification_cases=_verification_cases(
            task.hypothesis,
            arity=3,
            seed=211_000 + index,
        ),
    )
    grounded = _ground_document(runtime, current)
    return {
        "grounded": grounded,
        "active": _active_program(runtime, task.domain),
    }


def _oldest_program(
    runtime: HexCorePersistentLearningRuntime,
    domain: str,
) -> Dict[str, Any] | None:
    rows = [
        row
        for row in runtime.store.state["executable_knowledge"].values()
        if row.get("domain") == domain
    ]
    rows.sort(key=lambda row: int(row["revision"]))
    return rows[0] if rows else None


def _isolated_control(
    runtime: HexCorePersistentLearningRuntime,
    task: WorkspaceTask,
) -> Dict[str, Any]:
    program = _oldest_program(runtime, task.domain)
    data_task = ToolTask(
        task_id=f"{task.task_id}:data_control",
        family="data",
        instruction="Summarize sensor data.",
        payload={
            "data_series": list(task.data_series),
            "summary": task.summary,
        },
        expected=_summary(task),
    )
    data = _cold_attempt(data_task)
    photon_task = ToolTask(
        task_id=f"{task.task_id}:photon_control",
        family="photon",
        instruction="Canonicalize receipt.",
        payload={"photon_expression": task.photon_expression},
        expected=None,
    )
    photon = _cold_attempt(photon_task)
    state = (*task.leading_state, int(data["value"]))
    authorized = bool(
        program and _predict(tuple(program["hypothesis"]), state)
    )
    result = {
        "authorized": authorized,
        "state": list(state),
        "receipt": photon["value"] if authorized else "withheld",
    }
    return {
        "result": result,
        "cost": 1 + data["attempts"] + photon["attempts"] + 1,
        "program_revision": program["revision"] if program else None,
    }


def _workspace_step(
    runtime: HexCorePersistentLearningRuntime,
    task: WorkspaceTask,
    *,
    interrupt_after_data: bool,
) -> Dict[str, Any]:
    session = runtime.store.state["workspace_sessions"].setdefault(
        task.task_id,
        {
            "schema_version": "aion.hexcore.workspace_session.v1",
            "task_id": task.task_id,
            "domain": task.domain,
            "status": "active",
            "completed_steps": [],
            "artifacts": {},
            "trace": [],
            "created_at": _utc_timestamp(),
        },
    )
    completed = session["completed_steps"]
    artifacts = session["artifacts"]

    if "retrieve_active_rule" not in completed:
        active = _active_program(runtime, task.domain)
        claim = runtime.knowledge.query_claim(
            task.domain,
            "executable_program",
        )
        artifacts["program"] = active
        artifacts["knowledge_claim"] = claim["claim"]
        session["trace"].append(
            {
                "step": "retrieve_active_rule",
                "revision": active["revision"] if active else None,
                "source_uri": active["source_uri"] if active else None,
            }
        )
        completed.append("retrieve_active_rule")

    if "summarize_data" not in completed:
        data_task = ToolTask(
            task_id=f"{task.task_id}:data",
            family="data",
            instruction="Summarize sensor data.",
            payload={
                "data_series": list(task.data_series),
                "summary": task.summary,
            },
            expected=_summary(task),
        )
        data = _learned_attempt(data_task, TOOL_CONTRACTS)
        artifacts["summary"] = data["value"]
        artifacts["data_trace"] = data["trace"]
        session["trace"].append(
            {
                "step": "summarize_data",
                "tool": data["tool"],
                "attempts": data["attempts"],
            }
        )
        completed.append("summarize_data")
        runtime.store.commit(reason=f"workspace_checkpoint:{task.task_id}")
        if interrupt_after_data:
            return {
                "interrupted": True,
                "session_id": task.task_id,
            }

    if "evaluate_guard" not in completed:
        state: State = (
            *task.leading_state,
            int(artifacts["summary"]),
        )
        hypothesis = tuple(artifacts["program"]["hypothesis"])
        authorized = _predict(hypothesis, state)
        artifacts["state"] = list(state)
        artifacts["authorized"] = authorized
        session["trace"].append(
            {
                "step": "evaluate_guard",
                "program_id": artifacts["program"]["program_id"],
                "authorized": authorized,
            }
        )
        completed.append("evaluate_guard")

    if artifacts["authorized"] and "canonicalize_receipt" not in completed:
        photon_task = ToolTask(
            task_id=f"{task.task_id}:photon",
            family="photon",
            instruction="Canonicalize authorized receipt.",
            payload={"photon_expression": task.photon_expression},
            expected=None,
        )
        photon = _learned_attempt(photon_task, TOOL_CONTRACTS)
        artifacts["receipt"] = photon["value"]
        artifacts["photon_trace"] = photon["trace"]
        session["trace"].append(
            {
                "step": "canonicalize_receipt",
                "tool": photon["tool"],
                "attempts": photon["attempts"],
            }
        )
        completed.append("canonicalize_receipt")
    elif not artifacts["authorized"]:
        artifacts["receipt"] = "withheld"

    if "verify_goal" not in completed:
        artifacts["result"] = {
            "authorized": artifacts["authorized"],
            "state": artifacts["state"],
            "receipt": artifacts["receipt"],
        }
        session["trace"].append(
            {
                "step": "verify_goal",
                "outcome_hash": _canonical_hash(artifacts["result"]),
            }
        )
        completed.append("verify_goal")
        session["status"] = "complete"
        session["completed_at"] = _utc_timestamp()
        runtime.store.state["workspace_outcomes"].append(
            {
                "task_id": task.task_id,
                "success": True,
                "result_hash": _canonical_hash(artifacts["result"]),
                "program_id": artifacts["program"]["program_id"],
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"workspace_complete:{task.task_id}")

    tool_attempts = sum(
        row.get("attempts", 0)
        for row in session["trace"]
        if row["step"] in {"summarize_data", "canonicalize_receipt"}
    )
    return {
        "interrupted": False,
        "result": artifacts["result"],
        "cost": 1 + tool_attempts + 1,
        "session": session,
        "program_revision": artifacts["program"]["revision"],
        "provenance_complete": bool(
            artifacts["program"].get("source_uri")
            and artifacts["program"].get("capsule_checksum")
            and artifacts["knowledge_claim"].get("evidence_ids")
            and all(
                row.get("input_hash")
                and row.get("output_hash")
                and row.get("verification")
                for trace_name in ("data_trace", "photon_trace")
                for row in artifacts.get(trace_name, [])
                if row.get("accepted")
            )
        ),
    }


def run_integrated_cognitive_workspace_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_tasks: int = 16,
    sealed_tasks: int = 64,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase32_id = "procedure_tool_grounded_0e0527d8822a"
    runtime.store.state["tool_skills"] = {
        fingerprint: {
            "fingerprint": fingerprint,
            "tool": tool,
            "status": "promoted_dependency",
            "procedure_id": phase32_id,
        }
        for fingerprint, tool in TOOL_CONTRACTS.items()
    }
    runtime.store.commit(reason="load_phase32_tool_skills")
    baseline = ProcedureCandidate(
        procedure_id=phase32_id,
        goal="integrated_cognitive_workspace",
        steps=["isolated_component_execution"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase32_isolated_parent"},
    )
    runtime.skills.promote(baseline)

    development_rows = _make_tasks(
        count=development_tasks,
        seed=171_001,
        cohort="development",
    )
    for index, task in enumerate(development_rows):
        _install_task_knowledge(runtime, task, index=index)
        _workspace_step(
            runtime,
            task,
            interrupt_after_data=False,
        )

    sealed_rows = []
    interruptions = 0
    resumed = 0
    for index, task in enumerate(
        _make_tasks(
            count=sealed_tasks,
            seed=181_901,
            cohort="sealed",
        )
    ):
        _install_task_knowledge(runtime, task, index=1000 + index)
        expected = _goal_result(task, task.hypothesis)
        control = _isolated_control(runtime, task)
        interrupt = index % 3 == 0
        first = _workspace_step(
            runtime,
            task,
            interrupt_after_data=interrupt,
        )
        if first["interrupted"]:
            interruptions += 1
            runtime = HexCorePersistentLearningRuntime(
                state_path=state_path,
                authority_provider=_allow,
            )
            workspace = _workspace_step(
                runtime,
                task,
                interrupt_after_data=False,
            )
            resumed += int(not workspace["interrupted"])
        else:
            workspace = first
        sealed_rows.append(
            {
                "task_id": task.task_id,
                "stale_conflict": task.stale_conflict,
                "expected": expected,
                "control": control,
                "workspace": workspace,
                "workspace_correct": workspace["result"] == expected,
                "control_correct": control["result"] == expected,
            }
        )

    workspace_accuracy = sum(
        int(row["workspace_correct"]) for row in sealed_rows
    ) / len(sealed_rows)
    control_accuracy = sum(
        int(row["control_correct"]) for row in sealed_rows
    ) / len(sealed_rows)
    workspace_cost = sum(
        row["workspace"]["cost"] for row in sealed_rows
    ) / len(sealed_rows)
    control_cost = sum(row["control"]["cost"] for row in sealed_rows) / len(
        sealed_rows
    )
    conflict_rows = [row for row in sealed_rows if row["stale_conflict"]]
    gate = {
        "accuracy": workspace_accuracy,
        "isolated_control_accuracy": control_accuracy,
        "accuracy_gain": workspace_accuracy - control_accuracy,
        "weakest_conflict_accuracy": sum(
            int(row["workspace_correct"]) for row in conflict_rows
        )
        / len(conflict_rows),
        "conflict_recovery_gain": (
            sum(int(row["workspace_correct"]) for row in conflict_rows)
            - sum(int(row["control_correct"]) for row in conflict_rows)
        )
        / len(conflict_rows),
        "workspace_mean_cost": workspace_cost,
        "control_mean_cost": control_cost,
        "cost_reduction": 1.0 - workspace_cost / control_cost,
        "interruptions": interruptions,
        "successful_resumptions": resumed,
        "provenance_complete": sum(
            int(row["workspace"]["provenance_complete"])
            for row in sealed_rows
        )
        / len(sealed_rows),
    }
    errors = []
    if gate["accuracy"] < 1.0:
        errors.append("WORKSPACE_ACCURACY_NOT_EXACT")
    if gate["accuracy_gain"] <= 0.0:
        errors.append("NO_GAIN_OVER_ISOLATED_COMPONENTS")
    if gate["weakest_conflict_accuracy"] < 1.0:
        errors.append("CONFLICT_RECOVERY_REGRESSED")
    if gate["cost_reduction"] <= 0.0:
        errors.append("WORKSPACE_COST_NOT_REDUCED")
    if gate["successful_resumptions"] != gate["interruptions"]:
        errors.append("INTERRUPTED_SESSION_NOT_RESUMED")
    if gate["provenance_complete"] < 1.0:
        errors.append("WORKSPACE_PROVENANCE_INCOMPLETE")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate_record = {
        "gate": gate,
        "phase32_dependency": phase32_id,
        "workspace_components": [
            "knowledge_memory",
            "executable_program_memory",
            "tool_skill_memory",
            "working_session_memory",
            "outcome_memory",
        ],
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_integrated_workspace_"
            + _canonical_hash(candidate_record)[:12]
        ),
        goal="integrated_cognitive_workspace",
        steps=[
            "retrieve_active_provenance_bearing_rule",
            "execute_required_data_skill",
            "evaluate_program_guard",
            "conditionally_execute_photon_skill",
            "verify_goal_and_record_outcome",
            "checkpoint_and_resume_across_restart",
        ],
        score=1.0 + gate["accuracy_gain"] + gate["cost_reduction"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase33_integrated_workspace_sealed",
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
    runtime.store.commit(reason="phase33_integrated_workspace")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    sealed_ids = {row["task_id"] for row in sealed_rows}
    restart = {
        "all_sessions_retained": all(
            task_id in restarted.store.state["workspace_sessions"]
            and restarted.store.state["workspace_sessions"][task_id][
                "status"
            ]
            == "complete"
            for task_id in sealed_ids
        ),
        "outcomes_retained": all(
            task_id
            in {
                row["task_id"]
                for row in restarted.store.state["workspace_outcomes"]
            }
            for task_id in sealed_ids
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "integrated_cognitive_workspace"
            )
            == candidate.procedure_id
        ),
        "phase32_dependency_retained": all(
            fingerprint in restarted.store.state["tool_skills"]
            for fingerprint in TOOL_CONTRACTS
        ),
        "relearning_tasks": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["all_sessions_retained"]
        and restart["outcomes_retained"]
        and restart["champion_retained"]
        and restart["phase32_dependency_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.integrated_cognitive_workspace.v1",
        "benchmark": "persistent_multi_memory_workspace",
        "passed": passed,
        "gate": gate,
        "sealed": {
            "tasks": len(sealed_rows),
            "rows": sealed_rows,
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION integrated five persistent memory types on bounded typed "
            "workflows. Task schemas, tools and dependency structure remained "
            "engineered; this is not an unrestricted global workspace or "
            "open-ended autonomous project execution."
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
        description="Run HexCore integrated cognitive-workspace benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-tasks", type=int, default=16)
    parser.add_argument("--sealed-tasks", type=int, default=64)
    args = parser.parse_args()
    result = run_integrated_cognitive_workspace_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_tasks=args.development_tasks,
        sealed_tasks=args.sealed_tasks,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
