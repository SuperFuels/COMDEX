from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.cybersecurity_guard_service import (
    CybersecurityGuardScheduler,
)
from backend.modules.aion_business.runtime.support_polling_service import (
    SupportPollingService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _store(tmp_path) -> VaultDomainStore:
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Acme-acme.business-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"b" * 32
    )
    return VaultDomainStore(guardian)


def test_support_poller_discovers_only_guardian_polling_configurations(
    monkeypatch, tmp_path
):
    store = _store(tmp_path)
    store.put(
        "support.records",
        workspace_id="acme",
        entity_id="configuration/polling",
        payload={"enabled": True},
    )
    store.put(
        "support.records",
        workspace_id="other",
        entity_id="cases/case-1",
        payload={"status": "open"},
    )
    polled = []

    class Service:
        domain_store = store

        def poll_sources(self, workspace_id):
            polled.append(workspace_id)
            return {"ok": True}

    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.support_polling_service.SupportCaseService",
        Service,
    )

    assert SupportPollingService().tick() == {"acme": {"ok": True}}
    assert polled == ["acme"]


def test_security_scheduler_discovers_only_guardian_guard_states(tmp_path):
    store = _store(tmp_path)
    store.put(
        "security.records",
        workspace_id="acme",
        entity_id="guard/state",
        payload={"status": "active"},
    )
    store.put(
        "security.records",
        workspace_id="other",
        entity_id="finding/finding-1",
        payload={"status": "open"},
    )
    scanned = []

    class Service:
        domain_store = store
        root = tmp_path / "legacy-security"

        def run_safe_scan(self, workspace_id, *, actor_id):
            scanned.append((workspace_id, actor_id))
            return {"scan_run": {"run_id": "scan-1"}}

    assert CybersecurityGuardScheduler(Service()).run_once() == [
        {"workspace_id": "acme", "ok": True, "run_id": "scan-1"}
    ]
    assert scanned == [("acme", "cybersecurity_guard_scheduler")]


def test_desktop_pilot_scheduler_is_fail_closed_in_guardian_mode():
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[2] / "desktop_app.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _run_due_desktop_pilot_work")
    end = source.index("\ndef _desktop_pilot_scheduler_loop", start)
    block = source[start:end]
    assert "if guardian_mode_requested():" in block
    assert block.index("if guardian_mode_requested():") < block.index(
        "AIONBusinessPaths.BUSINESS_CONTAINERS"
    )
