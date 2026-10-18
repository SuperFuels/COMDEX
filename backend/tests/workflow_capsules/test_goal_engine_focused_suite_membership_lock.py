from pathlib import Path


SUITE_PATH = Path("scripts/run_goal_engine_focused_lock_suite.sh")


REQUIRED_LOCK_TESTS = [
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint1_gate_lock.py",
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint1_completion_lock.py",
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint2_outcome_evidence_lock.py",
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint3_checkpoint_resume_lock.py",
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint4_experiment_runtime_lock.py",
    "backend/tests/workflow_capsules/test_aion_goal_engine_sprint5_orchestrator_runtime_lock.py",
    "backend/tests/workflow_capsules/test_goal_engine_guarded_child_run_creation_request.py",
    "backend/tests/workflow_capsules/test_goal_engine_human_approved_child_run_creation_action.py",
    "backend/tests/workflow_capsules/test_goal_engine_child_run_executor_bridge.py",
    "backend/tests/workflow_capsules/test_goal_engine_child_run_creation_end_to_end_lock.py",
    "backend/tests/workflow_capsules/test_goal_engine_human_approved_conflict_resolution.py",
    "backend/tests/workflow_capsules/test_goal_engine_human_approved_conflict_resolution_end_to_end_lock.py",
    "backend/tests/workflow_capsules/test_goal_engine_guarded_multi_agent_orchestration_lock_doc.py",
]


def _suite_text() -> str:
    assert SUITE_PATH.exists(), "focused Goal Engine lock suite script is missing"
    return SUITE_PATH.read_text()


def test_focused_goal_engine_suite_contains_required_lock_files():
    text = _suite_text()

    missing = [path for path in REQUIRED_LOCK_TESTS if path not in text]

    assert missing == []


def test_focused_goal_engine_suite_uses_project_python_entrypoint():
    text = _suite_text()

    assert "python -m pytest" in text
    assert "pytest " not in text.replace("python -m pytest", "")


def test_focused_goal_engine_suite_starts_with_syntax_sweep():
    text = _suite_text()

    assert "syntax sweep: Goal Engine provider/container/boardroom files" in text
    assert "python -m py_compile" in text


def test_focused_goal_engine_suite_keeps_child_run_chain_in_order():
    text = _suite_text()

    guarded_idx = text.index("test_goal_engine_guarded_child_run_creation_request.py")
    approved_idx = text.index("test_goal_engine_human_approved_child_run_creation_action.py")
    bridge_idx = text.index("test_goal_engine_child_run_executor_bridge.py")
    e2e_idx = text.index("test_goal_engine_child_run_creation_end_to_end_lock.py")

    assert guarded_idx < approved_idx < bridge_idx < e2e_idx


def test_focused_goal_engine_suite_keeps_conflict_resolution_chain_in_order():
    text = _suite_text()

    conflict_idx = text.index("test_goal_engine_child_agent_conflict_preview.py")
    resolution_idx = text.index("test_goal_engine_human_approved_conflict_resolution.py")
    e2e_idx = text.index("test_goal_engine_human_approved_conflict_resolution_end_to_end_lock.py")
    ui_idx = text.index("test_goal_engine_human_approved_conflict_resolution_ui_lock.py")

    assert conflict_idx < resolution_idx < e2e_idx < ui_idx
