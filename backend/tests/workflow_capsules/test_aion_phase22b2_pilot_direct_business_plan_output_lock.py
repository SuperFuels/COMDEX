from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    brace = TEXT.index("{", start)
    depth = 0
    for i in range(brace, len(TEXT)):
        if TEXT[i] == "{":
            depth += 1
        elif TEXT[i] == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:i + 1]
    raise AssertionError(f"function not closed: {name}")


def test_phase22b2_no_appended_override_blocks_remain():
    assert "PHASE 22A.1 LOCK: Pilot create-plan dedicated click bridge" not in TEXT
    assert "PHASE 22B.1 LOCK: Pilot active output resolver override" not in TEXT


def test_phase22b2_business_plan_builder_exists():
    block = function_block("buildAionPilotBusinessPlanDraft")
    assert "Business Plan Draft:" in block
    assert "Business Overview" in block
    assert "Core Services" in block
    assert "90-Day Action Plan" in block


def test_phase22b2_output_preview_resolves_task_before_cache():
    block = function_block("getAionPilotOutputPreviewText")
    business_idx = block.index('if (taskType === "business_plan")')
    cache_idx = block.index("if (state.generated_output_text)")
    assert business_idx < cache_idx
    assert "buildAionPilotBusinessPlanDraft(safePlan, state)" in block


def test_phase22b2_open_output_uses_live_output_function():
    block = function_block("openAionPilotOutputPreview")
    assert "getAionPilotOutputPreviewText(plan, pilotState)" in block


def test_phase22b2_render_panel_uses_live_output_function():
    block = function_block("renderAionPilotOutputPanel")
    assert 'pilotState.output_panel_kind === "output"' in block
    assert "getAionPilotOutputPreviewText(plan, pilotState)" in block


def test_phase22b2_download_uses_live_output_function():
    block = function_block("downloadAionPilotOutputPreview")
    assert "getAionPilotOutputPreviewText(plan, pilotState)" in block
