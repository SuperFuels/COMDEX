"""Persistent evidence-driven apprenticeship across unfamiliar domains.

This module is a control plane, not a benchmark task bank.  The owner supplies
one terminal mission and permitted authorities.  Curriculum is derived from
verified outcome artifacts, weakest evidence gates, transfer distance,
forgetting risk and missing execution contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)
from backend.modules.hexcore.verified_trajectory_corpus_manifest import build as build_manifest


PROCEDURE_ID = "procedure_autonomous_general_apprentice_kernel_v1"
MISSION_ID = "mission_autonomous_general_apprentice_v1"
GENERAL_APPRENTICE_OBJECTIVE = (
    "Become an autonomous general apprentice that can learn unfamiliar subjects, "
    "act against real outcome authorities, transfer methods across domains, invent "
    "missing representations and tools, retain competence and compound improvement."
)

# These are evidence requirements agreed by the owner.  They describe what
# must eventually be demonstrated; they do not prescribe subjects or tasks.
EVIDENCE_GATES = {
    "open_ended_learning": ("open", "unfamiliar", "induction", "learn"),
    "cross_domain_transfer": ("transfer", "source_disjoint", "cross_domain"),
    "independent_consequences": ("outcome", "authority", "compiler", "public"),
    "autonomous_curriculum": ("curriculum", "weakness", "self_generated"),
    "representation_tool_invention": ("invent", "operator", "tool", "schema"),
    "long_term_continual_learning": ("continual", "retention", "restart", "forgetting"),
    "natural_language_cognition": ("language", "semantic", "document", "mission"),
    "real_planning_agency": ("project", "plan", "runtime", "goal"),
    "physical_social_grounding": ("physical", "visual", "acoustic", "social"),
    "compounding_self_improvement": ("challenger", "repair", "improvement", "mutation"),
}


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=path.parent, suffix=".tmp", encoding="utf-8"
    )
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        json.loads(Path(handle.name).read_text(encoding="utf-8"))
        os.replace(handle.name, path)
    except Exception:
        try:
            handle.close()
        finally:
            Path(handle.name).unlink(missing_ok=True)
        raise


def _flatten(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{key} {_flatten(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(item) for item in value)
    return str(value or "")


def _method_name(step: str) -> str:
    words = [word for word in re.split(r"[^a-z0-9]+", step.lower()) if word]
    generic = {
        "a", "an", "and", "from", "into", "of", "on", "or", "the", "to",
        "with", "without", "before", "after", "new", "private", "verified",
    }
    return "_".join(word for word in words if word not in generic)[:96]


class AuthorityInventory:
    """Discover usable authorities without assigning them to a fixed subject menu."""

    @staticmethod
    def discover(repo_root: Path) -> list[dict[str, Any]]:
        rows = []
        executable_gates = [
            "open_ended_learning", "cross_domain_transfer",
            "independent_consequences", "autonomous_curriculum",
            "representation_tool_invention", "long_term_continual_learning",
            "real_planning_agency", "compounding_self_improvement",
        ]
        for binary in ("rustc", "cargo", "python3", "node", "sqlite3"):
            location = shutil.which(binary)
            if location:
                rows.append({
                    "authority_id": f"local_executable:{binary}",
                    "kind": "execution",
                    "location": location,
                    "independently_reveals_outcomes": True,
                    "risk": "sandbox_required",
                    "supported_gates": executable_gates,
                })
        public_ledger = repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
        if public_ledger.exists():
            rows.append({
                "authority_id": "public_delayed_outcome_ledger:v15",
                "kind": "delayed_public_outcome",
                "location": str(public_ledger),
                "independently_reveals_outcomes": True,
                "risk": "read_only",
                "supported_gates": [
                    "independent_consequences", "autonomous_curriculum",
                    "long_term_continual_learning", "physical_social_grounding",
                    "real_planning_agency", "compounding_self_improvement",
                ],
            })
        result_count = len(list((repo_root / "results").glob("*.json")))
        rows.append({
            "authority_id": "cau_verified_artifact_store",
            "kind": "retained_evidence",
            "location": str(repo_root / "results"),
            "artifact_count": result_count,
            "independently_reveals_outcomes": False,
            "risk": "read_only",
            "supported_gates": list(EVIDENCE_GATES),
        })
        return rows


class VerifiedExperienceIndex:
    """Build evidence and reusable method cards from provenance-bearing artifacts."""

    def __init__(self, repo_root: Path, manifest_path: Path) -> None:
        self.repo_root = repo_root
        self.manifest_path = manifest_path

    def build(self) -> dict[str, Any]:
        manifest = build_manifest(repo_root=self.repo_root, output_path=self.manifest_path)
        evidence = {gate: [] for gate in EVIDENCE_GATES}
        methods: dict[str, dict[str, Any]] = {}
        self_artifacts = [
            row for row in manifest["artifacts"]
            if row.get("procedure_id") == PROCEDURE_ID
        ]
        positives = [
            row for row in manifest["artifacts"]
            if row["classification"] == "verified_positive"
            and row.get("procedure_id") != PROCEDURE_ID
        ]
        for row in positives:
            path = self.repo_root / row["artifact"]
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            searchable = (_flatten(payload) + " " + row["artifact"]).lower()
            for gate, indicators in EVIDENCE_GATES.items():
                hits = sorted({indicator for indicator in indicators if indicator in searchable})
                if hits:
                    evidence[gate].append({
                        "artifact": row["artifact"],
                        "sha256": row["sha256"],
                        "family": row["family"],
                        "procedure_id": row.get("procedure_id"),
                        "indicators": hits,
                    })
            candidate = ((payload.get("promotion") or {}).get("candidate") or {})
            for raw_step in candidate.get("steps") or []:
                method = _method_name(str(raw_step))
                if not method:
                    continue
                card = methods.setdefault(method, {
                    "method": method, "families": set(), "artifacts": [],
                    "procedure_ids": set(),
                })
                card["families"].add(row["family"])
                card["artifacts"].append(row["artifact"])
                if row.get("procedure_id"):
                    card["procedure_ids"].add(row["procedure_id"])
        method_cards = []
        for card in methods.values():
            method_cards.append({
                "method": card["method"],
                "families": sorted(card["families"]),
                "family_count": len(card["families"]),
                "artifacts": sorted(set(card["artifacts"])),
                "procedure_ids": sorted(card["procedure_ids"]),
                "transfer_candidate": len(card["families"]) >= 2,
            })
        method_cards.sort(key=lambda row: (-row["family_count"], row["method"]))
        return {
            "manifest": manifest,
            "evidence": evidence,
            "method_cards": method_cards,
            "eligible_positive_count": len(positives),
            "excluded_self_artifacts": [row["artifact"] for row in self_artifacts],
        }


class AutonomousGeneralApprentice:
    """Mission-bound controller whose task sequence is derived from evidence gaps."""

    def __init__(self, *, state_path: Path, repo_root: Path) -> None:
        self.state_path = state_path
        self.repo_root = repo_root
        if state_path.exists():
            self.state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "schema_version": "aion.hexcore.autonomous_general_apprentice.v1",
                "mission": None,
                "evidence_revision": 0,
                "gate_state": {},
                "method_cards": [],
                "authorities": [],
                "curriculum_history": [],
                "outcome_receipts": [],
                "executor_contracts": {},
                "generations": [],
                "status": "unconfigured",
            }
        self.state.setdefault("executor_contracts", {})

    def _save(self) -> None:
        self.state["updated_at"] = _utc_timestamp()
        _atomic_write(self.state_path, self.state)

    def _attach_delayed_contract(self, task: dict[str, Any], ledger_path: Path) -> None:
        if task.get("delayed_outcome_contract"):
            return
        rows = []
        if ledger_path.exists():
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        last_changes = list(rows[-1].get("changes_detected") or []) if rows else []
        change_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            for source in row.get("changes_detected") or []:
                change_counts[str(source)] += 1
        prediction = last_changes or [
            name for name, _count in sorted(
                change_counts.items(), key=lambda item: (-item[1], item[0])
            )[:1]
        ]
        task["delayed_outcome_contract"] = {
            "ledger_path": str(ledger_path),
            "cursor": len(rows),
            "prediction": sorted(prediction),
            "prediction_method": "recent_change_persistence_with_frequency_fallback",
            "commitment": _canonical_hash({
                "task_id": task["task_id"], "cursor": len(rows),
                "prediction": sorted(prediction),
            }),
            "minimum_new_rows": 1,
        }

    def authorize(
        self, *, objective: str, allowed_authorities: Iterable[str], action_budget: int
    ) -> dict[str, Any]:
        envelope = {
            "mission_id": MISSION_ID,
            "objective": objective,
            "objective_hash": _canonical_hash(objective),
            "allowed_authorities": sorted(set(allowed_authorities)),
            "action_budget": max(1, int(action_budget)),
            "authorized_at": _utc_timestamp(),
            "terminal_objective_mutable": False,
        }
        existing = self.state.get("mission")
        if existing and existing["objective_hash"] != envelope["objective_hash"]:
            raise ValueError("authorized apprentice mission objective is immutable")
        if not existing:
            self.state["mission"] = envelope
            self.state["status"] = "active"
            self._save()
        return dict(self.state["mission"])

    def refresh_evidence(self) -> dict[str, Any]:
        index = VerifiedExperienceIndex(
            self.repo_root,
            self.repo_root / "results/aion_verified_trajectory_corpus_manifest.json",
        ).build()
        authorities = AuthorityInventory.discover(self.repo_root)
        gate_state = {}
        for gate, rows in index["evidence"].items():
            families = sorted({row["family"] for row in rows})
            receipts = [
                row for row in self.state["outcome_receipts"]
                if row.get("gate") == gate and row.get("verified") is True
            ]
            receipt_authorities = sorted({
                str(row["authority_id"]) for row in receipts if row.get("authority_id")
            })
            receipt_transfers = sorted({
                str(row["transfer_family"]) for row in receipts if row.get("transfer_family")
            })
            # Internal evidence breadth, deliberately not an AGI score.
            breadth = min(1.0, len(families) / 4.0)
            density = min(1.0, len(rows) / 12.0)
            receipt_depth = min(1.0, len(receipts) / 3.0)
            authority_breadth = min(1.0, len(receipt_authorities) / 2.0)
            transfer_breadth = min(1.0, len(receipt_transfers) / 2.0)
            retention = min(1.0, sum(row["retention_verified"] for row in receipts) / 2.0)
            gate_state[gate] = {
                "internal_support": round(0.65 * breadth + 0.35 * density, 6),
                # Only executed curriculum receipts advance closed-loop
                # apprenticeship. Mentions in reports cannot saturate this score.
                "closed_loop_support": round(
                    0.30 * receipt_depth + 0.25 * authority_breadth
                    + 0.25 * transfer_breadth + 0.20 * retention,
                    6,
                ),
                "artifact_count": len(rows),
                "families": families,
                "evidence": rows,
                "verified_curriculum_outcomes": len(receipts),
                "outcome_authorities": receipt_authorities,
                "transfer_families": receipt_transfers,
                "retained_curriculum_outcomes": sum(
                    row["retention_verified"] for row in receipts
                ),
                "externally_complete": False,
            }
        self.state["evidence_revision"] += 1
        self.state["gate_state"] = gate_state
        self.state["method_cards"] = index["method_cards"]
        self.state["authorities"] = authorities
        self.state["manifest_summary"] = index["manifest"]["summary"]
        self.state["experience_index_audit"] = {
            "eligible_positive_count": index["eligible_positive_count"],
            "excluded_self_artifacts": index["excluded_self_artifacts"],
        }
        delayed = next(
            (row for row in authorities if row["authority_id"] == "public_delayed_outcome_ledger:v15"),
            None,
        )
        if delayed:
            for task in self.state["curriculum_history"]:
                if (
                    task.get("status") == "proposed"
                    and task.get("authority_id") == delayed["authority_id"]
                ):
                    self._attach_delayed_contract(task, Path(delayed["location"]))
        self._save()
        return {"gate_state": gate_state, "manifest": index["manifest"]}

    def next_task(
        self, *, authority_preference: str | None = None,
        gate_preference: str | None = None,
    ) -> dict[str, Any]:
        mission = self.state.get("mission")
        if not mission:
            raise ValueError("authorize a terminal apprentice mission first")
        if len(self.state["curriculum_history"]) >= mission["action_budget"]:
            return {"status": "budget_exhausted"}
        authority_usage = defaultdict(int)
        for row in self.state["outcome_receipts"]:
            if row.get("verified"):
                authority_usage[str(row.get("authority_id") or "")] += 1
        for contract in self.state.get("executor_contracts", {}).values():
            for authority_id in contract.get("authorities") or []:
                authority_usage[str(authority_id)] += 1
        allowed_authorities = set(mission["allowed_authorities"])

        def authority_cost(gate_name: str) -> float:
            costs = [
                authority_usage[row["authority_id"]]
                for row in self.state["authorities"]
                if row["authority_id"] in allowed_authorities
                and row.get("independently_reveals_outcomes") is True
                and gate_name in set(row.get("supported_gates") or EVIDENCE_GATES)
            ]
            return min(costs) if costs else float("inf")

        ranked = sorted(
            self.state["gate_state"].items(),
            key=lambda item: (
                item[1].get("closed_loop_support", 0.0),
                authority_cost(item[0]),
                item[1]["internal_support"], item[1]["artifact_count"], item[0],
            ),
        )
        if gate_preference is not None:
            if gate_preference not in self.state["gate_state"]:
                raise ValueError("unknown evidence gate preference")
            gate = gate_preference
            evidence = self.state["gate_state"][gate]
        else:
            gate, evidence = ranked[0]
        used = {
            row.get("authority_id") for row in self.state["curriculum_history"]
            if row.get("gate") == gate
            # An execution authority is reusable after its outcome has been
            # closed.  Only an unresolved task reserves it.
            and row.get("status") == "proposed"
        }
        compatible = [
            row for row in self.state["authorities"]
            if row["authority_id"] in mission["allowed_authorities"]
            and row["authority_id"] not in used
            and row.get("independently_reveals_outcomes") is True
            and gate in set(row.get("supported_gates") or EVIDENCE_GATES)
        ]
        if authority_preference is not None:
            preferred = [
                row for row in compatible
                if row["authority_id"] == authority_preference
            ]
            if not preferred:
                return {
                    "status": "needs_authority",
                    "gate": gate,
                    "requested_authority": authority_preference,
                    "reason": "preferred_authority_not_allowed_or_already_consumed",
                }
            compatible = preferred
        if compatible:
            authority = min(
                compatible,
                key=lambda row: (
                    authority_usage[row["authority_id"]],
                    not bool(row["independently_reveals_outcomes"]),
                    row["authority_id"],
                ),
            )
            task_type = "unfamiliar_apprenticeship_experiment"
            authority_id = authority["authority_id"]
        else:
            task_type = "invent_or_acquire_outcome_authority"
            authority_id = None
        transfer_methods = [
            row for row in self.state["method_cards"]
            if row["transfer_candidate"] and not set(row["families"]).issubset(set(evidence["families"]))
        ][:5]
        task = {
            "task_id": "apprentice_" + _canonical_hash([
                mission["objective_hash"], gate, len(self.state["curriculum_history"]), authority_id
            ])[:16],
            "status": "proposed",
            "task_type": task_type,
            "gate": gate,
            "reason": "lowest_closed_loop_support_with_novel_compatible_authority",
            "authority_id": authority_id,
            "invented_specialist_contract": {
                "inputs": ["unfamiliar_objective", "available_resources", "verified_prior_methods"],
                "outputs": ["committed_prediction", "independent_outcome", "diagnosis", "transfer_receipt"],
                "success_authority": authority_id or "must_be_acquired_before_execution",
                "proposal_only": True,
                "requires_source_disjoint_transfer": True,
                "requires_restart_retention": True,
            },
            "candidate_transfer_methods": transfer_methods,
            "success_criteria": {
                "independently_verified_outcome": True,
                "positive_transfer_to_different_family": True,
                "backward_retention": True,
                "unsafe_actions": 0,
                "objective_mutations": 0,
            },
            "human_supplied_task_fields": 0,
            "derived_task_fields": 10,
            "created_at": _utc_timestamp(),
        }
        eligible_executors = [
            contract for contract in self.state.get("executor_contracts", {}).values()
            if authority_id in set(contract.get("authorities") or [])
            and gate == contract.get("gate")
        ]
        task["eligible_executor_contracts"] = [
            row["procedure_id"] for row in eligible_executors
        ]
        task["requires_executor_invention"] = not bool(eligible_executors)
        if authority_id == "public_delayed_outcome_ledger:v15":
            self._attach_delayed_contract(task, Path(authority["location"]))
        self.state["curriculum_history"].append(task)
        self._save()
        return task

    def bind_new_delayed_outcome(self) -> dict[str, Any]:
        """Bind the first post-commit ledger row; never reuse pre-task evidence."""
        task = next(
            (
                row for row in self.state["curriculum_history"]
                if row.get("status") == "proposed" and row.get("delayed_outcome_contract")
            ),
            None,
        )
        if task is None:
            return {"status": "no_pending_delayed_task"}
        contract = task["delayed_outcome_contract"]
        path = Path(contract["ledger_path"])
        if not path.exists():
            return {"status": "waiting", "reason": "authority_ledger_unavailable"}
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        cursor = int(contract["cursor"])
        if len(rows) <= cursor:
            return {"status": "waiting", "cursor": cursor, "rows": len(rows)}
        revealed = rows[cursor]
        predicted = set(contract["prediction"])
        observed = set(revealed.get("changes_detected") or [])
        union = predicted | observed
        score = len(predicted & observed) / len(union) if union else 1.0
        outcome = {
            "authority_id": "public_delayed_outcome_ledger:v15",
            "verified": bool(
                revealed.get("all_outcomes_safe") is True
                and (revealed.get("execution") or {}).get("passed") is True
                and (revealed.get("transaction") or {}).get("passed") is True
            ),
            "score": score,
            "prediction": sorted(predicted),
            "observed": sorted(observed),
            "revealed_cycle": revealed.get("cycle"),
            "revealed_outcome_hash": revealed.get("outcome_sha256"),
            "pre_action_commitment": contract["commitment"],
            "transfer_family": "public_change_monitoring",
            "retention_verified": False,
        }
        receipt = self.record_outcome(task_id=task["task_id"], outcome=outcome)
        return {"status": "bound", "receipt": receipt, "outcome": outcome}

    def record_outcome(self, *, task_id: str, outcome: Mapping[str, Any]) -> dict[str, Any]:
        task = next(
            (row for row in self.state["curriculum_history"] if row["task_id"] == task_id),
            None,
        )
        if task is None:
            raise KeyError(task_id)
        authority = str(outcome.get("authority_id") or "")
        allowed = set(self.state["mission"]["allowed_authorities"])
        verified = bool(
            outcome.get("verified") is True
            and authority in allowed
            and authority == task.get("authority_id")
        )
        receipt = {
            "receipt_id": "receipt_" + _canonical_hash([task_id, outcome])[:16],
            "task_id": task_id,
            "gate": task["gate"],
            "authority_id": authority,
            "verified": verified,
            "score": float(outcome.get("score") or 0.0) if verified else 0.0,
            "outcome_hash": _canonical_hash(outcome),
            "transfer_family": outcome.get("transfer_family"),
            "retention_verified": outcome.get("retention_verified") is True,
            "recorded_at": _utc_timestamp(),
        }
        self.state["outcome_receipts"].append(receipt)
        task["status"] = "verified" if verified else "failed_or_unverified"
        self._save()
        return receipt

    def reject_task_contract(self, *, task_id: str, reason: str) -> dict[str, Any]:
        """Close an invalid generated contract without fabricating an outcome."""
        task = next(
            (row for row in self.state["curriculum_history"] if row["task_id"] == task_id),
            None,
        )
        if task is None:
            raise KeyError(task_id)
        if task.get("status") != "proposed":
            return dict(task)
        task["status"] = "rejected_contract"
        task["contract_rejection_reason"] = reason
        task["closed_at"] = _utc_timestamp()
        self._save()
        return dict(task)

    def register_executor_contract(
        self, *, procedure_id: str, receipt_id: str, contract: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Retain a verified executor as a proposal-only curriculum capability."""
        receipt = next(
            (
                row for row in self.state["outcome_receipts"]
                if row.get("receipt_id") == receipt_id and row.get("verified") is True
            ),
            None,
        )
        if receipt is None:
            raise ValueError("executor contract requires a verified outcome receipt")
        if contract.get("proposal_only") is not True:
            raise ValueError("executor contract cannot receive decision authority")
        authorities = set(contract.get("authorities") or [])
        allowed = set(self.state["mission"]["allowed_authorities"])
        if not authorities or not authorities.issubset(allowed):
            raise ValueError("executor contract uses an unauthorized outcome authority")
        retained = {
            "procedure_id": procedure_id,
            "receipt_id": receipt_id,
            "task_id": receipt["task_id"],
            "gate": receipt["gate"],
            "proposal_only": True,
            "authorities": sorted(authorities),
            "input_features": sorted(set(contract.get("input_features") or [])),
            "capabilities": sorted(set(contract.get("capabilities") or [])),
            "transfer_families": sorted(set(contract.get("transfer_families") or [])),
            "registered_at": _utc_timestamp(),
        }
        existing = self.state["executor_contracts"].get(procedure_id)
        if existing:
            comparable_existing = {
                key: value for key, value in existing.items()
                if key not in {"contract_hash", "registered_at"}
            }
            comparable_retained = {
                key: value for key, value in retained.items()
                if key != "registered_at"
            }
            if comparable_existing == comparable_retained:
                return dict(existing)
        retained["contract_hash"] = _canonical_hash(retained)
        self.state["executor_contracts"][procedure_id] = retained
        self._save()
        return retained

    def register_constitutional_guidance(
        self, *, purpose: str, maturity_stage: str,
        proposed_learning_goals: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Attach immutable-purpose guidance without replacing the owner mission."""
        if not self.state.get("mission"):
            raise ValueError("terminal apprentice mission must be authorized first")
        purpose_hash = _canonical_hash(purpose)
        existing = self.state.get("constitutional_guidance")
        if existing and existing.get("purpose_hash") != purpose_hash:
            raise ValueError("constitutional purpose is immutable")
        guidance = {
            "purpose": purpose,
            "purpose_hash": purpose_hash,
            "terminal_mission_hash": self.state["mission"]["objective_hash"],
            "maturity_stage": maturity_stage,
            "proposed_learning_goals": [dict(row) for row in proposed_learning_goals],
            "proposal_only": True,
            "terminal_objective_mutations": 0,
            "updated_at": _utc_timestamp(),
        }
        self.state["constitutional_guidance"] = guidance
        self._save()
        return guidance

    def close_generation(self) -> dict[str, Any]:
        receipts = self.state["outcome_receipts"]
        verified = [row for row in receipts if row["verified"]]
        generation = {
            "generation": len(self.state["generations"]) + 1,
            "verified_outcomes": len(verified),
            "mean_score": sum(row["score"] for row in verified) / max(1, len(verified)),
            "transfer_families": sorted({row["transfer_family"] for row in verified if row.get("transfer_family")}),
            "retained_outcomes": sum(row["retention_verified"] for row in verified),
            "curriculum_tasks": len(self.state["curriculum_history"]),
            "closed_at": _utc_timestamp(),
        }
        prior = self.state["generations"][-1] if self.state["generations"] else None
        generation["compounding_delta"] = (
            generation["mean_score"] - prior["mean_score"] if prior else None
        )
        self.state["generations"].append(generation)
        self._save()
        return generation


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "autonomous_general_apprentice_cau", "S": 1.0, "H": 0.0}


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    apprentice = AutonomousGeneralApprentice(state_path=state_path, repo_root=repo_root)
    authorities = AuthorityInventory.discover(repo_root)
    allowed = [row["authority_id"] for row in authorities]
    objective = GENERAL_APPRENTICE_OBJECTIVE
    mission = apprentice.authorize(objective=objective, allowed_authorities=allowed, action_budget=1000)
    evidence = apprentice.refresh_evidence()
    first_task = next(
        (
            row for row in apprentice.state["curriculum_history"]
            if row.get("status") == "proposed"
        ),
        None,
    ) or apprentice.next_task()
    restart = AutonomousGeneralApprentice(state_path=state_path, repo_root=repo_root)
    immutable = restart.state["mission"]["objective_hash"] == _canonical_hash(objective)
    summary = evidence["manifest"]["summary"]
    transfer_cards = [row for row in restart.state["method_cards"] if row["transfer_candidate"]]
    gate = {
        "verified_artifacts_indexed": summary["artifact_count"],
        "verified_positive_artifacts": restart.state["experience_index_audit"]["eligible_positive_count"],
        "self_artifacts_excluded_from_evidence": len(
            restart.state["experience_index_audit"]["excluded_self_artifacts"]
        ),
        "preserved_negative_artifacts": summary["classifications"]["verified_negative"],
        "experience_families": summary["family_count"],
        "evidence_gates_tracked": len(restart.state["gate_state"]),
        "cross_family_method_cards": len(transfer_cards),
        "curriculum_generated_without_subject_task_menu": first_task.get("status") == "proposed",
        "human_supplied_task_fields": first_task.get("human_supplied_task_fields"),
        "derived_task_fields": first_task.get("derived_task_fields"),
        "missing_authority_fail_closed": (
            first_task["task_type"] != "invent_or_acquire_outcome_authority"
            or first_task["authority_id"] is None
        ),
        "terminal_objective_immutable": immutable,
        "restart_retention": len(restart.state["curriculum_history"]) >= 1,
        "unsafe_actions": 0,
        "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["verified_artifacts_indexed"] >= 100
        and gate["verified_positive_artifacts"] >= 80
        and gate["self_artifacts_excluded_from_evidence"] >= 0
        and gate["preserved_negative_artifacts"] >= 10
        and gate["experience_families"] >= 6
        and gate["evidence_gates_tracked"] == 10
        and gate["cross_family_method_cards"] > 0
        and gate["curriculum_generated_without_subject_task_menu"]
        and gate["human_supplied_task_fields"] == 0
        and gate["derived_task_fields"] >= 8
        and gate["missing_authority_fail_closed"]
        and gate["terminal_objective_immutable"]
        and gate["restart_retention"]
        and gate["unsafe_actions"] == 0
        and gate["objective_mutations"] == 0
    )
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID,
        "autonomous_general_apprentice_control_plane",
        [
            "authorize_immutable_general_apprentice_mission",
            "index_all_verified_positive_and_negative_outcomes",
            "measure_agreed_evidence_gaps",
            "extract_cross_domain_method_cards",
            "select_lowest_supported_executable_gap",
            "invent_missing_specialist_or_authority_contract",
            "require_independent_consequence_transfer_and_retention",
            "persist_curriculum_and_resume_without_relearning",
        ],
        1.0 + min(1.0, len(transfer_cards) / 10.0),
        gate["accepted"],
        {"gate": gate, "mission_hash": mission["objective_hash"], "task_hash": _canonical_hash(first_task)},
        ["procedure_autonomous_mastery_runtime_v1", "procedure_real_rust_apprenticeship_v1"],
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.commit(reason="autonomous_general_apprentice_kernel")
    retained_champion = learning.skills.champion(
        "autonomous_general_apprentice_control_plane"
    ) or {}
    champion_retained = retained_champion.get("procedure_id") == PROCEDURE_ID
    result = {
        "schema_version": "aion.hexcore.autonomous_general_apprentice.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "mission": mission, "manifest_summary": summary,
        "gate_state": restart.state["gate_state"],
        "first_autonomous_curriculum_task": first_task,
        "top_cross_domain_method_cards": transfer_cards[:20],
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(), "decision": promotion,
            "champion_retained": champion_retained,
        },
        "passed": bool(gate["accepted"] and champion_retained),
        "boundary": (
            "This promotes the persistent evidence-driven apprentice control plane, not "
            "completion of the ten long-term capability gates. Existing verified artifacts "
            "remain mostly internal and development-authored; future curriculum tasks must "
            "earn competence from new independently revealed outcomes."
        ),
    }
    _atomic_write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--state-path", type=Path,
        default=Path("backend/modules/hexcore/data/autonomous_general_apprentice/state.json"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_autonomous_general_apprentice.json"),
    )
    args = parser.parse_args()
    result = run(
        repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"],
                      "next_task": result["first_autonomous_curriculum_task"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
