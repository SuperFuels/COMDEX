import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


@pytest.mark.smoke
def test_inject_and_export_smoke(tmp_path):
    # Fake container file
    container_path = tmp_path / "container.json"
    container_path.write_text(
        '{"id": "c1", "type": "dc", "logic": [], "glyphs": [], "tree": []}'
    )

    # Fake .lean file (content irrelevant for smoke test)
    lean_path = tmp_path / "theorem.lean"
    lean_path.write_text("theorem trivial : True := trivial")

    # --- Inject (standalone, normalize=False by default) ---
    resp = client.post(
        "/lean/inject",
        json={
            "container_path": str(container_path),
            "lean_path": str(lean_path),
            "mode": "standalone",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # Stub integration fields must exist
    assert "codex_ast" in data
    assert "sqi_scores" in data
    assert "mutations" in data
    assert data["mode"] == "standalone"
    assert data["normalize"] is False   # ✅ purity by default

    # --- Inject again (standalone + normalize=True) ---
    resp = client.post(
        "/lean/inject",
        json={
            "container_path": str(container_path),
            "lean_path": str(lean_path),
            "mode": "standalone",
            "normalize": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "standalone"
    assert data["normalize"] is True    # ✅ normalization flag respected

    # --- Export (integrated mode) ---
    resp = client.post(
        "/lean/export",
        json={
            "lean_path": str(lean_path),
            "container_type": "dc",
            "mode": "integrated",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "codex_ast" in data
    assert "sqi_scores" in data
    assert "mutations" in data
    assert data["mode"] == "integrated"