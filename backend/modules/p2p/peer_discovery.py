"""Signed, replay-resistant peer bootstrap records for GlyphChain nodes."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from backend.modules.p2p.crypto_ed25519 import sign_ed25519, stable_json_bytes, verify_ed25519


SCHEMA_VERSION = "glyphchain.peer-discovery.v1"
ROLES = {"light", "relay", "validator"}


class PeerDiscoveryError(ValueError):
    pass


def _unsigned(record: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(record))
    value.pop("signature_hex", None)
    return value


def discovery_sign_bytes(record: Mapping[str, Any]) -> bytes:
    return stable_json_bytes(_unsigned(record))


def sign_discovery_record(record: Mapping[str, Any], private_key_hex: str) -> dict[str, Any]:
    value = _unsigned(record)
    value["signature_hex"] = sign_ed25519(private_key_hex, discovery_sign_bytes(value))
    return value


class SignedPeerDiscoveryStore:
    """Retains only the latest valid record from each independently pinned authority."""

    MAX_PEERS_PER_RECORD = 100
    MAX_AUTHORITIES = 32
    MAX_RECORD_BYTES = 256 * 1024
    MAX_LIFETIME_SECONDS = 30 * 24 * 60 * 60
    MAX_CLOCK_SKEW_SECONDS = 10 * 60

    def __init__(
        self,
        root: str | Path,
        *,
        chain_id: str,
        trust_anchors: Mapping[str, str],
        clock: Callable[[], float] = time.time,
        allow_private_addresses: bool = False,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / "signed-peer-discovery.json"
        self.chain_id = self._component(chain_id, "chain_id")
        self.clock = clock
        self.allow_private_addresses = bool(allow_private_addresses)
        self._lock = threading.RLock()
        anchors = {self._component(key, "authority_id"): str(value).strip().lower()
                   for key, value in dict(trust_anchors or {}).items()}
        if len(anchors) > self.MAX_AUTHORITIES:
            raise PeerDiscoveryError("discovery_trust_anchor_limit_exceeded")
        for public_key in anchors.values():
            if not re.fullmatch(r"[0-9a-f]{64}", public_key):
                raise PeerDiscoveryError("discovery_trust_anchor_invalid")
        self.trust_anchors = anchors

    def import_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        encoded = stable_json_bytes(dict(record or {}))
        if len(encoded) > self.MAX_RECORD_BYTES:
            raise PeerDiscoveryError("discovery_record_too_large")
        validated = self._validate(record)
        authority = validated["authority_id"]
        with self._lock:
            state = self._state()
            previous = dict(state["records"].get(authority) or {})
            previous_sequence = int(previous.get("sequence") or 0)
            sequence = int(validated["sequence"])
            if sequence < previous_sequence:
                raise PeerDiscoveryError("discovery_record_replay")
            if sequence == previous_sequence:
                if previous and sha256(stable_json_bytes(previous)).hexdigest() == sha256(stable_json_bytes(validated)).hexdigest():
                    return {"accepted": False, "duplicate": True, "record": deepcopy(previous)}
                raise PeerDiscoveryError("discovery_sequence_equivocation")
            state["records"][authority] = validated
            self._write(state)
        return {"accepted": True, "duplicate": False, "record": deepcopy(validated)}

    def active_records(self) -> list[dict[str, Any]]:
        now = int(self.clock())
        records = [deepcopy(value) for value in self._state()["records"].values()
                   if int(value.get("expires_at") or 0) > now]
        records.sort(key=lambda value: (value["authority_id"], -int(value["sequence"])))
        return records

    def active_peers(self) -> list[dict[str, Any]]:
        by_node: dict[str, dict[str, Any]] = {}
        for record in self.active_records():
            for peer in record["peers"]:
                current = by_node.get(peer["node_id"])
                if current and int(current["discovery_sequence"]) > int(record["sequence"]):
                    continue
                by_node[peer["node_id"]] = {
                    **deepcopy(peer),
                    "discovery_authority_id": record["authority_id"],
                    "discovery_sequence": record["sequence"],
                    "discovery_expires_at": record["expires_at"],
                }
        return sorted(by_node.values(), key=lambda value: value["node_id"])

    def status(self) -> dict[str, Any]:
        state = self._state()
        active = self.active_records()
        return {
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.chain_id,
            "trusted_authority_count": len(self.trust_anchors),
            "retained_record_count": len(state["records"]),
            "active_record_count": len(active),
            "active_peer_count": len(self.active_peers()),
            "trust_anchor_required": True,
            "unsigned_discovery_accepted": False,
        }

    def _validate(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        value = deepcopy(dict(raw or {}))
        if value.get("schema_version") != SCHEMA_VERSION:
            raise PeerDiscoveryError("discovery_schema_unsupported")
        if str(value.get("chain_id") or "") != self.chain_id:
            raise PeerDiscoveryError("discovery_chain_mismatch")
        authority = self._component(str(value.get("authority_id") or ""), "authority_id")
        public_key = self.trust_anchors.get(authority)
        if not public_key:
            raise PeerDiscoveryError("discovery_authority_not_trusted")
        try:
            sequence = int(value.get("sequence"))
            issued_at = int(value.get("issued_at"))
            expires_at = int(value.get("expires_at"))
        except Exception:
            raise PeerDiscoveryError("discovery_time_or_sequence_invalid") from None
        now = int(self.clock())
        if sequence < 1:
            raise PeerDiscoveryError("discovery_sequence_invalid")
        if issued_at > now + self.MAX_CLOCK_SKEW_SECONDS:
            raise PeerDiscoveryError("discovery_record_not_yet_valid")
        if expires_at <= now:
            raise PeerDiscoveryError("discovery_record_expired")
        if expires_at <= issued_at or expires_at - issued_at > self.MAX_LIFETIME_SECONDS:
            raise PeerDiscoveryError("discovery_lifetime_invalid")
        peers = value.get("peers")
        if not isinstance(peers, list) or not peers or len(peers) > self.MAX_PEERS_PER_RECORD:
            raise PeerDiscoveryError("discovery_peer_count_invalid")
        validated_peers = [self._peer(peer) for peer in peers]
        if len({peer["node_id"] for peer in validated_peers}) != len(validated_peers):
            raise PeerDiscoveryError("discovery_duplicate_node_id")
        signature = str(value.get("signature_hex") or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{128}", signature):
            raise PeerDiscoveryError("discovery_signature_invalid")
        canonical = {
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.chain_id,
            "authority_id": authority,
            "sequence": sequence,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "peers": validated_peers,
            "signature_hex": signature,
        }
        if not verify_ed25519(public_key, signature, discovery_sign_bytes(canonical)):
            raise PeerDiscoveryError("discovery_signature_invalid")
        return canonical

    def _peer(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise PeerDiscoveryError("discovery_peer_invalid")
        node_id = self._component(str(raw.get("node_id") or ""), "node_id")
        role = str(raw.get("role") or "light").strip().lower()
        if role not in ROLES:
            raise PeerDiscoveryError("discovery_peer_role_invalid")
        base_url = str(raw.get("base_url") or "").strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in ({"https", "http"} if self.allow_private_addresses else {"https"}):
            raise PeerDiscoveryError("discovery_peer_transport_invalid")
        if not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise PeerDiscoveryError("discovery_peer_url_invalid")
        if not self.allow_private_addresses:
            try:
                address = ipaddress.ip_address(parsed.hostname)
                if address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified:
                    raise PeerDiscoveryError("discovery_private_address_rejected")
            except ValueError:
                if parsed.hostname.lower() == "localhost" or "." not in parsed.hostname:
                    raise PeerDiscoveryError("discovery_private_address_rejected")
        pubkey = str(raw.get("pubkey_hex") or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", pubkey):
            raise PeerDiscoveryError("discovery_peer_pubkey_invalid")
        val_id = str(raw.get("val_id") or "").strip()
        if val_id:
            val_id = self._component(val_id, "val_id")
        peer = {"node_id": node_id, "base_url": base_url, "role": role,
                "val_id": val_id or None, "pubkey_hex": pubkey}
        if raw.get("relay_url") is not None:
            relay_url = str(raw.get("relay_url") or "").strip().rstrip("/")
            relay = urlparse(relay_url)
            if relay.scheme not in ({"https", "http"} if self.allow_private_addresses else {"https"}):
                raise PeerDiscoveryError("discovery_peer_relay_transport_invalid")
            if not relay.hostname or relay.username or relay.password or relay.path not in {"", "/"} or relay.query or relay.fragment:
                raise PeerDiscoveryError("discovery_peer_relay_url_invalid")
            if not self.allow_private_addresses:
                try:
                    address = ipaddress.ip_address(relay.hostname)
                    if address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified:
                        raise PeerDiscoveryError("discovery_private_relay_rejected")
                except ValueError:
                    if relay.hostname.lower() == "localhost" or "." not in relay.hostname:
                        raise PeerDiscoveryError("discovery_private_relay_rejected")
            peer["relay_url"] = relay_url
        return peer

    def _state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "chain_id": self.chain_id, "records": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PeerDiscoveryError("discovery_state_unreadable") from exc
        if value.get("schema_version") != SCHEMA_VERSION or value.get("chain_id") != self.chain_id or not isinstance(value.get("records"), dict):
            raise PeerDiscoveryError("discovery_state_invalid")
        return value

    def _write(self, state: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)

    @staticmethod
    def _component(value: str, field: str) -> str:
        clean = str(value or "").strip()
        if not clean or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", clean):
            raise PeerDiscoveryError(f"discovery_{field}_invalid")
        return clean


def trust_anchors_from_env() -> dict[str, str]:
    raw = str(os.getenv("GLYPHCHAIN_DISCOVERY_TRUST_ANCHORS_JSON", "") or "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        raise PeerDiscoveryError("discovery_trust_anchors_json_invalid") from None
    if not isinstance(value, dict):
        raise PeerDiscoveryError("discovery_trust_anchors_json_invalid")
    return {str(key): str(public_key) for key, public_key in value.items()}
