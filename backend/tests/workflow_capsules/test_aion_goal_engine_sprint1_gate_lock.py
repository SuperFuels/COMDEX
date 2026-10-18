from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_sprint1_gate_lock.tex")
BUILD_PLAN = Path("docs/rfc/aion_managed_agent_goal_engine_build_plan_lock.tex")
APP = Path("desktop/mac/src/app.js")


def test_goal_engine_sprint1_gate_doc_exists():
    assert DOC.exists(), "missing Sprint 1 gate lock doc"


def test_goal_engine_sprint1_gate_references_core_scope():
    text = DOC.read_text(encoding="utf-8")

    assert "Goal Engine contract files exist" in text
    assert "Workflow Canvas / Architect picker" in text
    assert "Goal Engine inspector fields" in text
    assert "Goal Engine dry-run preview bundle" in text
    assert "Goal Engine step trace rows" in text
    assert "Goal Engine Boardroom preview state" in text
    assert "protected against drift" in text


def test_goal_engine_sprint1_gate_locks_canvas_and_boardroom_roles():
    text = DOC.read_text(encoding="utf-8")

    assert "The Workflow Canvas is where capability is built" in text
    assert "The Boardroom is where trust is explained" in text
    assert "Master Glyph Canvas is deprecated as a separate canvas mode" in text
    assert "Glyph Library modal" in text


def test_goal_engine_sprint1_gate_keeps_a2a_deferred():
    text = DOC.read_text(encoding="utf-8")

    assert "Agent-to-Agent layer is intentionally deferred" in text
    assert "canonical preview bundle" in text
    assert "stable Boardroom trace" in text
    assert "stable evidence references" in text
    assert "stable checkpoint/resume semantics" in text


def test_goal_engine_sprint1_gate_points_to_sprint2_runtime_consolidation():
    text = DOC.read_text(encoding="utf-8")

    assert "Goal-aware dry-run runtime consolidation" in text
    assert "reduce appended patching" in text
    assert "first-class runtime modules" in text


def test_managed_agent_build_plan_lock_still_exists():
    assert BUILD_PLAN.exists(), "managed-agent build plan lock disappeared"

    text = BUILD_PLAN.read_text(encoding="utf-8")
    assert "AION-MANAGED-AGENT-GOAL-ENGINE-BUILD-PLAN-V1" in text
    assert "A2A Transition Gate" in text


def test_app_contains_goal_engine_safety_badge_runtime_refs():
    text = APP.read_text(encoding="utf-8")

    assert "getAionGoalEngineCanvasSafetyBadgesV1" in text
    assert "renderAionGoalEngineCanvasSafetyBadgesV1" in text
    assert "injectAionGoalEngineCanvasSafetyBadgesV1" in text
    assert "Budget guarded" in text
    assert "Red-team warning" in text


def test_app_contains_goal_engine_visible_canvas_runtime_refs():
    text = APP.read_text(encoding="utf-8")

    assert "goal" in text.lower()
    assert "experiment" in text.lower()
    assert "outcome" in text.lower()
    assert "checkpoint" in text.lower()
