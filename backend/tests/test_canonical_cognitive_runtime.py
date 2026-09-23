from __future__ import annotations

import json
from pathlib import Path

from backend.AION.system.aion_heartbeat import SERVICES
from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
    RuntimePaths,
)


def _allow(goal: str):
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "canonical_runtime_test_cau",
    }


class VerifiedAdapter:
    def __init__(self, *, consent_required: bool = False):
        self.act_calls = 0
        self.consent_required = consent_required

    def investigate(self, goal, context):
        return {
            "known": [goal["objective"]],
            "recalled": context.get("recalled_knowledge", []),
            "unresolved_questions": ["which executable outcome proves success?"],
        }

    def learn_context(self, goal, investigation):
        return {
            "candidate_context_hash": "context-1",
            "knowledge_committed": False,
        }

    def plan(self, goal, investigation, learned_context):
        return {
            "actions": [
                {
                    "action_id": f"verify:{goal['goal_id']}",
                    "type": "executable_test",
                    "description": "run bounded verification",
                    "requires_consent": self.consent_required,
                    "consent_granted": False,
                    "executable": True,
                }
            ]
        }

    def act(self, action, context):
        self.act_calls += 1
        return {
            "status": "executed",
            "verified": True,
            "score": 1.0,
            "value": 42,
            "evidence": [{"id": "test:42", "source": "executable_test"}],
            "idempotency_key": context["idempotency_key"],
        }

    def observe(self, action_result, context):
        return {
            "verified": action_result.get("verified") is True,
            "score": action_result.get("score", 0.0),
            "confidence": 1.0,
            "verifier": "independent_test_executor",
            "verification_method": "executable",
            "lesson": "bounded verification returned 42",
            "evidence": action_result.get("evidence", []),
        }

    def criticise(self, cycle):
        return {
            "failure_type": "none",
            "verified_success": True,
            "needs_improvement": False,
        }

    def improve(self, cycle, criticism):
        return {
            "candidate": {
                "procedure_id": "procedure_canonical_runtime_test",
                "goal": cycle["goal_id"],
                "steps": ["investigate", "verify", "retain"],
                "score": 1.0,
                "success": True,
                "verified": True,
                "evidence": {"cycle_id": cycle["cycle_id"]},
            }
        }


class DelayedAdapter(VerifiedAdapter):
    def act(self, action, context):
        self.act_calls += 1
        return {
            "status": "awaiting_outcome",
            "outcome_token": "external:test:1",
            "idempotency_key": context["idempotency_key"],
        }


def _runtime(tmp_path: Path, adapter, goals, *, completions=None, writes=None):
    completions = completions if completions is not None else []
    writes = writes if writes is not None else []

    def writer(prompt, answer, resonance, metadata):
        writes.append(
            {
                "prompt": prompt,
                "answer": answer,
                "metadata": dict(metadata),
            }
        )
        return True

    return CanonicalAionCognitiveRuntime(
        paths=RuntimePaths(
            state=tmp_path / "state.json",
            learning=tmp_path / "learning.json",
            ledger=tmp_path / "ledger.jsonl",
        ),
        adapter=adapter,
        goal_provider=lambda: goals,
        goal_completion=lambda goal_id, outcome: completions.append(
            {"goal_id": goal_id, "outcome": dict(outcome)}
        ),
        authority_provider=_allow,
        recall_provider=lambda prompt: {
            "prompt": prompt,
            "answer": "retained context",
            "confidence": 0.9,
        },
        memory_writer=writer,
        wake_interval_seconds=0.05,
    )


def _goal(goal_id="goal-1", *, priority=1.0):
    return {
        "goal_id": goal_id,
        "name": f"Goal {goal_id}",
        "objective": "produce a verified outcome",
        "priority": priority,
        "approval_policy": "autonomous_allowed",
        "status": "active",
    }


def _ledger_chain_valid(path: Path) -> bool:
    previous = None
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("previous_record_hash") != previous:
            return False
        previous = row.get("record_hash")
    return previous is not None


