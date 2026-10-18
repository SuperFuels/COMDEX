from __future__ import annotations

import json
import os

import pytest

from backend.modules.aion_business.runtime.business_retention_closure import BusinessRetentionClosureService
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


def fixture(tmp_path):
    layout = provision_business_vault(
        tmp_path / "business-vault",
        business_name="Closure Qualification",
        business_stable_id="closure-qualification",
        application_root=tmp_path / "app",
        update_root=tmp_path / "update",
    )
    key = b"c" * 32
    guardian = VaultGuardian(
        layout, business_stable_id="closure-qualification", encryption_key=key
    )
    runtime = BusinessVaultRuntime(
        layout=layout,
        guardian=guardian,
        objects=VaultObjectStore(
            layout,
            guardian=guardian,
            business_stable_id="closure-qualification",
            encryption_key=key,
        ),
    )
    VaultDomainStore(guardian).put(
        "business.identity",
        workspace_id="workspace-1",
        entity_id="identity",
        payload={"business_name": "Private Business"},
        expected_version=None,
        idempotency_key="identity",
    )
    export = tmp_path / "export.tessaris-export"
    export.write_text(json.dumps({"schema_version": "tessaris.business-portable-export.v1"}))
    os.chmod(export, 0o600)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "snapshot.json").write_text(json.dumps({
        "schema_version": "tessaris.business-vault-snapshot.v1",
        "key_material_in_snapshot": False,
    }))
    return runtime, export, snapshot


def test_closure_preview_requires_reauthentication_and_never_destroys(tmp_path):
    runtime, export, snapshot = fixture(tmp_path)
    service = BusinessRetentionClosureService(runtime)
    with pytest.raises(PermissionError, match="reauthentication"):
        service.preview(
            workspace_id="workspace-1", closure_id="closure-1",
            customer_export_path=export, backup_snapshot_path=snapshot,
            reauthentication_verified=False, confirmation_phrase="PREVIEW CLOSE workspace-1",
        )
    result = service.preview(
        workspace_id="workspace-1", closure_id="closure-1",
        customer_export_path=export, backup_snapshot_path=snapshot,
        reauthentication_verified=True, confirmation_phrase="PREVIEW CLOSE workspace-1",
    )
    assert result["state"] == "preview_complete_no_destruction"
    assert result["destructive_action_executed"] is False
    assert result["application_update_has_vault_delete_authority"] is False
    assert result["tombstoned_history_recoverable"] is True
    assert result["preclosure_customer_export"]["verified"] is True
    assert result["preclosure_backup"]["verified"] is True
    replay = service.preview(
        workspace_id="workspace-1", closure_id="closure-1",
        customer_export_path=export, backup_snapshot_path=snapshot,
        reauthentication_verified=True, confirmation_phrase="PREVIEW CLOSE workspace-1",
    )
    assert replay["idempotent_replay"] is True
