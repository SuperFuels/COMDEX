import base64

from backend.modules.aion_business.providers.microsoft_graph_mail_adapter import (
    MicrosoftGraphMailAdapter,
    MicrosoftGraphMessageTraceAdapter,
)


def test_outlook_adapter_fails_closed_without_token():
    result = MicrosoftGraphMailAdapter(access_token="").send_email(
        to_emails=["person@example.com"], subject="Hello", body_text="Body"
    )
    assert result.ok is False
    assert result.error_code == "missing_microsoft_graph_access_token"


def test_outlook_adapter_builds_graph_send_request(monkeypatch):
    captured = {}

    class Response:
        status_code = 202
        headers = {"request-id": "graph-request-1"}
        content = b""
        text = ""

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    content = base64.b64encode(b"private evidence").decode("ascii")
    result = MicrosoftGraphMailAdapter(access_token="token").send_email(
        to_emails=["person@example.com"], subject="Visit reminder", body_text="Tomorrow at 10",
        attachments=[{"filename": "evidence.zip", "content_base64": content, "content_type": "application/zip"}],
    )

    assert result.ok is True
    assert result.provider_request_id == "graph-request-1"
    assert captured["url"].endswith("/me/sendMail")
    assert captured["json"]["message"]["toRecipients"][0]["emailAddress"]["address"] == "person@example.com"
    assert captured["json"]["message"]["attachments"] == [{
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "evidence.zip",
        "contentType": "application/zip",
        "contentBytes": content,
    }]
    assert captured["headers"]["Authorization"] == "Bearer token"


def test_outlook_traceable_send_retains_internet_message_id(monkeypatch):
    calls = []

    class Response:
        def __init__(self, status_code, body=None, request_id=""):
            self.status_code = status_code
            self._body = body or {}
            self.headers = {"request-id": request_id} if request_id else {}
            self.content = b"{}" if body else b""
            self.text = ""

        def json(self):
            return self._body

    responses = [
        Response(201, {
            "id": "immutable/draft+id",
            "internetMessageId": "<traceable-123@example.onmicrosoft.com>",
        }),
        Response(202, request_id="send-request-1"),
    ]

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    result = MicrosoftGraphMailAdapter(access_token="token").send_traceable_email(
        to_emails=["party@example.com"],
        subject="Signed agreement",
        body_text="Attached evidence",
        tracking_id="delivery-abc",
    )

    assert result.ok is True
    assert result.provider_request_id == "<traceable-123@example.onmicrosoft.com>"
    assert calls[0][0].endswith("/me/messages")
    assert calls[0][1]["headers"]["Prefer"] == 'IdType="ImmutableId"'
    assert calls[0][1]["json"]["internetMessageHeaders"] == [{
        "name": "x-tessaris-delivery-id", "value": "delivery-abc",
    }]
    assert calls[1][0].endswith("/me/messages/immutable%2Fdraft%2Bid/send")
    assert calls[1][1]["headers"]["Content-Length"] == "0"


def test_message_trace_lookup_requires_exact_message_and_recipient(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "value": [
                    {
                        "id": "wrong-recipient",
                        "messageId": "<message-1@example.com>",
                        "recipientAddress": "other@example.com",
                        "status": "delivered",
                        "receivedDateTime": "2026-09-26T12:00:00Z",
                    },
                    {
                        "id": "trace-1",
                        "messageId": "<message-1@example.com>",
                        "recipientAddress": "PARTY@example.com",
                        "status": "delivered",
                        "receivedDateTime": "2026-09-26T12:00:01Z",
                    },
                ],
            }

    def fake_get(url, *, headers, params, timeout):
        captured.update({"url": url, "headers": headers, "params": params, "timeout": timeout})
        return Response()

    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    result = MicrosoftGraphMessageTraceAdapter(access_token="trace-token").lookup(
        internet_message_id="<message-1@example.com>",
        recipient_email="party@example.com",
    )

    assert result.ok is True
    assert result.found is True
    assert result.trace_id == "trace-1"
    assert result.provider_status == "delivered"
    assert "messageId eq '<message-1@example.com>'" in captured["params"]["$filter"]
    assert "recipientAddress eq 'party@example.com'" in captured["params"]["$filter"]
    assert captured["headers"]["Authorization"] == "Bearer trace-token"
