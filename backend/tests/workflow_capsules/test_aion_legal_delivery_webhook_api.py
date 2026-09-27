from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import legal_signing_api
from backend.modules.aion_business.runtime.legal_signing_service import LegalSigningError


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(legal_signing_api.public_router)
    return TestClient(app)


def test_resend_webhook_requires_configured_signing_secret(monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("RESEND_WEBHOOK_SIGNING_SECRETS", raising=False)
    response = _client().post(
        "/api/aion/business/legal-signing/webhooks/resend",
        content=b"{}",
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "resend_webhook_signing_secret_not_configured"


def test_resend_webhook_passes_exact_bytes_and_returns_redacted_acknowledgement(monkeypatch):
    captured = {}

    class FakeService:
        def ingest_resend_delivery_webhook(self, raw_body, headers, *, webhook_secrets):
            captured.update({
                "raw_body": raw_body, "headers": headers,
                "webhook_secrets": webhook_secrets,
            })
            return {
                "accepted": True, "ignored": False, "duplicate": False,
                "outcome": "DELIVERED", "conflict": False,
                "workspace_id": "must-not-leak", "delivery_id": "must-not-leak",
            }

    monkeypatch.setenv("RESEND_WEBHOOK_SIGNING_SECRETS", "whsec_old, whsec_new")
    monkeypatch.setattr(legal_signing_api, "service", lambda: FakeService())
    raw = b'{"type":"email.delivered", "data":{"email_id":"id-1"}}'
    response = _client().post(
        "/api/aion/business/legal-signing/webhooks/resend",
        content=raw,
        headers={"svix-id": "msg-1", "svix-timestamp": "1", "svix-signature": "v1,abc"},
    )
    assert response.status_code == 202
    assert captured["raw_body"] == raw
    assert captured["webhook_secrets"] == ["whsec_old", "whsec_new"]
    assert response.json() == {
        "ok": True, "accepted": True, "ignored": False,
        "duplicate": False, "outcome": "DELIVERED", "conflict": False,
    }


def test_resend_webhook_maps_authentication_failure_to_unauthorised(monkeypatch):
    class FakeService:
        def ingest_resend_delivery_webhook(self, *_args, **_kwargs):
            raise LegalSigningError("resend_webhook_signature_invalid")

    monkeypatch.setenv("RESEND_WEBHOOK_SIGNING_SECRET", "whsec_test")
    monkeypatch.setattr(legal_signing_api, "service", lambda: FakeService())
    response = _client().post(
        "/api/aion/business/legal-signing/webhooks/resend",
        content=b"{}",
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "resend_webhook_signature_invalid"