def test_complete_cycle_connects_goal_action_learning_promotion_and_retention(tmp_path):
    adapter = VerifiedAdapter()
    completions = []
    writes = []
    runtime = _runtime(
        tmp_path,
        adapter,
        [_goal()],
        completions=completions,
        writes=writes,
    )

    status = runtime.run_cycle()

    assert status["completed_cycles"] == 1
    assert status["runtime_state"] == "idle"
    assert adapter.act_calls == 1
    assert completions[0]["goal_id"] == "goal-1"
    assert len(writes) == 1
    assert writes[0]["metadata"]["verified"] is True
    assert runtime.learning.skills.champion("goal-1")["procedure_id"] == "procedure_canonical_runtime_test"
    assert _ledger_chain_valid(tmp_path / "ledger.jsonl")
    completed = runtime.state["completed_cycles"][0]
    assert completed["verified"] is True
    assert completed["executive_method"] == "bounded_task"
    assert runtime.executive_skills.status()["verified_method_outcomes"] == 1
    assert runtime.executive_self.status()["mode"] == "work"
    assert runtime.state["metacognitive_history"][0]["outcome_reflection"]["cheap_noop"] is True

    restarted = _runtime(tmp_path, adapter, [], completions=completions, writes=writes)
    assert restarted.status()["completed_cycles"] == 1
    assert restarted.learning.skills.champion("goal-1")["procedure_id"] == "procedure_canonical_runtime_test"
    assert restarted.status()["executive_self"]["identity_immutable"] is True


def test_restart_resumes_same_cycle_before_action_without_duplicate_execution(tmp_path):
    adapter = VerifiedAdapter()
    runtime = _runtime(tmp_path, adapter, [_goal()])

    for _ in range(6):
        runtime.tick()
    before = runtime.status()
    assert before["active_stage"] == "act"
    cycle_id = before["active_cycle_id"]
    assert adapter.act_calls == 0

    restarted = _runtime(tmp_path, adapter, [_goal()])
    assert restarted.status()["active_cycle_id"] == cycle_id
    restarted.run_cycle()

    assert adapter.act_calls == 1
    assert restarted.status()["completed_cycles"] == 1


def test_restart_blocks_ambiguous_inflight_action_instead_of_reexecuting(tmp_path):
    adapter = VerifiedAdapter()
    runtime = _runtime(tmp_path, adapter, [_goal()])
    for _ in range(6):
        runtime.tick()
    runtime.state["active_cycle"]["action_commitment"]["execution_started"] = True
    runtime._checkpoint(event="test_simulated_process_loss_during_action")

    restarted = _runtime(tmp_path, adapter, [_goal()])
    restarted.run_cycle()

    assert adapter.act_calls == 0
    assert restarted.status()["completed_cycles"] == 1
    assert restarted.status()["failure_counts"]["interrupted_action"] == 1


def test_action_governance_denial_prevents_executor_and_records_authority_failure(tmp_path):
    adapter = VerifiedAdapter(consent_required=True)
    runtime = _runtime(tmp_path, adapter, [_goal()])

    runtime.run_cycle()

    assert adapter.act_calls == 0
    assert runtime.status()["failure_counts"]["authority"] == 1
    assert runtime.state["completed_cycles"][0]["status"] == "blocked"


def test_highest_priority_goal_is_selected_and_heartbeat_supervises_runtime(tmp_path):
    adapter = VerifiedAdapter()
    runtime = _runtime(
        tmp_path,
        adapter,
        [_goal("low", priority=1.0), _goal("high", priority=9.0)],
    )

    runtime.tick()

    assert runtime.status()["active_goal_id"] == "high"
    assert SERVICES["cognitive_runtime"].endswith("aion_cognitive_runtime_service.py")
    assert SERVICES["outcome_learning"].endswith("aion_real_outcome_learning_service.py")


def test_delayed_external_outcome_survives_restart_and_closes_cycle(tmp_path):
    adapter = DelayedAdapter()
    runtime = _runtime(tmp_path, adapter, [_goal()])

    runtime.run_cycle()

    assert runtime.status()["active_stage"] == "await_outcome"
    assert runtime.status()["pending_outcomes"] == 0
    assert adapter.act_calls == 1

    restarted = _runtime(tmp_path, adapter, [_goal()])
    restarted.submit_outcome(
        "external:test:1",
        {
            "status": "executed",
            "verified": True,
            "score": 1.0,
            "evidence": [{"id": "external:result:1", "source": "external_test"}],
        },
    )
    restarted.run_cycle()

    assert adapter.act_calls == 1
    assert restarted.status()["active_cycle_id"] is None
    assert restarted.status()["completed_cycles"] == 1


