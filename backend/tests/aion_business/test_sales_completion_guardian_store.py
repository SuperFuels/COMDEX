from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.sales_completion_service import SalesCompletionService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.tests.test_finance_bookkeeping_service import configure


def test_sales_completion_restarts_from_encrypted_vault_without_plaintext(monkeypatch, tmp_path):
    repository, _authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"c" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    subject = SalesCompletionService(
        repository, domain_store=domains, object_store=objects,
    )
    enquiry = subject.sales.create_enquiry(
        "acme", name="Completion Customer", email="completion@example.test",
        phone="+34600123456", company_name=None, enquiry="Private completion requirement",
        source="website", source_reference="completion-guardian-1", attribution={},
        consent={}, created_by_person_id="person.owner",
    )
    opportunity_id = enquiry["opportunity"]["opportunity_id"]
    subject.set_availability(
        "acme", person_id="person.owner", timezone="Europe/Madrid",
        weekly_hours={"monday": [["09:00", "17:00"]]}, buffer_minutes=15,
        changed_by_person_id="person.owner",
    )
    booking = subject.prepare_booking(
        "acme", opportunity_id,
        starts_at=(datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat(),
        duration_minutes=45, assigned_person_id="person.owner", channel="Private site visit",
        prepared_by_person_id="person.owner",
    )
    outcome = subject.record_outcome(
        "acme", opportunity_id, disposition="won", value=1250,
        reason="Owner verified conversion", variant="control",
        authority_reference="provider:conversion:private-reference",
        recorded_by_person_id="person.owner",
    )

    restarted = SalesCompletionService(
        repository, domain_store=domains, object_store=objects,
    )
    assert restarted.get_availability("acme")["timezone"] == "Europe/Madrid"
    assert restarted.list_bookings("acme")[0]["booking_id"] == booking["booking_id"]
    audit = domains.get(
        "sales.audit", workspace_id="acme",
        entity_id=f"outcomes/{outcome['outcome_id']}",
    )["payload"]
    assert audit["outcome_hash"] == outcome["outcome_hash"]
    assert audit["disposition"] == "won"
    assert "reason" not in audit and "authority_reference" not in audit
    assert not (repository.base_dir / "acme" / "sales" / "completion").exists()
    assert b"Completion Customer" not in guardian.database.read_bytes()
    assert b"Private site visit" not in guardian.database.read_bytes()
