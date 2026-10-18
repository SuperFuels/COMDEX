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


def test_phase22t_classifier_routes_marketing_before_business_plan():
    block = _function_block("classifyAionPilotUniversalTask")
    marketing_index = block.index('task_type: "marketing_plan"')
    business_index = block.index('task_type: "business_plan"')
    assert marketing_index < business_index
    assert '"marketing plan"' in block
    assert '"grow the business"' in block


def test_phase22t_business_plan_requires_specific_business_plan_intent():
    block = _function_block("classifyAionPilotUniversalTask")
    assert 'text.includes("business plan")' in block
    assert 'text.includes("business model")' in block
    assert '(text.includes("plan") && (text.includes("business")' not in block
    assert 'text.includes("home repair")' not in block


def test_phase22t_marketing_plan_package_exists():
    assert 'marketing_plan: {' in TEXT
    assert 'name: "Marketing plan package"' in TEXT
    assert '"Marketing objective"' in TEXT
    assert '"Channel plan"' in TEXT
    assert '"Lead capture workflow"' in TEXT


def test_phase22t_marketing_plan_output_builder_exists_and_is_not_business_plan():
    block = _function_block("buildAionPilotMarketingPlanDraft")
    assert "Marketing Plan Draft" in block
    assert "Marketing Objective" in block
    assert "Lead Capture Workflow" in block
    assert "Business Plan Draft" not in block


def test_phase22t_output_preview_routes_marketing_plan_before_business_plan():
    block = _function_block("getAionPilotOutputPreviewText")
    marketing_index = block.index('taskType === "marketing_plan"')
    business_index = block.index('taskType === "business_plan"')
    assert marketing_index < business_index
    assert "buildAionPilotMarketingPlanDraft" in block
