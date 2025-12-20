# backend/tests/helpers.py
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, IO, List, Optional
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes
import httpx


@dataclass
class NodeProc:
    idx: int
    port: int
    base_url: str
    state_dir: str
    proc: subprocess.Popen
    node_id: str = ""
    val_id: str = ""
    chain_id: str = ""
    log_path: str = ""
    _log_fp: Optional[IO[str]] = None

    # PR5.1: deterministic per-node P2P signing identity for integration tests
    p2p_privkey_hex: str = ""
    p2p_pubkey_hex: str = ""

    def __getitem__(self, k: str):
        if k == "node_id":
            return self.node_id
        if k == "chain_id":
            return self.chain_id
        if k in ("base_url", "url"):
            return self.base_url
        if k == "port":
            return self.port
        if k in ("val_id", "validator_id"):
            return self.val_id
        raise KeyError(k)


# -------------------------
# env helpers
# -------------------------

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except Exception:
        return float(default)


# -------------------------
# deterministic test keys (PR5.1)
# -------------------------

def _test_privkey_hex(idx: int) -> str:
    """
    Deterministic per-node 32-byte seed -> ed25519 private key bytes (seed).
    Stable across runs to keep integration deterministic.
    """
    seed = hashlib.sha256(f"glyphchain-test-p2p-key:{int(idx)}".encode("utf-8")).digest()
    return seed.hex()


