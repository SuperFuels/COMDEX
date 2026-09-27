import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService


def service(tmp_path: Path) -> WorkScheduleService:
    return WorkScheduleService(BusinessContainerRepository(tmp_path))


def test_desktop_and_mobile_share_the_same_canonical_job(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action("company", "create", {
        "title": "Roof survey", "customer": "Alex", "date": "2026-10-01", "time": "10:00",
        "duration": 90, "assignee": "James", "location": "1 High Street",
    }, actor_id="desktop")
    loaded = subject.get("company")

    assert loaded["items"][0]["id"] == created["jobs"][0]["id"]
    assert loaded["jobs"][0]["starts_at"] == "2026-10-01T10:00:00"
    assert loaded["jobs"][0]["customer"] == "Alex"


def test_reports_and_uploaded_evidence_are_real_files(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {
        "title": "Boiler service", "date": "2026-10-01", "time": "09:00",
    }, actor_id="desktop")
    item_id = model["items"][0]["id"]
    uploaded = subject.upload(
        "company", item_id, filename="photo.jpg", content_type="image/jpeg",
        data_base64=base64.b64encode(b"real image bytes").decode(), actor_id="phone",
    )
    generated = subject.generate_document("company", item_id, "service_report", actor_id="desktop")

    upload_path, _ = subject.file_path("company", item_id, uploaded["document"]["id"])
    report_path, _ = subject.file_path("company", item_id, generated["document"]["id"])
    assert upload_path.read_bytes() == b"real image bytes"
    assert report_path.read_bytes().startswith(b"%PDF-1.4")


def test_clashes_and_recurrence_are_calculated(tmp_path: Path) -> None:
    subject = service(tmp_path)
    first = subject.action("company", "create", {
        "title": "Weekly clinic", "date": "2026-10-01", "time": "10:00", "duration": 60,
        "assignee": "Dentist A", "resource_ids": ["Room 1"],
        "recurrence": {"frequency": "weekly", "count": 3},
    }, actor_id="office")
    assert len(first["items"]) == 3
    second = subject.action("company", "create", {
        "title": "Emergency appointment", "date": "2026-10-01", "time": "10:30", "duration": 30,
        "assignee": "Dentist B", "resource_ids": ["Room 1"],
    }, actor_id="office")
    assert second["conflicts"][0]["resources"] == ["Room 1"]


def test_natural_language_prepares_a_reviewable_draft(tmp_path: Path) -> None:
    result = service(tmp_path).interpret(
        "Book a roof survey for Alex next Tuesday at 10am and assign to James"
    )
    assert result["ready"] is True
    assert result["fields"]["title"] == "roof survey"
    assert result["fields"]["customer"] == "Alex"
    assert result["fields"]["assignee"] == "James"
    assert result["fields"]["time"] == "10:00"

    update = service(tmp_path).interpret("Move Alex roof survey to next Friday at 2pm")
    assert update["intent"] == "update_work"
    assert update["query"] == "Alex roof survey"
    assert update["fields"]["time"] == "14:00"


def test_revision_conflict_prevents_silent_overwrite(tmp_path: Path) -> None:
    subject = service(tmp_path)
    subject.action("company", "create", {"title": "Visit"}, actor_id="office")
    with pytest.raises(ValueError, match="work_schedule_revision_conflict"):
        subject.save("company", {"items": []}, expected_revision=0)


def test_delivery_records_stock_time_checklist_and_materials(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {"title": "Install roof"}, actor_id="office")
    item_id = model["items"][0]["id"]
    model = subject.action("company", "add_checklist", {"id": item_id, "label": "Photograph completed work"}, actor_id="engineer")
    checklist_id = model["items"][0]["checklist"][0]["id"]
    model = subject.action("company", "checklist", {"id": item_id, "checklist_id": checklist_id, "done": True}, actor_id="engineer")
    model = subject.action("company", "add_material", {"id": item_id, "name": "Roof tile", "quantity": 20, "unit": "tile", "unit_cost": "1.25"}, actor_id="engineer")
    model = subject.action("company", "add_time", {"id": item_id, "minutes": 90, "note": "Installation"}, actor_id="engineer")
    model = subject.action("company", "stock_movement", {"id": item_id, "name": "Roof tile", "quantity": 20, "movement_type": "use"}, actor_id="engineer")

    item = model["items"][0]
    assert item["checklist"][0]["done"] is True
    assert item["materials"][0]["unit_cost"] == "1.25"
    assert item["time_entries"][0]["minutes"] == 90
    assert model["stock_movements"][0]["quantity"] == -20


def test_numbered_quote_and_customer_portal_actions(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {
        "title": "Boiler service", "customer": "Alex", "date": "2026-10-01", "time": "09:00",
    }, actor_id="office")
    item_id = model["items"][0]["id"]
    generated = subject.generate_document(
        "company", item_id, "quote", actor_id="office",
        line_items=[{"description": "Service labour", "quantity": 2, "unit_price": "50"}], tax_rate="20",
    )
    assert generated["commercial"]["number"] == "Q-2026-0001"
    assert generated["commercial"]["total"] == "120.00"

    access = subject.issue_portal_access("company", item_id, actor_id="office")
    view = subject.portal_view(access["token"])
    assert view["item"]["customer"] == "Alex"
    changed = subject.portal_action(access["token"], "approve_quote", {})
    assert changed["item"]["quote"]["status"] == "customer_approved"


def test_due_reminders_are_prepared_but_not_claimed_as_sent(tmp_path: Path) -> None:
    subject = service(tmp_path)
    subject.action("company", "create", {
        "title": "Survey", "customer": "Alex", "customer_email": "alex@example.com",
        "date": "2026-10-01", "time": "10:00",
    }, actor_id="office")
    model = subject.prepare_due_reminders("company", now=datetime(2026, 9, 30, 10, 0, tzinfo=UTC))
    assert model["reminders"][0]["status"] == "needs_approval"
    assert model["reminders"][0]["channel"] == "email"
