from __future__ import annotations

import base64
import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .identity import DeviceIdentity


class HouseholdIdentityRegistry:
    """Local persona routing without putting private credentials on shared nodes."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "household" / "personas.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "aion.household.personas.v1", "personas": [], "updated_at": utc_now_iso()}

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    def ensure_local_persona(self, *, mother_id: str, display_name: str = "Local owner") -> Dict[str, Any]:
        key = canonical_hash({"mother_id": mother_id, "kind": "local_owner"})[:24]
        with self._lock:
            state = self._load()
            existing = next((item for item in state["personas"] if item.get("routing_key") == key), None)
            if existing:
                return dict(existing)
            persona = {
                "persona_id": f"persona_{uuid4().hex}",
                "display_name": " ".join(display_name.split()).strip()[:80] or "Local owner",
                "routing_key": key,
                "mother_id": mother_id,
                "private_phone_binding": None,
                "service_bindings": {},
                "shared_screen_policy": "private_by_default",
                "created_at": utc_now_iso(),
            }
            state["personas"].append(persona)
            self._save(state)
            return dict(persona)

    def ensure_private_identity_persona(
        self, *, private_persona_id: str, mother_id: str, display_name: str,
        allow_legacy_adoption: bool = False,
    ) -> Dict[str, Any]:
        """Resolve one production private identity to one isolated service persona.

        The first private owner may adopt the pre-existing local-owner record so
        earlier proposals and authorized service bindings are preserved. Every
        additional private identity receives a separate record and bindings.
        """
        if not re.fullmatch(r"persona_[A-Za-z0-9]+", str(private_persona_id)):
            raise ValueError("Private persona identity is invalid")
        clean_name = " ".join(str(display_name).split()).strip()[:80] or "Local owner"
        with self._lock:
            state = self._load()
            existing = next(
                (item for item in state["personas"] if item.get("private_persona_id") == private_persona_id),
                None,
            )
            if existing:
                if existing.get("mother_id") != mother_id:
                    raise PermissionError("That private identity belongs to a different mother")
                return dict(existing)
            adoptable = next(
                (
                    item for item in state["personas"]
                    if allow_legacy_adoption
                    and item.get("mother_id") == mother_id
                    and not item.get("private_persona_id")
                    and item.get("routing_key") == canonical_hash({"mother_id": mother_id, "kind": "local_owner"})[:24]
                ),
                None,
            )
            if adoptable is not None:
                adoptable["private_persona_id"] = private_persona_id
                adoptable["display_name"] = clean_name
                adoptable["identity_source"] = "production_private_identity"
                self._save(state)
                return dict(adoptable)
            persona = {
                "persona_id": f"persona_{uuid4().hex}",
                "private_persona_id": private_persona_id,
                "display_name": clean_name,
                "routing_key": canonical_hash({
                    "mother_id": mother_id, "private_persona_id": private_persona_id,
                })[:24],
                "mother_id": mother_id,
                "private_phone_binding": None,
                "service_bindings": {},
                "shared_screen_policy": "private_by_default",
                "identity_source": "production_private_identity",
                "created_at": utc_now_iso(),
            }
            state["personas"].append(persona)
            self._save(state)
            return dict(persona)

    def bind_service(self, persona_id: str, service: str, credential_reference: str) -> Dict[str, Any]:
        service = re.sub(r"[^a-z0-9_]+", "", service.lower())[:40]
        if service not in {"calendar", "email", "messaging", "shopping", "booking", "maps", "music"}:
            raise ValueError("Unsupported household service binding")
        if not re.fullmatch(r"(?:vault|provider)://[A-Za-z0-9._:/-]{3,180}", credential_reference):
            raise ValueError("Only an opaque vault or provider credential reference may be stored")
        with self._lock:
            state = self._load()
            persona = next((item for item in state["personas"] if item.get("persona_id") == persona_id), None)
            if persona is None:
                raise KeyError("Household persona was not found")
            persona.setdefault("service_bindings", {})[service] = credential_reference
            self._save(state)
            return {"persona_id": persona_id, "service": service, "bound": True}

    def get(self, persona_id: str) -> Dict[str, Any] | None:
        return next((dict(item) for item in self._load()["personas"] if item.get("persona_id") == persona_id), None)

    def snapshot(self, *, include_private_bindings: bool = False) -> Dict[str, Any]:
        state = self._load()
        personas = []
        for item in state["personas"]:
            public = {
                "persona_id": item.get("persona_id"),
                "display_name": item.get("display_name"),
                "mother_id": item.get("mother_id"),
                "shared_screen_policy": item.get("shared_screen_policy"),
                "bound_services": sorted((item.get("service_bindings") or {}).keys()),
            }
            if include_private_bindings:
                public["service_bindings"] = dict(item.get("service_bindings") or {})
            personas.append(public)
        return {"schema_version": state["schema_version"], "personas": personas, "count": len(personas), "updated_at": state.get("updated_at")}


class UniversalNodeAuthority:
    """One installed device node serving multiple explicitly trusted mothers."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path, *, node_id: str, identity: DeviceIdentity) -> None:
        self.path = Path(runtime_dir) / "universal_node" / "authority.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.node_id = node_id
        self.identity = identity

    def _initial(self) -> Dict[str, Any]:
        return {"schema_version": "aion.universal-node.v1", "node_id": self.node_id, "trusted_mothers": [], "pending_handshakes": [], "leases": [], "used_nonces": [], "updated_at": utc_now_iso()}

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) and value.get("node_id") == self.node_id else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    def enroll_mother(self, *, mother_id: str, public_key: str, persona_id: str, approved_by: str) -> Dict[str, Any]:
        if not mother_id.startswith("node_") or not re.fullmatch(r"(?:persona|principal)_[a-zA-Z0-9]+", persona_id) or not approved_by:
            raise ValueError("Invalid universal-node mother enrollment")
        try:
            if len(base64.b64decode(public_key, validate=True)) != 32:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Mother public key must be a valid Ed25519 key") from None
        with self._lock:
            state = self._load()
            mothers = [item for item in state["trusted_mothers"] if item.get("mother_id") != mother_id]
            record = {"mother_id": mother_id, "public_key": public_key, "persona_id": persona_id, "status": "trusted", "approved_by": approved_by[:100], "enrolled_at": utc_now_iso()}
            mothers.append(record)
            state["trusted_mothers"] = mothers
            self._save(state)
            return {key: value for key, value in record.items() if key != "public_key"}

    def begin_handshake(self, *, mother_id: str, public_key: str) -> Dict[str, Any]:
        """Resume known trust or mint a one-time, locally confirmed relationship."""
        if not mother_id.startswith("node_"):
            raise ValueError("Invalid mother node identity")
        try:
            if len(base64.b64decode(public_key, validate=True)) != 32:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Mother public key must be a valid Ed25519 key") from None
        with self._lock:
            state = self._load()
            known = next((item for item in state["trusted_mothers"] if item.get("mother_id") == mother_id and item.get("public_key") == public_key and item.get("status") == "trusted"), None)
            if known:
                return {"status": "recognized", "relationship_id": known.get("relationship_id"), "mother_id": mother_id, "node_id": self.node_id, "confirmation_required": False}
            now = datetime.now(timezone.utc)
            pending = [item for item in state.get("pending_handshakes", []) if datetime.fromisoformat(str(item["expires_at"]).replace("Z", "+00:00")) > now]
            existing = next((item for item in pending if item.get("mother_id") == mother_id and item.get("public_key") == public_key), None)
            if existing:
                state["pending_handshakes"] = pending
                self._save(state)
                return {"status": "confirmation_required", "handshake_id": existing["handshake_id"], "mother_id": mother_id, "node_id": self.node_id, "confirmation_required": True, "expires_at": existing["expires_at"]}
            code = f"{secrets.randbelow(1_000_000):06d}"
            payload = {
                "handshake_id": f"handshake_{uuid4().hex}",
                "mother_id": mother_id,
                "node_id": self.node_id,
                "mother_public_key": public_key,
                "nonce": secrets.token_urlsafe(24),
            }
            pending.append({
                **payload,
                "public_key": public_key,
                "code_hash": canonical_hash({"handshake_id": payload["handshake_id"], "code": code}),
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
                "created_at": utc_now_iso(),
            })
            state["pending_handshakes"] = pending[-31:]
            self._save(state)
            return {"status": "confirmation_required", "handshake_id": payload["handshake_id"], "mother_id": mother_id, "node_id": self.node_id, "confirmation_required": True, "confirmation_code": code, "challenge": payload, "expires_at": pending[-1]["expires_at"]}

    def complete_handshake(self, *, handshake_id: str, confirmation_code: str, mother_signature: str, approved_by: str) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            pending = next((item for item in state.get("pending_handshakes", []) if item.get("handshake_id") == handshake_id), None)
            if pending is None:
                raise KeyError("Universal-node handshake was not found")
            if datetime.fromisoformat(str(pending["expires_at"]).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                raise PermissionError("Universal-node handshake expired")
            if not secrets.compare_digest(str(pending["code_hash"]), canonical_hash({"handshake_id": handshake_id, "code": confirmation_code})):
                raise PermissionError("Universal-node confirmation code is invalid")
            challenge = {key: pending[key] for key in ("handshake_id", "mother_id", "node_id", "mother_public_key", "nonce")}
            if not DeviceIdentity.verify(str(pending["public_key"]), canonical_bytes(challenge), mother_signature):
                raise PermissionError("Mother did not prove possession of its identity key")
            relationship = {
                "relationship_id": f"relationship_{uuid4().hex}",
                "mother_id": pending["mother_id"],
                "public_key": pending["public_key"],
                "persona_id": f"principal_{canonical_hash(pending['public_key'])[:24]}",
                "status": "trusted",
                "approved_by": approved_by[:100],
                "enrolled_at": utc_now_iso(),
            }
            certificate = {key: value for key, value in relationship.items() if key != "public_key"}
            certificate["node_id"] = self.node_id
            certificate["node_public_key"] = self.identity.public_key_b64
            certificate["node_signature"] = self.identity.sign(canonical_bytes(certificate))
            state["trusted_mothers"] = [item for item in state["trusted_mothers"] if item.get("mother_id") != pending["mother_id"]] + [relationship]
            state["pending_handshakes"] = [item for item in state.get("pending_handshakes", []) if item.get("handshake_id") != handshake_id]
            self._save(state)
            return certificate

    def accept_lease_request(self, request: Dict[str, Any], signature: str) -> Dict[str, Any]:
        required = {"mother_id", "node_id", "persona_id", "capabilities", "nonce", "expires_at"}
        if set(request) != required or request.get("node_id") != self.node_id:
            raise ValueError("Invalid universal-node lease request")
        requested_capabilities = [str(item) for item in request.get("capabilities", [])]
        capabilities = sorted(set(requested_capabilities))
        if not capabilities or len(capabilities) > 32 or any(not re.fullmatch(r"[a-z0-9_.-]{3,100}", item) for item in capabilities):
            raise ValueError("Invalid requested capability scope")
        if requested_capabilities != capabilities:
            raise ValueError("Requested capabilities must be unique and canonically sorted")
        expires = datetime.fromisoformat(str(request["expires_at"]).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if expires <= now or expires > now + timedelta(hours=24):
            raise ValueError("Universal-node leases must expire within 24 hours")
        nonce = str(request["nonce"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", nonce):
            raise ValueError("Invalid lease nonce")
        with self._lock:
            state = self._load()
            mother = next((item for item in state["trusted_mothers"] if item.get("mother_id") == request["mother_id"] and item.get("status") == "trusted"), None)
            if mother is None or mother.get("persona_id") != request.get("persona_id"):
                raise PermissionError("That mother/persona binding is not trusted by this node")
            if nonce in state.get("used_nonces", []):
                raise PermissionError("Universal-node lease request replay detected")
            normalized = {**request, "capabilities": capabilities}
            if not DeviceIdentity.verify(str(mother["public_key"]), canonical_bytes(normalized), signature):
                raise PermissionError("Mother signature is invalid")
            lease = {
                "lease_id": f"lease_{uuid4().hex}",
                **normalized,
                "issued_at": utc_now_iso(),
                "issuer_node_id": self.node_id,
            }
            lease["payload_hash"] = canonical_hash(lease)
            lease["node_signature"] = self.identity.sign(canonical_bytes(lease))
            state["leases"] = list(state.get("leases") or [])[-127:] + [lease]
            state["used_nonces"] = list(state.get("used_nonces") or [])[-255:] + [nonce]
            self._save(state)
            return dict(lease)

    def snapshot(self) -> Dict[str, Any]:
        state = self._load()
        return {"schema_version": state["schema_version"], "node_id": self.node_id, "trusted_mothers": len([item for item in state["trusted_mothers"] if item.get("status") == "trusted"]), "pending_handshakes": len(state.get("pending_handshakes") or []), "issued_leases": len(state.get("leases") or []), "maximum_lease_hours": 24, "one_runtime_per_device": True, "new_mother_requires_local_confirmation": True, "updated_at": state.get("updated_at")}
