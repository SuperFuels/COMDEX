"""Mission -> capability -> knowledge -> governed action binding for AION.

This module does not execute arbitrary work. It translates a broad natural-
language objective into an inspectable capability contract, checks the
progressive competency authority, and tells the Action Switch whether to act,
act with stronger verification, or learn before acting.
"""
from __future__ import annotations

import re
import math
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.progressive_competency_system import (
    LEVEL_INDEX,
    ProgressiveCompetencySystem,
)


TASK_ARCHETYPES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("algorithm", "graph", "tree", "sorting", "search algorithm", "dependency scheduler"),
     ("algorithms_data_structures",)),
    (("test", "testing", "debug", "diagnose", "regression", "counterexample", "failure"),
     ("testing_debugging",)),
    (("distributed", "replicated", "replication", "quorum", "consensus", "partition"),
     ("distributed_systems",)),
    (("cloud", "deployment", "deploy", "rollout", "observability", "sre"),
     ("cloud_devops_sre", "architecture_operations")),
    (("process", "processes", "filesystem", "ipc", "thread", "memory allocation"),
     ("operating_systems",)),
    (("network", "networking", "tls", "dns", "http", "routing"),
     ("networking", "security_engineering")),
    (("app", "application", "software", "service", "api"),
     ("software_engineering", "testing_debugging", "security_engineering",
      "product_project_management")),
    (("web", "browser", "frontend", "website"),
     ("web_platform", "javascript_typescript", "ui_product_design", "security_engineering")),
    (("database", "ledger", "transaction", "account", "payment"),
     ("sql_databases", "database_engineering", "security_engineering")),
    (("analyse", "analyze", "data", "forecast", "statistics"),
     ("data_statistics", "python", "scientific_method")),
    (("research", "evidence", "report", "document", "policy"),
     ("research_communication", "english", "scientific_method")),
    (("business", "startup", "market", "customer", "product"),
     ("business_management", "economics_entrepreneurship", "product_project_management",
      "finance_accounting")),
    (("sensor", "physical", "robot", "device", "control"),
     ("embedded_robotics", "physics", "scientific_method")),
    (("secure", "security", "threat", "attack", "auth"),
     ("security_engineering", "secure_engineering")),
)


STOPWORDS = {
    "and", "the", "that", "then", "with", "from", "into", "for", "this", "those",
    "given", "using", "use", "must", "should", "need", "needs", "task", "objective",
}
DEFAULT_ROUTING_POLICY = {
    "semantic_floor": 3.0, "peak_ratio": 0.65,
    "minimum_overlap": 2, "maximum_subjects": 6,
    "contextual_archetypes": False,
    "additional_stopwords": [],
}


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


