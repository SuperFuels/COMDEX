from __future__ import annotations

import base64

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.modules.consensus.finality_checkpoint import (
    CHECKPOINT_SCHEMA,
    FinalityCheckpointError,
    normalize_checkpoint,
)
from backend.modules.consensus.finality_certificate import (
    build_finality_certificate,
    verify_finality_certificate,
)
from backend.modules.consensus.ledger_commitment import normalize_ledger_block
from backend.modules.consensus.sync_policy import SyncPolicy
from backend.modules.p2p.lane_limiter import LaneLimiter
from backend.modules.p2p.p2p_types import P2PEnvelope
from backend.modules.aion_business.runtime.request_body_limits import (
    ScopedRequestBodyLimitMiddleware,
)


def _validator(index: int) -> dict[str, object]:
    return {
        "validator_id": f"validator-{index}",
        "power": 1,
        "public_key_base64": base64.b64encode(bytes([index % 251]) * 32).decode("ascii"),
    }


def _checkpoint(validators: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-main",
        "network_id": "main",
        "epoch": 1,
        "effective_height": 10,
        "validator_set": validators,
    }


def test_rate_limit_peer_bucket_table_has_a_hard_lru_bound(monkeypatch):
    from backend.modules.p2p import rate_limit

    monkeypatch.setenv("GLYPHCHAIN_RATE_LIMIT_MAX_PEERS", "256")
    rate_limit._BUCKETS.clear()
    for index in range(400):
        assert rate_limit.allow(f"peer-{index}") is True
    assert len(rate_limit._BUCKETS) == 256
    assert "peer-0" not in rate_limit._BUCKETS
    assert "peer-399" in rate_limit._BUCKETS


def test_lane_configuration_clamps_untrusted_environment_sizes(monkeypatch):
    for lane in ("PROPOSAL", "VOTE", "SYNC", "BLOCK"):
        monkeypatch.setenv(f"P2P_LANE_MAX_QUEUE_{lane}", "999999999")
        monkeypatch.setenv(f"P2P_LANE_MAX_INFLIGHT_{lane}", "999999999")
        monkeypatch.setenv(f"P2P_LANE_DUP_LRU_{lane}", "999999999")
        monkeypatch.setenv(f"P2P_LANE_YIELD_EVERY_{lane}", "999999999")
    snapshot = LaneLimiter.from_env().snapshot()["lanes"]
    for value in snapshot.values():
        assert value["queue_max"] == 20_000
        assert value["inflight_max"] == 64
        assert value["dup_lru"] == 100_000


def test_sync_policy_state_and_environment_values_are_bounded(monkeypatch):
    monkeypatch.setenv("P2P_SYNC_POLICY_MAX_STATES", "256")
    monkeypatch.setenv("P2P_SYNC_LANE_MAX_INFLIGHT", "999999")
    monkeypatch.setenv("P2P_SYNC_BACKOFF_JITTER_PCT", "999999")
    policy = SyncPolicy()
    for index in range(400):
        policy.allow(f"peer-{index}", "sync")
    assert len(policy._st) == 256
    assert policy.max_inflight == 64
    assert policy.jitter_pct == 100


def test_finality_votes_and_ledger_transactions_have_explicit_work_limits():
    with pytest.raises(ValueError, match="finality_vote_limit_exceeded"):
        build_finality_certificate(
            chain_id="glyphchain-main", network_id="main", height=1, round=0,
            block_id="block-1", validator_set=[_validator(1)],
            votes=[{} for _ in range(257)],
        )
    malformed = verify_finality_certificate({
        "schema_version": "glyphchain.quorum-finality-certificate.v1",
        "chain_id": "glyphchain-main", "height": 1, "block_id": "block-1",
        "vote_type": "PRECOMMIT", "validator_set": [_validator(1)],
        "validator_set_root": "0" * 64, "quorum_power": 1,
        "votes": [{} for _ in range(257)],
    })
    assert malformed["valid"] is False
    assert "finality_certificate_malformed" in malformed["errors"]

    with pytest.raises(ValueError, match="ledger_transaction_limit_exceeded"):
        normalize_ledger_block(
            {"height": 1, "txs": [{} for _ in range(10_001)]},
            chain_id="glyphchain-main", height=1,
        )


def test_validator_checkpoint_rejects_unbounded_membership_and_fields():
    with pytest.raises(FinalityCheckpointError, match="validator_limit_exceeded"):
        normalize_checkpoint(_checkpoint([_validator(index) for index in range(257)]))

    oversized_id = _validator(1)
    oversized_id["validator_id"] = "v" * 241
    with pytest.raises(FinalityCheckpointError, match="entry_too_large"):
        normalize_checkpoint(_checkpoint([oversized_id]))

    oversized_network = _checkpoint([_validator(1)])
    oversized_network["network_id"] = "n" * 241
    with pytest.raises(FinalityCheckpointError, match="identity_too_large"):
        normalize_checkpoint(oversized_network)


def test_p2p_envelope_rejects_oversized_identity_url_and_hop_count():
    base = {
        "type": "STATUS",
        "from_node_id": "node-1",
        "chain_id": "glyphchain-main",
        "ts_ms": 1.0,
        "payload": {},
    }
    for field, value in (
        ("from_node_id", "n" * 241),
        ("chain_id", "c" * 241),
        ("base_url", "h" * 2049),
        ("hops", 17),
    ):
        with pytest.raises(ValidationError):
            P2PEnvelope(**{**base, field: value})


def test_scoped_body_middleware_rejects_before_route_reads_oversized_content():
    app = FastAPI()
    app.add_middleware(ScopedRequestBodyLimitMiddleware)

    @app.post("/api/aion/business/legal-signing/webhooks/resend")
    async def callback(request: Request):
        return {"bytes": len(await request.body())}

    client = TestClient(app)
    maximum = ScopedRequestBodyLimitMiddleware.RESEND_WEBHOOK_BYTES
    accepted = client.post(
        "/api/aion/business/legal-signing/webhooks/resend",
        content=b"x" * maximum,
    )
    assert accepted.status_code == 200
    assert accepted.json()["bytes"] == maximum

    rejected = client.post(
        "/api/aion/business/legal-signing/webhooks/resend",
        content=b"x" * (maximum + 1),
    )
    assert rejected.status_code == 413
    assert rejected.json()["detail"] == "request_body_too_large"


@pytest.mark.asyncio
async def test_scoped_body_middleware_enforces_limit_without_content_length():
    called = False

    async def downstream(_scope, receive, send):
        nonlocal called
        called = True
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = ScopedRequestBodyLimitMiddleware(downstream)
    maximum = middleware.RESEND_WEBHOOK_BYTES
    messages = iter((
        {"type": "http.request", "body": b"a" * maximum, "more_body": True},
        {"type": "http.request", "body": b"b", "more_body": False},
    ))
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    await middleware({
        "type": "http",
        "path": "/api/aion/business/legal-signing/webhooks/resend",
        "headers": [],
    }, receive, send)
    assert called is False
    assert sent[0]["status"] == 413
