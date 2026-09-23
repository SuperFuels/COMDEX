"""Reusable operating methods for AION's canonical cognitive runtime.

The library does not execute work or authorize an action.  It selects and
composes evidence-backed ways of organising work so a new mission does not
have to rediscover prioritisation, dependency analysis, delivery control or
retrospection from scratch.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "aion.hexcore.executive_skills.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8")
    try:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno()); handle.close()
        os.replace(handle.name, path)
    except Exception:
        try:
            handle.close(); os.unlink(handle.name)
        except Exception:
            pass
        raise


@dataclass(frozen=True)
class ExecutiveSkill:
    skill_id: str
    name: str
    purpose: str
    outputs: tuple[str, ...]
    verification: tuple[str, ...]
    risk_tags: tuple[str, ...] = ()


SKILLS: tuple[ExecutiveSkill, ...] = (
    ExecutiveSkill("objective_framing", "Objective framing", "Define the real outcome, users, constraints and evidence of success.", ("success_contract", "scope", "non_goals"), ("owner_intent_preserved", "criteria_measurable")),
    ExecutiveSkill("stakeholder_authority", "Stakeholder and authority mapping", "Identify affected people, decision owners and approval boundaries.", ("stakeholder_map", "approval_points"), ("authority_not_assumed", "consent_points_present"), ("human_impact",)),
    ExecutiveSkill("backlog_invention", "Backlog invention", "Convert outcomes into independently verifiable work items.", ("backlog",), ("every_item_has_done_evidence",)),
    ExecutiveSkill("dependency_mapping", "Dependency and critical-path mapping", "Order work by prerequisites rather than presentation order.", ("dependency_graph", "critical_path"), ("acyclic_or_cycle_reported", "blocked_work_not_started")),
    ExecutiveSkill("value_prioritisation", "Value, urgency and learning prioritisation", "Rank eligible work using value, urgency, risk reduction, learning value and cost.", ("ranked_backlog", "priority_rationale"), ("dependencies_respected", "score_components_visible")),
    ExecutiveSkill("scrum_delivery", "Scrum delivery", "Use iterative product increments when feedback and a sustained backlog justify sprints.", ("increments", "review_cadence", "definition_of_done"), ("working_increment_each_cycle", "review_changes_backlog")),
    ExecutiveSkill("kanban_flow", "Kanban flow", "Control continuous work and work-in-progress when arrivals are irregular.", ("flow_board", "wip_limits"), ("blocked_age_visible", "wip_limit_respected")),
    ExecutiveSkill("incident_response", "Incident response", "Stabilise, diagnose, repair and learn from urgent service failures.", ("impact", "containment", "diagnosis", "recovery", "postmortem"), ("service_restored", "root_cause_evidenced"), ("production",)),
    ExecutiveSkill("scientific_method", "Scientific investigation", "Turn uncertainty into hypotheses, discriminating experiments and retained conclusions.", ("hypotheses", "experiment_plan", "prediction", "criticism"), ("commit_before_observe", "counterexample_attempted")),
    ExecutiveSkill("decision_analysis", "Decision analysis", "Compare reversible alternatives using evidence and explicit trade-offs.", ("alternatives", "criteria", "decision_record"), ("rejected_alternative_recorded", "uncertainty_visible")),
    ExecutiveSkill("risk_management", "Risk management", "Identify failure modes and reduce exposure before irreversible work.", ("risk_register", "mitigations", "contingencies"), ("high_risks_have_owner", "rollback_exists"), ("irreversible",)),
    ExecutiveSkill("quality_assurance", "Quality assurance", "Derive executable acceptance, regression, security and adversarial checks.", ("test_strategy", "acceptance_evidence"), ("negative_tests_present", "security_cannot_be_traded_for_function")),
    ExecutiveSkill("resource_planning", "Resource planning", "Allocate time, compute, money, tools and human attention within explicit limits.", ("resource_budget", "bottleneck_map"), ("budget_visible", "approval_for_expansion"), ("resource",)),
    ExecutiveSkill("progress_control", "Progress and exception control", "Compare actual progress with commitments and replan only affected work.", ("progress_receipt", "variance", "replan"), ("claims_tied_to_outcomes", "stale_work_marked")),
    ExecutiveSkill("retrospective", "Outcome retrospective", "Extract narrowly scoped lessons and changes to future practice.", ("outcome_grade", "failure_attribution", "lesson", "next_experiment"), ("lesson_scope_bounded", "evidence_linked")),
    ExecutiveSkill("handover", "Documentation and handover", "Preserve decisions, operation, provenance and unresolved work for another actor or restart.", ("decision_log", "runbook", "open_questions"), ("restart_reconstructable", "provenance_complete")),
)


METHODS: dict[str, tuple[str, ...]] = {
    "product_delivery": ("objective_framing", "stakeholder_authority", "backlog_invention", "dependency_mapping", "value_prioritisation", "scrum_delivery", "risk_management", "quality_assurance", "progress_control", "retrospective", "handover"),
    "research_investigation": ("objective_framing", "scientific_method", "dependency_mapping", "value_prioritisation", "resource_planning", "progress_control", "retrospective", "handover"),
    "operational_incident": ("stakeholder_authority", "incident_response", "risk_management", "quality_assurance", "progress_control", "retrospective", "handover"),
    "continuous_operations": ("objective_framing", "kanban_flow", "value_prioritisation", "risk_management", "resource_planning", "progress_control", "retrospective", "handover"),
    "strategic_decision": ("objective_framing", "stakeholder_authority", "decision_analysis", "scientific_method", "risk_management", "resource_planning", "handover"),
    "learning_apprenticeship": ("objective_framing", "backlog_invention", "dependency_mapping", "scientific_method", "value_prioritisation", "quality_assurance", "progress_control", "retrospective", "handover"),
    "bounded_task": ("objective_framing", "dependency_mapping", "value_prioritisation", "quality_assurance", "retrospective", "handover"),
}


CLASS_SIGNALS: dict[str, tuple[str, ...]] = {
    "operational_incident": ("incident", "outage", "broken", "failure", "restore", "urgent", "security breach"),
    "research_investigation": ("research", "investigate", "discover", "hypothesis", "experiment", "experiments", "analyse", "analyze", "study"),
    "learning_apprenticeship": ("learn", "master", "curriculum", "practice", "teach", "competence"),
    "strategic_decision": ("strategy", "choose", "compare", "decide", "viable", "investment", "market"),
    "continuous_operations": ("monitor", "operate", "maintain", "support", "ongoing", "queue"),
    "product_delivery": ("build", "create", "develop", "launch", "application", "app", "product", "website", "platform"),
}


class ExecutiveSkillsLibrary:
    """Selects a work system, composes skill contracts and learns reliability."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path
        self.skills = {item.skill_id: item for item in SKILLS}
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        baseline = {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "method_outcomes": {},
            "skill_outcomes": {},
            "compositions": [],
            "updated_at": None,
        }
        if self.state_path and self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                if raw.get("schema_version") == SCHEMA_VERSION:
                    baseline.update(raw)
            except Exception:
                pass
        return baseline

    def _save(self) -> None:
        if not self.state_path:
            return
        self.state["revision"] = int(self.state.get("revision", 0)) + 1
        self.state["updated_at"] = _now()
        _write(self.state_path, self.state)

    def select_method(self, objective: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        text = objective.lower()
        def present(phrase: str) -> bool:
            return re.search(r"(?<![a-z0-9_])" + re.escape(phrase) + r"(?![a-z0-9_])", text) is not None

        scores = {name: sum(1 for token in tokens if present(token)) for name, tokens in CLASS_SIGNALS.items()}
        context = context or {}
        family = str(context.get("objective_family") or "")
        policy_path = self.state_path.with_name("cognitive_route_champion.json") if self.state_path else None
        if family and policy_path and policy_path.exists():
            try:
                policy = json.loads(policy_path.read_text(encoding="utf-8"))
                mapping = policy.get("routes") or {}
                routed = mapping.get(family)
                if (policy.get("active_for_proposals") is True and routed in METHODS
                        and policy.get("authority") == "cau_provisional_pending_later_outcome"):
                    return {
                        "method": routed, "score": 1,
                        "alternatives": [name for name in METHODS if name != routed][:2],
                        "scrum_selected": routed == "product_delivery",
                        "reason": "verified_cognitive_route_champion",
                        "objective_family": family,
                        "policy_id": policy.get("policy_id"),
                    }
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        if context.get("production_failure"):
            scores["operational_incident"] += 4
        if context.get("continuous_arrivals"):
            scores["continuous_operations"] += 3
        if context.get("uncertainty_high"):
            scores["research_investigation"] += 2
        winner = max(scores, key=lambda key: (scores[key], key))
        if scores[winner] == 0:
            winner = "bounded_task"
        return {
            "method": winner,
            "score": scores.get(winner, 0),
            "alternatives": [name for name, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if name != winner][:2],
            "scrum_selected": winner == "product_delivery",
            "reason": "selected_from_objective_and_operating_context",
        }

    @staticmethod
    def priority_score(item: Mapping[str, Any]) -> float:
        value = max(0.0, float(item.get("value", 1.0)))
        urgency = max(0.0, float(item.get("urgency", 1.0)))
        risk_reduction = max(0.0, float(item.get("risk_reduction", 0.0)))
        learning = max(0.0, float(item.get("learning_value", 0.0)))
        cost = max(0.1, float(item.get("cost", 1.0)))
        confidence = min(1.0, max(0.0, float(item.get("confidence", 1.0))))
        return ((value * 0.45) + (urgency * 0.25) + (risk_reduction * 0.15) + (learning * 0.15)) * confidence / cost

    def rank_backlog(self, items: Iterable[Mapping[str, Any]], completed: Iterable[str] = ()) -> list[dict[str, Any]]:
        completed_set = {str(item) for item in completed}
        rows = []
        for raw in items:
            item = dict(raw)
            dependencies = [str(value) for value in item.get("dependencies") or []]
            ready = all(value in completed_set for value in dependencies)
            item["ready"] = ready
            item["blocked_by"] = [value for value in dependencies if value not in completed_set]
            item["priority_score"] = round(self.priority_score(item), 6) if ready else 0.0
            rows.append(item)
        return sorted(rows, key=lambda row: (not row["ready"], -row["priority_score"], str(row.get("task_id", ""))))

    def compose(self, objective: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        selection = self.select_method(objective, context)
        skill_ids = METHODS[selection["method"]]
        contracts = [asdict(self.skills[skill_id]) for skill_id in skill_ids]
        composition = {
            "schema_version": "aion.hexcore.executive_work_system.v1",
            "composition_id": f"worksys_{_hash([objective, selection, skill_ids])[:16]}",
            "objective_hash": _hash(objective),
            "method_selection": selection,
            "skills": contracts,
            "stage_order": list(skill_ids),
            "authority": "proposal_only",
            "created_at": _now(),
        }
        self.state.setdefault("compositions", []).append({
            "composition_id": composition["composition_id"],
            "objective_hash": composition["objective_hash"],
            "method": selection["method"],
            "created_at": composition["created_at"],
        })
        self.state["compositions"] = self.state["compositions"][-1000:]
        self._save()
        return composition

    def record_outcome(self, work_system: Mapping[str, Any], *, verified: bool, score: float) -> None:
        method = str((work_system.get("method_selection") or {}).get("method") or "unknown")
        row = self.state.setdefault("method_outcomes", {}).setdefault(method, {"attempts": 0, "verified": 0, "score_sum": 0.0})
        row["attempts"] += 1
        row["verified"] += int(verified)
        row["score_sum"] += float(score)
        for skill_id in work_system.get("stage_order") or []:
            skill = self.state.setdefault("skill_outcomes", {}).setdefault(str(skill_id), {"attempts": 0, "verified": 0})
            skill["attempts"] += 1; skill["verified"] += int(verified)
        self._save()

    def status(self) -> dict[str, Any]:
        return {
            "skills": len(self.skills),
            "methods": len(METHODS),
            "compositions": len(self.state.get("compositions") or []),
            "verified_method_outcomes": sum(row.get("verified", 0) for row in (self.state.get("method_outcomes") or {}).values()),
            "state_path": str(self.state_path) if self.state_path else None,
        }
