# backend/tests/test_p2p_block_fetch.py
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

# --- sanity guard: fail fast if helpers were dropped during edits/pastes ---
def test__sanity__p2p_block_fetch_helpers_present() -> None:
    required = [
        "_spawn_node",
        "_reset_dev_chain",
        "_force_block_sync",
        "_wait_latest_header",
        "_extract_roots",
    ]
    missing = [name for name in required if name not in globals() or not callable(globals()[name])]
    assert not missing, f"Missing helper(s) in test_p2p_block_fetch.py: {missing}"

def _wait_latest_header(base: str, *, stderr_path: Path, timeout_s: float = 120.0) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last: Any = None

    paths = (
        "/api/chain_sim/dev/headers?limit=1&order=desc",
        "/chain_sim/dev/headers?limit=1&order=desc",
    )

    while time.time() < deadline:
        for path in paths:
            try:
                r = httpx.get(base + path, timeout=20.0)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                j = r.json()
                if isinstance(j, dict):
                    hs = j.get("headers") or []
                    if isinstance(hs, list) and hs and isinstance(hs[0], dict):
                        return hs[0]
                    last = j
            except Exception as e:
                last = e

        time.sleep(0.25)

    raise RuntimeError(f"no headers produced within timeout; last={last!r}\n--- stderr tail ---\n{_tail(stderr_path)}")

def _tail(path: Path, n: int = 160) -> str:
    try:
        lines = path.read_text(errors="ignore").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return "<no stderr>"


def _wait_ok(url: str, *, stderr_path: Path, timeout_s: float = 240.0) -> None:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                j = r.json()
                if isinstance(j, dict) and j.get("ok") is True:
                    return
                last = {"status": r.status_code, "json": j}
            else:
                last = {"status": r.status_code, "text": r.text[:200]}
        except Exception as e:
            last = e
        time.sleep(0.25)
    raise RuntimeError(f"service not ready: {url} last={last!r}\n--- stderr tail ---\n{_tail(stderr_path)}")


def _wait_200(url: str, *, stderr_path: Path, timeout_s: float = 300.0) -> None:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
            last = {"status": r.status_code, "text": r.text[:200]}
        except Exception as e:
            last = e
        time.sleep(0.25)
    raise RuntimeError(f"endpoint not ready: {url} last={last!r}\n--- stderr tail ---\n{_tail(stderr_path)}")


def _spawn_node(
    *,
    port: int,
    node_id: str,
    chain_id: str,
    self_val_id: str,
    stderr_path: Path,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "GLYPHCHAIN_BASE_URL": f"http://127.0.0.1:{port}",
            "GLYPHCHAIN_NODE_ID": node_id,
            "GLYPHCHAIN_CHAIN_ID": chain_id,
            "GLYPHCHAIN_SELF_VAL_ID": self_val_id,
            "CHAIN_SIM_SIG_MODE": env.get("CHAIN_SIM_SIG_MODE", "off"),
            # determinism knobs (ok even if not strictly required)
            "CHAIN_SIM_ASYNC_ENABLED": "1",
            "CHAIN_SIM_BLOCK_MAX_TX": "1",
            "CHAIN_SIM_BLOCK_MAX_MS": "50",
            "CHAIN_SIM_STATE_ROOT_INTERVAL": "1",
            "CHAIN_SIM_REPLAY_ON_STARTUP": "0",
            "CHAIN_SIM_REPLAY_STRICT": "0",
        }
    )

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    stderr_f = stderr_path.open("w", encoding="utf-8", errors="ignore")
    return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=stderr_f, text=True)


def _post_json(base: str, path: str, body: Dict[str, Any], timeout_s: float = 30.0) -> httpx.Response:
    return httpx.post(base + path, json=body, timeout=timeout_s)


def _get_json(base: str, path: str, timeout_s: float = 30.0) -> Dict[str, Any]:
    r = httpx.get(base + path, timeout=timeout_s)
    r.raise_for_status()
    j = r.json()
    assert isinstance(j, dict)
    return j


