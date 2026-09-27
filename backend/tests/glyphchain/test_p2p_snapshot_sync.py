from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from backend.modules.chain_sim.ledger_snapshot import SNAPSHOT_MEDIA_TYPE
from backend.modules.p2p import router as p2p
from backend.modules.p2p.transport_http import post_file


def _client():
    app = FastAPI()
    app.include_router(p2p.router, prefix="/api/p2p")
    return TestClient(app)


def _envelope(*, minimum_height: int = 0):
    return {
        "type": "SNAPSHOT_REQ",
        "from_node_id": "light-1",
        "from_val_id": "",
        "chain_id": p2p._CHAIN_ID,
        "ts_ms": 1_790_000_000_000,
        "payload": {
            "want": "latest_finalized_snapshot",
            "minimum_height": minimum_height,
            "request_nonce": "nonce-1",
            "sig_hex": "signed",
        },
        "hops": 0,
    }


def _enable_verified_request(monkeypatch):
    monkeypatch.setattr(p2p, "_CONSENSUS_OK", True)
    monkeypatch.setattr(p2p, "get_engine", lambda: object())
    monkeypatch.setattr(p2p, "participation_from_env", lambda: {"role": "relay"})
    monkeypatch.setattr(p2p, "_has_local_p2p_identity", lambda: True)
    monkeypatch.setattr(p2p, "_rl_or_429", lambda *args, **kwargs: None)
    monkeypatch.setattr(p2p, "_enforce_peer_binding", lambda *args, **kwargs: None)
    monkeypatch.setattr(p2p, "_verify_sig_or_403", lambda *args, **kwargs: None)


def test_verified_peer_can_stream_newer_finalized_snapshot(monkeypatch):
    _enable_verified_request(monkeypatch)

    def export(path):
        path.write_bytes(b"portable-snapshot")
        return {"snapshot_id": "ab" * 32, "ledger": {"height": 11}}

    monkeypatch.setattr(p2p, "export_current_finalized_snapshot", export)
    response = _client().post(
        "/api/p2p/snapshot_req",
        json=_envelope(minimum_height=9),
        headers={"x-glyphchain-p2p-node-id": "light-1"},
    )
    assert response.status_code == 200
    assert response.content == b"portable-snapshot"
    assert response.headers["content-type"] == SNAPSHOT_MEDIA_TYPE
    assert response.headers["x-glyphchain-snapshot-id"] == "ab" * 32
    assert response.headers["x-glyphchain-snapshot-height"] == "11"


def test_light_node_does_not_serve_snapshots(monkeypatch):
    _enable_verified_request(monkeypatch)
    monkeypatch.setattr(p2p, "participation_from_env", lambda: {"role": "light"})
    response = _client().post("/api/p2p/snapshot_req", json=_envelope())
    assert response.status_code == 403
    assert response.json()["detail"] == "snapshot_service_requires_relay_or_validator_role"


def test_peer_snapshot_request_rejects_stale_export(monkeypatch):
    _enable_verified_request(monkeypatch)

    def export(path):
        path.write_bytes(b"portable-snapshot")
        return {"snapshot_id": "cd" * 32, "ledger": {"height": 11}}

    monkeypatch.setattr(p2p, "export_current_finalized_snapshot", export)
    response = _client().post("/api/p2p/snapshot_req", json=_envelope(minimum_height=11))
    assert response.status_code == 409
    assert response.json()["detail"] == "peer_has_no_newer_finalized_snapshot"


@pytest.mark.asyncio
async def test_peer_snapshot_download_is_bounded_and_atomically_written(tmp_path):
    async def handler(request):
        assert request.url.path == "/api/p2p/snapshot_req"
        return httpx.Response(
            200,
            content=b"snapshot-body",
            headers={
                "content-type": SNAPSHOT_MEDIA_TYPE,
                "x-glyphchain-snapshot-id": "ef" * 32,
                "x-glyphchain-snapshot-height": "14",
            },
        )

    output = tmp_path / "received.snapshot"
    result = await post_file(
        "https://relay.example", "/api/p2p/snapshot_req", {"type": "SNAPSHOT_REQ"},
        output_path=output, expected_media_type=SNAPSHOT_MEDIA_TYPE, max_bytes=1024,
        transport=httpx.MockTransport(handler),
    )
    assert output.read_bytes() == b"snapshot-body"
    assert result["bytes"] == len(b"snapshot-body")
    assert result["snapshot_id"] == "ef" * 32
    assert not output.with_suffix(".snapshot.tmp").exists()


@pytest.mark.asyncio
async def test_peer_snapshot_download_rejects_oversized_response(tmp_path):
    async def handler(_request):
        return httpx.Response(200, content=b"x" * 20, headers={"content-type": SNAPSHOT_MEDIA_TYPE})

    output = tmp_path / "oversized.snapshot"
    with pytest.raises(RuntimeError, match="peer_snapshot_size_exceeded"):
        await post_file(
            "https://relay.example", "/api/p2p/snapshot_req", {},
            output_path=output, expected_media_type=SNAPSHOT_MEDIA_TYPE, max_bytes=10,
            transport=httpx.MockTransport(handler),
        )
    assert not output.exists()
