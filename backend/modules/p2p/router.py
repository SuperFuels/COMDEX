from __future__ import annotations

import hashlib
import json
import os
import time
import random
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, HTTPException, Request
from backend.modules.chain_sim.chain_sim_ledger import get_block
from .p2p_types import P2PEnvelope
from .peer_store import add_peer, list_peers, load_peers_from_env
from .rate_limit import allow as rl_allow
from .transport_http import get_json, post_json
import asyncio
import httpx

router = APIRouter()

# --- optional consensus wiring (PR1) ---
_CONSENSUS_OK = False
_CONSENSUS_ERR: Optional[str] = None
get_engine = None
Proposal = None
Vote = None

try:
    from backend.modules.consensus.engine import get_engine as _get_engine
    from backend.modules.consensus.types import Proposal as _Proposal, Vote as _Vote

    get_engine = _get_engine
    Proposal = _Proposal
    Vote = _Vote
    _CONSENSUS_OK = True
except Exception as e:
    _CONSENSUS_ERR = str(e)

_P2P_HDR_NODE = "x-glyphchain-p2p-node-id"
_P2P_HDR_VAL = "x-glyphchain-p2p-val-id"

_NODE_ID = (os.getenv("GLYPHCHAIN_NODE_ID", "") or os.getenv("P2P_NODE_ID", "") or "dev-node").strip()
_CHAIN_ID = (os.getenv("GLYPHCHAIN_CHAIN_ID", "") or os.getenv("CHAIN_ID", "") or "glyphchain-dev").strip()
_SELF_VAL_ID = (os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()

_BASE_URL = (os.getenv("GLYPHCHAIN_BASE_URL", "") or "http://127.0.0.1:8080").strip().rstrip("/")
_SELF_PRIVKEY_HEX = (os.getenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", "") or "").strip().lower()
_SELF_PUBKEY_HEX = ""  # lazily derived


from backend.modules.consensus.validator_set import ValidatorSet  # adjust path if different
from .peer_store import get_peer_by_node_id, set_peer_identity, find_peer_by_val_id
from .crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    canonical_hello_sign_bytes,
    verify_ed25519,
)

def _self_pubkey_hex() -> str:
    global _SELF_PUBKEY_HEX
    if _SELF_PUBKEY_HEX:
        return _SELF_PUBKEY_HEX
    if not _SELF_PRIVKEY_HEX:
        return ""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        sk = bytes.fromhex(_SELF_PRIVKEY_HEX)
        pk = Ed25519PrivateKey.from_private_bytes(sk).public_key()
        _SELF_PUBKEY_HEX = pk.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
        return _SELF_PUBKEY_HEX
    except Exception:
        return ""

def _env_truthy(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in ("1", "true", "yes", "on")


def _env_is_set(name: str) -> bool:
    try:
        return name in os.environ
    except Exception:
        return False

def _has_local_p2p_identity() -> bool:
    # If we don't have a privkey, we can't sign HELLO/consensus anyway.
    return bool((_SELF_PRIVKEY_HEX or "").strip())

def _require_signed_consensus() -> bool:
    # If explicitly configured, obey env; else require only when identity exists.
    if _env_is_set("P2P_REQUIRE_SIGNED_CONSENSUS"):
        return _env_truthy("P2P_REQUIRE_SIGNED_CONSENSUS", "1")
    return _has_local_p2p_identity()

def _require_signed_for_lane(lane: str) -> bool:
    lane = (lane or "").strip().lower()

    if lane == "consensus":
        if _env_is_set("P2P_REQUIRE_SIGNED_CONSENSUS"):
            return _env_truthy("P2P_REQUIRE_SIGNED_CONSENSUS", "1")
        return _has_local_p2p_identity()

    # ✅ IMPORTANT: sync signatures remain OFF by default (tests expect engine to reject w/400, not auth 403)
    if lane == "sync":
        if _env_is_set("P2P_REQUIRE_SIGNED_SYNC"):
            return _env_truthy("P2P_REQUIRE_SIGNED_SYNC", "0")
        return False

    if lane == "block":
        if _env_is_set("P2P_REQUIRE_SIGNED_BLOCK"):
            return _env_truthy("P2P_REQUIRE_SIGNED_BLOCK", "0")
        return False

    if lane == "tx":
        if _env_is_set("P2P_REQUIRE_SIGNED_TX"):
            return _env_truthy("P2P_REQUIRE_SIGNED_TX", "0")
        return False

    if _env_is_set("P2P_REQUIRE_SIGNED_P2P"):
        return _env_truthy("P2P_REQUIRE_SIGNED_P2P", "0")
    return False

def _require_hello_for_lane(lane: str) -> bool:
    lane = (lane or "").strip().lower()

    # If explicitly configured, obey env; else require only when identity exists.
    if lane == "consensus":
        if _env_is_set("P2P_REQUIRE_HELLO_BINDING_CONSENSUS"):
            return _env_truthy("P2P_REQUIRE_HELLO_BINDING_CONSENSUS", "1")
        return _has_local_p2p_identity()

    # ✅ For restart-catchup tests (no identity), HELLO binding must not hard-block sync.
    if lane == "sync":
        if _env_is_set("P2P_REQUIRE_HELLO_BINDING_SYNC"):
            return _env_truthy("P2P_REQUIRE_HELLO_BINDING_SYNC", "1")
        return _has_local_p2p_identity()

    if lane == "block":
        if _env_is_set("P2P_REQUIRE_HELLO_BINDING_BLOCK"):
            return _env_truthy("P2P_REQUIRE_HELLO_BINDING_BLOCK", "0")
        return False

    if lane == "tx":
        if _env_is_set("P2P_REQUIRE_HELLO_BINDING_TX"):
            return _env_truthy("P2P_REQUIRE_HELLO_BINDING_TX", "0")
        return False

    if _env_is_set("P2P_REQUIRE_HELLO_BINDING"):
        return _env_truthy("P2P_REQUIRE_HELLO_BINDING", "0")
    return False

def _verify_sig_or_403(*, peer_node: str, msg_type: str, payload: Dict[str, Any]) -> None:
    sig_hex = str(payload.get("sig_hex") or "").strip().lower()
    if not sig_hex:
        raise HTTPException(status_code=403, detail=f"missing {msg_type.lower()} sig_hex")

    peer = get_peer_by_node_id(peer_node)
    pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
    if not pubkey_hex:
        raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

    try:
        msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=_CHAIN_ID, payload=payload)
        if not verify_ed25519(pubkey_hex, sig_hex, msg):
            raise HTTPException(status_code=403, detail=f"{msg_type.lower()} signature invalid")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail=f"{msg_type.lower()} signature invalid (bad sig/pubkey encoding)")


