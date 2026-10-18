from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

from .canonical import canonical_hash, utc_now_iso
from .contracts import CapabilityCapsule, DeviceProfile, EnrollmentState, NodeRecord, NodeRole
from .delta import DeltaPacket, GlyphDeltaStream, apply_state_delta
from .discovery import DiscoveryObservation, DiscoveryRun
from .field_operator import FieldActionProposal
from .probe import ReadOnlyProbeReceipt
from .schema import ControlSurface, DeviceSchema, DocumentationArtifact
from .webos import WebOsActionReceipt, WebOsIntegrationReceipt, WebOsPairingReceipt


class GuardianFabricStore:
    """Encrypted authority for customer-owned Fabric topology and evidence."""

    _audit_lock = threading.RLock()

    def __init__(self, *, workspace_id: str, domain_store: VaultDomainStore) -> None:
        self.workspace_id = workspace_id
        self.domain_store = domain_store

    @staticmethod
    def _entity(kind: str, identity: str) -> str:
        return f"fabric.{kind}.{identity}"

    def _put_record(self, kind: str, identity: str, payload: Dict[str, Any]) -> None:
        entity_id = self._entity(kind, identity)
        existing = self.domain_store.get_optional(
            "security.records", workspace_id=self.workspace_id, entity_id=entity_id,
        )
        self.domain_store.put(
            "security.records",
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            payload={"record_type": kind, "record": payload, "updated_at": utc_now_iso()},
            expected_version=int(existing["version"]) if existing else None,
        )

    def _get_record(self, kind: str, identity: str) -> Dict[str, Any] | None:
        result = self.domain_store.get_optional(
            "security.records",
            workspace_id=self.workspace_id,
            entity_id=self._entity(kind, identity),
        )
        if result is None:
            return None
        payload = result["payload"]
        if payload.get("record_type") != kind or not isinstance(payload.get("record"), dict):
            raise RuntimeError("guardian_fabric_record_type_mismatch")
        return dict(payload["record"])

    def _list_records(self, kind: str) -> list[Dict[str, Any]]:
        output = []
        for result in self.domain_store.list("security.records", workspace_id=self.workspace_id):
            payload = result["payload"]
            if payload.get("record_type") == kind and isinstance(payload.get("record"), dict):
                output.append(dict(payload["record"]))
        return output

    def _audit_state(self) -> tuple[Dict[str, Any], int | None]:
        result = self.domain_store.get_optional(
            "security.audit", workspace_id=self.workspace_id, entity_id="fabric.audit-ledger",
        )
        if result is None:
            return {"schema_version": "tessaris.fabric-audit.v1", "events": []}, None
        return dict(result["payload"]), int(result["version"])

    def append_audit(self, event_type: str, payload: Dict[str, Any]) -> str:
        with self._audit_lock:
            state, version = self._audit_state()
            events = list(state.get("events") or [])
            previous_hash = events[-1]["event_hash"] if events else "0" * 64
            event = {
                "event_id": f"fabric_event_{uuid4().hex}",
                "event_type": str(event_type),
                "payload": dict(payload),
                "previous_hash": previous_hash,
                "created_at": utc_now_iso(),
            }
            event["event_hash"] = canonical_hash(event)
            events.append(event)
            state["events"] = events[-4096:]
            state["pruned_event_count"] = int(state.get("pruned_event_count") or 0) + max(
                0, len(events) - len(state["events"]),
            )
            state["anchor_hash"] = state["events"][0]["previous_hash"] if state["events"] else "0" * 64
            self.domain_store.put(
                "security.audit",
                workspace_id=self.workspace_id,
                entity_id="fabric.audit-ledger",
                payload=state,
                expected_version=version,
            )
            return event["event_hash"]

    def save_node(self, record: NodeRecord) -> None:
        self._put_record("node", record.profile.node_id, record.to_dict())
        self.append_audit("node_saved", {
            "node_id": record.profile.node_id,
            "role": record.role.value,
            "enrollment": record.enrollment.value,
        })

    @staticmethod
    def _node(value: Dict[str, Any]) -> NodeRecord:
        return NodeRecord(
            profile=DeviceProfile.from_dict(value["profile"]),
            role=NodeRole(value["role"]),
            public_key=value["public_key"],
            enrollment=EnrollmentState(value["enrollment"]),
            mother_id=value.get("mother_id"),
            last_seen_at=value["last_seen_at"],
        )

    def get_node(self, node_id: str) -> NodeRecord | None:
        value = self._get_record("node", node_id)
        return self._node(value) if value else None

    def list_nodes(self) -> list[NodeRecord]:
        return sorted((self._node(value) for value in self._list_records("node")), key=lambda x: x.profile.node_id)

    def save_capsule(self, capsule: CapabilityCapsule) -> None:
        self._put_record("capability", capsule.capsule_id, capsule.to_dict())
        self.append_audit("capability_capsule_issued", {
            "capsule_id": capsule.capsule_id, "subject_node_id": capsule.subject_node_id,
        })

    def latest_capsule_for_node(self, node_id: str) -> CapabilityCapsule | None:
        values = [value for value in self._list_records("capability") if value.get("subject_node_id") == node_id]
        if not values:
            return None
        return CapabilityCapsule(**max(values, key=lambda value: value.get("issued_at") or ""))

    def state_for(self, node_id: str) -> tuple[int, Dict[str, Any], str]:
        value = self._get_record("node_state", node_id)
        if not value:
            empty: Dict[str, Any] = {}
            return 0, empty, canonical_hash(empty)
        return int(value["sequence"]), dict(value["state"]), str(value["state_hash"])

    def accept_delta(self, packet: DeltaPacket, *, public_key: str) -> Dict[str, Any]:
        if not packet.verify(public_key):
            raise ValueError("Delta signature or payload hash is invalid")
        sequence, previous, previous_hash = self.state_for(packet.node_id)
        if packet.sequence != sequence + 1:
            raise ValueError(f"Delta sequence mismatch: expected {sequence + 1}, got {packet.sequence}")
        if packet.base_state_hash != previous_hash:
            raise ValueError("Delta base state does not match the mother ledger")
        current = apply_state_delta(previous, packet.changes)
        if canonical_hash(current) != packet.result_state_hash:
            raise ValueError("Delta result state hash is invalid")
        self._put_record("delta", packet.packet_id, packet.to_dict())
        self._put_record("node_state", packet.node_id, {
            "sequence": packet.sequence, "state": current, "state_hash": packet.result_state_hash,
        })
        self.append_audit("delta_accepted", {
            "packet_id": packet.packet_id, "node_id": packet.node_id, "sequence": packet.sequence,
        })
        return current

    def accept_stream(self, stream: GlyphDeltaStream, *, public_key: str) -> Dict[str, Any]:
        if not stream.verify(public_key):
            raise ValueError("Glyph delta stream signature or payload hash is invalid")
        sequence, _, previous_hash = self.state_for(stream.node_id)
        if stream.start_sequence != sequence + 1:
            raise ValueError(f"Stream sequence mismatch: expected {sequence + 1}, got {stream.start_sequence}")
        states = stream.states()
        if canonical_hash(states[0]) != previous_hash:
            raise ValueError("Glyph delta stream base state does not match the mother ledger")
        final_state = states[-1]
        self._put_record("stream", stream.stream_id, {
            "compact": stream.compact_dict(),
            "payload_hash": stream.payload_hash,
            "signature": stream.signature,
            "end_sequence": stream.end_sequence,
        })
        self._put_record("node_state", stream.node_id, {
            "sequence": stream.end_sequence,
            "state": final_state,
            "state_hash": canonical_hash(final_state),
        })
        self.append_audit("glyph_stream_accepted", {
            "stream_id": stream.stream_id,
            "node_id": stream.node_id,
            "start_sequence": stream.start_sequence,
            "end_sequence": stream.end_sequence,
        })
        return final_state

    def save_discovery_run(self, run: DiscoveryRun) -> None:
        self._put_record("discovery_run", run.run_id, run.to_dict())
        for observation in run.observations:
            self._put_record("discovery_observation", observation.observation_id, observation.to_dict())
        self.append_audit("discovery_completed", {
            "run_id": run.run_id, "observations": len(run.observations), "error_count": len(run.errors),
        })

    def list_observations(self) -> list[DiscoveryObservation]:
        return sorted(
            (DiscoveryObservation(**value) for value in self._list_records("discovery_observation")),
            key=lambda item: (item.observed_at, item.observation_id), reverse=True,
        )

    @staticmethod
    def _schema(value: Dict[str, Any]) -> DeviceSchema:
        data = dict(value)
        controls = []
        from .contracts import RiskLevel
        for item in data.get("controls", []):
            control = dict(item)
            control["risk"] = RiskLevel(control["risk"])
            controls.append(ControlSurface(**control))
        data["controls"] = controls
        data["documentation"] = [DocumentationArtifact(**item) for item in data.get("documentation", [])]
        return DeviceSchema(**data)

    def save_schema(self, schema: DeviceSchema) -> None:
        self._put_record("device_schema", schema.schema_id, schema.to_dict())
        self.append_audit("device_schema_generated", {
            "schema_id": schema.schema_id, "node_id": schema.node_id,
            "controls": len(schema.controls), "documents": len(schema.documentation),
        })

    def list_schemas(self) -> list[DeviceSchema]:
        return [self._schema(value) for value in self._list_records("device_schema")]

    def get_schema_for_node(self, node_id: str) -> DeviceSchema | None:
        schemas = [item for item in self.list_schemas() if item.node_id == node_id]
        return max(schemas, key=lambda item: (len(item.controls), len(item.documentation), item.confidence, item.generated_at)) if schemas else None

    def save_action_proposal(self, proposal: FieldActionProposal) -> None:
        self._put_record("action_proposal", proposal.proposal_id, proposal.to_dict())
        self.append_audit("field_action_proposed", {
            "proposal_id": proposal.proposal_id, "node_id": proposal.node_id, "state": proposal.state,
        })

    def save_probe_receipt(self, receipt: ReadOnlyProbeReceipt) -> None:
        self._put_record("probe_receipt", receipt.receipt_id, receipt.to_dict())
        self.append_audit("read_only_probe_completed", {
            "receipt_id": receipt.receipt_id, "node_id": receipt.node_id,
            "action_id": receipt.action_id, "response_status": receipt.response_status,
        })

    def save_webos_pairing_receipt(self, receipt: WebOsPairingReceipt) -> None:
        self._put_record("webos_pairing_receipt", receipt.receipt_id, receipt.to_dict())
        self.append_audit("webos_read_only_pairing_completed", {
            "receipt_id": receipt.receipt_id, "node_id": receipt.node_id,
            "proof_action": receipt.proof_action,
        })

    def save_webos_integration_receipt(self, receipt: WebOsIntegrationReceipt) -> None:
        self._put_record("webos_integration_receipt", receipt.receipt_id, receipt.to_dict())
        self.append_audit("webos_integration_completed", {
            "receipt_id": receipt.receipt_id, "node_id": receipt.node_id,
            "connected_surface_count": len(receipt.connected_surfaces),
        })

    def latest_webos_integration_receipt(self, node_id: str) -> WebOsIntegrationReceipt | None:
        values = [value for value in self._list_records("webos_integration_receipt") if value.get("node_id") == node_id]
        return WebOsIntegrationReceipt(**max(values, key=lambda value: value.get("created_at") or "")) if values else None

    def save_webos_action_receipt(self, receipt: WebOsActionReceipt, *, source: str) -> None:
        self._put_record("webos_action_receipt", receipt.receipt_id, receipt.to_dict())
        self.append_audit("webos_action_verified", {
            "receipt_id": receipt.receipt_id, "node_id": receipt.node_id,
            "action": receipt.action, "source": source, "verified": receipt.verified,
        })

    def counts(self) -> Dict[str, int]:
        mapping = {
            "nodes": "node", "capability_capsules": "capability", "delta_ledger": "delta",
            "stream_ledger": "stream", "discovery_observations": "discovery_observation",
            "device_schemas": "device_schema", "action_proposals": "action_proposal",
            "probe_receipts": "probe_receipt", "webos_pairing_receipts": "webos_pairing_receipt",
            "webos_integration_receipts": "webos_integration_receipt",
            "webos_action_receipts": "webos_action_receipt",
        }
        state, _ = self._audit_state()
        return {**{table: len(self._list_records(kind)) for table, kind in mapping.items()}, "audit_ledger": len(state.get("events") or [])}

    def verify_audit_chain(self) -> bool:
        state, _ = self._audit_state()
        previous = str(state.get("anchor_hash") or "0" * 64)
        for event in state.get("events") or []:
            value = dict(event)
            event_hash = value.pop("event_hash", None)
            if value.get("previous_hash") != previous or canonical_hash(value) != event_hash:
                return False
            previous = str(event_hash)
        return True


def configured_fabric_store(
    path: str | Path,
    *,
    workspace_id: str | None = None,
) -> Any:
    """Select the authoritative Fabric store without production fallback.

    The business stable ID is the Fabric workspace boundary unless an explicit
    workspace is supplied by a caller performing an isolated migration/test.
    """

    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        selected_workspace = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if not selected_workspace:
            raise RuntimeError("aion_fabric_workspace_id_required")
        selected = GuardianFabricStore(
            workspace_id=selected_workspace,
            domain_store=VaultDomainStore(runtime.guardian, actor_id="aion-fabric-runtime"),
        )
        legacy_path = Path(path)
        if legacy_path.exists():
            from .migrate_to_guardian import (
                legacy_source_sha256,
                migrate_legacy_fabric_store,
                migration_receipt_entity_id,
            )
            from .store import FabricStore

            source_hash = legacy_source_sha256(legacy_path)
            receipt = selected.domain_store.get_optional(
                "security.audit",
                workspace_id=selected_workspace,
                entity_id=migration_receipt_entity_id(source_hash),
            )
            if receipt is None:
                migrate_legacy_fabric_store(FabricStore(legacy_path), selected)
            elif not bool(receipt["payload"].get("verified")):
                raise RuntimeError("aion_fabric_guardian_migration_receipt_invalid")
        return selected
    mode = str(os.environ.get("TESSARIS_RUNTIME_MODE") or "development").lower()
    if mode in {"production", "prod"}:
        raise RuntimeError("aion_fabric_guardian_store_required_in_production")
    from .store import FabricStore
    return FabricStore(path)
