# backend/tests/test_consensus_sync_gap_catchup.py
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]


def _tail(path: Path, n: int = 120) -> str:
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
        time.sleep(0.2)
    raise RuntimeError(f"service not ready: {url} last={last!r}\n--- stderr ---\n{_tail(stderr_path)}")


def _post(base: str, path: str, body: Dict[str, Any], timeout_s: float = 10.0) -> Dict[str, Any]:
    r = httpx.post(base + path, json=body, timeout=timeout_s)
    r.raise_for_status()
    j = r.json()
    assert isinstance(j, dict)
    return j


def _get(base: str, path: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    r = httpx.get(base + path, timeout=timeout_s)
    r.raise_for_status()
    j = r.json()
    assert isinstance(j, dict)
    return j


def _connect_mesh(bases: list[str], node_ids: list[str], val_ids: list[str]) -> None:
    for i, base_i in enumerate(bases):
        for j, base_j in enumerate(bases):
            if i == j:
                continue
            _post(
                base_i,
                "/api/p2p/connect",
                {"base_url": base_j, "node_id": node_ids[j], "val_id": val_ids[j], "role": "peer"},
                timeout_s=8.0,
            )


def _spawn_node(
    *,
    port: int,
    node_id: str,
    val_id: str,
    chain_id: str,
    validators: str,
    stderr_path: Path,
    state_dir: Path,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "GLYPHCHAIN_BASE_URL": f"http://127.0.0.1:{port}",
            "GLYPHCHAIN_NODE_ID": node_id,
            "GLYPHCHAIN_CHAIN_ID": chain_id,
            "GLYPHCHAIN_SELF_VAL_ID": val_id,
            "GLYPHCHAIN_VALIDATORS": validators,
            "GLYPHCHAIN_STATE_DIR": str(state_dir),

            "CHAIN_SIM_ASYNC_ENABLED": "0",
            "CHAIN_SIM_REPLAY_ON_STARTUP": "0",
            "CHAIN_SIM_REPLAY_STRICT": "0",

            "AION_ENABLE_BOOT_LOADER": env.get("AION_ENABLE_BOOT_LOADER", "0"),
            "AION_ENABLE_HQCE": env.get("AION_ENABLE_HQCE", "0"),
            "AION_ENABLE_GHX_TELEMETRY": env.get("AION_ENABLE_GHX_TELEMETRY", "0"),
            "AION_ENABLE_DUAL_HEARTBEAT": env.get("AION_ENABLE_DUAL_HEARTBEAT", "0"),
            "AION_ENABLE_COG_THREADS": env.get("AION_ENABLE_COG_THREADS", "0"),
            "AION_ENABLE_SCHEDULER": env.get("AION_ENABLE_SCHEDULER", "0"),
            "AION_ENABLE_PHI_BALANCE": env.get("AION_ENABLE_PHI_BALANCE", "0"),

            "CONSENSUS_TICK_MS": env.get("CONSENSUS_TICK_MS", "25"),
            "CONSENSUS_ROUND_TIMEOUT_MS": env.get("CONSENSUS_ROUND_TIMEOUT_MS", "600"),
            "CONSENSUS_SYNC_EVERY_MS": env.get("CONSENSUS_SYNC_EVERY_MS", "800"),
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


@pytest.mark.integration
def test_consensus_sync_gap_catchup(tmp_path: Path) -> None:
    chain_id = "glyphchain-dev"
    vals = ["val-1", "val-2", "val-3", "val-4"]
    validators_env = ",".join(vals)

    ports = [18301, 18302, 18303, 18304]
    bases = [f"http://127.0.0.1:{p}" for p in ports]
    node_ids = [f"node-{i}" for i in range(1, 5)]

    procs: list[subprocess.Popen[str]] = []
    stderrs: list[Path] = []
    state_dirs: list[Path] = []

    for i, (p, v) in enumerate(zip(ports, vals), start=1):
        stderr = tmp_path / f"n{i}.stderr.log"
        stderrs.append(stderr)

        state_dir = tmp_path / f"state-node-{i}"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_dirs.append(state_dir)

        procs.append(
            _spawn_node(
                port=p,
                node_id=f"node-{i}",
                val_id=v,
                chain_id=chain_id,
                validators=validators_env,
                stderr_path=stderr,
                state_dir=state_dir,
            )
        )

    try:
        for b, s in zip(bases, stderrs):
            _wait_ok(b + "/api/p2p/peers", stderr_path=s, timeout_s=240.0)

        _connect_mesh(bases, node_ids, vals)

        # let all 4 progress a bit
        K1 = 3
        deadline = time.time() + 120.0
        while time.time() < deadline:
            hs = [int(_get(b, "/api/p2p/consensus_status").get("finalized_height") or 0) for b in bases]
            if max(hs) >= K1:
                break
            time.sleep(0.25)

        # kill node-4 hard (misses a whole finalized window)
        procs[3].kill()
        procs[3].wait(timeout=10)

        # remaining 3 should continue finalizing (round timeouts should skip dead leader)
        K2 = 10
        alive_bases = bases[:3]
        deadline = time.time() + 180.0
        while time.time() < deadline:
            hs = [int(_get(b, "/api/p2p/consensus_status").get("finalized_height") or 0) for b in alive_bases]
            if min(hs) >= K2:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(f"alive nodes did not reach K2={K2}; hs={hs!r}\n--- stderr(n1) ---\n{_tail(stderrs[0])}")

        # restart node-4 with SAME state_dir (it missed the window)
        stderr4b = tmp_path / "n4b.stderr.log"
        stderrs[3] = stderr4b
        procs[3] = _spawn_node(
            port=ports[3],
            node_id="node-4",
            val_id="val-4",
            chain_id=chain_id,
            validators=validators_env,
            stderr_path=stderr4b,
            state_dir=state_dirs[3],
        )
        _wait_ok(bases[3] + "/api/p2p/peers", stderr_path=stderr4b, timeout_s=240.0)

        # IMPORTANT: re-add peers into node-4 peer_store so it can request_sync()
        for j in range(3):
            _post(
                bases[3],
                "/api/p2p/connect",
                {"base_url": bases[j], "node_id": node_ids[j], "val_id": vals[j], "role": "peer"},
                timeout_s=8.0,
            )

        # now node-4 must catch up via PR4 sync loop
        deadline = time.time() + 180.0
        last = None
        while time.time() < deadline:
            h4 = int(_get(bases[3], "/api/p2p/consensus_status").get("finalized_height") or 0)
            last = h4
            if h4 >= K2:
                return
            time.sleep(0.25)

        raise RuntimeError(f"node-4 did not catch up to K2={K2}; last={last}\n--- stderr(node4) ---\n{_tail(stderrs[3])}")

    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass