from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_deliberation import AionFlowDeliberationEngine, DeliberationBudget


def candidate(name, quality, *, cost=0, output=None):
    return {
        "route_id": name, "provider": name, "model": name, "harness": "h1",
        "call": lambda payload: {
            "valid": True, "evidence_status": "verified", "quality": quality,
            "correctness": quality, "evidence_coverage": quality, "summary": name,
            "output": output or {"answer": name}, "usage": {"tokens": 10, "cost": cost, "energy_wh": 0.1},
        },
    }


def test_parallel_candidates_use_evidence_first_arbitration_and_preserve_dissent():
    engine = AionFlowDeliberationEngine()
    result = engine.deliberate(
        task={"question": "why"}, evidence_pack={"status": "verified"},
        candidate_routes=[candidate("local", 0.8), candidate("private", 0.95)],
        critic_routes=[{"route_id": "critic", "provider": "third", "model": "critic", "call": lambda payload: {"findings": ["check assumption"], "assumptions": ["seasonality"], "usage": {"tokens": 5}}}],
        budget=DeliberationBudget(maximum_cost=1),
    )
    assert result["status"] == "resolved"
    assert result["winner"]["candidate_id"] == "private"
    assert result["dissent"][0]["candidate_id"] == "local"
    assert result["arbitration_order"][0] == "deterministic_validation"
    assert result["model_vote_grants_authority"] is False


def test_invalid_or_unverified_candidate_cannot_win_even_with_high_model_score():
    engine = AionFlowDeliberationEngine()
    bad = candidate("bad", 1.0)
    bad["call"] = lambda payload: {"valid": True, "evidence_status": "unresolved", "quality": 1, "correctness": 1, "evidence_coverage": 1, "output": {"answer": "invented"}}
    result = engine.deliberate(task={}, evidence_pack={}, candidate_routes=[bad, candidate("verified", 0.8)], budget=DeliberationBudget(maximum_cost=1))
    assert result["winner"]["candidate_id"] == "verified"


def test_close_disagreement_and_high_consequence_require_human_arbitration():
    engine = AionFlowDeliberationEngine()
    result = engine.deliberate(task={}, evidence_pack={}, candidate_routes=[candidate("a", 0.91), candidate("b", 0.90)], budget=DeliberationBudget(maximum_cost=1), high_consequence=True)
    assert result["status"] == "awaiting_human_arbitration"
    assert result["winner"] is None
    assert result["proposed_winner"] is not None


def test_budget_ceiling_stops_deliberation_without_authority():
    engine = AionFlowDeliberationEngine()
    result = engine.deliberate(task={}, evidence_pack={}, candidate_routes=[candidate("paid", 0.9, cost=1)], budget=DeliberationBudget(maximum_cost=0))
    assert result["status"] == "budget_blocked"
    assert result["reason"] == "cost_budget_exceeded"
    assert result["downstream_execution_allowed"] is False


def test_refinement_stops_on_success_repetition_or_oscillation():
    engine = AionFlowDeliberationEngine()
    result = engine.refine(
        initial={"score": 0},
        improve=lambda payload: {"score": payload["candidate"]["score"] + 1, "usage": {"tokens": 1}},
        evidence_pack={"status": "verified"}, budget=DeliberationBudget(maximum_iterations=5, maximum_cost=1),
        success=lambda item: item["score"] >= 2,
    )
    assert result["status"] == "resolved"
    assert result["stop_reason"] == "success_criteria_met"
    repeated = engine.refine(
        initial={"score": 0}, improve=lambda payload: {"score": 0}, evidence_pack={},
        budget=DeliberationBudget(maximum_iterations=5, maximum_cost=1), success=lambda item: False,
    )
    assert repeated["stop_reason"] == "repeated_output"
    assert repeated["downstream_execution_allowed"] is False
