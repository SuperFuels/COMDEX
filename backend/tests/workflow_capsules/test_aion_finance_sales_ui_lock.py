from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "desktop" / "mac" / "src" / "aion_finance_sales_workspace.js"
INDEX = ROOT / "desktop" / "mac" / "src" / "index.html"


def test_sales_receivables_workspace_is_packaged_and_honest():
    source = SOURCE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    assert "aion_finance_sales_workspace.js" in index
    assert "Sales, receivables & month-end" in source
    assert "Prepare reminder" in source
    assert "Reminder drafted only. Nothing was sent." in source
    assert "No period was closed and no tax was filed." in source
    assert "Link this customer to the matching Xero contact first" in source
    assert "data-fsw-actor" in source
