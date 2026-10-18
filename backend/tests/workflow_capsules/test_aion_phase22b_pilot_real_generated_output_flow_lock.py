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


def test_phase22b_business_plan_builder_exists():
    assert "function buildAionPilotBusinessPlanDraft" in TEXT
    assert "Business Plan Draft:" in TEXT
    assert "Business Overview" in TEXT
    assert "90-Day Action Plan" in TEXT


def test_phase22b_runner_sets_generated_output():
    assert "appendAionPilotStepOutput" in TEXT


def test_phase22b_output_preview_uses_task_renderer_before_cache():
    block = function_block("getAionPilotOutputPreviewText")
    assert 'if (taskType === "business_plan")' in block
    assert "buildAionPilotBusinessPlanDraft(safePlan, state)" in block


def test_phase22b_open_download_and_panel_use_live_output_function():
    assert "getAionPilotOutputPreviewText(plan, pilotState)" in function_block("openAionPilotOutputPreview")
    assert "getAionPilotOutputPreviewText(plan, pilotState)" in function_block("downloadAionPilotOutputPreview")
    assert "const body = pilotState.output_panel_body ||" in function_block("renderAionPilotOutputPanel")


def test_phase22b_create_plan_has_visible_state_change():
    assert 'pilotState.status = "plan_ready";' in TEXT
    assert 'label: "Work package created",' in TEXT
