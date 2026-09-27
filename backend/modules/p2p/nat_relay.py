"""Outbound-only relay transport for GlyphChain nodes behind NAT.

The relay never becomes a consensus or finality authority.  It accepts only
transport-key authenticated operations from peers that have completed HELLO,
stores bounded original P2P envelopes, and lets the named recipient retrieve
them over an outbound HTTPS request.  The recipient still submits every
original envelope through its ordinary local P2P route, where the sender's
HELLO binding and lane signature are checked again.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import httpx

from .crypto_ed25519 import sign_ed25519, stable_json_bytes, verify_ed25519


SCHEMA_VERSION = "glyphchain.nat-relay.v1"
ALLOWED_MESSAGE_TYPES = {
    "HELLO", "TX_RELAY", "BLOCK_ANNOUNCE", "PROPOSAL", "VOTE",
}


class NATRelayError(ValueError):
    pass


def canonical_relay_operation(value: Mapping[str, Any]) -> bytes:
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    return stable_json_bytes(unsigned)


def sign_relay_operation(value: Mapping[str, Any], private_key_hex: str) -> dict[str, Any]:
    signed = dict(value)
    signed["signature_hex"] = sign_ed25519(private_key_hex, canonical_relay_operation(signed))
    return signed


def verify_relay_operation(
    value: Mapping[str, Any], *, expected_chain_id: str, public_key_hex: str,
    clock_ms: Callable[[], int] | None = None, maximum_skew_ms: int = 60_000,
) -> dict[str, Any]:
    body = dict(value)
    if body.get("schema_version") != SCHEMA_VERSION:
        raise NATRelayError("nat_relay_schema_unsupported")
    if str(body.get("chain_id") or "") != str(expected_chain_id or ""):
        raise NATRelayError("nat_relay_chain_mismatch")
    node_id = str(body.get("node_id") or "").strip()
    operation = str(body.get("operation") or "").strip().upper()
    nonce = str(body.get("nonce") or "").strip()
    if not node_id or len(node_id) > 180:
        raise NATRelayError("nat_relay_node_id_invalid")
    if operation not in {"PUT", "PULL", "ACK"}:
        raise NATRelayError("nat_relay_operation_invalid")
    if not nonce or len(nonce) > 180:
        raise NATRelayError("nat_relay_nonce_invalid")
    try:
        issued_at_ms = int(body.get("issued_at_ms"))
    except Exception as exc:
        raise NATRelayError("nat_relay_timestamp_invalid") from exc
    now = int((clock_ms or (lambda: int(time.time() * 1000)))())
    if abs(now - issued_at_ms) > max(1_000, int(maximum_skew_ms)):
        raise NATRelayError("nat_relay_timestamp_outside_window")
    signature = str(body.get("signature_hex") or "").strip().lower()
    if not signature or not verify_ed25519(public_key_hex, signature, canonical_relay_operation(body)):
        raise NATRelayError("nat_relay_signature_invalid")
    return body


@dataclass(frozen=True)
class NATRelayLimits:
    maximum_messages: int = 4096
    maximum_per_target: int = 512
    maximum_message_bytes: int = 1024 * 1024
    maximum_ttl_ms: int = 5 * 60 * 1000
    pull_batch: int = 64


class NATRelayStore:
    """Restart-safe, bounded queue for opaque signed P2P envelopes."""

    def __init__(
        self, root: str | Path, *, chain_id: str, limits: NATRelayLimits | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / "nat-relay-queue.json"
        self.replay_path = self.root / "nat-relay-replay.json"
        self.chain_id = str(chain_id or "").strip()
        self.limits = limits or NATRelayLimits()
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self._lock = threading.RLock()
        if not self.chain_id:
            raise NATRelayError("nat_relay_chain_required")

    def remember_operation_nonce(
        self,
        *,
        node_id: str,
        nonce: str,
        issued_at_ms: int,
        maximum_age_ms: int = 120_000,
        maximum_entries: int = 8192,
    ) -> None:
        """Persist an authenticated operation nonce across relay restarts.

        Only a digest of the peer identity and nonce is retained.  A corrupt or
        unwriteable replay journal fails closed rather than accepting an
        operation whose uniqueness cannot be established.
        """

        peer = str(node_id or "").strip()
        value = str(nonce or "").strip()
        if not peer or not value:
            raise NATRelayError("nat_relay_nonce_invalid")
        now = int(self.clock_ms())
        age = min(max(1_000, int(maximum_age_ms)), 10 * 60 * 1000)
        capacity = min(max(64, int(maximum_entries)), 100_000)
        replay_key = sha256(f"{peer}\0{value}".encode("utf-8")).hexdigest()
        expires_at = int(issued_at_ms) + age
        with self._lock:
            state = self._load_replay_locked()
            state["nonces"] = {
                key: expiry for key, expiry in state["nonces"].items()
                if int(expiry) >= now
            }
            if replay_key in state["nonces"]:
                raise NATRelayError("nat_relay_operation_replayed")
            if len(state["nonces"]) >= capacity:
                raise NATRelayError("nat_relay_replay_store_capacity_exceeded")
            state["nonces"][replay_key] = expires_at
            self._write_json_locked(self.replay_path, state)

    def put(
        self, *, from_node_id: str, target_node_id: str, envelope: Mapping[str, Any],
        ttl_ms: int,
    ) -> dict[str, Any]:
        sender = str(from_node_id or "").strip()
        target = str(target_node_id or "").strip()
        message = dict(envelope)
        if not sender or not target or sender == target:
            raise NATRelayError("nat_relay_route_invalid")
        if str(message.get("from_node_id") or "").strip() != sender:
            raise NATRelayError("nat_relay_sender_mismatch")
        if str(message.get("chain_id") or "") != self.chain_id:
            raise NATRelayError("nat_relay_envelope_chain_mismatch")
        if str(message.get("type") or "").strip().upper() not in ALLOWED_MESSAGE_TYPES:
            raise NATRelayError("nat_relay_message_type_invalid")
        encoded = stable_json_bytes(message)
        if len(encoded) <= 0 or len(encoded) > int(self.limits.maximum_message_bytes):
            raise NATRelayError("nat_relay_message_size_invalid")
        duration = int(ttl_ms)
        if duration < 1_000 or duration > int(self.limits.maximum_ttl_ms):
            raise NATRelayError("nat_relay_ttl_invalid")
        now = int(self.clock_ms())
        relay_id = "nat-" + sha256(stable_json_bytes({
            "chain_id": self.chain_id, "from_node_id": sender,
            "target_node_id": target, "envelope": message,
        })).hexdigest()
        with self._lock:
            state = self._load_locked()
            self._purge_locked(state, now)
            for existing in state["messages"]:
                if existing["relay_id"] == relay_id:
                    return {"accepted": True, "duplicate": True, "relay_id": relay_id}
            target_count = sum(1 for item in state["messages"] if item["target_node_id"] == target)
            if target_count >= int(self.limits.maximum_per_target):
                raise NATRelayError("nat_relay_target_queue_full")
            if len(state["messages"]) >= int(self.limits.maximum_messages):
                raise NATRelayError("nat_relay_queue_full")
            state["messages"].append({
                "relay_id": relay_id,
                "from_node_id": sender,
                "target_node_id": target,
                "created_at_ms": now,
                "expires_at_ms": now + duration,
                "delivery_attempts": 0,
                "envelope": message,
            })
            self._write_locked(state)
        return {"accepted": True, "duplicate": False, "relay_id": relay_id}

    def pull(self, *, target_node_id: str, limit: int | None = None) -> dict[str, Any]:
        target = str(target_node_id or "").strip()
        if not target:
            raise NATRelayError("nat_relay_target_required")
        batch = min(max(1, int(limit or self.limits.pull_batch)), int(self.limits.pull_batch))
        now = int(self.clock_ms())
        with self._lock:
            state = self._load_locked()
            changed = self._purge_locked(state, now)
            messages = [item for item in state["messages"] if item["target_node_id"] == target][:batch]
            for item in messages:
                item["delivery_attempts"] = int(item.get("delivery_attempts") or 0) + 1
                item["last_delivery_at_ms"] = now
                changed = True
            if changed:
                self._write_locked(state)
        return {"messages": messages, "remaining": max(0, self.count_for(target) - len(messages))}

    def ack(self, *, target_node_id: str, relay_ids: list[str]) -> dict[str, Any]:
        target = str(target_node_id or "").strip()
        ids = {str(value or "").strip() for value in relay_ids if str(value or "").strip()}
        if not target or not ids or len(ids) > int(self.limits.pull_batch):
            raise NATRelayError("nat_relay_ack_invalid")
        with self._lock:
            state = self._load_locked()
            before = len(state["messages"])
            state["messages"] = [
                item for item in state["messages"]
                if not (item["target_node_id"] == target and item["relay_id"] in ids)
            ]
            removed = before - len(state["messages"])
            if removed:
                self._write_locked(state)
        return {"acknowledged": removed}

    def status(self) -> dict[str, Any]:
        now = int(self.clock_ms())
        with self._lock:
            state = self._load_locked()
            if self._purge_locked(state, now):
                self._write_locked(state)
            counts: dict[str, int] = {}
            for item in state["messages"]:
                target_hash = sha256(item["target_node_id"].encode("utf-8")).hexdigest()
                counts[target_hash] = counts.get(target_hash, 0) + 1
            return {
                "schema_version": SCHEMA_VERSION,
                "queued_messages": len(state["messages"]),
                "target_count": len(counts),
                "maximum_messages": int(self.limits.maximum_messages),
                "maximum_per_target": int(self.limits.maximum_per_target),
                "maximum_message_bytes": int(self.limits.maximum_message_bytes),
                "maximum_ttl_ms": int(self.limits.maximum_ttl_ms),
            }

    def count_for(self, target_node_id: str) -> int:
        target = str(target_node_id or "").strip()
        with self._lock:
            state = self._load_locked()
            return sum(1 for item in state["messages"] if item["target_node_id"] == target)

    def _default(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "chain_id": self.chain_id, "messages": []}

    def _load_replay_locked(self) -> dict[str, Any]:
        if not self.replay_path.exists():
            return {
                "schema_version": SCHEMA_VERSION,
                "chain_id": self.chain_id,
                "nonces": {},
            }
        try:
            value = json.loads(self.replay_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise NATRelayError("nat_relay_replay_store_unreadable") from exc
        if value.get("schema_version") != SCHEMA_VERSION or value.get("chain_id") != self.chain_id:
            raise NATRelayError("nat_relay_replay_store_identity_invalid")
        nonces = value.get("nonces")
        if not isinstance(nonces, dict) or len(nonces) > 100_000:
            raise NATRelayError("nat_relay_replay_store_invalid")
        for key, expiry in nonces.items():
            if not isinstance(key, str) or len(key) != 64:
                raise NATRelayError("nat_relay_replay_store_invalid")
            try:
                int(expiry)
            except Exception as exc:
                raise NATRelayError("nat_relay_replay_store_invalid") from exc
        return value

    def _load_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise NATRelayError("nat_relay_queue_unreadable") from exc
        if value.get("schema_version") != SCHEMA_VERSION or value.get("chain_id") != self.chain_id:
            raise NATRelayError("nat_relay_queue_identity_invalid")
        if not isinstance(value.get("messages"), list):
            raise NATRelayError("nat_relay_queue_invalid")
        return value

    def _purge_locked(self, state: dict[str, Any], now: int) -> bool:
        before = len(state["messages"])
        state["messages"] = [item for item in state["messages"] if int(item.get("expires_at_ms") or 0) > now]
        return before != len(state["messages"])

    def _write_locked(self, state: Mapping[str, Any]) -> None:
        self._write_json_locked(self.path, state)

    def _write_json_locked(self, path: Path, state: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(state), sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)


def relay_limits_from_env() -> NATRelayLimits:
    def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            return min(maximum, max(minimum, int(os.getenv(name, str(default)) or default)))
        except Exception:
            return default
    return NATRelayLimits(
        maximum_messages=bounded("GLYPHCHAIN_NAT_RELAY_MAX_MESSAGES", 4096, 64, 100_000),
        maximum_per_target=bounded("GLYPHCHAIN_NAT_RELAY_MAX_PER_TARGET", 512, 8, 10_000),
        maximum_message_bytes=bounded("GLYPHCHAIN_NAT_RELAY_MAX_MESSAGE_BYTES", 1024 * 1024, 4096, 4 * 1024 * 1024),
        maximum_ttl_ms=bounded("GLYPHCHAIN_NAT_RELAY_MAX_TTL_MS", 300_000, 10_000, 3_600_000),
        pull_batch=bounded("GLYPHCHAIN_NAT_RELAY_PULL_BATCH", 64, 1, 256),
    )


def validate_nat_relay_url(value: str, *, allow_insecure: bool = False) -> str:
    url = str(value or "").strip().rstrip("/")
    parsed = urlparse(url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise NATRelayError("nat_relay_url_invalid")
    if parsed.scheme != "https" and not (allow_insecure and parsed.scheme == "http"):
        raise NATRelayError("nat_relay_https_required")
    return url


def active_transport_private_key(*, chain_id: str, node_id: str) -> str:
    configured = str(os.getenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", "") or "").strip().lower()
    if configured:
        return configured
    root = str(os.getenv("GLYPHCHAIN_NETWORK_KEY_DIR", "") or "").strip()
    if not root:
        return ""
    from .network_identity import NetworkIdentityStore
    return NetworkIdentityStore(root, chain_id=chain_id, node_id=node_id).active_private_key_hex()


def build_relay_operation(
    *, operation: str, chain_id: str, node_id: str, private_key_hex: str,
    payload: Mapping[str, Any] | None = None, clock_ms: Callable[[], int] | None = None,
) -> dict[str, Any]:
    now = int((clock_ms or (lambda: int(time.time() * 1000)))())
    seed = stable_json_bytes({
        "operation": str(operation or "").upper(), "chain_id": chain_id,
        "node_id": node_id, "issued_at_ms": now,
        "entropy": os.urandom(16).hex(),
    })
    value = {
        "schema_version": SCHEMA_VERSION,
        "operation": str(operation or "").upper(),
        "chain_id": str(chain_id or ""),
        "node_id": str(node_id or ""),
        "issued_at_ms": now,
        "nonce": sha256(seed).hexdigest(),
        **dict(payload or {}),
    }
    return sign_relay_operation(value, private_key_hex)


async def relay_post(
    *, relay_url: str, route: str, operation: Mapping[str, Any], timeout_s: float = 8.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    allow_insecure = str(os.getenv("GLYPHCHAIN_NAT_ALLOW_INSECURE", "0") or "0").lower() in {
        "1", "true", "yes", "on",
    }
    base = validate_nat_relay_url(relay_url, allow_insecure=allow_insecure)
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=False, transport=transport) as client:
        response = await client.post(base + route, json=dict(operation))
    try:
        payload = response.json()
    except Exception:
        payload = None
    return {
        "status": int(response.status_code),
        "json": payload,
        "text": response.text[:1024],
    }


async def enqueue_via_nat_relay(
    *, relay_url: str, chain_id: str, from_node_id: str, target_node_id: str,
    envelope: Mapping[str, Any], ttl_ms: int = 120_000,
    private_key_hex: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    private = str(private_key_hex or active_transport_private_key(
        chain_id=chain_id, node_id=from_node_id,
    )).strip().lower()
    if not private:
        raise NATRelayError("nat_relay_transport_identity_required")
    operation = build_relay_operation(
        operation="PUT", chain_id=chain_id, node_id=from_node_id,
        private_key_hex=private,
        payload={
            "target_node_id": str(target_node_id or "").strip(),
            "ttl_ms": int(ttl_ms),
            "envelope": dict(envelope),
        },
    )
    result = await relay_post(
        relay_url=relay_url, route="/api/p2p/nat/put", operation=operation,
        transport=transport,
    )
    if result["status"] != 200 or not isinstance(result.get("json"), dict):
        raise NATRelayError(f"nat_relay_put_failed:{result['status']}")
    return dict(result["json"])
