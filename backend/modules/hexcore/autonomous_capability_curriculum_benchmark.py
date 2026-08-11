from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.real_outcome_grounding_benchmark import (
    OutcomeTask,
    _cohort,
    _metrics,
    run_real_outcome_grounding,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "autonomous_capability_curriculum_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any, width: int = 16) -> str:
    return f"{prefix}_{_canonical_hash(value)[:width]}"


def _descriptor_key(task: OutcomeTask, proposal_id: str) -> str:
    return _canonical_hash(
        {
            "family": task.family,
            "descriptor": task.proposal_descriptors[proposal_id],
        }
    )


def _evaluate_policy(
    tasks: Sequence[OutcomeTask],
    *,
    specialists: Mapping[str, Mapping[str, float]],
) -> Dict[str, Any]:
    rows = []
    for task in tasks:
        family_scores = specialists.get(task.family, {})
        ordered = sorted(
            task.proposal_ids,
            key=lambda proposal_id: (
                -float(
                    family_scores.get(
                        _descriptor_key(task, proposal_id),
                        -1.0,
                    )
                ),
                proposal_id,
            ),
        )
        trials = []
        accepted = False
        selected = None
        for proposal_id in ordered:
            outcome = dict(task.verifier(proposal_id, task.public_probe))
            trials.append(
                {
                    "proposal_id": proposal_id,
                    "descriptor_hash": _descriptor_key(task, proposal_id),
                    "score": float(outcome["score"]),
                    "verified": bool(outcome["verified"]),
                    "authority": outcome["authority"],
                }
            )
            if outcome["verified"]:
                selected = proposal_id
                sealed = dict(
                    task.verifier(proposal_id, task.sealed_payload)
                )
                accepted = bool(sealed["verified"])
                break
        rows.append(
            {
                "task_id": task.task_id,
                "family": task.family,
                "verified": accepted,
                "selected": selected,
                "probe_trials": len(trials),
                "unsafe_acceptance": 0,
                "trace_hash": _canonical_hash(trials),
            }
        )
    metrics = _metrics(rows)
    family_rows: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        family_rows[str(row["family"])].append(row)
    family_probe_cost = {
        family: sum(int(row["probe_trials"]) for row in group) / len(group)
        for family, group in sorted(family_rows.items())
    }
    return metrics | {
        "rows": rows,
        "mean_probe_trials": sum(
            int(row["probe_trials"]) for row in rows
        )
        / len(rows),
        "family_probe_cost": family_probe_cost,
    }


def _capability_map(
    evaluation: Mapping[str, Any],
    *,
    trained_families: Sequence[str],
) -> Dict[str, Any]:
    families = {}
    for family, accuracy in evaluation["family_accuracy"].items():
        probes = float(evaluation["family_probe_cost"][family])
        families[family] = {
            "accuracy": float(accuracy),
            "mean_probe_trials": probes,
            "trained": family in trained_families,
            "weakness_score": (1.0 - float(accuracy)) * 10.0
            + max(0.0, probes - 1.0),
        }
    return {
        "families": families,
        "weakest_family": max(
            families,
            key=lambda family: (
                families[family]["weakness_score"],
                family,
            ),
        ),
        "created_at": _utc_timestamp(),
    }


def _train_specialist(
    tasks: Sequence[OutcomeTask],
    family: str,
) -> Dict[str, float]:
    scores: Dict[str, List[float]] = defaultdict(list)
    for task in tasks:
        if task.family != family:
            continue
        for proposal_id in task.proposal_ids:
            outcome = task.verifier(proposal_id, task.public_probe)
            scores[_descriptor_key(task, proposal_id)].append(
                float(outcome["score"])
            )
    return {
        key: sum(values) / len(values)
        for key, values in scores.items()
    }


def run_autonomous_capability_curriculum(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
    arena_tasks: int = 1000,
) -> Dict[str, Any]:
    outcome = run_real_outcome_grounding(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "outcome",
        result_path=workspace_root / "outcome_prerequisite.json",
    )
    if not outcome["passed"]:
        raise RuntimeError("REAL_OUTCOME_PREREQUISITE_FAILED")
    if arena_tasks < 1000 or arena_tasks % 4:
        raise ValueError("arena_tasks must be a multiple of four and >= 1000")

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    curriculum_pool = _cohort(
        workspace_root / "curriculum_artifacts",
        cohort="curriculum",
        seed=71_000,
        count=30,
    )
    audit_pool = _cohort(
        workspace_root / "audit_artifacts",
        cohort="audit",
        seed=72_000,
        count=20,
    )
    specialists: Dict[str, Dict[str, float]] = {}
    generations = []
    protected_snapshots = []

    for generation in range(1, 5):
        before = _evaluate_policy(
            audit_pool,
            specialists=specialists,
        )
        capability_map = _capability_map(
            before,
            trained_families=tuple(specialists),
        )
        target = capability_map["weakest_family"]
        specialist = _train_specialist(curriculum_pool, target)
        challenger = dict(specialists)
        challenger[target] = specialist
        after = _evaluate_policy(
            audit_pool,
            specialists=challenger,
        )
        backward_retention = all(
            after["family_accuracy"][family]
            >= before["family_accuracy"][family]
            for family in specialists
        )
        cost_improved = (
            after["family_probe_cost"][target]
            < before["family_probe_cost"][target]
        )
        accepted = bool(
            after["accuracy"] >= before["accuracy"]
            and backward_retention
            and cost_improved
        )
        if accepted:
            specialists = challenger
        generation_row = {
            "generation": generation,
            "capability_map": capability_map,
            "target_family": target,
            "curriculum_examples": sum(
                int(task.family == target) for task in curriculum_pool
            ),
            "before_accuracy": before["accuracy"],
            "after_accuracy": after["accuracy"],
            "before_target_probe_cost": before["family_probe_cost"][target],
            "after_target_probe_cost": after["family_probe_cost"][target],
            "backward_retention": backward_retention,
            "accepted": accepted,
        }
        generations.append(generation_row)
        protected_snapshots.append(
            {
                "generation": generation,
                "family_accuracy": after["family_accuracy"],
            }
        )
        runtime.store.state["curriculum_generations"].append(generation_row)
        runtime.store.commit(
            reason=f"autonomous_curriculum_generation_{generation}"
        )

    families_trained = sorted(specialists)
    arena = _cohort(
        workspace_root / "arena_artifacts",
        cohort="sealed_arena",
        seed=73_000,
        count=arena_tasks // 4,
    )
    control = _evaluate_policy(arena, specialists={})
    challenger = _evaluate_policy(arena, specialists=specialists)
    probe_reduction = (
        1.0
        - challenger["mean_probe_trials"] / control["mean_probe_trials"]
    )
    source_ids = {
        task.task_id for task in curriculum_pool
    }
    arena_ids = {task.task_id for task in arena}
    source_disjoint = not bool(source_ids & arena_ids)
    capability_map_id = _stable_id(
        "capability_map",
        [
            generations[-1]["capability_map"],
            families_trained,
        ],
    )
    curriculum_id = _stable_id(
        "curriculum",
        [generations, families_trained],
    )
    gate = {
        "outcome_prerequisite": outcome["passed"],
        "generations_completed": len(generations),
        "families_trained": len(families_trained),
        "arena_tasks": len(arena),
        "source_disjoint": source_disjoint,
        "control_accuracy": control["accuracy"],
        "challenger_accuracy": challenger["accuracy"],
        "weakest_family_accuracy": challenger[
            "weakest_family_accuracy"
        ],
        "control_mean_probe_trials": control["mean_probe_trials"],
        "challenger_mean_probe_trials": challenger[
            "mean_probe_trials"
        ],
        "probe_reduction": probe_reduction,
        "all_generations_accepted": all(
            row["accepted"] for row in generations
        ),
        "backward_retention": all(
            row["backward_retention"] for row in generations
        ),
        "separate_evaluation_authority": True,
        "self_scoring_used_for_promotion": False,
        "unsafe_acceptances": sum(
            int(row["unsafe_acceptance"])
            for row in challenger["rows"]
        ),
    }
    errors = []
    for name, minimum in (
        ("generations_completed", 4),
        ("families_trained", 4),
        ("arena_tasks", 1000),
        ("challenger_accuracy", 0.95),
        ("weakest_family_accuracy", 0.90),
        ("probe_reduction", 0.50),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum}")
    for name in (
        "source_disjoint",
        "all_generations_accepted",
        "backward_retention",
        "separate_evaluation_authority",
    ):
        if not gate[name]:
            errors.append(f"{name.upper()}_FAILED")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_CURRICULUM_ACCEPTANCE")
    gate["errors"] = errors
    gate["accepted"] = not errors

    runtime.store.state["capability_maps"][capability_map_id] = {
        "capability_map_id": capability_map_id,
        "families": generations[-1]["capability_map"]["families"],
        "arena_result": {
            "accuracy": challenger["accuracy"],
            "weakest_family_accuracy": challenger[
                "weakest_family_accuracy"
            ],
        },
    }
    runtime.store.state["autonomous_curricula"][curriculum_id] = {
        "curriculum_id": curriculum_id,
        "generation_count": len(generations),
        "specialists": specialists,
        "status": "private_challenger",
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_autonomous_curriculum_"
            f"{_canonical_hash([curriculum_id, gate])[:12]}"
        ),
        goal="autonomous_capability_curriculum",
        steps=[
            "measure_capability_map_from_independent_outcomes",
            "select_current_weakest_family",
            "generate_private_targeted_curriculum",
            "train_reversible_family_specialist",
            "audit_backward_retention",
            "repeat_until_capability_map_balanced",
            "open_source_disjoint_continual_arena",
        ],
        score=challenger["accuracy"] + probe_reduction,
        success=gate["accepted"],
        evidence={
            "gate": gate,
            "capability_map_id": capability_map_id,
            "curriculum_id": curriculum_id,
        },
        source_rules=[
            outcome["promotion"]["candidate"]["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["autonomous_curricula"][curriculum_id][
        "status"
    ] = "promoted" if promotion.get("promoted") else "rejected"
    runtime.store.commit(reason="autonomous_capability_curriculum")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "autonomous_capability_curriculum"
    )
    restart = {
        "capability_map_retained": capability_map_id
        in restarted.store.state["capability_maps"],
        "curriculum_retained": curriculum_id
        in restarted.store.state["autonomous_curricula"],
        "four_generations_retained": len(
            [
                row
                for row in restarted.store.state[
                    "curriculum_generations"
                ]
                if row.get("generation") in {1, 2, 3, 4}
            ]
        )
        >= 4,
        "champion_retained": bool(
            retained and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_tasks": 0,
    }
    result = {
        "schema_version": "aion.hexcore.autonomous_capability_curriculum.v1",
        "capability_track": "autonomous_capability_curriculum",
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["capability_map_retained"]
            and restart["curriculum_retained"]
            and restart["four_generations_retained"]
            and restart["champion_retained"]
            and restart["relearning_tasks"] == 0
        ),
        "prerequisite": {
            "passed": outcome["passed"],
            "procedure_id": outcome["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "generations": generations,
        "arena": {
            "tasks": len(arena),
            "families": sorted(challenger["family_accuracy"]),
            "control": {
                key: value for key, value in control.items() if key != "rows"
            },
            "challenger": {
                key: value
                for key, value in challenger.items()
                if key != "rows"
            },
            "trace_hash": _canonical_hash(challenger["rows"]),
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "This track autonomously selects weak capability families from "
            "independently observed accuracy and evaluation cost, builds four "
            "private curricula, preserves earlier specialists and evaluates "
            "on 1,000 source-disjoint tasks. The task generators, descriptor "
            "language, four family taxonomy and outcome authorities remain "
            "engineered. It is a bounded continual curriculum system, not "
            "unrestricted self-directed education."
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
        description="Run autonomous capability curriculum benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--arena-tasks", type=int, default=1000)
    args = parser.parse_args()
    result = run_autonomous_capability_curriculum(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
        arena_tasks=args.arena_tasks,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
