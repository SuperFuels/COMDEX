from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)



from backend.main import app


def _client() -> TestClient:
    return TestClient(app)


def _glyph(code: str = "GM-9001", version: str = "v1", scope: str = "my") -> dict:
    return {
        "glyph_id": f"glyph_{code.lower().replace('-', '_')}_{version}",
        "glyph_code": code,
        "glyph_scope": scope,
        "workflow_id": "workflow:gmail.enquiry_reply.v1",
        "workflow_version": version,
        "glyph_version": version,
        "display_name": "Gmail Enquiry Reply API Test",
        "description": "API test glyph.",
        "input_schema": {"type": "object", "properties": {"gmail_message_id": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"reply_draft": {"type": "string"}}},
        "required_connectors": ["gmail"],
        "risk_tier": "medium",
        "approval_policy": {"human_approval_required": True},
        "callable": True,
        "runtime_plan": {
            "steps": [
                {"step_id": "draft_reply", "kind": "draft_content"},
                {"step_id": "approval_checkpoint", "kind": "approval_checkpoint"},
            ]
        },
        "tags": ["gmail", "customer", "reply"],
    }


def test_workflow_glyph_api_save_get_search_and_list() -> None:
    client = _client()

    save_resp = client.post(
        "/api/workflow-glyphs",
        json={"glyph": _glyph(), "rebuild_index": True},
    )
    assert save_resp.status_code == 200
    saved = save_resp.json()
    assert saved["ok"] is True
    assert saved["glyph"]["glyph_code"] == "GM-9001"
    assert saved["glyph"]["version_hash"]

    get_resp = client.get("/api/workflow-glyphs/GM-9001")
    assert get_resp.status_code == 200
    got = get_resp.json()
    assert got["ok"] is True
    assert got["glyph"]["glyph_code"] == "GM-9001"

    version_resp = client.get("/api/workflow-glyphs/GM-9001/versions/v1")
    assert version_resp.status_code == 200
    assert version_resp.json()["glyph"]["glyph_version"] == "v1"

    search_resp = client.get("/api/workflow-glyphs/search", params={"q": "gmail", "callable_only": True})
    assert search_resp.status_code == 200
    search = search_resp.json()
    assert search["ok"] is True
    assert any(g["glyph_code"] == "GM-9001" for g in search["glyphs"])

    list_resp = client.get("/api/workflow-glyphs", params={"scope": "my", "callable_only": True})
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["ok"] is True
    assert any(g["glyph_code"] == "GM-9001" for g in listed["glyphs"])


def test_workflow_glyph_api_404_for_missing_glyph() -> None:
    client = _client()

    resp = client.get("/api/workflow-glyphs/NO-0000")
    assert resp.status_code == 404
    assert "glyph_not_found" in resp.text



def test_copy_universal_glyph_to_my_glyphs(client, tmp_path, monkeypatch):
    from backend.api import workflow_glyph_router
    from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import WorkflowGlyphRepository

    repo = WorkflowGlyphRepository(
        glyph_dir=tmp_path / "glyphs",
        index_path=tmp_path / "index.json",
    )
    monkeypatch.setattr(workflow_glyph_router, "get_glyph_repo", lambda: repo)

    universal = {
        "glyph_id": "glyph.gm-1001.v1",
        "glyph_code": "GM-1001",
        "name": "Gmail Customer Enquiry Reply",
        "workflow_id": "universal.gmail_customer_enquiry_reply.v1",
        "workflow_version": "v1",
        "glyph_version": "v1",
        "scope": "universal",
        "callable": True,
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "required_connectors": ["gmail"],
        "risk_tier": "medium",
        "approval_policy": {"dry_run_first": True},
        "runtime_plan": {"dry_run_only": True},
        "tags": ["gmail", "universal"],
        "description": "Universal Gmail reply glyph.",
    }

    create = client.post("/api/workflow-glyphs", json={"glyph": universal})
    assert create.status_code == 200

    response = client.post(
        "/api/workflow-glyphs/copy",
        json={"source_glyph_code": "GM-1001"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is True
    assert payload["source_glyph_code"] == "GM-1001"
    assert payload["copied_glyph_code"].startswith("GM-")
    assert payload["copied_glyph_code"] != "GM-1001"

    copied = payload["glyph"]
    assert copied["scope"] == "my"
    assert copied["source_glyph_code"] == "GM-1001"
    assert copied["required_connectors"] == ["gmail"]

    my_list = client.get("/api/workflow-glyphs?scope=my").json()
    assert my_list["count"] == 1
    assert my_list["glyphs"][0]["source_glyph_code"] == "GM-1001"

    universal_list = client.get("/api/workflow-glyphs?scope=universal").json()
    assert universal_list["count"] == 1
    assert universal_list["glyphs"][0]["glyph_code"] == "GM-1001"
