"""Customer-approved, content-free diagnostic support handoff."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.content_free_diagnostics import append_diagnostic_event
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


DIAGNOSTIC_BUNDLE_SCHEMA = "tessaris.redacted-diagnostic-support-bundle.v1"
FORBIDDEN_KEYS = frozenset({
    "prompt", "document", "content", "path", "file_path", "secret", "token",
    "password", "api_key", "authorization", "customer_name", "email", "phone",
})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _private_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _assert_content_free(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"diagnostic_bundle_forbidden_field:{key}")
            _assert_content_free(item)
    elif isinstance(value, list):
        for item in value:
            _assert_content_free(item)


class DiagnosticSupportHandoffService:
    def __init__(
        self,
        runtime: BusinessVaultRuntime,
        *,
        diagnostics_root: str | Path,
        export_root: str | Path,
        actor_id: str = "diagnostic-support-handoff",
    ) -> None:
        self.runtime = runtime
        self.diagnostics_root = Path(diagnostics_root).resolve(strict=False)
        self.export_root = Path(export_root).resolve(strict=False)
        self.store = VaultDomainStore(runtime.guardian, actor_id=actor_id)
        self.actor_id = actor_id

    def exercise_failure(self, *, failure_id: str) -> dict[str, Any]:
        event = append_diagnostic_event(
            self.diagnostics_root / "events.jsonl",
            event_type="qualification_failure",
            code="local_component_unavailable",
            source_fingerprint=_hash({"component": "qualification-component"}),
            detail_fingerprint=_hash({"failure_id": failure_id, "class": "bounded-test"}),
            line=0,
        )
        return {
            "event_type": event["event_type"],
            "code": event["code"],
            "source_fingerprint": event["source_fingerprint"],
            "detail_fingerprint": event["detail_fingerprint"],
            "content_free": True,
        }

    def prepare(
        self,
        *,
        workspace_id: str,
        handoff_id: str,
        failure: Mapping[str, Any],
        customer_approved: bool,
        approved_by: str,
    ) -> dict[str, Any]:
        # Resolve the current customer-controlled desktop working projection so
        # the handoff is bound to this node state without copying its contents.
        self.store.list("business.working_state", workspace_id=workspace_id)
        existing = self.store.get_optional(
            "support.records", workspace_id=workspace_id, entity_id=handoff_id
        )
        if existing is not None:
            return {**dict(existing["payload"]), "idempotent_replay": True}
        manifest = {
            "schema_version": DIAGNOSTIC_BUNDLE_SCHEMA,
            "handoff_id": handoff_id,
            "workspace_fingerprint": _hash({"workspace_id": workspace_id}),
            "failure": dict(failure),
            "runtime": {
                "desktop_contract": "tessaris.desktop-backend.v1",
                "diagnostic_format": "content-free-fingerprints",
            },
            "redaction": {
                "prompts_excluded": True,
                "documents_excluded": True,
                "secrets_excluded": True,
                "raw_paths_excluded": True,
                "personal_data_excluded": True,
            },
            "generated_at": _now(),
        }
        manifest["manifest_sha256"] = _hash(manifest)
        _assert_content_free(manifest)
        preview = {
            "manifest_sha256": manifest["manifest_sha256"],
            "event_count": 1,
            "redaction": manifest["redaction"],
            "export_requires_customer_approval": True,
        }
        if not customer_approved or not str(approved_by or "").strip():
            return {
                "state": "awaiting_customer_approval",
                "preview": preview,
                "export_created": False,
                "customer_content_in_response": False,
            }
        export = {
            **manifest,
            "approval": {
                "approved": True,
                "approver_fingerprint": _hash({"approved_by": approved_by}),
                "approved_at": _now(),
                "scope": "this_redacted_manifest_only",
            },
        }
        export["bundle_sha256"] = _hash(export)
        _assert_content_free(export)
        destination = self.export_root / f"{handoff_id}.diagnostic.json"
        _private_json(destination, export)

        record = {
            "schema_version": DIAGNOSTIC_BUNDLE_SCHEMA,
            "handoff_id": handoff_id,
            "state": "customer_approved_export_ready",
            "manifest_sha256": manifest["manifest_sha256"],
            "bundle_sha256": export["bundle_sha256"],
            "customer_approved": True,
            "customer_content_in_bundle": False,
            "export_file_name": destination.name,
            "completed_at": _now(),
            "idempotent_replay": False,
        }
        for domain_id, entity_id, payload in (
            ("support.records", handoff_id, record),
            ("security.audit", handoff_id, {**record, "event": "diagnostic_bundle_customer_approved"}),
            (
                "departments.operational_audit",
                handoff_id,
                {**record, "event": "support_diagnostic_handoff_prepared"},
            ),
        ):
            self.store.put(
                domain_id,
                workspace_id=workspace_id,
                entity_id=entity_id,
                payload=payload,
                expected_version=None,
                idempotency_key=f"diagnostic-{domain_id.replace('.', '-')}-{handoff_id}",
                actor_id=self.actor_id,
            )
        return record