def test_open_mastery_compilation_is_proposal_only_until_explicit_authorization(tmp_path):
    runtime = _runtime(tmp_path, VerifiedAdapter(), [])
    proposal = runtime.compile_and_authorize_mastery_mission(
        mission_id="mission-open",
        objective="Learn Rust systems engineering and master accessible interface design",
        allowed_authorities=["sealed_compiler", "sealed_accessibility"],
    )
    assert proposal["status"] == "invented"
    assert proposal["authorized"] is False
    assert "mission-open" not in runtime.state["authorized_missions"]

    authorized = runtime.compile_and_authorize_mastery_mission(
        mission_id="mission-open",
        objective="Learn Rust systems engineering and master accessible interface design",
        allowed_authorities=["sealed_compiler", "sealed_accessibility"],
        authorize=True,
    )
    assert authorized["authorized"] is True
    assert "mission-open" in runtime.state["authorized_missions"]
    assert len(runtime.state["open_specialist_contracts"]["mission-open"]["contracts"]) == 9


class MissionMasteryAdapter(VerifiedAdapter):
    def investigate(self, goal, context):
        return {"task": goal["mastery_task"], "proposal_only": True}

    def plan(self, goal, investigation, learned_context):
        task = goal["mastery_task"]
        return {
            "actions": [{
                "action_id": f"mastery:{task['task_id']}",
                "type": "independent_mastery_trial",
                "description": goal["objective"],
                "risk_tier": "low",
                "requires_consent": False,
                "executable": True,
                "task": task,
            }]
        }

    def act(self, action, context):
        self.act_calls += 1
        task = action["task"]
        return {
            "status": "executed",
            "verified": True,
            "score": 1.0,
            "authority": task["authority"],
            "evidence": [{"source": f"sealed:{task['task_id']}"}],
        }

    def observe(self, action_result, context):
        return {
            "verified": True,
            "score": 1.0,
            "confidence": 1.0,
            "authority": action_result["authority"],
            "verifier": action_result["authority"],
            "verification_method": "independently_revealed_outcome",
            "lesson": "verified transfer outcome",
            "evidence": action_result["evidence"],
        }


def test_mission_generates_weakness_driven_goals_and_compounds_after_restart(tmp_path):
    adapter = MissionMasteryAdapter()
    runtime = _runtime(tmp_path, adapter, [])
    runtime.authorize_mission({
        "mission_id": "mission-general-learner",
        "objective": "learn unfamiliar domains and retain transferable competence",
        "approval_policy": "autonomous_allowed",
        "action_budget": 8,
        "allowed_authorities": ["independent-math", "independent-language"],
        "capability_requirements": [
            {
                "capability": "mathematical_rule_induction",
                "target_score": 1.0,
                "minimum_verified_outcomes": 2,
                "minimum_transfer_outcomes": 1,
                "tasks": [
                    {"task_id": "math-dev", "cohort": "development", "authority": "independent-math"},
                    {"task_id": "math-transfer", "cohort": "transfer", "authority": "independent-math"},
                ],
            },
            {
                "capability": "novel_language_induction",
                "target_score": 1.0,
                "minimum_verified_outcomes": 2,
                "minimum_transfer_outcomes": 1,
                "tasks": [
                    {"task_id": "language-dev", "cohort": "development", "authority": "independent-language"},
                    {"task_id": "language-transfer", "cohort": "transfer", "authority": "independent-language"},
                ],
            },
        ],
    })

    for _ in range(4):
        runtime.run_cycle()

    status = runtime.status()
    assert status["completed_cycles"] == 4
    assert status["capabilities_mastered"] == 2
    assert status["outcome_receipts"] == 4
    assert runtime.state["authorized_missions"]["mission-general-learner"]["status"] == "capability_complete"
    assert all(row["verified"] for row in runtime.state["outcome_receipts"])
    assert {row["cohort"] for row in runtime.state["outcome_receipts"]} == {"development", "transfer"}

    restarted = _runtime(tmp_path, adapter, [])
    assert restarted.status()["capabilities_mastered"] == 2
    assert restarted.status()["outcome_receipts"] == 4


def test_unapproved_outcome_authority_cannot_create_mastery(tmp_path):
    adapter = MissionMasteryAdapter()
    runtime = _runtime(tmp_path, adapter, [])
    runtime.authorize_mission({
        "mission_id": "mission-authority-boundary",
        "objective": "learn only from approved consequences",
        "approval_policy": "autonomous_allowed",
        "allowed_authorities": ["approved-authority"],
        "capability_requirements": [{
            "capability": "evidence_use",
            "target_score": 1.0,
            "minimum_verified_outcomes": 1,
            "minimum_transfer_outcomes": 0,
            "tasks": [{"task_id": "bad-authority", "authority": "self-certified"}],
        }],
    })

    runtime.run_cycle()

    receipt = runtime.state["outcome_receipts"][0]
    assert receipt["authority_allowed"] is False
    assert receipt["verified"] is False
    assert runtime.status()["capabilities_mastered"] == 0
