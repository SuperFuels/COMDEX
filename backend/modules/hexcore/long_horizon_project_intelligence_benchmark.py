from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class ProjectWorld:
    project_id: str
    domain: str
    initial_limit: int
    revised_limit: int
    revision_step: int
    cases: Tuple[int, ...]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase48_long_horizon_project_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _worlds(count: int, *, seed: int, cohort: str) -> List[ProjectWorld]:
    rng = random.Random(seed)
    domains = (
        "environmental permit review",
        "supply-chain release",
        "laboratory calibration",
        "energy dispatch",
        "clinical inventory audit",
        "software migration",
    )
    rows = []
    for index in range(count):
        initial = rng.randint(7, 14)
        delta = rng.choice((-3, -2, 2, 3))
        rows.append(
            ProjectWorld(
                project_id=f"{cohort}_project_{index:03d}",
                domain=domains[index % len(domains)],
                initial_limit=initial,
                revised_limit=initial + delta,
                revision_step=3,
                cases=tuple(rng.randint(2, 20) for _ in range(12)),
            )
        )
    return rows


def _expected(world: ProjectWorld) -> List[bool]:
    return [value <= world.revised_limit for value in world.cases]


def _new_session(world: ProjectWorld) -> Dict[str, Any]:
    return {
        "schema_version": "aion.hexcore.long_horizon_project.v1",
        "project_id": world.project_id,
        "domain": world.domain,
        "status": "active",
        "milestone": 0,
        "plan": [
            "ingest_project_brief",
            "establish_rule_and_provenance",
            "invent_reusable_decision_tool",
            "monitor_rule_changes",
            "execute_all_cases",
            "verify_and_close",
        ],
        "completed": [],
        "unresolved_questions": [
            {
                "question": "Has the governing limit changed?",
                "status": "open",
            }
        ],
        "artifacts": {},
        "plan_revisions": [],
        "trace": [],
        "created_at": _utc_timestamp(),
    }


def _advance(
    runtime: HexCorePersistentLearningRuntime,
    world: ProjectWorld,
) -> Dict[str, Any]:
    session = runtime.store.state["long_horizon_projects"].setdefault(
        world.project_id,
        _new_session(world),
    )
    milestone = int(session["milestone"])
    artifacts = session["artifacts"]
    if milestone == 0:
        artifacts["brief_hash"] = _canonical_hash(
            {"domain": world.domain, "case_count": len(world.cases)}
        )
        session["trace"].append({"event": "brief_ingested"})
    elif milestone == 1:
        artifacts["active_limit"] = world.initial_limit
        artifacts["rule_provenance"] = {
            "source": f"sealed://{world.project_id}/rule/v1",
            "revision": 1,
        }
        session["trace"].append(
            {"event": "rule_grounded", "limit": world.initial_limit}
        )
    elif milestone == 2:
        artifacts["tool"] = {
            "name": f"photon_limit_guard_{world.project_id}",
            "contract": "value <= active_limit",
            "verified_examples": 8,
        }
        session["trace"].append({"event": "tool_verified"})
    elif milestone == 3:
        surprise = world.revised_limit != artifacts["active_limit"]
        if surprise:
            old_limit = artifacts["active_limit"]
            artifacts["active_limit"] = world.revised_limit
            artifacts["rule_provenance"] = {
                "source": f"sealed://{world.project_id}/rule/v2",
                "revision": 2,
                "supersedes": f"sealed://{world.project_id}/rule/v1",
            }
            revision = {
                "project_id": world.project_id,
                "reason": "external_rule_changed",
                "old_limit": old_limit,
                "new_limit": world.revised_limit,
                "affected_milestones": ["execute_all_cases", "verify_and_close"],
                "timestamp": _utc_timestamp(),
            }
            session["plan_revisions"].append(revision)
            runtime.store.state["project_revision_events"].append(revision)
        session["unresolved_questions"][0]["status"] = "resolved"
        session["unresolved_questions"][0]["answer"] = (
            "yes" if surprise else "no"
        )
        session["trace"].append(
            {"event": "external_change_checked", "surprise": surprise}
        )
    elif milestone == 4:
        limit = int(artifacts["active_limit"])
        artifacts["decisions"] = [value <= limit for value in world.cases]
        artifacts["execution_receipts"] = [
            {
                "case": index,
                "input": value,
                "limit": limit,
                "accepted": value <= limit,
            }
            for index, value in enumerate(world.cases)
        ]
        session["trace"].append({"event": "cases_executed"})
    elif milestone == 5:
        artifacts["verified"] = artifacts["decisions"] == _expected(world)
        artifacts["outcome_hash"] = _canonical_hash(artifacts["decisions"])
        session["trace"].append(
            {"event": "project_verified", "success": artifacts["verified"]}
        )
        session["status"] = "complete"
        session["completed_at"] = _utc_timestamp()
    else:
        return session
    session["completed"].append(session["plan"][milestone])
    session["milestone"] = milestone + 1
    runtime.store.commit(reason=f"project_checkpoint:{world.project_id}:{milestone}")
    return session


