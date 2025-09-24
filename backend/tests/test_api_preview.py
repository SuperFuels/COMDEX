import json
import tempfile
import pathlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 🔹 Patch missing get_last_audit_events before router import
import backend.modules.lean.lean_audit as lean_audit
if not hasattr(lean_audit, "get_last_audit_events"):
    def _fake(limit: int = 50):
        return []
    lean_audit.get_last_audit_events = _fake

# ✅ Import only the lean router, avoid pulling in backend/main.py
from backend.routes.lean_inject_api import router as lean_router

# Build minimal FastAPI app just for lean routes
app = FastAPI()
app.include_router(lean_inject_api.router, prefix="/api")
client = TestClient(app)


def _make_temp_container():
    """Create a minimal container.json file on disk."""
    data = {
        "type": "dc",
        "id": "test-container",
        "symbolic_logic": [
            {"name": "A_implies_B", "symbol": "⊢", "logic": "A → B"}
        ],
        "glyphs": [],
        "tree": [],
        "previews": [],
    }
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    path = pathlib.Path(tmp.name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _make_dummy_lean(tmp_path: pathlib.Path):
    """Create a dummy Lean file with a trivial theorem."""
    lean_file = tmp_path / "dummy.lean"
    lean_file.write_text("theorem trivial : True := by trivial\n")
    return lean_file


def test_preview_mermaid(tmp_path):
    container = _make_temp_container()
    lean_file = _make_dummy_lean(tmp_path)

    resp = client.post(
        "/lean/inject?preview=mermaid",
        json={
            "lean_path": str(lean_file),
            "container_path": str(container),
            "overwrite": True,
            "auto_clean": False,
            "dedupe": False,
            "preview": "normalized",
            "validate": True,
            "fail_on_error": False,
            "mode": "standalone",
            "normalize": False,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/")
    body = resp.text
    assert "graph" in body or "mermaid" in body


def test_preview_png(tmp_path):
    container = _make_temp_container()
    lean_file = _make_dummy_lean(tmp_path)

    resp = client.post(
        "/lean/inject?preview=png",
        json={
            "lean_path": str(lean_file),
            "container_path": str(container),
            "overwrite": True,
            "auto_clean": False,
            "dedupe": False,
            "preview": "normalized",
            "validate": True,
            "fail_on_error": False,
            "mode": "standalone",
            "normalize": False,
        },
    )
    # Either actual image or graceful text fallback
    assert resp.status_code == 200, resp.text
    ctype = resp.headers["content-type"]
    assert ctype.startswith("image/png") or ctype.startswith("text/plain")