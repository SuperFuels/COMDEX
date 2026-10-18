from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.business_vault_portable_transfer import (
    BusinessVaultPortableExportService,
    BusinessVaultPortableTransferError,
    LegacyBusinessImportService,
)
from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


def runtime(tmp_path: Path) -> BusinessVaultRuntime:
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Qualification Ltd",
        business_stable_id="qualification-ltd",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="qualification-ltd", encryption_key=b"v" * 32
    )
    return BusinessVaultRuntime(
        layout=layout,
        guardian=guardian,
        objects=VaultObjectStore(
            layout,
            guardian=guardian,
            business_stable_id="qualification-ltd",
            encryption_key=b"v" * 32,
        ),
    )


def legacy_source(tmp_path: Path) -> Path:
    source = tmp_path / "legacy-business"
    originals = source / "originals"
    originals.mkdir(parents=True)
    (source / "business_map.json").write_text(
        json.dumps({"name": "Legacy qualification business", "revision": 7})
    )
    (source / "departments_map.json").write_text(
        json.dumps({"departments": [{"id": "operations"}, {"id": "quality"}]})
    )
    (source / "automations.json").write_text(
        json.dumps({"automations": [{"id": "weekly-review", "enabled": True}]})
    )
    (originals / "customer-handbook.txt").write_text("Private legacy handbook")
    return source


def test_legacy_import_dry_run_copy_verify_receipt_and_source_retention(tmp_path):
    vault_runtime = runtime(tmp_path)
    source = legacy_source(tmp_path)
    before = {path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()}
    service = LegacyBusinessImportService(vault_runtime)

    dry_run = service.inspect(source_root=source, migration_id="migration-25")
    assert dry_run["mode"] == "dry_run"
    assert dry_run["record_candidate_count"] == 3
    assert dry_run["original_candidate_count"] == 1
    assert dry_run["source_retained"] is True

    result = service.execute(
        workspace_id="qualification-ltd",
        source_root=source,
        migration_id="migration-25",
    )
    assert result["state"] == "copied_verified_source_retained"
    assert result["verified_record_count"] == 3
    assert result["verified_original_count"] == 1
    assert result["source_delete_permitted"] is False
    assert before == {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }

    replay = service.execute(
        workspace_id="qualification-ltd",
        source_root=source,
        migration_id="migration-25",
    )
    assert replay["idempotent_replay"] is True
    store = VaultDomainStore(vault_runtime.guardian)
    assert len(store.list("vault.migration_receipts", workspace_id="qualification-ltd")) == 1
    assert len(store.list("file_cabinet.governance", workspace_id="qualification-ltd")) == 1
    tree = store.get("file_cabinet.tree", workspace_id="qualification-ltd", entity_id="tree")
    assert tree["payload"]["root"]["children"][0]["children"][0]["name"] == "customer-handbook.txt"


def test_legacy_import_replay_fails_closed_if_source_changes(tmp_path):
    vault_runtime = runtime(tmp_path)
    source = legacy_source(tmp_path)
    service = LegacyBusinessImportService(vault_runtime)
    service.execute(
        workspace_id="qualification-ltd", source_root=source, migration_id="migration-25"
    )
    (source / "business_map.json").write_text(json.dumps({"revision": 8}))
    with pytest.raises(BusinessVaultPortableTransferError, match="source_changed"):
        service.execute(
            workspace_id="qualification-ltd", source_root=source, migration_id="migration-25"
        )


def test_encrypted_whole_business_export_readback_includes_required_state(tmp_path):
    vault_runtime = runtime(tmp_path)
    LegacyBusinessImportService(vault_runtime).execute(
        workspace_id="qualification-ltd",
        source_root=legacy_source(tmp_path),
        migration_id="migration-25",
    )
    service = BusinessVaultPortableExportService(vault_runtime)
    export = service.create_export(
        workspace_id="qualification-ltd",
        export_id="whole-business-25",
        destination_root=tmp_path / "customer-export",
        passphrase="correct horse battery staple",
        created_at="2026-10-18T06:30:00+00:00",
    )
    raw = export.read_bytes()
    assert b"Private legacy handbook" not in raw
    assert b"Legacy qualification business" not in raw
    assert export.stat().st_mode & 0o777 == 0o600

    payload = service.readback(
        export_path=export, passphrase="correct horse battery staple"
    )
    summary = service.summary(payload)
    manifest = summary["manifest"]
    assert manifest["includes_maps"] is True
    assert manifest["includes_departments"] is True
    assert manifest["includes_automations"] is True
    assert manifest["includes_originals"] is True
    assert all(manifest["required_coverage"].values())
    assert summary["original_count"] == 1
    assert summary["all_originals_verified"] is True
    assert len(summary["originals_manifest_sha256"]) == 64
    assert "originals" not in summary
    assert summary["customer_content_in_response"] is False
    assert service.create_export(
        workspace_id="qualification-ltd",
        export_id="whole-business-25",
        destination_root=tmp_path / "customer-export",
        passphrase="correct horse battery staple",
    ) == export


def test_export_wrong_passphrase_and_tampering_fail_closed(tmp_path):
    vault_runtime = runtime(tmp_path)
    LegacyBusinessImportService(vault_runtime).execute(
        workspace_id="qualification-ltd",
        source_root=legacy_source(tmp_path),
        migration_id="migration-25",
    )
    service = BusinessVaultPortableExportService(vault_runtime)
    export = service.create_export(
        workspace_id="qualification-ltd",
        export_id="whole-business-25",
        destination_root=tmp_path / "customer-export",
        passphrase="correct horse battery staple",
    )
    with pytest.raises(BusinessVaultPortableTransferError, match="decryption_failed"):
        service.readback(export_path=export, passphrase="this passphrase is wrong")

    envelope = json.loads(export.read_text())
    envelope["ciphertext_sha256"] = "0" * 64
    export.write_text(json.dumps(envelope))
    with pytest.raises(BusinessVaultPortableTransferError, match="ciphertext_integrity_failed"):
        service.readback(export_path=export, passphrase="correct horse battery staple")