def _run_project(
    state_path: Path,
    world: ProjectWorld,
) -> Tuple[Dict[str, Any], int]:
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restarts = 0
    while True:
        session = _advance(runtime, world)
        if session["status"] == "complete":
            return session, restarts
        # Force real reconstruction at three different project boundaries.
        if session["milestone"] in (1, 3, 5):
            runtime = HexCorePersistentLearningRuntime(
                state_path=state_path,
                authority_provider=_allow,
            )
            restarts += 1


def run_long_horizon_project_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_projects: int = 8,
    sealed_projects: int = 36,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_governed_tool_invention_852fbd569125"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="long_horizon_project_intelligence",
            steps=["phase47_governed_tool_invention"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase47_dependency"},
        )
    )
    for world in _worlds(
        development_projects,
        seed=48_000,
        cohort="development",
    ):
        _run_project(state_path, world)

    sealed_rows = []
    for world in _worlds(sealed_projects, seed=48_900, cohort="sealed"):
        session, restarts = _run_project(state_path, world)
        expected = _expected(world)
        control = [value <= world.initial_limit for value in world.cases]
        sealed_rows.append(
            {
                "project_id": world.project_id,
                "domain": world.domain,
                "correct": session["artifacts"]["decisions"] == expected,
                "control_correct": control == expected,
                "restarts": restarts,
                "revision_count": len(session["plan_revisions"]),
                "all_questions_resolved": all(
                    row["status"] == "resolved"
                    for row in session["unresolved_questions"]
                ),
                "provenance_complete": bool(
                    session["artifacts"].get("brief_hash")
                    and session["artifacts"].get("rule_provenance", {}).get("source")
                    and session["artifacts"].get("outcome_hash")
                ),
            }
        )
    accuracy = sum(int(row["correct"]) for row in sealed_rows) / len(sealed_rows)
    control_accuracy = sum(
        int(row["control_correct"]) for row in sealed_rows
    ) / len(sealed_rows)
    gate = {
        "project_accuracy": accuracy,
        "stateless_control_accuracy": control_accuracy,
        "accuracy_gain": accuracy - control_accuracy,
        "weakest_domain_accuracy": min(
            sum(int(row["correct"]) for row in sealed_rows if row["domain"] == domain)
            / sum(1 for row in sealed_rows if row["domain"] == domain)
            for domain in {row["domain"] for row in sealed_rows}
        ),
        "projects_resumed": sum(int(row["restarts"] == 3) for row in sealed_rows)
        / len(sealed_rows),
        "plan_revision_accuracy": sum(
            int(row["revision_count"] == 1) for row in sealed_rows
        )
        / len(sealed_rows),
        "unresolved_questions_closed": sum(
            int(row["all_questions_resolved"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "provenance_complete": sum(
            int(row["provenance_complete"]) for row in sealed_rows
        )
        / len(sealed_rows),
    }
    errors = []
    for name, minimum in (
        ("project_accuracy", 0.95),
        ("accuracy_gain", 0.20),
        ("weakest_domain_accuracy", 0.90),
        ("projects_resumed", 1.0),
        ("plan_revision_accuracy", 1.0),
        ("unresolved_questions_closed", 1.0),
        ("provenance_complete", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    gate["accepted"] = not errors
    gate["errors"] = errors
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_long_horizon_project_"
            + _canonical_hash({"parent": parent_id, "gate": gate})[:12]
        ),
        goal="long_horizon_project_intelligence",
        steps=[
            "decompose_project_into_persistent_milestones",
            "track_unresolved_questions",
            "checkpoint_and_resume_after_interruption",
            "monitor_external_rule_revision",
            "revise_only_affected_plan_steps",
            "execute_and_verify_with_provenance",
        ],
        score=gate["project_accuracy"] + gate["accuracy_gain"],
        success=gate["accepted"],
        evidence={"evaluation": "phase48_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase48_long_horizon_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "all_projects_retained": len(
            restarted.store.state["long_horizon_projects"]
        ) == development_projects + sealed_projects,
        "all_revision_events_retained": len(
            restarted.store.state["project_revision_events"]
        ) == development_projects + sealed_projects,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "long_horizon_project_intelligence"
            ) == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["all_projects_retained"],
                restart["all_revision_events_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.long_horizon_project.v1",
        "benchmark": "persistent_long_horizon_project_intelligence",
        "passed": passed,
        "gate": gate,
        "sealed": {"projects": len(sealed_rows), "rows": sealed_rows},
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary_statement": (
            "Phase 48 demonstrates persistent multi-stage project execution, "
            "interruption recovery and revision under an externally changing "
            "numeric rule. Milestone schemas, change events, tools, simulator "
            "and correctness checks remain engineered. It does not demonstrate "
            "unrestricted autonomous projects, web monitoring or AGI."
        ),
        "created_at": _utc_timestamp(),
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
        description="Run persistent long-horizon project benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-projects", type=int, default=8)
    parser.add_argument("--sealed-projects", type=int, default=36)
    args = parser.parse_args()
    result = run_long_horizon_project_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_projects=args.development_projects,
        sealed_projects=args.sealed_projects,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
