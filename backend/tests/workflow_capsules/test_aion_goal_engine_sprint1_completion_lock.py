from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_sprint1_completion_lock.tex")


def test_sprint1_completion_lock_exists():
    assert DOC.exists()


def test_sprint1_completion_lock_records_72_test_pass():
    text = DOC.read_text()

    assert "72 passed in 0.34s" in text
    assert "Goal Engine Sprint 1 canonical bundle suite passing with 72 tests" in text


def test_sprint1_completion_lock_names_canonical_bundle():
    text = DOC.read_text()

    assert "GoalEnginePreviewBundle" in text
    assert "single source of truth" in text
    assert "goal_engine_preview_bundle" not in text or "canonical preview bundle" in text


def test_sprint1_completion_lock_preserves_legacy_mirrors():
    text = DOC.read_text()

    assert "goal_engine_manifest" in text
    assert "goal_engine_step_trace" in text
    assert "goal_engine_boardroom_trace" in text
    assert "goal_engine_machine_trace" in text


def test_sprint1_completion_lock_defers_a2a():
    text = DOC.read_text()

    assert "agent_ready = false" in text
    assert "a2a_deferred = true" in text
    assert "commercial_interface_ready = false" in text


def test_sprint1_completion_lock_sets_sprint2_gate():
    text = DOC.read_text()

    assert "Sprint 2 --- Goal-Aware Dry-Run Runtime" in text
    assert "must not reintroduce parallel manifest, trace, or Boardroom serialization paths" in text


def test_sprint1_completion_lock_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-SPRINT-1-COMPLETION-LOCK-V1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
