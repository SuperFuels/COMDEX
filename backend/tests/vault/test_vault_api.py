from fastapi.testclient import TestClient

from backend.api.vault_router import router
from fastapi import FastAPI


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_gmail_status_missing_by_default() -> None:
    client = _client()

    response = client.get("/api/vault/connectors/gmail/status")
    data = response.json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["gmail"]["ready"] is False
    assert data["gmail"]["reason"] in {"credential_missing", "credential_not_connected"}
    assert data["live_send_enabled"] is False


def test_dev_seed_gmail_then_status_connected() -> None:
    client = _client()

    seed = client.post(
        "/api/vault/dev/seed-gmail",
        json={
            "business_id": "costa-conexion",
            "workspace_id": "costa-conexion",
            "owner_user_id": "local_user",
            "connected": True,
        },
    )
    assert seed.status_code == 200
    assert seed.json()["ok"] is True
    assert "secret_ref" not in seed.json()["credential"]

    status = client.get("/api/vault/connectors/gmail/status")
    data = status.json()

    assert data["gmail"]["ready"] is True
    assert data["gmail"]["reason"] == "connector_ready"
    assert data["live_send_enabled"] is False


def test_vault_credentials_list_is_public_safe() -> None:
    client = _client()

    client.post(
        "/api/vault/dev/seed-gmail",
        json={
            "business_id": "costa-conexion",
            "workspace_id": "costa-conexion",
            "owner_user_id": "local_user",
            "connected": True,
        },
    )

    response = client.get("/api/vault/credentials")
    data = response.json()

    assert data["ok"] is True
    assert len(data["credentials"]) >= 1
    assert "secret_ref" not in data["credentials"][0]
    assert data["credentials"][0]["has_secret_ref"] is True


def test_readiness_rejects_send_scope() -> None:
    client = _client()

    client.post(
        "/api/vault/dev/seed-gmail",
        json={
            "business_id": "costa-conexion",
            "workspace_id": "costa-conexion",
            "owner_user_id": "local_user",
            "connected": True,
        },
    )

    response = client.post(
        "/api/vault/connectors/readiness",
        json={
            "business_id": "costa-conexion",
            "workspace_id": "costa-conexion",
            "owner_user_id": "local_user",
            "connector_id": "gmail",
            "credential_key": "vault.gmail.credentials",
            "required_scopes": [
                "https://www.googleapis.com/auth/gmail.send",
            ],
        },
    )
    data = response.json()

    assert data["ok"] is True
    assert data["readiness"]["ready"] is False
    assert data["readiness"]["reason"] == "missing_required_scopes"


def test_integration_catalog_is_public_safe_and_keeps_payments_deferred() -> None:
    response = _client().get("/api/vault/integration-providers")
    data = response.json()

    assert response.status_code == 200
    assert data["schema_version"] == "tessaris.business_integrations.v1"
    assert data["payments_deferred"] is True
    providers = {item["provider_id"]: item for item in data["providers"]}
    assert {"gmail", "microsoft_outlook", "mailchimp_marketing", "resend"} <= set(providers)
    assert providers["gmail"]["available_to_connect"] is True
    assert "secret-value" not in response.text.lower()
    assert "bearer " not in response.text.lower()


def test_telephony_status_never_returns_provider_secrets(monkeypatch) -> None:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService

    monkeypatch.setattr(TelephonyVaultService, "status", lambda self, workspace_id: {
        "ok": True,
        "workspace_id": workspace_id,
        "twilio": {"connected": True, "phone_number": "+34711269364"},
        "retell": {"connected": True, "agent_count": 1},
        "routing": {"ready_to_build_callers": True},
        "completed_steps": 2,
        "total_steps": 2,
    })
    response = _client().get("/api/vault/telephony/home-fixed")
    body = response.json()

    assert response.status_code == 200
    assert body["completed_steps"] == 2
    assert "api_key_secret" not in response.text
    assert "sip_password" not in response.text


def test_twilio_vault_route_passes_required_setup_fields(monkeypatch) -> None:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService

    captured = {}
    def fake_save(self, workspace_id, values):
        captured.update(values)
        return {"ok": True, "workspace_id": workspace_id, "completed_steps": 1}
    monkeypatch.setattr(TelephonyVaultService, "save_twilio", fake_save)

    response = _client().post("/api/vault/telephony/home-fixed/twilio", json={
        "account_sid": "AC" + "1" * 32,
        "api_key_sid": "SK" + "2" * 32,
        "api_key_secret": "secret-value",
        "from_number": "+34711269364",
        "termination_uri": "home-fixed.pstn.twilio.com",
        "sip_username": "tessaris",
        "sip_password": "sip-secret",
    })

    assert response.status_code == 200
    assert captured["from_number"] == "+34711269364"
    assert captured["sip_password"] == "sip-secret"
