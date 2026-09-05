"""Tenant-safe commercial controls and zero-content operational assurance."""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso


OWNERSHIP_FEATURES = {
    "brain.read", "brain.correct", "brain.export", "brain.restore", "brain.migrate",
    "business_map.read", "memory.read", "provider.replace",
}
CORE_FEATURES = [
    "brain.local", "brain.read", "brain.correct", "brain.export", "brain.restore",
    "business_map.read", "memory.read", "provider.replace", "pilot.personal",
    "model.local", "model.customer_key", "agent_to_agent",
]
EDITIONS = {
    "pilot_free": {"features": CORE_FEATURES + ["workspace.business.basic", "workflow.manual"], "support": "community"},
    "operator": {"features": CORE_FEATURES + ["workspace.business.basic", "workflow.manual", "workflow.scheduled", "operator.one", "connectors.standard", "mobile.approvals"], "support": "standard"},
    "boardroom": {"features": CORE_FEATURES + ["workspace.business", "workflow.scheduled", "boardroom", "business.connectors", "capability.catalogue", "department.multiple", "approval.chains"], "support": "business_hours"},
    "growth": {"features": CORE_FEATURES + ["workspace.business", "workflow.scheduled", "boardroom", "business.connectors", "capability.catalogue", "department.multiple", "approval.chains", "multi_entity", "enterprise.identity", "private.compute", "regional.policy"], "support": "priority"},
    "sovereign": {"features": CORE_FEATURES + ["workspace.business", "workflow.scheduled", "boardroom", "business.connectors", "capability.catalogue", "department.multiple", "approval.chains", "multi_entity", "enterprise.identity", "private.compute", "regional.policy", "assurance.exports", "contracted.operations"], "support": "contracted_sla"},
}
# Backward-compatible edition identifier retained for existing signed records.
EDITIONS["sovereign_fabric"] = EDITIONS["sovereign"]
CONTENT_KEYS = re.compile(r"(prompt|response|result|message|document|customer.?content|conversation|secret|token|password|private.?key)", re.I)
METER_METADATA_KEYS = {"model_class", "route_class", "region", "residency", "accelerator", "latency_band", "billing_tier"}


