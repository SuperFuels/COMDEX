# backend/tests/test_chain_sim_perf_ingest.py
from __future__ import annotations

import importlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient


def _truthy(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _pct(xs, p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = int((p / 100.0) * (len(xs) - 1))
    return float(xs[k])


class _ClientWrap:
    """
    Unifies remote httpx.Client and local TestClient behind .get/.post
    using absolute URL when remote, path-only when local.
    """

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


def _get_effective_config(c: _ClientWrap, base_path: str) -> dict[str, Any]:
    """
    Pull effective runtime config from /api/chain_sim/dev/state.
    Supports both shapes:
      { ok, config, state, state_root }
    and older:
      { ok, state:{config,...}, state_root }
    """
    rr = c.get(f"{base_path}/chain_sim/dev/state")
    rr.raise_for_status()
    j = rr.json() or {}
    cfg = j.get("config")
    if isinstance(cfg, dict):
        return cfg
    st = j.get("state")
    if isinstance(st, dict):
        cfg2 = st.get("config")
        if isinstance(cfg2, dict):
            return cfg2
    return {}


def _write_perf_artifacts(payload: dict) -> None:
    out_dir = Path(__file__).resolve().parent / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "glyphchain_ingest_perf_latest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )

    ts = int(payload.get("ts_unix", time.time()))
    mode = payload.get("mode", "unknown")
    n = payload.get("n", "na")

    # Prefer effective_config (truth) for filenames; fallback to env (requested)
    eff = payload.get("effective_config") or {}
    env = payload.get("env") or {}

    def _pick(k: str, default: str = "na") -> str:
        v = eff.get(k, None)
        if v is None:
            v = env.get(k, None)
        if v is None:
            return default
        return str(v)

    max_tx = _pick("CHAIN_SIM_BLOCK_MAX_TX", "na")
    max_ms = _pick("CHAIN_SIM_BLOCK_MAX_MS", "na")

    fname = f"glyphchain_ingest_perf_{mode}_n{n}_tx{max_tx}_ms{max_ms}_{ts}.json"
    (out_dir / fname).write_text(json.dumps(payload, indent=2, sort_keys=True))


def _count_applied_txs(c: _ClientWrap, base_path: str, address: str, n_hint: int) -> int:
    # /dev/txs supports (limit, offset) and often supports address filtering.
    limit = max(50, min(5000, n_hint + 200))
    params = {"limit": limit, "offset": 0, "address": address}
    rr = c.get(f"{base_path}/chain_sim/dev/txs", params=params)
    if rr.status_code != 200:
        # fallback if address param is unsupported
        rr = c.get(f"{base_path}/chain_sim/dev/txs", params={"limit": limit, "offset": 0})
        rr.raise_for_status()
    j = rr.json()
    txs = j.get("txs") or []
    return int(len(txs))


def _wait_for_applied_txs(c: _ClientWrap, base_path: str, address: str, expected_n: int, timeout_s: float = 60.0) -> int:
    """
    Finality condition for async perf: ledger contains >= expected_n applied txs.
    Invariant: rejected txs are NOT recorded in /dev/txs, so this matches "finalized applied".
    """
    deadline = time.time() + timeout_s
    last = 0
    sleep_s = 0.02

    while time.time() < deadline:
        last = _count_applied_txs(c, base_path, address, expected_n)
        if last >= expected_n:
            return last
        time.sleep(sleep_s)
        # mild backoff to reduce load
        if sleep_s < 0.10:
            sleep_s *= 1.1

    raise AssertionError(f"only applied {last}/{expected_n} within {timeout_s}s")


@pytest.fixture
def c(tmp_path, monkeypatch):
    # perf knobs come from env (sweeps set these)
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", os.getenv("CHAIN_SIM_ASYNC_ENABLED", "1"))
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")

    # keep startup light in pytest
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")

    # persistence: allow env override; if enabled, force tmp sqlite path (in-process only)
    persist = _truthy(os.getenv("CHAIN_SIM_PERSIST"), default=False)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1" if persist else "0")
    if persist:
        db = tmp_path / "chain_sim_ingest_perf.sqlite3"
        monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db))

    # IMPORTANT: default 8080 (your normal dev port)
    base = os.getenv("GLYPHCHAIN_BASE_URL", "http://127.0.0.1:8080").rstrip("/")

    # remote if server up
    use_remote = False
    try:
        rr = httpx.get(base + "/openapi.json", timeout=0.25)
        use_remote = rr.status_code == 200
    except Exception:
        use_remote = False

    if use_remote:
        # IMPORTANT:
        # In remote mode, these env vars do NOT change the running uvicorn config.
        # So we do NOT monkeypatch CHAIN_SIM_BLOCK_* here (avoids lying artifacts).
        client = httpx.Client(timeout=60.0)
        w = _ClientWrap(remote=client, base=base)
        yield w
        w.close()
        return

    # in-process only: apply defaults/overrides (these DO control config)
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", os.getenv("CHAIN_SIM_ASYNC_ENABLED", "1"))
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", os.getenv("CHAIN_SIM_BLOCK_MAX_TX", "100"))
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", os.getenv("CHAIN_SIM_BLOCK_MAX_MS", "25"))
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")

    # persistence for in-process only (remote server owns its DB path)
    persist = _truthy(os.getenv("CHAIN_SIM_PERSIST"), default=False)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1" if persist else "0")
    if persist:
        db = tmp_path / "chain_sim_ingest_perf.sqlite3"
        monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db))

    import backend.main as main
    importlib.reload(main)
    with TestClient(main.app) as tc:
        yield _ClientWrap(local=tc)


