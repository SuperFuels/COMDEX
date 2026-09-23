from __future__ import annotations

import json


def test_prediction_engine_keeps_base_and_is_deterministic():
    from backend.modules.consciousness.prediction_engine import PredictionEngine, PredictionEngineBase

    assert issubclass(PredictionEngine, PredictionEngineBase)
    mission = {
        "objective": "Build a secure application and verify it",
        "capability_decision": {"decision": "learn_then_execute"},
    }
    first = PredictionEngineBase.assess_feasibility(object(), mission)
    second = PredictionEngineBase.assess_feasibility(object(), mission)
    assert first == second == 0.3


def test_planning_preserves_dependency_order_and_never_claims_execution():
    from backend.modules.consciousness.planning_engine import PlanningEngine

    plan = PlanningEngine.__new__(PlanningEngine).generate_governed_plan(
        {"objective": "Build and verify an application"},
        {"decision": "learn_then_execute", "action_contract": ["learn", "build", "verify"]},
    )
    assert [step["description"] for step in plan["steps"]] == ["learn", "build", "verify"]
    assert plan["steps"][1]["depends_on"] == [plan["steps"][0]["step_id"]]
    assert plan["proposal_only"] is True
    assert all(step["execution_authority"] is False for step in plan["steps"])


def test_strategy_requires_real_adapter_and_verified_outcome():
    from backend.modules.hexcore.strategy_engine import StrategyEngine

    engine = StrategyEngine.__new__(StrategyEngine)
    proposal = {
        "objective": "Compile the project",
        "capability_decision": "execute",
        "approval_policy": "autonomous_allowed",
    }
    denied = engine.execute_plan(proposal)
    assert denied["status"] == "not_executed"
    assert "verified_execution_adapter_missing" in denied["authority_check"]["reasons"]

    unverified = engine.execute_plan(proposal, lambda _: {"returncode": 0})
    assert unverified["status"] == "unverified_outcome"

    verified = engine.execute_plan(
        proposal,
        lambda _: {"returncode": 0, "verified": True, "outcome_hash": "sha256:abc"},
    )
    assert verified["status"] == "verified"


def test_owner_key_cannot_bypass_block_law(monkeypatch):
    import backend.modules.consciousness.ethics_engine as ethics_module

    monkeypatch.setattr(ethics_module, "KEVIN_MASTER_KEY", "owner-key")
    report = ethics_module.EthicsEngine().evaluate_action({
        "objective": "attack and harm a person",
        "capability_decision": "execute",
        "approval_policy": "human_approved",
        "override_key": "owner-key",
    })
    assert report["owner_authorization_recorded"] is True
    assert report["allowed"] is False
    assert report["owner_authorization_is_not_safety_bypass"] is True


def test_identity_core_is_immutable_and_phase_progression_is_bounded(tmp_path):
    from backend.modules.consciousness.identity_engine import IdentityEngine

    path = tmp_path / "identity.json"
    path.write_text(json.dumps({"name": "Imposter", "creator": "Unknown", "phase": "learner"}))
    identity = IdentityEngine(file_path=str(path))
    assert identity.get_identity()["name"] == "AION"
    assert identity.get_identity()["creator"] == "Kevin Robinson"
    identity.update_phase("apprentice")
    try:
        identity.update_phase("capable_assistant")
    except ValueError:
        pass
    else:
        raise AssertionError("phase skip should fail")


def test_situational_events_require_independent_evidence_fields():
    from backend.modules.consciousness.situational_engine import SituationalEngine

    engine = SituationalEngine()
    assert engine.ingest_verified_event({"description": "changed"})["accepted"] is False
    accepted = engine.ingest_verified_event({
        "description": "upstream API changed",
        "source": "public-api",
        "authority": "independent-observation",
        "outcome_hash": "sha256:def",
        "origin": "external_change",
        "impact": "negative",
    })
    assert accepted["accepted"] is True
    context = engine.analyze_context()
    assert context["external_changes"] == 1
    assert context["internal_failures"] == 0

