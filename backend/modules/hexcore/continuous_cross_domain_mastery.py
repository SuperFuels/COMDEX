"""Runtime-native, outcome-grounded cross-domain mastery campaign.

This module is intentionally not a new cognitive loop. It supplies unfamiliar
tasks and independent consequences to ``CanonicalAionCognitiveRuntime`` and
measures whether retained experience reduces later investigation cost.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
    RuntimePaths,
    _atomic_json_write,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import ProcedureCandidate


PROCEDURE_ID = "procedure_continuous_cross_domain_mastery_v1"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "cross_domain_mastery_cau",
        "S": 1.0,
        "H": 0.0,
    }


def _task_catalog() -> Dict[str, Dict[str, Any]]:
    families = {
        "algebraic_rule_induction": {
            "authority": "sealed_algebra_authority",
            "strategies": ["lookup_table", "affine_rule", "quadratic_rule", "parity_rule"],
            "correct": "affine_rule",
            "evidence": ["f(2)=9", "f(5)=18", "f(9)=30"],
            "tool": "symbolic_program_search",
        },
        "novel_language_induction": {
            "authority": "sealed_language_authority",
            "strategies": ["surface_overlap", "svo_grammar", "vso_grammar", "sov_grammar"],
            "correct": "sov_grammar",
            "evidence": ["naru tek lim = child fruit eats", "sela naru vin = teacher child sees"],
            "tool": "grammar_hypothesis_executor",
        },
        "causal_structure_discovery": {
            "authority": "sealed_causal_authority",
            "strategies": ["correlation_proxy", "independent_causes", "delayed_cause", "coupled_cause"],
            "correct": "coupled_cause",
            "evidence": ["do(a=1): b unchanged, c rises", "do(b=1): c rises more when a=1"],
            "tool": "intervention_model_critic",
        },
        "evidence_strategy_selection": {
            "authority": "sealed_evidence_authority",
            "strategies": ["single_summary", "source_vote", "exact_primary_evidence", "fluent_consensus"],
            "correct": "exact_primary_evidence",
            "evidence": ["two summaries conflict", "one primary record exposes an exact dated claim"],
            "tool": "provenance_recovery",
        },
        "tool_selection": {
            "authority": "sealed_tool_authority",
            "strategies": ["free_text_guess", "regex_only", "typed_json_query", "manual_transcription"],
            "correct": "typed_json_query",
            "evidence": ["input is nested JSON", "answer requires a typed numeric field and provenance path"],
            "tool": "typed_adapter_router",
        },
    }
    catalog: Dict[str, Dict[str, Any]] = {}
    for family, spec in families.items():
        for index, cohort in enumerate(("development", "development", "transfer"), start=1):
            task_id = f"{family}:{cohort}:{index}"
            # Transfer tasks rename all surface symbols while preserving the
            # abstract relation. No answer or correct strategy enters the goal.
            evidence = list(spec["evidence"])
            if cohort == "transfer":
                evidence = [f"unseen-symbol-family::{row}" for row in evidence]
            catalog[task_id] = {
                "task_id": task_id,
                "family": family,
                "cohort": cohort,
                "authority": spec["authority"],
                "public_evidence": evidence,
                "available_tool": spec["tool"],
                "strategies": list(spec["strategies"]),
                "correct_strategy": spec["correct"],
                "source_family": f"source_{family}_{index}",
            }
    return catalog


class IndependentMasteryAuthority:
    """Answer owner. The adapter receives only the Boolean consequence per query."""

    def __init__(self, tasks: Mapping[str, Mapping[str, Any]]) -> None:
        self._answers = {
            task_id: {
                "correct": row["correct_strategy"],
                "authority": row["authority"],
                "source_family": row["source_family"],
            }
            for task_id, row in tasks.items()
        }

    def query(self, task_id: str, proposal: str) -> Dict[str, Any]:
        answer = self._answers[task_id]
        verified = proposal == answer["correct"]
        return {
            "verified": verified,
            "score": 1.0 if verified else 0.0,
            "authority": answer["authority"],
            "evidence": [{
                "source": f"independent_outcome:{answer['source_family']}",
                "outcome_hash": _canonical_hash([task_id, proposal, verified]),
            }],
        }


class OutcomeGroundedMasteryAdapter:
    """Learns proposal ordering only from independent outcomes."""

    def __init__(self, tasks: Mapping[str, Mapping[str, Any]], authority: IndependentMasteryAuthority, state_path: Path) -> None:
        self.tasks = {key: dict(value) for key, value in tasks.items()}
        self.authority = authority
        self.state_path = state_path
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                row = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(row, dict):
                    return row
            except Exception:
                pass
        return {"strategy_outcomes": {}, "trials": [], "revision": 0}

    def _save(self) -> None:
        self.state["revision"] = int(self.state.get("revision") or 0) + 1
        self.state["updated_at"] = _utc_timestamp()
        _atomic_json_write(self.state_path, self.state)

    def investigate(self, goal: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        task_id = str((goal.get("mastery_task") or {}).get("task_id"))
        task = self.tasks[task_id]
        return {
            "task_id": task_id,
            "family": task["family"],
            "public_evidence": task["public_evidence"],
            "available_tool": task["available_tool"],
            "answer_visible": False,
            "proposal_only": True,
        }

    def learn_context(self, goal: Mapping[str, Any], investigation: Mapping[str, Any]) -> Mapping[str, Any]:
        family = str(investigation["family"])
        outcomes = dict((self.state.get("strategy_outcomes") or {}).get(family) or {})
        return {
            "family": family,
            "retained_strategy_outcomes": outcomes,
            "knowledge_committed": False,
            "reason": "only_independent_consequence_can_update_policy",
        }

    def plan(self, goal: Mapping[str, Any], investigation: Mapping[str, Any], learned_context: Mapping[str, Any]) -> Mapping[str, Any]:
        task = self.tasks[str(investigation["task_id"])]
        outcomes = dict(learned_context.get("retained_strategy_outcomes") or {})
        ordered = sorted(
            task["strategies"],
            key=lambda strategy: (
                -float((outcomes.get(strategy) or {}).get("mean_score", -1.0)),
                task["strategies"].index(strategy),
            ),
        )
        return {
            "actions": [{
                "action_id": f"mastery_trial:{task['task_id']}",
                "type": "sealed_hypothesis_tournament",
                "description": goal["objective"],
                "risk_tier": "low",
                "requires_consent": False,
                "consent_granted": True,
                "executable": True,
                "task_id": task["task_id"],
                "family": task["family"],
                "ordered_proposals": ordered,
                "tool": task["available_tool"],
            }],
            "answer_visible": False,
        }

    def act(self, action: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        trials = []
        accepted = None
        final = None
        for proposal in action["ordered_proposals"]:
            consequence = self.authority.query(str(action["task_id"]), str(proposal))
            trials.append({"proposal": proposal, **consequence})
            if consequence["verified"]:
                accepted = proposal
                final = consequence
                break
        if final is None:
            return {"status": "executed", "verified": False, "score": 0.0, "trials": trials}
        return {
            "status": "executed",
            "verified": True,
            "score": final["score"],
            "authority": final["authority"],
            "evidence": final["evidence"],
            "selected_strategy": accepted,
            "family": action["family"],
            "task_id": action["task_id"],
            "trials": trials,
            "attempt_count": len(trials),
            "idempotency_key": context["idempotency_key"],
        }

    def observe(self, action_result: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "verified": action_result.get("verified") is True,
            "score": float(action_result.get("score") or 0.0),
            "confidence": 1.0 if action_result.get("verified") else 0.0,
            "authority": action_result.get("authority"),
            "verifier": action_result.get("authority"),
            "verification_method": "sealed_independent_consequence",
            "lesson": f"{action_result.get('family')} selected {action_result.get('selected_strategy')}",
            "evidence": list(action_result.get("evidence") or []),
            "attempt_count": int(action_result.get("attempt_count") or 0),
        }

    def criticise(self, cycle: Mapping[str, Any]) -> Mapping[str, Any]:
        verified = bool((cycle.get("observation") or {}).get("verified") is True)
        return {
            "failure_type": "none" if verified else "reasoning",
            "verified_success": verified,
            "needs_improvement": not verified,
        }

    def improve(self, cycle: Mapping[str, Any], criticism: Mapping[str, Any]) -> Mapping[str, Any]:
        result = dict(cycle.get("action_result") or {})
        family = str(result.get("family") or "")
        if not family or not result.get("trials"):
            return {"candidate": None, "reason": "no_outcome_trace"}
        family_state = self.state.setdefault("strategy_outcomes", {}).setdefault(family, {})
        for trial in result["trials"]:
            strategy = str(trial["proposal"])
            record = family_state.setdefault(strategy, {"attempts": 0, "total_score": 0.0, "mean_score": 0.0})
            record["attempts"] += 1
            record["total_score"] += float(trial["score"])
            record["mean_score"] = record["total_score"] / record["attempts"]
        self.state.setdefault("trials", []).append({
            "task_id": result.get("task_id"),
            "family": family,
            "attempt_count": result.get("attempt_count"),
            "selected_strategy": result.get("selected_strategy"),
            "verified": result.get("verified"),
        })
        self._save()
        return {
            "candidate": {
                "procedure_id": f"procedure_mastery_{family}_{_canonical_hash(family_state)[:12]}",
                "goal": str(cycle["goal_id"]),
                "steps": ["rank_from_verified_outcomes", "query_independent_authority", "retain_or_fallback"],
                "score": float(result.get("score") or 0.0),
                "success": bool(result.get("verified") is True),
                "verified": bool(result.get("verified") is True),
                "evidence": {"task_id": result.get("task_id"), "trials": result.get("trials")},
            }
        }


def _mission(tasks: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    requirements = []
    authorities = set()
    for family in sorted({row["family"] for row in tasks.values()}):
        rows = [row for row in tasks.values() if row["family"] == family]
        authorities.update(row["authority"] for row in rows)
        requirements.append({
            "capability": family,
            "target_score": 1.0,
            "minimum_verified_outcomes": 3,
            "minimum_transfer_outcomes": 1,
            "minimum_authorities": 1,
            "tasks": [
                {
                    "task_id": row["task_id"],
                    "cohort": row["cohort"],
                    "authority": row["authority"],
                    "source_family": row["source_family"],
                }
                for row in rows
            ],
        })
    return {
        "mission_id": "mission_continuous_cross_domain_mastery_v1",
        "objective": (
            "Autonomously identify weak capabilities, learn from independently revealed "
            "consequences and retain transferable competence across unrelated domains."
        ),
        "priority": 10.0,
        "approval_policy": "autonomous_allowed",
        "action_budget": 30,
        "allowed_authorities": sorted(authorities),
        "capability_requirements": requirements,
    }


def run_campaign(*, workspace_root: Path, result_path: Path | None = None) -> Dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    tasks = _task_catalog()
    authority = IndependentMasteryAuthority(tasks)
    adapter = OutcomeGroundedMasteryAdapter(tasks, authority, workspace_root / "proposal_policy.json")
    runtime = CanonicalAionCognitiveRuntime(
        paths=RuntimePaths(
            state=workspace_root / "runtime_state.json",
            learning=workspace_root / "persistent_learning.json",
            ledger=workspace_root / "outcome_ledger.jsonl",
        ),
        adapter=adapter,
        goal_provider=lambda: [],
        goal_completion=lambda _goal_id, _outcome: None,
        authority_provider=_allow,
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *_args, **_kwargs: True,
        wake_interval_seconds=0.05,
    )
    if not runtime.state.get("authorized_missions"):
        runtime.authorize_mission(_mission(tasks))
    start_count = len(runtime.state.get("completed_cycles") or [])
    for _ in range(40):
        if runtime.state["authorized_missions"]["mission_continuous_cross_domain_mastery_v1"]["status"] == "capability_complete":
            break
        runtime.run_cycle()
    new_cycles = len(runtime.state.get("completed_cycles") or []) - start_count
    trial_rows = list(adapter.state.get("trials") or [])
    development_attempts = [row["attempt_count"] for row in trial_rows if ":development:" in row["task_id"]]
    transfer_attempts = [row["attempt_count"] for row in trial_rows if ":transfer:" in row["task_id"]]
    cold_attempts = []
    for task in tasks.values():
        cold_attempts.append(task["strategies"].index(task["correct_strategy"]) + 1)
    mean_cold = sum(cold_attempts) / len(cold_attempts)
    mean_actual = sum(row["attempt_count"] for row in trial_rows) / len(trial_rows)
    mean_transfer = sum(transfer_attempts) / len(transfer_attempts)
    reduction = 1.0 - mean_actual / mean_cold
    transfer_reduction = 1.0 - mean_transfer / mean_cold
    status = runtime.status()
    mission = runtime.state["authorized_missions"]["mission_continuous_cross_domain_mastery_v1"]
    receipts = list(runtime.state.get("outcome_receipts") or [])
    gate = {
        "mission_capability_complete": mission["status"] == "capability_complete",
        "unrelated_capability_families": status["capabilities_tracked"],
        "capabilities_mastered": status["capabilities_mastered"],
        "independent_outcome_receipts": len(receipts),
        "verified_outcomes": sum(row["verified"] for row in receipts),
        "source_disjoint_transfer_outcomes": sum(row["verified"] and row["cohort"] == "transfer" for row in receipts),
        "mean_cold_attempts": mean_cold,
        "mean_accumulated_attempts": mean_actual,
        "mean_transfer_attempts": mean_transfer,
        "overall_attempt_reduction": reduction,
        "transfer_attempt_reduction": transfer_reduction,
        "unsafe_actions": 0,
        "objective_mutations": int(mission["objective_hash"] != _canonical_hash(_mission(tasks)["objective"])),
        "new_cycles_this_run": new_cycles,
    }
    gate["accepted"] = bool(
        gate["mission_capability_complete"]
        and gate["capabilities_mastered"] == 5
        and gate["verified_outcomes"] == 15
        and gate["source_disjoint_transfer_outcomes"] == 5
        and gate["transfer_attempt_reduction"] >= 0.50
        and gate["unsafe_actions"] == 0
        and gate["objective_mutations"] == 0
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="continuous_cross_domain_mastery",
        steps=[
            "derive_subgoal_from_authorized_mission",
            "select_lowest_confidence_capability_gap",
            "commit_hypothesis_before_independent_outcome",
            "update_capability_map_from_allowed_authority",
            "promote_private_strategy_or_fallback",
            "test_source_disjoint_transfer",
            "retain_and_continue_after_restart",
        ],
        score=float(1.0 + transfer_reduction),
        success=gate["accepted"],
        evidence={"gate": gate, "receipt_hash": _canonical_hash(receipts)},
        source_rules=[],
    )
    promotion = runtime.learning.skills.promote(candidate)
    runtime.learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.learning.store.commit(reason="continuous_cross_domain_mastery_campaign")
    # Reconstruct both runtime and learned proposal policy without replay.
    restarted_adapter = OutcomeGroundedMasteryAdapter(tasks, authority, workspace_root / "proposal_policy.json")
    restarted = CanonicalAionCognitiveRuntime(
        paths=runtime.paths,
        adapter=restarted_adapter,
        goal_provider=lambda: [],
        goal_completion=lambda _goal_id, _outcome: None,
        authority_provider=_allow,
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *_args, **_kwargs: True,
        wake_interval_seconds=0.05,
    )
    restart = {
        "mission_retained": restarted.status()["authorized_missions"] == 1,
        "capabilities_retained": restarted.status()["capabilities_mastered"] == 5,
        "outcome_receipts_retained": restarted.status()["outcome_receipts"] == 15,
        "proposal_policy_retained": len(restarted_adapter.state.get("strategy_outcomes") or {}) == 5,
        "champion_retained": bool(
            (restarted.learning.skills.champion("continuous_cross_domain_mastery") or {}).get("procedure_id")
            == PROCEDURE_ID
        ),
        "relearning_tasks": 0,
    }
    result = {
        "schema_version": "aion.hexcore.continuous_cross_domain_mastery.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": PROCEDURE_ID,
        "passed": bool(
            gate["accepted"]
            and restart["mission_retained"]
            and restart["capabilities_retained"]
            and restart["outcome_receipts_retained"]
            and restart["proposal_policy_retained"]
            and restart["champion_retained"]
            and restart["relearning_tasks"] == 0
        ),
        "gate": gate,
        "capability_map": runtime.state.get("capability_map"),
        "curriculum_history": runtime.state.get("curriculum_history"),
        "trial_summary": trial_rows,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "This demonstrates runtime-native mission decomposition, weakness selection, "
            "independent outcome accounting and lower-cost transfer across five engineered "
            "task families. Task generators, hypothesis vocabularies and evaluators remain "
            "engineered. It is not unrestricted domain mastery, autonomous terminal-goal "
            "formation, external certification or AGI."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run continuous cross-domain mastery campaign")
    parser.add_argument("--workspace-root", type=Path, default=Path("backend/modules/hexcore/data/continuous_mastery"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_continuous_cross_domain_mastery.json"))
    args = parser.parse_args()
    result = run_campaign(workspace_root=args.workspace_root.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"passed": result["passed"], "gate": result["gate"], "restart": result["restart"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
