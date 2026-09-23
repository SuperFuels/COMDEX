from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

from backend.modules.aion_business.providers.resend_actions import ResendActions
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService


class WorkNotificationDeliveryService:
    """Approval-gated delivery for prepared Work & Schedule reminders."""

    def __init__(
        self,
        *,
        schedule: Optional[WorkScheduleService] = None,
        email_sender: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        sms_sender: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.schedule = schedule or WorkScheduleService()
        self.email_sender = email_sender or self._send_resend
        self.sms_sender = sms_sender or self._send_twilio

    def send_approved(self, workspace_id: str, reminder_id: str, *, approved_by: str) -> Dict[str, Any]:
        current = self.schedule.get(workspace_id)
        reminder = next((row for row in current.get("reminders", []) if row.get("id") == reminder_id), None)
        if reminder is None:
            raise LookupError("work_reminder_not_found")
        if reminder.get("status") != "needs_approval":
            raise PermissionError("work_reminder_needs_approval")
        channel = str(reminder.get("channel") or "").casefold()
        if channel not in {"email", "sms"}:
            raise ValueError("work_reminder_channel_not_deliverable")

        payload = {
            "workspace_id": workspace_id,
            "reminder_id": reminder_id,
            "recipient": reminder.get("recipient") or "",
            "message": reminder.get("message") or "",
            "kind": reminder.get("kind") or "work_reminder",
        }
        receipt = self.email_sender(payload) if channel == "email" else self.sms_sender(payload)
        if not receipt.get("ok") or not receipt.get("provider_request_id"):
            reminder.update({
                "status": "failed",
                "approved_by": approved_by,
                "provider": receipt.get("provider") or "",
                "failure_code": receipt.get("error_code") or "provider_receipt_missing",
            })
        else:
            reminder.update({
                "status": "submitted_to_provider",
                "approved_by": approved_by,
                "provider": receipt.get("provider") or "",
                "provider_request_id": receipt["provider_request_id"],
                "provider_status": receipt.get("provider_status") or "submitted",
            })
        saved = self.schedule.save(
            workspace_id,
            current,
            expected_revision=current["revision"],
            changed_by=approved_by,
        )
        persisted = next(row for row in saved["reminders"] if row.get("id") == reminder_id)
        return {"reminder": persisted, "schedule": saved, "external_message_sent": persisted["status"] == "submitted_to_provider"}

    @staticmethod
    def _send_resend(payload: Dict[str, Any]) -> Dict[str, Any]:
        result = ResendActions().send_email(
            to_emails=[str(payload["recipient"])],
            subject="Booking reminder",
            body_text=str(payload["message"]),
            tags=[{"name": "type", "value": str(payload["kind"])}, {"name": "workspace", "value": str(payload["workspace_id"])}],
        )
        return {
            "ok": result.ok,
            "provider": "resend",
            "provider_request_id": str((result.raw or {}).get("id") or ""),
            "provider_status": "submitted" if result.ok else "failed",
            "error_code": result.error_code,
        }

    @staticmethod
    def _send_twilio(payload: Dict[str, Any]) -> Dict[str, Any]:
        account = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        secret = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        sender = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        if not all((account, secret, sender)):
            return {"ok": False, "provider": "twilio_messaging", "provider_request_id": "", "error_code": "twilio_messaging_credentials_missing"}
        data = urllib.parse.urlencode({"From": sender, "To": payload["recipient"], "Body": payload["message"]}).encode()
        request = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account)}/Messages.json",
            data=data,
            headers={
                "Authorization": "Basic " + base64.b64encode(f"{account}:{secret}".encode()).decode(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                receipt = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"ok": False, "provider": "twilio_messaging", "provider_request_id": "", "error_code": f"twilio_message_failed:{exc}"}
        return {
            "ok": bool(receipt.get("sid")),
            "provider": "twilio_messaging",
            "provider_request_id": str(receipt.get("sid") or ""),
            "provider_status": receipt.get("status") or "submitted",
            "error_code": None if receipt.get("sid") else "twilio_provider_receipt_missing",
        }

