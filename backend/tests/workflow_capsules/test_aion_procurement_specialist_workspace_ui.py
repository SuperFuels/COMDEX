from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
OPERATING = (ROOT / "desktop/mac/src/aion_operating_model_workspace.js").read_text(encoding="utf-8")
PROCUREMENT = (ROOT / "desktop/mac/src/aion_procurement_workspace.js").read_text(encoding="utf-8")
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
GATEWAY = (ROOT / "backend/modules/pilot_unified/workspace_gateway.py").read_text(encoding="utf-8")


def test_stock_and_procurement_is_connected_and_routable():
    assert '{ key: "procurement", icon: "S&P", label: "Stock & procurement" }' in APP
    assert 'departmentKey === "procurement"' in APP
    assert 'return renderProcurementWorkspaceSurface()' in APP
    assert 'isProcurementWorkspace = specialist.slug === "procurement"' in APP
    assert "Procurement Pilot · stock, sourcing and approval-gated purchasing" in APP


def test_procurement_has_standard_split_pilot_and_functional_workspace():
    for marker in (
        'data-aion-procurement-command-centre="true"',
        'data-aion-procurement-pilot-thread="true"',
        'data-aion-procurement-pilot-form="true"',
        'data-aion-procurement-split-handle="true"',
        'data-aion-procurement-workspace-pane="true"',
        'department_id: "procurement"',
    ):
        assert marker in APP


def test_procurement_workspace_owns_stock_purchases_and_suppliers():
    for marker in (
        "Stock on hand",
        "Purchasing list",
        "Suppliers and terms",
        "Save & update Boardroom",
        "No silent purchasing",
        "inventory_items",
        "procurement_queue",
        "suppliers",
    ):
        assert marker in PROCUREMENT
    assert '<script src="./aion_procurement_workspace.js"></script>' in INDEX


def test_products_and_services_no_longer_exposes_duplicate_stock_or_procurement_tabs():
    tabs = OPERATING[OPERATING.index("const TABS"):OPERATING.index("const state")]
    assert "['stock', 'Stock']" not in tabs
    assert "['procurement', 'Procurement']" not in tabs
    assert "Stock and purchasing live in Stock &amp; Procurement" in OPERATING


def test_procurement_chat_is_grounded_in_the_shared_operating_model():
    assert 'if department == "procurement"' in GATEWAY
    assert 'load_optional_dict(workspace_ref, "business_operating_model")' in GATEWAY
    assert '"provider": "business_operating_model_projection"' in GATEWAY
    assert '"external_writes_performed": False' in GATEWAY
    assert '"approval_gated": True' in GATEWAY
