# backend/tests/test_api_report.py
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def _mk_container(tmp_path, cid):
    p = tmp_path / f"{cid}.json"
    # Minimal, spec-friendly dc container
    p.write_text(json.dumps(
        {"id": cid, "type": "dc", "logic": [], "glyphs": [], "tree": []},
        indent=2
    ))
    return p

def test_api_inject_invalid_lean(tmp_path, client):
    container_path = _mk_container(tmp_path, "bad1")
    lean_path = tmp_path / "bad.lean"
    lean_path.write_text("axiom foo : ???")  # deliberately invalid

    resp = client.post(
        "/api/lean/inject",
        data={
            "container_path": str(container_path),
            "fail_on_error": "true",   # Form(bool) → FastAPI coerces "true" → True
        },
        files={
            "lean_file": ("bad.lean", lean_path.read_bytes(), "text/plain"),
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "validation_errors" in detail
    assert isinstance(detail["validation_errors"], list)

def test_api_inject_report_json(tmp_path, client):
    container_path = _mk_container(tmp_path, "demo1")
    lean_path = tmp_path / "demo.lean"
    lean_path.write_text("axiom foo : True")

    resp = client.post(
        "/api/lean/inject?report=json",
        data={"container_path": str(container_path)},
        files={"lean_file": ("demo.lean", lean_path.read_bytes(), "text/plain")},
    )
    assert resp.status_code == 200
    payload = json.loads(resp.text)  # report is returned as a JSON string body
    assert payload["kind"] == "lean.inject"
    assert "audit" in payload
    assert "container" in payload
    assert "validation_errors" in payload

def test_api_inject_report_md(tmp_path, client):
    container_path = _mk_container(tmp_path, "demo2")
    lean_path = tmp_path / "demo.lean"
    lean_path.write_text("axiom bar : True")

    resp = client.post(
        "/api/lean/inject?report=md",
        data={"container_path": str(container_path)},
        files={"lean_file": ("demo.lean", lean_path.read_bytes(), "text/plain")},
    )
    assert resp.status_code == 200
    text = resp.text
    assert text.startswith("# Lean Report")
    assert "Validation Errors" in text