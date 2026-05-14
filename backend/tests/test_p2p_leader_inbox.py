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


def _wait_ok(
    url: str,
    *,
    proc: subprocess.Popen,
    stderr_path: Path,
    timeout_s: float = 90.0,  # ⬅️ bumped (startup is heavy)
) -> None:
    deadline = time.time() + timeout_s
    last = None

    while time.time() < deadline:
        # if process died, surface stderr immediately
        rc = proc.poll()
        if rc is not None:
            raise RuntimeError(
                f"server process exited (rc={rc}) while waiting for {url}\n"
                f"--- stderr tail ---\n{_tail(stderr_path)}\n"
            )

        try:
            r = httpx.get(url, timeout=1.0)
            # any response means socket is up
            if r.status_code < 600:
                return
            last = f"{r.status_code} {r.text}"
        except Exception as e:
            last = repr(e)

        time.sleep(0.2)

    raise RuntimeError(
        f"service not ready: {url} (last={last})\n"
        f"--- stderr tail ---\n{_tail(stderr_path)}\n"
    )


@pytest.mark.integration
def test_p2p_non_leader_relays_to_leader(tmp_path: Path):
    port1 = 18080
    port2 = 18081
    base1 = f"http://127.0.0.1:{port1}"
    base2 = f"http://127.0.0.1:{port2}"
    cs1 = base1 + "/api/chain_sim"
    cs2 = base2 + "/api/chain_sim"

    peers_json = f"""[
      {{"node_id":"n1","base_url":"{base1}","val_id":"pho1-dev-val1","role":"validator"}},
      {{"node_id":"n2","base_url":"{base2}","val_id":"pho1-dev-val2","role":"validator"}}
    ]"""

    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "devnet",
        "allocs": [
            {"address": "pho1-dev-val1", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-val2", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-user1", "balances": {"PHO": "1000", "TESS": "0"}},
        ],
        "validators": [
            {"address": "pho1-dev-val1", "power": "100", "commission": "0"},
            {"address": "pho1-dev-val2", "power": "100", "commission": "0"},
        ],
    }

    repo_root = os.getcwd()

    def mk_env(node_id: str, self_val: str, base_url: str) -> dict:
        env = os.environ.copy()
        env["GLYPHCHAIN_SELF_VAL_ID"] = self_val
        env["GLYPHCHAIN_NODE_ID"] = node_id
        env["GLYPHCHAIN_BASE_URL"] = base_url
        env["P2P_PEERS_JSON"] = peers_json
        # make sure subprocess can import backend.*
        env["PYTHONPATH"] = repo_root + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return env

    stderr1 = tmp_path / "uvicorn_1.stderr.log"
    stderr2 = tmp_path / "uvicorn_2.stderr.log"
    stdout1 = tmp_path / "uvicorn_1.stdout.log"
    stdout2 = tmp_path / "uvicorn_2.stdout.log"

    p1 = p2 = None
    f_out1 = f_err1 = f_out2 = f_err2 = None

    try:
        f_out1 = open(stdout1, "w", encoding="utf-8")
        f_err1 = open(stderr1, "w", encoding="utf-8")
        f_out2 = open(stdout2, "w", encoding="utf-8")
        f_err2 = open(stderr2, "w", encoding="utf-8")

        p1 = subprocess.Popen(
            ["python", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port1), "--log-level", "warning"],
            env=mk_env("n1", "pho1-dev-val1", base1),
            cwd=repo_root,
            stdout=f_out1,
            stderr=f_err1,
            text=True,
        )
        p2 = subprocess.Popen(
            ["python", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port2), "--log-level", "warning"],
            env=mk_env("n2", "pho1-dev-val2", base2),
            cwd=repo_root,
            stdout=f_out2,
            stderr=f_err2,
            text=True,
        )

        _wait_ok(cs1 + "/dev/blocks?limit=1", proc=p1, stderr_path=stderr1)
        _wait_ok(cs2 + "/dev/blocks?limit=1", proc=p2, stderr_path=stderr2)

        r = httpx.post(cs1 + "/dev/reset", json=genesis, timeout=8.0)
        assert r.status_code == 200, r.text
        r = httpx.post(cs2 + "/dev/reset", json=genesis, timeout=8.0)
        assert r.status_code == 200, r.text

        leader = httpx.get(cs1 + "/dev/leader_inbox/leader", timeout=5.0).json()["leader"]
        assert leader == "pho1-dev-val1"

        tx = {
            "from_addr": "pho1-dev-user1",
            "nonce": 1,
            "tx_type": "BANK_SEND",
            "payload": {"to": "pho1-dev-val1", "denom": "PHO", "amount": "1"},
        }

        resp = httpx.post(cs2 + "/dev/submit_tx_async", json=tx, timeout=8.0)
        assert resp.status_code == 202, resp.text
        j = resp.json()
        assert j.get("relayed") is True
        qid = j.get("qid")
        assert qid, j

        poll = httpx.get(cs1 + f"/dev/leader_inbox/poll?leader_id={leader}&limit=10", timeout=8.0).json()
        assert qid in (poll.get("qids") or []), poll

        deadline = time.time() + 10.0
        last = None
        while time.time() < deadline:
            st = httpx.get(cs1 + f"/dev/tx_status/{qid}", timeout=5.0).json()
            last = st
            if (st.get("status") or {}).get("state") == "finalized":
                return
            time.sleep(0.2)
        pytest.fail(f"tx did not finalize: {last}")

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