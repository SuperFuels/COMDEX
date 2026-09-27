from __future__ import annotations

import base64

from backend.modules.aion_business.providers.resend_adapter import ResendAdapter


def test_resend_adapter_sends_base64_attachment_without_leaking_it_in_receipt(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"id": "resend-message-1"}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    content = base64.b64encode(b"private evidence").decode("ascii")
    result = ResendAdapter(api_key="secret", default_from_email="legal@example.com").send_email(
        prompt="Private completed agreement",
        metadata={
            "to_emails": ["party@example.com"],
            "subject": "Completed agreement",
            "attachments": [{"filename": "evidence.zip", "content": content}],
        },
    )

    assert result.ok is True
    assert captured["json"]["attachments"] == [{"filename": "evidence.zip", "content": content}]
    assert result.raw["metadata"]["attachment_names"] == ["evidence.zip"]
    assert content not in repr(result.raw)


def test_resend_adapter_rejects_non_base64_attachment():
    result = ResendAdapter(api_key="secret", default_from_email="legal@example.com").send_email(
        prompt="Body",
        metadata={
            "to_emails": ["party@example.com"],
            "attachments": [{"filename": "evidence.zip", "content": "not base64!"}],
        },
    )
    assert result.ok is False
    assert result.error_code == "resend_attachment_content_must_be_base64"