def _enforce_peer_binding(request: Request, env: P2PEnvelope, *, lane: str = "consensus") -> None:
    """
    Enforce that sender completed signed HELLO and identity matches headers/envelope.
    Lane-specific (consensus/sync strict by default; tx/block optional by default).
    """
    if not _require_hello_for_lane(lane):
        return

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()

    if not peer_node:
        raise HTTPException(status_code=400, detail="missing from_node_id")

    p = get_peer_by_node_id(peer_node)
    if p is None:
        raise HTTPException(status_code=403, detail="peer not registered (missing HELLO)")
    if getattr(p, "banned", False):
        raise HTTPException(status_code=403, detail="peer banned")
    if not bool(getattr(p, "hello_ok", False)):
        raise HTTPException(status_code=403, detail="peer not hello_ok")

    stored_val = (getattr(p, "val_id", None) or "").strip()
    if stored_val and peer_val and peer_val != stored_val:
        raise HTTPException(status_code=403, detail="val_id mismatch vs registered peer")

    if (env.from_node_id or "").strip() != peer_node:
        raise HTTPException(status_code=403, detail="from_node_id mismatch vs header")
    if stored_val and (env.from_val_id or "").strip() != stored_val:
        raise HTTPException(status_code=403, detail="from_val_id mismatch vs registered peer")

def _require_signed_p2p() -> bool:
    # simplest: reuse the same switch you already use for consensus
    return _require_signed_consensus()


def _verify_p2p_or_403(request: Request, env: P2PEnvelope, *, msg_type: str) -> tuple[str, str, str]:
    """
    Returns (peer_key, peer_node, peer_val) if ok; raises HTTPException otherwise.
    Enforces:
      - chain_id match
      - rate limit + dedup
      - peer binding (HELLO must have happened)
      - signature (if required)
    """
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env)

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        # caller should return this directly
        raise HTTPException(status_code=200, detail=json.dumps(d))  # see note below

    payload = env.payload or {}

    if _require_signed_p2p():
        sig_hex = str(payload.get("sig_hex") or "").strip().lower()
        if not sig_hex:
            raise HTTPException(status_code=403, detail=f"missing {msg_type} sig_hex")

        peer = get_peer_by_node_id(peer_node)
        pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
        if not pubkey_hex:
            raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

        msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=_CHAIN_ID, payload=payload)
        if not verify_ed25519(pubkey_hex, sig_hex, msg):
            raise HTTPException(status_code=403, detail=f"{msg_type.lower()} signature invalid")

    return peer_key, peer_node, peer_val

