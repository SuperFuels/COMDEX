from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1, f"Missing function {name}"

    signature_end = TEXT.find(") {", start)
    assert signature_end != -1
    brace_start = signature_end + 2

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
            in_double = True
        elif char == "`":
            in_template = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:index + 1]

    raise AssertionError(f"Could not extract function {name}")


def test_phase22r_approval_mode_classifier_exists():
    block = _function_block("classifyAionPilotApprovalRequirementMode")
    assert "live_execution_approval" in block
    assert "content_approval" in block
    assert "payment" in block
    assert "deploy" in block
    assert "account" in block


def test_phase22r_content_approval_produces_draft_before_approval():
    block = _function_block("buildAionPilotPriorityStepOutput")
    assert "approvalMode === \"content_approval\"" in block
    assert "buildAionPilotApprovalDraftOutput" in block
    assert "pendingDrafts[nextFollowOn.key] = true" in block
    assert "delete pendingDrafts[nextFollowOn.key]" in block


def test_phase22r_live_execution_still_pauses_without_running():
    block = _function_block("buildAionPilotPriorityStepOutput")
    assert "live, external, financial, account, deployment, booking, customer contact or credentialed action" in block
    assert "Pilot has not executed this live action" in block


def test_phase22r_sticky_queue_has_approval_draft_labels():
    block = _function_block("renderAionPilotFollowOnWorkQueue")
    assert "Approval draft ready" in block
    assert "Waiting for approval draft" in block
    assert "Create approval draft" in block
    assert "Approve and continue" in block


def test_phase22r_approval_draft_copy_is_clear():
    block = _function_block("buildAionPilotApprovalDraftOutput")
    assert "Draft asset for approval" in block
    assert "Approving this item allows Pilot to continue with the next safe draft task" in block
    assert "It does not approve live posting" in block
