from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignVault
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


_BINDING_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{0,79}")
_SECRET_KEYS = re.compile(r"(?:password|passphrase|secret|api[_-]?key|access[_-]?token|private[_-]?key|authorization)", re.I)
_SECRET_VALUES = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+\S+)")


class AionFlowModelBindings:
    """Stable model bindings with separate metadata and credential authorities.

    Customer-visible binding metadata is business configuration and therefore
    belongs to the Business Vault in Guardian mode. Raw credentials never enter
    that record: they remain in the dedicated encrypted secrets store.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        workspace_id: str = "default",
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.root = Path(
            root
            or os.environ.get("TESSARIS_AION_FLOW_CREDENTIAL_STORE_PATH")
            or Path.home() / ".tessaris/security/aion-flow-model-bindings"
        ).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "model-bindings.json"
        self.vault = SovereignVault(self.root / "vault")
        self.vault.initialize()
        self.workspace_id = self._workspace_id(workspace_id)
        self.domain_store = domain_store
        if root is None and domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="aion-flow-model-binding-runtime",
            )

    def create(self, *, binding_id: str, provider: str, secret: str, label: str = "") -> Dict[str, Any]:
        clean_id = str(binding_id or "").strip().lower()
        if not _BINDING_ID.fullmatch(clean_id):
            raise ValueError("model_binding_id_invalid")
        if not str(provider or "").strip():
            raise ValueError("model_binding_provider_required")
        clean_secret = str(secret or "").strip()
        if not clean_secret:
            raise ValueError("model_binding_secret_required")
        if len(clean_secret) > 65536:
            raise ValueError("model_binding_secret_too_large")
        state = self._state()
        if clean_id in state["bindings"]:
            raise ValueError("model_binding_already_exists")
        vault_name = f"model.{clean_id}.{uuid4().hex}"
        self.vault.set_secret(vault_name, clean_secret)
        record = {
            "binding_id": clean_id,
            "reference": f"vault://model/{clean_id}",
            "provider": str(provider).strip().lower(),
            "label": str(label or provider).strip()[:100],
            "vault_name": vault_name,
            "status": "active",
            "revision": 1,
            "created_at": utc_now_iso(),
            "rotated_at": "",
            "revoked_at": "",
        }
        state["bindings"][clean_id] = record
        self._write(state)
        return self._public(record)

    def rotate(self, reference: str, *, secret: str) -> Dict[str, Any]:
        state, record = self._record(reference)
        if record["status"] != "active":
            raise PermissionError("active_model_binding_required")
        previous = record["vault_name"]
        replacement = f"model.{record['binding_id']}.{uuid4().hex}"
        self.vault.set_secret(replacement, secret)
        record.update({"vault_name": replacement, "revision": int(record["revision"]) + 1, "rotated_at": utc_now_iso()})
        self._write(state)
        self.vault.delete_secret(previous)
        return self._public(record)

    def revoke(self, reference: str) -> Dict[str, Any]:
        state, record = self._record(reference)
        if record["status"] != "revoked":
            self.vault.delete_secret(record["vault_name"])
            record.update({"status": "revoked", "revision": int(record["revision"]) + 1, "revoked_at": utc_now_iso()})
            self._write(state)
        return self._public(record)

    def resolve(self, reference: str) -> str:
        _state, record = self._record(reference)
        if record["status"] != "active":
            raise PermissionError("model_binding_revoked")
        secret = self.vault.get_secret(record["vault_name"])
        if not secret:
            raise PermissionError("model_binding_secret_unavailable")
        return secret

    def public_bindings(self, *, provider: str = "") -> Dict[str, Any]:
        state = self._state()
        values = [self._public(item) for item in state["bindings"].values()]
        if provider:
            values = [item for item in values if item["provider"] == provider.strip().lower()]
        return {
            "schema_version": "aion.flow.model_bindings.public.v1",
            "bindings": sorted(values, key=lambda item: item["binding_id"]),
            "raw_secrets_exposed": False,
        }

    @staticmethod
    def bounded_connectivity_test(registry: Any, adapter_id: str, *, timeout_seconds: float = 2.0) -> Dict[str, Any]:
        """Expose health metadata only; never return model-list bodies or credentials."""
        result = dict(registry.health(adapter_id, timeout_seconds=max(0.1, min(float(timeout_seconds), 5.0))))
        allowed = {key: result[key] for key in ("healthy", "status", "latency_ms", "error") if key in result}
        allowed.update({
            "adapter_id": str(adapter_id),
            "checked_at": utc_now_iso(),
            "response_body_exposed": False,
            "credentials_exposed": False,
        })
        allowed["health_hash"] = canonical_hash(allowed)
        return allowed

    @staticmethod
    def redact_for_canvas(value: Any) -> Any:
        """Defence in depth for autosave, preview, log, receipt and export paths."""
        if isinstance(value, Mapping):
            clean: Dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                if _SECRET_KEYS.search(name) and not name.endswith(("binding_ref", "binding_reference")):
                    clean[name] = "[REDACTED]"
                else:
                    clean[name] = AionFlowModelBindings.redact_for_canvas(item)
            return clean
        if isinstance(value, list):
            return [AionFlowModelBindings.redact_for_canvas(item) for item in value]
        if isinstance(value, tuple):
            return [AionFlowModelBindings.redact_for_canvas(item) for item in value]
        text = str(value) if isinstance(value, str) else value
        if isinstance(text, str) and _SECRET_VALUES.search(text):
            return "[REDACTED]"
        return value

    def _record(self, reference: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        prefix = "vault://model/"
        if not str(reference).startswith(prefix):
            raise ValueError("model_binding_reference_invalid")
        binding_id = str(reference)[len(prefix):]
        state = self._state()
        record = state["bindings"].get(binding_id)
        if not record:
            raise KeyError("model_binding_not_found")
        return state, record

    @staticmethod
    def _public(record: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            key: value for key, value in record.items()
            if key not in {"vault_name", "schema_version"}
        } | {"secret_exposed": False}

    def _state(self) -> Dict[str, Any]:
        if self.domain_store is not None:
            bindings: Dict[str, Any] = {}
            for item in self.domain_store.list(
                "train_agent.automations", workspace_id=self.workspace_id,
            ):
                entity_id = str(item.get("entity_id") or "")
                if not entity_id.startswith("aion_flow/model_binding/"):
                    continue
                record = dict(item["payload"])
                binding_id = str(record.get("binding_id") or "")
                if not _BINDING_ID.fullmatch(binding_id):
                    raise RuntimeError("model_binding_state_invalid")
                if record.get("schema_version") != "aion.flow.model_binding.v2":
                    raise RuntimeError("model_binding_state_invalid")
                bindings[binding_id] = record
            return {"schema_version": "aion.flow.model_bindings.v2", "bindings": bindings}
        if not self.state_path.exists():
            return {"schema_version": "aion.flow.model_bindings.v1", "bindings": {}}
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "aion.flow.model_bindings.v1" or not isinstance(value.get("bindings"), dict):
            raise RuntimeError("model_binding_state_invalid")
        return value

    def _write(self, state: Mapping[str, Any]) -> None:
        if self.domain_store is not None:
            for binding_id, raw_record in dict(state.get("bindings") or {}).items():
                if not _BINDING_ID.fullmatch(str(binding_id)):
                    raise RuntimeError("model_binding_state_invalid")
                record = dict(raw_record)
                record["schema_version"] = "aion.flow.model_binding.v2"
                entity_id = f"aion_flow/model_binding/{binding_id}"
                current = self.domain_store.get_optional(
                    "train_agent.automations",
                    workspace_id=self.workspace_id,
                    entity_id=entity_id,
                )
                self.domain_store.put(
                    "train_agent.automations",
                    workspace_id=self.workspace_id,
                    entity_id=entity_id,
                    payload=record,
                    expected_version=int(current["version"]) if current else None,
                    actor_id="aion-flow-model-binding-runtime",
                )
            return
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)

    @staticmethod
    def _workspace_id(value: str) -> str:
        clean = str(value or "").strip()
        if not clean or len(clean) > 160 or any(ord(character) < 32 for character in clean):
            raise ValueError("workspace_id_invalid")
        return clean
