from backend.modules.aion_business.providers.microsoft_graph_mail_adapter import MicrosoftGraphMailAdapter


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
    result = MicrosoftGraphMailAdapter(access_token="token").send_email(
        to_emails=["person@example.com"], subject="Visit reminder", body_text="Tomorrow at 10"
    )

    assert result.ok is True
    assert result.provider_request_id == "graph-request-1"
    assert captured["url"].endswith("/me/sendMail")
    assert captured["json"]["message"]["toRecipients"][0]["emailAddress"]["address"] == "person@example.com"
    assert captured["headers"]["Authorization"] == "Bearer token"
