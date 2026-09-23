"""Evidence-gated business improvement without hidden authority expansion."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


SENSITIVE = re.compile(r"(password|secret|token|private.?key|api.?key|cvv|card.?number|medical|salary)", re.I)
ALLOWED_DATASET_LICENSES = {"customer_owned", "consented_internal", "cc0", "cc-by-4.0", "apache-2.0", "mit"}


class GovernedImprovementService:
    """Stores evidence and promotes only reviewed, reversible improvements."""

    def __init__(self, root: str | Path, *, freshness_days: int = 30, minimum_retention_days: int = 1) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.freshness_days = max(1, int(freshness_days))
        self.minimum_retention_days = max(1, int(minimum_retention_days))
        self.corrections_path = self.root / "corrections.json"
        self.outcomes_path = self.root / "verified_outcomes.json"
        self.preferences_path = self.root / "route_preferences.json"
        self.automations_path = self.root / "automation_proposals.json"
        self.datasets_path = self.root / "curated_datasets.json"
        self.releases_path = self.root / "model_releases.json"
        self.changes_path = self.root / "customer_change_log.json"

    def record_correction(self, *, correction_id: str, task_class: str, target_ref: str,
                          corrected_value: Any, actor_id: str, conversation_ref: str = "") -> Dict[str, Any]:
        self._required(correction_id, task_class, target_ref, actor_id)
        records = self._records(self.corrections_path)
        if any(item["correction_id"] == correction_id for item in records):
            raise ValueError("correction_id_reused")
        record = {
            "schema_version": "aion.business_correction.v1", "correction_id": correction_id,
            "task_class": task_class, "target_ref": target_ref,
            "corrected_value_hash": canonical_hash(corrected_value), "actor_id": actor_id,
            "conversation_ref_hash": canonical_hash(conversation_ref) if conversation_ref else "",
            "recorded_at": utc_now_iso(), "conversation_content_stored": False,
            "authority_added": False,
        }
        records.append(record)
        self._save_records(self.corrections_path, records)
        self._change("correction_recorded", actor_id, record, reversible=False)
        return record

    def record_outcome(self, *, outcome_id: str, task_class: str, route_id: str,
                       procedure_id: str, verified: bool, authority_ref: str,
                       score: float, observed_at: str | None = None,
                       unfamiliar: bool = False, source_disjoint: bool = False) -> Dict[str, Any]:
        self._required(outcome_id, task_class, route_id, procedure_id, authority_ref)
        if not 0 <= float(score) <= 1:
            raise ValueError("outcome_score_out_of_range")
        records = self._records(self.outcomes_path)
        if any(item["outcome_id"] == outcome_id for item in records):
            raise ValueError("outcome_id_reused")
        record = {
            "schema_version": "aion.verified_business_outcome.v1", "outcome_id": outcome_id,
            "task_class": task_class, "route_id": route_id, "procedure_id": procedure_id,
            "verified": bool(verified), "authority_ref": authority_ref, "score": float(score),
            "observed_at": self._iso(observed_at or utc_now_iso()), "unfamiliar": bool(unfamiliar),
            "source_disjoint": bool(source_disjoint), "conversation_content_stored": False,
        }
        record["evidence_hash"] = canonical_hash(record)
        records.append(record)
        self._save_records(self.outcomes_path, records)
        self.refresh_preference(task_class=task_class)
        return record

    def refresh_preference(self, *, task_class: str, as_of: str | None = None) -> Dict[str, Any]:
        now = self._datetime(as_of or utc_now_iso())
        fresh_after = now - timedelta(days=self.freshness_days)
        outcomes = [item for item in self._records(self.outcomes_path)
                    if item["task_class"] == task_class and item["verified"] and self._datetime(item["observed_at"]) >= fresh_after]
        groups: Dict[tuple[str, str], list[Dict[str, Any]]] = {}
        for item in outcomes:
            groups.setdefault((item["route_id"], item["procedure_id"]), []).append(item)
        ranked = []
        for (route_id, procedure_id), rows in groups.items():
            ranked.append({"route_id": route_id, "procedure_id": procedure_id, "verified_samples": len(rows),
                           "mean_score": sum(row["score"] for row in rows) / len(rows),
                           "latest_verified_at": max(row["observed_at"] for row in rows)})
        ranked.sort(key=lambda item: (item["mean_score"], item["verified_samples"], item["latest_verified_at"]), reverse=True)
        preferred = ranked[0] if ranked and ranked[0]["verified_samples"] >= 3 else None
        record = {"schema_version": "aion.business_route_preference.v1", "task_class": task_class,
                  "status": "preferred" if preferred else "insufficient_fresh_evidence", "preferred": preferred,
                  "candidates": ranked, "valid_until": (now + timedelta(days=self.freshness_days)).isoformat(),
                  "authority_added": False, "updated_at": now.isoformat()}
        preferences = [item for item in self._records(self.preferences_path) if item["task_class"] != task_class]
        preferences.append(record)
        self._save_records(self.preferences_path, preferences)
        return record

    def preference(self, *, task_class: str, as_of: str | None = None) -> Dict[str, Any]:
        current = next((item for item in self._records(self.preferences_path) if item["task_class"] == task_class), None)
        if not current:
            return {"task_class": task_class, "status": "no_preference", "preferred": None}
        now = self._datetime(as_of or utc_now_iso())
        if now > self._datetime(current["valid_until"]):
            return {**current, "status": "stale_revalidation_required", "preferred": None}
        return current

    def propose_automation(self, *, task_class: str, proposed_by: str, minimum_repetitions: int = 5) -> Dict[str, Any]:
        self._required(task_class, proposed_by)
        outcomes = [item for item in self._records(self.outcomes_path) if item["task_class"] == task_class and item["verified"] and item["score"] >= .8]
        if len(outcomes) < max(3, int(minimum_repetitions)):
            raise ValueError("repeated_verified_evidence_required")
        preference = self.preference(task_class=task_class)
        if preference.get("status") != "preferred":
            raise ValueError("fresh_preference_required")
        preferred = preference["preferred"]
        matching = [item for item in outcomes if item["route_id"] == preferred["route_id"] and item["procedure_id"] == preferred["procedure_id"]]
        if len(matching) < max(3, int(minimum_repetitions)):
            raise ValueError("repeated_preferred_route_evidence_required")
        proposal_id = f"automation.{canonical_hash({'task_class': task_class, 'evidence': [item['evidence_hash'] for item in matching]})[:20]}"
        existing = next((item for item in self._records(self.automations_path) if item["proposal_id"] == proposal_id), None)
        if existing:
            return existing
        record = {"schema_version": "aion.automation_proposal.v1", "proposal_id": proposal_id,
                  "task_class": task_class, "route": preferred, "evidence_count": len(matching),
                  "evidence_hashes": [item["evidence_hash"] for item in matching], "proposed_by": proposed_by,
                  "status": "awaiting_owner_approval", "execution_authority": False, "created_at": utc_now_iso()}
        record["proposal_hash"] = canonical_hash(record)
        records = self._records(self.automations_path)
        records.append(record)
        self._save_records(self.automations_path, records)
        return record

    def approve_automation(self, *, proposal_id: str, proposal_hash: str, owner_id: str) -> Dict[str, Any]:
        records = self._records(self.automations_path)
        proposal = next((item for item in records if item["proposal_id"] == proposal_id), None)
        if not proposal or proposal.get("proposal_hash") != proposal_hash:
            raise ValueError("automation_proposal_integrity_failure")
        if proposal.get("status") != "awaiting_owner_approval":
            raise ValueError("automation_proposal_not_approvable")
        proposal.update({"status": "approved_but_unactivated", "approved_by": owner_id,
                         "approved_at": utc_now_iso(), "execution_authority": False})
        self._save_records(self.automations_path, records)
        self._change("automation_approved", owner_id, proposal, reversible=True,
                     reverse_action={"kind": "disable_automation", "proposal_id": proposal_id})
        return proposal

    def curate_dataset(self, *, dataset_id: str, owner_id: str, licence: str, consent_ref: str,
                       source_refs: Iterable[str], records: Iterable[Dict[str, Any]],
                       permitted_purposes: Iterable[str]) -> Dict[str, Any]:
        self._required(dataset_id, owner_id, licence, consent_ref)
        if licence.lower() not in ALLOWED_DATASET_LICENSES:
            raise ValueError("dataset_licence_not_approved")
        rows = list(records)
        for row in rows:
            if any(SENSITIVE.search(str(key)) for key in row):
                raise ValueError("dataset_sensitive_field_requires_prior_redaction")
        purposes = sorted({str(item).strip() for item in permitted_purposes if str(item).strip()})
        if not purposes:
            raise ValueError("dataset_permitted_purpose_required")
        record = {"schema_version": "aion.curated_dataset.v1", "dataset_id": dataset_id,
                  "owner_id": owner_id, "licence": licence.lower(), "consent_ref_hash": canonical_hash(consent_ref),
                  "source_ref_hashes": [canonical_hash(item) for item in source_refs], "record_count": len(rows),
                  "content_hash": canonical_hash(rows), "permitted_purposes": purposes,
                  "raw_content_stored_in_registry": False, "revoked": False, "curated_at": utc_now_iso()}
        datasets = self._records(self.datasets_path)
        if any(item["dataset_id"] == dataset_id for item in datasets):
            raise ValueError("dataset_id_reused")
        datasets.append(record)
        self._save_records(self.datasets_path, datasets)
        return record

    def revoke_dataset(self, *, dataset_id: str, owner_id: str) -> Dict[str, Any]:
        datasets = self._records(self.datasets_path)
        dataset = next((item for item in datasets if item["dataset_id"] == dataset_id), None)
        if not dataset:
            raise KeyError("dataset_not_found")
        dataset.update({"revoked": True, "revoked_by": owner_id, "revoked_at": utc_now_iso()})
        self._save_records(self.datasets_path, datasets)
        return dataset

    def stage_model_release(self, *, release_id: str, base_model_ref: str, dataset_ids: Iterable[str],
                            method: str, reviewed_by: str, rollback_to: str) -> Dict[str, Any]:
        self._required(release_id, base_model_ref, method, reviewed_by, rollback_to)
        if method not in {"fine_tune", "distillation", "adapter"}:
            raise ValueError("model_release_method_not_allowed")
        datasets = {item["dataset_id"]: item for item in self._records(self.datasets_path)}
        selected = list(dataset_ids)
        if not selected or any(item not in datasets or datasets[item].get("revoked") for item in selected):
            raise ValueError("eligible_dataset_required")
        if any(method not in set(datasets[item].get("permitted_purposes") or []) and "model_training" not in set(datasets[item].get("permitted_purposes") or []) for item in selected):
            raise ValueError("dataset_purpose_not_permitted")
        releases = self._records(self.releases_path)
        if any(item["release_id"] == release_id for item in releases):
            raise ValueError("model_release_id_reused")
        record = {"schema_version": "aion.reviewed_model_release.v1", "release_id": release_id,
                  "base_model_ref": base_model_ref, "dataset_ids": selected, "method": method,
                  "reviewed_by": reviewed_by, "rollback_to": rollback_to, "status": "evaluation_required",
                  "active": False, "created_at": utc_now_iso(), "evaluations": []}
        record["release_hash"] = canonical_hash(record)
        releases.append(record)
        self._save_records(self.releases_path, releases)
        return record

    def record_release_evaluation(self, *, release_id: str, evaluation_id: str, cohort: str,
                                  passed: bool, authority_ref: str, observed_at: str | None = None,
                                  source_disjoint: bool = False) -> Dict[str, Any]:
        releases = self._records(self.releases_path)
        release = next((item for item in releases if item["release_id"] == release_id), None)
        if not release:
            raise KeyError("model_release_not_found")
        if any(item["evaluation_id"] == evaluation_id for item in release["evaluations"]):
            raise ValueError("evaluation_id_reused")
        evaluation = {"evaluation_id": evaluation_id, "cohort": cohort, "passed": bool(passed),
                      "authority_ref": authority_ref, "observed_at": self._iso(observed_at or utc_now_iso()),
                      "source_disjoint": bool(source_disjoint)}
        release["evaluations"].append(evaluation)
        self._save_records(self.releases_path, releases)
        return evaluation

    def promote_release(self, *, release_id: str, owner_id: str, as_of: str | None = None) -> Dict[str, Any]:
        releases = self._records(self.releases_path)
        release = next((item for item in releases if item["release_id"] == release_id), None)
        if not release:
            raise KeyError("model_release_not_found")
        cohorts = {item["cohort"] for item in release["evaluations"] if item["passed"]}
        if not {"retention", "unfamiliar_transfer"} <= cohorts:
            raise ValueError("retention_and_unfamiliar_transfer_required")
        if any(item["cohort"] in {"retention", "unfamiliar_transfer"} and not item["passed"] for item in release["evaluations"]):
            raise ValueError("model_release_evaluation_failed")
        transfer = next(item for item in release["evaluations"] if item["cohort"] == "unfamiliar_transfer" and item["passed"])
        if not transfer.get("source_disjoint"):
            raise ValueError("source_disjoint_transfer_required")
        retention = next(item for item in release["evaluations"] if item["cohort"] == "retention" and item["passed"])
        not_before = self._datetime(release["created_at"]) + timedelta(days=self.minimum_retention_days)
        if self._datetime(retention["observed_at"]) < not_before:
            raise ValueError("elapsed_retention_required")
        for item in releases:
            item["active"] = False
        release.update({"active": True, "status": "active", "promoted_by": owner_id,
                        "promoted_at": self._iso(as_of or utc_now_iso())})
        self._save_records(self.releases_path, releases)
        self._change("model_release_promoted", owner_id, release, reversible=True,
                     reverse_action={"kind": "rollback_model_release", "release_id": release_id,
                                     "rollback_to": release["rollback_to"]})
        return release

    def customer_changes(self) -> Dict[str, Any]:
        records = self._records(self.changes_path)
        return {"schema_version": "aion.customer_change_view.v1", "changes": records,
                "count": len(records), "generated_at": utc_now_iso()}

    def reverse_change(self, *, change_id: str, owner_id: str) -> Dict[str, Any]:
        records = self._records(self.changes_path)
        change = next((item for item in records if item["change_id"] == change_id), None)
        if not change or not change.get("reversible"):
            raise ValueError("change_not_reversible")
        if change.get("reversed_at"):
            raise ValueError("change_already_reversed")
        action = dict(change.get("reverse_action") or {})
        if action.get("kind") == "disable_automation":
            automations = self._records(self.automations_path)
            target = next(item for item in automations if item["proposal_id"] == action["proposal_id"])
            target.update({"status": "disabled", "execution_authority": False})
            self._save_records(self.automations_path, automations)
        elif action.get("kind") == "rollback_model_release":
            releases = self._records(self.releases_path)
            for item in releases:
                item["active"] = item["release_id"] == action["rollback_to"]
                if item["release_id"] == action["release_id"]:
                    item["status"] = "rolled_back"
            self._save_records(self.releases_path, releases)
        else:
            raise ValueError("reverse_action_not_supported")
        change.update({"reversed_at": utc_now_iso(), "reversed_by": owner_id})
        self._save_records(self.changes_path, records)
        return change

    def _change(self, kind: str, actor: str, detail: Dict[str, Any], *, reversible: bool,
                reverse_action: Dict[str, Any] | None = None) -> Dict[str, Any]:
        records = self._records(self.changes_path)
        record = {"change_id": f"change.{len(records) + 1:06d}", "kind": kind, "actor": actor,
                  "why": kind.replace("_", " "), "detail_hash": canonical_hash(detail),
                  "reversible": reversible, "reverse_action": reverse_action or {}, "changed_at": utc_now_iso()}
        records.append(record)
        self._save_records(self.changes_path, records)
        return record

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
    def _save_records(path: Path, records: list[Dict[str, Any]]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"records": records}, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
