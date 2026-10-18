from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SETTINGS = (ROOT / "desktop/mac/src/aion_usage_billing_workspace.js").read_text(
    encoding="utf-8"
)
MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")


def test_business_configuration_settings_are_vault_backed_and_actionable():
    assert "global.AionBusinessContainerClient?.resolveBusinessId?.()" in SETTINGS
    assert "global.AionBusinessContainerClient?.canonicalBusinessId?.(candidate)" in SETTINGS
    assert 'return "business-not-registered"' in SETTINGS
    assert 'data-aion-business-identity-form="true"' in SETTINGS
    assert 'data-aion-business-policy-form="true"' in SETTINGS
    assert 'data-aion-custom-department-form="true"' in SETTINGS
    assert "/api/aion/business/data/business-identity/" in SETTINGS
    assert "/governance/facts" in SETTINGS
    assert "/governance/facts/${encodeURIComponent(proposed.fact.fact_id)}/review" in SETTINGS
    assert "/api/aion/business/data/custom-departments/" in SETTINGS


def test_custom_department_desktop_reader_uses_backend_not_legacy_runtime_files():
    reader_start = MAIN.index("async function readAionCustomDepartments")
    reader_end = MAIN.index("\n}", reader_start) + 2
    reader = MAIN[reader_start:reader_end]

    assert "/api/aion/business/data/custom-departments/" in reader
    assert ".runtime/AION_BUSINESS/business_containers" not in reader
    assert "department_intelligence.json" not in reader
