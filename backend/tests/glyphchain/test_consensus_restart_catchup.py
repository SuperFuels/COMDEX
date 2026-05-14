# backend/tests/test_consensus_restart_catchup.py
from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]


def _tail(path: Path, n: int = 80) -> str:
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
            last = repr(e)
        time.sleep(0.2)
    raise RuntimeError(f"service not ready: {url} last={last!r}\n--- stderr ---\n{_tail(stderr_path)}")


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

            # ✅ per-node consensus persistence directory
            "GLYPHCHAIN_STATE_DIR": str(state_dir),

            # keep chain_sim from doing surprise background work for this test
            "CHAIN_SIM_ASYNC_ENABLED": "0",
            "CHAIN_SIM_REPLAY_ON_STARTUP": "0",
            "CHAIN_SIM_REPLAY_STRICT": "0",

            # reduce startup storms in this test process
            "AION_ENABLE_BOOT_LOADER": env.get("AION_ENABLE_BOOT_LOADER", "0"),
            "AION_ENABLE_HQCE": env.get("AION_ENABLE_HQCE", "0"),
            "AION_ENABLE_GHX_TELEMETRY": env.get("AION_ENABLE_GHX_TELEMETRY", "0"),
            "AION_ENABLE_DUAL_HEARTBEAT": env.get("AION_ENABLE_DUAL_HEARTBEAT", "0"),
            "AION_ENABLE_COG_THREADS": env.get("AION_ENABLE_COG_THREADS", "0"),
            "AION_ENABLE_SCHEDULER": env.get("AION_ENABLE_SCHEDULER", "0"),
            "AION_ENABLE_PHI_BALANCE": env.get("AION_ENABLE_PHI_BALANCE", "0"),

            # faster ticks for test
            "CONSENSUS_TICK_MS": env.get("CONSENSUS_TICK_MS", "25"),
        }
    )

    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "warning",
    ]
    stderr_f = stderr_path.open("w", encoding="utf-8", errors="ignore")
    return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=stderr_f, text=True)


def _post(base: str, path: str, body: Dict[str, Any], timeout_s: float = 10.0) -> Dict[str, Any]:
    r = httpx.post(base + path, json=body, timeout=timeout_s)
    if r.status_code == 422:
        raise RuntimeError(f"422 at {base+path}:\n{r.text[:2000]}\n\nbody={body!r}")
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
                {
                    "base_url": base_j,
                    "node_id": node_ids[j],
                    "val_id": val_ids[j],
                    "role": "peer",
                },
                timeout_s=8.0,
            )


def _wait_mesh_visible(bases: list[str], *, want: int, stderrs: list[Path], timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        ok = True
        for b in bases:
            try:
                j = _get(b, "/api/p2p/peers", timeout_s=5.0)
                peers = j.get("peers") or []
                n = len(peers) if isinstance(peers, list) else 0
                if n < want:
                    ok = False
                    last = {"base": b, "peers": n, "json": j}
                    break
            except Exception as e:
                ok = False
                last = {"base": b, "err": repr(e)}
                break
        if ok:
            return
        time.sleep(0.2)
    raise RuntimeError(f"peer mesh not visible; last={last!r}\n--- stderr[1] ---\n{_tail(stderrs[0])}")


def _poll_finalized(bases: list[str], *, timeout_s: float = 60.0) -> list[int]:
    deadline = time.time() + timeout_s
    last: list[int] = [0 for _ in bases]
    while time.time() < deadline:
        hs: list[int] = []
        for b in bases:
            st = _get(b, "/api/p2p/consensus_status", timeout_s=10.0)
            hs.append(int(st.get("finalized_height") or 0))
        last = hs
        return last
    return last


@pytest.mark.integration
def test_consensus_restart_catchup_does_not_regress(tmp_path: Path) -> None:
    chain_id = "glyphchain-dev"
    vals = ["val-1", "val-2", "val-3", "val-4"]
    validators_env = ",".join(vals)

    ports = [18201, 18202, 18203, 18204]
    bases = [f"http://127.0.0.1:{p}" for p in ports]
    node_ids = [f"node-{i}" for i in range(1, 5)]

    procs: list[subprocess.Popen[str]] = []
    stderrs: list[Path] = []
    state_dirs: list[Path] = []

    # spawn 4 nodes with isolated state dirs
    for i, (p, v) in enumerate(zip(ports, vals), start=1):
        stderr = tmp_path / f"restart-n{i}.stderr.log"
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

    # we will kill/restart node 4
    kill_idx = 3
    K = 8

    try:
        # wait for p2p ok
        for b, s in zip(bases, stderrs):
            _wait_ok(b + "/api/p2p/peers", stderr_path=s, timeout_s=240.0)

        # connect mesh
        _connect_mesh(bases, node_ids, vals)
        _wait_mesh_visible(bases, want=3, stderrs=stderrs, timeout_s=30.0)

        # wait until the soon-to-be-killed node has made *some* progress (or at least observed progress)
        deadline = time.time() + 60.0
        h_before = 0
        while time.time() < deadline:
            st = _get(bases[kill_idx], "/api/p2p/consensus_status", timeout_s=10.0)
            h_before = int(st.get("finalized_height") or 0)
            if h_before >= 2:
                break
            time.sleep(0.25)

        # kill node 4 hard
        p4 = procs[kill_idx]
        try:
            os.kill(p4.pid, signal.SIGKILL)
        except Exception:
            try:
                p4.kill()
            except Exception:
                pass
        try:
            p4.wait(timeout=5)
        except Exception:
            pass

        # keep the remaining 3 running; give them time to advance
        time.sleep(2.0)

        # restart node 4 with the SAME state dir
        stderr_restart = tmp_path / "restart-node-4.stderr.log"
        stderrs[kill_idx] = stderr_restart

        p4r = _spawn_node(
            port=ports[kill_idx],
            node_id=node_ids[kill_idx],
            val_id=vals[kill_idx],
            chain_id=chain_id,
            validators=validators_env,
            stderr_path=stderr_restart,
            state_dir=state_dirs[kill_idx],  # ✅ SAME DIR
        )
        procs[kill_idx] = p4r

        # wait until it’s back
        _wait_ok(bases[kill_idx] + "/api/p2p/peers", stderr_path=stderr_restart, timeout_s=240.0)

        # reconnect mesh (idempotent; ensures everyone re-learns restarted peer)
        _connect_mesh(bases, node_ids, vals)
        _wait_mesh_visible(bases, want=3, stderrs=stderrs, timeout_s=30.0)

        # non-regression check: after restart, finalized_height should not drop below what it had
        st_after = _get(bases[kill_idx], "/api/p2p/consensus_status", timeout_s=10.0)
        h_after = int(st_after.get("finalized_height") or 0)
        assert h_after >= h_before, f"regressed: before={h_before}, after={h_after}\n{st_after!r}"

        # catch-up check: eventually reach K
        deadline = time.time() + 120.0
        last: list[int] | None = None
        while time.time() < deadline:
            hs: list[int] = []
            for b in bases:
                st = _get(b, "/api/p2p/consensus_status", timeout_s=10.0)
                hs.append(int(st.get("finalized_height") or 0))
            last = hs

            if hs[kill_idx] >= K:
                return

            time.sleep(0.25)

        raise RuntimeError(
            f"restarted node did not catch up to K={K}; finalized_heights={last!r}\n--- stderr(node4) ---\n{_tail(stderrs[kill_idx])}"
        )

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