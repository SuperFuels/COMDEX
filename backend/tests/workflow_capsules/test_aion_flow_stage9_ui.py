from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_stage9_comparison_is_visible_in_existing_workflow_footer():
    text = APP.read_text(encoding="utf-8")
    for marker in (
        "Compare stacks",
        "data-aion-flow-comparison-open",
        "Duplicate &amp; compare",
        "Run same-pack dry comparison",
        "Measured results",
        "Promote challenger",
        "Return to champion",
        "What AION learned",
    ):
        assert marker in text


def test_stage9_ui_calls_customer_owned_evaluation_routes():
    text = APP.read_text(encoding="utf-8")
    for route in (
        "/api/workflow-capsules/aion-flow/evaluations",
        "/run-same-pack",
        "/results",
        'action === "promote"',
        'data-aion-flow-reverse-routing',
    ):
        assert route in text
    assert "Customer-private outcomes" in text
    assert "Public benchmark" in text
    assert "Unverified results never change routing" in text
