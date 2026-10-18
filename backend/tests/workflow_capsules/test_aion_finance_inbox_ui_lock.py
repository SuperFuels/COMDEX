from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
SOURCE = (ROOT / "desktop/mac/src/aion_finance_inbox_workspace.js").read_text(encoding="utf-8")


def test_finance_inbox_loads_after_app_and_hr_authority():
    assert INDEX.index("app.js") < INDEX.index("aion_finance_inbox_workspace.js")
    assert INDEX.index("aion_hr_people_workspace.js") < INDEX.index("aion_finance_inbox_workspace.js")


def test_finance_inbox_exposes_daily_capture_review_and_approval_workflow():
    assert "data-aion-finance-inbox" in SOURCE
    assert "data-fiw-upload-form" in SOURCE
    assert 'capture="environment"' in SOURCE
    assert "data-fiw-review-form" in SOURCE
    assert "data-fiw-decision-form" in SOURCE
    assert "Approved provider-neutral accounting draft created. Nothing was posted externally." in SOURCE
    assert "data-fiw-read-document" in SOURCE
    assert "/extract" in SOURCE
    assert "Reader suggestions · human confirmation required" in SOURCE
    assert "The receipt cannot answer these" in SOURCE
    assert "Expense rules" in SOURCE
    assert "meal_receipt_limit" in SOURCE
    assert "mileage_rate" in SOURCE
    assert "receipt_reader_provider" in SOURCE
    assert "Automatic — first available cloud reader" in SOURCE
    assert "Local Gemma is explicit-only" in SOURCE
    assert "reader_providers" in SOURCE
    assert "data-fiw-prepare-bookkeeping" in SOURCE
    assert "data-fiw-bookkeeping-form" in SOURCE
    assert "/api/aion/finance-bookkeeping/" in SOURCE
    assert "Accounting connections" in SOURCE
    assert "Kept separate from provider actuals to prevent double-counting." in SOURCE
    assert "data-fiw-prepare-xero" in SOURCE
    assert "data-fiw-xero-form" in SOURCE
    assert "Create and verify in Xero" in SOURCE
    assert "xero_contact_id" in SOURCE
    assert "/bookkeeping-exports" in SOURCE
    assert "data-fiw-new-xero-supplier" in SOURCE
    assert "data-fiw-xero-supplier-form" in SOURCE
    assert "/supplier-contacts" in SOURCE
    assert "Phone photo / mobile app" not in SOURCE  # channel labels come from the canonical backend contract


def test_finance_inbox_is_mutation_safe_and_uses_canonical_authority():
    assert "new MutationObserver(scheduleInstall)" in SOURCE
    assert "requestAnimationFrame(installIfPresent)" in SOURCE
    assert "/api/aion/business/organisation/" in SOURCE
    assert "/api/aion/business/finance-inbox/" in SOURCE
