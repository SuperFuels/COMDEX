from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from backend.modules.aion_business.providers.resend_adapter import (
    ResendAdapter,
    ResendAdapterResult,
)


class ResendActions:
    """
    Higher-level email actions built on top of ResendAdapter.

    This is the real business-action wrapper layer for:
    - founder summaries
    - review queue notifications
    - invoice reminders
    - support replies
    """

    def __init__(
        self,
        *,
        resend_adapter: Optional[ResendAdapter] = None,
        default_from_email: Optional[str] = None,
    ):
        self.resend_adapter = resend_adapter or ResendAdapter(
            default_from_email=default_from_email,
        )

    def send_email(
        self,
        *,
        to_emails: List[str],
        subject: str,
        body_text: str,
        from_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
        html: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResendAdapterResult:
        payload: Dict[str, Any] = {
            "to_emails": to_emails,
            "subject": subject,
        }

        if from_email:
            payload["from_email"] = from_email
        if cc_emails:
            payload["cc_emails"] = cc_emails
        if bcc_emails:
            payload["bcc_emails"] = bcc_emails
        if reply_to:
            payload["reply_to"] = reply_to
        if html:
            payload["html"] = html

        normalized_tags = self._normalize_tags(tags)
        if normalized_tags:
            payload["tags"] = normalized_tags

        if metadata:
            payload.update(metadata)

        return self.resend_adapter.send_email(
            prompt=body_text,
            metadata=payload,
        )

    def send_founder_summary(
        self,
        *,
        to_emails: List[str],
        workspace_name: str,
        summary_text: str,
        from_email: Optional[str] = None,
    ) -> ResendAdapterResult:
        return self.send_email(
            to_emails=to_emails,
            from_email=from_email,
            subject=f"{workspace_name} Founder Summary",
            body_text=summary_text,
            tags=[
                {"name": "type", "value": "founder_summary"},
                {"name": "workspace", "value": workspace_name},
            ],
        )

    def send_review_queue_summary(
        self,
        *,
        to_emails: List[str],
        workspace_name: str,
        summary_text: str,
        from_email: Optional[str] = None,
    ) -> ResendAdapterResult:
        return self.send_email(
            to_emails=to_emails,
            from_email=from_email,
            subject=f"{workspace_name} Review Queue Summary",
            body_text=summary_text,
            tags=[
                {"name": "type", "value": "review_queue_summary"},
                {"name": "workspace", "value": workspace_name},
            ],
        )

    def send_invoice_reminder(
        self,
        *,
        to_emails: List[str],
        customer_name: str,
        invoice_reference: str,
        reminder_text: str,
        from_email: Optional[str] = None,
    ) -> ResendAdapterResult:
        return self.send_email(
            to_emails=to_emails,
            from_email=from_email,
            subject=f"Payment reminder for invoice {invoice_reference}",
            body_text=(
                f"Hello {customer_name},\n\n"
                f"{reminder_text}\n\n"
                f"Invoice reference: {invoice_reference}"
            ),
            tags=[
                {"name": "type", "value": "invoice_reminder"},
                {"name": "invoice_reference", "value": invoice_reference},
            ],
        )

    def send_support_reply(
        self,
        *,
        to_emails: List[str],
        subject: str,
        reply_text: str,
        from_email: Optional[str] = None,
        reply_to: Optional[List[str]] = None,
    ) -> ResendAdapterResult:
        return self.send_email(
            to_emails=to_emails,
            from_email=from_email,
            subject=subject,
            body_text=reply_text,
            reply_to=reply_to,
            tags=[
                {"name": "type", "value": "support_reply"},
            ],
        )

    @classmethod
    def _normalize_tags(
        cls,
        tags: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, str]]:
        if not tags:
            return []

        normalized: List[Dict[str, str]] = []
        for tag in tags:
            raw_name = (tag.get("name") or "").strip()
            raw_value = (tag.get("value") or "").strip()

            name = cls._sanitize_tag_component(raw_name)
            value = cls._sanitize_tag_component(raw_value)

            if not name or not value:
                continue

            normalized.append({"name": name, "value": value})

        return normalized

    @staticmethod
    def _sanitize_tag_component(value: str) -> str:
        text = unicodedata.normalize("NFKD", value)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = text.lower().strip()
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"[^a-z0-9_-]", "-", text)
        text = re.sub(r"-{2,}", "-", text)
        text = re.sub(r"_{2,}", "_", text)
        text = text.strip("-_")
        return text