from __future__ import annotations

import base64
from email import policy
from email.parser import BytesParser

from backend.modules.local_node.local_node_runtime import LocalNodeRuntime


def test_gmail_quote_draft_attaches_the_pdf_and_never_sends() -> None:
    runtime = object.__new__(LocalNodeRuntime)
    runtime._refresh_gmail_access_token_if_needed = lambda: {"access_token": "token"}
    captured: dict = {}

    def post(_url: str, _token: str, payload: dict) -> dict:
        captured.update(payload)
        return {"id": "draft-1", "message": {"id": "message-1", "threadId": "thread-1"}}

    runtime._gmail_api_post_json = post
    runtime._gmail_api_get_json = lambda _url, _token: {"emailAddress": "sender@example.com"}
    result = runtime._create_gmail_draft(
        to="customer@example.com",
        subject="Your quotation Q-2026-0001",
        body="Please see the attached quotation.",
        html_body='<p>Please see the attached quotation.</p><a href="https://example.test/accept">Accept quotation</a>',
        attachments=[{
            "filename": "Quotation Q-2026-0001.pdf",
            "content_type": "application/pdf",
            "data_base64": base64.b64encode(b"%PDF-1.4\nquote").decode("ascii"),
        }],
    )

    message = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(captured["message"]["raw"]))
    attachment = next(message.iter_attachments())
    html_part = next(part for part in message.walk() if part.get_content_type() == "text/html")
    assert result["created"] is True
    assert result["sent"] is False
    assert result["attachments"] == ["Quotation Q-2026-0001.pdf"]
    assert result["gmail_url"] == "https://mail.google.com/mail/?authuser=sender%40example.com#drafts?compose=message-1"
    assert result["account_email"] == "sender@example.com"
    assert "Accept quotation" in html_part.get_content()
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_filename() == "Quotation Q-2026-0001.pdf"
    assert attachment.get_payload(decode=True).startswith(b"%PDF-1.4")


def test_approved_payment_email_can_send_the_invoice_pdf() -> None:
    runtime = object.__new__(LocalNodeRuntime)
    runtime._refresh_gmail_access_token_if_needed = lambda: {"access_token": "token"}
    captured: dict = {}

    def post(_url: str, _token: str, payload: dict) -> dict:
        captured.update(payload)
        return {"id": "message-2", "threadId": "thread-2"}

    runtime._gmail_api_post_json = post
    result = runtime._send_gmail_message(
        to="customer@example.com",
        subject="Payment invoice INV-2026-0001",
        body="Your payment invoice is attached.",
        html_body="<p>Your payment invoice is attached.</p>",
        attachments=[{
            "filename": "Invoice INV-2026-0001.pdf",
            "content_type": "application/pdf",
            "data_base64": base64.b64encode(b"%PDF-1.4\ninvoice").decode("ascii"),
        }],
    )

    message = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(captured["raw"]))
    attachment = next(message.iter_attachments())
    assert result["sent"] is True
    assert result["attachments"] == ["Invoice INV-2026-0001.pdf"]
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_payload(decode=True).startswith(b"%PDF-1.4")


def test_gmail_draft_refreshes_once_when_google_rejects_a_stale_access_token() -> None:
    runtime = object.__new__(LocalNodeRuntime)
    refreshes: list[bool] = []

    def refresh(*, force: bool = False) -> dict:
        refreshes.append(force)
        return {"access_token": "fresh-token" if force else "stale-token"}

    attempts: list[str] = []

    def post(_url: str, token: str, _payload: dict) -> dict:
        attempts.append(token)
        if token == "stale-token":
            raise RuntimeError("HTTP Error 401: UNAUTHENTICATED Invalid Credentials")
        return {"id": "draft-2", "message": {"id": "message-2"}}

    runtime._refresh_gmail_access_token_if_needed = refresh
    runtime._gmail_api_post_json = post
    runtime._gmail_api_get_json = lambda _url, _token: {"emailAddress": "sender@example.com"}

    result = runtime._create_gmail_draft(
        to="customer@example.com",
        subject="Quotation",
        body="Please review the quotation.",
    )

    assert result["created"] is True
    assert refreshes == [False, True]
    assert attempts == ["stale-token", "fresh-token"]
