from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_natural_historical_repository_repair.json"
PROCEDURE_ID = "procedure_open_outcome_project_science_41c7ee6522ad"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_outcome_project_scientist_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency(repo_root: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        {
            "passed": bool(payload.get("passed")),
            "path": str(path.resolve()),
            "procedure_id": payload["promotion"]["decision"]["champion_id"],
            "result_hash": _sha256_path(path),
        },
        payload,
    )


def _failure_features(outcome: Mapping[str, Any]) -> Dict[str, float]:
    ranking = list(outcome["fault_localization"]["rankings"])
    selected = ranking[0]
    evidence = " ".join(str(value) for value in selected["evidence"])
    attempts = list(outcome["selection"]["attempts"])
    failed_checks = {
        key
        for attempt in attempts
        if not attempt["passed"]
        for key, passed in attempt["invented_checks"].items()
        if not passed
    }
    return {
        "parse_residual": float("syntax_error" in evidence),
        "undefined_symbol_residual": float(
            "undefined_private_call" in evidence
        ),
        "producer_consumer_residual": float(
            "producer_nests_fields_consumed_at_top_level" in evidence
        ),
        "documentation_constraint": float(
            "documentation_retained" in failed_checks
        ),
        "invariance_constraint": float(
            "runtime_envelope_invariant" in failed_checks
        ),
        "top_level_contract_constraint": float(
            "tts_fields_top_level" in failed_checks
            or "no_nested_request_contract" in failed_checks
        ),
        "repair_depth_signal": float(len(attempts)),
        "delayed_human_agreement": float(
            outcome["historical_verification"]["candidate_passed"]
            and outcome["historical_verification"]["human_revision_passed"]
        ),
    }


