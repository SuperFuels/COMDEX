from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]


def test_settings_usage_billing_surface_is_loaded_and_routed():
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    index = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
    workspace = (ROOT / "desktop/mac/src/aion_usage_billing_workspace.js").read_text(
        encoding="utf-8"
    )
    assert '{ key: "settings", label: "Settings" }' in app
    assert 'state.activeTab === "settings"' in app
    assert "AionUsageBillingWorkspace" in app
    assert './aion_usage_billing_workspace.js' in index
    assert "Your local intelligence is free." in workspace
    assert "private_content_included !== false" in workspace
    assert "localStorage" not in workspace
    assert "setSignedPhotonSnapshot" not in workspace
    assert "setBillingRecords" not in workspace
    assert "Signed wallet and receipt state is intentionally not renderer-settable" in workspace


def test_usage_billing_surface_does_not_claim_unverified_balance_or_tax_invoice():
    workspace = (ROOT / "desktop/mac/src/aion_usage_billing_workspace.js").read_text(
        encoding="utf-8"
    )
    assert "A signed billing session has not been connected" in workspace
    assert "not presented as a statutory tax invoice" in workspace
    assert "Payment cards stay with Revolut" in workspace


def test_photon_desktop_broker_verifies_signed_content_free_views():
    preload = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")
    main = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
    workspace = (ROOT / "desktop/mac/src/aion_usage_billing_workspace.js").read_text(
        encoding="utf-8"
    )
    assert "aion-photon-billing-view" in preload
    assert "aion-photon-billing-view" in main
    assert "getPhotonBillingView" in workspace
    assert "exportPhotonBillingRecords" in workspace
    assert "TESSARIS_PHOTON_AUTHORITY_PUBLIC_KEY_PATH" in main
    assert "createPhotonSecureSessionStore" in main
    assert "photon-desktop-session.enc.json" in main
    assert "aion-photon-billing-export" in preload
    assert "aion-photon-billing-export" in main
    assert "fields.map((field) => photonCsvCell(record[field]))" in main
    result = subprocess.run(
        ["node", "--test", "desktop/mac/electron/photon-billing-broker.test.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    secure_store = subprocess.run(
        ["node", "--test", "desktop/mac/electron/photon-secure-session-store.test.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert secure_store.returncode == 0, secure_store.stdout + secure_store.stderr
