"""Progressive, evidence-backed competency and curriculum control plane.

Unlike the earlier binary Academy receipts, this ledger distinguishes an
assessment pass from subject competence.  A subject advances only through
repeated subskill evidence, unfamiliar projects, failure recovery, transfer,
elapsed retention, declining scaffolding and independently owned outcomes.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from functools import wraps
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.constitutional_north_star_mastery_registry import SUBJECTS
from backend.modules.hexcore.guided_foundation_academy import MODULES
from backend.modules.hexcore.file_locking import exclusive_file_lock


SCHEMA = "aion.hexcore.progressive_competency_system.v1"
LEVELS = ("unassessed", "beginner", "intermediate", "advanced", "expert")
LEVEL_INDEX = {level: index for index, level in enumerate(LEVELS)}
DEFAULT_TARGET = "advanced"
CURRICULUM_POLICY_VERSION = "cross_domain_depth_acceleration_v4"
EXPERT_RETENTION_MILESTONES_DAYS = (1, 7, 30, 90)

# Breadth is still dynamic, but the foundational computing sequence is
# intentional.  Dictionary ordering must never decide what AION learns next.
FOUNDATION_ORDER = (
    "python_core", "advanced_python", "testing_debugging",
    "algorithms_data_structures", "software_engineering", "database_engineering",
    "operating_systems", "networking", "distributed_systems", "secure_engineering",
    "architecture_operations", "rust_systems", "integrated_engineering_capstone",
    "english", "mathematics", "scientific_method", "product_project_management",
    "business_management", "finance_accounting", "research_communication",
)
FOUNDATION_PRIORITY = {subject_id: len(FOUNDATION_ORDER) - index
                       for index, subject_id in enumerate(FOUNDATION_ORDER)}

# Top-level apprenticeship missions. Each mission expands into assessed leaf
# subjects, and each leaf subject expands into its complete declared subskill
# set. Overlap is deliberate: transfer across missions is part of competence.
APPRENTICESHIP_DOMAINS: tuple[dict[str, Any], ...] = (
    {"domain_id": "systems_software", "name": "Systems and software engineering", "tier": 1,
     "subjects": ("python_core", "advanced_python", "algorithms_data_structures", "testing_debugging",
                  "software_engineering", "operating_systems", "networking", "distributed_systems",
                  "rust_systems", "architecture_operations", "cloud_devops_sre", "compilers_languages",
                  "integrated_engineering_capstone")},
    {"domain_id": "data_transactional", "name": "Data and transactional integrity", "tier": 1,
     "subjects": ("database_engineering", "sql_databases", "data_statistics", "finance_accounting")},
    {"domain_id": "empirical_science", "name": "Empirical and scientific modelling", "tier": 1,
     "subjects": ("scientific_method", "data_statistics", "physics", "chemistry", "biology_medicine")},
    {"domain_id": "document_evidence", "name": "Document and evidence work", "tier": 1,
     "subjects": ("english", "research_communication", "law_policy_ethics")},
    {"domain_id": "tool_environment", "name": "Tool and environment acquisition", "tier": 1,
     "subjects": ("software_engineering", "cloud_devops_sre", "compilers_languages", "security_engineering")},
    {"domain_id": "mathematics_formal", "name": "Mathematics and formal reasoning", "tier": 2,
     "subjects": ("mathematics", "algorithms_data_structures", "compilers_languages")},
    {"domain_id": "planning_projects", "name": "Planning and long-horizon projects", "tier": 2,
     "subjects": ("product_project_management", "business_management", "economics_entrepreneurship",
                  "research_communication")},
    {"domain_id": "physical_grounding", "name": "Physical and sensor-actuator grounding", "tier": 2,
     "subjects": ("embedded_robotics", "physics", "computer_graphics")},
    {"domain_id": "causal_investigation", "name": "Causal investigation", "tier": 2,
     "subjects": ("scientific_method", "data_statistics", "machine_learning_ai")},
    {"domain_id": "security_robustness", "name": "Security and adversarial robustness", "tier": 2,
     "subjects": ("security_engineering", "secure_engineering", "networking", "law_policy_ethics")},
    {"domain_id": "natural_language", "name": "Natural-language instruction and dialogue", "tier": 3,
     "subjects": ("english", "spanish", "research_communication")},
    {"domain_id": "social_commonsense", "name": "Commonsense and social judgment", "tier": 3,
     "subjects": ("social_commonsense", "law_policy_ethics", "business_management")},
    {"domain_id": "creative_synthesis", "name": "Creative synthesis under constraints", "tier": 3,
     "subjects": ("creative_invention", "ui_product_design", "computer_graphics")},
    {"domain_id": "multiagent_institutions", "name": "Multi-agent and institutional reasoning", "tier": 3,
     "subjects": ("social_commonsense", "business_management", "economics_entrepreneurship",
                  "law_policy_ethics", "distributed_systems")},
    {"domain_id": "research_metalearning", "name": "Research and meta-learning", "tier": 3,
     "subjects": ("scientific_method", "research_communication", "machine_learning_ai",
                  "product_project_management")},
)

KNOWLEDGE_KINDS = {"lesson", "knowledge_test", "assessment", "exercise", "project", "retention"}
PRACTICAL_KINDS = {"exercise", "project", "debugging", "transfer", "retention"}

# Coverage added beyond the older registry.  These are curriculum headings,
# not claims that AION already knows them.
EXTENDED_SUBJECTS: tuple[dict[str, Any], ...] = (
    {"subject_id": "cloud_devops_sre", "name": "Cloud, DevOps and Site Reliability", "group": "computing",
     "subskills": ("linux_operations", "containers", "ci_cd", "cloud_architecture", "infrastructure_as_code", "observability", "capacity", "reliability", "incident_response", "cost")},
    {"subject_id": "machine_learning_ai", "name": "Machine Learning and AI Engineering", "group": "computing",
     "subskills": ("linear_algebra", "optimisation", "supervised_learning", "unsupervised_learning", "deep_learning", "evaluation", "data_governance", "deployment", "monitoring", "safety")},
    {"subject_id": "compilers_languages", "name": "Compilers and Programming Languages", "group": "computing",
     "subskills": ("lexing", "parsing", "type_systems", "intermediate_representations", "optimisation", "code_generation", "interpreters", "runtime_systems", "language_design")},
    {"subject_id": "embedded_robotics", "name": "Embedded Systems and Robotics", "group": "computing_physical",
     "subskills": ("electronics", "microcontrollers", "realtime_systems", "sensors", "actuators", "control", "communications", "power", "safety", "hardware_debugging"),
     "practical_blocker_template": "Physical prototype, instrumentation and independent hardware outcome required."},
    {"subject_id": "computer_graphics", "name": "Computer Graphics and Visual Computing", "group": "computing",
     "subskills": ("geometry", "linear_algebra", "rendering", "shaders", "images", "animation", "visualisation", "performance", "accessibility")},
    {"subject_id": "economics_entrepreneurship", "name": "Economics and Entrepreneurship", "group": "business",
     "subskills": ("microeconomics", "macroeconomics", "market_research", "business_models", "unit_economics", "fundraising", "competition", "regulation", "experimentation")},
    {"subject_id": "product_project_management", "name": "Product, Project and Scrum Management", "group": "business",
     "subskills": ("goal_definition", "discovery", "prioritisation", "dependencies", "scrum", "risk", "stakeholders", "delivery", "metrics", "retrospectives")},
    {"subject_id": "research_communication", "name": "Research, Writing and Professional Communication", "group": "human_language",
     "subskills": ("source_evaluation", "synthesis", "argument", "technical_writing", "persuasion", "audience_adaptation", "presentation", "negotiation", "citation")},
    {"subject_id": "law_policy_ethics", "name": "Law, Policy and Applied Ethics", "group": "social",
     "subskills": ("legal_research", "contracts", "privacy", "intellectual_property", "employment", "regulation", "ethics", "jurisdiction", "uncertainty", "escalation")},
)


ACADEMY_TO_GROUP = {
    "python_core": "computing", "advanced_python": "computing",
    "algorithms_data_structures": "computing", "testing_debugging": "computing",
    "software_engineering": "computing", "database_engineering": "computing",
    "operating_systems": "computing", "networking": "computing",
    "distributed_systems": "computing", "rust_systems": "computing",
    "secure_engineering": "computing", "architecture_operations": "computing",
    "integrated_engineering_capstone": "computing",
}


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.{os.getpid()}.", suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _state_transaction(method):
    """Reload and mutate the competency ledger under its single-writer lock."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with exclusive_file_lock(self.lock_path):
            self._lock_depth += 1
            try:
                current_digest = _state_digest(self.state_path)
                if current_digest is not None and current_digest != self._loaded_digest:
                    self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
                    self._loaded_digest = current_digest
                return method(self, *args, **kwargs)
            finally:
                self._lock_depth -= 1
    return wrapped


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


