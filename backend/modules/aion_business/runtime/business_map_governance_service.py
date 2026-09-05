from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict
from uuid import uuid4

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso


GOVERNANCE_VERSION = "aion.business_map_governance.v1"
REVIEW_ACTIONS = {"approve", "correct", "reject", "delete"}
STRUCTURE_RELATIONSHIPS = {
    "services": "offers",
    "revenue_streams": "earns_through",
    "cost_items": "incurs_cost",
    "payment_terms": "uses_payment_term",
    "fulfillment_processes": "fulfills_through",
    "functions": "has_function",
    "teams": "has_team",
    "human_agents": "has_human_agent",
    "ai_agents": "has_ai_agent",
    "channels": "uses_channel",
}
_LOCK = RLock()


class BusinessMapGovernanceService:
    """Lifecycle controls over the existing Boardroom BusinessMapContainer."""

    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def propose_fact(
        self,
        workspace_id: str,
        *,
        field: str,
        value: Any,
        source_ref: str,
        confidence: float,
        proposed_by: str,
        function: str = "business",
        category: str = "foundation",
        review_owner_id: str | None = None,
        effective_from: str | None = None,
        effective_until: str | None = None,
        expected_revision: int | None = None,
    ) -> Dict[str, Any]:
        field_name = str(field or "").strip()
        source = str(source_ref or "").strip()
        actor = str(proposed_by or "").strip()
        if not field_name:
            raise ValueError("business_map_field_required")
        if value in (None, ""):
            raise ValueError("business_map_value_required")
        if not source:
            raise ValueError("business_map_source_required")
        if not actor:
            raise ValueError("business_map_proposer_required")
        score = float(confidence)
        if not 0 <= score <= 1:
            raise ValueError("business_map_confidence_out_of_range")
        self._parse_optional_time(effective_from)
        self._parse_optional_time(effective_until)
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            fact = {
                "fact_id": f"bmf_{uuid4().hex}",
                "workspace_id": workspace_id,
                "function": str(function or "business").strip(),
                "category": str(category or "foundation").strip(),
                "field": field_name,
                "value": value,
                "source_ref": source,
                "confidence": score,
                "review_state": "proposed",
                "verification_status": "awaiting_owner_review",
                "proposed_by": actor,
                "review_owner_id": str(review_owner_id or "").strip() or None,
                "effective_from": effective_from,
                "effective_until": effective_until,
                "observed_at": utc_now_iso(),
                "created_at": utc_now_iso(),
            }
            model.facts.append(fact)
            model.revision = int(model.revision or 0) + 1
            model.meta.updated_at = utc_now_iso()
            model.meta.source = "business_map_governance"
            self.repository.save_model(model)
            receipt = self._receipt(workspace_id, "fact_proposed", fact, model.revision)
            return {"ok": True, "fact": fact, "revision": model.revision, "receipt": receipt}

    def review_fact(
        self,
        workspace_id: str,
        fact_id: str,
        *,
        action: str,
        actor_id: str,
        expected_revision: int | None = None,
        corrected_value: Any = None,
        reason: str = "",
        confirm_delete: bool = False,
    ) -> Dict[str, Any]:
        decision = str(action or "").strip().lower()
        actor = str(actor_id or "").strip()
        if decision not in REVIEW_ACTIONS:
            raise ValueError("business_map_review_action_invalid")
        if not actor:
            raise ValueError("business_map_review_actor_required")
        if decision == "correct" and corrected_value in (None, ""):
            raise ValueError("business_map_corrected_value_required")
        if decision == "delete" and confirm_delete is not True:
            raise PermissionError("business_map_delete_confirmation_required")
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            index = next((i for i, item in enumerate(model.facts) if item.get("fact_id") == fact_id), None)
            if index is None:
                raise KeyError("business_map_fact_not_found")
            before = dict(model.facts[index])
            now = utc_now_iso()
            if decision == "delete":
                model.facts.pop(index)
                after = None
            else:
                fact = dict(before)
                history = list(fact.get("revision_history") or [])[-19:]
                if decision == "correct":
                    history.append({
                        "value_hash": canonical_hash({"value": fact.get("value")}),
                        "changed_at": now,
                        "changed_by": actor,
                    })
                    fact["value"] = corrected_value
                    fact["review_state"] = "approved"
                    fact["verification_status"] = "owner_corrected"
                    fact["revision_history"] = history
                elif decision == "approve":
                    fact["review_state"] = "approved"
                    fact["verification_status"] = "owner_attested"
                else:
                    fact["review_state"] = "rejected"
                    fact["verification_status"] = "owner_rejected"
                fact["reviewed_by"] = actor
                fact["reviewed_at"] = now
                fact["review_reason"] = str(reason or "").strip()[:500]
                model.facts[index] = fact
                after = fact
            model.revision = int(model.revision or 0) + 1
            model.meta.updated_at = now
            model.meta.source = "business_map_governance"
            self.repository.save_model(model)
            evidence = {
                "fact_id": fact_id,
                "action": decision,
                "actor_id": actor,
                "before_hash": canonical_hash(before),
                "after_hash": canonical_hash(after) if after is not None else None,
                "reason": str(reason or "").strip()[:500],
            }
            receipt = self._receipt(workspace_id, f"fact_{decision}", evidence, model.revision)
            return {"ok": True, "fact": after, "deleted": decision == "delete", "revision": model.revision, "receipt": receipt}

    def merge_facts(
        self,
        workspace_id: str,
        *,
        primary_fact_id: str,
        duplicate_fact_id: str,
        actor_id: str,
        expected_revision: int | None = None,
    ) -> Dict[str, Any]:
        if not actor_id.strip():
            raise ValueError("business_map_review_actor_required")
        if primary_fact_id == duplicate_fact_id:
            raise ValueError("business_map_merge_requires_distinct_facts")
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            primary_index = next((i for i, item in enumerate(model.facts) if item.get("fact_id") == primary_fact_id), None)
            duplicate_index = next((i for i, item in enumerate(model.facts) if item.get("fact_id") == duplicate_fact_id), None)
            if primary_index is None or duplicate_index is None:
                raise KeyError("business_map_fact_not_found")
            primary = dict(model.facts[primary_index])
            duplicate = dict(model.facts[duplicate_index])
            if str(primary.get("field") or "") != str(duplicate.get("field") or ""):
                raise ValueError("business_map_merge_field_mismatch")
            now = utc_now_iso()
            primary["merged_fact_hashes"] = list(dict.fromkeys([
                *(primary.get("merged_fact_hashes") or []), canonical_hash(duplicate)
            ]))[-20:]
            primary["merged_source_refs"] = list(dict.fromkeys([
                primary.get("source_ref"), *(primary.get("merged_source_refs") or []), duplicate.get("source_ref")
            ]))[-20:]
            primary["review_state"] = "approved"
            primary["verification_status"] = "owner_merged"
            primary["reviewed_by"] = actor_id.strip()
            primary["reviewed_at"] = now
            model.facts[primary_index] = primary
            model.facts.pop(duplicate_index)
            model.revision = int(model.revision or 0) + 1
            model.meta.updated_at = now
            model.meta.source = "business_map_governance"
            self.repository.save_model(model)
            evidence = {"primary_fact_id": primary_fact_id, "duplicate_fact_hash": canonical_hash(duplicate), "actor_id": actor_id.strip()}
            return {"ok": True, "fact": primary, "revision": model.revision, "receipt": self._receipt(workspace_id, "facts_merged", evidence, model.revision)}

    def propose_relationship(
        self,
        workspace_id: str,
        *,
        from_id: str,
        relationship_type: str,
        to_id: str,
        source_ref: str,
        confidence: float,
        proposed_by: str,
        review_owner_id: str | None = None,
        expected_revision: int | None = None,
    ) -> Dict[str, Any]:
        values = [str(value or "").strip() for value in (from_id, relationship_type, to_id, source_ref, proposed_by)]
        if not all(values):
            raise ValueError("business_map_relationship_fields_required")
        score = float(confidence)
        if not 0 <= score <= 1:
            raise ValueError("business_map_confidence_out_of_range")
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            triple = tuple(values[:3])
            if any(tuple(str(item.get(key) or "").strip() for key in ("from_id", "relationship_type", "to_id")) == triple for item in model.relationships):
                raise ValueError("business_map_relationship_duplicate")
            relationship = {
                "relationship_id": f"bmr_{uuid4().hex}", "workspace_id": workspace_id,
                "from_id": values[0], "relationship_type": values[1], "to_id": values[2],
                "source_ref": values[3], "confidence": score, "review_state": "proposed",
                "verification_status": "awaiting_owner_review", "proposed_by": values[4],
                "review_owner_id": str(review_owner_id or "").strip() or None,
                "observed_at": utc_now_iso(), "created_at": utc_now_iso(),
            }
            model.relationships.append(relationship)
            self._save_model(model)
            return {"ok": True, "relationship": relationship, "revision": model.revision, "receipt": self._receipt(workspace_id, "relationship_proposed", relationship, model.revision)}

    def review_relationship(self, workspace_id: str, relationship_id: str, *, action: str, actor_id: str, expected_revision: int | None = None, corrected_from_id: str | None = None, corrected_relationship_type: str | None = None, corrected_to_id: str | None = None, reason: str = "", confirm_delete: bool = False) -> Dict[str, Any]:
        decision = str(action or "").strip().lower()
        actor = str(actor_id or "").strip()
        if decision not in REVIEW_ACTIONS:
            raise ValueError("business_map_review_action_invalid")
        if not actor:
            raise ValueError("business_map_review_actor_required")
        if decision == "delete" and confirm_delete is not True:
            raise PermissionError("business_map_delete_confirmation_required")
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            index = next((i for i, item in enumerate(model.relationships) if item.get("relationship_id") == relationship_id), None)
            if index is None:
                raise KeyError("business_map_relationship_not_found")
            before = dict(model.relationships[index])
            now = utc_now_iso()
            if decision == "delete":
                model.relationships.pop(index)
                after = None
            else:
                relationship = dict(before)
                if decision == "correct":
                    replacements = {
                        "from_id": corrected_from_id,
                        "relationship_type": corrected_relationship_type,
                        "to_id": corrected_to_id,
                    }
                    if not any(str(value or "").strip() for value in replacements.values()):
                        raise ValueError("business_map_relationship_correction_required")
                    for key, value in replacements.items():
                        if str(value or "").strip():
                            relationship[key] = str(value).strip()
                    relationship["verification_status"] = "owner_corrected"
                    relationship["review_state"] = "approved"
                elif decision == "approve":
                    relationship["review_state"] = "approved"
                    relationship["verification_status"] = "owner_attested"
                else:
                    relationship["review_state"] = "rejected"
                    relationship["verification_status"] = "owner_rejected"
                relationship["reviewed_by"] = actor
                relationship["reviewed_at"] = now
                relationship["review_reason"] = str(reason or "").strip()[:500]
                model.relationships[index] = relationship
                after = relationship
            self._save_model(model, now=now)
            evidence = {"relationship_id": relationship_id, "action": decision, "actor_id": actor, "before_hash": canonical_hash(before), "after_hash": canonical_hash(after) if after else None}
            return {"ok": True, "relationship": after, "deleted": decision == "delete", "revision": model.revision, "receipt": self._receipt(workspace_id, f"relationship_{decision}", evidence, model.revision)}

    def normalize_legacy_relationships(self, workspace_id: str, *, actor_id: str, expected_revision: int | None = None) -> Dict[str, Any]:
        actor = str(actor_id or "").strip()
        if not actor:
            raise ValueError("business_map_review_actor_required")
        with _LOCK:
            model = self.repository.load_business_map(workspace_id)
            self._check_revision(model.revision, expected_revision)
            normalized, derived = 0, 0
            existing: set[tuple[str, str, str]] = set()
            for position, raw in enumerate(model.relationships):
                relationship = dict(raw)
                relationship.setdefault("relationship_id", f"bmr_{canonical_hash({'workspace': workspace_id, 'position': position, 'relationship': raw})[-24:]}")
                relationship.setdefault("source_ref", f"legacy_business_map:relationships:{position + 1}")
                relationship.setdefault("confidence", 0.5)
                relationship.setdefault("review_state", "proposed")
                relationship.setdefault("verification_status", "legacy_relationship_pending_review")
                relationship.setdefault("review_owner_id", actor)
                relationship.setdefault("provenance_quality", "legacy_storage_location_only")
                relationship.setdefault("created_at", utc_now_iso())
                if relationship != raw:
                    normalized += 1
                    model.relationships[position] = relationship
                existing.add(tuple(str(relationship.get(key) or "").strip() for key in ("from_id", "relationship_type", "to_id")))
            try:
                structure = self.repository.load_business_structure(workspace_id)
            except FileNotFoundError:
                structure = None
            if structure:
                root_id = f"business:{workspace_id}"
                for collection, relation_type in STRUCTURE_RELATIONSHIPS.items():
                    for item in getattr(structure, collection):
                        item_id = str(item.get("id") or "").strip()
                        if not item_id:
                            continue
                        triple = (root_id, relation_type, item_id)
                        if triple in existing:
                            continue
                        model.relationships.append({
                            "relationship_id": f"bmr_{uuid4().hex}", "workspace_id": workspace_id,
                            "from_id": root_id, "relationship_type": relation_type, "to_id": item_id,
                            "source_ref": f"business_structure:{collection}:{item_id}", "confidence": 1.0,
                            "review_state": "proposed", "verification_status": "persisted_structure_pending_relationship_review",
                            "proposed_by": "deterministic_structure_normalizer", "review_owner_id": actor,
                            "provenance_quality": "explicit_persisted_structure", "created_at": utc_now_iso(),
                        })
                        existing.add(triple)
                        derived += 1
            if normalized or derived:
                self._save_model(model)
            evidence = {"normalized": normalized, "derived": derived, "relationship_count": len(model.relationships)}
            return {"ok": True, **evidence, "revision": model.revision, "receipt": self._receipt(workspace_id, "legacy_relationships_normalized", evidence, model.revision)}

    def queues(self, workspace_id: str, *, now: datetime | None = None) -> Dict[str, Any]:
        model = self.repository.load_business_map(workspace_id)
        instant = now or datetime.now(timezone.utc)
        proposed, stale, missing_provenance, missing_review_owner = [], [], [], []
        for fact in model.facts:
            if fact.get("review_state", "proposed") == "proposed":
                proposed.append(fact)
                if not fact.get("review_owner_id"):
                    missing_review_owner.append(fact)
            if not fact.get("source_ref") or fact.get("confidence") is None:
                missing_provenance.append(fact)
            until = self._parse_optional_time(fact.get("effective_until"))
            if fact.get("review_state") == "stale" or (until is not None and until < instant):
                stale.append(fact)
        queues = {
            "proposed": proposed,
            "stale": stale,
            "missing_provenance": missing_provenance,
            "missing_review_owner": missing_review_owner,
            "unknowns": model.unknowns,
            "conflicts": model.conflicts,
            "unanswered_fields": model.unanswered_fields,
            "department_discovery_gaps": model.department_discovery_gaps,
            "relationships_proposed": [item for item in model.relationships if item.get("review_state", "proposed") == "proposed"],
            "relationships_missing_provenance": [item for item in model.relationships if not item.get("source_ref") or item.get("confidence") is None],
            "relationships_missing_review_owner": [item for item in model.relationships if item.get("review_state", "proposed") == "proposed" and not item.get("review_owner_id")],
        }
        return {
            "ok": True,
            "schema_version": GOVERNANCE_VERSION,
            "workspace_id": workspace_id,
            "revision": model.revision,
            "queues": queues,
            "counts": {name: len(items) for name, items in queues.items()},
        }

    def export(self, workspace_id: str) -> Dict[str, Any]:
        payload = self.repository.load_business_map(workspace_id).model_dump(mode="json")
        return {
            "schema_version": GOVERNANCE_VERSION,
            "workspace_id": workspace_id,
            "source_of_truth": "boardroom_business_containers",
            "business_map": payload,
            "content_hash": canonical_hash(payload),
            "exported_at": utc_now_iso(),
        }

    def _receipt(self, workspace_id: str, action: str, evidence: Dict[str, Any], revision: int) -> Dict[str, Any]:
        payload = {
            "schema_version": GOVERNANCE_VERSION,
            "receipt_id": f"bmg_{uuid4().hex}",
            "workspace_id": workspace_id,
            "action": action,
            "business_map_revision": revision,
            "evidence_hash": canonical_hash(evidence),
            "created_at": utc_now_iso(),
        }
        path = self.repository.base_dir / workspace_id / "business_map_governance.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as handle:
            handle.write(canonical_bytes(payload) + b"\n")
        return payload

    def _save_model(self, model: Any, *, now: str | None = None) -> None:
        model.revision = int(model.revision or 0) + 1
        model.meta.updated_at = now or utc_now_iso()
        model.meta.source = "business_map_governance"
        self.repository.save_model(model)

    @staticmethod
    def _check_revision(current: int, expected: int | None) -> None:
        if expected is not None and int(expected) != int(current):
            raise ValueError("business_map_revision_conflict")

    @staticmethod
    def _parse_optional_time(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("business_map_time_invalid") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
