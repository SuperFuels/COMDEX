"""Approval-gated creation of a new Xero supplier contact."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str: return datetime.now(UTC).replace(microsecond=0).isoformat()
def _safe(value: Any) -> str: return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class XeroSupplierContactService:
    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)

    def prepare(self, workspace_id: str, *, name: str, prepared_by_person_id: str,
                email: str | None = None) -> dict[str, Any]:
        access = self.authority.access_decision(workspace_id, person_id=prepared_by_person_id,
                                                capability="finance.prepare")
        if not access.get("allowed"): raise PermissionError(access.get("reason") or "finance_prepare_not_authorised")
        name = re.sub(r"\s+", " ", str(name or "").strip())
        if not name or len(name) > 255 or "<" in name or ">" in name: raise ValueError("valid_xero_contact_name_required")
        existing = self._existing_contacts(workspace_id)
        duplicate = next((item for item in existing if str(item.get("Name") or "").casefold() == name.casefold()), None)
        if duplicate: raise ValueError(f"xero_contact_already_exists:{duplicate.get('ContactID')}")
        contact_number = "TESS-" + canonical_contract_hash({"workspace_id": workspace_id, "name": name}).split(":", 1)[1][:20]
        contact = {"Name": name, "ContactNumber": contact_number}
        if str(email or "").strip(): contact["EmailAddress"] = str(email).strip().lower()
        payload = {"Contacts": [contact]}; payload_hash = canonical_contract_hash(payload)
        record = {"schema_version": "aion.xero.supplier_contact.v1",
                  "contact_request_id": f"xero-contact-{contact_number.lower()}", "workspace_id": workspace_id,
                  "payload": payload, "payload_hash": payload_hash,
                  "idempotency_key": ("aion-contact-" + payload_hash.split(":", 1)[1])[:128],
                  "prepared_by_person_id": prepared_by_person_id, "prepared_at": _now(), "approval": None,
                  "execution": None, "verification": None, "status": "exact_provider_approval_required",
                  "external_write_performed": False}
        record["record_hash"] = canonical_contract_hash(record); self._save(workspace_id, record); return record

    def approve(self, workspace_id: str, request_id: str, *, approved_by_person_id: str,
                approved_payload_hash: str) -> dict[str, Any]:
        record = self.load(workspace_id, request_id)
        access = self.authority.access_decision(workspace_id, person_id=approved_by_person_id,
                                                capability="finance.approve_posting")
        if not access.get("allowed"): raise PermissionError(access.get("reason") or "finance_posting_approval_not_authorised")
        if approved_payload_hash != record["payload_hash"]: raise ValueError("approved_xero_contact_payload_hash_mismatch")
        record["approval"] = {"approved_by_person_id": approved_by_person_id, "approved_at": _now(),
                              "approved_payload_hash": approved_payload_hash, "authority_decision": access}
        record["status"] = "approved_for_xero_write"; self._rehash(record, workspace_id); return record

    def execution_request(self, workspace_id: str, request_id: str, *, executed_by_person_id: str) -> dict[str, Any]:
        record = self.load(workspace_id, request_id)
        if record.get("status") == "verified_in_xero": return record
        if record.get("status") not in {"approved_for_xero_write", "provider_response_received"}: raise PermissionError("exact_xero_contact_approval_required")
        access = self.authority.access_decision(workspace_id, person_id=executed_by_person_id, capability="finance.prepare")
        if not access.get("allowed"): raise PermissionError(access.get("reason") or "finance_xero_execution_not_authorised")
        return record

    def record_response(self, workspace_id: str, request_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, request_id); rows = response.get("Contacts") or []
        item = rows[0] if rows and isinstance(rows[0], dict) else {}
        if item.get("HasErrors") or not item.get("ContactID"): raise ValueError("xero_provider_did_not_create_contact")
        record["execution"] = {"resource_id": item["ContactID"], "received_at": _now(),
                               "provider_response_hash": canonical_contract_hash(response)}
        record["status"] = "provider_response_received"; record["external_write_performed"] = True
        self._rehash(record, workspace_id); return record

    def verify(self, workspace_id: str, request_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, request_id); expected = record["payload"]["Contacts"][0]
        rows = response.get("Contacts") or []; resource_id = (record.get("execution") or {}).get("resource_id")
        item = next((row for row in rows if row.get("ContactID") == resource_id), None); errors = []
        if not item: errors.append("contact_not_returned")
        elif item.get("Name") != expected.get("Name"): errors.append("contact_name_mismatch")
        elif item.get("ContactNumber") != expected.get("ContactNumber"): errors.append("contact_number_mismatch")
        record["verification"] = {"verified_at": _now(), "resource_id": resource_id, "errors": errors,
                                  "provider_readback_hash": canonical_contract_hash(response)}
        record["status"] = "verification_failed" if errors else "verified_in_xero"; self._rehash(record, workspace_id)
        if errors: raise ValueError("xero_contact_readback_verification_failed:" + ",".join(errors))
        return record

    def load(self, workspace_id: str, request_id: str) -> dict[str, Any]:
        path = self._dir(workspace_id) / f"{_safe(request_id)}.json"
        if not path.exists(): raise FileNotFoundError(f"Xero supplier contact request not found: {request_id}")
        value = json.loads(path.read_text()); expected = value.get("record_hash"); payload = dict(value); payload.pop("record_hash", None)
        if not expected or canonical_contract_hash(payload) != expected: raise ValueError("xero_supplier_contact_hash_mismatch")
        if value.get("workspace_id") != workspace_id: raise PermissionError("xero_supplier_contact_workspace_isolation_violation")
        return value

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load(workspace_id, path.stem) for path in sorted(self._dir(workspace_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def _existing_contacts(self, workspace_id: str) -> list[dict[str, Any]]:
        connection_path = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations/xero/connection.json"
        if not connection_path.exists(): return []
        connection = json.loads(connection_path.read_text())
        sync_id = str((connection.get("latest_snapshot_ref") or {}).get("sync_id") or "")
        path = AIONBusinessPaths.business_container_dir(workspace_id) / f"integrations/xero/syncs/{sync_id}/contacts.json"
        return (json.loads(path.read_text()).get("Contacts") or []) if path.exists() else []

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/xero_supplier_contacts"; path.mkdir(parents=True, exist_ok=True); return path
    def _save(self, workspace_id: str, value: dict[str, Any]) -> None:
        (self._dir(workspace_id) / f"{_safe(value['contact_request_id'])}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    def _rehash(self, value: dict[str, Any], workspace_id: str) -> None:
        value.pop("record_hash", None); value["record_hash"] = canonical_contract_hash(value); self._save(workspace_id, value)
