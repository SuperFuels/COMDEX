from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


_PATH = re.compile(r"[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*")
_REDACTED = "[REDACTED BY AION POLICY]"


class AionFlowHarnessAuthority:
    """Signed harnesses and minimum-necessary business context, independent of models."""

    def __init__(self, root: str | Path, *, trusted_issuers: Iterable[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "harnesses.json"
        self.trusted_issuers = set(trusted_issuers)

    @staticmethod
    def harness_ref(manifest: Mapping[str, Any]) -> str:
        return f"{manifest.get('harness_id')}@{manifest.get('version')}"

    @staticmethod
    def sign_manifest(payload: Mapping[str, Any], identity: DeviceIdentity) -> Dict[str, Any]:
        value = {key: item for key, item in dict(payload).items() if key not in {"manifest_hash", "signature"}}
        value.setdefault("schema_version", "aion.flow.harness_manifest.v1")
        value["issuer_public_key"] = identity.public_key_b64
        value["manifest_hash"] = canonical_hash(value)
        value["signature"] = identity.sign(canonical_bytes(value))
        return value

    def register(self, manifest: Mapping[str, Any]) -> Dict[str, Any]:
        value = dict(manifest)
        self._validate_manifest(value)
        if value["issuer_public_key"] not in self.trusted_issuers:
            raise PermissionError("harness_issuer_not_trusted")
        signed = {key: item for key, item in value.items() if key != "signature"}
        if canonical_hash({key: item for key, item in signed.items() if key != "manifest_hash"}) != value["manifest_hash"]:
            raise ValueError("harness_manifest_hash_mismatch")
        if not DeviceIdentity.verify(value["issuer_public_key"], canonical_bytes(signed), value["signature"]):
            raise ValueError("harness_manifest_signature_invalid")
        state = self._state()
        reference = self.harness_ref(value)
        existing = dict(state["harnesses"].get(reference) or {})
        if existing and existing["manifest_hash"] != value["manifest_hash"]:
            raise PermissionError("immutable_harness_version_conflict")
        state["harnesses"][reference] = {
            "manifest": value,
            "manifest_hash": value["manifest_hash"],
            "status": existing.get("status") or "qualified",
            "registered_at": existing.get("registered_at") or utc_now_iso(),
        }
        self._write(state)
        return self.record(reference)

    def select(self, *, route_id: str, harness_ref: str) -> Dict[str, Any]:
        state = self._state()
        self._require(state, harness_ref)
        route = state["routes"].setdefault(route_id, {"active": "", "previous": "", "history": []})
        if route["active"] != harness_ref:
            route["previous"] = route["active"]
            route["active"] = harness_ref
            route["history"].append({"selected": harness_ref, "at": utc_now_iso()})
        self._write(state)
        return dict(route)

    def rollback(self, *, route_id: str) -> Dict[str, Any]:
        state = self._state()
        route = state["routes"].get(route_id) or {}
        if not route.get("previous"):
            raise ValueError("previous_harness_unavailable")
        route["active"], route["previous"] = route["previous"], route["active"]
        route.setdefault("history", []).append({"selected": route["active"], "reason": "rollback", "at": utc_now_iso()})
        self._write(state)
        return dict(route)

    def compare(self, left_ref: str, right_ref: str) -> Dict[str, Any]:
        left = self.record(left_ref)["manifest"]
        right = self.record(right_ref)["manifest"]
        fields = ("instructions", "input_schema", "output_schema", "examples", "declared_tools", "domain_pack")
        changed = [field for field in fields if left.get(field) != right.get(field)]
        return {
            "left": left_ref,
            "right": right_ref,
            "changed_fields": changed,
            "model_manifest_changed": False,
            "comparison_hash": canonical_hash({"left": left_ref, "right": right_ref, "changed": changed}),
        }

    def authorize_tool(self, harness_ref: str, *, tool_id: str, access: Mapping[str, Any]) -> Dict[str, Any]:
        manifest = self.record(harness_ref)["manifest"]
        declaration = next((item for item in manifest["declared_tools"] if item.get("tool_id") == tool_id), None)
        if not declaration:
            raise PermissionError("undeclared_harness_tool_denied")
        for key in ("network_hosts", "file_roots", "actions"):
            requested = set(access.get(key) or [])
            allowed = set(declaration.get(key) or [])
            if not requested.issubset(allowed):
                raise PermissionError(f"harness_tool_{key}_denied")
        grant = {
            "harness_ref": harness_ref,
            "tool_id": tool_id,
            "access": {key: sorted(set(access.get(key) or [])) for key in ("network_hosts", "file_roots", "actions")},
            "granted_at": utc_now_iso(),
        }
        grant["grant_hash"] = canonical_hash(grant)
        return grant

    def assemble_context(
        self,
        *,
        identity: Mapping[str, Any],
        purpose: str,
        memory: Mapping[str, Any],
        business_map: Mapping[str, Any],
        include: Iterable[str],
        exclude: Iterable[str] = (),
        redact: Iterable[str] = (),
        summarize: Iterable[str] = (),
        permitted_paths: Iterable[str],
        downstream: Iterable[Mapping[str, Any]] = (),
    ) -> Dict[str, Any]:
        if not str(purpose).strip():
            raise ValueError("context_purpose_required")
        required_identity = ("person_id", "organisation_id", "workspace_id", "role")
        if any(not str(identity.get(key) or "").strip() for key in required_identity):
            raise PermissionError("active_business_identity_incomplete")
        requested = self._clean_paths(include)
        permitted = set(self._clean_paths(permitted_paths))
        denied = [path for path in requested if not self._path_permitted(path, permitted)]
        if denied:
            raise PermissionError(f"business_context_path_denied:{','.join(denied)}")
        excluded = set(self._clean_paths(exclude))
        redacted = set(self._clean_paths(redact))
        summarized = set(self._clean_paths(summarize))
        sources = {"memory": dict(memory), "business_map": dict(business_map)}
        values: Dict[str, Any] = {}
        for path in requested:
            if any(self._path_matches(path, item) for item in excluded):
                continue
            value = self._lookup(sources, path)
            if any(self._path_matches(path, item) for item in redacted):
                value = _REDACTED
            elif any(self._path_matches(path, item) for item in summarized):
                value = self._summary(value)
            values[path] = value
        context = {
            "schema_version": "aion.flow.minimum_context.v1",
            "identity": {key: identity.get(key) for key in (*required_identity, "space_id")},
            "purpose": str(purpose).strip(),
            "fields": values,
            "minimum_context": True,
            "source_interpretation_separated": True,
            "created_at": utc_now_iso(),
        }
        context["context_hash"] = canonical_hash(context)
        disclosure = []
        for node in downstream:
            disclosed = list(node.get("fields") or requested)
            disclosure.append({
                "node_id": str(node.get("node_id") or ""),
                "destination": str(node.get("destination") or "local"),
                "fields": [path for path in disclosed if path in values],
                "data_classes": sorted(set(node.get("data_classes") or [])),
                "encrypted": bool(node.get("encrypted", node.get("destination") == "local")),
            })
        return {"context": context, "disclosure_preflight": disclosure, "unauthorized_fields_exposed": False}

    def record(self, harness_ref: str) -> Dict[str, Any]:
        return self._require(self._state(), harness_ref)

    @staticmethod
    def _validate_manifest(manifest: Mapping[str, Any]) -> None:
        required = (
            "harness_id", "version", "instructions", "input_schema", "output_schema",
            "examples", "declared_tools", "domain_pack", "issuer_public_key", "manifest_hash", "signature",
        )
        missing = [key for key in required if key not in manifest or manifest.get(key) in (None, "")]
        if missing:
            raise ValueError(f"harness_manifest_fields_missing:{','.join(missing)}")
        if not isinstance(manifest.get("declared_tools"), list) or not isinstance(manifest.get("examples"), list):
            raise ValueError("harness_manifest_collections_invalid")
        if manifest.get("model_id") or manifest.get("provider_credentials"):
            raise PermissionError("harness_must_remain_model_and_credential_independent")

    @staticmethod
    def _clean_paths(values: Iterable[str]) -> list[str]:
        result = []
        for value in values:
            path = str(value).strip()
            if not _PATH.fullmatch(path):
                raise ValueError("business_context_path_invalid")
            if path not in result:
                result.append(path)
        return result

    @staticmethod
    def _path_matches(path: str, candidate: str) -> bool:
        return path == candidate or path.startswith(candidate + ".")

    @classmethod
    def _path_permitted(cls, path: str, permitted: set[str]) -> bool:
        return any(cls._path_matches(path, allowed) for allowed in permitted)

    @staticmethod
    def _lookup(source: Mapping[str, Any], path: str) -> Any:
        value: Any = source
        for part in path.split("."):
            if not isinstance(value, Mapping) or part not in value:
                raise KeyError(f"business_context_field_missing:{path}")
            value = value[part]
        return value

    @staticmethod
    def _summary(value: Any) -> Dict[str, Any]:
        if isinstance(value, Mapping):
            return {"type": "object", "keys": sorted(str(key) for key in value), "item_count": len(value)}
        if isinstance(value, (list, tuple)):
            return {"type": "list", "item_count": len(value)}
        return {"type": type(value).__name__, "present": value not in (None, "")}

    @staticmethod
    def _require(state: Mapping[str, Any], reference: str) -> Dict[str, Any]:
        record = (state.get("harnesses") or {}).get(reference)
        if not record:
            raise KeyError("harness_not_registered")
        if record.get("status") != "qualified":
            raise PermissionError("qualified_harness_required")
        return record

    def _state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": "aion.flow.harnesses.v1", "harnesses": {}, "routes": {}}
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "aion.flow.harnesses.v1":
            raise RuntimeError("harness_state_invalid")
        return value

    def _write(self, state: Mapping[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)
