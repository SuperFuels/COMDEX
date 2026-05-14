import importlib
import json
import os
import time
from pathlib import Path
import pytest
import httpx
from fastapi.testclient import TestClient


def _truthy(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


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


@pytest.fixture
def c(tmp_path, monkeypatch):
    # ---- perf knobs come from env (sweep loop sets these) ----
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", os.getenv("CHAIN_SIM_ASYNC_ENABLED", "1"))
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", os.getenv("CHAIN_SIM_BLOCK_MAX_TX", "200"))
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", os.getenv("CHAIN_SIM_BLOCK_MAX_MS", "25"))

    # keep chain-sim sig off for perf
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")

    # keep startup lightweight in pytest (avoid subprocess + heavy systems)
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")

    # persistence: allow env override; if enabled, force tmp sqlite path
    persist = _truthy(os.getenv("CHAIN_SIM_PERSIST"), default=False)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1" if persist else "0")
    if persist:
        db = tmp_path / "chain_sim_perf.sqlite3"
        monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db))

    base = os.getenv("GLYPHCHAIN_BASE_URL", "http://127.0.0.1:8080").rstrip("/")

    # ---- if a server is running, use it; otherwise use in-process app ----
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

    # in-process mode
    import backend.main as main
    importlib.reload(main)
    app = main.app
    with TestClient(app) as tc:
        yield _ClientWrap(local=tc)

def _write_perf_artifacts(payload: dict) -> None:
    out_dir = Path(__file__).resolve().parent / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # always update latest
    (out_dir / "glyphchain_perf_latest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )

    # also write unique snapshot per run
    ts = int(payload.get("ts_unix", time.time()))
    env = payload.get("env") or {}
    max_tx = env.get("CHAIN_SIM_BLOCK_MAX_TX", "na")
    max_ms = env.get("CHAIN_SIM_BLOCK_MAX_MS", "na")
    mode = payload.get("mode", "unknown")

    fname = f"glyphchain_perf_{mode}_tx{max_tx}_ms{max_ms}_{ts}.json"
    (out_dir / fname).write_text(json.dumps(payload, indent=2, sort_keys=True))

def _latest_height(c: _ClientWrap) -> int:
    r = c.get("/api/chain_sim/dev/blocks", params={"limit": 1, "offset": 0})
    assert r.status_code == 200, getattr(r, "text", "")
    blocks = r.json().get("blocks") or []
    return int(blocks[0]["height"]) if blocks else 0


def test_glyphchain_perf_smoke(c: _ClientWrap):
    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "local",
        "allocs": [{"address": "pho1-s0", "balances": {"PHO": "100000", "TESS": "0"}}],
        "validators": [],
    }

    r = c.post("/api/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, getattr(r, "text", "")

    # ---- Invariant: rejected tx must NOT create a new block ----
    pre_h = _latest_height(c)
    bad = c.post(
        "/api/chain_sim/dev/submit_tx",
        json={
            "chain_id": "glyphchain-dev",
            "from_addr": "pho1-s0",
            "nonce": 999999999,
            "tx_type": "BANK_SEND",
            "payload": {"denom": "PHO", "to": "pho1-nope", "amount": "1"},
        },
    )
    assert bad.status_code == 200, getattr(bad, "text", "")
    bad_j = bad.json()
    assert bad_j.get("ok") is True
    assert bad_j.get("applied") is False
    assert "tx_id" not in bad_j  # hard rule from your RFC

    post_h = _latest_height(c)
    assert post_h == pre_h

    # ---- warmup + measure a small, stable slice ----
    def timed_get(path: str, n: int) -> float:
        t0 = time.perf_counter()
        for _ in range(n):
            rr = c.get(path)
            assert rr.status_code == 200, getattr(rr, "text", "")
        return (time.perf_counter() - t0) / float(n)

    n = int(os.getenv("CHAIN_SIM_PERF_N", "20") or "20")

    t_state = timed_get("/api/chain_sim/dev/state", n)
    t_supply = timed_get("/api/chain_sim/dev/supply", n)

    payload = {
        "ok": True,
        "ts_unix": time.time(),
        "mode": "remote" if c.remote else "inprocess",
        "env": {
            "CHAIN_SIM_ASYNC_ENABLED": os.getenv("CHAIN_SIM_ASYNC_ENABLED"),
            "CHAIN_SIM_BLOCK_MAX_TX": os.getenv("CHAIN_SIM_BLOCK_MAX_TX"),
            "CHAIN_SIM_BLOCK_MAX_MS": os.getenv("CHAIN_SIM_BLOCK_MAX_MS"),
            "CHAIN_SIM_PERSIST": os.getenv("CHAIN_SIM_PERSIST"),
        },
        "avg_seconds": {
            "GET /api/chain_sim/dev/state": t_state,
            "GET /api/chain_sim/dev/supply": t_supply,
        },
        "n": n,
    }

    _write_perf_artifacts(payload)
    assert payload["avg_seconds"]["GET /api/chain_sim/dev/state"] > 0