async def _send_hello(to_base_url: str, *, is_reply: bool = False) -> None:
    from backend.modules.p2p.crypto_ed25519 import canonical_hello_sign_bytes, sign_ed25519

    chain_id = (_CHAIN_ID or "").strip()
    node_id  = (_NODE_ID or "").strip()
    val_id   = (_SELF_VAL_ID or "").strip()
    base_url = (_BASE_URL or "").strip().rstrip("/")
    priv_hex = (_SELF_PRIVKEY_HEX or "").strip().lower()

    to_base_url = (to_base_url or "").strip().rstrip("/")
    if not to_base_url:
        return

    if not (chain_id and node_id and base_url and priv_hex):
        return

    pub_hex = _self_pubkey_hex()
    if not pub_hex:
        return

    msg = canonical_hello_sign_bytes(
        chain_id=chain_id,
        node_id=node_id,
        val_id=(val_id or None),
        base_url=base_url,
        pubkey_hex=pub_hex,
    )
    sig_hex = sign_ed25519(priv_hex, msg)

    env = {
        "type": "HELLO",
        "from_node_id": node_id,
        "from_val_id": val_id,
        "chain_id": chain_id,
        "ts_ms": float(time.time() * 1000.0),
        "payload": {
            "base_url": base_url,
            "val_id": val_id,
            "role": "peer",
            "pubkey_hex": pub_hex,
            "sig_hex": sig_hex,
            "is_reply": bool(is_reply),
        },
        "hops": 0,
    }

    headers = {
        _P2P_HDR_NODE: node_id,
        _P2P_HDR_VAL: val_id,
        "x-glyphchain-p2p-chain-id": chain_id,
    }

    url = to_base_url + "/api/p2p/hello"

    attempts = int(os.getenv("P2P_HELLO_ATTEMPTS", "12") or 12)
    base_s   = float(os.getenv("P2P_HELLO_RETRY_BASE_S", "0.15") or 0.15)
    cap_s    = float(os.getenv("P2P_HELLO_RETRY_CAP_S", "1.25") or 1.25)

    for i in range(max(1, attempts)):
        try:
            async with httpx.AsyncClient(timeout=4.0) as c:
                await c.post(url, json=env, headers=headers)
            return
        except Exception:
            if i >= attempts - 1:
                return
            # exponential backoff + tiny jitter
            sleep_s = min(cap_s, base_s * (2 ** i)) + (random.random() * 0.05)
            await asyncio.sleep(sleep_s)

def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _local_base_url() -> str:
    return (os.getenv("GLYPHCHAIN_BASE_URL", "") or "http://127.0.0.1:8080").strip().rstrip("/")


