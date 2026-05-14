# backend/tests/test_chain_sim_replay_determinism.py
from __future__ import annotations

import os
import importlib
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient


class _ClientWrap:
    def __init__(self, *, remote: httpx.Client | None = None, local: TestClient | None = None, base: str = ""):
        self.remote = remote
        self.local = local
        self.base = base.rstrip("/")

    def post(self, path: str, **kw):
        if self.remote:
            return self.remote.post(self.base + path, **kw)
        return self.local.post(path, **kw)

    def get(self, path: str, **kw):
        if self.remote:
            return self.remote.get(self.base + path, **kw)
        return self.local.get(path, **kw)

    def close(self):
        if self.remote:
            self.remote.close()
        if self.local:
            self.local.close()


@pytest.fixture
def c(monkeypatch):
    # keep startup light in pytest
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")

    base = os.getenv("GLYPHCHAIN_BASE_URL", "http://127.0.0.1:8080").rstrip("/")

    use_remote = False
    try:
        rr = httpx.get(base + "/openapi.json", timeout=0.25)
        use_remote = rr.status_code == 200
    except Exception:
        use_remote = False

    if use_remote:
        client = httpx.Client(timeout=60.0)
        w = _ClientWrap(remote=client, base=base)
        yield w
        w.close()
        return

    import backend.main as main
    importlib.reload(main)
    with TestClient(main.app) as tc:
        yield _ClientWrap(local=tc)


def _get_last_block(c: _ClientWrap, base_path: str) -> dict[str, Any]:
    rr = c.get(f"{base_path}/chain_sim/dev/blocks", params={"limit": 1, "offset": 0})
    rr.raise_for_status()
    j = rr.json() or {}
    blocks = j.get("blocks") or []
    assert isinstance(blocks, list) and blocks, f"no blocks returned: {j}"
    blk = blocks[-1]
    assert isinstance(blk, dict), f"block not dict: {blk}"
    return blk


def _reset_and_run(c: _ClientWrap, base_path: str, n: int) -> dict[str, Any]:
    sender = "pho1-s0"
    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "local",
        "allocs": [{"address": sender, "balances": {"PHO": "1000000", "TESS": "0"}}],
        "validators": [],
    }

    r = c.post(f"{base_path}/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, getattr(r, "text", "")

    a = c.get(f"{base_path}/chain_sim/dev/account", params={"address": sender})
    assert a.status_code == 200, getattr(a, "text", "")
    nonce0 = int(a.json().get("nonce", 0))

    # deterministic tx log
    for i in range(n):
        tx = {
            "chain_id": "glyphchain-dev",
            "from_addr": sender,
            "nonce": nonce0 + i,
            "tx_type": "BANK_BURN",
            "payload": {"denom": "PHO", "amount": "1"},
        }
        resp = c.post(f"{base_path}/chain_sim/dev/submit_tx", json=tx)
        assert resp.status_code == 200, getattr(resp, "text", "")
        j = resp.json()
        assert j.get("applied") is True, j

    st = c.get(f"{base_path}/chain_sim/dev/state")
    assert st.status_code == 200, getattr(st, "text", "")
    stj = st.json() or {}
    state_root = stj.get("state_root")
    assert isinstance(state_root, str) and state_root

    blk = _get_last_block(c, base_path)
    height = int(blk.get("height") or 0)
    assert height > 0, f"bad height: {blk}"

    txs_root = blk.get("txs_root")
    if txs_root is not None:
        assert isinstance(txs_root, str) and txs_root, f"bad txs_root: {blk}"

    blk_state_root = blk.get("state_root")
    if blk_state_root is not None:
        assert isinstance(blk_state_root, str) and blk_state_root, f"bad block state_root: {blk}"

    return {
        "state_root": state_root,
        "last_height": height,
        "last_txs_root": txs_root,
        "last_block_state_root": blk_state_root,
    }


def test_chain_sim_replay_determinism_roots(c):
    base_path = "/api"
    N = int(os.getenv("CHAIN_SIM_TXN", "200"))

    r1 = _reset_and_run(c, base_path, N)
    r2 = _reset_and_run(c, base_path, N)

    assert r1["state_root"] == r2["state_root"], (r1, r2)
    assert r1["last_height"] == r2["last_height"], (r1, r2)

    # only assert if ledger exposes txs_root
    if r1["last_txs_root"] is not None or r2["last_txs_root"] is not None:
        assert r1["last_txs_root"] == r2["last_txs_root"], (r1, r2)

    # only assert if ledger exposes state_root at block level
    if r1["last_block_state_root"] is not None or r2["last_block_state_root"] is not None:
        assert r1["last_block_state_root"] == r2["last_block_state_root"], (r1, r2)