class CommercialAssuranceService:
    def __init__(self, root: str | Path, *, signing_key: Ed25519PrivateKey | None = None,
                 verification_key: Ed25519PublicKey | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.verification_key = verification_key or (signing_key.public_key() if signing_key else None)
        self.licences_path = self.root / "tenant_licences.json"
        self.meter_path = self.root / "optional_service_meter.json"
        self.telemetry_path = self.root / "telemetry_policy.json"
        self.diagnostics_path = self.root / "zero_content_diagnostics.json"

    def issue_licence(self, *, licence_id: str, tenant_id: str, edition: str,
                      expires_at: str, limits: Dict[str, int] | None = None) -> Dict[str, Any]:
        if not self.signing_key:
            raise PermissionError("licence_signing_authority_unavailable")
        if edition not in EDITIONS:
            raise ValueError("licence_edition_invalid")
        self._required(licence_id, tenant_id, expires_at)
        payload = {"schema_version": "aion.tenant_entitlement.v2", "catalogue_version": "2026-09-05",
                   "licence_id": licence_id,
                   "tenant_id": tenant_id, "edition": edition,
                   "features": list(EDITIONS[edition]["features"]), "support": EDITIONS[edition]["support"],
                   "limits": {key: int(value) for key, value in (limits or {}).items()},
                   "issued_at": utc_now_iso(), "expires_at": self._iso(expires_at),
                   "customer_content_bound": False, "customer_data_access_granted": False,
                   "portable_brain_ownership_changed": False,
                   "ownership_features_subscription_independent": sorted(OWNERSHIP_FEATURES)}
        envelope = {"payload": payload, "signature": base64.b64encode(self.signing_key.sign(canonical_bytes(payload))).decode("ascii")}
        records = self._records(self.licences_path)
        if any(item["payload"]["licence_id"] == licence_id for item in records):
            raise ValueError("licence_id_reused")
        records.append(envelope)
        self._write(self.licences_path, records)
        return envelope

    def verify_licence(self, envelope: Dict[str, Any], *, tenant_id: str, as_of: str | None = None) -> Dict[str, Any]:
        if not self.verification_key:
            return {"valid": False, "reason": "licence_verification_key_unavailable"}
        try:
            payload = dict(envelope["payload"])
            self.verification_key.verify(base64.b64decode(envelope["signature"], validate=True), canonical_bytes(payload))
        except Exception:
            return {"valid": False, "reason": "licence_signature_invalid"}
        if payload.get("tenant_id") != tenant_id:
            return {"valid": False, "reason": "licence_tenant_mismatch"}
        if self._datetime(as_of or utc_now_iso()) >= self._datetime(payload["expires_at"]):
            return {"valid": False, "reason": "licence_expired"}
        if payload.get("customer_content_bound") or payload.get("customer_data_access_granted"):
            return {"valid": False, "reason": "entitlement_customer_data_boundary_invalid"}
        return {"valid": True, "reason": "verified", "edition": payload["edition"],
                "features": payload["features"], "limits": payload["limits"],
                "support": payload.get("support"), "catalogue_version": payload.get("catalogue_version")}

    def decide_entitlement(self, envelope: Dict[str, Any] | None, *, tenant_id: str,
                           feature: str, current_usage: int = 0, as_of: str | None = None) -> Dict[str, Any]:
        """Resolve a commercial feature without ever licensing access to the customer's brain."""
        self._required(tenant_id, feature)
        if feature in OWNERSHIP_FEATURES:
            return {"allowed": True, "reason": "customer_ownership_invariant", "commercial_charge": False}
        if not envelope:
            return {"allowed": False, "reason": "entitlement_missing", "commercial_charge": False}
        verified = self.verify_licence(envelope, tenant_id=tenant_id, as_of=as_of)
        if not verified["valid"]:
            return {"allowed": False, "reason": verified["reason"], "commercial_charge": False}
        if feature not in set(verified["features"]):
            return {"allowed": False, "reason": "feature_not_entitled", "commercial_charge": False}
        limit = verified["limits"].get(feature)
        if limit is not None and int(current_usage) >= int(limit):
            return {"allowed": False, "reason": "entitlement_limit_reached", "limit": int(limit),
                    "commercial_charge": False}
        return {"allowed": True, "reason": "signed_entitlement", "edition": verified["edition"],
                "limit": int(limit) if limit is not None else None, "commercial_charge": feature not in CORE_FEATURES}

    def record_optional_usage(self, *, usage_id: str, tenant_id: str, capability: str,
                              provider: str, units: float, unit_name: str, cost: float,
                              currency: str, provider_receipt_ref: str,
                              metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        self._required(usage_id, tenant_id, capability, provider, unit_name, currency, provider_receipt_ref)
        if float(units) < 0 or float(cost) < 0:
            raise ValueError("usage_value_invalid")
        metadata = dict(metadata or {})
        if any(CONTENT_KEYS.search(str(key)) or CONTENT_KEYS.search(str(value)) for key, value in metadata.items()):
            raise ValueError("private_content_not_permitted_in_meter")
        if any(str(key) not in METER_METADATA_KEYS for key in metadata):
            raise ValueError("meter_metadata_key_not_allowed")
        records = self._records(self.meter_path)
        if any(item["usage_id"] == usage_id for item in records):
            raise ValueError("usage_id_reused")
        record = {"schema_version": "aion.optional_service_usage.v1", "usage_id": usage_id,
                  "tenant_id": tenant_id, "capability": capability, "provider": provider,
                  "units": float(units), "unit_name": unit_name, "cost": float(cost),
                  "currency": currency.upper(), "provider_receipt_hash": canonical_hash(provider_receipt_ref),
                  "metadata": metadata, "customer_content_stored": False, "recorded_at": utc_now_iso()}
        records.append(record)
        self._write(self.meter_path, records)
        return record

    def usage_summary(self, *, tenant_id: str) -> Dict[str, Any]:
        records = [item for item in self._records(self.meter_path) if item["tenant_id"] == tenant_id]
        totals: Dict[str, float] = {}
        for item in records:
            totals[item["currency"]] = totals.get(item["currency"], 0.0) + item["cost"]
        return {"tenant_id": tenant_id, "records": records, "totals_by_currency": totals,
                "cross_currency_total_suppressed": len(totals) > 1, "private_content_monetized": False}

    def configure_telemetry(self, *, tenant_id: str, actor_id: str,
                            enabled_categories: Iterable[str]) -> Dict[str, Any]:
        allowed = {"availability", "performance", "security", "update", "billing"}
        enabled = sorted({str(item) for item in enabled_categories})
        if not set(enabled) <= allowed:
            raise ValueError("telemetry_category_not_allowed")
        record = {"schema_version": "aion.customer_telemetry_policy.v1", "tenant_id": tenant_id,
                  "enabled_categories": enabled, "disabled_by_default": True,
                  "customer_content_allowed": False, "changed_by": actor_id, "changed_at": utc_now_iso()}
        policies = [item for item in self._records(self.telemetry_path) if item["tenant_id"] != tenant_id]
        policies.append(record)
        self._write(self.telemetry_path, policies)
        return record

    def record_diagnostic(self, *, tenant_id: str, category: str, component: str,
                          status: str, duration_ms: int | None = None,
                          error_code: str = "") -> Dict[str, Any]:
        policy = next((item for item in self._records(self.telemetry_path) if item["tenant_id"] == tenant_id), None)
        if not policy or category not in set(policy["enabled_categories"]):
            raise PermissionError("telemetry_not_consented")
        record = {"schema_version": "aion.zero_content_diagnostic.v1", "tenant_id": tenant_id,
                  "category": category, "component": component, "status": status,
                  "duration_ms": int(duration_ms) if duration_ms is not None else None,
                  "error_code": error_code, "customer_content_stored": False, "recorded_at": utc_now_iso()}
        records = self._records(self.diagnostics_path)
        records.append(record)
        self._write(self.diagnostics_path, records[-5000:])
        return record

    @staticmethod
    def operational_commitments() -> Dict[str, Any]:
        return {
            "schema_version": "aion.operational_commitments.v1",
            "service_levels": {
                "community": {"response_target": "no_contractual_target"},
                "business_hours": {"response_target": "published_plan_required"},
                "standard": {"response_target": "published_plan_required"},
                "priority": {"response_target": "published_plan_required"},
                "contracted_sla": {"response_target": "customer_contract"},
            },
            "disaster_recovery": {"encrypted_backup_required": True, "restore_test_required": True,
                                  "customer_selected_rpo_rto": True},
            "incident_response": {"severity_levels": ["critical", "high", "medium", "low"],
                                  "customer_notification_required": True, "content_access_default": "none"},
            "vulnerability_disclosure": {"published_security_contact_required": True,
                                         "safe_harbour_review_required": True},
            "current_contractual_sla_claimed": False,
        }

    @staticmethod
    def public_ownership_guarantees() -> Dict[str, Any]:
        return {
            "schema_version": "aion.public_ownership_guarantees.v1",
            "customer_owns_brain_and_business_map": True,
            "provider_can_be_replaced": True,
            "customer_export_and_restore": True,
            "provider_disclosure_before_external_send": True,
            "private_content_not_required_for_licensing_or_metering": True,
            "premium_model_not_required_for_core_operation": True,
            "token_or_blockchain_not_required": True,
            "plain_language": "Your brain and business map remain yours. Models and compute providers are replaceable. Optional paid usage is measured without selling or copying your private content.",
        }

    @staticmethod
    def external_release_gates() -> Dict[str, Any]:
        return {"independent_penetration_test": "required", "software_supply_chain_review": "required",
                "launch_region_legal_and_privacy_assessment": "required",
                "employment_and_sector_assessment": "required",
                "small_business_field_pilot": "required", "medium_multi_unit_field_pilot": "required",
                "all_satisfied": False}

    @staticmethod
    def _required(*values: str) -> None:
        if any(not str(value or "").strip() for value in values):
            raise ValueError("required_value_missing")

    @staticmethod
    def _datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    @classmethod
    def _iso(cls, value: str) -> str:
        return cls._datetime(value).astimezone(UTC).isoformat()

    @staticmethod
    def _records(path: Path) -> list[Dict[str, Any]]:
        if not path.exists():
            return []
        return list(json.loads(path.read_text(encoding="utf-8")).get("records") or [])

    @staticmethod
    def _write(path: Path, records: list[Dict[str, Any]]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"records": records}, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