def _approx_bytes(obj: Any) -> int:
    try:
        return len(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    except Exception:
        return 0


def _rl_or_429(peer_key: str, payload_bytes: int) -> None:
    msg_rate = float(os.getenv("P2P_RL_MSG_PER_SEC", "50") or 50)
    msg_burst = float(os.getenv("P2P_RL_MSG_BURST", "100") or 100)
    byt_rate = float(os.getenv("P2P_RL_BYTES_PER_SEC", "512000") or 512000)  # 512KB/s
    byt_burst = float(os.getenv("P2P_RL_BYTES_BURST", "1048576") or 1048576)  # 1MB burst

    if not rl_allow(
        peer_key,
        cost_msgs=1.0,
        cost_bytes=float(payload_bytes),
        msg_rate_per_sec=msg_rate,
        msg_burst=msg_burst,
        bytes_rate_per_sec=byt_rate,
        bytes_burst=byt_burst,
    ):
        raise HTTPException(status_code=429, detail=f"rate limited (peer={peer_key})")


import base64
from backend.modules.p2p.peer_store import get_peer_by_node_id, set_peer_identity
from backend.modules.consensus.validator_set import ValidatorSet  # adjust import path if needed



def _parse_bytes_maybe_hex_or_b64(s: str) -> bytes:
    x = (s or "").strip()
    if not x:
        return b""
    # hex?
    try:
        return bytes.fromhex(x)
    except Exception:
        pass
    # base64 (standard / urlsafe)
    try:
        return base64.b64decode(x + "===")
    except Exception:
        try:
            return base64.urlsafe_b64decode(x + "===")
        except Exception:
            return b""

def _verify_ed25519(pubkey_bytes: bytes, sig_bytes: bytes, msg: bytes) -> bool:
    if not pubkey_bytes or not sig_bytes:
        return False
    # try cryptography first
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(pubkey_bytes).verify(sig_bytes, msg)
        return True
    except Exception:
        pass
    # then pynacl
    try:
        from nacl.signing import VerifyKey
        VerifyKey(pubkey_bytes).verify(msg, sig_bytes)
        return True
    except Exception:
        return False

def _hello_sign_bytes(chain_id: str, from_node_id: str, payload: Dict[str, Any]) -> bytes:
    """
    Canonical sign-bytes for HELLO. Must be stable across nodes.
    IMPORTANT: exclude 'sig' from payload.
    """
    p = dict(payload or {})
    p.pop("sig", None)
    obj = {
        "type": "HELLO",
        "chain_id": str(chain_id or ""),
        "from_node_id": str(from_node_id or ""),
        "payload": p,
    }
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return raw

# -----------------------------------------------------------------------------
# PR4.3: bounded TTL+LRU replay protection
# PR4.3b: response cache for request-like lanes (STATUS, SYNC_REQ)
# -----------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return default


def _stable_hash(obj: Any) -> str:
    try:
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        raw = repr(obj).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _msg_key(peer_key: str, env: P2PEnvelope) -> str:
    """
    Single source of truth for "same message" semantics.
    Dedup + response cache MUST use this 1:1.
    Prefer payload.msg_id when present; otherwise hash payload.
    """
    msg_id = None
    try:
        if isinstance(env.payload, dict):
            msg_id = env.payload.get("msg_id")
    except Exception:
        msg_id = None

    if isinstance(msg_id, str) and msg_id:
        return "|".join(
            [
                str(peer_key or ""),
                str(env.chain_id or ""),
                str(env.type or ""),
                "msg",
                msg_id,
            ]
        )

    return "|".join(
        [
            str(peer_key or ""),
            str(env.from_node_id or ""),
            str(env.chain_id or ""),
            str(env.type or ""),
            _stable_hash(env.payload or {}),
        ]
    )


class _TtlLruDedup:
    def __init__(self, *, max_items: int, ttl_ms: int) -> None:
        self.max_items = int(max_items)
        self.ttl_ms = int(ttl_ms)
        self._lock = Lock()
        self._m: "OrderedDict[str, float]" = OrderedDict()  # key -> last_seen_ms

    def seen(self, key: str) -> bool:
        if self.ttl_ms <= 0 or self.max_items <= 0:
            return False

        now = _now_ms()
        with self._lock:
            ts = self._m.get(key)
            if ts is not None:
                if (now - float(ts)) <= float(self.ttl_ms):
                    # still within TTL => duplicate
                    try:
                        self._m.move_to_end(key, last=True)
                    except Exception:
                        pass
                    return True
                # expired => treat as new, overwrite
                try:
                    self._m.pop(key, None)
                except Exception:
                    pass

            # record new
            self._m[key] = now
            try:
                self._m.move_to_end(key, last=True)
            except Exception:
                pass

            # enforce bound (LRU)
            while len(self._m) > int(self.max_items):
                try:
                    self._m.popitem(last=False)
                except Exception:
                    break

        return False


_DEDUP_TTL_MS = _env_int("P2P_DEDUP_TTL_MS", 15000)  # 15s
_DEDUP_MAX = _env_int("P2P_DEDUP_MAX", 20000)
_DEDUP = _TtlLruDedup(max_items=_DEDUP_MAX, ttl_ms=_DEDUP_TTL_MS)


def _drop_if_dup(peer_key: str, env: P2PEnvelope) -> Optional[Dict[str, Any]]:
    # Request-like lanes must NEVER return the dedup placeholder.
    # They either serve from resp-cache or compute a fresh response.
    t = (env.type or "").strip().upper()
    if t in ("STATUS", "SYNC_REQ", "BLOCK_REQ"):
        return None

    try:
        if _DEDUP.seen(_msg_key(peer_key, env)):
            return {"ok": True, "dedup": True, "applied": False}
    except Exception:
        pass
    return None

# PR4.3b response cache (STATUS, SYNC_REQ)
_P2P_RESP_CACHE_TTL_MS = _env_int("P2P_RESP_CACHE_TTL_MS", 1500)
_P2P_RESP_CACHE_MAX = _env_int("P2P_RESP_CACHE_MAX", 2048)

_RESP_LOCK = Lock()
_RESP_CACHE: "OrderedDict[str, tuple[float, Dict[str, Any]]]" = OrderedDict()  # key -> (ts_ms, resp)


def _resp_cache_get(peer_key: str, env: P2PEnvelope) -> Optional[Dict[str, Any]]:
    ttl_ms = int(_P2P_RESP_CACHE_TTL_MS)
    max_n = int(_P2P_RESP_CACHE_MAX)

    # TTL=0 or MAX=0 disables response cache entirely
    if ttl_ms <= 0 or max_n <= 0:
        return None

    k = _msg_key(peer_key, env)
    now = _now_ms()

    with _RESP_LOCK:
        it = _RESP_CACHE.get(k)
        if not it:
            return None

        ts_ms, resp = it
        if (now - float(ts_ms)) > float(ttl_ms):
            try:
                _RESP_CACHE.pop(k, None)
            except Exception:
                pass
            return None

        # refresh LRU
        try:
            _RESP_CACHE.move_to_end(k, last=True)
        except Exception:
            pass

        # copy so handlers can safely mutate flags (dedup/cached) without corrupting cache
        return dict(resp) if isinstance(resp, dict) else None


def _resp_cache_set(peer_key: str, env: P2PEnvelope, resp: Dict[str, Any]) -> None:
    ttl_ms = int(_P2P_RESP_CACHE_TTL_MS)
    max_n = int(_P2P_RESP_CACHE_MAX)

    # TTL=0 or MAX=0 disables response cache entirely
    if ttl_ms <= 0 or max_n <= 0:
        return
    if not isinstance(resp, dict):
        return

    k = _msg_key(peer_key, env)
    now = _now_ms()

    with _RESP_LOCK:
        _RESP_CACHE[k] = (now, dict(resp))
        try:
            _RESP_CACHE.move_to_end(k, last=True)
        except Exception:
            pass

        # enforce max size (LRU eviction)
        while len(_RESP_CACHE) > max_n:
            try:
                _RESP_CACHE.popitem(last=False)
            except Exception:
                break

@router.on_event("startup")
async def _p2p_bootstrap_hello() -> None:
    try:
        load_peers_from_env()
    except Exception:
        return

    async def _run() -> None:
        try:
            delay_s = float(os.getenv("P2P_BOOTSTRAP_HELLO_DELAY_S", "0") or 0.0)
            if delay_s > 0:
                await asyncio.sleep(delay_s)

            for p in list_peers():
                try:
                    if (p.node_id or "").strip() == (_NODE_ID or "").strip():
                        continue
                    base = (p.base_url or "").strip().rstrip("/")
                    if not base:
                        continue
                    if base == (_BASE_URL or "").strip().rstrip("/"):
                        continue
                    await _send_hello(base, is_reply=False)
                except Exception:
                    continue
        except Exception:
            return

    # ✅ do NOT block FastAPI startup
    asyncio.create_task(_run())
# -----------------------------------------------------------------------------
# routes
# -----------------------------------------------------------------------------

@router.get("/peers")
async def p2p_peers() -> Dict[str, Any]:
    load_peers_from_env()
    return {
        "ok": True,
        "node_id": _NODE_ID,
        "chain_id": _CHAIN_ID,
        "peers": [p.model_dump() for p in list_peers()],
    }


@router.post("/connect")
async def p2p_connect(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    load_peers_from_env()
    base_url = str(body.get("base_url") or body.get("url") or "").strip()
    node_id = str(body.get("node_id") or "").strip()
    val_id = body.get("val_id")
    role = str(body.get("role") or "peer")
    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and node_id required")

    p = add_peer(
        base_url=base_url,
        node_id=node_id,
        val_id=(str(val_id) if val_id is not None else None),
        role=role,
    )

    # ✅ NEW: on connect, initiate HELLO so we can accept SYNC_RESP from them.
    if base_url and base_url.rstrip("/") != _BASE_URL.rstrip("/"):
        asyncio.create_task(_send_hello(base_url, is_reply=False))

    return {"ok": True, "added": True, "peer": p.model_dump()}


@router.post("/hello")
async def p2p_hello(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "HELLO":
        raise HTTPException(status_code=400, detail="expected type=HELLO")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    base_url = str((env.base_url or payload.get("base_url") or "")).strip().rstrip("/")
    node_id = str(env.from_node_id or "").strip()
    val_id = (env.from_val_id or payload.get("val_id") or None)
    role = str((env.role or payload.get("role") or "peer"))

    pubkey_hex = str(payload.get("pubkey_hex") or "").strip().lower()
    sig_hex = str(payload.get("sig_hex") or "").strip().lower()
    is_reply = bool(payload.get("is_reply"))

    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and from_node_id required")
    if not pubkey_hex or not sig_hex:
        raise HTTPException(status_code=400, detail="payload.pubkey_hex and payload.sig_hex required")

    msg = canonical_hello_sign_bytes(
        chain_id=_CHAIN_ID,
        node_id=node_id,
        val_id=(str(val_id).strip() if val_id is not None else None),
        base_url=base_url,
        pubkey_hex=pubkey_hex,
    )
    if not verify_ed25519(pubkey_hex, sig_hex, msg):
        raise HTTPException(status_code=403, detail="HELLO signature invalid")

    load_peers_from_env()
    p = add_peer(
        base_url=base_url,
        node_id=node_id,
        val_id=(str(val_id).strip() if val_id is not None else None),
        role=role,
    )

    set_peer_identity(
        node_id=node_id,
        base_url=base_url,
        val_id=(str(val_id).strip() if val_id is not None else None),
        pubkey_hex=pubkey_hex,
        hello_ok=True,
    )

    # **CRITICAL**: reply once so both sides become hello_ok (restart-safe)
    if (not is_reply) and base_url and base_url.rstrip("/") != (_BASE_URL or "").strip().rstrip("/"):
        asyncio.create_task(_send_hello(base_url, is_reply=True))

    return {
        "ok": True,
        "added": True,
        "peer": p.model_dump(),
        "peers": [x.model_dump() for x in list_peers()],
    }


@router.post("/refresh")
async def p2p_refresh(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    load_peers_from_env()
    target = str(body.get("base_url") or body.get("url") or "").strip().rstrip("/")
    if not target:
        raise HTTPException(status_code=400, detail="base_url required")

    upstream = await get_json(target, "/api/p2p/peers", timeout_s=8.0)
    j = upstream.get("json") or {}
    if not isinstance(j, dict) or not j.get("ok"):
        raise HTTPException(status_code=502, detail=f"upstream peers fetch failed: {upstream}")

    merged = 0
    for pj in (j.get("peers") or []):
        if not isinstance(pj, dict):
            continue
        base_url = str(pj.get("base_url") or "").strip()
        node_id = str(pj.get("node_id") or "").strip()
        if not base_url or not node_id:
            continue

        add_peer(
            base_url=base_url,
            node_id=node_id,
            val_id=(str(pj.get("val_id")) if pj.get("val_id") is not None else None),
            role=str(pj.get("role") or "peer"),
        )
        merged += 1

        # ✅ NEW: proactively HELLO newly learned peers so we can accept SYNC_RESP, etc.
        if base_url and base_url.rstrip("/") != _BASE_URL.rstrip("/"):
            asyncio.create_task(_send_hello(base_url, is_reply=False))

    return {"ok": True, "merged": merged, "peers": [p.model_dump() for p in list_peers()]}


@router.post("/tx_relay")
async def p2p_tx_relay(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "TX_RELAY":
        raise HTTPException(status_code=400, detail="expected type=TX_RELAY")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="tx")

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    tx = env.payload.get("tx") or env.payload.get("body") or {}
    if not isinstance(tx, dict):
        raise HTTPException(status_code=400, detail="payload.tx must be object")

    local_base = _local_base_url()
    upstream = await post_json(
        local_base,
        "/api/chain_sim/dev/submit_tx_async",
        tx,
        timeout_s=8.0,
        add_p2p_headers=True,
        p2p_from_node_id=(peer_node or env.from_node_id or "unknown"),
        p2p_from_val_id=(peer_val or _SELF_VAL_ID or ""),
        p2p_chain_id=_CHAIN_ID,
    )

    up_json = upstream.get("json")
    if isinstance(up_json, dict):
        out = dict(up_json)
        out["via_p2p"] = True
        out["p2p_from_node_id"] = env.from_node_id
        out["p2p_hops"] = env.hops
        return out

    return {"ok": True, "via_p2p": True, "upstream": upstream}


@router.post("/relay_tx")
async def p2p_relay_tx(request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    tx = body.get("tx") or body.get("body") or body
    if not isinstance(tx, dict):
        raise HTTPException(status_code=400, detail="tx must be object")

    env = P2PEnvelope(
        type="TX_RELAY",
        from_node_id=_NODE_ID,
        chain_id=_CHAIN_ID,
        ts_ms=float(body.get("ts_ms") or 0) or 0.0,
        payload={"tx": tx},
        hops=int(body.get("hops") or 0),
    )
    return await p2p_tx_relay(request, env)


# -------------------------
# Block announce + fetch
# -------------------------

@router.post("/block_announce")
async def p2p_block_announce(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "BLOCK_ANNOUNCE":
        raise HTTPException(status_code=400, detail="expected type=BLOCK_ANNOUNCE")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="block")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    # message-like lane: verify signature first (if required), then allow dedup-placeholder
    if _require_signed_for_lane("block"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="BLOCK_ANNOUNCE", payload=payload)

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    h = int(payload.get("height") or 0)
    if h <= 0:
        raise HTTPException(status_code=400, detail="payload.height required")

    return {"ok": True, "announced": True, "height": h}


@router.post("/block_req")
async def p2p_block_req(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "BLOCK_REQ":
        raise HTTPException(status_code=400, detail="expected type=BLOCK_REQ")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="block")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    if _require_signed_for_lane("block"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="BLOCK_REQ", payload=payload)

    h = int(payload.get("height") or 0)
    want = str(payload.get("want") or "block").strip().lower()
    if h <= 0:
        raise HTTPException(status_code=400, detail="payload.height required")
    if want not in ("block", "header"):
        raise HTTPException(status_code=400, detail='payload.want must be "block" or "header"')

    # -------------------------
    # block lookup helpers
    # -------------------------
    def _blk_height(v: Any) -> Optional[int]:
        try:
            if isinstance(v, dict):
                if v.get("height") is not None:
                    return int(v.get("height") or 0) or None
                hdr = v.get("header") or (v.get("block") or {}).get("header") or {}
                if isinstance(hdr, dict) and hdr.get("height") is not None:
                    return int(hdr.get("height") or 0) or None
        except Exception:
            pass
        return None

    def _find_by_height_in_store(store: Any, height: int) -> Any:
        if store is None:
            return None

        if isinstance(store, dict):
            # direct keyed by int/str height
            try:
                v = store.get(height)
                if v:
                    return v
            except Exception:
                pass
            try:
                v = store.get(str(height))
                if v:
                    return v
            except Exception:
                pass

            # keyed by block_id like "h276-r0-PvalX"
            pref = f"h{height}-"
            try:
                for k, v in store.items():
                    if isinstance(k, str) and k.startswith(pref) and v:
                        return v
            except Exception:
                pass

            # scan values for matching header.height
            try:
                for v in store.values():
                    if _blk_height(v) == height:
                        return v
            except Exception:
                pass

            # common nested dicts
            for nk in ("by_height", "blocks_by_height", "_by_height", "_blocks_by_height"):
                try:
                    sub = store.get(nk)
                    v = _find_by_height_in_store(sub, height)
                    if v:
                        return v
                except Exception:
                    pass

            return None

        if isinstance(store, list):
            try:
                for v in store:
                    if _blk_height(v) == height:
                        return v
            except Exception:
                pass
            return None

        # mapping-ish .get
        try:
            v = store.get(height)  # type: ignore[attr-defined]
            if v:
                return v
        except Exception:
            pass

        return None

    def _deep_search(obj: Any, height: int, *, depth: int, seen: set[int]) -> Any:
        if obj is None or depth < 0:
            return None
        oid = id(obj)
        if oid in seen:
            return None
        seen.add(oid)

        # direct store hit
        hit = _find_by_height_in_store(obj, height)
        if hit:
            return hit

        # dict recurse
        if isinstance(obj, dict):
            try:
                for v in obj.values():
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
            except Exception:
                return None
            return None

        # list recurse
        if isinstance(obj, list):
            try:
                for v in obj:
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
            except Exception:
                return None
            return None

        # object attrs recurse (best-effort; avoid huge/side-effect-y stuff)
        try:
            for name in dir(obj):
                if not name or name.startswith("__"):
                    continue
                if name in ("logger", "log", "app", "router", "client", "http", "session"):
                    continue
                try:
                    v = getattr(obj, name)
                except Exception:
                    continue
                if callable(v):
                    continue
                # only follow plausible containers
                if isinstance(v, (dict, list)) or ("block" in name.lower()) or ("store" in name.lower()):
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
        except Exception:
            return None

        return None

    blk: Any = None

    # -------------------------
    # 1) consensus engine (deep)
    # -------------------------
    try:
        if _CONSENSUS_OK and get_engine is not None:
            eng = get_engine()

            # common method names first
            for name in (
                "get_block_by_height",
                "block_by_height",
                "get_committed_block_by_height",
                "get_committed_block",
                "get_block",
            ):
                fn = getattr(eng, name, None)
                if callable(fn):
                    try:
                        blk = fn(h)
                        if blk:
                            break
                    except Exception:
                        pass

            # deep search engine object graph (covers nested stores)
            if not blk:
                blk = _deep_search(eng, h, depth=3, seen=set())
    except Exception:
        blk = None

    # -------------------------
    # 2) chain_sim ledger fallback
    # -------------------------
    if not blk:
        try:
            blk = get_block(h)
        except Exception:
            blk = None

    if not blk:
        try:
            from backend.modules.chain_sim.chain_sim_ledger import replay_ledger_only_from_db
            replay_ledger_only_from_db()
        except Exception:
            try:
                from backend.modules.chain_sim.chain_sim_ledger import replay_state_from_db
                replay_state_from_db()
            except Exception:
                pass
        try:
            blk = get_block(h)
        except Exception:
            blk = None

    if blk:
        if want == "header":
            if isinstance(blk, dict):
                header = blk.get("header") or (blk.get("block") or {}).get("header") or {}
            else:
                header = {}
            return {"ok": True, "height": h, "header": header}
        return {"ok": True, "height": h, "block": blk}

    # -------------------------
    # proxy-on-miss
    # -------------------------
    max_hops = _env_int("P2P_BLOCK_PROXY_MAX_HOPS", 2)
    cur_hops = int(getattr(env, "hops", 0) or 0)
    if cur_hops >= max_hops:
        raise HTTPException(status_code=404, detail=f"block not found (height={h})")

    try:
        load_peers_from_env()
        local = _local_base_url()
        peers: list[str] = []
        for p in list_peers():
            base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
            if not base or base == local:
                continue
            peers.append(base)

        random.shuffle(peers)

        fwd = env.model_dump()
        fwd["from_node_id"] = _NODE_ID
        fwd["from_val_id"] = _SELF_VAL_ID or None
        fwd["ts_ms"] = _now_ms()
        fwd["hops"] = cur_hops + 1

        for base in peers:
            try:
                upstream = await post_json(
                    base,
                    "/api/p2p/block_req",
                    fwd,
                    timeout_s=10.0,
                    add_p2p_headers=True,
                    p2p_from_node_id=_NODE_ID,
                    p2p_from_val_id=_SELF_VAL_ID,
                    p2p_chain_id=_CHAIN_ID,
                )
                if int(upstream.get("status") or 0) != 200:
                    continue
                j = upstream.get("json")
                if isinstance(j, dict) and j.get("ok") is True:
                    out = dict(j)
                    out["proxied"] = True
                    out["proxy_from"] = base
                    return out
            except Exception:
                continue
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"block not found (height={h})")

# -------------------------
# Consensus messages (PR1)
# -------------------------

@router.get("/consensus_status")
async def p2p_consensus_status() -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")
    eng = get_engine()
    return eng.status()


# add near the top of router.py with other imports
from backend.modules.consensus.validator_set import ValidatorSet  # (or wherever validate_set.py lives)
# e.g. if file is backend/modules/consensus/validate_set.py:
# from backend.modules.consensus.validate_set import ValidatorSet


@router.post("/proposal")
async def p2p_proposal(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None or Proposal is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")

    if env.type != "PROPOSAL":
        raise HTTPException(status_code=400, detail="expected type=PROPOSAL")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env)

    vset = ValidatorSet.from_env()
    if not vset.is_member(peer_val or env.from_val_id or ""):
        raise HTTPException(status_code=403, detail="from_val_id not in ValidatorSet")

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    payload = env.payload or {}
    if _require_signed_consensus():
        sig_hex = str(payload.get("sig_hex") or "").strip().lower()
        if not sig_hex:
            raise HTTPException(status_code=403, detail="missing proposal sig_hex")

        peer = get_peer_by_node_id(peer_node)
        pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
        if not pubkey_hex:
            raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

        try:
            msg = canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=_CHAIN_ID, payload=payload)
            if not verify_ed25519(pubkey_hex, sig_hex, msg):
                raise HTTPException(status_code=403, detail="proposal signature invalid")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=403,
                detail="proposal signature invalid (bad sig/pubkey encoding)",
            )

    try:
        p = Proposal(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad proposal payload: {e}")

    eng = get_engine()
    try:
        out = eng.handle_proposal(p)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"proposal handler exception: {type(e).__name__}: {e}")

    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=str(out.get("error") or "proposal rejected"))
    return out


@router.post("/vote")
async def p2p_vote(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None or Vote is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")

    if env.type != "VOTE":
        raise HTTPException(status_code=400, detail="expected type=VOTE")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env)

    vset = ValidatorSet.from_env()
    if not vset.is_member(peer_val or env.from_val_id or ""):
        raise HTTPException(status_code=403, detail="from_val_id not in ValidatorSet")

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    payload = env.payload or {}
    if _require_signed_consensus():
        sig_hex = str(payload.get("sig_hex") or "").strip().lower()
        if not sig_hex:
            raise HTTPException(status_code=403, detail="missing vote sig_hex")

        peer = get_peer_by_node_id(peer_node)
        pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
        if not pubkey_hex:
            raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

        try:
            msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=_CHAIN_ID, payload=payload)
            if not verify_ed25519(pubkey_hex, sig_hex, msg):
                raise HTTPException(status_code=403, detail="vote signature invalid")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=403, detail="vote signature invalid (bad sig/pubkey encoding)")

    try:
        v = Vote(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad vote payload: {e}")

    eng = get_engine()
    try:
        out = eng.handle_vote(v)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"vote handler exception: {type(e).__name__}: {e}")

    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=str(out.get("error") or "vote rejected"))
    return out


