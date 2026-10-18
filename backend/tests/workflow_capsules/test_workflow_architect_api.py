from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_workflow_architect_health_route() -> None:
    response = client.get("/api/workflow-architect/health")

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert data["service"] == "workflow_architect"
    assert data["default_provider"] == "mock"
    assert data["live_send_enabled"] is False
    assert data["dry_run_first"] is True


def test_workflow_architect_build_review_mock_provider_returns_dry_run_review() -> None:
    response = client.post(
        "/api/workflow-architect/build-review",
        json={
            "workflow_goal": "Create a Gmail customer reply workflow.",
            "provider": "mock",
            "business_context": {
                "business_name": "Demo Business",
                "industry": "local services",
            },
            "connected_credentials": ["gmail"],
            "missing_credentials": ["hubspot"],
            "inputs": {
                "gmail_message_id": "api-architect-test-message",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert data["provider"]["provider"] == "mock"
    assert data["provider"]["spec"]["schema_version"] == "aion.workflow_builder_spec.v1"

    review = data["review"]
    assert review["phase"] == "architect_review"
    assert review["review"]["dry_run_only"] is True
    assert review["review"]["live_send_enabled"] is False
    assert review["review"]["canvas_ready"] is True

    assert data["build_pack"]["business_context"]["business_name"] == "Demo Business"
    assert data["build_pack"]["permission_runtime_rules"]["live_send_disabled"] is True
    assert data["build_pack"]["required_output_schema"]["strict_json_only"] is True

    combined = str(data).lower()
    assert "users.messages.send" not in combined
    assert "send_message" not in combined
    assert "gmail_live_send" not in combined


def test_workflow_architect_build_review_openai_provider_fails_closed_without_live_network() -> None:
    response = client.post(
        "/api/workflow-architect/build-review",
        json={
            "workflow_goal": "Create a Gmail customer reply workflow.",
            "provider": "openai",
            "model": "placeholder",
            "connected_credentials": ["gmail"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is False
    assert data["provider"]["provider"] == "openai"
    assert "provider_network_disabled:openai" in data["errors"] or "provider_not_configured:openai" in data["errors"]
    assert data["review"] == {}


def test_workflow_architect_build_review_requires_goal() -> None:
    response = client.post(
        "/api/workflow-architect/build-review",
        json={
            "workflow_goal": "",
            "provider": "mock",
        },
    )

    assert response.status_code == 422
