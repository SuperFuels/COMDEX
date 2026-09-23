from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


class CapabilityPackageAuthority:
    """Signed, least-authority capability packages around an immutable customer brain."""

    def __init__(self, root: str | Path, *, trusted_publishers: Iterable[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "capability_packages.json"
        self.trusted_publishers = set(trusted_publishers)

    @staticmethod
    def package_ref(manifest: Dict[str, Any]) -> str:
        return f"{manifest.get('package_id')}@{manifest.get('version')}"

    @staticmethod
    def sign_manifest(payload: Dict[str, Any], identity: DeviceIdentity) -> Dict[str, Any]:
        value = {key: item for key, item in payload.items() if key not in {"manifest_hash", "signature"}}
        value.setdefault("schema_version", "aion.capability_package_manifest.v1")
        value["publisher_public_key"] = identity.public_key_b64
        value["manifest_hash"] = canonical_hash(value)
        value["signature"] = identity.sign(canonical_bytes(value))
        return value

    def install(self, manifest: Dict[str, Any], artifact_path: str | Path) -> Dict[str, Any]:
        self._validate_manifest(manifest)
        if manifest["publisher_public_key"] not in self.trusted_publishers:
            raise PermissionError("capability_publisher_not_trusted")
        signed = {key: item for key, item in manifest.items() if key != "signature"}
        if canonical_hash({key: item for key, item in signed.items() if key != "manifest_hash"}) != manifest["manifest_hash"]:
            raise ValueError("capability_manifest_hash_mismatch")
        if not DeviceIdentity.verify(manifest["publisher_public_key"], canonical_bytes(signed), manifest["signature"]):
            raise ValueError("capability_manifest_signature_invalid")
        path = Path(artifact_path)
        if not path.is_file():
            raise FileNotFoundError("capability_artifact_missing")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        artifact = manifest["artifact"]
        if digest.hexdigest() != artifact["sha256"] or path.stat().st_size != int(artifact["bytes"]):
            raise ValueError("capability_artifact_integrity_mismatch")
        state = self._state()
        ref = self.package_ref(manifest)
        existing = dict((state.get("packages") or {}).get(ref) or {})
        if existing and existing["manifest_hash"] != manifest["manifest_hash"]:
            raise PermissionError("immutable_capability_version_conflict")
        state.setdefault("packages", {})[ref] = {
            "manifest": manifest,
            "manifest_hash": manifest["manifest_hash"],
            "status": existing.get("status") or "installed_unqualified",
            "tests": existing.get("tests") or {},
            "installed_at": existing.get("installed_at") or utc_now_iso(),
            "active_components": existing.get("active_components") or dict(manifest["components"]),
        }
        self._write(state)
        return self.record(ref)

    def record_test(self, package_ref: str, *, kind: str, passed: bool, evidence: Dict[str, Any]) -> Dict[str, Any]:
        if kind not in {"dry_run", "adversarial_permission", "outcome"}:
            raise ValueError("capability_test_kind_invalid")
        state = self._state()
        record = self._require(state, package_ref)
        event = {"kind": kind, "passed": bool(passed), "evidence": dict(evidence), "tested_at": utc_now_iso()}
        event["evidence_hash"] = canonical_hash(event)
        record.setdefault("tests", {})[kind] = event
        if not passed:
            record["status"] = "blocked"
        self._write(state)
        return event

    def activate(self, package_ref: str, *, accountable_owner: str, approval_receipt: str) -> Dict[str, Any]:
        if not accountable_owner.strip() or not approval_receipt.strip():
            raise PermissionError("human_owner_and_approval_required")
        state = self._state()
        record = self._require(state, package_ref)
        tests = record.get("tests") or {}
        required = {"dry_run", "adversarial_permission", "outcome"}
        if set(tests) < required or not all(tests[key].get("passed") is True for key in required):
            raise PermissionError("capability_qualification_incomplete")
        if record.get("status") in {"blocked", "revoked", "removed"}:
            raise PermissionError("capability_not_activatable")
        activation = {"accountable_owner": accountable_owner, "approval_receipt_hash": canonical_hash(approval_receipt), "activated_at": utc_now_iso()}
        record.update({"status": "active", "activation": activation})
        self._write(state)
        return activation

    def authorize(self, package_ref: str, *, kind: str, target: str, action: str = "") -> Dict[str, Any]:
        state = self._state()
        record = self._require(state, package_ref)
        if record.get("status") != "active":
            raise PermissionError("active_capability_required")
        permissions = dict(record["manifest"].get("permissions") or {})
        allowed = {
            "network": list(permissions.get("network_hosts") or []),
            "file": list(permissions.get("file_roots") or []),
            "identity": list(permissions.get("identity_scopes") or []),
            "tool": list(permissions.get("tools") or []),
            "execution": list(permissions.get("execution_actions") or []),
        }
        if kind not in allowed:
            raise ValueError("capability_permission_kind_invalid")
        if kind == "file":
            requested = Path(target).resolve()
            permitted = any(requested.is_relative_to(Path(root).resolve()) for root in allowed[kind])
        else:
            permitted = target in allowed[kind]
        if not permitted:
            raise PermissionError(f"undeclared_{kind}_access_denied")
        if kind == "execution" and (not action or action != target):
            raise PermissionError("raw_execution_denied")
        limit = int(record["manifest"].get("limits", {}).get("maximum_authorizations") or 100)
        usage = int(record.get("authorization_count") or 0)
        if usage >= limit:
            raise PermissionError("capability_authorization_limit_reached")
        record["authorization_count"] = usage + 1
        grant = {
            "package_ref": package_ref,
            "kind": kind,
            "target": target,
            "action": action,
            "accountable_owner": record["activation"]["accountable_owner"],
            "granted_at": utc_now_iso(),
        }
        grant["grant_hash"] = canonical_hash(grant)
        self._write(state)
        return grant

    def select_component(self, package_ref: str, *, component: str, version: str) -> Dict[str, Any]:
        if component not in {"prompt", "procedure", "tools", "policy"}:
            raise ValueError("capability_component_invalid")
        state = self._state()
        record = self._require(state, package_ref)
        permitted = list((record["manifest"].get("component_versions") or {}).get(component) or [])
        if version not in permitted:
            raise PermissionError("capability_component_version_not_declared")
        previous = record.setdefault("active_components", {}).get(component)
        record["active_components"][component] = version
        record.setdefault("component_history", []).append(
            {"component": component, "previous": previous, "selected": version, "at": utc_now_iso()}
        )
        self._write(state)
        return {"component": component, "previous": previous, "selected": version}

    def revoke(self, package_ref: str, *, reason: str) -> Dict[str, Any]:
        if not reason.strip():
            raise ValueError("capability_revocation_reason_required")
        state = self._state()
        record = self._require(state, package_ref)
        record.update({"status": "revoked", "revocation": {"reason": reason, "at": utc_now_iso()}})
        self._write(state)
        return record["revocation"]

    def remove(self, package_ref: str) -> Dict[str, Any]:
        state = self._state()
        record = self._require(state, package_ref)
        record.update({"status": "removed", "removed_at": utc_now_iso()})
        self._write(state)
        return {"package_ref": package_ref, "removed": True, "evidence_retained": True}

    def catalogue(self) -> Dict[str, Any]:
        state = self._state()
        entries = []
        for ref, record in sorted((state.get("packages") or {}).items()):
            manifest = record["manifest"]
            entries.append(
                {
                    "package_ref": ref,
                    "name": manifest["name"],
                    "status": record["status"],
                    "publisher_class": manifest["publishing"]["publisher_class"],
                    "curated": manifest["publishing"]["curated"],
                    "commercial_terms": manifest["publishing"]["commercial_terms"],
                    "department": manifest.get("department"),
                    "industry": manifest.get("industry"),
                    "accountable_owner": (record.get("activation") or {}).get("accountable_owner", ""),
                }
            )
        return {"schema_version": "aion.capability_catalogue.v1", "entries": entries, "customer_brain_content_exposed": False}

    def record(self, package_ref: str) -> Dict[str, Any]:
        return self._require(self._state(), package_ref)

    @staticmethod
    def _validate_manifest(manifest: Dict[str, Any]) -> None:
        required = (
            "package_id", "version", "name", "artifact", "permissions", "limits",
            "components", "component_versions", "publishing", "publisher_public_key",
            "manifest_hash", "signature",
        )
        missing = [key for key in required if not manifest.get(key)]
        if missing:
            raise ValueError(f"capability_manifest_fields_missing:{','.join(missing)}")
        artifact = dict(manifest["artifact"])
        if len(str(artifact.get("sha256") or "")) != 64 or int(artifact.get("bytes") or 0) <= 0:
            raise ValueError("capability_artifact_identity_invalid")
        if manifest.get("contains_customer_brain") is not False or manifest.get("contains_customer_data") is not False:
            raise PermissionError("capability_package_must_not_copy_customer_brain_or_data")
        components = dict(manifest["components"])
        versions = dict(manifest["component_versions"])
        for component in ("prompt", "procedure", "tools", "policy"):
            if not components.get(component) or components[component] not in list(versions.get(component) or []):
                raise ValueError("capability_component_versions_invalid")
        publishing = dict(manifest["publishing"])
        if publishing.get("publisher_class") not in {"tessaris", "customer", "third_party"}:
            raise ValueError("capability_publisher_class_invalid")
        if publishing.get("publisher_class") == "third_party" and not publishing.get("commercial_terms"):
            raise ValueError("third_party_commercial_terms_required")
        limits = dict(manifest["limits"])
        if not 1 <= int(limits.get("maximum_authorizations") or 0) <= 100_000:
            raise ValueError("capability_authorization_limit_invalid")

    @staticmethod
    def _require(state: Dict[str, Any], package_ref: str) -> Dict[str, Any]:
        record = (state.get("packages") or {}).get(package_ref)
        if not record:
            raise KeyError("capability_package_not_installed")
        return record

    def _state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": "aion.capability_packages.v1", "packages": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write(self, state: Dict[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)