# -------------------------
# PR4: STATUS / SYNC lanes
# -------------------------

@router.post("/status")
async def p2p_status(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")

    if env.type != "STATUS":
        raise HTTPException(status_code=400, detail="expected type=STATUS")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()

    # ✅ allow self-calls (tests do _p2p_status(a, a))
    if peer_node and peer_node == (_NODE_ID or ""):
        eng = get_engine()
        st = eng.status()
        return {
            "ok": True,
            "payload": {
                "node_id": st.get("node_id"),
                "finalized_height": int(st.get("finalized_height") or 0),
                "height": int(st.get("height") or st.get("next_height") or 0),
                "round": int(st.get("round") or 0),
                "last_qc": st.get("last_qc"),
            },
            "self": True,
        }

    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="sync")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    if _require_signed_for_lane("sync"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="STATUS", payload=payload)

    cached = _resp_cache_get(peer_key, env)
    if cached is not None:
        cached["dedup"] = True
        cached["cached"] = True
        return cached

    eng = get_engine()
    st = eng.status()

    resp = {
        "ok": True,
        "payload": {
            "node_id": st.get("node_id"),
            "finalized_height": int(st.get("finalized_height") or 0),
            "height": int(st.get("height") or st.get("next_height") or 0),
            "round": int(st.get("round") or 0),
            "last_qc": st.get("last_qc"),
        },
    }
    _resp_cache_set(peer_key, env, resp)
    return resp


