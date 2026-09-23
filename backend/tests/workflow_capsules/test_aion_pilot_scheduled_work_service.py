from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.modules.aion_business.runtime.pilot_scheduled_work_service import PilotScheduledWorkService


class _Authority:
    def access_decision(self, workspace_id, *, person_id, capability, **kwargs):
        return {"allowed": person_id == "owner-1", "capability": capability, "workspace_id": workspace_id}


class _Revenue:
    def import_gmail_messages(self, workspace_id, *, messages, imported_by_person_id):
        assert imported_by_person_id == "owner-1"
        return {"imported": 1, "deduplicated": 0, "skipped": [], "opportunities": [{
            "opportunity_id": "opp-1", "title": "Pergola enquiry", "enquiry": "Is the pergola aluminium?",
            "contact": {"name": "Jamie Example", "email": "jamie@example.test"},
        }], "gmail_mutated": False, "reply_sent": False}


class _Completion:
    def __init__(self):
        self.prepared = []

    def prepare_message(self, workspace_id, opportunity_id, **kwargs):
        self.prepared.append(kwargs)
        return {"message_id": "msg-1", "message_hash": "hash-message", "payload_hash": "hash-payload",
                "status": "exact_approval_required", "external_message_sent": False}


class _Knowledge:
    def search(self, workspace_id, query, *, actor_scope, limit):
        assert actor_scope == "sales"
        return {"matches": [{"claim_id": "claim-1", "source_hash": "sha256:source",
                              "text": "The pergola frame is aluminium."}],
                "receipt": {"receipt_id": "receipt-1", "claim_ids": ["claim-1"]}}


def _service(tmp_path):
    completion = _Completion()
    service = PilotScheduledWorkService(
        base_dir=tmp_path, authority=_Authority(), revenue=_Revenue(), completion=completion,
        knowledge=_Knowledge(), gmail_fetcher=lambda query, limit: [{
            "id": "gmail-1", "from": "Jamie <jamie@example.test>", "subject": "Pergola enquiry",
            "body": "Is the pergola aluminium?",
        }])
    return service, completion


def test_schedule_is_durable_disabled_by_default_and_hash_checked(tmp_path):
    service, _ = _service(tmp_path)
    created = service.create("company", title="Sales inbox", job_type="sales_inbox_monitor",
                             cadence_minutes=15, created_by_person_id="owner-1")
    assert created["enabled"] is False
    assert created["external_side_effects"] == "forbidden_during_schedule_run"
    resumed, _ = _service(tmp_path)
    listing = resumed.list("company")
    assert listing["summary"]["total"] == 1
    assert listing["schedules"][0]["schedule_hash"] == created["schedule_hash"]


def test_due_sales_inbox_run_prepares_cited_message_and_never_sends(tmp_path):
    service, completion = _service(tmp_path)
    created = service.create("company", title="Sales inbox", job_type="sales_inbox_monitor",
                             cadence_minutes=5, created_by_person_id="owner-1", enabled=True)
    due = datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=6)
    runs = service.run_due("company", now=due)
    assert len(runs) == 1
    result = runs[0]["result"]
    assert result["status"] == "approval_required"
    assert result["external_messages_sent"] == 0
    assert result["gmail_mutated"] is False
    assert result["awaiting_approval_count"] == 1
    assert result["prepared"][0]["knowledge_receipt"]["claim_ids"] == ["claim-1"]
    assert result["prepared"][0]["artifact"]["status"] == "human_review_required"
    assert "aluminium" in completion.prepared[0]["body"]
    assert service.list("company")["schedules"][0]["last_run_id"] == runs[0]["run_id"]


def test_schedule_rejects_untrusted_actor_and_too_fast_loop(tmp_path):
    service, _ = _service(tmp_path)
    try:
        service.create("company", title="Bad", job_type="sales_inbox_monitor", cadence_minutes=1,
                       created_by_person_id="owner-1")
        raise AssertionError("expected cadence rejection")
    except ValueError:
        pass
    try:
        service.create("company", title="Bad", job_type="sales_inbox_monitor", cadence_minutes=5,
                       created_by_person_id="unknown")
        raise AssertionError("expected authority rejection")
    except PermissionError:
        pass
