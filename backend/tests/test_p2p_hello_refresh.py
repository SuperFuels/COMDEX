import os
import signal
import subprocess
import time
from pathlib import Path

import httpx
import pytest


def _tail(path: Path, n: int = 200) -> str:
    try:
        txt = path.read_text(errors="replace")
    except Exception:
        return f"<could not read {path}>"
    lines = txt.splitlines()
    return "\n".join(lines[-n:])


def _wait_ok(url: str, *, proc: subprocess.Popen, stderr_path: Path, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    last = None

    while time.time() < deadline:
        rc = proc.poll()
        if rc is not None:
            raise RuntimeError(
                f"server process exited (rc={rc}) while waiting for {url}\n"
                f"--- stderr tail ---\n{_tail(stderr_path)}\n"
            )

        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code < 600:
                return
            last = f"{r.status_code} {r.text}"
        except Exception as e:
            last = repr(e)

        time.sleep(0.25)

    raise RuntimeError(
        f"service not ready: {url} (last={last})\n"
        f"--- stderr tail ---\n{_tail(stderr_path)}\n"
    )


@pytest.mark.integration
def test_p2p_hello_registers_and_refresh_merges(tmp_path: Path):
    port1 = 18090
    port2 = 18091

    base1 = f"http://127.0.0.1:{port1}"
    base2 = f"http://127.0.0.1:{port2}"

    p2p1 = base1 + "/api/p2p"
    p2p2 = base2 + "/api/p2p"

    repo_root = os.getcwd()

    seed_peer = {
        "node_id": "n-seed",
        "base_url": "http://127.0.0.1:19999",
        "val_id": "pho1-dev-seed",
        "role": "peer",
    }
    seed_peers_json = f"[{seed_peer!r}]".replace("'", '"')

    def mk_env(node_id: str, self_val: str, base_url: str, *, seed: bool) -> dict:
        env = os.environ.copy()
        env["GLYPHCHAIN_CHAIN_ID"] = "glyphchain-dev"
        env["GLYPHCHAIN_NODE_ID"] = node_id
        env["GLYPHCHAIN_SELF_VAL_ID"] = self_val
        env["GLYPHCHAIN_BASE_URL"] = base_url
        env["P2P_PEERS_JSON"] = seed_peers_json if seed else "[]"
        env["PYTHONPATH"] = repo_root + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return env

    stderr1 = tmp_path / "uvicorn_p2p_1.stderr.log"
    stderr2 = tmp_path / "uvicorn_p2p_2.stderr.log"
    stdout1 = tmp_path / "uvicorn_p2p_1.stdout.log"
    stdout2 = tmp_path / "uvicorn_p2p_2.stdout.log"

    p1 = p2 = None
    f_out1 = f_err1 = f_out2 = f_err2 = None

    try:
        f_out1 = open(stdout1, "w", encoding="utf-8")
        f_err1 = open(stderr1, "w", encoding="utf-8")
        f_out2 = open(stdout2, "w", encoding="utf-8")
        f_err2 = open(stderr2, "w", encoding="utf-8")

        # Start node1 first (avoid CPU/RAM contention during heavy startup)
        p1 = subprocess.Popen(
            ["python", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port1), "--log-level", "warning"],
            env=mk_env("n1", "pho1-dev-val1", base1, seed=True),
            cwd=repo_root,
            stdout=f_out1,
            stderr=f_err1,
            text=True,
        )
        _wait_ok(p2p1 + "/peers", proc=p1, stderr_path=stderr1, timeout_s=90.0)

        # Then start node2
        p2 = subprocess.Popen(
            ["python", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port2), "--log-level", "warning"],
            env=mk_env("n2", "pho1-dev-val2", base2, seed=False),
            cwd=repo_root,
            stdout=f_out2,
            stderr=f_err2,
            text=True,
        )
        _wait_ok(p2p2 + "/peers", proc=p2, stderr_path=stderr2, timeout_s=90.0)

        # 1) HELLO: node2 -> node1 registers node2 on node1
        hello_env = {
            "type": "HELLO",
            "from_node_id": "n2",
            "chain_id": "glyphchain-dev",
            "ts_ms": float(time.time() * 1000.0),
            "payload": {"base_url": base2, "val_id": "pho1-dev-val2", "role": "validator"},
            "hops": 0,
        }
        r = httpx.post(p2p1 + "/hello", json=hello_env, timeout=10.0)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        peers1 = j.get("peers") or []
        assert any(p.get("node_id") == "n2" and p.get("base_url") == base2 for p in peers1), peers1

        # 2) REFRESH: node2 pulls peers from node1 and merges (should learn seeded peer)
        r = httpx.post(p2p2 + "/refresh", json={"base_url": base1}, timeout=15.0)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        peers2 = j.get("peers") or []
        assert any(p.get("node_id") == "n-seed" for p in peers2), peers2

    finally:
        for p in (p2, p1):
            if p is None:
                continue
            try:
                p.send_signal(signal.SIGTERM)
            except Exception:
                pass
        for p in (p2, p1):
            if p is None:
                continue
            try:
                p.wait(timeout=5.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        for f in (f_out1, f_err1, f_out2, f_err2):
            try:
                if f:
                    f.close()
            except Exception:
                pass