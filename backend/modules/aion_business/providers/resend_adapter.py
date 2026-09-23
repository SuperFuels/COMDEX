from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.modules.aion_business.providers.model_policy import ModelPolicy


@dataclass(slots=True)
class ResendAdapterResult:
    ok: bool
    provider: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class ResendAdapter:
    """
    Minimal Resend adapter for real email delivery.

    v1 focus:
    - send_email
    - compatible shape with other provider adapters
    - safe fallback/error handling
    - no raw secret exposure

    Expected env:
    - RESEND_API_KEY

    input metadata fields supported:
    - from_email
    - to_emails (list[str] or comma-separated str)
    - cc_emails (list[str] or comma-separated str)
    - bcc_emails (list[str] or comma-separated str)
    - reply_to
    - subject
    - html
    - tags
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        default_from_email: Optional[str] = None,
        default_subject_prefix: str = "",
        model: str = "resend-email-v1",
    ):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        self.default_from_email = (
            default_from_email
            or os.getenv("RESEND_FROM_EMAIL")
            or os.getenv("DEFAULT_FROM_EMAIL")
        )
        self.default_subject_prefix = default_subject_prefix
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def send_email(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str] = None,
        policy: Optional[ModelPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[str] = None,
        max_tokens: int = 512,  # kept for interface compatibility
    ) -> ResendAdapterResult:
        del system_prompt
        del max_tokens

        if policy and policy.byok_required and not self.api_key:
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="byok_required_missing_resend_key",
                raw=None,
            )

        if not self.api_key:
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_resend_api_key",
                raw=None,
            )

        try:
            import requests
        except Exception as exc:
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code=f"requests_import_failed:{exc}",
                raw=None,
            )

        payload_meta = dict(metadata or {})

        from_email = self._to_safe_text(
            str(
                payload_meta.get("from_email")
                or self.default_from_email
                or ""
            )
        ).strip()
        if not from_email:
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_from_email",
                raw={"metadata": payload_meta},
            )

        to_emails = self._normalize_recipients(payload_meta.get("to_emails"))
        if not to_emails:
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_to_emails",
                raw={"metadata": payload_meta},
            )

        cc_emails = self._normalize_recipients(payload_meta.get("cc_emails"))
        bcc_emails = self._normalize_recipients(payload_meta.get("bcc_emails"))
        reply_to = self._normalize_recipients(payload_meta.get("reply_to"))
        tags = self._normalize_tags(payload_meta.get("tags"))

        subject = self._to_safe_text(
            str(payload_meta.get("subject") or "Aion Business Email")
        ).strip()
        if self.default_subject_prefix:
            subject = f"{self.default_subject_prefix}{subject}"

        text_body = self._to_safe_text(prompt).strip()
        html_body = payload_meta.get("html")
        if html_body:
            html_body = self._to_safe_text(str(html_body))
        else:
            html_body = self._text_to_basic_html(text_body)

        request_payload: Dict[str, Any] = {
            "from": from_email,
            "to": to_emails,
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }
        if cc_emails:
            request_payload["cc"] = cc_emails
        if bcc_emails:
            request_payload["bcc"] = bcc_emails
        if reply_to:
            request_payload["reply_to"] = reply_to
        if tags:
            request_payload["tags"] = tags

        started = time.time()

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
                timeout=30,
            )
            latency_ms = int((time.time() - started) * 1000)

            response_json: Dict[str, Any]
            try:
                response_json = response.json()
            except Exception:
                response_json = {"raw_text": response.text}

            if response.status_code >= 400:
                return ResendAdapterResult(
                    ok=False,
                    provider="resend",
                    model=preferred_model or self.model,
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    error_code=f"resend_request_failed:{response.status_code}",
                    raw={
                        "status_code": response.status_code,
                        "response": response_json,
                        "metadata": payload_meta,
                        "request_preview": {
                            "from": from_email,
                            "to_count": len(to_emails),
                            "subject": subject,
                        },
                    },
                )

            email_id = response_json.get("id")
            return ResendAdapterResult(
                ok=True,
                provider="resend",
                model=preferred_model or self.model,
                content=f"email_sent:{email_id or 'ok'}",
                usage={},
                latency_ms=latency_ms,
                error_code=None,
                raw={
                    "id": email_id,
                    "response": response_json,
                    "metadata": payload_meta,
                    "request_preview": {
                        "from": from_email,
                        "to": to_emails,
                        "cc": cc_emails,
                        "bcc_count": len(bcc_emails),
                        "reply_to": reply_to,
                        "subject": subject,
                        "tags": tags,
                    },
                },
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return ResendAdapterResult(
                ok=False,
                provider="resend",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"resend_request_failed:{exc}",
                raw={
                    "metadata": payload_meta,
                    "request_preview": {
                        "from": from_email,
                        "to_count": len(to_emails),
                        "subject": subject,
                    },
                },
            )

    @staticmethod
    def _normalize_recipients(value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
            return [item for item in items if item]

        if isinstance(value, list):
            out: List[str] = []
            for item in value:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    out.append(text)
            return out

        text = str(value).strip()
        return [text] if text else []

    @staticmethod
    def _normalize_tags(value: Any) -> List[Dict[str, str]]:
        if value is None:
            return []

        out: List[Dict[str, str]] = []

        if isinstance(value, dict):
            for key, val in value.items():
                k = str(key).strip()
                v = str(val).strip()
                if k and v:
                    out.append({"name": k, "value": v})
            return out

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    name = str(item.get("name") or "").strip()
                    tag_value = str(item.get("value") or "").strip()
                    if name and tag_value:
                        out.append({"name": name, "value": tag_value})
            return out

        return out

    @staticmethod
    def _text_to_basic_html(text: str) -> str:
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return "<div style=\"font-family:Arial,sans-serif;white-space:pre-wrap;\">" + safe + "</div>"

    @staticmethod
    def _to_safe_text(value: str) -> str:
        text = unicodedata.normalize("NFKC", value)
        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u00a0": " ",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text.encode("utf-8", errors="ignore").decode("utf-8")