def _reset_dev_chain(
    base: str,
    *,
    chain_id: str,
    network_id: str,
    allocs: list[dict[str, Any]],
    validators: list[dict[str, Any]],
    stderr_path: Path,
) -> Dict[str, Any]:
    """
    POST /api/chain_sim/dev/reset expects DevResetRequest (all optional),
    but we supply a deterministic genesis here.

    IMPORTANT: validators self-delegate TESS in staking.apply_genesis_validators(),
    so validator *addresses must have TESS allocs* (or set self_delegation_tess="0").
    """
    body = {
        "chain_id": chain_id,
        "network_id": network_id,
        "allocs": allocs,
        "validators": validators,
    }

    try:
        r = _post_json(base, "/api/chain_sim/dev/reset", body, timeout_s=60.0)
        if r.status_code == 422:
            raise RuntimeError(f"reset 422: {r.text[:1200]}")
        if r.status_code >= 400:
            raise RuntimeError(f"reset failed status={r.status_code} body={r.text[:1200]}")
        j = r.json()
        assert isinstance(j, dict)
        return j
    except Exception as e:
        raise RuntimeError(f"reset failed: {e}\n--- stderr tail ---\n{_tail(stderr_path)}") from e


def _get_state(base: str, *, stderr_path: Path) -> Dict[str, Any]:
    try:
        return _get_json(base, "/api/chain_sim/dev/state", timeout_s=30.0)
    except Exception as e:
        raise RuntimeError(f"state fetch failed: {e}\n--- stderr tail ---\n{_tail(stderr_path)}") from e


def _submit_tx_sync(base: str, tx: Dict[str, Any], *, stderr_path: Path) -> Dict[str, Any]:
    """
    Use the CHAIN_SIM router (not the legacy DEV_LEDGER router).
    In chain_sim_routes.py this is:
      POST /dev/submit_tx   (mounted under /api/chain_sim)
    => /api/chain_sim/dev/submit_tx
    """
    try:
        r = _post_json(base, "/api/chain_sim/dev/submit_tx", tx, timeout_s=60.0)
        if r.status_code == 422:
            raise RuntimeError(f"submit_tx 422: {r.text[:1200]}")
        if r.status_code >= 400:
            raise RuntimeError(f"submit_tx failed status={r.status_code} body={r.text[:1200]}")
        j = r.json()
        assert isinstance(j, dict)
        return j
    except Exception as e:
        raise RuntimeError(f"submit_tx failed: {e}\n--- stderr tail ---\n{_tail(stderr_path)}") from e


def _force_block_sync(base: str, chain_id: str, *, stderr_path: Path) -> None:
    # deterministic: alice -> bob BANK_SEND (1 PHO)
    to_addr = "pho1-dev-bob"
    tx_base: Dict[str, Any] = {
        "from_addr": "pho1-dev-alice",
        "tx_type": "BANK_SEND",
        "payload": {
            "to": to_addr,          # ✅ required by current executor
            "to_addr": to_addr,     # ✅ legacy alias (safe)
            "amount": "1",
            "denom": "PHO",
        },
        "chain_id": chain_id,
    }

    nonce = 0
    last: Any = None

    for _ in range(8):
        tx = dict(tx_base)
        tx["nonce"] = nonce

        j = _submit_tx_sync(base, tx, stderr_path=stderr_path)
        last = j

        if j.get("applied") is True:
            return

        # Prefer structured expected_nonce
        exp: Any = None
        res = j.get("result")
        if isinstance(res, dict) and res.get("expected_nonce") is not None:
            exp = res.get("expected_nonce")

        # Fallback: parse from error text
        if exp is None:
            err = str(j.get("error") or "")
            import re

            m = re.search(r"expected\s+(\d+)", err)
            if m:
                exp = int(m.group(1))

        if exp is None:
            raise RuntimeError(
                f"forced tx rejected: {j!r}\n--- stderr tail ---\n{_tail(stderr_path)}"
            )

        exp_i = int(exp)
        if exp_i == nonce:
            break
        nonce = exp_i

    raise RuntimeError(f"could not force block; last={last!r}\n--- stderr tail ---\n{_tail(stderr_path)}")


def _extract_roots(hrec: Dict[str, Any]) -> Tuple[str, str]:
    hdr = hrec.get("header") if isinstance(hrec.get("header"), dict) else {}
    sr = str((hdr.get("state_root") if isinstance(hdr, dict) else "") or hrec.get("state_root") or "")
    tr = str((hdr.get("txs_root") if isinstance(hdr, dict) else "") or hrec.get("txs_root") or "")
    return sr, tr


