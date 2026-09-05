from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from backend.modules.aion_business.contracts.sovereign_brain import CANONICAL_STORE_KINDS
from backend.modules.aion_business.runtime.sovereign_brain_setup import (
    HardwareProfiler,
    BusinessRequirementsProfiler,
    SovereignBrainSetup,
    public_setup_choices,
)
from backend.modules.aion_business.runtime.sovereign_setup_service import build_handler
from backend.modules.aion_fabric.identity import IdentityStore


def test_hardware_profile_contains_capacity_not_stable_identity(tmp_path):
    profile = HardwareProfiler.profile(tmp_path)
    assert profile["cpu_count"] >= 1
    assert profile["storage_free_bytes"] > 0
    assert profile["contains_stable_device_identifier"] is False
    assert "hostname" not in profile
    assert "serial" not in profile


@pytest.mark.parametrize(
    ("memory_gib", "disk_gib", "tier"),
    [(8, 8, "lite"), (16, 12, "standard"), (32, 30, "capable"), (96, 80, "workstation")],
)
def test_model_plan_is_hardware_bounded(memory_gib, disk_gib, tier):
    plan = HardwareProfiler.model_plan(
        {"memory_bytes": memory_gib * 1024**3, "storage_free_bytes": disk_gib * 1024**3}
    )
    assert plan["tier"] == tier
    assert plan["local_core_supported"] is True
    assert plan["automatic_model_download"] is False


def test_business_requirements_activate_modules_without_size_label():
    profile = BusinessRequirementsProfiler.profile({
        "legal_entities": 3, "locations": 8, "countries": 2, "currencies": 2,
        "users": 80, "project_budgeting": True, "external_collaborators": True,
        "approval_levels": 2, "separation_of_duties": True,
        "enterprise_identity": True, "regulated_data": True, "private_compute": True,
    })
    assert profile["business_size_label_used"] is False
    assert "project_operations" in profile["recommended_modules"]
    assert "multi_entity_group" in profile["recommended_modules"]
    assert "regulated_data_controls" in profile["recommended_modules"]
    assert profile["commercial_entitlement_decided_separately"] is True


def test_clean_first_run_creates_empty_provider_free_brain(tmp_path, monkeypatch):
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    setup = SovereignBrainSetup(tmp_path / "customer-brain")
    first = setup.initialize(owner_display_name="Test Owner", business_requirements={"project_budgeting": True})
    second = setup.initialize(owner_display_name="Test Owner", business_requirements={"project_budgeting": True})
    assert first["ok"] is True
    assert first["brain_id"] == second["brain_id"]
    assert first["provider_keys_required"] is False
    assert first["demo_data_installed"] is False
    assert first["business_requirements"]["recommended_modules"] == ["core_business_brain", "boardroom_core", "project_operations"]
    assert set(first["canonical_stores"]) == set(CANONICAL_STORE_KINDS)
    for kind in CANONICAL_STORE_KINDS:
        store = json.loads((setup.root / "brain" / "stores" / f"{kind}.json").read_text())
        if kind == "business_map":
            assert len(store["records"]) == 1
            assert store["records"][0]["source_of_truth"] == "boardroom_business_containers"
            assert store["records"][0]["workspace_ids"] == []
            assert "facts" not in store["records"][0]
        else:
            assert store["records"] == []
    with pytest.raises(PermissionError, match="already owned"):
        setup.initialize(owner_display_name="Different Owner")


def test_vault_encrypts_secret_and_exposes_only_binding(tmp_path):
    setup = SovereignBrainSetup(tmp_path / "customer-brain")
    setup.initialize(owner_display_name="Test Owner")
    receipt = setup.vault.set_secret("provider.gemini.primary", "super-private-api-key")
    assert receipt["secret_exposed"] is False
    assert setup.vault.get_secret("provider.gemini.primary") == "super-private-api-key"
    assert b"super-private-api-key" not in setup.vault.data_path.read_bytes()
    status = setup.vault.status()
    assert status["bindings"] == ["provider.gemini.primary"]
    assert "super-private-api-key" not in json.dumps(status)
    assert setup.vault.delete_secret("provider.gemini.primary") is True
    assert setup.vault.get_secret("provider.gemini.primary") == ""


