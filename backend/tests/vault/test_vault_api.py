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