def _ed25519_pubkey_hex_from_priv_hex(priv_hex: str) -> str:
    """
    Derive ed25519 pubkey from 32-byte private key seed hex.
    Uses cryptography (commonly installed in python envs).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        sk = bytes.fromhex((priv_hex or "").strip())
        pk = Ed25519PrivateKey.from_private_bytes(sk).public_key()
        raw = pk.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw.hex()
    except Exception:
        return ""


# -------------------------
# ASGI app import
# -------------------------

def _app_import() -> str:
    """
    IMPORTANT: do NOT import backend.main here (it has heavy side effects in this repo).
    Prefer env var, else default to backend.main:app.
    """
    env = (os.getenv("GLYPHCHAIN_ASGI_APP", "") or "").strip()
    return env or "backend.main:app"


def _sanitize_lifespan(val: str) -> str:
    """
    uvicorn --lifespan accepts: auto|on|off
    People sometimes pass true/false; normalize that to on/off.
    """
    v = (val or "").strip().lower()
    if v in ("on", "off", "auto"):
        return v
    if v in ("1", "true", "yes", "y"):
        return "on"
    if v in ("0", "false", "no", "n", ""):
        return "off"
    return "off"


# -------------------------
# http helpers
# -------------------------

async def http_post(base_url: str, path: str, json_body: Dict[str, Any], timeout_s: float = 6.0) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=timeout_s) as c:
        r = await c.post(url, json=json_body)
        try:
            j = r.json()
        except Exception:
            j = None
        out: Dict[str, Any] = {"status": r.status_code, "json": j, "text": r.text}
        if isinstance(j, dict):
            out.update(j)
        return out


async def http_get(base_url: str, path: str, timeout_s: float = 6.0) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=timeout_s) as c:
        r = await c.get(url)
        try:
            j = r.json()
        except Exception:
            j = None
        out: Dict[str, Any] = {"status": r.status_code, "json": j, "text": r.text}
        if isinstance(j, dict):
            out.update(j)
        return out


async def connect_full_mesh(nodes: List[NodeProc]) -> None:
    """
    Ensure every node knows every other node via /api/p2p/connect.
    Required so consensus broadcasts can reach peers in tests.
    Best-effort.
    """
    for src in nodes:
        for dst in nodes:
            if src.idx == dst.idx:
                continue
            try:
                await http_post(
                    src.base_url,
                    "/api/p2p/connect",
                    {
                        "base_url": dst.base_url,
                        "node_id": dst.node_id,
                        "val_id": dst.val_id,
                        "role": "peer",
                    },
                    timeout_s=6.0,
                )
            except Exception:
                pass


async def hello_full_mesh(nodes: List[NodeProc]) -> None:
    """
    Ensure every node registers every other node's identity via /api/p2p/hello.
    Populates peer_store.pubkey_hex + hello_ok.
    Best-effort.
    """
    from backend.modules.p2p.crypto_ed25519 import (
        canonical_hello_sign_bytes,
        sign_ed25519,
    )

    def now_ms() -> float:
        return float(time.time() * 1000.0)

    for src in nodes:
        if not src.p2p_pubkey_hex or not src.p2p_privkey_hex:
            continue

        for dst in nodes:
            if src.idx == dst.idx:
                continue

            try:
                msg = canonical_hello_sign_bytes(
                    chain_id=src.chain_id,
                    node_id=src.node_id,
                    val_id=src.val_id,
                    base_url=src.base_url,
                    pubkey_hex=src.p2p_pubkey_hex,
                )
                sig_hex = sign_ed25519(src.p2p_privkey_hex, msg)

                env = {
                    "type": "HELLO",
                    "from_node_id": src.node_id,
                    "from_val_id": src.val_id,
                    "chain_id": src.chain_id,
                    "ts_ms": now_ms(),
                    "payload": {
                        "base_url": src.base_url,
                        "val_id": src.val_id,
                        "role": "peer",
                        "pubkey_hex": src.p2p_pubkey_hex,
                        "sig_hex": sig_hex,
                    },
                    "hops": 0,
                }

                # include headers too (harmless if HELLO doesn't require them)
                url = dst.base_url.rstrip("/") + "/api/p2p/hello"
                headers = {
                    "x-p2p-node-id": src.node_id,
                    "x-p2p-val-id": src.val_id,
                    "x-p2p-chain-id": src.chain_id,
                }

                async with httpx.AsyncClient(timeout=6.0) as c:
                    await c.post(url, json=env, headers=headers)

            except Exception:
                pass


# -------------------------
# port helpers
# -------------------------

def _is_port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", int(port)))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _pick_free_ports(n: int, start: int = 18080) -> List[int]:
    ports: List[int] = []
    p = int(start)
    while len(ports) < int(n):
        if _is_port_free(p):
            ports.append(p)
        p += 1
        if p > 65500:
            raise RuntimeError("could not find free ports")
    return ports


def _tcp_listening(host: str, port: int, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return True
    except Exception:
        return False


def _tail_file(path: str, max_bytes: int = 6000) -> str:
    if not path:
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            n = f.tell()
            f.seek(max(0, n - max_bytes), os.SEEK_SET)
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


# -------------------------
# readiness
# -------------------------

async def wait_nodes_ready(nodes: List[NodeProc], timeout_s: float = 90.0) -> None:
    """
    Two-phase readiness:
      1) TCP connect succeeds (uvicorn bound)
      2) /api/p2p/peers returns {ok:true}
    """
    timeout_s = float(_env_float("GLYPHCHAIN_TEST_READY_TIMEOUT_S", timeout_s))
    deadline = time.time() + float(timeout_s)

    pending: Dict[int, NodeProc] = {n.idx: n for n in nodes}
    last_err: Dict[int, str] = {}

    while pending and time.time() < deadline:
        done: List[int] = []

        for idx, n in list(pending.items()):
            if n.proc.poll() is not None:
                tail = _tail_file(n.log_path)
                raise RuntimeError(
                    f"node exited before ready: {n.base_url}\n"
                    f"exit_code={n.proc.returncode}\n"
                    f"--- uvicorn log tail ---\n{tail}"
                )

            if not _tcp_listening("127.0.0.1", n.port, timeout_s=0.2):
                last_err[idx] = "tcp not listening yet"
                continue

            try:
                r = await http_get(n.base_url, "/api/p2p/peers", timeout_s=2.0)
                if int(r.get("status") or 0) == 200 and isinstance(r.get("json"), dict) and r["json"].get("ok"):
                    done.append(idx)
                else:
                    last_err[idx] = f"http status={r.get('status')} json={r.get('json')}"
            except Exception as e:
                last_err[idx] = str(e)

        for idx in done:
            pending.pop(idx, None)
            last_err.pop(idx, None)

        if pending:
            await asyncio.sleep(0.25)

    if pending:
        chunks: List[str] = []
        for idx, n in pending.items():
            tail = _tail_file(n.log_path)
            chunks.append(f"\n=== {n.base_url} (port={n.port}) last_err={last_err.get(idx)} ===\n{tail}")
        left = ", ".join([pending[i].base_url for i in pending])
        raise RuntimeError(f"nodes not ready before timeout: {left}\n{''.join(chunks)}")


# -------------------------
# process lifecycle
# -------------------------

def _start_n_nodes_sync(
    n: int,
    *,
    base_port: int = 18080,
    chain_id: str = "glyphchain-dev",
    validators: Optional[List[str]] = None,
) -> List[NodeProc]:
    nn = int(n or 0)
    if nn <= 0:
        raise ValueError("n must be > 0")

    vals = validators or [f"val{i+1}" for i in range(nn)]
    vset_env = ",".join([f"{vid}:1" for vid in vals])

    ports = _pick_free_ports(nn, start=int(base_port or 18080))

    # Precompute peer bootstrap list so restarted nodes re-learn peers deterministically.
    peer_items: List[Dict[str, Any]] = []
    for i in range(nn):
        peer_items.append(
            {
                "node_id": f"node{i+1}",
                "base_url": f"http://127.0.0.1:{int(ports[i])}",
                "val_id": vals[i],
                "role": "peer",
            }
        )
    peers_json = json.dumps(peer_items)
    out: List[NodeProc] = []

    lifespan = _sanitize_lifespan(os.getenv("GLYPHCHAIN_TEST_UVICORN_LIFESPAN", "off"))

    for i in range(nn):
        port = int(ports[i])
        base_url = f"http://127.0.0.1:{port}"
        state_dir = tempfile.mkdtemp(prefix=f"glyphchain-node{i+1}-")
        log_path = os.path.join(state_dir, "uvicorn.log")
        log_fp = open(log_path, "a", buffering=1, encoding="utf-8")

        env = dict(os.environ)

        node_id = f"node{i+1}"
        val_id = vals[i]

        env["GLYPHCHAIN_CHAIN_ID"] = chain_id
        env["GLYPHCHAIN_NODE_ID"] = node_id
        env["GLYPHCHAIN_SELF_VAL_ID"] = val_id
        env["GLYPHCHAIN_BASE_URL"] = base_url
        env["GLYPHCHAIN_STATE_DIR"] = state_dir

        # per-node sqlite so blocks/txs don’t collide across nodes
        env["CHAIN_SIM_DB_PATH"] = os.path.join(state_dir, "chain_sim.sqlite3")

        # Critical: peer bootstrap survives restart (peer_store is in-memory otherwise)
        env["P2P_PEERS_JSON"] = peers_json

        # --- consensus test wiring (CSV "val:power,val:power") ---
        env["GLYPHCHAIN_VALIDATORS"] = vset_env
        env["GLYPHCHAIN_VALIDATOR_SET"] = vset_env
        env["CONSENSUS_VALIDATORS"] = vset_env

        # Force consensus on in subprocesses
        env["GLYPHCHAIN_CONSENSUS_ENABLE"] = "1"

        # PR5.1: deterministic per-node P2P signing key
        p2p_priv = _test_privkey_hex(i)
        env["GLYPHCHAIN_P2P_PRIVKEY_HEX"] = p2p_priv

        cmd = [
            "python",
            "-m",
            "uvicorn",
            _app_import(),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
            "--no-access-log",
            "--lifespan",
            lifespan,
        ]

        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            text=True,
        )

        p2p_pub = _ed25519_pubkey_hex_from_priv_hex(p2p_priv)

        out.append(
            NodeProc(
                idx=i,
                port=port,
                base_url=base_url,
                state_dir=state_dir,
                proc=proc,
                node_id=node_id,
                val_id=val_id,
                chain_id=chain_id,
                log_path=log_path,
                _log_fp=log_fp,
                p2p_privkey_hex=p2p_priv,
                p2p_pubkey_hex=p2p_pub,
            )
        )

    return out


async def start_n_nodes(
    n: int,
    *,
    base_port: int = 18080,
    chain_id: str = "glyphchain-dev",
    validators: Optional[List[str]] = None,
) -> List[NodeProc]:
    nodes = _start_n_nodes_sync(n, base_port=base_port, chain_id=chain_id, validators=validators)
    await wait_nodes_ready(nodes, timeout_s=90.0)

    # peer the nodes so consensus gossip works
    await connect_full_mesh(nodes)

    # PR5.1: identity binding so sig verification can work
    await hello_full_mesh(nodes)

    return nodes


def _stop_nodes_sync(nodes: List[NodeProc]) -> None:
    for n in nodes:
        try:
            if n.proc.poll() is None:
                n.proc.terminate()
        except Exception:
            pass

    t0 = time.time()
    for n in nodes:
        try:
            if n.proc.poll() is None:
                n.proc.wait(timeout=max(0.0, 8.0 - (time.time() - t0)))
        except Exception:
            try:
                if n.proc.poll() is None:
                    n.proc.kill()
            except Exception:
                pass

    for n in nodes:
        try:
            try:
                if getattr(n, "_log_fp", None) is not None:
                    n._log_fp.close()
            except Exception:
                pass
            shutil.rmtree(n.state_dir, ignore_errors=True)
        except Exception:
            pass


async def stop_nodes(nodes: List[NodeProc]) -> None:
    _stop_nodes_sync(nodes)
    await asyncio.sleep(0)  # yield back to event loop