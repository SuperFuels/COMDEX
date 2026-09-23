from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_sprint5_orchestrator_runtime_lock.tex")


def test_sprint5_lock_doc_exists():
    assert DOC.exists()


def test_sprint5_lock_records_schema_versions_and_contracts():
    text = DOC.read_text()

    assert "AGENT_ASSIGNMENT_SCHEMA_VERSION" in text
    assert "ORCHESTRATOR_SCHEMA_VERSION" in text
    assert "AgentAssignmentContract" in text
    assert "OrchestratorContract" in text


def test_sprint5_lock_records_bounded_orchestration_rule():
    text = DOC.read_text()

    assert "unbounded_orchestration_blocked" in text
    assert "max_parallel_agents > 0" in text


def test_sprint5_lock_records_bundle_and_bridge_contract():
    text = DOC.read_text()

    assert "orchestrator_runtime_summary" in text
    assert "goal_engine_orchestrator_runtime_summary" in text
    assert "MUST NOT rebuild" in text


def test_sprint5_lock_records_boardroom_visibility():
    text = DOC.read_text()

    assert "Orchestrator Runtime Summary" in text
    assert "Agent assignments" in text or "agent assignments" in text
    assert "glyph code" in text


def test_sprint5_lock_records_dry_run_safety():
    text = DOC.read_text()

    assert "dry_run_only = true" in text
    assert "would_execute = false" in text
    assert "would_write_external = false" in text
    assert "would_grant_permission = false" in text


def test_sprint5_lock_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-SPRINT-5-ORCHESTRATOR-RUNTIME-LOCK-V1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
