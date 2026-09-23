from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_legacy_costa_identity_is_explicitly_blocked():
    block = function_block("isAionLegacyDemoBusinessIdentity")

    assert "costa_conexion" in block
    assert "costaconexion" in block
    assert "costa_connection" in block


def test_registered_identity_reads_business_form_not_workflow_graph():
    block = function_block("getAionRegisteredBusinessIdentity")

    assert "state?.approvedSmallBusinessFoundation" in block
    assert "state?.businessContextFoundation" in block
    assert "state?.smallBusinessFoundationDraft" in block
    assert "aion.approvedSmallBusinessFoundation" in block
    assert "aion.businessContextFoundation" in block
    assert "aion.smallBusinessFoundationDraft" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "window.__aionWorkflowGraph" not in block


def test_workflow_container_rejects_stale_costa_graph_identity():
    block = function_block("getAionWorkflowBusinessContainerId")

    assert "isAionLegacyDemoBusinessIdentity(fromGoalLoop)" in block
    assert "business_not_registered" in block
    assert 'window.__aionWorkflowGraph?.canvas_type === "goal_loop"' in block
    assert "getAionRegisteredBusinessIdentity()" in block
