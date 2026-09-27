from backend.modules.aion_business.runtime.work_notification_delivery import WorkNotificationDeliveryService


class FakeSchedule:
    def __init__(self):
        self.model = {
            "revision": 3,
            "reminders": [{"id": "reminder-1", "status": "needs_approval", "channel": "email", "recipient": "customer@example.com", "message": "Tomorrow at 10", "kind": "appointment_24h"}],
        }

    def get(self, workspace_id):
        return self.model

    def save(self, workspace_id, model, *, expected_revision, changed_by):
        assert expected_revision == 3
        assert changed_by == "owner-1"
        model["revision"] = 4
        self.model = model
        return model


def test_reminder_requires_provider_receipt_before_marking_sent():
    service = WorkNotificationDeliveryService(
        schedule=FakeSchedule(),
        email_sender=lambda payload: {"ok": True, "provider": "resend", "provider_request_id": "email-123", "provider_status": "queued"},
    )
    result = service.send_approved("workspace", "reminder-1", approved_by="owner-1")
    assert result["external_message_sent"] is True
    assert result["reminder"]["status"] == "submitted_to_provider"
    assert result["reminder"]["provider_request_id"] == "email-123"


def test_reminder_fails_closed_without_provider_receipt():
    service = WorkNotificationDeliveryService(
        schedule=FakeSchedule(),
        email_sender=lambda payload: {"ok": False, "provider": "resend", "provider_request_id": "", "error_code": "not_configured"},
    )
    result = service.send_approved("workspace", "reminder-1", approved_by="owner-1")
    assert result["external_message_sent"] is False
    assert result["reminder"]["status"] == "failed"
