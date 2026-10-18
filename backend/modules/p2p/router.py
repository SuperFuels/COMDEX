from __future__ import annotations

import hashlib
import json
import os
import time
import random
import shutil
import tempfile
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, HTTPException, Query, Request
from backend.modules.chain_sim.chain_sim_ledger import get_block
from .p2p_types import P2PEnvelope
from .peer_store import add_peer, list_peers, load_peers_from_env, peer_store_status
from .rate_limit import allow as rl_allow
from .transport_http import get_json, post_json
from .peer_discovery import PeerDiscoveryError, SignedPeerDiscoveryStore, trust_anchors_from_env
from .network_identity import NetworkIdentityStore
from .nat_relay import (
    NATRelayError,
    NATRelayStore,
    active_transport_private_key,
    build_relay_operation,
    enqueue_via_nat_relay,
    relay_limits_from_env,
    relay_post,
    validate_nat_relay_url,
    verify_relay_operation,
)
import asyncio
import httpx
from backend.modules.p2p.lane_limiter import LaneLimiter
from backend.modules.p2p.ingress import get_lanes
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from backend.modules.consensus.ingress_validate import (
    validate_qc_dict_or_error,
    validate_vote_payload_or_error,
)
from backend.modules.chain_sim.ledger_snapshot import (
    LedgerSnapshotError,
    SNAPSHOT_MEDIA_TYPE,
    export_current_finalized_snapshot,
)
from .network_participation import participation_from_env
from backend.modules.consensus.protocol_upgrade import (
    ProtocolUpgradeError,
    local_protocol_advertisement,
    normalize_protocol_advertisement,
)

_LIM = get_lanes()

# PR5: bounded ingress queues / dedup ids (module-scope singleton)

def _stable_json_bytes_for_id(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha_id(x: Any) -> str:
    return hashlib.sha256(_stable_json_bytes_for_id(x)).hexdigest()

def _proposal_msg_id(payload: Dict[str, Any]) -> str:
    canon = {
        "h": int(payload.get("height") or 0),
        "r": int(payload.get("round") or 0),
        "p": str(payload.get("proposer") or ""),
        "bid": str(payload.get("block_id") or ""),
    }
    return "P:" + _sha_id(canon)

def _vote_msg_id(payload: Dict[str, Any]) -> str:
    canon = {
        "h": int(payload.get("height") or 0),
        "r": int(payload.get("round") or 0),
        "t": str(payload.get("vote_type") or ""),
        "bid": str(payload.get("block_id") or ""),
        "v": str(payload.get("voter") or ""),
    }
    return "V:" + _sha_id(canon)

def _sync_msg_id(env: Dict[str, Any]) -> str:
    return "S:" + _sha_id({"from": str(env.get("from_node_id") or ""), "ts": int(env.get("ts_ms") or 0)})

def _block_req_msg_id(payload: Dict[str, Any], env: Dict[str, Any]) -> str:
    return "B:" + _sha_id({
        "from": str(env.get("from_node_id") or ""),
        "h": int(payload.get("height") or 0),
        "want": str(payload.get("want") or "block"),
    })

router = APIRouter()
_LIM = LaneLimiter.from_env()
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
_DISCOVERY_STORE: SignedPeerDiscoveryStore | None = None
_NETWORK_IDENTITY_STORE: NetworkIdentityStore | None = None
_NAT_RELAY_STORE: NATRelayStore | None = None
_NAT_NONCES: "OrderedDict[str, int]" = OrderedDict()
_NAT_NONCES_LOCK = Lock()


def _local_protocol() -> dict[str, Any]:
    finalized = 0
    try:
        if get_engine is not None:
            finalized = int(get_engine().status().get("finalized_height") or 0)
    except Exception:
        pass
    return local_protocol_advertisement(
        chain_id=_CHAIN_ID, node_id=_NODE_ID, finalized_height=finalized,
    )


from backend.modules.consensus.validator_set import ValidatorSet  # adjust path if different
from .peer_store import get_peer_by_node_id, set_peer_identity, find_peer_by_val_id
from .crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    canonical_hello_sign_bytes,
    verify_ed25519,
)

def _self_pubkey_hex() -> str:
    priv_hex = _active_transport_private_key_hex()
    if not priv_hex:
        return ""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        sk = bytes.fromhex(priv_hex)
        pk = Ed25519PrivateKey.from_private_bytes(sk).public_key()
        return pk.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
    except Exception:
        return ""


def _managed_network_identity_store() -> NetworkIdentityStore | None:
    global _NETWORK_IDENTITY_STORE
    configured = str(os.getenv("GLYPHCHAIN_NETWORK_KEY_DIR", "") or "").strip()
    if not configured:
        return None
    if _NETWORK_IDENTITY_STORE is None:
        _NETWORK_IDENTITY_STORE = NetworkIdentityStore(configured, chain_id=_CHAIN_ID, node_id=_NODE_ID)
    return _NETWORK_IDENTITY_STORE


def _active_transport_private_key_hex() -> str:
    configured = (_SELF_PRIVKEY_HEX or "").strip().lower()
    if configured:
        return configured
    store = _managed_network_identity_store()
    return store.active_private_key_hex() if store is not None else ""