def test_vault_tampering_fails_authentication(tmp_path):
    setup = SovereignBrainSetup(tmp_path / "customer-brain")
    setup.initialize(owner_display_name="Test Owner")
    setup.vault.set_secret("provider.test.primary", "secret value")
    envelope = json.loads(setup.vault.data_path.read_text())
    envelope["ciphertext"] = envelope["ciphertext"][:-4] + "AAAA"
    setup.vault.data_path.write_text(json.dumps(envelope))
    with pytest.raises(PermissionError, match="decrypted or authenticated"):
        setup.vault.status()


def test_repair_restores_regenerable_metadata_but_not_identity(tmp_path):
    setup = SovereignBrainSetup(tmp_path / "customer-brain")
    setup.initialize(owner_display_name="Test Owner")
    setup.model_plan_path.unlink()
    assert setup.repair()["ok"] is True
    identity_store = IdentityStore(setup.root / "identity")
    identity_store.private_path.unlink()
    status = setup.status()
    assert status["state"] == "restore_required"
    assert not identity_store.private_path.exists()
    with pytest.raises(RuntimeError, match="restore an encrypted backup"):
        setup.repair()


def test_complete_export_restore_preserves_logical_brain_and_vault(tmp_path):
    setup = SovereignBrainSetup(tmp_path / "source-brain")
    original = setup.initialize(
        owner_display_name="Test Owner", deployment_profile="home_server", customer_compute="customer_server"
    )
    setup.vault.set_secret("provider.private.endpoint", "private endpoint credential")
    source_identity = IdentityStore(setup.root / "identity").load_or_create()
    package = tmp_path / "exports" / "brain.pilotmigration"
    exported = setup.create_complete_export(
        destination=package, passphrase="a long sovereign backup phrase"
    )
    assert exported["verified"] is True
    assert b"private endpoint credential" not in package.read_bytes()

    restored = SovereignBrainSetup.restore_complete_export(
        package=package,
        destination=tmp_path / "restored-brain",
        passphrase="a long sovereign backup phrase",
        source_public_key=source_identity.public_key_b64,
    )
    assert restored["logical_brain_preserved"] is True
    assert restored["brain_status"]["brain_id"] == original["brain_id"]
    restored_setup = SovereignBrainSetup(tmp_path / "restored-brain")
    assert restored_setup.vault.get_secret("provider.private.endpoint") == "private endpoint credential"


def test_public_choices_default_to_local_without_provider_key():
    choices = public_setup_choices()
    assert choices["default_deployment"] == "personal_computer"
    assert choices["default_intelligence_location"] == "local"
    assert choices["provider_keys_required"] is False
    assert any(item["id"] == "customer_cloud" for item in choices["intelligence_locations"])


def test_local_setup_wizard_creates_brain_and_rejects_unmarked_posts(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(tmp_path / "wizard-brain"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(base + "/", timeout=2).read().decode("utf-8")
        assert "Make this Pilot yours" in page
        assert "No provider key was required" in page
        raw = json.dumps(
            {
                "owner_display_name": "Wizard Owner",
                "deployment_profile": "personal_computer",
                "customer_compute": "local",
            }
        ).encode("utf-8")
        unmarked = urllib.request.Request(
            base + "/api/setup", data=raw, method="POST", headers={"Content-Type": "application/json"}
        )
        with pytest.raises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(unmarked, timeout=2)
        assert rejected.value.code == 403
        marked = urllib.request.Request(
            base + "/api/setup",
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json", "X-AION-Setup": "local-wizard-v1"},
        )
        result = json.loads(urllib.request.urlopen(marked, timeout=3).read())
        assert result["ok"] is True
        assert result["provider_keys_required"] is False
        status = json.loads(urllib.request.urlopen(base + "/api/status", timeout=2).read())
        assert status["brain_id"] == result["brain_id"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
