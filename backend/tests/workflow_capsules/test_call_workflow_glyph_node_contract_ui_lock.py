from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _authoritative_patch() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    assert "AION PATCH: Backend Glyph Marketplace Authoritative Render v1" in src
    assert "AION PATCH: Master Glyph Workflow Tab v1" in src
    return src.split("AION PATCH: Backend Glyph Marketplace Authoritative Render v1", 1)[1].split(
        "AION PATCH: Master Glyph Workflow Tab v1", 1
    )[0]


def test_staged_glyph_node_uses_real_call_workflow_glyph_type():
    patch = _authoritative_patch()

    assert 'type: "call_workflow_glyph"' in patch
    assert 'kind: "call_workflow_glyph"' in patch
    assert 'display_type: "Workflow Glyph"' in patch
    assert 'action_id: "call_workflow_glyph"' in patch
    assert 'module_id: "workflow.call_workflow_glyph"' in patch


def test_staged_glyph_node_stores_contract_fields_top_level():
    patch = _authoritative_patch()

    for field in [
        "glyph_code: glyph.glyph_code",
        "glyph_id: glyph.glyph_id",
        'glyph_version: glyph.glyph_version || "v1"',
        'glyph_scope: glyph.scope || glyph.glyph_scope || "my"',
        "child_workflow_id: glyph.workflow_id",
        "source_glyph_code: glyph.source_glyph_code || null",
        'version_hash: glyph.version_hash || glyph.meta?.version_hash || ""',
        "input_schema: clone(glyph.input_schema || {})",
        "output_schema: clone(glyph.output_schema || {})",
        "required_connectors: clone(glyph.required_connectors || [])",
        'risk_tier: glyph.risk_tier || "low"',
        "approval_policy: clone(glyph.approval_policy || {})",
        "runtime_plan: clone(glyph.runtime_plan || {})",
    ]:
        assert field in patch


def test_staged_glyph_node_remains_dry_run_only():
    patch = _authoritative_patch()

    assert "dry_run_only: true" in patch
    assert "live_send_enabled: false" in patch
    assert "Runtime remains dry-run only until validation is" in patch