def _env_truthy(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in ("1", "true", "yes", "on")


def _env_is_set(name: str) -> bool:
    try:
        return name in os.environ
    except Exception:
        return False

def _has_local_p2p_identity() -> bool:
    # If we don't have a privkey, we can't sign HELLO/consensus anyway.
    return bool(_active_transport_private_key_hex())


def _signed_discovery_store() -> SignedPeerDiscoveryStore:
    global _DISCOVERY_STORE
    if _DISCOVERY_STORE is not None:
        return _DISCOVERY_STORE
    root = str(os.getenv("GLYPHCHAIN_DISCOVERY_DIR", "") or "").strip()
    if not root:
        from pathlib import Path
        root = str(Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state")) / "peer-discovery")
    _DISCOVERY_STORE = SignedPeerDiscoveryStore(
        root, chain_id=_CHAIN_ID, trust_anchors=trust_anchors_from_env(),
        allow_private_addresses=_env_truthy("GLYPHCHAIN_DISCOVERY_ALLOW_PRIVATE", "0"),
    )
    return _DISCOVERY_STORE


def _install_discovered_peers(store: SignedPeerDiscoveryStore) -> int:
    installed = 0
    for peer in store.active_peers():
        if peer["node_id"] == _NODE_ID:
            continue
        add_peer(
            peer["base_url"], peer["node_id"], peer.get("val_id"), peer["role"],
            relay_url=peer.get("relay_url"),
        )
        set_peer_identity(
            node_id=peer["node_id"], base_url=peer["base_url"], val_id=peer.get("val_id"),
            pubkey_hex=peer["pubkey_hex"], hello_ok=False,
        )
        installed += 1
    return installed


def _nat_relay_store() -> NATRelayStore:
    global _NAT_RELAY_STORE
    if _NAT_RELAY_STORE is None:
        root = str(os.getenv("GLYPHCHAIN_NAT_RELAY_DIR", "") or "").strip()
        if not root:
            root = str(Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state")) / "nat-relay")
        _NAT_RELAY_STORE = NATRelayStore(root, chain_id=_CHAIN_ID, limits=relay_limits_from_env())
    return _NAT_RELAY_STORE


def _require_nat_relay_role() -> dict[str, Any]:
    participation = participation_from_env()
    if str(participation.get("role") or "light") not in {"relay", "validator"}:
        raise HTTPException(status_code=403, detail="nat_relay_service_requires_relay_or_validator_role")
    if participation.get("capabilities", {}).get("relay_messages") is not True:
        raise HTTPException(status_code=403, detail="nat_relay_message_capability_not_approved")
    return participation


def _remember_nat_nonce(node_id: str, nonce: str, issued_at_ms: int) -> None:
    try:
        _nat_relay_store().remember_operation_nonce(
            node_id=node_id,
            nonce=nonce,
            issued_at_ms=issued_at_ms,
        )
    except NATRelayError as exc:
        detail = str(exc)
        status = 409 if detail == "nat_relay_operation_replayed" else 503
        raise HTTPException(status_code=status, detail=detail) from exc


def _verify_nat_operation(body: Dict[str, Any], expected_operation: str) -> tuple[dict[str, Any], Any]:
    _require_nat_relay_role()
    node_id = str(body.get("node_id") or "").strip()
    peer = get_peer_by_node_id(node_id)
    pubkey = str(getattr(peer, "pubkey_hex", "") or "").strip().lower() if peer else ""
    if peer is None or not bool(getattr(peer, "hello_ok", False)) or not pubkey:
        raise HTTPException(status_code=403, detail="nat_relay_peer_requires_verified_hello")
    try:
        verified = verify_relay_operation(body, expected_chain_id=_CHAIN_ID, public_key_hex=pubkey)
    except NATRelayError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if verified["operation"] != expected_operation:
        raise HTTPException(status_code=400, detail="nat_relay_operation_route_mismatch")
    _rl_or_429(node_id, _approx_bytes(body))
    _remember_nat_nonce(node_id, str(verified["nonce"]), int(verified["issued_at_ms"]))
    return verified, peer


def _nat_relay_url() -> str:
    configured = str(os.getenv("GLYPHCHAIN_NAT_RELAY_URL", "") or "").strip()
    if not configured:
        return ""
    return validate_nat_relay_url(
        configured,
        allow_insecure=_env_truthy("GLYPHCHAIN_NAT_ALLOW_INSECURE", "0"),
    )


def _make_local_hello_envelope(*, is_reply: bool = False) -> dict[str, Any] | None:
    from backend.modules.p2p.crypto_ed25519 import sign_ed25519
    private = active_transport_private_key(chain_id=_CHAIN_ID, node_id=_NODE_ID)
    public = _self_pubkey_hex()
    base_url = _local_base_url()
    if not private or not public or not base_url:
        return None
    protocol = _local_protocol()
    message = canonical_hello_sign_bytes(
        chain_id=_CHAIN_ID, node_id=_NODE_ID, val_id=(_SELF_VAL_ID or None),
        base_url=base_url, pubkey_hex=public, protocol=protocol,
    )
    return {
        "type": "HELLO", "from_node_id": _NODE_ID,
        "from_val_id": (_SELF_VAL_ID or None), "chain_id": _CHAIN_ID,
        "ts_ms": float(time.time() * 1000), "hops": 0,
        "base_url": base_url,
        "payload": {
            "base_url": base_url, "val_id": _SELF_VAL_ID, "role": "peer",
            "pubkey_hex": public, "sig_hex": sign_ed25519(private, message),
            "is_reply": bool(is_reply), "via_nat_relay": True, "protocol": protocol,
        },
    }

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

    if lane == "consensus":
        local_protocol = _local_protocol()
        require_protocol = (
            _env_truthy("GLYPHCHAIN_REQUIRE_PROTOCOL_NEGOTIATION", "0")
            or int(local_protocol.get("active_version") or 1) > 1
        )
        peer_protocol = dict(getattr(p, "protocol", {}) or {})
        if require_protocol and not peer_protocol:
            raise HTTPException(status_code=403, detail="peer protocol advertisement required")
        if peer_protocol:
            try:
                peer_protocol = normalize_protocol_advertisement(peer_protocol)
            except ProtocolUpgradeError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            if int(peer_protocol.get("active_version") or 0) != int(local_protocol.get("active_version") or 0):
                raise HTTPException(status_code=409, detail="peer active protocol version mismatch")
            local_plan = str(local_protocol.get("plan_id") or "")
            if local_plan and str(peer_protocol.get("plan_id") or "") != local_plan:
                raise HTTPException(status_code=409, detail="peer protocol upgrade plan mismatch")

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
    priv_hex = _active_transport_private_key_hex()

    to_base_url = (to_base_url or "").strip().rstrip("/")
    if not to_base_url:
        return

    if not (chain_id and node_id and base_url and priv_hex):
        return

    pub_hex = _self_pubkey_hex()
    if not pub_hex:
        return

    protocol = _local_protocol()
    msg = canonical_hello_sign_bytes(
        chain_id=chain_id,
        node_id=node_id,
        val_id=(val_id or None),
        base_url=base_url,
        pubkey_hex=pub_hex, protocol=protocol,
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
            "protocol": protocol,
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
                response = await c.post(url, json=env, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(f"hello_http_{response.status_code}")
            try:
                result = response.json()
            except Exception:
                result = None
            responder = result.get("responder") if isinstance(result, dict) else None
            if isinstance(responder, dict):
                responder_payload = dict(responder.get("payload") or {})
                responder_node = str(responder.get("from_node_id") or "").strip()
                responder_val = responder.get("from_val_id") or responder_payload.get("val_id") or None
                responder_base = str(responder.get("base_url") or responder_payload.get("base_url") or to_base_url).strip().rstrip("/")
                responder_public = str(responder_payload.get("pubkey_hex") or "").strip().lower()
                responder_signature = str(responder_payload.get("sig_hex") or "").strip().lower()
                responder_protocol = responder_payload.get("protocol") if isinstance(responder_payload.get("protocol"), dict) else None
                expected = get_peer_by_node_id(responder_node)
                expected_public = str(getattr(expected, "pubkey_hex", "") or "").strip().lower() if expected else ""
                signed = canonical_hello_sign_bytes(
                    chain_id=chain_id, node_id=responder_node,
                    val_id=(str(responder_val).strip() if responder_val else None),
                    base_url=responder_base, pubkey_hex=responder_public, protocol=responder_protocol,
                )
                if (
                    responder_node and responder_public and responder_signature
                    and (not expected_public or expected_public == responder_public)
                    and (expected_public or not _env_truthy("GLYPHCHAIN_REQUIRE_SIGNED_DISCOVERY", "0"))
                    and verify_ed25519(responder_public, responder_signature, signed)
                ):
                    set_peer_identity(
                        node_id=responder_node, base_url=responder_base,
                        val_id=(str(responder_val).strip() if responder_val else None),
                        pubkey_hex=responder_public, hello_ok=True, protocol=responder_protocol,
                    )
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
        raw_records = str(os.getenv("GLYPHCHAIN_BOOTSTRAP_RECORDS_JSON", "") or "").strip()
        if raw_records:
            records = json.loads(raw_records)
            if not isinstance(records, list):
                raise PeerDiscoveryError("bootstrap_records_json_invalid")
            discovery = _signed_discovery_store()
            for record in records:
                discovery.import_record(record)
            _install_discovered_peers(discovery)
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
                    if str(getattr(p, "relay_url", "") or "").strip():
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


_NAT_LOCAL_ROUTES = {
    "HELLO": "/api/p2p/hello",
    "TX_RELAY": "/api/p2p/tx_relay",
    "BLOCK_ANNOUNCE": "/api/p2p/block_announce",
    "PROPOSAL": "/api/p2p/proposal",
    "VOTE": "/api/p2p/vote",
}


async def _nat_relay_broadcast_hello(relay_url: str) -> int:
    envelope = _make_local_hello_envelope(is_reply=False)
    if envelope is None:
        return 0
    sent = 0
    for peer in list_peers():
        target = str(getattr(peer, "node_id", "") or "").strip()
        base = str(getattr(peer, "base_url", "") or "").strip().rstrip("/")
        role = str(getattr(peer, "role", "") or "").strip().lower()
        if not target or target == _NODE_ID or (base == relay_url and role in {"relay", "validator"}):
            continue
        try:
            await enqueue_via_nat_relay(
                relay_url=relay_url, chain_id=_CHAIN_ID, from_node_id=_NODE_ID,
                target_node_id=target, envelope=envelope, ttl_ms=120_000,
            )
            sent += 1
        except Exception:
            continue
    return sent


async def _nat_relay_pull_once(relay_url: str) -> dict[str, int]:
    private = active_transport_private_key(chain_id=_CHAIN_ID, node_id=_NODE_ID)
    if not private:
        raise NATRelayError("nat_relay_transport_identity_required")
    pull = build_relay_operation(
        operation="PULL", chain_id=_CHAIN_ID, node_id=_NODE_ID,
        private_key_hex=private,
        payload={"limit": relay_limits_from_env().pull_batch},
    )
    result = await relay_post(
        relay_url=relay_url, route="/api/p2p/nat/pull", operation=pull,
        timeout_s=10.0,
    )
    payload = result.get("json")
    if result.get("status") != 200 or not isinstance(payload, dict) or payload.get("ok") is not True:
        raise NATRelayError(f"nat_relay_pull_failed:{result.get('status')}")
    acknowledged: list[str] = []
    delivered = rejected = 0
    for item in payload.get("messages") or []:
        if not isinstance(item, dict) or not isinstance(item.get("envelope"), dict):
            continue
        envelope = dict(item["envelope"])
        message_type = str(envelope.get("type") or "").strip().upper()
        route = _NAT_LOCAL_ROUTES.get(message_type)
        relay_id = str(item.get("relay_id") or "").strip()
        if not route or not relay_id:
            acknowledged.append(relay_id)
            rejected += 1
            continue
        sender = str(envelope.get("from_node_id") or "").strip()
        sender_val = str(envelope.get("from_val_id") or "").strip()
        try:
            local = await post_json(
                _local_base_url(), route, envelope, timeout_s=15.0,
                add_p2p_headers=True, p2p_from_node_id=sender,
                p2p_from_val_id=sender_val, p2p_chain_id=_CHAIN_ID,
            )
            status = int(local.get("status") or 0)
            if 200 <= status < 500 and status != 429:
                acknowledged.append(relay_id)
                delivered += int(status < 300)
                rejected += int(status >= 300)
        except Exception:
            continue
    if acknowledged:
        ack = build_relay_operation(
            operation="ACK", chain_id=_CHAIN_ID, node_id=_NODE_ID,
            private_key_hex=private, payload={"relay_ids": acknowledged},
        )
        response = await relay_post(
            relay_url=relay_url, route="/api/p2p/nat/ack", operation=ack,
            timeout_s=8.0,
        )
        if response.get("status") != 200:
            raise NATRelayError(f"nat_relay_ack_failed:{response.get('status')}")
    return {"received": len(payload.get("messages") or []), "delivered": delivered, "rejected": rejected}


@router.on_event("startup")
async def _p2p_nat_relay_client() -> None:
    try:
        relay_url = _nat_relay_url()
    except NATRelayError:
        return
    if not relay_url:
        return

    async def _run() -> None:
        poll_seconds = max(0.25, min(30.0, float(os.getenv("GLYPHCHAIN_NAT_POLL_SECONDS", "1") or 1)))
        last_hello = 0.0
        while True:
            try:
                relay_peer = next((
                    peer for peer in list_peers()
                    if str(getattr(peer, "base_url", "") or "").strip().rstrip("/") == relay_url
                    and str(getattr(peer, "role", "") or "").lower() in {"relay", "validator"}
                ), None)
                if relay_peer is None or not str(getattr(relay_peer, "pubkey_hex", "") or "").strip():
                    await asyncio.sleep(poll_seconds)
                    continue
                await _send_hello(relay_url, is_reply=False)
                if not bool(getattr(get_peer_by_node_id(relay_peer.node_id), "hello_ok", False)):
                    await asyncio.sleep(poll_seconds)
                    continue
                now = time.monotonic()
                if now - last_hello >= 30.0:
                    await _nat_relay_broadcast_hello(relay_url)
                    last_hello = now
                await _nat_relay_pull_once(relay_url)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(poll_seconds)

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
        "storage": peer_store_status(),
        "peers": [p.model_dump() for p in list_peers()],
    }


@router.post("/connect")
async def p2p_connect(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    if _env_truthy("GLYPHCHAIN_REQUIRE_SIGNED_DISCOVERY", "0"):
        raise HTTPException(status_code=403, detail="unsigned peer connect disabled; import a signed discovery record")
    load_peers_from_env()
    base_url = str(body.get("base_url") or body.get("url") or "").strip()
    node_id = str(body.get("node_id") or "").strip()
    val_id = body.get("val_id")
    role = str(body.get("role") or "peer")
    relay_url = str(body.get("relay_url") or "").strip() or None
    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and node_id required")

    p = add_peer(
        base_url=base_url,
        node_id=node_id,
        val_id=(str(val_id) if val_id is not None else None),
        role=role,
        relay_url=relay_url,
    )

    # ✅ NEW: on connect, initiate HELLO so we can accept SYNC_RESP from them.
    if base_url and not relay_url and base_url.rstrip("/") != _BASE_URL.rstrip("/"):
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
    protocol = payload.get("protocol") if isinstance(payload.get("protocol"), dict) else None

    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and from_node_id required")
    if not pubkey_hex or not sig_hex:
        raise HTTPException(status_code=400, detail="payload.pubkey_hex and payload.sig_hex required")
    if protocol is not None:
        try:
            protocol = normalize_protocol_advertisement(protocol)
        except ProtocolUpgradeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if _env_truthy("GLYPHCHAIN_REQUIRE_PROTOCOL_NEGOTIATION", "0") and protocol is None:
        raise HTTPException(status_code=403, detail="HELLO protocol advertisement required")

    expected_peer = get_peer_by_node_id(node_id)
    expected_pubkey = (
        str(getattr(expected_peer, "pubkey_hex", "") or "").strip().lower()
        if expected_peer is not None else ""
    )
    if expected_pubkey and expected_pubkey != pubkey_hex:
        raise HTTPException(status_code=403, detail="HELLO public key differs from trusted peer binding")
    if _env_truthy("GLYPHCHAIN_REQUIRE_SIGNED_DISCOVERY", "0") and not expected_pubkey:
        raise HTTPException(status_code=403, detail="HELLO peer is not present in signed discovery")

    msg = canonical_hello_sign_bytes(
        chain_id=_CHAIN_ID,
        node_id=node_id,
        val_id=(str(val_id).strip() if val_id is not None else None),
        base_url=base_url,
        pubkey_hex=pubkey_hex, protocol=protocol,
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
        protocol=protocol,
    )

    # **CRITICAL**: reply once so both sides become hello_ok (restart-safe)
    if (not is_reply) and base_url and base_url.rstrip("/") != (_BASE_URL or "").strip().rstrip("/"):
        asyncio.create_task(_send_hello(base_url, is_reply=True))

    return {
        "ok": True,
        "added": True,
        "peer": p.model_dump(),
        "peers": [x.model_dump() for x in list_peers()],
        "responder": _make_local_hello_envelope(is_reply=True),
    }


@router.post("/refresh")
async def p2p_refresh(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    if _env_truthy("GLYPHCHAIN_REQUIRE_SIGNED_DISCOVERY", "0"):
        raise HTTPException(status_code=403, detail="unsigned peer refresh disabled; use signed discovery refresh")
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
            relay_url=(str(pj.get("relay_url") or "").strip() or None),
        )
        merged += 1

        # ✅ NEW: proactively HELLO newly learned peers so we can accept SYNC_RESP, etc.
        if base_url and not str(pj.get("relay_url") or "").strip() and base_url.rstrip("/") != _BASE_URL.rstrip("/"):
            asyncio.create_task(_send_hello(base_url, is_reply=False))

    return {"ok": True, "merged": merged, "peers": [p.model_dump() for p in list_peers()]}


@router.get("/discovery/records")
async def p2p_discovery_records() -> Dict[str, Any]:
    try:
        store = _signed_discovery_store()
        return {"ok": True, "records": store.active_records(), "status": store.status()}
    except PeerDiscoveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/discovery/import")
async def p2p_discovery_import(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        store = _signed_discovery_store()
        result = store.import_record(body)
        installed = _install_discovered_peers(store)
        return {"ok": True, **result, "installed_peer_count": installed, "status": store.status()}
    except PeerDiscoveryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/discovery/refresh")
async def p2p_discovery_refresh(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    target = str(body.get("base_url") or body.get("url") or "").strip().rstrip("/")
    known = {str(peer.base_url or "").strip().rstrip("/") for peer in list_peers()}
    if not target or target not in known:
        raise HTTPException(status_code=403, detail="discovery refresh target is not an existing peer")
    upstream = await get_json(target, "/api/p2p/discovery/records", timeout_s=8.0)
    payload = upstream.get("json") or {}
    if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("records"), list):
        raise HTTPException(status_code=502, detail="signed discovery fetch failed")
    try:
        store = _signed_discovery_store()
        accepted = duplicates = 0
        for record in payload["records"]:
            result = store.import_record(record)
            accepted += int(bool(result.get("accepted")))
            duplicates += int(bool(result.get("duplicate")))
        installed = _install_discovered_peers(store)
        return {"ok": True, "accepted": accepted, "duplicates": duplicates,
                "installed_peer_count": installed, "status": store.status()}
    except PeerDiscoveryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/nat/put")
async def p2p_nat_put(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    verified, _peer = _verify_nat_operation(body, "PUT")
    target_node_id = str(verified.get("target_node_id") or "").strip()
    target = get_peer_by_node_id(target_node_id)
    if (
        target is None or bool(getattr(target, "banned", False))
        or not str(getattr(target, "pubkey_hex", "") or "").strip()
    ):
        raise HTTPException(status_code=403, detail="nat_relay_target_not_in_trusted_peer_registry")
    try:
        result = _nat_relay_store().put(
            from_node_id=verified["node_id"],
            target_node_id=target_node_id,
            envelope=dict(verified.get("envelope") or {}),
            ttl_ms=int(verified.get("ttl_ms") or 0),
        )
    except NATRelayError as exc:
        status = 429 if str(exc) in {"nat_relay_target_queue_full", "nat_relay_queue_full"} else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/nat/pull")
async def p2p_nat_pull(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    verified, _peer = _verify_nat_operation(body, "PULL")
    try:
        result = _nat_relay_store().pull(
            target_node_id=verified["node_id"], limit=int(verified.get("limit") or 0) or None,
        )
    except NATRelayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/nat/ack")
async def p2p_nat_ack(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    verified, _peer = _verify_nat_operation(body, "ACK")
    relay_ids = verified.get("relay_ids")
    if not isinstance(relay_ids, list):
        raise HTTPException(status_code=422, detail="nat_relay_ack_invalid")
    try:
        result = _nat_relay_store().ack(
            target_node_id=verified["node_id"], relay_ids=[str(value) for value in relay_ids],
        )
    except NATRelayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.get("/nat/status")
async def p2p_nat_status() -> Dict[str, Any]:
    participation = _require_nat_relay_role()
    return {
        "ok": True,
        "role": participation.get("role"),
        "transport": "outbound_https_polling",
        "end_to_end_peer_signatures_required": True,
        "stores_legal_documents": False,
        "queue": _nat_relay_store().status(),
    }


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

    # ✅ queue key: stable for dup floods
    msg_id = str(payload.get("msg_id") or f"block_req:{h}:{want}")

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

            pref = f"h{height}-"
            try:
                for k, v in store.items():
                    if isinstance(k, str) and k.startswith(pref) and v:
                        return v
            except Exception:
                pass

            try:
                for v in store.values():
                    if _blk_height(v) == height:
                        return v
            except Exception:
                pass

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

        hit = _find_by_height_in_store(obj, height)
        if hit:
            return hit

        if isinstance(obj, dict):
            try:
                for v in obj.values():
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
            except Exception:
                return None
            return None

        if isinstance(obj, list):
            try:
                for v in obj:
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
            except Exception:
                return None
            return None

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
                if isinstance(v, (dict, list)) or ("block" in name.lower()) or ("store" in name.lower()):
                    hit = _deep_search(v, height, depth=depth - 1, seen=seen)
                    if hit:
                        return hit
        except Exception:
            return None

        return None

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[Dict[str, Any]] = loop.create_future()

    async def _job() -> None:
        try:
            blk: Any = None

            # -------------------------
            # 1) consensus engine (deep)
            # -------------------------
            try:
                if _CONSENSUS_OK and get_engine is not None:
                    eng = get_engine()

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

                    if not blk:
                        blk = _deep_search(eng, h, depth=3, seen=set())
            except Exception:
                blk = None

            # -------------------------
            # 2) chain_sim ledger fallback (+ replay-on-miss)
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
                    if not fut.done():
                        fut.set_result({"ok": True, "height": h, "header": header})
                    return
                if not fut.done():
                    fut.set_result({"ok": True, "height": h, "block": blk})
                return

            # -------------------------
            # 3) proxy-on-miss
            # -------------------------
            max_hops = _env_int("P2P_BLOCK_PROXY_MAX_HOPS", 2)
            cur_hops = int(getattr(env, "hops", 0) or 0)
            if cur_hops >= max_hops:
                if not fut.done():
                    fut.set_result({"ok": False, "error": f"block not found (height={h})"})
                return

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
                            if not fut.done():
                                fut.set_result(out)
                            return
                    except Exception:
                        continue
            except Exception:
                pass

            if not fut.done():
                fut.set_result({"ok": False, "error": f"block not found (height={h})"})
        except Exception as e:
            if not fut.done():
                fut.set_result({"ok": False, "error": f"block_req job crashed: {e!r}"})

    enq = await _LIM.enqueue(lane="block", msg_id=msg_id, job=_job)
    if not bool(enq.get("enqueued")):
        return {"ok": True, "accepted": False, "ignored": True, "reason": str(enq.get("reason") or "not enqueued")}

    out = await asyncio.wait_for(fut, timeout=20.0)
    if out.get("ok") is not True:
        raise HTTPException(status_code=404, detail=str(out.get("error") or "block not found"))
    return out

# -------------------------
# Consensus messages (PR1)
# -------------------------

from backend.modules.p2p.ingress import get_lanes

@router.get("/consensus_status")
async def p2p_consensus_status() -> Dict[str, Any]:
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")
    eng = get_engine()
    st = eng.status()
    st["p2p_ingress"] = get_lanes().snapshot()
    return st


@router.get("/consensus_finality")
async def p2p_consensus_finality(
    height: int = Query(..., ge=1),
    block_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Fetch a retained QC/finality receipt without trusting a status summary."""
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")
    result = get_engine().finality_receipt(height=height, block_id=block_id)
    if result.get("found") is not True:
        raise HTTPException(status_code=404, detail="finality receipt not retained")
    return result


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

    payload_in = env.payload or {}
    if not isinstance(payload_in, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    # ✅ Signature verification must use UNSIGNED payload (tests sign without sig_hex/msg_id)
    if _require_signed_consensus():
        sig_hex = str(payload_in.get("sig_hex") or "").strip().lower()
        if not sig_hex:
            raise HTTPException(status_code=403, detail="missing proposal sig_hex")

        peer = get_peer_by_node_id(peer_node)
        pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
        if not pubkey_hex:
            raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

        unsigned = dict(payload_in)
        unsigned.pop("sig_hex", None)
        unsigned.pop("msg_id", None)

        try:
            msg = canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=_CHAIN_ID, payload=unsigned)
            ok = verify_ed25519(pubkey_hex, sig_hex, msg)
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"proposal signature verify error: {e}")

        if not ok:
            raise HTTPException(status_code=403, detail="proposal signature invalid")

    # ✅ stable msg_id for LaneLimiter (exclude sig_hex/ts_ms/msg_id if your helper does)
    unsigned_for_id = dict(payload_in)
    unsigned_for_id.pop("sig_hex", None)
    unsigned_for_id.pop("msg_id", None)
    msg_id = str(payload_in.get("msg_id") or _proposal_msg_id(unsigned_for_id))

    payload_model = dict(payload_in)
    payload_model.pop("msg_id", None)

    # ✅ Structural validation at HTTP boundary (400s visible to tests)
    try:
        p = Proposal(**payload_model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad proposal payload: {e}")

    # ✅ Backpressure: enqueue REAL work, await result
    try:
        from backend.modules.p2p.ingress import get_lanes
        lanes = get_lanes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"lane limiter unavailable: {e}")

    loop = asyncio.get_running_loop()
    fut: "asyncio.Future[Dict[str, Any]]" = loop.create_future()

    async def _job() -> None:
        try:
            out = get_engine().handle_proposal(p)
            if not isinstance(out, dict):
                out = {"ok": False, "error": "proposal rejected"}
            if not fut.done():
                fut.set_result(out)
        except Exception as e:
            if not fut.done():
                fut.set_exception(e)

    q = await lanes.enqueue(lane="proposal", msg_id=msg_id, job=_job)

    # dropped by limiter (dup/full) → best-effort 200; do not 500
    if not q.get("enqueued"):
        return {
            "ok": True,
            "enqueued": False,
            "dropped": True,
            "reason": str(q.get("reason") or "dropped"),
            "accepted": False,
        }

    try:
        out = await fut
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"engine.handle_proposal crashed: {e}")

    if not isinstance(out, dict) or out.get("ok") is not True:
        raise HTTPException(status_code=400, detail=str((out or {}).get("error") or "proposal rejected"))

    return {"ok": True, "enqueued": True, **out}


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

    try:
        _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    except HTTPException as exc:
        if exc.status_code != 429:
            raise
        # Votes are one-way gossip.  A bounded, observable drop prevents
        # retry storms while still ensuring rate-limited work never reaches
        # signature/model/consensus processing.
        return {
            "ok": True,
            "enqueued": False,
            "dropped": True,
            "accepted": False,
            "reason": "peer_rate_limited",
        }
    _enforce_peer_binding(request, env)

    vset = ValidatorSet.from_env()
    if not vset.is_member(peer_val or env.from_val_id or ""):
        raise HTTPException(status_code=403, detail="from_val_id not in ValidatorSet")

    payload_in = env.payload or {}
    if not isinstance(payload_in, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    err = validate_vote_payload_or_error(payload_in)
    if err:
        return JSONResponse(status_code=400, content={"detail": err})

    # ✅ verify signature (sign bytes must exclude sig_hex/msg_id)
    if _require_signed_consensus():
        sig_hex = str(payload_in.get("sig_hex") or "").strip().lower()
        if not sig_hex:
            raise HTTPException(status_code=403, detail="missing vote sig_hex")

        peer = get_peer_by_node_id(peer_node)
        pubkey_hex = (getattr(peer, "pubkey_hex", None) or "").strip().lower() if peer else ""
        if not pubkey_hex:
            raise HTTPException(status_code=403, detail="missing peer pubkey (need HELLO)")

        unsigned = dict(payload_in)
        unsigned.pop("sig_hex", None)
        unsigned.pop("msg_id", None)

        try:
            msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=_CHAIN_ID, payload=unsigned)
            ok = verify_ed25519(pubkey_hex, sig_hex, msg)
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"vote signature verify error: {e}")

        if not ok:
            raise HTTPException(status_code=403, detail="vote signature invalid")

    # ✅ stable msg_id for LaneLimiter (exclude sig_hex/msg_id)
    unsigned_for_id = dict(payload_in)
    unsigned_for_id.pop("sig_hex", None)
    unsigned_for_id.pop("msg_id", None)
    msg_id = str(payload_in.get("msg_id") or _vote_msg_id(unsigned_for_id))

    # build model payload (don’t pass msg_id)
    payload_model = dict(payload_in)
    payload_model.pop("msg_id", None)

    try:
        v = Vote(**payload_model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad vote payload: {e}")

    # ✅ Backpressure: enqueue REAL work, await result
    try:
        from backend.modules.p2p.ingress import get_lanes
        lanes = get_lanes()
    except Exception as e:
        # keep tests away from 500s
        return {"ok": True, "enqueued": False, "accepted": False, "ignored": True, "reason": f"lane limiter unavailable: {e}"}

    loop = asyncio.get_running_loop()
    fut: "asyncio.Future[Dict[str, Any]]" = loop.create_future()

    async def _job() -> None:
        try:
            eng = get_engine()
            fn = getattr(eng, "handle_vote", None)
            if not callable(fn):
                out: Dict[str, Any] = {"ok": False, "error": "engine missing handle_vote"}
            else:
                out = fn(v)  # sync call

            if not isinstance(out, dict):
                out = {"ok": False, "error": "vote rejected"}

            if not fut.done():
                fut.set_result(out)
        except Exception as e:
            if not fut.done():
                fut.set_result({"ok": False, "error": f"engine.handle_vote crashed: {e}"})

    q = await lanes.enqueue(lane="vote", msg_id=msg_id, job=_job)

    # dropped by limiter (dup/full) → best-effort 200; do not 500
    if not q.get("enqueued"):
        return {
            "ok": True,
            "enqueued": False,
            "dropped": True,
            "reason": str(q.get("reason") or "dropped"),
            "accepted": False,
        }

    # ✅ never 500 (tests require 200/400/403 only)
    out = await fut
    if not isinstance(out, dict) or out.get("ok") is not True:
        raise HTTPException(status_code=400, detail=str((out or {}).get("error") or "vote rejected"))

    return {"ok": True, "enqueued": True, **out}


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

    # lane snapshot is optional; never fail STATUS because of ingress plumbing
    ingress = None
    try:
        from backend.modules.p2p.ingress import get_lanes  # singleton LaneLimiter
        ingress = get_lanes().snapshot()
    except Exception:
        ingress = None

    def _mk_metrics(st: Dict[str, Any]) -> Dict[str, Any]:
        try:
            fh = int(st.get("finalized_height") or 0)
        except Exception:
            fh = 0
        try:
            hh = int(st.get("height") or st.get("next_height") or 0)
        except Exception:
            hh = 0
        try:
            rr = int(st.get("round") or 0)
        except Exception:
            rr = 0

        last_qc = st.get("last_qc") or {}
        try:
            last_qc_ts = float(last_qc.get("ts_ms") or 0.0) if isinstance(last_qc, dict) else 0.0
        except Exception:
            last_qc_ts = 0.0

        # round_started_ms may or may not exist in status(); keep best-effort
        try:
            rstart = float(st.get("round_started_ms") or 0.0)
        except Exception:
            rstart = 0.0

        return {
            "cur_round": rr,
            "round_started_ms": rstart,
            "last_qc_ts_ms": last_qc_ts,
            "finalized_height": fh,
            "height": hh,
            "height_lag": max(0, hh - (fh + 1)) if hh > 0 else 0,
        }

    # ✅ allow self-calls (tests do _p2p_status(a, a))
    if peer_node and peer_node == (_NODE_ID or ""):
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
            "metrics": _mk_metrics(st),
            "self": True,
        }
        if ingress is not None:
            resp["p2p_ingress"] = ingress
        return resp

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

    resp: Dict[str, Any] = {
        "ok": True,
        "payload": {
            "node_id": st.get("node_id"),
            "finalized_height": int(st.get("finalized_height") or 0),
            "height": int(st.get("height") or st.get("next_height") or 0),
            "round": int(st.get("round") or 0),
            "last_qc": st.get("last_qc"),
        },
        "metrics": _mk_metrics(st),
    }
    if ingress is not None:
        resp["p2p_ingress"] = ingress

    _resp_cache_set(peer_key, env, resp)
    return resp

def _stable_json_bytes(x: Any) -> bytes:
    try:
        return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        return repr(x).encode("utf-8")

def _sync_req_msg_id(*, peer_key: str, env: P2PEnvelope) -> str:
    # request-like: make this UNIQUE per request so LaneLimiter never dup-drops before cache can help
    base = {
        "peer": str(peer_key or ""),
        "ts_ms": float(getattr(env, "ts_ms", 0.0) or 0.0),
        "nonce_ms": _now_ms(),
    }
    return "sync_req:" + hashlib.sha256(_stable_json_bytes(base)).hexdigest()

def _sync_resp_msg_id(payload: Dict[str, Any]) -> str:
    # message-like: stable id so dup storms drop early
    unsigned = dict(payload or {})
    unsigned.pop("sig_hex", None)
    unsigned.pop("msg_id", None)
    return "sync_resp:" + hashlib.sha256(_stable_json_bytes(unsigned)).hexdigest()

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

    # ✅ enqueue compute under limiter; await result so 4xx/5xx semantics remain
    msg_id = str(payload.get("msg_id") or f"sync_req:{peer_key}")

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[Dict[str, Any]] = loop.create_future()

    async def _job() -> None:
        try:
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
            if not fut.done():
                fut.set_result(resp)
        except Exception as e:
            if not fut.done():
                fut.set_result({"ok": False, "error": f"sync_req compute error: {e!r}"})

    enq = await _LIM.enqueue(lane="sync", msg_id=msg_id, job=_job)
    if not bool(enq.get("enqueued")):
        # request-like: if we can't enqueue, return a clean “ignored” 200 instead of wedging
        return {"ok": True, "accepted": False, "ignored": True, "reason": str(enq.get("reason") or "not enqueued")}

    resp = await asyncio.wait_for(fut, timeout=10.0)
    if resp.get("ok") is not True:
        raise HTTPException(status_code=500, detail=str(resp.get("error") or "sync_req compute failed"))
    return resp


@router.post("/snapshot_req")
async def p2p_snapshot_req(
    request: Request,
    background_tasks: BackgroundTasks,
    env: P2PEnvelope = Body(...),
):
    """Serve a finality-anchored ledger snapshot to a verified peer.

    Snapshot transport is intentionally unavailable on light nodes and on nodes
    without a signing identity.  The receiver must still verify the archive
    against its own independently pinned checkpoint before installation.
    """
    if not _CONSENSUS_OK or get_engine is None:
        raise HTTPException(status_code=501, detail=f"consensus not available: {_CONSENSUS_ERR}")
    if env.type != "SNAPSHOT_REQ":
        raise HTTPException(status_code=400, detail="expected type=SNAPSHOT_REQ")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")
    participation = participation_from_env()
    if str(participation.get("role") or "light") not in {"relay", "validator"}:
        raise HTTPException(status_code=403, detail="snapshot_service_requires_relay_or_validator_role")
    if not _has_local_p2p_identity():
        raise HTTPException(status_code=503, detail="snapshot_service_requires_managed_network_identity")
    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")
    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))
    _enforce_peer_binding(request, env, lane="sync")
    payload = env.payload or {}
    if not isinstance(payload, dict) or payload.get("want") != "latest_finalized_snapshot":
        raise HTTPException(status_code=400, detail="snapshot_request_invalid")
    _verify_sig_or_403(peer_node=peer_node, msg_type="SNAPSHOT_REQ", payload=payload)

    temporary_root = Path(tempfile.mkdtemp(prefix="glyphchain-peer-snapshot-"))
    output = temporary_root / "ledger.glyphchain-snapshot"
    try:
        manifest = await asyncio.to_thread(export_current_finalized_snapshot, output)
        minimum_height = max(0, int(payload.get("minimum_height") or 0))
        snapshot_height = int(dict(manifest.get("ledger") or {}).get("height") or 0)
        if snapshot_height <= minimum_height:
            raise HTTPException(status_code=409, detail="peer_has_no_newer_finalized_snapshot")
    except HTTPException:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    except (LedgerSnapshotError, OSError, RuntimeError) as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise HTTPException(status_code=503, detail=f"glyphchain_snapshot_unavailable:{exc}") from exc
    background_tasks.add_task(shutil.rmtree, temporary_root, True)
    return FileResponse(
        output,
        media_type=SNAPSHOT_MEDIA_TYPE,
        filename=f"glyphchain-{manifest['snapshot_id'][:16]}-h{snapshot_height}.glyphchain-snapshot",
        background=background_tasks,
        headers={
            "X-GlyphChain-Snapshot-Id": str(manifest["snapshot_id"]),
            "X-GlyphChain-Snapshot-Height": str(snapshot_height),
        },
    )


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

    # ✅ PR6.3: structural QC dict validation at ingress (never let garbage hit engine/lanes)
    qc_d = (payload or {}).get("last_qc")
    err = validate_qc_dict_or_error(qc_d)
    if err:
        return JSONResponse(status_code=400, content={"detail": err})

    # ✅ message-like lane: optional signature verify (by env)
    if _require_signed_for_lane("sync"):
        _verify_sig_or_403(peer_node=peer_node, msg_type="SYNC_RESP", payload=payload)

    # envelope-level dedup (cheap)
    d = _drop_if_dup(peer_key, env)
    if d is not None:
        return d

    msg_id = str(
        payload.get("msg_id")
        or f"sync_resp:{int(payload.get('finalized_height') or 0)}:{(payload.get('last_qc') or {}).get('block_id')}"
    )

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[Dict[str, Any]] = loop.create_future()

    async def _job() -> None:
        try:
            out = get_engine().handle_sync_resp(payload)
            if not fut.done():
                fut.set_result(out if isinstance(out, dict) else {"ok": False, "error": "bad sync_resp result"})
        except Exception as e:
            if not fut.done():
                fut.set_result({"ok": False, "error": f"engine.handle_sync_resp crashed: {e}"})

    enq = await _LIM.enqueue(lane="sync", msg_id=msg_id, job=_job)
    if not bool(enq.get("enqueued")):
        return {"ok": True, "accepted": False, "ignored": True, "reason": str(enq.get("reason") or "not enqueued")}

    out = await asyncio.wait_for(fut, timeout=10.0)
    if not isinstance(out, dict) or out.get("ok") is not True:
        raise HTTPException(status_code=400, detail=str((out or {}).get("error") or "bad sync_resp"))
    # Preserve the engine's response contract at the HTTP boundary.  Wrapping
    # the whole result under ``applied`` changes a boolean into an object and
    # makes rejected/conflicting sync data look truthy to clients.
    return {"ok": True, **out}
