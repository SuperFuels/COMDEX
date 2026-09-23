from pathlib import Path


LOCK = Path("docs/rfc/aion_goal_engine_sprint4_experiment_runtime_lock.tex")


def test_sprint4_experiment_runtime_lock_doc_exists():
    assert LOCK.exists()


def test_sprint4_lock_records_experiment_policy_contract():
    text = LOCK.read_text()

    assert "EXPERIMENT_POLICY_SCHEMA_VERSION" in text
    assert "ExperimentPolicyContract" in text
    assert "aion.goal_engine.experiment_policy.v1" in text


def test_sprint4_lock_records_unbounded_experiment_blocking():
    text = LOCK.read_text()

    assert "unbounded_experiment_plan_blocked" in text
    assert "max_iterations_required" in text
    assert "max_runtime_minutes_required" in text
    assert "metric_required" in text


def test_sprint4_lock_records_premature_convergence_blocking():
    text = LOCK.read_text()

    assert "premature_convergence_blocked = true" in text
    assert "Premature convergence blocked" in text


def test_sprint4_lock_records_bundle_and_bridge_ownership():
    text = LOCK.read_text()

    assert "GoalEnginePreviewBundle" in text
    assert "single source of truth" in text
    assert "experiment_runtime_summary" in text
    assert "goal_engine_experiment_runtime_summary" in text
    assert "MUST NOT rebuild" in text


def test_sprint4_lock_records_boardroom_visibility():
    text = LOCK.read_text()

    assert "Experiment Runtime Summary" in text
    assert "Unbounded experiment plan blocked" in text
    assert "Premature convergence blocked" in text


def test_sprint4_lock_footer_is_present():
    text = LOCK.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-SPRINT-4-EXPERIMENT-RUNTIME-LOCK-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
