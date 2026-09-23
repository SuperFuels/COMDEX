"""Persistent capability registry for progressive competency executors.

The registry separates three facts that were previously conflated:
1. a subject has been selected;
2. some historical benchmark exists for that subject; and
3. a verified executor can satisfy the *current* progressive requirement.

Only (3) permits evidence collection. Missing executors become explicit,
resumable acquisition contracts rather than invisible retry loops.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable, Mapping


LEGACY_CANDIDATES = {
    "advanced_python", "architecture_operations", "database_engineering",
    "distributed_systems", "integrated_engineering_capstone", "networking",
    "operating_systems", "rust_systems", "secure_engineering",
    "software_engineering", "testing_debugging",
}

EXTERNAL_AUTHORITY_GROUPS = {"computing_physical", "human", "creative_engineering"}

FAMILY_BY_GROUP = {
    "computing": "code_and_system_execution",
    "programming": "compiler_and_test_execution",
    "engineering": "software_project_execution",
    "analysis": "data_and_statistical_outcome",
    "formal_reasoning": "proof_and_calculation",
    "science": "empirical_dataset_or_experiment",
    "business": "transaction_or_project_outcome",
    "human_language": "document_and_delayed_question",
    "social": "document_and_human_judgment",
    "creative_engineering": "constraint_and_human_judgment",
    "human": "independent_multi_rater",
    "computing_physical": "physical_sensor_or_simulator",
}


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class ProgressiveExecutorRegistry:
    def __init__(self, *, path: Path) -> None:
        self.path = path
        if path.exists():
            self.state = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "schema_version": "aion.hexcore.progressive_executor_registry.v1",
                "adapters": {}, "gaps": {}, "events": [], "updated_epoch": time.time(),
            }

    def _save(self) -> None:
        self.state["updated_epoch"] = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def family(subject: Mapping[str, Any]) -> str:
        return FAMILY_BY_GROUP.get(str(subject.get("group") or ""), "specialist_outcome_authority")

    def sync_adapters(self, names: Iterable[str]) -> None:
        available = set(names)
        for name in sorted(available):
            self.state["adapters"][name] = {
                "adapter_id": f"progressive:{name}", "subject_id": name,
                "status": "verified_available", "source": "progressive_runner_registry",
                "updated_epoch": time.time(),
            }
        for name, row in self.state["adapters"].items():
            if row.get("source") == "progressive_runner_registry" and name not in available:
                row["status"] = "retired_unavailable"
        for gap in self.state.get("gaps", {}).values():
            if gap.get("subject_id") in available and gap.get("status") == "acquisition_required":
                gap.update({
                    "status": "resolved", "resolved_epoch": time.time(),
                    "resolution": f"progressive:{gap['subject_id']}",
                })
        self._save()

    def adapter_available(self, subject_id: str) -> bool:
        return (self.state.get("adapters", {}).get(subject_id) or {}).get("status") == "verified_available"

    def observe_contract(
        self, *, contract: Mapping[str, Any], subject: Mapping[str, Any],
        available_subjects: Iterable[str], reason: str | None = None,
    ) -> dict[str, Any]:
        self.sync_adapters(available_subjects)
        subject_id = str(contract["subject_id"])
        requirement = dict(contract.get("requirement") or {})
        gap_material = {
            "subject_id": subject_id, "kind": requirement.get("kind"),
            "subskills": requirement.get("subskills") or [],
            "authority": requirement.get("authority"),
        }
        gap_id = "executor_gap_" + _hash(gap_material)[:18]
        if self.adapter_available(subject_id):
            gap = self.state["gaps"].get(gap_id)
            if gap and gap.get("status") != "resolved":
                gap.update({"status": "resolved", "resolved_epoch": time.time(),
                            "resolution": f"progressive:{subject_id}"})
                self._save()
            return {"status": "available", "adapter_id": f"progressive:{subject_id}",
                    "gap_id": gap_id, "subject_id": subject_id}

        family = self.family(subject)
        if str(subject.get("group")) in EXTERNAL_AUTHORITY_GROUPS:
            acquisition = "external_authority_required"
        elif subject_id in LEGACY_CANDIDATES:
            acquisition = "upgrade_legacy_candidate_to_progressive_adapter"
        else:
            acquisition = "invent_and_verify_progressive_adapter"
        prior = self.state["gaps"].get(gap_id) or {}
        gap = {
            **prior, "gap_id": gap_id, **gap_material,
            "subject_name": subject.get("name"), "family": family,
            "status": "acquisition_required", "acquisition_action": acquisition,
            "legacy_candidate_available": subject_id in LEGACY_CANDIDATES,
            "reason": reason or "No verified adapter satisfies the active progressive contract.",
            "first_seen_epoch": prior.get("first_seen_epoch", time.time()),
            "last_seen_epoch": time.time(), "observations": int(prior.get("observations", 0)) + 1,
            "resume_condition": f"verified adapter registered for {subject_id}",
            "proposal_only": True,
        }
        self.state["gaps"][gap_id] = gap
        self.state["events"].append({
            "event": "executor_gap_observed", "gap_id": gap_id,
            "subject_id": subject_id, "epoch": time.time(),
        })
        self.state["events"] = self.state["events"][-1000:]
        self._save()
        return gap

    def summary(self, *, subjects: Mapping[str, Any]) -> dict[str, Any]:
        available = sorted(
            name for name, row in self.state.get("adapters", {}).items()
            if row.get("status") == "verified_available"
        )
        gaps = [row for row in self.state.get("gaps", {}).values()
                if row.get("status") == "acquisition_required"]
        families: dict[str, int] = {}
        for row in gaps:
            families[row["family"]] = families.get(row["family"], 0) + 1
        uncovered = []
        for subject_id, subject in subjects.items():
            if subject_id in available:
                continue
            group = str(subject.get("group") or "")
            uncovered.append({
                "subject_id": subject_id,
                "subject_name": subject.get("name", subject_id),
                "family": self.family(subject),
                "acquisition_action": (
                    "external_authority_required" if group in EXTERNAL_AUTHORITY_GROUPS
                    else "upgrade_legacy_candidate_to_progressive_adapter"
                    if subject_id in LEGACY_CANDIDATES
                    else "invent_and_verify_progressive_adapter"
                ),
            })
        uncovered.sort(key=lambda row: (row["acquisition_action"], row["subject_name"]))
        return {
            "subjects_total": len(subjects), "verified_adapters": len(available),
            "available_subjects": available, "open_gaps": len(gaps),
            "open_gap_families": families,
            "active_acquisitions": sorted(gaps, key=lambda row: row.get("last_seen_epoch", 0), reverse=True)[:10],
            "catalog_coverage_gaps": len(uncovered),
            "uncovered_subjects": uncovered,
            "legacy_candidates": sorted(LEGACY_CANDIDATES),
            "coverage": len(available) / max(1, len(subjects)),
            "updated_epoch": self.state.get("updated_epoch"),
        }
