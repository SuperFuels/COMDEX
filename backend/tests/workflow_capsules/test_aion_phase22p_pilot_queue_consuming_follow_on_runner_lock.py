from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")

def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1, f"Missing function {name}"

    brace_start = TEXT.find("{", start)
    assert brace_start != -1

    depth = 0
    in_single = False
    in_double = False
    in_template = False
    escaped = False

    for index in range(brace_start, len(TEXT)):
        char = TEXT[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if in_single:
            if char == "'":
                in_single = False
            continue

        if in_double:
            if char == '"':
                in_double = False
            continue

        if in_template:
            if char == "`":
                in_template = False
            continue

        if char == "'":
            in_single = True
        elif char == '"':
            in_double = False if False else True
        elif char == "`":
            in_template = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:index + 1]

    raise AssertionError(f"Could not extract function {name}")



def test_phase22p_queue_helpers_exist():
    for marker in [
        "function getAionPilotFollowOnWorkQueue",
        "function getAionPilotCompletedFollowOnWork",
        "function getAionPilotNextExecutableFollowOnWorkItem",
        "function buildAionPilotFollowOnTaskDraftOutput",
    ]:
        assert marker in TEXT


def test_phase22p_continue_safe_work_consumes_next_queue_item():
    block = _function_block("buildAionPilotPriorityStepOutput")

    assert "getAionPilotNextExecutableFollowOnWorkItem" in block
    assert "completed[nextFollowOn.key] = true" in block
    assert "buildAionPilotFollowOnTaskDraftOutput" in block
    assert "Prepare the next safe draft output" not in block


def test_phase22p_approval_gated_item_pauses_instead_of_executing():
    block = _function_block("buildAionPilotPriorityStepOutput")

    assert "Approval required" in block
    assert "needs human approval before Pilot can run it" in block
    assert "No live external action has been taken" in block


def test_phase22p_follow_on_queue_mounted_once_only():
    assert TEXT.count("renderAionPilotFollowOnWorkQueue(plan, pilotState)") == 1


def test_phase22p_follow_on_renderer_marks_completed_items():
    start = TEXT.index("function renderAionPilotFollowOnWorkQueue")
    end = TEXT.index("window.deriveAionPilotFollowOnWorkItems", start)
    block = TEXT[start:end]

    assert "✓ Completed" in block
    assert "aion-pilot-follow-on-completed" in block
    assert "completed[key] === true" in block


def test_phase22p_customer_profile_is_not_hard_approval_signal():
    start = TEXT.index("function classifyAionPilotFollowOnWorkItem")
    end = TEXT.index("function getAionPilotFollowOnApprovalStages", start)
    block = TEXT[start:end]

    assert '"customer"' not in block
    assert '"publish"' in block
    assert '"send "' in block
    assert '"deploy"' in block
