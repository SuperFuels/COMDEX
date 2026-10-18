from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _canvas_payload():
    return {
        "canonical_key": "workflow:canvas.api_demo.v1",
        "display_name": "Canvas API Demo Workflow",
        "meaning": "API-saved canvas workflow capsule.",
        "display_glyph": "WG-CANVAS-API-001",
        "tags": ["canvas", "api", "demo"],
        "vault_requirements": ["vault.gmail.credentials"],
        "nodes": [
            {
                "id": "read",
                "type": "read_email",
                "data": {
                    "step_id": "read_email",
                    "kind": "read_email",
                    "label": "Read message",
                    "connector": "gmail",
                    "requires": ["vault.gmail.credentials"],
                    "output_ref": "gmail.message",
                },
            },
            {
                "id": "draft",
                "type": "draft_reply",
                "data": {
                    "step_id": "draft_reply",
                    "kind": "draft_content",
                    "label": "Draft reply",
                    "output_ref": "gmail.reply",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
        ],
    }


def test_canvas_compile_save_api_saves_without_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    response = client.post(
        "/api/workflow-capsules/canvas/compile-save",
        json={
            "canvas": _canvas_payload(),
            "scope": "workspace",
            "workspace_id": "api_test_workspace",
            "overwrite": True,
            "rebuild_registry": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert data["phase"] == "canvas_compile_save"
    assert data["canonical_key"] == "workflow:canvas.api_demo.v1"
    assert data["display_glyph"] == "WG-CANVAS-API-001"
    assert data["executed"] is False
    assert data["path"].endswith(".workflow.wiki.phn")
    assert data["checksum"]


def test_canvas_compile_save_api_rejects_secret_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    canvas = _canvas_payload()
    canvas["nodes"][0]["data"]["access_token"] = "must-not-store"

    response = client.post(
        "/api/workflow-capsules/canvas/compile-save",
        json={
            "canvas": canvas,
            "scope": "workspace",
            "workspace_id": "api_test_workspace",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is False
    assert "canvas_payload_must_not_contain_secret_fields" in data["errors"]


def test_canvas_compile_save_api_rejects_reserved_display_glyph(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    canvas = _canvas_payload()
    canvas["display_glyph"] = "^"

    response = client.post(
        "/api/workflow-capsules/canvas/compile-save",
        json={
            "canvas": canvas,
            "scope": "workspace",
            "workspace_id": "api_test_workspace",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is False
    assert "display_glyph_collides_with_reserved_glyphos_primitive" in data["errors"]