@router.post("/sync_req")
async def p2p_sync_req(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")

    if env.type != "SYNC_REQ":
        raise HTTPException(status_code=400, detail="expected type=SYNC_REQ")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="sync")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    # ✅ request-like lane: verify signature (optional by env) BEFORE cache
    if _require_signed_for_lane("sync"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="SYNC_REQ", payload=payload)

    # PR4.3b: return identical cached response for duplicate request-like messages
    cached = _resp_cache_get(peer_key, env)
    if cached is not None:
        cached["dedup"] = True
        cached["cached"] = True
        return cached

    # IMPORTANT: do NOT _drop_if_dup() on SYNC_REQ (request-like). If cache miss, compute fresh.

    eng = get_engine()
    st = eng.status()

    resp = {
        "ok": True,
        "payload": {
            "node_id": st.get("node_id"),
            "finalized_height": int(st.get("finalized_height") or 0),
            "height": int(st.get("height") or st.get("next_height") or 0),
            "round": int(st.get("round") or 0),
            "last_qc": st.get("last_qc"),
        },
    }
    _resp_cache_set(peer_key, env, resp)
    return resp


@router.post("/sync_resp")
async def p2p_sync_resp(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")

    if env.type != "SYNC_RESP":
        raise HTTPException(status_code=400, detail="expected type=SYNC_RESP")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="sync")

    payload = env.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    # ✅ message-like lane: optional signature verify (by env) + dedup placeholder
    if _require_signed_for_lane("sync"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="SYNC_RESP", payload=payload)

    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    out = get_engine().handle_sync_resp(payload)
    if not isinstance(out, dict) or out.get("ok") is not True:
        raise HTTPException(status_code=400, detail=str((out or {}).get("error") or "bad sync_resp"))

    return {"ok": True, "applied": out}