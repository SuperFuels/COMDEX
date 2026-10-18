from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass(slots=True)
class MailchimpAdapterResult:
    ok: bool
    provider: str
    action: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class MailchimpAdapter:
    """
    Minimal Mailchimp adapter for Aion Business v1.

    Supported actions:
    - upsert_contact
    - create_campaign_draft

    Expected env:
    - MAILCHIMP_API_KEY
    - MAILCHIMP_SERVER_PREFIX   e.g. us21
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        server_prefix: Optional[str] = None,
        timeout_s: int = 20,
    ):
        self.api_key = api_key or os.getenv("MAILCHIMP_API_KEY")
        self.server_prefix = server_prefix or os.getenv("MAILCHIMP_SERVER_PREFIX")
        self.timeout_s = timeout_s

    def is_configured(self) -> bool:
        return bool(self.api_key and self.server_prefix)

    def upsert_contact(
        self,
        *,
        list_id: str,
        email: str,
        status_if_new: str = "subscribed",
        merge_fields: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MailchimpAdapterResult:
        if not self.is_configured():
            return MailchimpAdapterResult(
                ok=False,
                provider="mailchimp",
                action="upsert_contact",
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_mailchimp_configuration",
                raw={"metadata": metadata or {}},
            )

        subscriber_hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
        url = (
            f"https://{self.server_prefix}.api.mailchimp.com/3.0"
            f"/lists/{list_id}/members/{subscriber_hash}"
        )

        payload: Dict[str, Any] = {
            "email_address": email.strip(),
            "status_if_new": status_if_new,
            "merge_fields": merge_fields or {},
        }

        started = time.time()
        try:
            response = requests.put(
                url,
                auth=("anystring", self.api_key),
                json=payload,
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)

            if response.status_code >= 400:
                return MailchimpAdapterResult(
                    ok=False,
                    provider="mailchimp",
                    action="upsert_contact",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code=f"mailchimp_upsert_failed:{response.status_code}",
                    raw={
                        "response_text": response.text[:1000],
                        "metadata": metadata or {},
                    },
                )

            body = response.json()

            if tags:
                tag_result = self._apply_tags(
                    list_id=list_id,
                    subscriber_hash=subscriber_hash,
                    tags=tags,
                )
                if not tag_result.ok:
                    return tag_result

            return MailchimpAdapterResult(
                ok=True,
                provider="mailchimp",
                action="upsert_contact",
                content=f"Mailchimp contact upserted for {email.strip()}",
                usage={},
                latency_ms=latency_ms,
                raw={
                    "id": body.get("id"),
                    "email_address": body.get("email_address"),
                    "status": body.get("status"),
                    "list_id": list_id,
                    "metadata": metadata or {},
                },
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return MailchimpAdapterResult(
                ok=False,
                provider="mailchimp",
                action="upsert_contact",
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"mailchimp_request_failed:{exc}",
                raw={"metadata": metadata or {}},
            )

    def create_campaign_draft(
        self,
        *,
        list_id: str,
        subject_line: str,
        title: str,
        from_name: str,
        reply_to: str,
        html: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MailchimpAdapterResult:
        if not self.is_configured():
            return MailchimpAdapterResult(
                ok=False,
                provider="mailchimp",
                action="create_campaign_draft",
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_mailchimp_configuration",
                raw={"metadata": metadata or {}},
            )

        base = f"https://{self.server_prefix}.api.mailchimp.com/3.0"
        campaign_url = f"{base}/campaigns"

        campaign_payload = {
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject_line,
                "title": title,
                "from_name": from_name,
                "reply_to": reply_to,
            },
        }

        started = time.time()
        try:
            campaign_response = requests.post(
                campaign_url,
                auth=("anystring", self.api_key),
                json=campaign_payload,
                timeout=self.timeout_s,
            )
            if campaign_response.status_code >= 400:
                latency_ms = int((time.time() - started) * 1000)
                return MailchimpAdapterResult(
                    ok=False,
                    provider="mailchimp",
                    action="create_campaign_draft",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code=f"mailchimp_campaign_create_failed:{campaign_response.status_code}",
                    raw={
                        "response_text": campaign_response.text[:1000],
                        "metadata": metadata or {},
                    },
                )

            campaign_body = campaign_response.json()
            campaign_id = campaign_body.get("id")
            if not campaign_id:
                latency_ms = int((time.time() - started) * 1000)
                return MailchimpAdapterResult(
                    ok=False,
                    provider="mailchimp",
                    action="create_campaign_draft",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code="mailchimp_campaign_missing_id",
                    raw={"metadata": metadata or {}},
                )

            content_url = f"{base}/campaigns/{campaign_id}/content"
            content_response = requests.put(
                content_url,
                auth=("anystring", self.api_key),
                json={"html": html},
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)

            if content_response.status_code >= 400:
                return MailchimpAdapterResult(
                    ok=False,
                    provider="mailchimp",
                    action="create_campaign_draft",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code=f"mailchimp_campaign_content_failed:{content_response.status_code}",
                    raw={
                        "campaign_id": campaign_id,
                        "response_text": content_response.text[:1000],
                        "metadata": metadata or {},
                    },
                )

            return MailchimpAdapterResult(
                ok=True,
                provider="mailchimp",
                action="create_campaign_draft",
                content=f"Mailchimp campaign draft created: {campaign_id}",
                usage={},
                latency_ms=latency_ms,
                raw={
                    "campaign_id": campaign_id,
                    "web_id": campaign_body.get("web_id"),
                    "list_id": list_id,
                    "title": title,
                    "metadata": metadata or {},
                },
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return MailchimpAdapterResult(
                ok=False,
                provider="mailchimp",
                action="create_campaign_draft",
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"mailchimp_request_failed:{exc}",
                raw={"metadata": metadata or {}},
            )

    def _apply_tags(
        self,
        *,
        list_id: str,
        subscriber_hash: str,
        tags: list[str],
    ) -> MailchimpAdapterResult:
        base = f"https://{self.server_prefix}.api.mailchimp.com/3.0"
        url = f"{base}/lists/{list_id}/members/{subscriber_hash}/tags"

        payload = {
            "tags": [{"name": tag, "status": "active"} for tag in tags],
        }

        started = time.time()
        try:
            response = requests.post(
                url,
                auth=("anystring", self.api_key),
                json=payload,
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)

            if response.status_code >= 400:
                return MailchimpAdapterResult(
                    ok=False,
                    provider="mailchimp",
                    action="apply_tags",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code=f"mailchimp_tag_apply_failed:{response.status_code}",
                    raw={"response_text": response.text[:1000]},
                )

            return MailchimpAdapterResult(
                ok=True,
                provider="mailchimp",
                action="apply_tags",
                content="Mailchimp tags applied",
                usage={},
                latency_ms=latency_ms,
                raw={"tags": tags},
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return MailchimpAdapterResult(
                ok=False,
                provider="mailchimp",
                action="apply_tags",
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"mailchimp_request_failed:{exc}",
                raw={"tags": tags},
            )