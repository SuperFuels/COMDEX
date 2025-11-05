# backend/symatics/tests/test_bridge.py
import pytest

# ---- Direct bridge smoke (async) --------------------------------------------
@pytest.mark.asyncio
async def test_bridge_execute_raw_jsonl_no_attr_get_error():
    try:
        from backend.symatics.photon_symatics_bridge import PhotonSymaticsBridge
    except Exception as e:
        pytest.skip(f"PhotonSymaticsBridge not importable: {e}")

    bridge = PhotonSymaticsBridge()
    jsonl = '{"operator":"⊕"}\n{"expr":"hello"}\n{"operator":"↔"}'

    res = await bridge.execute_raw(jsonl)
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert res.get("count") == 3

    # No "'str' object has no attribute 'get'" style errors
    assert not any(
        r.get("status") == "error" and "has no attribute 'get'" in (r.get("error") or "")
        for r in res.get("results", [])
    )


@pytest.mark.asyncio
async def test_bridge_execute_raw_free_text_no_attr_get_error():
    try:
        from backend.symatics.photon_symatics_bridge import PhotonSymaticsBridge
    except Exception as e:
        pytest.skip(f"PhotonSymaticsBridge not importable: {e}")

    bridge = PhotonSymaticsBridge()
    free_text = 'emit "hello"\n⊕\nworld'  # should be coerced to JSONL inside the bridge pipeline

    res = await bridge.execute_raw(free_text)
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert res.get("count") == 3
    assert not any(
        r.get("status") == "error" and "has no attribute 'get'" in (r.get("error") or "")
        for r in res.get("results", [])
    )

# ---- API smoke (router-only FastAPI app, no heavy main startup) -------------
def _make_router_app():
    from fastapi import FastAPI
    from backend.api.photon_api import router as photon_router
    app = FastAPI()
    app.include_router(photon_router)
    return app

def test_api_execute_raw_capsule_and_text_roundtrip():
    from fastapi.testclient import TestClient
    app = _make_router_app()
    client = TestClient(app)

    # Case A: capsule path
    capsule = {"glyphs": ["⊕", "hello", "↔"]}
    r = client.post("/api/photon/execute_raw", json={"source": capsule})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("count") == 3
    assert not any(
        x.get("status") == "error" and "has no attribute 'get'" in (x.get("error") or "")
        for x in data.get("results", [])
    )

    # Case B: free text path
    r2 = client.post("/api/photon/execute_raw", json={"source": 'emit "hello"\n⊕\nworld'})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("ok") is True
    assert data2.get("count") == 3
    assert not any(
        x.get("status") == "error" and "has no attribute 'get'" in (x.get("error") or "")
        for x in data2.get("results", [])
    )