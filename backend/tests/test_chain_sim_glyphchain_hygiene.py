from __future__ import annotations

import importlib
import json

from fastapi.testclient import TestClient


def test_no_comdex_dev_default_chain_id(monkeypatch):
    # keep boot noise off
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")

    # keep requests easy
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "0")

    import backend.main as main
    importlib.reload(main)

    with TestClient(main.app) as tc:
        # 1) GET state without reset should already be glyphchain-dev
        st0 = tc.get("/api/chain_sim/dev/state").json()
        cid0 = ((st0.get("state") or {}).get("config") or {}).get("chain_id")
        assert cid0 == "glyphchain-dev"
        assert "comdex-dev" not in json.dumps(st0)

        # 2) POST reset *without* providing chain_id should still be glyphchain-dev
        rr = tc.post("/api/chain_sim/dev/reset").json()
        cid1 = (rr.get("config") or {}).get("chain_id")
        assert cid1 == "glyphchain-dev"
        assert "comdex-dev" not in json.dumps(rr)

        # 3) sanity: config endpoint should also not leak comdex-dev
        cfg = tc.get("/api/chain_sim/dev/config").json()
        assert "comdex-dev" not in json.dumps(cfg)