import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app


CHAIN_ID = "glyphchain-dev"
NETWORK_ID = "local"


def _stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _mock_sig(chain_id, from_addr, nonce, tx_type, payload):
    # must match verify_sig_or_raise() mock mode
    sign_dict = {
        "chain_id": chain_id,
        "from_addr": from_addr,
        "nonce": int(nonce),
        "tx_type": tx_type,
        "payload": payload,
    }
    h = hashlib.sha256(_stable_json(sign_dict).encode("utf-8")).hexdigest()
    return "mock:" + h


def _ed25519_keypair_and_sig(sign_dict):
    # must match verify_sig_or_raise() ed25519 mode: verify(sig, stable_json(sign_dict))
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    msg = _stable_json(sign_dict).encode("utf-8")
    sig = priv.sign(msg)
    return pub.hex(), sig.hex()


@pytest.fixture
def client():
    # single client fixture keeps reset/metrics consistent
    with TestClient(app) as c:
        yield c


def _reset_chain(client: TestClient):
    genesis = {
        "chain_id": CHAIN_ID,
        "network_id": NETWORK_ID,
        "allocs": [
            {"address": "pho1-s0", "balances": {"PHO": "100000", "TESS": "0"}},
            {"address": "pho1-bob", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [{"address": "val1", "self_delegation_tess": "0", "commission": "0"}],
    }
    r = client.post("/api/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, r.text


@pytest.fixture(autouse=True)
def _reset_chain_before_each_test(client):
    _reset_chain(client)
    yield


def test_sig_reject_fast_sync_no_chain_advance(client: TestClient, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "mock")

    # missing/bad sig -> 400
    r = client.post(
        "/api/chain_sim/dev/submit_tx",
        json={
            "chain_id": CHAIN_ID,
            "from_addr": "pho1-s0",
            "nonce": 0,
            "tx_type": "BANK_SEND",
            "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            # no signature
        },
    )
    assert r.status_code == 400

    # no blocks, no txs
    blocks = client.get("/api/chain_sim/dev/blocks?limit=5").json().get("blocks") or []
    txs = client.get("/api/chain_sim/dev/txs?limit=5").json().get("txs") or []
    assert len(blocks) == 0
    assert len(txs) == 0


def test_sig_accepts_mock_sync_applies(client: TestClient, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "mock")

    sig = _mock_sig(
        CHAIN_ID,
        "pho1-s0",
        0,
        "BANK_SEND",
        {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
    )

    r = client.post(
        "/api/chain_sim/dev/submit_tx",
        json={
            "chain_id": CHAIN_ID,
            "from_addr": "pho1-s0",
            "nonce": 0,
            "tx_type": "BANK_SEND",
            "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            "signature": sig,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("applied") is True
    assert data.get("tx_id")
    assert data.get("tx_hash")
    assert data.get("block_height") is not None

    blocks = client.get("/api/chain_sim/dev/blocks?limit=5").json().get("blocks") or []
    txs = client.get("/api/chain_sim/dev/txs?limit=5").json().get("txs") or []
    assert len(blocks) >= 1
    assert len(txs) >= 1


def test_sig_reject_fast_async_never_enqueues(client: TestClient, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "mock")

    # snapshot BEFORE
    before_blocks = len(client.get("/api/chain_sim/dev/blocks?limit=200").json().get("blocks") or [])
    before_txs = len(client.get("/api/chain_sim/dev/txs?limit=200").json().get("txs") or [])
    before_m = client.get("/api/chain_sim/dev/queue_metrics").json().get("metrics") or {}
    before_accepted = int(before_m.get("accepted_total") or 0)
    before_applied = int(before_m.get("applied_total") or 0)

    # missing signature -> reject fast (never enqueue)
    r = client.post(
        "/api/chain_sim/dev/submit_tx_async",
        json={
            "chain_id": CHAIN_ID,
            "from_addr": "pho1-s0",
            "nonce": 0,
            "tx_type": "BANK_SEND",
            "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            # no signature
        },
    )
    assert r.status_code == 400

    # metrics must NOT advance
    after_m = client.get("/api/chain_sim/dev/queue_metrics").json().get("metrics") or {}
    assert int(after_m.get("accepted_total") or 0) == before_accepted
    assert int(after_m.get("applied_total") or 0) == before_applied

    # chain must NOT advance
    after_blocks = len(client.get("/api/chain_sim/dev/blocks?limit=200").json().get("blocks") or [])
    after_txs = len(client.get("/api/chain_sim/dev/txs?limit=200").json().get("txs") or [])
    assert after_blocks == before_blocks
    assert after_txs == before_txs


def test_sig_accepts_ed25519_sync_applies(client: TestClient, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "ed25519")

    payload = {"denom": "PHO", "to": "pho1-bob", "amount": "1"}
    sign_dict = {
        "chain_id": CHAIN_ID,
        "from_addr": "pho1-s0",
        "nonce": 0,
        "tx_type": "BANK_SEND",
        "payload": payload,
    }
    pubkey_hex, sig_hex = _ed25519_keypair_and_sig(sign_dict)

    r = client.post(
        "/api/chain_sim/dev/submit_tx",
        json={
            "chain_id": CHAIN_ID,
            "from_addr": "pho1-s0",
            "nonce": 0,
            "tx_type": "BANK_SEND",
            "payload": payload,
            "pubkey": pubkey_hex,
            "signature": sig_hex,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("applied") is True
    assert data.get("tx_id")
    assert data.get("tx_hash")
    assert data.get("block_height") is not None


def test_sig_reject_fast_ed25519_async_never_enqueues(client: TestClient, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "ed25519")

    # snapshot BEFORE
    before_m = client.get("/api/chain_sim/dev/queue_metrics").json().get("metrics") or {}
    before_accepted = int(before_m.get("accepted_total") or 0)
    before_applied = int(before_m.get("applied_total") or 0)

    # invalid (bad lengths) -> reject fast (never enqueue)
    r = client.post(
        "/api/chain_sim/dev/submit_tx_async",
        json={
            "chain_id": CHAIN_ID,
            "from_addr": "pho1-s0",
            "nonce": 0,
            "tx_type": "BANK_SEND",
            "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            "pubkey": "00",       # should be 32 bytes hex
            "signature": "00",    # should be 64 bytes hex
        },
    )
    assert r.status_code == 400

    # metrics must NOT advance
    after_m = client.get("/api/chain_sim/dev/queue_metrics").json().get("metrics") or {}
    assert int(after_m.get("accepted_total") or 0) == before_accepted
    assert int(after_m.get("applied_total") or 0) == before_applied