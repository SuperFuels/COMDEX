from __future__ import annotations

import base64

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import DepartmentOperationalStore
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService


def _service(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"w" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    return WorkScheduleService(
        domain_store=VaultDomainStore(guardian), object_store=objects,
    ), guardian, objects


def test_work_customer_quote_and_evidence_round_trip_only_through_vault(tmp_path):
    subject, guardian, objects = _service(tmp_path)
    created = subject.action(
        "acme", "create",
        {"title": "Private roof survey", "customer": "Alex Secret", "customer_email": "alex@example.com"},
        actor_id="person:founder",
    )
    item_id = created["items"][0]["id"]
    uploaded = subject.upload(
        "acme", item_id, filename="roof-secret.txt", content_type="text/plain",
        data_base64=base64.b64encode(b"private customer evidence").decode(),
        actor_id="person:engineer",
    )
    report = subject.generate_document("acme", item_id, "service_report", actor_id="person:founder")

    restarted = WorkScheduleService(
        domain_store=subject.domain_store, object_store=subject.object_store,
    )
    loaded = restarted.get("acme")
    assert loaded["items"][0]["customer"] == "Alex Secret"
    evidence, evidence_document = restarted.file_bytes("acme", item_id, uploaded["document"]["id"])
    generated, generated_document = restarted.file_bytes("acme", item_id, report["document"]["id"])
    assert evidence == b"private customer evidence"
    assert generated.startswith(b"%PDF-1.4")
    assert evidence_document["vault_object_id"]
    assert generated_document["vault_object_id"]
    assert b"Alex Secret" not in guardian.database.read_bytes()
    assert b"private customer evidence" not in b"".join(path.read_bytes() for path in objects.objects.rglob("*.tvobj"))


def test_customer_portal_token_resolves_without_scanning_application_files(tmp_path):
    subject, _guardian, _objects = _service(tmp_path)
    created = subject.action("acme", "create", {"title": "Survey", "customer": "Alex"}, actor_id="office")
    item_id = created["items"][0]["id"]
    access = subject.issue_portal_access("acme", item_id, actor_id="office")

    view = subject.portal_view(access["token"])

    assert view["workspace_id"] == "acme"
    assert view["item"]["id"] == item_id


def test_schedule_lifecycle_has_immutable_operational_audit(tmp_path):
    subject, _guardian, _objects = _service(tmp_path)
    created = subject.action(
        "acme", "create",
        {"title": "Commission boiler", "date": "2026-11-20", "assignee": "Engineer A"},
        actor_id="office",
    )
    item_id = created["items"][0]["id"]
    updated = subject.action(
        "acme", "update",
        {"id": item_id, "date": "2026-11-21", "assignee": "Engineer B", "status": "completed"},
        actor_id="engineer",
    )

    audit = DepartmentOperationalStore(domain_store=subject.domain_store).list_audit(
        workspace_id="acme", department_id="operations", feature_id="work_schedule",
    )

    assert updated["items"][0]["status"] == "completed"
    assert [row["payload"]["kind"] for row in audit] == [
        "work_created", "work_rescheduled_or_assigned", "work_status_changed",
    ]
    assert all(row["payload"]["work_item_id"] == item_id for row in audit)


def test_stock_movement_has_immutable_operational_audit(tmp_path):
    subject, _guardian, _objects = _service(tmp_path)

    saved = subject.action(
        "acme",
        "stock_movement",
        {
            "id": "inventory.filter-cartridge",
            "name": "Filter cartridge",
            "quantity": 12,
            "movement_type": "receive",
        },
        actor_id="operations-manager",
    )
    audit = DepartmentOperationalStore(domain_store=subject.domain_store).list_audit(
        workspace_id="acme", department_id="operations", feature_id="work_schedule",
    )

    assert saved["stock_movements"][0]["quantity"] == 12
    assert [row["payload"]["kind"] for row in audit] == ["stock_movement_recorded"]
    assert audit[0]["payload"]["inventory_item_id"] == "inventory.filter-cartridge"
    assert audit[0]["payload"]["movement_type"] == "receive"


def test_mobile_evidence_retry_reuses_one_encrypted_vault_object(tmp_path):
    subject, guardian, objects = _service(tmp_path)
    created = subject.action(
        "acme", "create", {"title": "Field inspection", "assignee": "Engineer A"},
        actor_id="office",
    )
    item_id = created["items"][0]["id"]
    encoded = base64.b64encode(b"one encrypted mobile photograph").decode()

    first = subject.upload(
        "acme", item_id, filename="field.jpg", content_type="image/jpeg",
        data_base64=encoded, actor_id="mobile-engineer",
        idempotency_key="field-photo-vault-001",
    )
    replay = subject.upload(
        "acme", item_id, filename="field.jpg", content_type="image/jpeg",
        data_base64=encoded, actor_id="mobile-engineer",
        idempotency_key="field-photo-vault-001",
    )

    assert replay["idempotent_replay"] is True
    assert replay["document"]["vault_object_id"] == first["document"]["vault_object_id"]
    assert len(list(objects.objects.rglob("*.tvobj"))) == 1
    assert b"one encrypted mobile photograph" not in guardian.database.read_bytes()
    assert b"one encrypted mobile photograph" not in next(objects.objects.rglob("*.tvobj")).read_bytes()

    subject.action(
        "acme", "add_update", {"id": item_id, "text": "Field reading recorded"},
        actor_id="mobile-engineer", idempotency_key="field-update-vault-001",
    )
    audit = DepartmentOperationalStore(domain_store=subject.domain_store).list_audit(
        workspace_id="acme", department_id="operations", feature_id="work_schedule",
    )
    assert [row["payload"]["kind"] for row in audit] == [
        "work_created", "work_evidence_added", "work_update_added",
    ]
