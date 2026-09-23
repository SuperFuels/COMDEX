from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DRY_RUN = ROOT / "backend/modules/workflow_capsules/execution/workflow_capsule_dry_run.py"


def test_goal_engine_bridge_is_not_attached_inside_permission_evaluator():
    text = DRY_RUN.read_text()

    permission_section = text.split("def _evaluate_step_permission", 1)[1].split("def _preview_step", 1)[0]

    assert "attach_goal_engine_manifest_to_dry_result(" not in permission_section
    assert "return result" in permission_section


def test_goal_engine_bridge_attaches_to_final_dry_run_result():
    text = DRY_RUN.read_text()

    run_section = text.split("class WorkflowCapsuleDryRunExecutor", 1)[1].split("def _evaluate_step_permission", 1)[0]

    assert "# GOAL ENGINE DRY-RUN BRIDGE V2" in run_section
    assert "result = WorkflowDryRunResult(" in run_section
    assert "attach_goal_engine_manifest_to_dry_result(" in run_section
    assert "run_id=run_id" in run_section
    assert "return result" in run_section


def test_goal_engine_bridge_comment_explains_final_result_contract():
    text = DRY_RUN.read_text()

    assert "Attach Goal Engine manifest, step trace, and Boardroom trace" in text
    assert "final WorkflowDryRunResult" in text
    assert "not to per-step permission dictionaries" in text
