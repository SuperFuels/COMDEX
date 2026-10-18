from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .private_identity import ProductionPrivateIdentity, configured_private_identity


class PersonaGoogleOAuth:
    """Google installed-app PKCE flow with opaque persona-bound vault references."""

    _lock = threading.RLock()
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SERVICE_SCOPES = {
        "calendar": {
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.events.freebusy",
        },
        "email_send": {"https://www.googleapis.com/auth/gmail.send"},
        "email_read": {"https://www.googleapis.com/auth/gmail.readonly"},
    }

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        identities: ProductionPrivateIdentity | None = None,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "provider_accounts"; self.path = self.root / "google.json"
        self.domain_store = domain_store
        self.workspace_id = str(workspace_id or "").strip()
        if self.domain_store is None:
            self.root.mkdir(parents=True, exist_ok=True)
        elif not self.workspace_id:
            raise ValueError("aion_fabric_google_oauth_workspace_required")
        self.identities = identities or configured_private_identity(runtime_dir)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "pilot.google-oauth.v1", "pending": [], "bindings": [], "revocations": []}

    def _read(self) -> Dict[str, Any]:
        if self.domain_store is not None:
            result = self.domain_store.get_optional(
                "security.records",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.google_oauth",
            )
            return dict(result["payload"]) if result else self._initial()
        if not self.path.exists(): return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8")); return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError): return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        if self.domain_store is not None:
            existing = self.domain_store.get_optional(
                "security.records",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.google_oauth",
            )
            self.domain_store.put(
                "security.records",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.google_oauth",
                payload=state,
                expected_version=int(existing["version"]) if existing else None,
            )
            return
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state)); os.chmod(temporary, 0o600); os.replace(temporary, self.path)

    def _known(self, persona_id: str) -> None:
        if not any(item.get("persona_id") == persona_id and item.get("status") == "active" for item in self.identities.snapshot().get("profiles", [])):
            raise PermissionError("A production private identity is required")

    def begin(self, *, persona_id: str, services: list[str], client_id: str, redirect_uri: str) -> Dict[str, Any]:
        self._known(persona_id)
        selected = sorted(set(str(item) for item in services))
        if not selected or any(item not in self.SERVICE_SCOPES for item in selected): raise ValueError("Unsupported Google service scope")
        if not client_id.endswith(".apps.googleusercontent.com"): raise ValueError("A registered Google OAuth client ID is required")
        if not (redirect_uri.startswith("http://127.0.0.1:") or redirect_uri.startswith("https://")): raise ValueError("Use a registered HTTPS or loopback redirect URI")
        verifier = secrets.token_urlsafe(64)[:96]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        state_token = secrets.token_urlsafe(32); scopes = sorted({scope for service in selected for scope in self.SERVICE_SCOPES[service]})
        pending = {
            "authorization_id": f"google_auth_{uuid4().hex}", "persona_id": persona_id,
            "services": selected, "scopes": scopes, "client_id": client_id, "redirect_uri": redirect_uri,
            "state_hash": canonical_hash(state_token), "code_verifier": verifier,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(), "created_at": utc_now_iso(),
        }
        query = urllib.parse.urlencode({
            "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": " ".join(scopes), "state": state_token, "code_challenge": challenge,
            "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent",
        })
        with self._lock:
            stored = self._read(); stored["pending"] = [item for item in stored["pending"] if datetime.fromisoformat(item["expires_at"]) > datetime.now(timezone.utc)][-19:] + [pending]; self._write(stored)
        return {"authorization_id": pending["authorization_id"], "authorization_url": f"{self.AUTH_URL}?{query}", "state": state_token, "services": selected, "scopes": scopes, "expires_at": pending["expires_at"], "system_browser_required": True, "embedded_browser_forbidden": True}

    @staticmethod
    def exchange_code(pending: Dict[str, Any], code: str) -> Dict[str, Any]:
        data = urllib.parse.urlencode({"client_id": pending["client_id"], "code": code, "code_verifier": pending["code_verifier"], "redirect_uri": pending["redirect_uri"], "grant_type": "authorization_code"}).encode("ascii")
        request = urllib.request.Request(PersonaGoogleOAuth.TOKEN_URL, data=data, headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(256_001)
        if len(body) > 256_000: raise RuntimeError("Google token response exceeded its safety limit")
        value = json.loads(body)
        if not isinstance(value, dict): raise RuntimeError("Google token response was invalid")
        return value

    def complete(
        self, *, authorization_id: str, state_token: str, code: str,
        token_exchange: Callable[[Dict[str, Any], str], Dict[str, Any]] | None = None,
        vault_store: Callable[[str, Dict[str, Any]], str],
    ) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); pending = next((item for item in state["pending"] if item.get("authorization_id") == authorization_id), None)
            if pending is None: raise KeyError("Google authorization request was not found")
            if datetime.fromisoformat(pending["expires_at"]) <= datetime.now(timezone.utc): raise PermissionError("Google authorization request expired")
            if not secrets.compare_digest(str(pending["state_hash"]), canonical_hash(state_token)): raise PermissionError("Google OAuth state validation failed")
            tokens = (token_exchange or self.exchange_code)(dict(pending), str(code))
            granted = set(str(tokens.get("scope") or "").split())
            required = set(pending["scopes"])
            if not required.issubset(granted): raise PermissionError("Google did not grant every reviewed scope")
            if not tokens.get("access_token") or not tokens.get("refresh_token"): raise RuntimeError("Google did not return durable authorized tokens")
            secret_payload = {key: tokens[key] for key in ("access_token", "refresh_token", "expires_in", "token_type") if key in tokens}
            reference = str(vault_store(str(pending["persona_id"]), secret_payload) or "")
            if not reference.startswith("vault://"): raise RuntimeError("OAuth tokens must be stored in an authorized secret vault")
            binding = {
                "binding_id": f"google_binding_{uuid4().hex}", "persona_id": pending["persona_id"],
                "services": pending["services"], "scopes": pending["scopes"], "vault_reference": reference,
                "provider": "google", "status": "connected", "connected_at": utc_now_iso(),
                "raw_tokens_retained_in_fabric": False,
            }
            state["bindings"] = [item for item in state["bindings"] if not (item.get("persona_id") == pending["persona_id"] and set(item.get("services") or []) & set(pending["services"]))] + [binding]
            state["pending"] = [item for item in state["pending"] if item.get("authorization_id") != authorization_id]
            self._write(state); return {key: value for key, value in binding.items() if key != "vault_reference"}

    def revoke(self, *, persona_id: str, binding_id: str, vault_revoke: Callable[[str], None]) -> Dict[str, Any]:
        self._known(persona_id)
        with self._lock:
            state = self._read(); binding = next((item for item in state["bindings"] if item.get("binding_id") == binding_id and item.get("persona_id") == persona_id), None)
            if binding is None: raise KeyError("Google account binding was not found")
            vault_revoke(str(binding["vault_reference"])); binding["status"] = "revoked"; binding["revoked_at"] = utc_now_iso()
            receipt = {"revocation_id": f"google_revocation_{uuid4().hex}", "binding_id": binding_id, "persona_id": persona_id, "created_at": utc_now_iso()}; state["revocations"].append(receipt); self._write(state); return receipt

    def snapshot(self, *, persona_id: str) -> Dict[str, Any]:
        self._known(persona_id); state = self._read()
        return {"bindings": [{key: value for key, value in item.items() if key != "vault_reference"} for item in state["bindings"] if item.get("persona_id") == persona_id], "raw_tokens_exposed": False}

    def authorized_binding(self, *, persona_id: str, service: str) -> Dict[str, Any]:
        """Return one mother-private binding for an adapter, never for a client projection."""
        self._known(persona_id)
        if service not in self.SERVICE_SCOPES:
            raise ValueError("Unsupported Google service scope")
        binding = next(
            (
                item for item in reversed(self._read().get("bindings", []))
                if item.get("persona_id") == persona_id
                and item.get("status") == "connected"
                and service in set(item.get("services") or [])
            ),
            None,
        )
        if binding is None:
            raise PermissionError("This person has not authorized that Google service")
        reference = str(binding.get("vault_reference") or "")
        if not reference.startswith("vault://"):
            raise RuntimeError("The Google authorization is not stored in the protected vault")
        return dict(binding)


