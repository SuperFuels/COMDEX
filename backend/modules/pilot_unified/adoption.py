from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


ADOPTION_VERSION = "pilot.trusted-network.v1"
RELATIONSHIPS = frozenset({"household", "family", "friend", "professional"})
INVITATION_KINDS = frozenset({"contact", "employer", "client", "boardroom"})
WORKSPACE_ROLES = frozenset({"participant", "reviewer", "approver", "administrator"})
_LABEL = re.compile(r"^[^<>\x00-\x1f]{1,100}$")


class TrustedNetworkAuthority:
    """Consent-led relationship and useful-request invitation authority."""

    def __init__(self, runtime_dir: str | Path, *, mother_identity: DeviceIdentity) -> None:
        self.root = Path(runtime_dir) / "pilot_trusted_network"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.json"
        self.discovery_key_path = self.root / "discovery.key"
        self.identity = mother_identity
        self.discovery_key = self._key()

    def _key(self) -> bytes:
        if self.discovery_key_path.exists():
            return self.discovery_key_path.read_bytes()
        key = secrets.token_bytes(32)
        self.discovery_key_path.write_bytes(key)
        os.chmod(self.discovery_key_path, 0o600)
        return key

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": ADOPTION_VERSION, "invitations": [], "relationships": [], "events": [], "revocations": []}
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema_version") != ADOPTION_VERSION:
            raise RuntimeError("Trusted network state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def invite(
        self, *, sender_persona_id: str, sender_display_name: str, recipient_hint: str,
        relationship: str, exact_request: dict[str, Any], kind: str = "contact",
        workspace_ref: str | None = None, workspace_role: str | None = None,
    ) -> dict[str, Any]:
        if relationship not in RELATIONSHIPS or kind not in INVITATION_KINDS:
            raise ValueError("Invitation scope is unsupported")
        if not _LABEL.fullmatch(sender_display_name) or not isinstance(exact_request, dict) or not exact_request:
            raise ValueError("Invitation must have an unambiguous sender and useful request")
        if kind != "contact" and (not workspace_ref or workspace_role not in WORKSPACE_ROLES):
            raise ValueError("Workspace invitation requires an exact role and workspace")
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        private = {
            "recipient_hint_hash": canonical_hash({"recipient_hint": recipient_hint.strip().casefold()}),
            "exact_request": exact_request,
        }
        payload = {
            "schema_version": "pilot.useful-invitation.v1", "invitation_id": f"invite_{uuid4().hex}",
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "sender_persona_id": sender_persona_id, "sender_display_name": sender_display_name,
            "relationship": relationship, "kind": kind, "workspace_ref": workspace_ref,
            "workspace_role": workspace_role, "request_kind": str(exact_request.get("kind") or "request")[:60],
            "request_summary": str(exact_request.get("summary") or "A useful Pilot request")[:240],
            "request_hash": canonical_hash(exact_request), "status": "pending",
            "created_at": now.isoformat(), "expires_at": (now + timedelta(days=7)).isoformat(),
        }
        record = {**payload, "private": private, "signature": self.identity.sign(canonical_bytes(payload))}
        state = self._read()
        state["invitations"].append(record)
        state["events"].append({"type": "invitation_created", "kind": kind, "recorded_at": payload["created_at"]})
        self._write(state)
        return {"token": token, **{key: payload[key] for key in payload if key not in {"token_hash"}}}

    def inspect(self, token: str) -> dict[str, Any]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        state = self._read()
        record = next((item for item in state["invitations"] if item["token_hash"] == token_hash), None)
        if not record or record["status"] != "pending" or datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
            raise PermissionError("Invitation is unavailable")
        self._verify_invitation(record)
        return {key: record[key] for key in ("invitation_id", "sender_display_name", "relationship", "kind", "workspace_ref", "workspace_role", "request_kind", "request_summary", "request_hash", "expires_at", "status")}

    def _verify_invitation(self, record: dict[str, Any]) -> None:
        payload = {key: value for key, value in record.items() if key not in {"private", "signature", "accepted_by", "accepted_at"}}
        if not DeviceIdentity.verify(self.identity.public_key_b64, canonical_bytes(payload), str(record.get("signature") or "")):
            raise PermissionError("Invitation signature is invalid")
        if canonical_hash(record["private"]["exact_request"]) != record["request_hash"]:
            raise PermissionError("Invitation request no longer matches its signed scope")

    def accept(self, *, token: str, recipient_persona_id: str, recipient_hint: str) -> dict[str, Any]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        state = self._read()
        record = next((item for item in state["invitations"] if item["token_hash"] == token_hash), None)
        if not record or record["status"] != "pending":
            raise PermissionError("Invitation is unavailable")
        self._verify_invitation(record)
        if record["private"]["recipient_hint_hash"] != canonical_hash({"recipient_hint": recipient_hint.strip().casefold()}):
            raise PermissionError("Invitation was intended for another recipient route")
        if datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
            raise PermissionError("Invitation has expired")
        relationship = {
            "relationship_id": f"relationship_{uuid4().hex}",
            "sender_persona_id": record["sender_persona_id"], "recipient_persona_id": recipient_persona_id,
            "scope": record["relationship"], "kind": record["kind"], "workspace_ref": record.get("workspace_ref"),
            "workspace_role": record.get("workspace_role"), "status": "active", "accepted_at": utc_now_iso(),
        }
        record["status"] = "accepted"
        record["accepted_by"] = recipient_persona_id
        record["accepted_at"] = relationship["accepted_at"]
        state["relationships"].append(relationship)
        state["events"].append({"type": "invitation_accepted", "kind": record["kind"], "recorded_at": relationship["accepted_at"]})
        self._write(state)
        claim_payload = {
            "schema_version": "pilot.relationship-claim.v1",
            "relationship": relationship,
            "issuer_public_key": self.identity.public_key_b64,
        }
        relationship_claim = {**claim_payload, "signature": self.identity.sign(canonical_bytes(claim_payload))}
        return {
            **relationship,
            "continued_request": dict(record["private"]["exact_request"]),
            "unrelated_sender_data_included": False,
            "relationship_claim": relationship_claim,
        }

    def import_relationship(self, claim: dict[str, Any], *, actor_persona_id: str) -> dict[str, Any]:
        """Import the signed bilateral relationship onto the other mother brain."""
        required = {"schema_version", "relationship", "issuer_public_key", "signature"}
        if set(claim) != required or claim.get("schema_version") != "pilot.relationship-claim.v1":
            raise ValueError("Pilot relationship claim is malformed")
        payload = {key: claim[key] for key in required if key != "signature"}
        if not DeviceIdentity.verify(str(claim["issuer_public_key"]), canonical_bytes(payload), str(claim["signature"])):
            raise PermissionError("Pilot relationship claim signature is invalid")
        relationship = dict(claim["relationship"])
        if actor_persona_id not in {relationship.get("sender_persona_id"), relationship.get("recipient_persona_id")}:
            raise PermissionError("This relationship does not include the active person")
        if relationship.get("status") != "active" or relationship.get("scope") not in RELATIONSHIPS or relationship.get("kind") not in INVITATION_KINDS:
            raise PermissionError("Pilot relationship claim is not active or supported")
        state = self._read()
        existing = next((item for item in state["relationships"] if item.get("relationship_id") == relationship.get("relationship_id")), None)
        if existing:
            if canonical_hash(existing) != canonical_hash(relationship):
                raise PermissionError("That relationship identifier already has different scope")
            return dict(existing)
        state["relationships"].append(relationship)
        state["events"].append({"type": "relationship_imported", "kind": relationship["kind"], "recorded_at": utc_now_iso()})
        self._write(state)
        return dict(relationship)

    def discovery_tokens(self, *, contacts: list[str], consent: bool, epoch: str) -> dict[str, Any]:
        if not consent:
            raise PermissionError("Contact discovery requires explicit consent")
        if len(contacts) > 5000:
            raise ValueError("Address-book discovery exceeds the supported bound")
        tokens = []
        for value in contacts:
            normal = re.sub(r"\s+", "", value).casefold()
            if "@" not in normal and not re.fullmatch(r"\+?[0-9]{7,20}", normal):
                continue
            tokens.append(hmac.new(self.discovery_key, f"{epoch}:{normal}".encode(), hashlib.sha256).hexdigest())
        return {"schema_version": "pilot.contact-discovery.v1", "epoch": epoch, "tokens": sorted(set(tokens)), "readable_contacts_uploaded": False}

    def activation_metrics(self) -> dict[str, Any]:
        state = self._read()
        created = [item for item in state["events"] if item["type"] == "invitation_created"]
        accepted = [item for item in state["events"] if item["type"] == "invitation_accepted"]
        by_kind = {kind: {"created": sum(item["kind"] == kind for item in created), "accepted": sum(item["kind"] == kind for item in accepted)} for kind in INVITATION_KINDS}
        return {"schema_version": "pilot.activation-metrics.v1", "aggregate_only": True, "created": len(created), "accepted": len(accepted), "by_kind": by_kind}

    def revoke(self, *, relationship_id: str, actor_persona_id: str) -> dict[str, Any]:
        state = self._read()
        relationship = next((item for item in state["relationships"] if item["relationship_id"] == relationship_id), None)
        if not relationship or actor_persona_id not in {relationship["sender_persona_id"], relationship["recipient_persona_id"]}:
            raise PermissionError("That relationship cannot be revoked by this person")
        relationship["status"] = "revoked"
        relationship["revoked_at"] = utc_now_iso()
        tombstone = {"relationship_hash": canonical_hash(relationship), "revoked_at": relationship["revoked_at"], "future_contact_blocked": True}
        state["revocations"].append(tombstone)
        self._write(state)
        return tombstone

    def authorize_contact(self, *, relationship_id: str, sender_persona_id: str, recipient_persona_id: str) -> bool:
        state = self._read()
        relationship = next((item for item in state["relationships"] if item["relationship_id"] == relationship_id), None)
        if not relationship or relationship["status"] != "active":
            return False
        return {sender_persona_id, recipient_persona_id} == {relationship["sender_persona_id"], relationship["recipient_persona_id"]}

    def relationships_for(self, persona_id: str) -> list[dict[str, Any]]:
        """Return only active relationship routing facts relevant to one person."""
        state = self._read()
        visible = []
        for item in state["relationships"]:
            if item.get("status") != "active" or persona_id not in {item.get("sender_persona_id"), item.get("recipient_persona_id")}:
                continue
            peer_persona_id = item["recipient_persona_id"] if item["sender_persona_id"] == persona_id else item["sender_persona_id"]
            visible.append({
                "relationship_id": item["relationship_id"],
                "peer_persona_id": peer_persona_id,
                "scope": item["scope"],
                "kind": item["kind"],
                "workspace_ref": item.get("workspace_ref"),
                "workspace_role": item.get("workspace_role"),
                "accepted_at": item["accepted_at"],
                "status": "active",
            })
        return visible

    def export_person(self, persona_id: str) -> dict[str, Any]:
        state = self._read()
        relationships = [item for item in state["relationships"] if persona_id in {item["sender_persona_id"], item["recipient_persona_id"]}]
        invitations = [
            {key: item.get(key) for key in ("invitation_id", "sender_persona_id", "sender_display_name", "relationship", "kind", "workspace_ref", "workspace_role", "request_summary", "status", "created_at", "expires_at")}
            for item in state["invitations"] if item["sender_persona_id"] == persona_id or item.get("accepted_by") == persona_id
        ]
        export = {"schema_version": "pilot.network-export.v1", "persona_id": persona_id, "relationships": relationships, "invitations": invitations, "exported_at": utc_now_iso()}
        return {**export, "export_hash": canonical_hash(export)}

    def delete_person(self, persona_id: str) -> dict[str, Any]:
        state = self._read()
        affected = [item for item in state["relationships"] if persona_id in {item["sender_persona_id"], item["recipient_persona_id"]}]
        for item in affected:
            item["status"] = "revoked"
            item["revoked_at"] = utc_now_iso()
        state["invitations"] = [item for item in state["invitations"] if item["sender_persona_id"] != persona_id and item.get("accepted_by") != persona_id]
        self._write(state)
        return {"persona_id": persona_id, "deleted_private_invitations": True, "relationships_revoked": len(affected), "future_contact_blocked": True}
