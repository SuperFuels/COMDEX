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


def test_phase22c3_output_prepared_detail_defines_goal():
    block = function_block("getAionPilotOutputPreparedDetail")
    assert 'const safePlan = plan || buildAionPilotUniversalPlan("");' in block
    assert 'const goal = String(safePlan.goal || "the requested task");' in block


def test_phase22c3_campaign_detail_no_missing_goal_reference():
    block = function_block("getAionPilotOutputPreparedDetail")
    assert "Preparing campaign plan, advert draft, customer message and approval checklist" in block
    assert "${goal}" in block
