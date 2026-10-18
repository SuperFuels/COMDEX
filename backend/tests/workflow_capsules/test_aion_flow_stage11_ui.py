from pathlib import Path


APP_JS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def test_production_review_is_visible_and_mobile_is_read_only():
    source = APP_JS.read_text(encoding="utf-8")
    assert "Production qualification" in source
    assert "Read-only mobile review" in source
    assert 'mobile ? "disabled"' in source
    assert "data-aion-flow-production-open" in source


def test_production_review_exposes_checks_not_execution():
    source = APP_JS.read_text(encoding="utf-8")
    assert "/aion-flow/production/qualify" in source
    assert "/aion-flow/production/commit" in source
    assert "/aion-flow/production/load-qualification" in source
    assert "Run sustained-load qualification" in source
    assert "It does not publish or execute the workflow" in source


def test_large_graph_groups_subflows_and_visual_diff_are_exposed():
    source = APP_JS.read_text(encoding="utf-8")
    assert "Groups and reusable subflows" in source
    assert "data-aion-flow-group-create" in source
    assert "data-aion-flow-subflow-create" in source
    assert "data-aion-flow-group-focus" in source
    assert "Visual version difference" in source
    assert 'post("/api/workflow-capsules/aion-flow/production/diff"' in source


def test_encrypted_transfer_is_exposed_and_clears_password():
    source = APP_JS.read_text(encoding="utf-8")
    assert "Move this workflow without moving authority" in source
    assert 'passwordInput.value = ""' in source
    assert "/aion-flow/production/export" in source
    assert "/aion-flow/production/import" in source
    assert "imported.authority_granted = false" in source


def test_production_access_uses_canonical_person_and_workspace_not_a_role_claim():
    source = APP_JS.read_text(encoding="utf-8")
    assert "aion.sales.signedInPerson.${workspaceId}.v1" in source
    assert "const actor = () => getAionStage8Actor()" in source
    assert 'role: "owner"' not in source[source.index("(function installAionFlowStage11ProductionReview"):source.index("(function installAionFlowStage9Comparison")]
    assert 'post("/api/workflow-capsules/aion-flow/production/history"' in source


def test_production_dialog_has_keyboard_and_screen_reader_contract():
    source = APP_JS.read_text(encoding="utf-8")
    fragment = source[source.index("function renderAionFlowProductionCentre"):source.index("function loadAionFlowTemplateIntoCanvas")]
    assert 'role="dialog"' in fragment
    assert 'aria-modal="true"' in fragment
    assert 'aria-labelledby="aion-flow-production-title"' in fragment
    assert 'aria-live="polite"' in fragment
    installer = source[source.index("(function installAionFlowStage11ProductionReview"):source.index("(function installAionFlowStage9Comparison")]
    assert 'event.key !== "Escape"' in installer
    assert "__aionFlowProductionReturnFocus" in installer