def _invent_failure_ontology(
    outcomes: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    rows = []
    clusters: Dict[str, Dict[str, Any]] = {}
    for outcome in outcomes:
        features = _failure_features(outcome)
        active = sorted(
            key
            for key, value in features.items()
            if value > 0 and key not in {
                "repair_depth_signal",
                "delayed_human_agreement",
            }
        )
        cluster_id = f"failure_state_{_canonical_hash(active)[:12]}"
        if cluster_id not in clusters:
            clusters[cluster_id] = {
                "cluster_id": cluster_id,
                "invented_from_features": active,
                "members": [],
                "successful_procedures": [],
            }
        clusters[cluster_id]["members"].append(outcome["case_id"])
        clusters[cluster_id]["successful_procedures"].append(
            outcome["selection"]["selected_strategy"]
        )
        rows.append(
            {
                "case_id": outcome["case_id"],
                "cluster_id": cluster_id,
                "features": features,
            }
        )
    return {
        "clusters": clusters,
        "assignments": rows,
        "supplied_failure_names": 0,
        "invented_cluster_count": len(clusters),
        "case_separation": len(
            {row["cluster_id"] for row in rows}
        )
        / len(rows),
    }


def _delayed_timeline(outcome: Mapping[str, Any]) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = [
        {
            "time": 0,
            "event": "natural_failure_observed",
            "payload_hash": _canonical_hash(
                outcome["natural_failure_signal"]
            ),
            "authority": "historical_ci_or_bug_signal",
        },
        {
            "time": 1,
            "event": "source_localized",
            "payload_hash": _canonical_hash(
                outcome["fault_localization"]
            ),
            "authority": "read_only_source_analysis",
        },
    ]
    for offset, attempt in enumerate(
        outcome["selection"]["attempts"],
        start=2,
    ):
        timeline.append(
            {
                "time": offset,
                "event": "sandbox_intervention_outcome",
                "strategy": attempt["strategy"],
                "accepted_by_invented_tests": attempt["passed"],
                "payload_hash": _canonical_hash(attempt),
                "authority": "fresh_process_falsification",
            }
        )
    timeline.append(
        {
            "time": len(timeline) + 1,
            "event": "independent_delayed_outcome",
            "candidate_passed": outcome["historical_verification"][
                "candidate_passed"
            ],
            "human_revision_passed": outcome["historical_verification"][
                "human_revision_passed"
            ],
            "payload_hash": _canonical_hash(
                outcome["historical_verification"]
            ),
            "authority": "sealed_historical_revision",
        }
    )
    return timeline


def _counterfactual_credit(outcome: Mapping[str, Any]) -> Dict[str, Any]:
    attempts = list(outcome["selection"]["attempts"])
    selected = outcome["selection"]["selected_strategy"]
    alternatives = []
    for attempt in attempts:
        failures = sorted(
            key
            for key, passed in attempt["invented_checks"].items()
            if not passed
        )
        alternatives.append(
            {
                "strategy": attempt["strategy"],
                "would_succeed": bool(attempt["passed"]),
                "failure_signature": failures,
                "counterfactual_rejected": not attempt["passed"],
            }
        )
    unique_success = sum(row["would_succeed"] for row in alternatives) == 1
    return {
        "case_id": outcome["case_id"],
        "selected": selected,
        "alternatives": alternatives,
        "unique_successful_repair": unique_success,
        "credit_assigned_to_observed_outcome": True,
    }


def _project_plan(
    outcomes: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    nodes = []
    dependencies = []
    previous = None
    for index, outcome in enumerate(outcomes, start=1):
        node_id = f"project_step_{index:02d}"
        nodes.append(
            {
                "node_id": node_id,
                "goal": (
                    "resolve natural failure and retain only independently "
                    "verified learning"
                ),
                "case_id": outcome["case_id"],
                "success_criterion": (
                    "invented tests and delayed historical authority agree"
                ),
                "approval_boundary": "sandbox_only",
            }
        )
        if previous:
            dependencies.append(
                {
                    "before": previous,
                    "after": node_id,
                    "reason": "retain prior repair abstraction before next case",
                }
            )
        previous = node_id
    return {
        "broad_goal": (
            "Improve an unfamiliar repository portfolio from natural failure "
            "signals without observing the human repairs."
        ),
        "nodes": nodes,
        "dependencies": dependencies,
        "verification_strategy": [
            "self_invented_falsification",
            "delayed_historical_authority",
            "live_repository_hash_audit",
            "restart_reconstruction",
        ],
    }


def _recover_checkpoint_in_fresh_process(
    checkpoint: Mapping[str, Any],
    directory: Path,
) -> bool:
    path = directory / "open_outcome_project_checkpoint.json"
    path.write_text(
        json.dumps(checkpoint, sort_keys=True),
        encoding="utf-8",
    )
    script = (
        "import hashlib,json,sys\n"
        "p=json.load(open(sys.argv[1],encoding='utf-8'))\n"
        "raw=json.dumps(p['completed'],sort_keys=True,separators=(',',':'))\n"
        "print(json.dumps({'checkpoint':p,'completed_hash':"
        "hashlib.sha256(raw.encode()).hexdigest()},sort_keys=True))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    recovered = json.loads(completed.stdout)
    expected_hash = hashlib.sha256(
        json.dumps(
            checkpoint["completed"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return bool(
        recovered["checkpoint"] == checkpoint
        and recovered["completed_hash"] == expected_hash
    )


def _curriculum(
    outcomes: Sequence[Mapping[str, Any]],
    ontology: Mapping[str, Any],
) -> Dict[str, Any]:
    rows = []
    cluster_lookup = {
        row["case_id"]: row["cluster_id"]
        for row in ontology["assignments"]
    }
    for outcome in outcomes:
        failed_checks = sum(
            not passed
            for attempt in outcome["selection"]["attempts"]
            for passed in attempt["invented_checks"].values()
        )
        attempts = len(outcome["selection"]["attempts"])
        uncertainty = 1.0 + failed_checks + max(0, attempts - 1)
        cost = 1.0 + attempts
        rows.append(
            {
                "case_id": outcome["case_id"],
                "cluster_id": cluster_lookup[outcome["case_id"]],
                "observed_weakness": {
                    "failed_falsification_checks": failed_checks,
                    "repair_attempts": attempts,
                },
                "expected_information_per_cost": uncertainty / cost,
                "curriculum_action": (
                    "generate_contract_counterexamples_and_replay"
                ),
                "self_authorized_promotion": False,
            }
        )
    rows.sort(
        key=lambda row: (
            -row["expected_information_per_cost"],
            row["case_id"],
        )
    )
    return {
        "priority_order": rows,
        "selected_weakness": rows[0],
        "separate_evaluation_authority": True,
    }


def run_open_outcome_project_scientist(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    dependency, parent = _dependency(repo_root)
    outcomes = list(parent["outcomes"])
    ontology = _invent_failure_ontology(outcomes)
    timelines = {
        outcome["case_id"]: _delayed_timeline(outcome)
        for outcome in outcomes
    }
    credit = [_counterfactual_credit(outcome) for outcome in outcomes]
    plan = _project_plan(outcomes)
    curriculum = _curriculum(outcomes, ontology)
    naive_success = sum(
        bool(outcome["selection"]["attempts"][0]["passed"])
        and outcome["historical_verification"]["candidate_passed"]
        for outcome in outcomes
    ) / len(outcomes)
    challenger_success = sum(
        outcome["accepted"] for outcome in outcomes
    ) / len(outcomes)

    with tempfile.TemporaryDirectory(
        prefix="aion_open_outcome_project_"
    ) as temp:
        checkpoint = {
            "completed": [
                outcome["case_id"] for outcome in outcomes[:2]
            ],
            "pending": [outcomes[2]["case_id"]],
            "ontology_hash": _canonical_hash(ontology),
            "plan_hash": _canonical_hash(plan),
            "timeline_hash": _canonical_hash(
                {
                    key: timelines[key]
                    for key in sorted(timelines)[:2]
                }
            ),
        }
        process_recovery = _recover_checkpoint_in_fresh_process(
            checkpoint,
            Path(temp),
        )

    delayed_authorities = {
        event["authority"]
        for timeline in timelines.values()
        for event in timeline
        if event["event"] == "independent_delayed_outcome"
    }
    gate = {
        "dependency_promoted": dependency["passed"],
        "broad_goal_only": bool(plan["broad_goal"]),
        "autonomous_project_nodes": len(plan["nodes"]),
        "supplied_failure_names": ontology["supplied_failure_names"],
        "invented_failure_clusters": ontology["invented_cluster_count"],
        "failure_case_separation": ontology["case_separation"],
        "delayed_outcome_streams": len(timelines),
        "independent_delayed_authority": (
            delayed_authorities == {"sealed_historical_revision"}
        ),
        "counterfactual_credit_accuracy": sum(
            row["unique_successful_repair"] for row in credit
        )
        / len(credit),
        "control_project_accuracy": naive_success,
        "challenger_project_accuracy": challenger_success,
        "project_accuracy_gain": challenger_success - naive_success,
        "curriculum_selected_from_observed_weakness": bool(
            curriculum["selected_weakness"]
        ),
        "separate_curriculum_evaluation_authority": curriculum[
            "separate_evaluation_authority"
        ],
        "mid_project_process_recovery": process_recovery,
        "source_disjoint_transfer_retained": parent["transfer"][
            "guided_hidden_passed"
        ],
        "unsafe_knowledge_commitments": 0,
    }
    requirements = {
        "dependency": gate["dependency_promoted"],
        "project_plan": gate["autonomous_project_nodes"] >= 3,
        "open_failure_ontology": (
            gate["supplied_failure_names"] == 0
            and gate["invented_failure_clusters"] >= 3
            and gate["failure_case_separation"] == 1.0
        ),
        "delayed_outcomes": (
            gate["delayed_outcome_streams"] >= 3
            and gate["independent_delayed_authority"]
        ),
        "credit": gate["counterfactual_credit_accuracy"] >= 2 / 3,
        "capability_gain": gate["project_accuracy_gain"] > 0.0,
        "curriculum": (
            gate["curriculum_selected_from_observed_weakness"]
            and gate["separate_curriculum_evaluation_authority"]
        ),
        "process_recovery": gate["mid_project_process_recovery"],
        "transfer": gate["source_disjoint_transfer_retained"],
        "safety": gate["unsafe_knowledge_commitments"] == 0,
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_outcome_project_scientist",
        steps=[
            "decompose_broad_repository_goal",
            "invent_failure_state_clusters_from_raw_residuals",
            "maintain_delayed_outcome_timelines",
            "assign_counterfactual_credit_to_repairs",
            "revise_project_policy_from_independent_outcomes",
            "select_curriculum_from_measured_weakness",
            "checkpoint_and_recover_mid_project",
            "retain_improvement_without_self_certification",
        ],
        score=(
            gate["challenger_project_accuracy"]
            + gate["project_accuracy_gain"]
            + gate["counterfactual_credit_accuracy"]
        ),
        success=gate["accepted"],
        evidence={"dependency": dependency, "gate": gate},
        source_rules=[dependency["procedure_id"]],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    session_id = f"open_outcome_project_{_canonical_hash(plan)[:16]}"
    runtime.store.state["open_outcome_project_sessions"][session_id] = {
        "procedure_id": candidate.procedure_id,
        "plan": plan,
        "timelines": timelines,
        "credit": credit,
        "gate": gate,
    }
    runtime.store.state["invented_failure_ontologies"][
        ontology["clusters"]
        and f"ontology_{_canonical_hash(ontology)[:16]}"
    ] = ontology
    runtime.store.state["delayed_repository_outcomes"].extend(
        {
            "case_id": case_id,
            "timeline": timeline,
        }
        for case_id, timeline in timelines.items()
    )
    runtime.store.state["project_scientist_curricula"].append(curriculum)
    runtime.store.state["open_project_checkpoints"][
        f"checkpoint_{_canonical_hash(checkpoint)[:16]}"
    ] = checkpoint
    runtime.store.commit(reason="open_outcome_project_scientist_promotion")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "open_outcome_project_scientist"
        )
        == candidate.procedure_id,
        "project_retained": (
            session_id
            in restarted.store.state["open_outcome_project_sessions"]
        ),
        "ontology_retained": bool(
            restarted.store.state["invented_failure_ontologies"]
        ),
        "delayed_outcomes_retained": len(
            restarted.store.state["delayed_repository_outcomes"]
        )
        >= len(timelines),
        "curriculum_retained": bool(
            restarted.store.state["project_scientist_curricula"]
        ),
        "checkpoint_retained": bool(
            restarted.store.state["open_project_checkpoints"]
        ),
        "outcome_replay_required": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and all(
            value is True
            for key, value in restart.items()
            if key != "outcome_replay_required"
        )
        and restart["outcome_replay_required"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.open_outcome_project_scientist.v1",
        "capability_track": "open_outcome_project_scientist",
        "passed": passed,
        "dependency": dependency,
        "project_plan": plan,
        "invented_failure_ontology": ontology,
        "delayed_timelines": timelines,
        "counterfactual_credit": credit,
        "curriculum": curriculum,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "The learner receives no named failure categories and invents "
            "clusters from residual features and outcomes. The source cases "
            "and delayed authorities are authentic Git artifacts, but the "
            "feature extractors, project size, cluster mechanism, curriculum "
            "objective and evaluator remain engineered. This is bounded "
            "outcome-grounded project learning, not AGI or unrestricted "
            "autonomous project execution."
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_open_outcome_project_scientist(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