@pytest.mark.integration
def test_p2p_block_req_returns_block_and_header(tmp_path: Path) -> None:
    chain_id = "glyphchain-dev"
    network_id = "devnet"

    p1_port, p2_port = 18092, 18093
    base1 = f"http://127.0.0.1:{p1_port}"
    base2 = f"http://127.0.0.1:{p2_port}"

    stderr1 = tmp_path / "node1.stderr.log"
    stderr2 = tmp_path / "node2.stderr.log"

    p1 = _spawn_node(port=p1_port, node_id="node-1", chain_id=chain_id, self_val_id="val-1", stderr_path=stderr1)
    p2 = _spawn_node(port=p2_port, node_id="node-2", chain_id=chain_id, self_val_id="val-2", stderr_path=stderr2)

    try:
        _wait_ok(base1 + "/api/p2p/peers", stderr_path=stderr1, timeout_s=240.0)
        _wait_ok(base2 + "/api/p2p/peers", stderr_path=stderr2, timeout_s=240.0)

        _wait_200(base1 + "/api/chain_sim/dev/queue_metrics", stderr_path=stderr1, timeout_s=300.0)
        _wait_200(base2 + "/api/chain_sim/dev/queue_metrics", stderr_path=stderr2, timeout_s=300.0)

        # Deterministic genesis:
        # - fund alice/bob for BANK_SEND
        # - fund val-1/val-2 with TESS so staking self-delegation succeeds during reset
        allocs = [
            {"address": "pho1-dev-alice", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-bob", "balances": {"PHO": "1000", "TESS": "0"}},
            {"address": "val-1", "balances": {"PHO": "0", "TESS": "10"}},
            {"address": "val-2", "balances": {"PHO": "0", "TESS": "10"}},
        ]
        validators = [
            {"address": "val-1", "self_delegation_tess": "1", "commission": "0"},
            {"address": "val-2", "self_delegation_tess": "1", "commission": "0"},
        ]

        _reset_dev_chain(base1, chain_id=chain_id, network_id=network_id, allocs=allocs, validators=validators, stderr_path=stderr1)
        _reset_dev_chain(base2, chain_id=chain_id, network_id=network_id, allocs=allocs, validators=validators, stderr_path=stderr2)

        # Force a committed block (SYNC submit_tx path)
        _force_block_sync(base1, chain_id=chain_id, stderr_path=stderr1)

        hrec = _wait_latest_header(base1, stderr_path=stderr1, timeout_s=120.0)
        h = int(hrec.get("height") or 0)
        assert h > 0

        sr1, tr1 = _extract_roots(hrec)

        # --- BLOCK_REQ (want=block) ---
        env_req_block = {
            "type": "BLOCK_REQ",
            "from_node_id": "node-2",
            "chain_id": chain_id,
            "ts_ms": time.time() * 1000.0,
            "payload": {"height": h, "want": "block"},
            "hops": 0,
        }
        rb = _post_json(base1, "/api/p2p/block_req", env_req_block, timeout_s=30.0)
        rb.raise_for_status()
        jb = rb.json()
        assert jb.get("ok") is True
        blk = jb.get("block") or {}
        assert isinstance(blk, dict)

        hdr2 = blk.get("header") or (blk.get("block") or {}).get("header") or {}
        assert isinstance(hdr2, dict)
        if sr1:
            assert str(hdr2.get("state_root") or "") == sr1
        if tr1:
            assert str(hdr2.get("txs_root") or "") == tr1

        # --- BLOCK_REQ (want=header) ---
        env_req_hdr = dict(env_req_block)
        env_req_hdr["payload"] = {"height": h, "want": "header"}
        rh = _post_json(base1, "/api/p2p/block_req", env_req_hdr, timeout_s=30.0)
        rh.raise_for_status()
        jh = rh.json()
        assert jh.get("ok") is True
        hdr_only = jh.get("header") or {}
        assert isinstance(hdr_only, dict)
        if sr1:
            assert str(hdr_only.get("state_root") or "") == sr1
        if tr1:
            assert str(hdr_only.get("txs_root") or "") == tr1

        # --- BLOCK_ANNOUNCE hits receiver ---
        env_announce = {
            "type": "BLOCK_ANNOUNCE",
            "from_node_id": "node-1",
            "chain_id": chain_id,
            "ts_ms": time.time() * 1000.0,
            "payload": {"height": h, "state_root": sr1, "txs_root": tr1},
            "hops": 0,
        }
        ra = _post_json(base2, "/api/p2p/block_announce", env_announce, timeout_s=30.0)
        ra.raise_for_status()
        ja = ra.json()
        assert ja.get("ok") is True
        assert ja.get("announced") is True
        assert int(ja.get("height") or 0) == h

    finally:
        for p in (p1, p2):
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass