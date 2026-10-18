from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / "backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py"


def _function_body(text: str, name: str) -> str:
    start = text.index(f"def {name}(")
    next_def = text.find("\ndef ", start + 1)
    if next_def == -1:
        return text[start:]
    return text[start:next_def]


def test_attach_goal_engine_manifest_attaches_step_trace_once():
    text = BRIDGE.read_text()
    body = _function_body(text, "attach_goal_engine_manifest_to_dry_result")

    assert body.count("attach_goal_engine_step_trace_rows_to_dry_result(") == 1


def test_step_trace_attachment_happens_after_manifest_and_boardroom_are_set():
    text = BRIDGE.read_text()
    body = _function_body(text, "attach_goal_engine_manifest_to_dry_result")

    manifest_pos = body.index('setattr(dry_result, "goal_engine_manifest", manifest)')
    boardroom_pos = body.index('setattr(dry_result, "goal_engine_boardroom_trace", boardroom_trace)')
    trace_pos = body.index("attach_goal_engine_step_trace_rows_to_dry_result(")

    assert manifest_pos < trace_pos
    assert boardroom_pos < trace_pos


def test_attach_goal_engine_manifest_keeps_single_to_dict_wrapper_path():
    text = BRIDGE.read_text()
    body = _function_body(text, "attach_goal_engine_manifest_to_dry_result")

    assert body.count("original_to_dict = dry_result.to_dict") == 1
    assert body.count("def to_dict_with_goal_engine_manifest") == 1
