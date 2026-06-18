from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    brace = TEXT.index("{", start)
    depth = 0
    in_string = None
    escape = False

    for i in range(brace, len(TEXT)):
        ch = TEXT[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue

        if ch in ("'", '"', "`"):
            in_string = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:i + 1]

    raise AssertionError(f"function not closed: {name}")


def test_phase22c_stream_shell_uses_step_runner_marker():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "data-aion-phase22c-step-runner-ui" in block


def test_phase22c_top_duplicate_safety_banner_removed_from_active_stream():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "data-aion-pilot-safety-banner" not in block
    assert "Tell Pilot what you want done. New work appears" not in block


def test_phase22c_results_are_only_visible_after_safe_work_completed():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "safeWorkCompleted" in block
    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert 'safeWorkCompleted\\n                  ? `' in block or "safeWorkCompleted" in block


def test_phase22c_approve_button_is_next_step_language():
    block = function_block("renderAionPilotWorkPackageCard")
    assert "data-aion-pilot-work-package-actions" in block
    assert "data-aion-pilot-feedback-approve" in block
    assert "Approve" in block
    assert "Revise" in block
    assert "Stop" in block

def test_phase22c_campaign_output_is_real_campaign_pack():
    block = function_block("getAionPilotOutputPreviewText")
    assert "Campaign Pack:" in block
    assert "Generate 10 qualified roof repair enquiries" in block
    assert "Draft Advert" in block
    assert "Draft Customer Message" in block
    assert "Approval Needed Before Going Live" in block
