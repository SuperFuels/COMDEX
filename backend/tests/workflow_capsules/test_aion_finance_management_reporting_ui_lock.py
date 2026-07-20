from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
BRIDGE = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(
    encoding="utf-8"
)


def test_management_account_ui_remains_in_modular_department_pilot_bridge():
    assert "aion_department_pilot_backend.js" in INDEX
    assert "function financeManagementHandback" in BRIDGE
    assert "data-aion-finance-management-handback" in BRIDGE
    assert "Management account" in BRIDGE
    assert "Budget variance" in BRIDGE
    assert "Previous period" in BRIDGE
    assert "Evidence:" in BRIDGE


def test_management_account_ui_exposes_missing_comparisons_and_warnings():
    assert "No budget comparison" in BRIDGE
    assert "No previous period comparison" in BRIDGE
    assert "evidence or reporting warning" in BRIDGE
    assert ".aion-finance-management-kpis" in BRIDGE
