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


def test_phase22b1_no_appended_override_blocks_remain():
    assert "PHASE 22B.1 LOCK: Pilot active output resolver override" not in TEXT
    assert "PHASE 22A.1 LOCK: Pilot create-plan dedicated click bridge" not in TEXT


def test_phase22b1_business_plan_beats_cached_generic_output():
    block = function_block("getAionPilotOutputPreviewText")
    business_idx = block.index('if (taskType === "business_plan")')
    cache_idx = block.index("if (state.generated_output_text)")
    assert business_idx < cache_idx
    assert "buildAionPilotBusinessPlanDraft(safePlan, state)" in block


def test_phase22b1_output_panel_uses_selected_body_not_recomputed_plan():
    block = function_block("renderAionPilotOutputPanel")
    assert "const body = pilotState.output_panel_body ||" in block
    assert "getAionPilotOutputPreviewText(plan, pilotState)" not in block
    assert "normaliseAionPilotPreviewText(body)" in block