def configured_google_oauth(
    runtime_dir: str | Path,
    *,
    identities: ProductionPrivateIdentity | None = None,
) -> PersonaGoogleOAuth:
    """Protect OAuth workflow metadata while raw tokens remain in key custody."""

    runtime_path = Path(runtime_dir)
    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        workspace_id = str(os.environ.get("TESSARIS_BUSINESS_STABLE_ID") or "").strip()
        if not workspace_id:
            raise RuntimeError("aion_fabric_google_oauth_workspace_required")
        domains = VaultDomainStore(runtime.guardian, actor_id="aion-fabric-google-oauth")
        selected = PersonaGoogleOAuth(
            runtime_path,
            identities=identities,
            domain_store=domains,
            workspace_id=workspace_id,
        )
        source = runtime_path / "provider_accounts" / "google.json"
        if source.exists() and domains.get_optional(
            "security.records",
            workspace_id=workspace_id,
            entity_id="aion_fabric.google_oauth",
        ) is None:
            state = PersonaGoogleOAuth(runtime_path, identities=identities)._read()
            selected._write(state)
            if selected._read() != state or not source.exists():
                raise RuntimeError("aion_fabric_google_oauth_migration_verification_failed")
            from hashlib import sha256

            source_hash = sha256(source.read_bytes()).hexdigest()
            domains.put(
                "security.audit",
                workspace_id=workspace_id,
                entity_id=f"aion_fabric.google_oauth_migration.{source_hash}",
                payload={
                    "schema_version": "aion.google-oauth-migration.v1",
                    "source_sha256": source_hash,
                    "source_retained": True,
                    "copied_and_verified": True,
                    "completed_at": utc_now_iso(),
                    "raw_provider_tokens_copied": False,
                },
            )
        return selected
    mode = str(os.environ.get("TESSARIS_RUNTIME_MODE") or "development").lower()
    if mode in {"production", "prod"}:
        raise RuntimeError("aion_fabric_guardian_google_oauth_required_in_production")
    return PersonaGoogleOAuth(runtime_path, identities=identities)
