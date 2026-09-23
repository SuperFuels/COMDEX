"""Persisted customer-owned execution policy for AION Flow."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity, IdentityStore


class AionFlowPolicyStore:
    def __init__(self, root: str | Path = ".runtime/aion_flow/policies") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.identity = IdentityStore(self.root / "policy-identity").load_or_create()

    def effective(self, workspace_id: str) -> dict[str, Any]:
        path = self._path(workspace_id)
        if not path.exists():
            return self._write(self._default(workspace_id))
        value = json.loads(path.read_text(encoding="utf-8"))
        if not self._verify(value):
            raise PermissionError("aion_flow_policy_signature_invalid")
        return value

    def configure(self, workspace_id: str, policy: Mapping[str, Any], *, changed_by: str, expected_revision: int) -> dict[str, Any]:
        current = self.effective(workspace_id)
        if int(current.get("revision") or 0) != int(expected_revision):
            raise RuntimeError("aion_flow_policy_revision_conflict")
        allowed = {
            "allowed_purposes", "allowed_destinations", "allowed_residencies",
            "maximum_external_classification", "max_cost_per_run", "max_loop_iterations",
            "external_writes_allowed", "approval_before_external_write", "dry_run_first",
        }
        clean = {key: value for key, value in dict(policy).items() if key in allowed}
        merged = {**self._default(workspace_id), **clean, "revision": int(current["revision"]) + 1, "changed_by": str(changed_by), "changed_at": utc_now_iso()}
        return self._write(merged)

    def governance_policy(self, workspace_id: str) -> dict[str, Any]:
        stored = self.effective(workspace_id)
        return {
            key: value for key, value in stored.items()
            if key not in {"signature", "policy_hash", "signer_public_key", "schema_version", "workspace_id", "revision", "changed_by", "changed_at"}
        } | {"allowed_roles": ["canonical_authority"], "policy_receipt": {"revision": stored["revision"], "policy_hash": stored["policy_hash"], "signature": stored["signature"]}}

    def _default(self, workspace_id: str) -> dict[str, Any]:
        return {
            "schema_version": "aion.flow.execution-policy.v1", "workspace_id": str(workspace_id),
            "revision": 1, "changed_by": "mother_brain_safe_default", "changed_at": utc_now_iso(),
            "allowed_purposes": ["workflow_execution", "evaluation", "template_management"],
            "allowed_destinations": ["local"], "allowed_residencies": ["local"],
            "maximum_external_classification": "internal", "max_cost_per_run": 0.0,
            "max_loop_iterations": 3, "external_writes_allowed": False,
            "approval_before_external_write": True, "dry_run_first": True,
        }

    def _write(self, value: Mapping[str, Any]) -> dict[str, Any]:
        unsigned = {key: item for key, item in dict(value).items() if key not in {"signature", "policy_hash", "signer_public_key"}}
        unsigned["signer_public_key"] = self.identity.public_key_b64
        unsigned["policy_hash"] = canonical_hash(unsigned)
        signed = {**unsigned, "signature": self.identity.sign(canonical_bytes(unsigned))}
        path = self._path(str(signed["workspace_id"])); temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600); os.replace(temporary, path)
        return signed

    @staticmethod
    def _verify(value: Mapping[str, Any]) -> bool:
        unsigned = {key: item for key, item in dict(value).items() if key != "signature"}
        expected = canonical_hash({key: item for key, item in unsigned.items() if key != "policy_hash"})
        return expected == value.get("policy_hash") and DeviceIdentity.verify(str(value.get("signer_public_key") or ""), canonical_bytes(unsigned), str(value.get("signature") or ""))

    def _path(self, workspace_id: str) -> Path:
        safe = "".join(character for character in str(workspace_id) if character.isalnum() or character in {"-", "_", "."})
        if not safe:
            raise ValueError("workspace_id_required")
        return self.root / f"{safe}.json"
