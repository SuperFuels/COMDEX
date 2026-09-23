from pathlib import Path


APP_JS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def test_template_gallery_is_visible_and_uses_safe_bindings():
    source = APP_JS.read_text(encoding="utf-8")
    assert "Intelligence Stack templates" in source
    assert "data-aion-flow-template-open" in source
    assert "/api/workflow-capsules/aion-flow/templates" in source
    assert "/api/vault/aion-flow/bindings" in source
    assert "Choose a secure Visual Vault binding" in source
    assert "grants no execution authority" in source


def test_template_loading_is_draft_only():
    source = APP_JS.read_text(encoding="utf-8")
    assert "function loadAionFlowTemplateIntoCanvas" in source
    assert 'graph.status = "draft"' in source
    assert "template_manifest_hash" in source
    assert "Template logic loaded as a non-executing draft" in source
