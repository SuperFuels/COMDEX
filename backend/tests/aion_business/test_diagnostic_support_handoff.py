from __future__ import annotations

import json

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.diagnostic_support_handoff import DiagnosticSupportHandoffService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


def runtime(tmp_path):
    layout = provision_business_vault(
        tmp_path / "business-vault",
        business_name="Support Qualification",
        business_stable_id="support-qualification",
        application_root=tmp_path / "app",
        update_root=tmp_path / "update",
    )
    key = b"d" * 32
    guardian = VaultGuardian(
        layout, business_stable_id="support-qualification", encryption_key=key
    )
    return BusinessVaultRuntime(
        layout=layout,
        guardian=guardian,
        objects=VaultObjectStore(
            layout,
            guardian=guardian,
            business_stable_id="support-qualification",
            encryption_key=key,
        ),
    )


def test_diagnostic_export_waits_for_approval_and_contains_no_customer_content(tmp_path):
    value = runtime(tmp_path)
    service = DiagnosticSupportHandoffService(
        value,
        diagnostics_root=tmp_path / "node-state" / "diagnostics",
        export_root=tmp_path / "customer-exports",
    )
    failure = service.exercise_failure(failure_id="failure-1")
    preview = service.prepare(
        workspace_id="workspace-1",
        handoff_id="handoff-1",
        failure=failure,
        customer_approved=False,
        approved_by="",
    )
    assert preview["state"] == "awaiting_customer_approval"
    assert preview["export_created"] is False
    assert not list((tmp_path / "customer-exports").glob("*"))

    completed = service.prepare(
        workspace_id="workspace-1",
        handoff_id="handoff-1",
        failure=failure,
        customer_approved=True,
        approved_by="owner-1",
    )
    assert completed["state"] == "customer_approved_export_ready"
    bundle = (tmp_path / "customer-exports" / completed["export_file_name"]).read_text()
    assert "private prompt" not in bundle
    assert "raw/path" not in bundle
    assert "password" not in bundle.lower()
    assert json.loads(bundle)["redaction"] == {
        "documents_excluded": True,
        "personal_data_excluded": True,
        "prompts_excluded": True,
        "raw_paths_excluded": True,
        "secrets_excluded": True,
    }
    store = VaultDomainStore(value.guardian)
    assert len(store.list("support.records", workspace_id="workspace-1")) == 1
    assert len(store.list("security.audit", workspace_id="workspace-1")) == 1
    assert len(store.list("departments.operational_audit", workspace_id="workspace-1")) == 1
    replay = service.prepare(
        workspace_id="workspace-1",
        handoff_id="handoff-1",
        failure=failure,
        customer_approved=True,
        approved_by="owner-1",
    )
    assert replay["idempotent_replay"] is True