class MissionCapabilityActionHarness:
    """Bind mission semantics to actual retained competence before action."""

    def __init__(self, *, repo_root: Path,
                 state_path: Path | None = None,
                 routing_policy: Mapping[str, Any] | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.system = ProgressiveCompetencySystem(
            repo_root=self.repo_root,
            state_path=(state_path or self.repo_root /
                        "backend/modules/hexcore/data/progressive_competency/state.json"),
        )
        champion_path = (
            self.repo_root / "backend/modules/hexcore/data/capability_routing_champion.json"
        )
        retained = {}
        if routing_policy is None and champion_path.exists():
            try:
                retained = json.loads(champion_path.read_text(encoding="utf-8")).get("policy") or {}
            except (OSError, ValueError, TypeError):
                retained = {}
        self.routing_policy = {**DEFAULT_ROUTING_POLICY, **retained, **dict(routing_policy or {})}
        # A promoted routing policy may improve recall, but it must not weaken
        # the precision floor that prevents a generic token (for example
        # "dependency" or "allocation") from importing unrelated domains.
        # These are governance bounds, not tournament-tunable hyperparameters.
        self.routing_policy["semantic_floor"] = max(
            float(DEFAULT_ROUTING_POLICY["semantic_floor"]),
            float(self.routing_policy["semantic_floor"]),
        )
        self.routing_policy["peak_ratio"] = max(
            float(DEFAULT_ROUTING_POLICY["peak_ratio"]),
            float(self.routing_policy["peak_ratio"]),
        )
        self.routing_policy["minimum_overlap"] = max(
            int(DEFAULT_ROUTING_POLICY["minimum_overlap"]),
            int(self.routing_policy["minimum_overlap"]),
        )
        self.routing_policy["maximum_subjects"] = min(
            int(DEFAULT_ROUTING_POLICY["maximum_subjects"]),
            max(1, int(self.routing_policy["maximum_subjects"])),
        )

    def _explicit_requirements(self, plan: Mapping[str, Any]) -> list[str]:
        raw = plan.get("required_capabilities") or plan.get("capability_requirements") or []
        values: list[str] = []
        for item in raw:
            values.append(str(item.get("capability") if isinstance(item, Mapping) else item))
        return [value for value in values if value]

    def infer_subjects(self, objective: str, *, explicit: Iterable[str] = ()) -> list[str]:
        extra_stopwords = set(self.routing_policy.get("additional_stopwords") or [])
        text_tokens = _tokens(objective) - extra_stopwords
        scores: dict[str, float] = {}
        archetype_requirements: list[str] = []
        vocabularies: dict[str, set[str]] = {}
        for subject_id, subject in self.system.state["subjects"].items():
            vocabulary = _tokens(subject_id.replace("_", " ") + " " + str(subject.get("name", ""))) - extra_stopwords
            vocabulary.update(_tokens(" ".join(subject.get("subskills") or [])) - extra_stopwords)
            vocabularies[subject_id] = vocabulary
        document_frequency = {
            token: sum(token in vocabulary for vocabulary in vocabularies.values())
            for token in text_tokens
        }
        for subject_id, vocabulary in vocabularies.items():
            overlap = text_tokens & vocabulary
            if overlap:
                scores[subject_id] = scores.get(subject_id, 0.0) + sum(
                    1.0 + math.log((len(vocabularies) + 1) / (document_frequency[token] + 1))
                    for token in overlap
                )
        lowered = objective.lower()
        for cues, subjects in TASK_ARCHETYPES:
            hits = sum(bool(re.search(r"\b" + re.escape(cue) + r"\b", lowered)) for cue in cues)
            # "Replication" is polysemous. Scientific replication does not
            # imply a distributed-system topology unless systems context is
            # independently present. This switch is tournament-controlled so
            # the retained champion can be compared with the challenger.
            if (
                self.routing_policy.get("contextual_archetypes")
                and "distributed_systems" in subjects
                and "replication" in lowered
                and any(token in lowered for token in ("experiment", "measurement", "causal", "uncertainty"))
                and not any(token in lowered for token in ("cluster", "node", "quorum", "service", "database"))
            ):
                hits -= int(bool(re.search(r"\breplication\b", lowered)))
            if hits:
                for subject_id in subjects:
                    if subject_id in self.system.state["subjects"]:
                        scores[subject_id] = scores.get(subject_id, 0.0) + 1.5 * hits
                        if subject_id not in archetype_requirements:
                            archetype_requirements.append(subject_id)
        for requested in explicit:
            query = self.system.capability_query(requested)
            if query.get("answer") == "known":
                scores[str(query["subject_id"])] = scores.get(str(query["subject_id"]), 0.0) + 20.0
        ranked = sorted(scores, key=lambda subject_id: (-scores[subject_id], subject_id))
        # Preserve the essential capabilities implied by the task archetype,
        # then use semantic scores to fill the bounded mission contract.
        # Do not convert a single generic overlapping word into a compulsory
        # domain. Keep explicit/archetypal requirements, then only add strong
        # discriminative matches near the best observed semantic score.
        semantic_peak = max((scores[row] for row in ranked), default=0.0)
        strong = [
            subject_id for subject_id in ranked
            if scores[subject_id] >= max(float(self.routing_policy["semantic_floor"]),
                                         semantic_peak * float(self.routing_policy["peak_ratio"]))
            and (
                len(text_tokens & vocabularies[subject_id]) >= int(self.routing_policy["minimum_overlap"])
                or str(self.system.state["subjects"][subject_id].get("name", "")).lower() in lowered
            )
            and subject_id not in archetype_requirements
        ]
        ordered = archetype_requirements + strong
        return ordered[:int(self.routing_policy["maximum_subjects"])]

    @staticmethod
    def _technology(objective: str) -> dict[str, Any]:
        text = objective.lower()
        if any(term in text for term in ("browser", "frontend", "web app", "website")):
            return {"stack": ["TypeScript", "HTML/CSS"], "reason": "browser-native typed application"}
        if any(term in text for term in ("ledger", "payment", "financial transaction")):
            return {"stack": ["SQL", "Rust"], "reason": "transactional integrity plus memory-safe service"}
        if any(term in text for term in ("low latency", "embedded", "memory safe", "systems")):
            return {"stack": ["Rust"], "reason": "predictable performance and memory safety"}
        if any(term in text for term in ("data", "research", "analysis", "forecast", "prototype")):
            return {"stack": ["Python", "SQL"], "reason": "rapid evidence work with durable data authority"}
        if any(term in text for term in ("app", "application", "api", "service")):
            return {"stack": ["Python", "TypeScript", "SQL"],
                    "reason": "measured default for service, interface and persistence; benchmark before final choice"}
        return {"stack": [], "reason": "technology must be selected after requirements and measurements"}

    def evaluate(self, plan: Mapping[str, Any], *, register_learning: bool = False) -> dict[str, Any]:
        objective = str(plan.get("objective") or plan.get("goal") or plan.get("description") or "").strip()
        if not objective:
            return {"decision": "clarify", "reason": "missing_objective", "requirements": []}
        subject_ids = self.infer_subjects(objective, explicit=self._explicit_requirements(plan))
        requirements = []
        for subject_id in subject_ids:
            assessment = self.system.assess(subject_id)
            requirements.append({
                "subject_id": subject_id, "name": assessment["name"],
                "knowledge_level": assessment["knowledge_level"],
                "practical_level": assessment["practical_level"],
                "overall_level": assessment["overall_level"],
                "work_readiness": self.system.capability_query(assessment["name"]).get("work_readiness"),
                "target_level": assessment["target_level"],
                "missing_subskills": [skill for skill, counts in assessment["per_subskill"].items()
                                      if counts["total"] < 2],
            })
        if not requirements:
            decision = "clarify"
            reason = "no_grounded_capability_mapping"
        else:
            floor = min(LEVEL_INDEX[row["overall_level"]] for row in requirements)
            if floor >= LEVEL_INDEX["advanced"]:
                decision, reason = "execute", "all_required_capabilities_advanced_or_better"
            elif floor >= LEVEL_INDEX["intermediate"]:
                decision, reason = "execute_with_strong_verification", "bounded_competence_requires_outcome_checks"
            else:
                decision, reason = "learn_then_execute", "one_or_more_required_capabilities_below_intermediate"
        if register_learning and decision == "learn_then_execute":
            weakest = min(requirements, key=lambda row: (LEVEL_INDEX[row["overall_level"]], row["subject_id"]))
            self.system.prioritize_for_mission(
                subject_id=weakest["subject_id"], mission=objective,
                evidence=f"action_switch:{plan.get('goal_id') or plan.get('id') or 'unidentified_goal'}",
            )
        return {
            "decision": decision, "reason": reason, "objective": objective,
            "requirements": requirements, "technology_proposal": self._technology(objective),
            "action_contract": [
                "interpret_objective_and_define_success", "retrieve_relevant_verified_knowledge",
                "close_or_bound_capability_gaps", "select_tools_and_architecture_from_requirements",
                "decompose_dependencies", "execute_in_governed_environment",
                "verify_independent_outcome", "reflect_and_update_competency",
            ],
            "authority_boundary": "Competency controls readiness; execution outcomes control success.",
        }