class ProgressiveCompetencySystem:
    def __init__(self, *, repo_root: Path, state_path: Path) -> None:
        self.repo_root = repo_root
        self.state_path = state_path
        self.lock_path = state_path.with_suffix(state_path.suffix + ".lock")
        self._lock_depth = 0
        self._loaded_digest: str | None = None
        with exclusive_file_lock(self.lock_path):
            self._lock_depth += 1
            try:
                if state_path.exists():
                    self.state = json.loads(state_path.read_text(encoding="utf-8"))
                    self._loaded_digest = _state_digest(state_path)
                else:
                    self.state = {
                        "schema_version": SCHEMA, "subjects": {}, "evidence": [], "contracts": [],
                        "blockers": [], "mission_gaps": [], "active_subject_id": None,
                        "target_level_default": DEFAULT_TARGET, "curriculum_cycles": [],
                        "programme_stage": "foundation_to_advanced",
                        "lane_scheduler": {"breadth_contracts": 0, "depth_contracts": 0,
                                           "expert_unlocks": []},
                        "owner_lesson_steps": 0, "unsafe_actions": 0,
                    }
                    self._seed_catalogue()
                    self._import_existing_evidence()
                    self.state["active_subject_id"] = "python_core"
                    self._save()
                if self.state.get("schema_version") != SCHEMA:
                    raise ValueError("unsupported progressive competency state")
                self._migrate()
            finally:
                self._lock_depth -= 1

    def _migrate(self) -> None:
        changed = False
        integrity_invalidated_subjects: set[str] = set()
        prior_policy = self.state.get("curriculum_policy_version")
        if prior_policy != CURRICULUM_POLICY_VERSION:
            # An earlier policy selected equal-priority subjects by lexical
            # order.  Supersede only untouched contracts created by that policy;
            # retained evidence and delayed tests remain immutable.
            if prior_policy != "parallel_retention_foundation_order_v2":
                for contract in self.state.get("contracts") or []:
                    if (contract.get("status") == "open"
                            and not (contract.get("requirement") or {}).get("not_before_epoch")
                            and not self.evidence_for(str(contract.get("subject_id")))):
                        contract["status"] = "superseded_curriculum_policy_upgrade"
                        contract["closed_at"] = _utc_timestamp()
            self.state["curriculum_policy_version"] = CURRICULUM_POLICY_VERSION
            if prior_policy != "parallel_retention_foundation_order_v2" and "python_core" in self.state.get("subjects", {}):
                self.state["active_subject_id"] = "python_core"
            changed = True
        if "programme_stage" not in self.state:
            self.state["programme_stage"] = "foundation_to_advanced"
            changed = True
        if "lane_scheduler" not in self.state:
            self.state["lane_scheduler"] = {
                "breadth_contracts": 0, "depth_contracts": 0, "expert_unlocks": []
            }
            changed = True
        domain_payload = {
            row["domain_id"]: {**row, "subjects": list(row["subjects"])}
            for row in APPRENTICESHIP_DOMAINS
        }
        if self.state.get("apprenticeship_domains") != domain_payload:
            self.state["apprenticeship_domains"] = domain_payload
            changed = True
        for row in self.state.get("evidence") or []:
            # Restart persistence is valuable but is not an elapsed closed-book
            # retention test. Older registries conflated the two.
            if row.get("imported") and row.get("retained"):
                row["restart_retained"] = True
                row["retained"] = False
                changed = True
            if row.get("imported") and "academy_committed_assessment" in (row.get("authority") or []):
                if row.get("kind") == "assessment":
                    row["kind"] = "exercise"
                    changed = True
            if not row.get("imported") and row.get("verified") is True and row.get("artifact"):
                artifact = self.repo_root / str(row["artifact"])
                if artifact.exists() and row.get("artifact_hash") != _sha256(artifact):
                    row["verified"] = False
                    row["invalidated_reason"] = "artifact_hash_changed_after_recording"
                    row["invalidated_at"] = _utc_timestamp()
                    integrity_invalidated_subjects.add(str(row.get("subject_id")))
                    changed = True
        for blocker in self.state.get("blockers") or []:
            if "executor" in str(blocker.get("reason", "")).lower() and blocker.get("blocker_type") != "executor_capability":
                blocker["blocker_type"] = "executor_capability"
                changed = True
            if "blocker_type" not in blocker:
                blocker["blocker_type"] = (
                    "executor_capability" if "executor" in (
                        str(blocker.get("required_authority", "")) + str(blocker.get("reason", ""))
                    ).lower()
                    else "external_practical"
                )
                changed = True
        for subject in self.state.get("subjects", {}).values():
            template = subject.get("practical_blocker_template")
            if template and not any(row.get("subject_id") == subject["subject_id"] and row.get("reason") == template
                                    for row in self.state.get("blockers") or []):
                body = {"subject_id": subject["subject_id"], "subskills": list(subject["subskills"]),
                        "reason": template, "required_authority": "authorized_human_or_robot_hardware_execution",
                        "blocker_type": "external_practical", "status": "open", "created_at": _utc_timestamp()}
                body["blocker_id"] = "competency_blocker_" + _canonical_hash(body)[:18]
                self.state["blockers"].append(body)
                changed = True
        if integrity_invalidated_subjects:
            for contract in self.state.get("contracts") or []:
                if contract.get("subject_id") in integrity_invalidated_subjects and contract.get("status") == "open":
                    contract["status"] = "superseded_after_integrity_audit"
                    contract["closed_at"] = _utc_timestamp()
                    changed = True
        if changed:
            self._save()

    def _seed_catalogue(self) -> None:
        for spec in SUBJECTS:
            self._add_subject(spec.subject_id, spec.name, spec.group, spec.subskills,
                              importance=float(spec.importance), source="north_star_registry")
        for row in EXTENDED_SUBJECTS:
            self._add_subject(str(row["subject_id"]), str(row["name"]), str(row["group"]),
                              row["subskills"], importance=0.75, source="extended_core_catalogue",
                              practical_blocker_template=row.get("practical_blocker_template"))
            if row.get("practical_blocker_template"):
                body = {
                    "subject_id": row["subject_id"], "subskills": list(row["subskills"]),
                    "reason": row["practical_blocker_template"],
                    "required_authority": "authorized_human_or_robot_hardware_execution",
                    "blocker_type": "external_practical",
                    "status": "open", "created_at": _utc_timestamp(),
                }
                body["blocker_id"] = "competency_blocker_" + _canonical_hash(body)[:18]
                self.state["blockers"].append(body)

        # These are permanent curriculum definitions, not learned claims, and
        # must exist even in a fresh workspace without an Academy state file.
        for module in MODULES:
            self._add_subject(
                module.module_id, module.name,
                ACADEMY_TO_GROUP.get(module.module_id, "computing"),
                module.competencies, importance=1.0,
                source="guided_foundation_academy_definition",
            )

        academy_path = self.repo_root / "backend/modules/hexcore/data/guided_foundation_academy/state.json"
        if academy_path.exists():
            academy = json.loads(academy_path.read_text(encoding="utf-8"))
            for module_id, module in (academy.get("modules") or {}).items():
                self._add_subject(
                    module_id, str(module.get("name") or module_id),
                    ACADEMY_TO_GROUP.get(module_id, "computing"),
                    module.get("competencies") or (), importance=1.0,
                    source="guided_foundation_academy",
                )

    def _add_subject(self, subject_id: str, name: str, group: str,
                     subskills: Iterable[str], *, importance: float, source: str,
                     practical_blocker_template: str | None = None) -> None:
        existing = self.state["subjects"].get(subject_id)
        if existing:
            existing["subskills"] = sorted(set(existing["subskills"]) | set(subskills))
            return
        self.state["subjects"][subject_id] = {
            "subject_id": subject_id, "name": name, "group": group,
            "importance": importance, "target_level": DEFAULT_TARGET,
            "subskills": sorted(set(str(item) for item in subskills)),
            "source": source, "status": "active", "created_at": _utc_timestamp(),
            "practical_blocker_template": practical_blocker_template,
        }

    def _import_existing_evidence(self) -> None:
        registry_path = self.repo_root / "results/hexcore_constitutional_north_star_mastery_registry.json"
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            for subject_id, subject in (registry.get("subjects") or {}).items():
                for row in subject.get("evidence") or []:
                    artifact = self.repo_root / str(row["artifact"])
                    if artifact.exists():
                        self._append_evidence({
                            "subject_id": subject_id, "kind": self._infer_kind(str(row["artifact"])),
                            "subskills": row.get("demonstrated_subskills") or [], "score": 1.0,
                            "verified": True, "source_disjoint": bool(row.get("transfer_verified")),
                            "retained": False, "restart_retained": bool(row.get("retention_verified")),
                            "independent_outcome": bool(row.get("authorities")), "unfamiliar": True,
                            "scaffolding": 0.65, "trials": 1, "artifact": str(row["artifact"]),
                            "artifact_hash": _sha256(artifact), "authority": row.get("authorities") or [],
                            "imported": True,
                        })

        academy_path = self.repo_root / "backend/modules/hexcore/data/guided_foundation_academy/state.json"
        if academy_path.exists():
            academy = json.loads(academy_path.read_text(encoding="utf-8"))
            for module_id, module in (academy.get("modules") or {}).items():
                for row in module.get("evidence") or []:
                    artifact_name = row.get("artifact")
                    artifact = self.repo_root / artifact_name if artifact_name else None
                    self._append_evidence({
                        "subject_id": module_id, "kind": "exercise",
                        "subskills": module.get("competencies") or [],
                        "score": float(row.get("score", 1.0)), "verified": bool(row.get("verified", True)),
                        "source_disjoint": bool(row.get("transfer_verified")),
                        "retained": False, "restart_retained": bool(row.get("restart_verified")), "independent_outcome": True,
                        "unfamiliar": False, "scaffolding": 0.70, "trials": 1,
                        "artifact": artifact_name, "artifact_hash": _sha256(artifact) if artifact and artifact.exists() else row.get("hash"),
                        "authority": ["academy_committed_assessment"], "imported": True,
                    })

    @staticmethod
    def _infer_kind(artifact: str) -> str:
        lowered = artifact.lower()
        if "repair" in lowered or "debug" in lowered:
            return "debugging"
        if "project" in lowered or "arena" in lowered:
            return "project"
        if "transfer" in lowered:
            return "transfer"
        if "apprentice" in lowered or "teacher" in lowered:
            return "exercise"
        return "assessment"

    def _append_evidence(self, row: Mapping[str, Any]) -> dict[str, Any]:
        body = dict(row)
        body.setdefault("created_at", _utc_timestamp())
        body.setdefault("recorded_epoch", time.time())
        evidence_id = "competency_evidence_" + _canonical_hash(body)[:20]
        if evidence_id in {item["evidence_id"] for item in self.state["evidence"]}:
            return next(item for item in self.state["evidence"] if item["evidence_id"] == evidence_id)
        body["evidence_id"] = evidence_id
        self.state["evidence"].append(body)
        return body

    @_state_transaction
    def record_evidence(self, *, subject_id: str, kind: str, subskills: Iterable[str],
                        score: float, artifact: str, artifact_hash: str,
                        verified: bool, source_disjoint: bool = False,
                        retained: bool = False, independent_outcome: bool = False,
                        unfamiliar: bool = False, scaffolding: float = 1.0,
                        trials: int = 1, authority: Iterable[str] = (),
                        project_family: str | None = None,
                        experience_class: str = "bounded_practical_execution",
                        retention_milestone_days: int | None = None) -> dict[str, Any]:
        if subject_id not in self.state["subjects"]:
            raise KeyError(subject_id)
        if kind not in KNOWLEDGE_KINDS | PRACTICAL_KINDS:
            raise ValueError(f"unsupported evidence kind: {kind}")
        declared = set(self.state["subjects"][subject_id]["subskills"])
        covered = set(subskills)
        if not covered or not covered <= declared:
            raise ValueError("evidence subskills must be non-empty and declared")
        if not 0.0 <= score <= 1.0 or not 0.0 <= scaffolding <= 1.0:
            raise ValueError("score and scaffolding must be in [0,1]")
        if retention_milestone_days is not None:
            if kind != "retention":
                raise ValueError("retention milestones may only be attached to retention evidence")
            if retention_milestone_days not in EXPERT_RETENTION_MILESTONES_DAYS:
                raise ValueError("unsupported retention milestone")
        row = self._append_evidence({
            "subject_id": subject_id, "kind": kind, "subskills": sorted(covered),
            "score": score, "verified": verified, "source_disjoint": source_disjoint,
            "retained": retained, "independent_outcome": independent_outcome,
            "unfamiliar": unfamiliar, "scaffolding": scaffolding, "trials": trials,
            "artifact": artifact, "artifact_hash": artifact_hash,
            "authority": list(authority), "imported": False,
            "project_family": project_family,
            "experience_class": experience_class,
            "retention_milestone_days": retention_milestone_days,
        })
        self._close_matching_contract(subject_id, row)
        self._save()
        return row

    def _close_matching_contract(self, subject_id: str, evidence: Mapping[str, Any]) -> None:
        if not evidence.get("verified"):
            return
        for contract in self.state["contracts"]:
            if contract.get("subject_id") == subject_id and contract.get("status") == "open":
                contract["status"] = "satisfied"
                contract["evidence_id"] = evidence["evidence_id"]
                contract["closed_at"] = _utc_timestamp()
                break

    @_state_transaction
    def park_executor_blocked_contract(self, contract_id: str, *, reason: str,
                                       required_authority: str) -> dict[str, Any]:
        """Park an unexecutable contract without treating it as satisfied.

        An open executor-capability blocker must not let the same contract
        monopolise every curriculum cycle.  Parking preserves the unmet
        requirement and its blocker while allowing the scheduler to select a
        different eligible subject.  No evidence or competence is awarded.
        """
        contract = next(
            row for row in self.state["contracts"]
            if row.get("contract_id") == contract_id
        )
        if contract.get("status") == "open":
            contract.update({
                "status": "blocked_executor_capability",
                "parked_at": _utc_timestamp(),
                "parked_reason": reason,
                "required_authority": required_authority,
            })
        if self.state.get("active_subject_id") == contract.get("subject_id"):
            self.state["active_subject_id"] = None
        self._save()
        return dict(contract)

    @_state_transaction
    def reissue_executor_blocked_contract(
        self, contract_id: str, *, executor_version: str, authority_artifact: str,
        artifact_hash: str,
    ) -> dict[str, Any]:
        """Reissue a parked obligation only after a new executable authority exists.

        The historical contract remains immutable evidence of the earlier gap.
        Reissuance creates a fresh commitment tied to the upgraded portfolio and
        resolves only the capability blocker; it awards no competency evidence.
        """
        prior = next(
            row for row in self.state["contracts"]
            if row.get("contract_id") == contract_id
        )
        if prior.get("status") != "blocked_executor_capability":
            raise ValueError("only an executor-blocked contract can be reissued")
        existing = next((
            row for row in self.state["contracts"]
            if row.get("reissued_from_contract_id") == contract_id
            and row.get("executor_version") == executor_version
            and row.get("status") == "open"
        ), None)
        if existing:
            return dict(existing)
        prior["status"] = "superseded_executor_upgrade"
        prior["superseded_at"] = _utc_timestamp()
        prior["superseded_by_executor_version"] = executor_version
        body = {
            "subject_id": prior["subject_id"],
            "target_level": prior.get("target_level"),
            "current_level": self.assess(prior["subject_id"])["overall_level"],
            "requirement": dict(prior.get("requirement") or {}),
            "generation_index": len(self.state["contracts"]),
            "prior_evidence_commitment": _canonical_hash(
                [row["evidence_id"] for row in self.evidence_for(prior["subject_id"])]
            ),
            "reissued_from_contract_id": contract_id,
            "executor_version": executor_version,
            "executor_authority_artifact": authority_artifact,
            "executor_authority_hash": artifact_hash,
            "minimum_score": prior.get("minimum_score", 0.90),
            "teacher_proposal_only": True,
            "solution_replay_forbidden": True,
            "requires_transfer": True,
            "requires_retention": True,
        }
        contract = {
            **body,
            "contract_id": "competency_contract_" + _canonical_hash(body)[:20],
            "commitment": _canonical_hash(body),
            "status": "open", "created_at": _utc_timestamp(),
            "created_epoch": time.time(), "no_progress_cycles": 0,
        }
        self.state["contracts"].append(contract)
        for blocker in self.state.get("blockers") or []:
            if (blocker.get("subject_id") == prior["subject_id"]
                    and blocker.get("blocker_type") == "executor_capability"
                    and blocker.get("status") == "open"):
                blocker.update({
                    "status": "resolved", "resolved_at": _utc_timestamp(),
                    "authority_artifact": authority_artifact,
                    "artifact_hash": artifact_hash,
                    "resolution": "versioned_executor_portfolio_installed",
                    "executor_version": executor_version,
                })
        self.state["active_subject_id"] = prior["subject_id"]
        self._save()
        return dict(contract)

    @_state_transaction
    def add_practical_blocker(self, *, subject_id: str, subskills: Iterable[str], reason: str,
                              required_authority: str,
                              blocker_type: str = "external_practical") -> dict[str, Any]:
        existing = next((row for row in self.state["blockers"]
                         if row.get("subject_id") == subject_id and row.get("reason") == reason
                         and row.get("status") == "open"), None)
        if existing:
            return existing
        body = {"subject_id": subject_id, "subskills": sorted(set(subskills)), "reason": reason,
                "required_authority": required_authority, "blocker_type": blocker_type,
                "status": "open", "created_at": _utc_timestamp()}
        body["blocker_id"] = "competency_blocker_" + _canonical_hash(body)[:18]
        if body["blocker_id"] not in {row["blocker_id"] for row in self.state["blockers"]}:
            self.state["blockers"].append(body)
        self._save()
        return body

    @_state_transaction
    def resolve_blocker(self, blocker_id: str, *, authority_artifact: str, artifact_hash: str) -> None:
        blocker = next(row for row in self.state["blockers"] if row["blocker_id"] == blocker_id)
        blocker.update({"status": "resolved", "authority_artifact": authority_artifact,
                        "artifact_hash": artifact_hash, "resolved_at": _utc_timestamp()})
        self._save()

    @_state_transaction
    def register_mission_gap(self, *, mission: str, subject_name: str, group: str,
                             proposed_subskills: Iterable[str], evidence: str) -> dict[str, Any]:
        slug = "".join(char if char.isalnum() else "_" for char in subject_name.lower()).strip("_")
        subject_id = "mission_" + slug[:48]
        self._add_subject(subject_id, subject_name, group, proposed_subskills,
                          importance=0.95, source="mission_gap")
        gap = {"gap_id": "mission_gap_" + _canonical_hash([mission, subject_id, evidence])[:18],
               "mission": mission, "subject_id": subject_id, "evidence": evidence,
               "status": "curriculum_required", "created_at": _utc_timestamp()}
        if gap["gap_id"] not in {row["gap_id"] for row in self.state["mission_gaps"]}:
            self.state["mission_gaps"].append(gap)
        self.state["active_subject_id"] = subject_id
        self._save()
        return gap

    @_state_transaction
    def install_comprehensive_curriculum(
        self, *, curriculum: Mapping[str, Any], curriculum_artifact: str
    ) -> dict[str, Any]:
        """Install curriculum definitions without awarding competence.

        The installer is deliberately catalogue-only. It adds declared
        capabilities, subjects, domains and bridge metadata, but never writes
        evidence or changes an assessment directly.
        """
        from backend.modules.hexcore.comprehensive_expertise_curriculum import (
            SCHEMA as COMPREHENSIVE_SCHEMA,
            validate_curriculum,
        )

        if curriculum.get("schema_version") != COMPREHENSIVE_SCHEMA:
            raise ValueError("unsupported comprehensive curriculum schema")
        validation = validate_curriculum(curriculum)
        if not validation["valid"]:
            raise ValueError(validation["errors"])
        prior_evidence = len(self.state.get("evidence") or [])
        digest = str(curriculum.get("curriculum_digest") or _canonical_hash(curriculum))

        installed_capabilities = []
        for capability_id, row in (curriculum.get("learning_capabilities") or {}).items():
            subject_id = f"capability_{capability_id}"
            self._add_subject(
                subject_id,
                str(row.get("name") or capability_id),
                "learning_capability",
                row.get("outcomes") or (),
                importance=1.0,
                source="comprehensive_expertise_curriculum",
            )
            self.state["subjects"][subject_id]["target_level"] = "expert"
            installed_capabilities.append(subject_id)

        installed_subjects = []
        for subject_id, row in (curriculum.get("subjects") or {}).items():
            self._add_subject(
                subject_id,
                str(row.get("name") or subject_id),
                str(row.get("domain") or "cross_domain"),
                row.get("competencies") or (),
                importance=0.9,
                source="comprehensive_expertise_curriculum",
            )
            installed = self.state["subjects"][subject_id]
            installed["target_level"] = "expert"
            installed["prerequisites"] = list(row.get("prerequisites") or [])
            installed["risk"] = str(row.get("risk") or "ordinary")
            installed_subjects.append(subject_id)

        domain_registry = self.state.setdefault("apprenticeship_domains", {})
        for domain_id, subject_ids in (curriculum.get("domains") or {}).items():
            domain_registry[f"comprehensive_{domain_id}"] = {
                "domain_id": f"comprehensive_{domain_id}",
                "name": str(domain_id).replace("_", " ").title(),
                "tier": 2,
                "subjects": list(subject_ids),
                "source": "comprehensive_expertise_curriculum",
            }

        record = {
            "schema_version": "aion.hexcore.installed_comprehensive_curriculum.v1",
            "curriculum_digest": digest,
            "curriculum_artifact": curriculum_artifact,
            "capability_subjects": installed_capabilities,
            "subject_academies": installed_subjects,
            "cross_domain_bridges": list(curriculum.get("cross_domain_bridges") or []),
            "capstones": list(curriculum.get("capstones") or []),
            "installed_at": _utc_timestamp(),
            "catalogue_only": True,
            "awards_competence": False,
            "evidence_records_before": prior_evidence,
            "evidence_records_after": len(self.state.get("evidence") or []),
        }
        if record["evidence_records_before"] != record["evidence_records_after"]:
            raise RuntimeError("curriculum installation attempted to award evidence")
        self.state.setdefault("external_curricula", {})[digest] = record
        self.state["active_subject_id"] = "capability_learning_strategy"
        self.state["programme_stage"] = "comprehensive_learn_to_learn"
        self._save()
        return {
            "curriculum_digest": digest,
            "capabilities_installed": len(installed_capabilities),
            "subjects_installed": len(installed_subjects),
            "domains_installed": len(curriculum.get("domains") or {}),
            "bridges_registered": len(curriculum.get("cross_domain_bridges") or []),
            "capstones_registered": len(curriculum.get("capstones") or []),
            "active_subject_id": self.state["active_subject_id"],
            "evidence_records_added": 0,
            "awards_competence": False,
        }

    @_state_transaction
    def set_active_subject(self, subject_id: str) -> None:
        if subject_id not in self.state["subjects"]:
            raise KeyError(subject_id)
        self.state["active_subject_id"] = subject_id
        self._save()

    def evidence_for(self, subject_id: str) -> list[dict[str, Any]]:
        return [row for row in self.state["evidence"]
                if row.get("subject_id") == subject_id and row.get("verified") is True]

    def assess(self, subject_id: str) -> dict[str, Any]:
        subject = self.state["subjects"][subject_id]
        raw_evidence = self.evidence_for(subject_id)
        # A scheduler retry of the same named case is an audit receipt, not a
        # new learning family.  Preserve all raw rows but score each explicit
        # family once per kind and subskill set.  Legacy rows without a family
        # remain distinct because their equivalence cannot be inferred safely.
        evidence = []
        seen_families: set[tuple[Any, ...]] = set()
        for row in raw_evidence:
            family = row.get("project_family")
            key = (
                "family", row.get("kind"), str(family),
                tuple(sorted(str(skill) for skill in (row.get("subskills") or []))),
            ) if family else ("receipt", str(row.get("evidence_id")))
            if key in seen_families:
                continue
            seen_families.add(key)
            evidence.append(row)
        subskills = subject["subskills"]
        per_skill: dict[str, dict[str, int]] = {
            skill: {"knowledge": 0, "practical": 0, "total": 0} for skill in subskills
        }
        for row in evidence:
            for skill in row.get("subskills") or []:
                if skill not in per_skill:
                    continue
                per_skill[skill]["total"] += 1
                if row.get("kind") in KNOWLEDGE_KINDS:
                    per_skill[skill]["knowledge"] += 1
                if row.get("kind") in PRACTICAL_KINDS:
                    per_skill[skill]["practical"] += 1
        knowledge_covered = sum(value["knowledge"] > 0 for value in per_skill.values())
        practical_covered = sum(value["practical"] > 0 for value in per_skill.values())
        coverage_k = knowledge_covered / max(1, len(subskills))
        coverage_p = practical_covered / max(1, len(subskills))
        mean_score = sum(float(row.get("score", 0)) for row in evidence) / max(1, len(evidence))
        kinds = {row.get("kind") for row in evidence}
        project_rows = [row for row in evidence if row.get("kind") == "project"]
        projects = len({row.get("project_family") or row.get("evidence_id") for row in project_rows})
        unfamiliar_projects = len({row.get("project_family") or row.get("evidence_id")
                                   for row in project_rows if row.get("unfamiliar")})
        debugging = sum(row.get("kind") == "debugging" for row in evidence)
        # Source-disjoint assessment is valuable, but it is not automatically
        # a transfer outcome.  Transfer is credited only when the contract was
        # explicitly a transfer task; otherwise ordinary lessons and exercises
        # could silently satisfy this practical gate.
        transfers = sum(row.get("kind") == "transfer" for row in evidence)
        retention_rows = [
            row for row in evidence
            if bool(row.get("retained")) or row.get("kind") == "retention"
        ]
        retention = len(retention_rows)
        retention_milestones = sorted({
            int(row["retention_milestone_days"])
            for row in retention_rows
            if row.get("retention_milestone_days") in EXPERT_RETENTION_MILESTONES_DAYS
        })
        long_term_retention_complete = all(
            milestone in retention_milestones
            for milestone in EXPERT_RETENTION_MILESTONES_DAYS
        )
        independent = sum(bool(row.get("independent_outcome")) for row in evidence)
        trials = sum(int(row.get("trials") or 1) for row in evidence)
        scaffold_values = [float(row.get("scaffolding", 1.0)) for row in evidence if not row.get("imported")]
        latest_scaffolding = sum(scaffold_values[-3:]) / len(scaffold_values[-3:]) if scaffold_values else 1.0

        knowledge = "unassessed"
        if evidence and coverage_k >= 0.20 and mean_score >= 0.60:
            knowledge = "beginner"
        if len(evidence) >= 2 and coverage_k >= 0.50 and mean_score >= 0.75:
            knowledge = "intermediate"
        if (coverage_k >= 0.90 and all(value["knowledge"] >= 2 for value in per_skill.values())
                and len(evidence) >= 8 and mean_score >= 0.90 and trials >= 8):
            knowledge = "advanced"
        if (knowledge == "advanced" and all(value["knowledge"] >= 4 for value in per_skill.values())
                and len(evidence) >= 20 and mean_score >= 0.95
                and long_term_retention_complete):
            knowledge = "expert"

        practical = "unassessed"
        if practical_covered and mean_score >= 0.60:
            practical = "beginner"
        if (coverage_p >= 0.50 and len(evidence) >= 3 and projects >= 1 and debugging >= 1
                and transfers >= 1 and trials >= 3):
            practical = "intermediate"
        if (coverage_p >= 0.90 and all(value["practical"] >= 2 for value in per_skill.values())
                and projects >= 5 and unfamiliar_projects >= 3 and debugging >= 3
                and transfers >= 2 and retention >= 1 and independent >= 3
                and trials >= 10 and latest_scaffolding <= 0.35):
            practical = "advanced"
        if (practical == "advanced" and all(value["practical"] >= 4 for value in per_skill.values())
                and projects >= 12 and unfamiliar_projects >= 8 and debugging >= 6
                and transfers >= 4 and long_term_retention_complete and independent >= 8
                and trials >= 25 and latest_scaffolding <= 0.15):
            practical = "expert"

        open_blockers = [row for row in self.state["blockers"]
                         if row["subject_id"] == subject_id and row["status"] == "open"]
        overall = LEVELS[min(LEVEL_INDEX[knowledge], LEVEL_INDEX[practical])]
        display = overall
        if LEVEL_INDEX[knowledge] >= LEVEL_INDEX["advanced"] and LEVEL_INDEX[practical] < LEVEL_INDEX["advanced"] and open_blockers:
            display = ("advanced_theory_practical_blocked"
                       if all(row.get("blocker_type", "external_practical") == "external_practical" for row in open_blockers)
                       else "advanced_theory_executor_blocked")
        target = subject.get("target_level", DEFAULT_TARGET)
        target_reached = LEVEL_INDEX[overall] >= LEVEL_INDEX[target]
        return {
            "subject_id": subject_id, "name": subject["name"], "group": subject["group"],
            "knowledge_level": knowledge, "practical_level": practical,
            "overall_level": overall, "display_level": display, "target_level": target,
            "target_reached": target_reached, "evidence_records": len(evidence),
            "raw_evidence_records": len(raw_evidence),
            "coverage": {"knowledge": coverage_k, "practical": coverage_p},
            "mean_score": mean_score, "projects": projects,
            "unfamiliar_projects": unfamiliar_projects, "debugging_cases": debugging,
            "transfer_cases": transfers, "retention_cases": retention,
            "retention_milestones_completed": retention_milestones,
            "required_expert_retention_milestones": list(EXPERT_RETENTION_MILESTONES_DAYS),
            "long_term_retention_complete": long_term_retention_complete,
            "independent_outcomes": independent, "trials": trials,
            "latest_scaffolding": latest_scaffolding, "per_subskill": per_skill,
            "open_blockers": open_blockers, "evidence_kinds": sorted(str(kind) for kind in kinds),
        }

    def _unlock_expert_targets(self) -> list[str]:
        """Move each independently Advanced subject into the depth lane."""
        unlocked = []
        lane = self.state.setdefault(
            "lane_scheduler", {"breadth_contracts": 0, "depth_contracts": 0,
                               "expert_unlocks": []},
        )
        known = set(lane.setdefault("expert_unlocks", []))
        for subject_id, subject in self.state["subjects"].items():
            assessment = self.assess(subject_id)
            if (assessment["overall_level"] == "advanced"
                    and subject.get("target_level", DEFAULT_TARGET) == "advanced"):
                subject["target_level"] = "expert"
                if subject_id not in known:
                    lane["expert_unlocks"].append(subject_id)
                    known.add(subject_id)
                unlocked.append(subject_id)
        if lane["expert_unlocks"]:
            self.state["programme_stage"] = "parallel_breadth_and_expert_depth"
        return unlocked

    def _priority_subject(self) -> str | None:
        now = time.time()
        open_contracts = [row for row in self.state["contracts"] if row.get("status") == "open"]

        # A due retention assessment has priority because it is now an
        # actionable closed-book test.  A future retention assessment parks
        # only its subject; it must never pause the whole academy.
        due_retention = [
            row for row in open_contracts
            if (row.get("requirement") or {}).get("not_before_epoch")
            and now >= float((row.get("requirement") or {})["not_before_epoch"])
        ]
        if due_retention:
            return min(due_retention, key=lambda row: float(row.get("created_epoch") or 0))["subject_id"]

        future_waiting_subjects = {
            row["subject_id"] for row in open_contracts
            if (row.get("requirement") or {}).get("not_before_epoch")
            and now < float((row.get("requirement") or {})["not_before_epoch"])
        }
        executor_blocked_subjects = {
            row["subject_id"] for row in self.state.get("blockers") or []
            if row.get("status") == "open" and row.get("blocker_type") == "executor_capability"
        }
        # The comprehensive curriculum allocates a real bootstrapping lane to
        # learning abilities.  Older depth targets must not monopolise the
        # scheduler and make the visible learn-to-learn phase cosmetic.  Use a
        # rolling contract window: when fewer than three of the latest six fresh
        # contracts concern a learning capability, the next available ability
        # receives priority.  This reserves half of the primary lane for the
        # abilities that improve every other curriculum lane while leaving the
        # other half for domain and real-adapter prerequisites. Blocked
        # abilities remain fail-closed.
        available_capabilities = []
        if self.state.get("external_curricula"):
            for subject_id, subject in self.state["subjects"].items():
                if (subject.get("group") != "learning_capability"
                        or subject_id in future_waiting_subjects
                        or subject_id in executor_blocked_subjects):
                    continue
                result = self.assess(subject_id)
                if not result["target_reached"]:
                    available_capabilities.append(subject_id)
        recent_contracts = self.state.get("contracts", [])[-6:]
        recent_capability_contracts = sum(
            str(row.get("subject_id") or "").startswith("capability_")
            for row in recent_contracts
        )
        if available_capabilities and recent_capability_contracts < 3:
            # Bootstrap breadth before repeatedly deepening one ability. Pick
            # the least-evidenced, least-recently-contracted available ability;
            # importance breaks ties. This gives every declared learning
            # capability practical contact instead of pinning the scheduler to
            # whichever capability happened to become active first.
            last_contract_index = {
                subject_id: max(
                    (index for index, row in enumerate(self.state.get("contracts") or [])
                     if row.get("subject_id") == subject_id),
                    default=-1,
                )
                for subject_id in available_capabilities
            }
            return min(
                available_capabilities,
                key=lambda subject_id: (
                    self.assess(subject_id)["evidence_records"],
                    last_contract_index[subject_id],
                    -float(self.state["subjects"][subject_id].get("importance", 0.5)),
                    subject_id,
                ),
            )
        breadth_ranked = []
        depth_ranked = []
        for subject_id, subject in self.state["subjects"].items():
            if subject_id in future_waiting_subjects or subject_id in executor_blocked_subjects:
                continue
            result = self.assess(subject_id)
            if (result["target_reached"]
                    or result["display_level"] in {
                        "advanced_theory_practical_blocked", "advanced_theory_executor_blocked"
                    }):
                continue
            focus = self.state.get("depth_acceleration") or {}
            focus_targets = list(focus.get("advanced_targets") or [])
            focus_boost = 150.0 if subject_id in focus_targets else 0.0
            mission_boost = 100.0 if subject["source"] == "mission_gap" else 0.0
            foundation_priority = FOUNDATION_PRIORITY.get(subject_id, 0)
            rank = (focus_boost + mission_boost, foundation_priority, float(subject.get("importance", 0.5)),
                    -LEVEL_INDEX[result["overall_level"]], subject_id)
            row = (rank, subject_id)
            if subject.get("target_level") == "expert" and result["overall_level"] == "advanced":
                depth_ranked.append(row)
            else:
                breadth_ranked.append(row)

        lane = self.state.setdefault(
            "lane_scheduler", {"breadth_contracts": 0, "depth_contracts": 0,
                               "expert_unlocks": []},
        )
        breadth_count = int(lane.get("breadth_contracts", 0))
        depth_count = int(lane.get("depth_contracts", 0))
        depth_due = bool(depth_ranked and (not breadth_ranked or depth_count * 3 < breadth_count))
        selected = depth_ranked if depth_due else breadth_ranked or depth_ranked
        if not selected:
            return None
        active = self.state.get("active_subject_id")
        focus_targets = set(((self.state.get("depth_acceleration") or {}).get("advanced_targets") or []))
        focused_available = any(row[1] in focus_targets for row in selected)
        active_match = next(
            (row for row in selected if row[1] == active
             and (not focused_available or active in focus_targets)),
            None,
        )
        return (active_match or max(selected))[1]

    def _next_requirement(self, result: Mapping[str, Any]) -> dict[str, Any]:
        expert = result.get("target_level") == "expert"
        knowledge_repetitions = 4 if expert else 2
        practical_repetitions = 4 if expert else 2
        project_target = 12 if expert else 5
        unfamiliar_target = 8 if expert else 3
        debugging_target = 6 if expert else 3
        transfer_target = 4 if expert else 2
        independent_target = 8 if expert else 3
        trial_target = 25 if expert else 10
        scaffolding_ceiling = 0.15 if expert else 0.35
        for skill, counts in result["per_subskill"].items():
            if counts["knowledge"] < knowledge_repetitions:
                return {"kind": "lesson" if counts["knowledge"] == 0 else "knowledge_test", "subskills": [skill],
                        "authority": "authoritative_source_plus_withheld_assessment"}
        for skill, counts in result["per_subskill"].items():
            if counts["practical"] < practical_repetitions:
                return {"kind": "exercise", "subskills": [skill],
                        "authority": "independent_execution_or_observed_outcome"}
        if result["projects"] < project_target:
            return {"kind": "project", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "unfamiliar_project_with_hidden_outcome"}
        # Project count alone is not breadth.  A curriculum may already hold
        # five exercises from one familiar template while still having zero
        # unfamiliar projects.  Continue generating genuinely new project
        # families until this independent gate is met.
        if result["unfamiliar_projects"] < unfamiliar_target:
            return {"kind": "project", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "unfamiliar_project_with_hidden_outcome",
                    "novelty_required": True,
                    "minimum_unfamiliar_projects": unfamiliar_target}
        if result["debugging_cases"] < debugging_target:
            return {"kind": "debugging", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "injected_or_natural_failure_and_later_verification"}
        if result["transfer_cases"] < transfer_target:
            return {"kind": "transfer", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "source_disjoint_domain_outcome"}
        completed_milestones = set(result.get("retention_milestones_completed") or [])
        required_milestones = EXPERT_RETENTION_MILESTONES_DAYS if expert else (1,)
        missing_milestone = next(
            (milestone for milestone in required_milestones if milestone not in completed_milestones),
            None,
        )
        if missing_milestone is not None:
            subject_id = str(result.get("subject_id") or "")
            timestamps = [
                float(row.get("recorded_epoch") or 0)
                for row in self.evidence_for(subject_id)
                if float(row.get("recorded_epoch") or 0) > 0
            ]
            learning_anchor = min(timestamps) if timestamps else time.time()
            return {
                "kind": "retention", "subskills": list(result["per_subskill"]),
                "authority": "elapsed_closed_book_fresh_tasks",
                "retention_milestone_days": missing_milestone,
                "not_before_epoch": learning_anchor + missing_milestone * 24 * 3600,
            }
        if result["independent_outcomes"] < independent_target:
            return {"kind": "project", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "independently_owned_fresh_outcome",
                    "independent_outcome_required": True}
        if result["trials"] < trial_target or result["latest_scaffolding"] > scaffolding_ceiling:
            return {"kind": "project", "subskills": list(result["per_subskill"])[0:4],
                    "authority": "fresh_low_scaffolding_consistency_outcome",
                    "maximum_scaffolding": scaffolding_ceiling,
                    "minimum_trials": trial_target}
        return {"kind": "repeated_trial", "subskills": list(result["per_subskill"]),
                "authority": "fresh_seed_consistency"}

    @_state_transaction
    def configure_depth_acceleration(
        self, *, advanced_targets: Iterable[str], expert_targets: Iterable[str]
    ) -> dict[str, Any]:
        """Persist a cross-domain depth lane without awarding any evidence.

        The lane changes scheduling only.  Existing assessment, execution,
        delayed-retention and authority gates remain the sole level authority.
        """
        advanced = [sid for sid in dict.fromkeys(advanced_targets) if sid in self.state["subjects"]]
        expert = [sid for sid in dict.fromkeys(expert_targets) if sid in advanced]
        self.state["depth_acceleration"] = {
            "policy_version": CURRICULUM_POLICY_VERSION,
            "advanced_targets": advanced,
            "expert_targets": expert,
            "configured_at": _utc_timestamp(),
            "scheduling_only": True,
            "awards_competency": False,
        }
        superseded = self._supersede_premature_retention_contracts(set(advanced))
        self.state["depth_acceleration"]["superseded_premature_retention_contracts"] = superseded
        self._save()
        return dict(self.state["depth_acceleration"])

    def _supersede_premature_retention_contracts(self, subject_ids: set[str]) -> list[str]:
        """Release legacy retention waits that skipped newly explicit gates."""
        superseded: list[str] = []
        for contract in self.state.get("contracts") or []:
            if (contract.get("status") != "open" or contract.get("subject_id") not in subject_ids
                    or (contract.get("requirement") or {}).get("kind") != "retention"):
                continue
            result = self.assess(contract["subject_id"])
            expert = result.get("target_level") == "expert"
            prerequisites_met = bool(
                result["projects"] >= (12 if expert else 5)
                and result["unfamiliar_projects"] >= (8 if expert else 3)
                and result["debugging_cases"] >= (6 if expert else 3)
                and result["transfer_cases"] >= (4 if expert else 2)
            )
            if prerequisites_met:
                continue
            contract["status"] = "superseded_missing_prerequisite"
            contract["superseded_at"] = _utc_timestamp()
            contract["superseded_reason"] = (
                "Legacy retention appointment preceded the explicit unfamiliar-project gate; "
                "no evidence was awarded and the missing practical requirement resumes."
            )
            superseded.append(contract["contract_id"])
        return superseded

    @_state_transaction
    def step(self) -> dict[str, Any]:
        unlocked = self._unlock_expert_targets()
        subject_id = self._priority_subject()
        if subject_id is None:
            advanced = [row for row in self.state["subjects"].values()
                        if LEVEL_INDEX[self.assess(row["subject_id"])["overall_level"]] >= LEVEL_INDEX["advanced"]]
            deepen = [row for row in advanced if row.get("target_level") != "expert"]
            if deepen:
                for row in deepen:
                    row["target_level"] = "expert"
                self.state["programme_stage"] = "advanced_to_expert"
                subject_id = sorted(deepen, key=lambda row: (-float(row.get("importance", 0)), row["subject_id"]))[0]["subject_id"]
                self.state["active_subject_id"] = subject_id
                action = {"status": "expert_deepening_unlocked", "subject_id": subject_id,
                          "subjects_raised_to_expert": len(deepen)}
            else:
                action = {"status": "all_current_targets_reached_or_externally_blocked"}
        else:
            self.state["active_subject_id"] = subject_id
            existing = next((row for row in self.state["contracts"]
                             if row["subject_id"] == subject_id and row["status"] == "open"), None)
            result = self.assess(subject_id)
            if existing:
                age = time.time() - float(existing["created_epoch"])
                existing["no_progress_cycles"] = int(existing.get("no_progress_cycles", 0)) + 1
                not_before = (existing.get("requirement") or {}).get("not_before_epoch")
                if not_before and time.time() < float(not_before):
                    contract_status = "waiting_elapsed_retention"
                else:
                    contract_status = "executor_required" if age < 1800 else "stalled_executor_required"
                action = {"status": contract_status,
                          "subject_id": subject_id, "contract_id": existing["contract_id"],
                          "requirement": existing["requirement"], "age_seconds": age,
                          "no_progress_cycles": existing["no_progress_cycles"]}
            else:
                requirement = self._next_requirement(result)
                body = {"subject_id": subject_id, "target_level": result["target_level"],
                        "current_level": result["overall_level"], "requirement": requirement,
                        "generation_index": len(self.state["contracts"]),
                        "prior_evidence_commitment": _canonical_hash(
                            [row["evidence_id"] for row in self.evidence_for(subject_id)]
                        ),
                        "minimum_score": 0.90, "teacher_proposal_only": True,
                        "solution_replay_forbidden": True, "requires_transfer": True,
                        "requires_retention": True}
                contract = {**body, "contract_id": "competency_contract_" + _canonical_hash(body)[:20],
                            "commitment": _canonical_hash(body), "status": "open",
                            "created_at": _utc_timestamp(), "created_epoch": time.time(),
                            "no_progress_cycles": 0}
                self.state["contracts"].append(contract)
                lane_key = (
                    "depth_contracts"
                    if result["target_level"] == "expert" and result["overall_level"] == "advanced"
                    else "breadth_contracts"
                )
                scheduler = self.state.setdefault("lane_scheduler", {})
                scheduler[lane_key] = int(scheduler.get(lane_key, 0)) + 1
                action = {"status": "curriculum_contract_created", "subject_id": subject_id,
                          "contract_id": contract["contract_id"], "requirement": requirement,
                          "assessment": result,
                          "lane": "expert_depth" if lane_key == "depth_contracts" else "breadth"}
        if unlocked:
            action["expert_targets_unlocked"] = unlocked
        cycle = {"cycle_id": "competency_cycle_" + _canonical_hash([len(self.state["curriculum_cycles"]), action])[:18],
                 "created_at": _utc_timestamp(), "action": action}
        self.state["curriculum_cycles"].append(cycle)
        self.state["curriculum_cycles"] = self.state["curriculum_cycles"][-2000:]
        self._save()
        return {"cycle": cycle, "summary": self.summary()}

    def summary(self) -> dict[str, Any]:
        assessments = [self.assess(subject_id) for subject_id in self.state["subjects"]]
        counts: dict[str, int] = {}
        for row in assessments:
            counts[row["display_level"]] = counts.get(row["display_level"], 0) + 1
        valid_evidence = [row for row in self.state["evidence"]
                          if row.get("verified") is True and not row.get("invalidated_reason")]
        invalidated_evidence = [row for row in self.state["evidence"]
                                if row.get("invalidated_reason")]
        domain_rows = self.domain_assessments()
        lane = self.state.get("lane_scheduler") or {}
        expert_queue = [
            row for row in assessments
            if row["target_level"] == "expert" and row["overall_level"] == "advanced"
        ]
        return {"subjects": len(assessments), "levels": counts,
                "advanced_or_expert": sum(LEVEL_INDEX[row["overall_level"]] >= LEVEL_INDEX["advanced"] for row in assessments),
                "active_subject_id": self.state.get("active_subject_id"),
                "open_contracts": sum(row["status"] == "open" for row in self.state["contracts"]),
                "open_external_blockers": sum(row["status"] == "open" for row in self.state["blockers"]),
                "mission_gaps": len(self.state["mission_gaps"]),
                "programme_stage": self.state.get("programme_stage", "foundation_to_advanced"),
                "expert_depth_queue": len(expert_queue),
                "breadth_contracts": int(lane.get("breadth_contracts", 0)),
                "depth_contracts": int(lane.get("depth_contracts", 0)),
                "expert_unlocks": len(lane.get("expert_unlocks") or []),
                "depth_acceleration": self.state.get("depth_acceleration") or {},
                "top_level_domains": len(domain_rows),
                "domains_complete": sum(row["target_reached"] for row in domain_rows.values()),
                "evidence_records": len(valid_evidence),
                "invalidated_evidence_records": len(invalidated_evidence),
                "owner_lesson_steps": self.state["owner_lesson_steps"],
                "unsafe_actions": self.state["unsafe_actions"]}

    def snapshot(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA, "created_at": _utc_timestamp(),
                "summary": self.summary(),
                "domains": self.domain_assessments(),
                "subjects": {subject_id: self.assess(subject_id) for subject_id in self.state["subjects"]},
                "active_contracts": [row for row in self.state["contracts"] if row["status"] == "open"],
                "blockers": self.state["blockers"], "mission_gaps": self.state["mission_gaps"],
                "boundary": "Competency levels are earned from evidence gates. Catalogue inclusion and assessment passes do not imply competence."}

    def domain_assessments(self) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for domain_id, domain in (self.state.get("apprenticeship_domains") or {}).items():
            subject_ids = [subject_id for subject_id in domain.get("subjects") or []
                           if subject_id in self.state["subjects"]]
            assessments = [self.assess(subject_id) for subject_id in subject_ids]
            reached = [row for row in assessments if row["target_reached"]]
            subskills = sum(len(self.state["subjects"][subject_id]["subskills"])
                            for subject_id in subject_ids)
            next_subject = next((row for row in assessments
                                 if not row["target_reached"]
                                 and row["display_level"] != "advanced_theory_practical_blocked"), None)
            rows[domain_id] = {
                "domain_id": domain_id, "name": domain.get("name", domain_id),
                "tier": int(domain.get("tier") or 3), "subjects": subject_ids,
                "subject_count": len(subject_ids), "subjects_at_target": len(reached),
                "subskills_declared": subskills,
                "progress": len(reached) / max(1, len(subject_ids)),
                "target_reached": bool(subject_ids and len(reached) == len(subject_ids)),
                "next_subject_id": (next_subject or {}).get("subject_id"),
                "next_subject_name": (next_subject or {}).get("name"),
            }
        return rows

    @_state_transaction
    def prioritize_for_mission(self, *, subject_id: str, mission: str,
                               evidence: str = "mission_capability_gap") -> dict[str, Any]:
        if subject_id not in self.state["subjects"]:
            raise KeyError(subject_id)
        body = {"demand_id": "mission_demand_" + _canonical_hash([mission, subject_id, evidence])[:18],
                "mission": mission, "subject_id": subject_id, "evidence": evidence,
                "created_at": _utc_timestamp(), "status": "active_until_target"}
        demands = self.state.setdefault("mission_demands", [])
        if body["demand_id"] not in {row.get("demand_id") for row in demands}:
            demands.append(body)
        if not self.assess(subject_id)["target_reached"]:
            self.state["active_subject_id"] = subject_id
        self._save()
        return body

    def capability_query(self, query: str) -> dict[str, Any]:
        normalized = "".join(char for char in query.lower() if char.isalnum())
        candidates = []
        for subject_id, subject in self.state["subjects"].items():
            forms = {
                "".join(char for char in subject_id.lower() if char.isalnum()),
                "".join(char for char in str(subject.get("name", "")).lower() if char.isalnum()),
            }
            score = max((len(form) for form in forms if form and (form in normalized or normalized in form)), default=0)
            if score:
                candidates.append((score, subject_id))
        if not candidates:
            return {"answer": "unknown_subject", "query": query,
                    "action": "register_mission_gap_or_clarify_subject"}
        subject_id = max(candidates)[1]
        result = self.assess(subject_id)
        level = result["overall_level"]
        readiness = {
            "unassessed": "not_ready",
            "beginner": "practice_only",
            "intermediate": "bounded_work_with_strong_verification",
            "advanced": "independent_work_with_normal_verification",
            "expert": "lead_complex_work_and_teach",
        }[level]
        return {"answer": "known", "subject_id": subject_id, "name": result["name"],
                "knowledge_level": result["knowledge_level"], "practical_level": result["practical_level"],
                "overall_level": level, "display_level": result["display_level"],
                "work_readiness": readiness, "target_level": result["target_level"],
                "target_reached": result["target_reached"], "blockers": result["open_blockers"]}

    def _save(self) -> None:
        self.state["updated_at"] = _utc_timestamp()
        if self._lock_depth:
            _atomic_write(self.state_path, self.state)
            self._loaded_digest = _state_digest(self.state_path)
            return
        with exclusive_file_lock(self.lock_path):
            _atomic_write(self.state_path, self.state)
            self._loaded_digest = _state_digest(self.state_path)
