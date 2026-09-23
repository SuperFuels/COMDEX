from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings
from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity, IdentityStore


TEMPLATE_REF = re.compile(r"[a-z0-9][a-z0-9_.-]{0,79}@[0-9][a-zA-Z0-9_.-]{0,39}")
SECRET_FIELD = re.compile(r"(^|[_-])(api[_-]?key|password|passwd|secret|private[_-]?key|access[_-]?token|refresh[_-]?token|bearer|authorization)($|[_-])", re.IGNORECASE)
MAX_TEMPLATE_BYTES = 2 * 1024 * 1024


class AionFlowTemplateLibrary:
    """Signed reusable logic with customer bindings and memory kept outside packages."""

    def __init__(self, root: str | Path = ".runtime/aion_flow/templates") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "template-library.json"
        self.installation_path = self.root / "organisation-installations.json"
        self.identity = IdentityStore(self.root / "publisher-identity").load_or_create()
        self._seed_builtin_templates()

    def list(self) -> Dict[str, Any]:
        state = self._state()
        values = []
        for ref, record in sorted(state["templates"].items()):
            manifest = record["manifest"]
            values.append({
                "template_ref": ref, "template_id": manifest["template_id"], "version": manifest["version"],
                "label": manifest["label"], "department": manifest["department"], "description": manifest["description"],
                "status": record["status"], "required_bindings": manifest["required_bindings"],
                "permissions": manifest["permissions"], "publisher_class": manifest["publisher_class"],
                "manifest_hash": manifest["manifest_hash"], "contains_credentials": False, "contains_customer_data": False,
            })
        return {"schema_version": "aion.flow.template_catalogue.public.v1", "templates": values, "third_party_publishing_enabled": False}

    def inspect(self, template_ref: str) -> Dict[str, Any]:
        record = self._require(template_ref)
        result = {**record, "signature_valid": self._verify(record["manifest"]), "dependencies": self._dependency_review(record["manifest"])}
        result["customer_bindings_in_package"] = False
        return result

    def install(self, template_ref: str, *, organisation_id: str, bindings: Mapping[str, str], actor_role: str) -> Dict[str, Any]:
        record = self._require(template_ref)
        if record["status"] in {"revoked", "quarantined"}:
            raise PermissionError("template_not_installable")
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("template_install_role_required")
        manifest = record["manifest"]
        if not self._verify(manifest):
            raise ValueError("template_signature_invalid")
        review = self._dependency_review(manifest)
        if not review["compatible"]:
            raise PermissionError("template_dependencies_not_satisfied")
        supplied = {str(key): str(value) for key, value in bindings.items()}
        missing = [item for item in manifest["required_bindings"] if not supplied.get(item)]
        if missing:
            raise ValueError(f"template_bindings_missing:{','.join(missing)}")
        if any(not value.startswith("vault://") for value in supplied.values()):
            raise ValueError("template_bindings_must_be_opaque_vault_references")
        installations = self._installations()
        installation_id = f"{organisation_id}:{manifest['template_id']}"
        previous = (installations["installations"].get(installation_id) or {}).get("active_template_ref", "")
        event = {
            "installation_id": installation_id, "organisation_id": str(organisation_id), "active_template_ref": template_ref,
            "previous_template_ref": previous, "bindings": supplied, "installed_by_role": actor_role,
            "installed_at": utc_now_iso(), "status": "installed_unapproved", "authority_granted": False,
        }
        event["installation_hash"] = canonical_hash(event)
        installations["installations"][installation_id] = event
        self._write(self.installation_path, installations)
        return event

    def list_installations(self, *, organisation_id: str) -> Dict[str, Any]:
        items = [
            dict(item)
            for item in self._installations()["installations"].values()
            if item.get("organisation_id") == str(organisation_id)
        ]
        return {
            "schema_version": "aion.flow.template_installations.public.v1",
            "organisation_id": str(organisation_id),
            "installations": sorted(items, key=lambda item: item.get("installed_at", ""), reverse=True),
        }

    def pin(self, installation_id: str, *, template_ref: str, actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("template_pin_role_required")
        template = self._require(template_ref)
        if template["status"] != "available" or not self._verify(template["manifest"]):
            raise PermissionError("template_version_not_available")
        state = self._installations()
        item = state["installations"].get(str(installation_id))
        if not item:
            raise KeyError("template_installation_not_found")
        current = item.get("active_template_ref", "")
        if current == template_ref:
            return dict(item)
        item.update({
            "active_template_ref": template_ref,
            "previous_template_ref": current,
            "pinned_at": utc_now_iso(),
            "pinned_by_role": actor_role,
            "status": "installed_unapproved",
            "authority_granted": False,
        })
        item["installation_hash"] = canonical_hash({key: value for key, value in item.items() if key != "installation_hash"})
        self._write(self.installation_path, state)
        return dict(item)

    def remove(self, installation_id: str, *, actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("template_remove_role_required")
        state = self._installations()
        item = state["installations"].get(str(installation_id))
        if not item:
            raise KeyError("template_installation_not_found")
        item.update({"status": "removed", "removed_at": utc_now_iso(), "authority_granted": False})
        item["installation_hash"] = canonical_hash({key: value for key, value in item.items() if key != "installation_hash"})
        self._write(self.installation_path, state)
        return dict(item)

    def publish_private(self, *, organisation_id: str, payload: Mapping[str, Any], actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("private_template_publish_role_required")
        clean = AionFlowModelBindings.redact_for_canvas(dict(payload))
        encoded = json.dumps(clean)
        if len(encoded.encode("utf-8")) > MAX_TEMPLATE_BYTES:
            raise ValueError("template_size_limit_exceeded")
        if "vault://" in encoded or "[REDACTED]" in encoded or self._contains_secret_field(clean):
            raise ValueError("template_must_not_embed_bindings_or_secret_shaped_values")
        clean.update({"publisher_class": "customer_private", "organisation_id": str(organisation_id), "contains_credentials": False, "contains_customer_data": False})
        manifest = self._sign(clean)
        self._register(manifest)
        return self.inspect(f"{manifest['template_id']}@{manifest['version']}")

    def lifecycle(self, template_ref: str, *, action: str, reason: str, actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("template_lifecycle_role_required")
        if action not in {"quarantine", "revoke", "restore"}:
            raise ValueError("template_lifecycle_action_invalid")
        if not str(reason).strip():
            raise ValueError("template_lifecycle_reason_required")
        state = self._state(); record = self._require(template_ref, state=state)
        previous = record["status"]
        record["status"] = {"quarantine": "quarantined", "revoke": "revoked", "restore": "available"}[action]
        event = {"action": action, "previous": previous, "status": record["status"], "reason": str(reason)[:500], "at": utc_now_iso(), "actor_role": actor_role}
        event["event_hash"] = canonical_hash(event)
        record.setdefault("history", []).append(event); self._write(self.state_path, state)
        return self.inspect(template_ref)

    def rollback(self, installation_id: str, *, actor_role: str) -> Dict[str, Any]:
        if actor_role not in {"owner", "admin", "workflow_publisher", "canonical_authority"}:
            raise PermissionError("template_rollback_role_required")
        state = self._installations(); item = state["installations"].get(installation_id)
        if not item or not item.get("previous_template_ref"):
            raise ValueError("previous_template_version_unavailable")
        previous, current = item["previous_template_ref"], item["active_template_ref"]
        item.update({"active_template_ref": previous, "previous_template_ref": current, "rolled_back_at": utc_now_iso(), "status": "rolled_back"})
        item["installation_hash"] = canonical_hash({key: value for key, value in item.items() if key != "installation_hash"})
        self._write(self.installation_path, state); return item

    def _seed_builtin_templates(self) -> None:
        for spec in self._builtins():
            ref = f"{spec['template_id']}@{spec['version']}"
            if ref not in self._state()["templates"]:
                self._register(self._sign(spec))

    def _sign(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        value = {key: item for key, item in dict(payload).items() if key not in {"manifest_hash", "signature", "publisher_public_key"}}
        value.setdefault("schema_version", "aion.flow.template_manifest.v1")
        value["publisher_public_key"] = self.identity.public_key_b64
        value["manifest_hash"] = canonical_hash(value)
        value["signature"] = self.identity.sign(canonical_bytes(value))
        return value

    @staticmethod
    def _verify(manifest: Mapping[str, Any]) -> bool:
        signed = {key: item for key, item in dict(manifest).items() if key != "signature"}
        expected = canonical_hash({key: item for key, item in signed.items() if key != "manifest_hash"})
        return expected == manifest.get("manifest_hash") and DeviceIdentity.verify(str(manifest.get("publisher_public_key")), canonical_bytes(signed), str(manifest.get("signature")))

    def _register(self, manifest: Mapping[str, Any]) -> None:
        self._validate(manifest); state = self._state(); ref = f"{manifest['template_id']}@{manifest['version']}"
        if ref in state["templates"] and state["templates"][ref]["manifest"]["manifest_hash"] != manifest["manifest_hash"]:
            raise PermissionError("immutable_template_version_conflict")
        state["templates"][ref] = {"manifest": dict(manifest), "status": "available", "history": [], "registered_at": utc_now_iso()}
        self._write(self.state_path, state)

    def _validate(self, manifest: Mapping[str, Any]) -> None:
        ref = f"{manifest.get('template_id')}@{manifest.get('version')}"
        if not TEMPLATE_REF.fullmatch(ref): raise ValueError("template_identity_invalid")
        if manifest.get("contains_credentials") is not False or manifest.get("contains_customer_data") is not False: raise PermissionError("template_must_not_copy_customer_state")
        if not self._verify(manifest): raise ValueError("template_signature_invalid")
        graph = manifest.get("graph") or {}
        encoded = json.dumps(graph)
        if len(encoded.encode("utf-8")) > MAX_TEMPLATE_BYTES: raise ValueError("template_size_limit_exceeded")
        if "vault://" in encoded or "[REDACTED]" in encoded or self._contains_secret_field(graph): raise ValueError("template_graph_contains_binding_or_secret")

    @staticmethod
    def _contains_secret_field(value: Any) -> bool:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if SECRET_FIELD.search(str(key)) and item not in (None, "", False):
                    return True
                if AionFlowTemplateLibrary._contains_secret_field(item):
                    return True
        elif isinstance(value, list):
            return any(AionFlowTemplateLibrary._contains_secret_field(item) for item in value)
        return False

    @staticmethod
    def _dependency_review(manifest: Mapping[str, Any]) -> Dict[str, Any]:
        dependencies = list(manifest.get("dependencies") or [])
        permissions = list(manifest.get("permissions") or [])
        licences = list(manifest.get("licences") or [])
        failures = []
        if any(not item for item in dependencies): failures.append("dependency_identifier_missing")
        if any(not item for item in permissions): failures.append("permission_identifier_missing")
        if any(not item for item in licences): failures.append("licence_identifier_missing")
        return {"compatible": not failures, "failures": failures, "dependencies": dependencies, "permissions": permissions, "licences": licences, "review_hash": canonical_hash({"dependencies": dependencies, "permissions": permissions, "licences": licences})}

    def _require(self, template_ref: str, *, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        value = (state or self._state())["templates"].get(str(template_ref))
        if not value: raise KeyError("template_not_found")
        return value

    def _state(self) -> Dict[str, Any]:
        if not self.state_path.exists(): return {"schema_version": "aion.flow.template_library.v1", "templates": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _installations(self) -> Dict[str, Any]:
        if not self.installation_path.exists(): return {"schema_version": "aion.flow.template_installations.v1", "installations": {}}
        return json.loads(self.installation_path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, value: Mapping[str, Any]) -> None:
        temporary = path.with_suffix(".tmp"); temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True), encoding="utf-8"); os.chmod(temporary, 0o600); os.replace(temporary, path)

    @staticmethod
    def _builtins() -> list[Dict[str, Any]]:
        def template(template_id: str, label: str, department: str, description: str, nodes: list[str], bindings: list[str] | None = None, permissions: list[str] | None = None) -> Dict[str, Any]:
            return {
                "template_id": template_id, "version": "1.0.0", "label": label, "department": department, "description": description,
                "publisher_class": "tessaris", "contains_credentials": False, "contains_customer_data": False,
                "required_bindings": bindings or [], "dependencies": ["aion-flow>=1"], "licences": ["Tessaris-runtime"], "permissions": permissions or ["read_scoped_context"],
                "graph": {"nodes": [{"id": f"step_{index+1}", "module_id": module} for index, module in enumerate(nodes)], "edges": [{"source": f"step_{index+1}", "target": f"step_{index+2}"} for index in range(len(nodes)-1)]},
            }
        return [
            template("local-first-research", "Local-first research", "Research", "Use local context, evidence and validation before any optional provider.", ["intelligence.aion_admission", "intelligence.evidence_retrieval", "intelligence.model_local", "intelligence.deterministic_validator", "intelligence.verify_receipt"]),
            template("gemini-evidence-analysis", "Gemini evidence analysis", "Research", "Interpret one governed evidence pack with a customer-connected Gemini model.", ["intelligence.aion_admission", "intelligence.evidence_retrieval", "intelligence.disclosure_gate", "intelligence.model_private_endpoint", "intelligence.deterministic_validator", "intelligence.verify_receipt"], ["model_provider"]),
            template("private-business-analysis", "Private business analysis", "Boardroom", "Analyse scoped Business Map evidence on customer-controlled compute.", ["intelligence.aion_admission", "intelligence.business_map", "intelligence.compute_target", "intelligence.model_private_endpoint", "intelligence.verify_receipt"], ["private_compute"]),
            template("multi-model-critic", "Multi-model critic", "Boardroom", "Generate, independently critique and reconcile against evidence within hard bounds.", ["intelligence.aion_admission", "intelligence.evidence_retrieval", "intelligence.critic", "intelligence.reconcile", "intelligence.deterministic_validator", "intelligence.verify_receipt"], ["critic_models"]),
            template("governed-email-drafting", "Governed email drafting", "Operations", "Draft from minimum context and require private approval before any send capability.", ["intelligence.aion_admission", "intelligence.harness", "intelligence.model_local", "intelligence.human_approval", "intelligence.capability", "intelligence.verify_receipt"], ["email_connector"], ["read_scoped_context", "draft_email", "send_email_after_approval"]),
            template("boardroom-decision-analysis", "Boardroom decision analysis", "Boardroom", "Use the confirmed Business Map, independent criticism and founder review.", ["intelligence.aion_admission", "intelligence.business_map", "intelligence.critic", "intelligence.reconcile", "intelligence.human_approval", "intelligence.verify_receipt"]),
        ]