def test_glyphchain_perf_ingest(c):
    base_path = "/api"
    N = int(os.getenv("CHAIN_SIM_TXN", "200"))

    sender = "pho1-s0"
    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "local",
        "allocs": [{"address": sender, "balances": {"PHO": "1000000", "TESS": "0"}}],
        "validators": [],
    }

    r = c.post(f"{base_path}/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, getattr(r, "text", "")

    # fetch nonce
    a = c.get(f"{base_path}/chain_sim/dev/account", params={"address": sender})
    assert a.status_code == 200, getattr(a, "text", "")
    nonce = int(a.json().get("nonce", 0))

    # async mode is only reliable in REMOTE (uvicorn) runs.
    async_enabled_env = os.getenv("CHAIN_SIM_ASYNC_ENABLED", "1") == "1"
    async_on = bool(async_enabled_env and c.remote)

    lat_ms: list[float] = []

    t0_all = time.perf_counter()
    submit_elapsed: float | None = None

    if async_on:
        # async submit: measure ingest latency (submit acceptance)
        t_submit0 = time.perf_counter()
        for i in range(N):
            t1 = time.perf_counter()
            tx = {
                "chain_id": "glyphchain-dev",
                "from_addr": sender,
                "nonce": nonce + i,
                "tx_type": "BANK_BURN",
                "payload": {"denom": "PHO", "amount": "1"},
            }
            resp = c.post(f"{base_path}/chain_sim/dev/submit_tx_async", json=tx)
            assert resp.status_code in (200, 202), getattr(resp, "text", "")
            j = resp.json()
            assert j.get("qid"), j
            lat_ms.append((time.perf_counter() - t1) * 1000.0)
        submit_elapsed = time.perf_counter() - t_submit0

        # finality: wait until ledger has N applied txs (NOT queue metrics)
        _wait_for_applied_txs(c, base_path, sender, expected_n=N, timeout_s=60.0)

    else:
        # sync submit (works in-process and remote)
        for i in range(N):
            t1 = time.perf_counter()
            tx = {
                "chain_id": "glyphchain-dev",
                "from_addr": sender,
                "nonce": nonce + i,
                "tx_type": "BANK_BURN",
                "payload": {"denom": "PHO", "amount": "1"},
            }
            resp = c.post(f"{base_path}/chain_sim/dev/submit_tx", json=tx)
            assert resp.status_code == 200, getattr(resp, "text", "")
            j = resp.json()
            assert j.get("applied") is True, j
            lat_ms.append((time.perf_counter() - t1) * 1000.0)

    elapsed_all = time.perf_counter() - t0_all
    tps_finalized = (N / elapsed_all) if elapsed_all > 0 else 0.0
    tps_ingest = (N / submit_elapsed) if (submit_elapsed and submit_elapsed > 0) else None

    # pull effective runtime config (truth)
    effective_cfg = _get_effective_config(c, base_path)

    payload = {
        "ok": True,
        "ts_unix": time.time(),
        "mode": "remote" if c.remote else "inprocess",
        "n": N,
        "async": async_on,
        "env": {
            "CHAIN_SIM_ASYNC_ENABLED": os.getenv("CHAIN_SIM_ASYNC_ENABLED"),
            "CHAIN_SIM_BLOCK_MAX_TX": os.getenv("CHAIN_SIM_BLOCK_MAX_TX"),
            "CHAIN_SIM_BLOCK_MAX_MS": os.getenv("CHAIN_SIM_BLOCK_MAX_MS"),
            "CHAIN_SIM_PERSIST": os.getenv("CHAIN_SIM_PERSIST"),
            "GLYPHCHAIN_BASE_URL": os.getenv("GLYPHCHAIN_BASE_URL", "http://127.0.0.1:8080"),
        },
        "effective_config": effective_cfg,
        "elapsed_s_finalized": elapsed_all,
        "elapsed_s_submit": submit_elapsed,
        "tps_finalized": tps_finalized,
        "tps_ingest": tps_ingest,
        "lat_ms": {"p50": _pct(lat_ms, 50), "p95": _pct(lat_ms, 95), "p99": _pct(lat_ms, 99)},
    }

    if os.getenv("CHAIN_SIM_WRITE_ARTIFACT", "1").strip().lower() not in ("0", "false", "off", ""):
        _write_perf_artifacts(payload)

    assert tps_finalized > 0.0