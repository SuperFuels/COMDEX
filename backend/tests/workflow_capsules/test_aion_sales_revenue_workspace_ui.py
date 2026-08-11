from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_sales_revenue_workspace_is_loaded_and_replaces_placeholder_with_operating_surface():
    index = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert '<script src="./aion_sales_revenue_workspace.js"></script>' in index
    assert 'data-aion-sales-live-agents-workspace-o14d="true"' in app
    assert 'data-aion-shared-department="sales"' in sales
    assert "Sales Revenue Spine" in sales
    assert "SALES AGENT STUDIO" in sales
    assert "external_transport_started" not in sales or "No external call was initiated" in sales
    assert "Human handoff" in sales
    assert "Prepare appointment" in sales
    assert "AI identity was disclosed" in sales
    assert "GENUINE MARKETING INTAKE" in sales
    assert "Import matching enquiries now" in sales
    assert "Run 11 executable safety scenarios" in sales
    assert "LIVE CALL CONSOLE" in sales
    assert "if (mount() && id && (state.workspaceId !== id || !state.data)) load()" in sales
    assert "new AbortController()" in sales


def test_sales_ui_keeps_external_actions_exactly_approved_and_fail_closed():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "This does not write to a calendar or notify the customer" in sales
    assert "No external writes" in sales
    assert "It does not initiate an external call" in sales
    assert "Approve exact call" in sales
    assert "Start this exact approved customer call now?" in sales
    assert "Retell webhook signatures are replay-bounded" in sales
