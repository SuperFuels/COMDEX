from pathlib import Path

DOC = Path("docs/rfc/aion_managed_agent_goal_engine_build_plan_lock.tex")


def test_aion_managed_agent_build_plan_lock_exists():
    assert DOC.exists(), "missing managed-agent Goal Engine build plan lock doc"


def test_aion_managed_agent_build_plan_records_core_layers():
    text = DOC.read_text(encoding="utf-8")

    assert "Founder UI / Boardroom" in text
    assert "Workflow Canvas" in text
    assert "Workflow Engine" in text
    assert "Evidence Trace" in text
    assert "Agent API" in text


def test_aion_managed_agent_build_plan_locks_canvas_direction():
    text = DOC.read_text(encoding="utf-8")

    assert "Workflow Canvas is the single editing and composition surface" in text
    assert "Master Glyph Canvas mode is deprecated as a separate canvas mode" in text
    assert "Glyph Library modal" in text


def test_aion_managed_agent_build_plan_has_a2a_transition_gate():
    text = DOC.read_text(encoding="utf-8")

    assert "A2A Transition Gate" in text
    assert "business-to-agent telemetry" in text
    assert "fulfilment protocol" in text


def test_aion_managed_agent_build_plan_locks_non_negotiables():
    text = DOC.read_text(encoding="utf-8")

    assert "Goal nodes define intent only" in text
    assert "Resume is not continue" in text
    assert "Outcome scores require evidence" in text
    assert "Learning is advisory only" in text
    assert "Managed-agent providers are accelerators" in text
    assert "Version everything" in text
