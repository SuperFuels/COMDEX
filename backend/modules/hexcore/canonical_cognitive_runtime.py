from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import math
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Protocol

from backend.modules.hexcore.governed_runtime import (
    AppendOnlyOutcomeLedger,
    HexCoreGovernedRuntime,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)
from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary
from backend.modules.hexcore.persistent_executive_self import PersistentExecutiveSelf


SCHEMA_VERSION = "aion.hexcore.canonical_cognitive_runtime.v1"
STAGES = (
    "goal",
    "investigate",
    "learn",
    "plan",
    "metacognitive_review",
    "commit_action",
    "act",
    "await_outcome",
    "observe",
    "criticise",
    "post_action_reflection",
    "improve",
    "retain",
    "complete",
)
TERMINAL_STATES = {"completed", "failed", "blocked", "cancelled"}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    """Conservative competence estimate; a single lucky success cannot imply mastery."""
    if total <= 0:
        return 0.0
    proportion = successes / total
    denominator = 1.0 + (z * z / total)
    centre = proportion + (z * z / (2.0 * total))
    margin = z * math.sqrt(
        (proportion * (1.0 - proportion) / total)
        + (z * z / (4.0 * total * total))
    )
    return max(0.0, (centre - margin) / denominator)


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
        encoding="utf-8",
    )
    try:
        json.dump(_json_safe(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        json.loads(Path(handle.name).read_text(encoding="utf-8"))
        os.replace(handle.name, path)
    except Exception:
        try:
            handle.close()
        except Exception:
            pass
        try:
            os.unlink(handle.name)
        except Exception:
            pass
        raise


def _normalise_goal(raw: Mapping[str, Any]) -> Dict[str, Any]:
    goal = dict(raw)
    goal_id = str(goal.get("goal_id") or goal.get("id") or goal.get("name") or "").strip()
    name = str(goal.get("goal_name") or goal.get("name") or goal.get("title") or goal_id).strip()
    objective = str(goal.get("objective") or goal.get("description") or name).strip()
    if not goal_id or not objective:
        raise ValueError("goal requires an id/name and objective")
    return {
        **_json_safe(goal),
        "goal_id": goal_id,
        "goal_name": name or goal_id,
        "objective": objective,
        "priority": float(goal.get("priority") or 0.0),
        "risk_tier": str(goal.get("risk_tier") or "low"),
        "approval_policy": str(goal.get("approval_policy") or "dry_run_only"),
        "status": str(goal.get("status") or "active"),
    }


class CognitiveAdapter(Protocol):
    """Replaceable proposal/action surface. HexCore remains the authority shell."""

    def investigate(self, goal: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def learn_context(self, goal: Mapping[str, Any], investigation: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def plan(
        self,
        goal: Mapping[str, Any],
        investigation: Mapping[str, Any],
        learned_context: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def act(self, action: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def observe(self, action_result: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def criticise(self, cycle: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def improve(self, cycle: Mapping[str, Any], criticism: Mapping[str, Any]) -> Mapping[str, Any]: ...


class NativeAionCognitiveAdapter:
    """
    Lazy bridge to the existing AION cognition stack.

    Tessaris/Theta propose investigation and planning. HexCore performs the
    governed cognitive action only for goals explicitly marked
    ``autonomous_allowed``. Other goals remain proposal-only.
    """

    def __init__(self) -> None:
        self._thinking_loop = None
        self._hexcore = None
        self._native_router = None
        self._native_composer = None
        self._governed_legacy_stack = None

    def _legacy_stack(self):
        if self._governed_legacy_stack is None:
            from backend.modules.hexcore.governed_cognitive_stack import GovernedCognitiveStack
            self._governed_legacy_stack = GovernedCognitiveStack()
        return self._governed_legacy_stack

    def _route(self, text: str) -> Mapping[str, Any]:
        if self._native_router is False:
            return {"status": "unavailable", "proposal_only": True}
        if self._native_router is None:
            weights = Path("backend/modules/hexcore/data/verified_native_router/router.npz")
            encoder = Path("backend/models/all-MiniLM-L6-v2")
            if not weights.exists() or not encoder.exists():
                self._native_router = False
                return {"status": "unavailable", "proposal_only": True}
            try:
                from backend.modules.hexcore.verified_cross_domain_native_router import NativeRouterProposalEngine
                self._native_router = NativeRouterProposalEngine(encoder_path=encoder, weights_path=weights)
            except Exception as error:
                self._native_router = False
                return {"status": "unavailable", "reason": type(error).__name__, "proposal_only": True}
        return self._native_router.propose(text)

    def _compose(self, text: str) -> Mapping[str, Any]:
        if self._native_composer is False:
            return {"status": "unavailable", "proposal_only": True}
        if self._native_composer is None:
            weights = Path("backend/modules/hexcore/data/native_composition/router_v2.npz")
            encoder = Path("backend/models/all-MiniLM-L6-v2")
            if not weights.exists() or not encoder.exists():
                self._native_composer = False
                return {"status": "unavailable", "proposal_only": True}
            try:
                from backend.modules.hexcore.continual_native_cognitive_composition import NativeCompositionProposalEngine
                self._native_composer = NativeCompositionProposalEngine(encoder_path=encoder, weights_path=weights)
            except Exception as error:
                self._native_composer = False
                return {"status": "unavailable", "reason": type(error).__name__, "proposal_only": True}
        return self._native_composer.propose(text)

    def _theta(self):
        if self._thinking_loop is None:
            from backend.modules.aion_thinking.theta_orchestrator import ThinkingLoop

            self._thinking_loop = ThinkingLoop(
                namespace="canonical_cognitive_runtime",
                auto_tick=False,
            )
        return self._thinking_loop

    def _core(self):
        if self._hexcore is None:
            from backend.modules.hexcore.hexcore import HexCore

            self._hexcore = HexCore()
        return self._hexcore

    @staticmethod
    def _lightweight_specialist_goal(goal: Mapping[str, Any]) -> bool:
        return (
            goal.get("origin") == "procedure_autonomous_capability_research_executive_v1"
            and goal.get("authority_scope") == "read_only_or_private_workspace"
            and goal.get("lane") in {"useful_work", "capability_practice", "cognitive_research"}
        )

    def investigate(self, goal: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        if self._lightweight_specialist_goal(goal):
            lane = str(goal["lane"])
            specialist = {
                "useful_work": "open_useful_objective_acquisition",
                "capability_practice": "progressive_competency_service",
                "cognitive_research": "private_cognitive_research_lab",
            }[lane]
            return {
                "proposal": {"status": "specialist_dispatch", "specialist": specialist},
                "native_specialist_route": {"status": "deterministic_verified_route", "specialist": specialist},
                "native_composition_proposal": {"status": "single_specialist_contract", "lane": lane},
                "recalled_knowledge": list(context.get("recalled_knowledge") or []),
                "unresolved_questions": ["await independently verified specialist outcome"],
                "governed_legacy_deliberation": {
                    "capability": {"decision": "delegate_to_governed_specialist"},
                    "plan": {"dispatcher": specialist, "ambient_authority_expansion": False},
                },
                "resource_policy": "lightweight_no_neural_initialisation",
                "proposal_only": True,
            }
        prompt = (
            "Investigate what is known, uncertain, disputed, and missing for this goal: "
            f"{goal['objective']}"
        )
        proposal = self._theta().think(prompt)
        governed_deliberation = self._legacy_stack().deliberate(
            {
                **dict(goal),
                "evidence_refs": list(context.get("recalled_knowledge") or []),
                "decision_history": list(context.get("decision_history") or []),
            },
            register_learning=False,
        )
        return {
            "proposal": _json_safe(proposal),
            "native_specialist_route": _json_safe(self._route(str(goal["objective"]))),
            "native_composition_proposal": _json_safe(self._compose(str(goal["objective"]))),
            "recalled_knowledge": list(context.get("recalled_knowledge") or []),
            "unresolved_questions": list(goal.get("unresolved_questions") or []),
            "governed_legacy_deliberation": _json_safe(governed_deliberation),
            "proposal_only": True,
        }

    def learn_context(self, goal: Mapping[str, Any], investigation: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "goal_id": goal["goal_id"],
            "evidence_count": len(investigation.get("recalled_knowledge") or []),
            "candidate_context_hash": _canonical_hash(investigation),
            "knowledge_committed": False,
            "reason": "proposal_context_requires_verified_outcome",
        }

    def plan(
        self,
        goal: Mapping[str, Any],
        investigation: Mapping[str, Any],
        learned_context: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if self._lightweight_specialist_goal(goal):
            specialist = ((investigation.get("native_specialist_route") or {}).get("specialist"))
            return {
                "proposal": {"status": "delegate_existing_specialist", "specialist": specialist},
                "native_specialist_route": _json_safe(investigation.get("native_specialist_route")),
                "native_composition_proposal": _json_safe(investigation.get("native_composition_proposal")),
                "actions": [{
                    "action_id": f"action:{goal['goal_id']}:1",
                    "type": "governed_specialist_dispatch",
                    "description": goal["objective"],
                    "specialist": specialist,
                    "risk_tier": "low", "requires_consent": False,
                    "consent_granted": True, "executable": False,
                    "capability_decision": "specialist_service_already_authoritative",
                    "verification_plan": ["independent specialist outcome receipt"],
                }],
                "governed_legacy_plan": {"dispatcher": specialist},
                "resource_policy": "lightweight_no_neural_initialisation",
                "proposal_only": True,
            }
        prompt = (
            "Construct a bounded, verifiable plan for this objective. Identify the next "
            f"information or execution action and its success evidence: {goal['objective']}"
        )
        proposal = self._theta().deep_resonance_loop(prompt)
        legacy = dict(investigation.get("governed_legacy_deliberation") or {})
        capability = dict(legacy.get("capability") or {})
        capability_ready = capability.get("decision") in {
            "execute", "execute_with_strong_verification"
        }
        autonomous = goal.get("approval_policy") == "autonomous_allowed"
        return {
            "proposal": _json_safe(proposal),
            "native_specialist_route": _json_safe(investigation.get("native_specialist_route")),
            "native_composition_proposal": _json_safe(investigation.get("native_composition_proposal")),
            "actions": [
                {
                    "action_id": f"action:{goal['goal_id']}:1",
                    "type": "hexcore_cognitive_cycle",
                    "description": goal["objective"],
                    "risk_tier": goal.get("risk_tier", "low"),
                    "requires_consent": goal.get("approval_policy") == "human_approval_required",
                    "consent_granted": bool(goal.get("consent_granted") is True),
                    "executable": autonomous and capability_ready,
                    "capability_decision": capability.get("decision"),
                    "verification_plan": list(goal.get("success_criteria") or []),
                }
            ],
            "governed_legacy_plan": _json_safe(legacy.get("plan") or {}),
            "proposal_only": not (autonomous and capability_ready),
        }

    def act(self, action: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        if action.get("executable") is not True:
            return {
                "status": "proposal_only",
                "verified": False,
                "action_id": action.get("action_id"),
                "reason": "goal_not_authorized_for_autonomous_execution",
            }
        decision, entry = asyncio.run(self._core().run_loop(str(action.get("description") or "")))
        governance = dict(entry.get("action_governance") or {})
        return {
            "status": "executed" if governance.get("allowed") else "denied",
            "verified": False,
            "decision": _json_safe(decision),
            "hexcore_entry": _json_safe(entry),
            "action_governance": governance,
            "reason": "external_success_evidence_required",
        }

    def observe(self, action_result: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "status": action_result.get("status", "unknown"),
            "verified": bool(action_result.get("verified") is True),
            "score": float(action_result.get("score") or 0.0),
            "evidence": list(action_result.get("evidence") or []),
            "result_hash": _canonical_hash(action_result),
        }

    def criticise(self, cycle: Mapping[str, Any]) -> Mapping[str, Any]:
        observation = dict(cycle.get("observation") or {})
        result = dict(cycle.get("action_result") or {})
        if result.get("status") == "denied":
            failure_type = "authority"
        elif result.get("status") == "proposal_only":
            failure_type = "awaiting_authority"
        elif result.get("error"):
            failure_type = "execution"
        elif observation.get("verified") is not True:
            failure_type = "verification"
        elif float(observation.get("score") or 0.0) < 1.0:
            failure_type = "outcome"
        else:
            failure_type = "none"
        return {
            "failure_type": failure_type,
            "needs_improvement": failure_type not in {"none", "awaiting_authority"},
            "verified_success": failure_type == "none",
        }

    def improve(self, cycle: Mapping[str, Any], criticism: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "candidate": None,
            "reason": (
                "no_private_challenger_without_verified_failure_and_evaluator"
                if criticism.get("needs_improvement")
                else "no_improvement_required"
            ),
        }


@dataclass
class RuntimePaths:
    state: Path
    learning: Path
    ledger: Path

    @classmethod
    def defaults(cls) -> "RuntimePaths":
        root = Path(os.getenv("DATA_ROOT", "data")) / "aion" / "canonical_runtime"
        return cls(
            state=root / "state.json",
            learning=root / "persistent_learning.json",
            ledger=root / "outcomes.jsonl",
        )


class CanonicalAionCognitiveRuntime:
    """One restart-persistent scheduler for AION's existing cognitive layers."""

    def __init__(
        self,
        *,
        paths: Optional[RuntimePaths] = None,
        adapter: Optional[CognitiveAdapter] = None,
        goal_provider: Optional[Callable[[], Iterable[Mapping[str, Any]]]] = None,
        goal_completion: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
        authority_provider: Optional[Callable[[str], Mapping[str, Any]]] = None,
        recall_provider: Optional[Callable[[str], Mapping[str, Any]]] = None,
        memory_writer: Optional[Callable[[str, str, Mapping[str, float], Mapping[str, Any]], bool]] = None,
        wake_interval_seconds: float = 60.0,
    ) -> None:
        self.paths = paths or RuntimePaths.defaults()
        self.adapter = adapter or NativeAionCognitiveAdapter()
        self.goal_provider = goal_provider or self._active_goal_engine_goals
        self.goal_completion = goal_completion or self._complete_goal_engine_goal
        self.wake_interval_seconds = max(0.05, float(wake_interval_seconds))
        self.ledger = AppendOnlyOutcomeLedger(self.paths.ledger)
        self.governed = HexCoreGovernedRuntime(
            authority_provider=authority_provider,
            recall_provider=recall_provider,
            memory_writer=memory_writer,
            outcome_ledger=self.ledger,
            learning_state_path=self.paths.learning,
        )
        self.learning = HexCorePersistentLearningRuntime(
            state_path=self.paths.learning,
            authority_provider=authority_provider,
        )
        self.executive_skills = ExecutiveSkillsLibrary(
            self.paths.state.with_name("executive_skills.json")
        )
        self.executive_self = PersistentExecutiveSelf(
            self.paths.state.with_name("executive_self.json")
        )
        self.state = self._load_state()
        if self.paths.state.resolve() == RuntimePaths.defaults().state.resolve():
            registry_path = Path(
                os.getenv(
                    "AION_NORTH_STAR_REGISTRY",
                    "results/hexcore_constitutional_north_star_mastery_registry.json",
                )
            )
            if registry_path.exists():
                try:
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    if (
                        registry.get("passed") is True
                        and registry.get("purpose_mutable") is False
                        and registry.get("constitutional_purpose")
                    ):
                        self.executive_self.register_commitment(
                            {
                                "commitment_id": "constitutional:north_star",
                                "objective": registry["constitutional_purpose"],
                                "priority": 10.0,
                                "strategic_alignment": 1.0,
                                "authority": "immutable_constitutional_registry",
                            }
                        )
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
        for mission in (self.state.get("authorized_missions") or {}).values():
            if mission.get("mission_id") and mission.get("objective"):
                self.executive_self.register_commitment(
                    {
                        "commitment_id": mission["mission_id"],
                        "objective": mission["objective"],
                        "priority": mission.get("priority", 1.0),
                        "authority": "owner_authorized",
                    }
                )
        from backend.modules.hexcore.metacognitive_control import MetacognitiveController
        self.metacognition = MetacognitiveController()
        self._stop_requested = False

    @staticmethod
    def _active_goal_engine_goals() -> Iterable[Mapping[str, Any]]:
        from backend.modules.skills.goal_engine import GOALS

        # Goals may be published by persistent autonomous executives in other
        # supervised processes.  Refresh the disk-backed queue on every wake so
        # the canonical runtime does not remain idle with a stale import-time
        # snapshot.
        GOALS.load_goals()
        return GOALS.get_active_goals()

    @staticmethod
    def _complete_goal_engine_goal(goal_id: str, outcome: Mapping[str, Any]) -> None:
        if outcome.get("verified") is not True:
            return
        from backend.modules.skills.goal_engine import GOALS

        GOALS.mark_complete(goal_id, canonical_runtime_outcome=_json_safe(outcome))

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "created_at": _utc_timestamp(),
            "updated_at": None,
            "status": "idle",
            "active_cycle": None,
            "completed_cycles": [],
            "mission_goals": [],
            "authorized_missions": {},
            "capability_map": {},
            "curriculum_history": [],
            "outcome_receipts": [],
            "failure_queues": {},
            "private_challengers": [],
            "metacognitive_history": [],
            "open_specialist_contracts": {},
            "diagnostic_experiments": [],
            "pending_outcomes": {},
            "goal_runtime": {},
            "next_wake_at": None,
            "last_heartbeat_at": None,
            "last_error": None,
        }

    def _load_state(self) -> Dict[str, Any]:
        if not self.paths.state.exists():
            return self._empty_state()
        try:
            raw = json.loads(self.paths.state.read_text(encoding="utf-8"))
        except Exception:
            return self._empty_state()
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            return self._empty_state()
        state = self._empty_state()
        state.update(raw)
        return state

    def _checkpoint(self, *, event: str) -> str:
        self.state["revision"] = int(self.state.get("revision") or 0) + 1
        self.state["updated_at"] = _utc_timestamp()
        self.state["last_event"] = event
        _atomic_json_write(self.paths.state, self.state)
        return self.ledger.append(
            {
                "schema_version": "aion.hexcore.canonical_runtime_event.v1",
                "timestamp": self.state["updated_at"],
                "event": event,
                "revision": self.state["revision"],
                "cycle_id": (self.state.get("active_cycle") or {}).get("cycle_id"),
                "state_hash": _canonical_hash(self.state),
            }
        )

    def enqueue_goal(self, goal: Mapping[str, Any]) -> Dict[str, Any]:
        normalized = _normalise_goal(goal)
        existing = {
            str(item.get("goal_id"))
            for item in self.state.get("mission_goals") or []
            if isinstance(item, Mapping)
        }
        if normalized["goal_id"] not in existing:
            self.state.setdefault("mission_goals", []).append(normalized)
            self._checkpoint(event=f"goal_enqueued:{normalized['goal_id']}")
        return normalized

    def authorize_mission(self, mission: Mapping[str, Any]) -> Dict[str, Any]:
        """Persist an owner mission and its bounded capability requirements.

        Generated learning goals may serve this mission, but can never alter its
        terminal objective, action policy, budget, or accepted authorities.
        """
        mission_id = str(mission.get("mission_id") or mission.get("id") or "").strip()
        objective = str(mission.get("objective") or "").strip()
        requirements = list(mission.get("capability_requirements") or [])
        if not mission_id or not objective or not requirements:
            raise ValueError("mission requires mission_id, objective and capability_requirements")
        normalized_requirements = []
        for raw in requirements:
            if not isinstance(raw, Mapping):
                raise ValueError("capability requirement must be a mapping")
            capability = str(raw.get("capability") or "").strip()
            tasks = [_json_safe(item) for item in raw.get("tasks") or []]
            if not capability or not tasks:
                raise ValueError("each capability requires a name and evaluator-owned tasks")
            normalized_requirements.append(
                {
                    "capability": capability,
                    "target_score": float(raw.get("target_score", 0.8)),
                    "minimum_verified_outcomes": max(
                        1, int(raw.get("minimum_verified_outcomes", 2))
                    ),
                    "minimum_transfer_outcomes": max(
                        0, int(raw.get("minimum_transfer_outcomes", 1))
                    ),
                    "minimum_authorities": max(1, int(raw.get("minimum_authorities", 1))),
                    "dependencies": [str(item) for item in raw.get("dependencies") or []],
                    "tasks": tasks,
                }
            )
        envelope = {
            "mission_id": mission_id,
            "objective": objective,
            "objective_hash": _canonical_hash(objective),
            "authorized_at": _utc_timestamp(),
            "status": "active",
            "priority": float(mission.get("priority", 1.0)),
            "approval_policy": str(mission.get("approval_policy") or "autonomous_allowed"),
            "action_budget": max(1, int(mission.get("action_budget", 100))),
            "actions_used": 0,
            "allowed_authorities": sorted(
                {str(item) for item in mission.get("allowed_authorities") or []}
            ),
            "capability_requirements": normalized_requirements,
        }
        existing = (self.state.get("authorized_missions") or {}).get(mission_id)
        if isinstance(existing, Mapping):
            if existing.get("objective_hash") != envelope["objective_hash"]:
                raise ValueError("an authorized mission objective is immutable")
            return dict(existing)
        self.state.setdefault("authorized_missions", {})[mission_id] = envelope
        self.executive_self.register_commitment(
            {
                "commitment_id": mission_id,
                "objective": objective,
                "priority": envelope["priority"],
                "authority": "owner_authorized",
                "strategic_alignment": 1.0,
            }
        )
        self._checkpoint(event=f"mission_authorized:{mission_id}")
        self._register_progressive_competency_gap(envelope)
        self.refresh_curriculum(mission_id)
        return envelope

    def _register_progressive_competency_gap(self, mission: Mapping[str, Any]) -> None:
        """Bind the first unsatisfied mission capability to the live curriculum.

        This only runs for the canonical persistent runtime. Custom/test
        runtimes remain isolated. The competency system decides levels; mission
        authorization merely supplies evidence that a capability is required.
        """
        if self.paths.state.resolve() != RuntimePaths.defaults().state.resolve():
            return
        requirements = list(mission.get("capability_requirements") or [])
        if not requirements:
            return
        try:
            from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem

            repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
            system = ProgressiveCompetencySystem(
                repo_root=repo_root,
                state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
            )
            requirement = requirements[0]
            capability = str(requirement.get("capability") or "").strip()
            normalized = "".join(char for char in capability.lower() if char.isalnum())
            match = next((subject_id for subject_id, subject in system.state["subjects"].items()
                          if normalized in {
                              "".join(char for char in subject_id.lower() if char.isalnum()),
                              "".join(char for char in str(subject.get("name", "")).lower() if char.isalnum()),
                          }), None)
            if match:
                system.set_active_subject(match)
            else:
                task_tokens = []
                for task in requirement.get("tasks") or []:
                    if isinstance(task, Mapping):
                        token = task.get("subskill") or task.get("skill") or task.get("task_id") or task.get("id")
                        if token:
                            task_tokens.append(str(token))
                subskills = task_tokens or [
                    "domain_foundations", "authoritative_sources", "practical_application",
                    "failure_recovery", "cross_domain_transfer",
                ]
                system.register_mission_gap(
                    mission=str(mission.get("objective") or capability),
                    subject_name=capability, group="mission_domain",
                    proposed_subskills=subskills,
                    evidence=f"authorized_mission:{mission.get('mission_id')}",
                )
            status_path = repo_root / "results/aion_progressive_competency_status.json"
            _atomic_json_write(status_path, system.snapshot())
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            # Curriculum binding is fail-closed and cannot invalidate the
            # already authorized mission. The service will surface the gap.
            return

    def compile_and_authorize_mastery_mission(
        self,
        *,
        mission_id: str,
        objective: str,
        allowed_authorities: Iterable[str],
        action_budget: int = 100,
        authorize: bool = False,
    ) -> Dict[str, Any]:
        """Invent a capability graph from broad owner intent.

        Compilation is proposal-only by default.  ``authorize=True`` is an
        explicit owner/runtime boundary; the compiler cannot authorize its own
        terminal goal.
        """
        from backend.modules.hexcore.autonomous_mastery_runtime import (
            OpenCapabilityGraphInventor,
        )

        induction = OpenCapabilityGraphInventor().invent(
            mission_id=mission_id,
            objective=objective,
            authorities=list(allowed_authorities),
            action_budget=action_budget,
        )
        if induction.get("status") != "invented" or not authorize:
            return _json_safe({**induction, "authorized": False})
        envelope = self.authorize_mission(induction["mission_envelope"])
        self.state.setdefault("open_specialist_contracts", {})[
            mission_id
        ] = _json_safe({
            "objective_hash": induction["objective_hash"],
            "graph_hash": induction["graph_hash"],
            "contracts": induction["specialist_contracts"],
            "authorized_at": _utc_timestamp(),
        })
        self._checkpoint(event=f"open_mastery_mission_authorized:{mission_id}")
        return _json_safe({
            **induction,
            "authorized": True,
            "authorized_envelope": envelope,
        })

    def _capability_record(self, mission_id: str, capability: str) -> Dict[str, Any]:
        key = f"{mission_id}:{capability}"
        record = self.state.setdefault("capability_map", {}).setdefault(
            key,
            {
                "mission_id": mission_id,
                "capability": capability,
                "attempts": 0,
                "verified_successes": 0,
                "transfer_successes": 0,
                "authorities": [],
                "outcome_ids": [],
                "mean_score": 0.0,
                "lower_confidence_bound": 0.0,
                "mastered": False,
            },
        )
        return record

    @staticmethod
    def _requirement_mastered(record: Mapping[str, Any], requirement: Mapping[str, Any]) -> bool:
        return bool(
            int(record.get("verified_successes") or 0)
            >= int(requirement.get("minimum_verified_outcomes") or 1)
            and int(record.get("transfer_successes") or 0)
            >= int(requirement.get("minimum_transfer_outcomes") or 0)
            and len(record.get("authorities") or [])
            >= int(requirement.get("minimum_authorities") or 1)
            and float(record.get("mean_score") or 0.0)
            >= float(requirement.get("target_score") or 0.0)
        )

    def refresh_curriculum(self, mission_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generate exactly one mission-bound learning goal from the weakest gap."""
        missions = self.state.get("authorized_missions") or {}
        candidates = [
            item for key, item in missions.items()
            if (mission_id is None or key == mission_id) and item.get("status") == "active"
        ]
        candidates.sort(key=lambda item: (-float(item.get("priority") or 0.0), item["mission_id"]))
        for mission in candidates:
            if int(mission.get("actions_used") or 0) >= int(mission.get("action_budget") or 0):
                mission["status"] = "budget_exhausted"
                continue
            requirements = {
                row["capability"]: row for row in mission["capability_requirements"]
            }
            gaps = []
            for capability, requirement in requirements.items():
                record = self._capability_record(mission["mission_id"], capability)
                mastered = self._requirement_mastered(record, requirement)
                record["mastered"] = mastered
                dependencies_ready = all(
                    self._capability_record(mission["mission_id"], dependency).get("mastered")
                    for dependency in requirement.get("dependencies") or []
                )
                if not mastered and dependencies_ready:
                    gaps.append((float(record.get("lower_confidence_bound") or 0.0), capability, requirement, record))
            if not gaps:
                if all(
                    self._capability_record(mission["mission_id"], name).get("mastered")
                    for name in requirements
                ):
                    mission["status"] = "capability_complete"
                    self._checkpoint(event=f"mission_capability_complete:{mission['mission_id']}")
                continue
            _, capability, requirement, record = min(gaps, key=lambda row: (row[0], row[1]))
            attempted = set(record.get("outcome_ids") or [])
            task = next(
                (
                    item for item in requirement["tasks"]
                    if str(item.get("task_id") or _canonical_hash(item)) not in attempted
                ),
                None,
            )
            if task is None:
                mission["status"] = "needs_new_tasks"
                self._checkpoint(event=f"curriculum_exhausted:{mission['mission_id']}:{capability}")
                continue
            task_id = str(task.get("task_id") or _canonical_hash(task))
            goal_id = f"learn:{mission['mission_id']}:{capability}:{task_id}"
            goal = {
                "goal_id": goal_id,
                "goal_name": f"Learn {capability}",
                "objective": (
                    f"Acquire and demonstrate {capability} because it blocks the authorized "
                    f"mission: {mission['objective']}"
                ),
                "priority": float(mission.get("priority") or 1.0) + 0.1,
                "risk_tier": str(task.get("risk_tier") or "low"),
                "approval_policy": mission["approval_policy"],
                "status": "active",
                "parent_mission_id": mission["mission_id"],
                "parent_objective_hash": mission["objective_hash"],
                "self_generated_subgoal": True,
                "capability": capability,
                "mastery_task": task,
                "derivation": {
                    "reason": "lowest_confidence_unmet_capability",
                    "lower_confidence_bound": record.get("lower_confidence_bound", 0.0),
                    "dependencies": requirement.get("dependencies", []),
                },
            }
            self.enqueue_goal(goal)
            mission["actions_used"] = int(mission.get("actions_used") or 0) + 1
            self.state.setdefault("curriculum_history", []).append(
                {
                    "timestamp": _utc_timestamp(),
                    "mission_id": mission["mission_id"],
                    "capability": capability,
                    "task_id": task_id,
                    "goal_id": goal_id,
                    "reason": goal["derivation"],
                }
            )
            self._checkpoint(event=f"curriculum_goal_generated:{goal_id}")
            return goal
        return None

    def _record_mastery_outcome(self, cycle: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        goal = dict(cycle.get("goal") or {})
        mission_id = str(goal.get("parent_mission_id") or "")
        capability = str(goal.get("capability") or "")
        task = dict(goal.get("mastery_task") or {})
        if not mission_id or not capability or not task:
            return None
        observation = dict(cycle.get("observation") or {})
        task_id = str(task.get("task_id") or _canonical_hash(task))
        authority = str(observation.get("authority") or observation.get("verifier") or "")
        mission = (self.state.get("authorized_missions") or {}).get(mission_id) or {}
        allowed = set(mission.get("allowed_authorities") or [])
        authority_allowed = bool(authority and (not allowed or authority in allowed))
        verified = bool(observation.get("verified") is True and authority_allowed)
        score = float(observation.get("score") or 0.0) if verified else 0.0
        receipt = {
            "receipt_id": f"receipt_{_canonical_hash([cycle.get('cycle_id'), observation])[:16]}",
            "cycle_id": cycle.get("cycle_id"),
            "mission_id": mission_id,
            "capability": capability,
            "task_id": task_id,
            "cohort": str(task.get("cohort") or "development"),
            "authority": authority,
            "authority_allowed": authority_allowed,
            "verified": verified,
            "score": score,
            "evidence_hash": _canonical_hash(observation.get("evidence") or []),
            "received_at": _utc_timestamp(),
        }
        self.state.setdefault("outcome_receipts", []).append(receipt)
        record = self._capability_record(mission_id, capability)
        prior_attempts = int(record.get("attempts") or 0)
        record["attempts"] = prior_attempts + 1
        record["verified_successes"] = int(record.get("verified_successes") or 0) + int(verified)
        record["transfer_successes"] = int(record.get("transfer_successes") or 0) + int(
            verified and receipt["cohort"] == "transfer"
        )
        if authority_allowed and authority:
            record["authorities"] = sorted(set(record.get("authorities") or []) | {authority})
        record["outcome_ids"] = list(record.get("outcome_ids") or []) + [task_id]
        old_total = float(record.get("mean_score") or 0.0) * prior_attempts
        record["mean_score"] = (old_total + score) / record["attempts"]
        record["lower_confidence_bound"] = _wilson_lower_bound(
            int(record["verified_successes"]), int(record["attempts"])
        )
        requirement = next(
            row for row in mission.get("capability_requirements") or []
            if row.get("capability") == capability
        )
        record["mastered"] = self._requirement_mastered(record, requirement)
        return receipt

    def _eligible_goals(self) -> list[Dict[str, Any]]:
        rows = list(self.state.get("mission_goals") or []) + list(self.goal_provider() or [])
        completed = {
            str(item.get("goal_id"))
            for item in self.state.get("completed_cycles") or []
            if isinstance(item, Mapping) and item.get("verified") is True
        }
        unique: Dict[str, Dict[str, Any]] = {}
        for raw in rows:
            try:
                goal = _normalise_goal(raw)
            except (TypeError, ValueError):
                continue
            if goal["status"] not in {"active", "pending", "draft"}:
                continue
            if goal["goal_id"] in completed:
                continue
            runtime_state = dict(
                (self.state.get("goal_runtime") or {}).get(goal["goal_id"]) or {}
            )
            if float(runtime_state.get("next_eligible_at") or 0.0) > time.time():
                continue
            current = unique.get(goal["goal_id"])
            if current is None or goal["priority"] > current["priority"]:
                unique[goal["goal_id"]] = goal
        return sorted(unique.values(), key=lambda item: (-item["priority"], item["goal_id"]))

    def _executive_capability_context(self) -> Dict[str, Dict[str, Any]]:
        """Merge runtime and academy gaps for portfolio-level reflection."""
        merged = {
            str(key): dict(value)
            for key, value in (self.state.get("capability_map") or {}).items()
            if isinstance(value, Mapping)
        }
        academy_path = Path(
            os.getenv(
                "AION_GUIDED_ACADEMY_STATE",
                "backend/modules/hexcore/data/guided_foundation_academy/state.json",
            )
        )
        if academy_path.exists():
            try:
                academy = json.loads(academy_path.read_text(encoding="utf-8"))
                for module_id, row in (academy.get("modules") or {}).items():
                    status = str(row.get("status") or "unknown")
                    merged[f"academy:{module_id}"] = {
                        "capability": row.get("name") or module_id,
                        "mastered": status == "passed_bounded",
                        "status": status,
                        "strategic_priority": (
                            10.0 if status in {"executor_required", "remediation_required", "learning"}
                            else 8.0 if status == "ready"
                            else 1.0
                        ),
                    }
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        return merged

    def _start_cycle(self) -> Optional[Dict[str, Any]]:
        goals = self._eligible_goals()
        if not goals:
            self.refresh_curriculum()
            goals = self._eligible_goals()
        executive_attention = self.executive_self.wake(
            goals=goals,
            authorized_missions=self.state.get("authorized_missions") or {},
            capability_map=self._executive_capability_context(),
            recent_failures=self.state.get("failure_queues") or {},
        )
        self.state["executive_attention"] = _json_safe(executive_attention)
        if not goals:
            self.state["status"] = "idle"
            self.state["next_wake_at"] = time.time() + self.wake_interval_seconds
            self._checkpoint(event="heartbeat_idle")
            return None
        goal = goals[0]
        # In the live canonical runtime, let the verified situation appraisal
        # choose among already-authorized goals.  It cannot create a goal or
        # widen authority; it only changes attention within the eligible set.
        if self.paths.state.resolve() == RuntimePaths.defaults().state.resolve():
            situation_path = Path(os.getenv(
                "AION_SITUATIONAL_EXECUTIVE_RESULT",
                "results/hexcore_situational_executive_driver.json",
            ))
            try:
                situated = json.loads(situation_path.read_text(encoding="utf-8"))
                driver = ((situated.get("situation") or {}).get("current_driver") or {})
                driver_terms = {
                    token for token in re.findall(r"[a-z0-9]+", (
                        str(driver.get("need_id") or "") + " " + str(driver.get("summary") or "")
                    ).lower()) if len(token) > 3
                }
                ranked = []
                for candidate_goal in goals:
                    objective_terms = set(re.findall(
                        r"[a-z0-9]+", str(candidate_goal.get("objective") or "").lower()
                    ))
                    relevance = len(driver_terms & objective_terms)
                    ranked.append((relevance, float(candidate_goal.get("priority") or 0.0),
                                   candidate_goal["goal_id"], candidate_goal))
                if ranked and max(row[0] for row in ranked) > 0:
                    goal = max(ranked, key=lambda row: (row[0], row[1], row[2]))[3]
                    self.state["situational_selection"] = {
                        "situation_hash": (situated.get("situation") or {}).get("situation_hash"),
                        "driver": driver, "selected_goal_id": goal["goal_id"],
                        "eligible_goal_count": len(goals), "authority_expanded": False,
                    }
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        cycle = {
            "schema_version": "aion.hexcore.cognitive_cycle.v1",
            "cycle_id": f"cycle_{uuid.uuid4().hex[:16]}",
            "goal_id": goal["goal_id"],
            "goal": goal,
            "stage": "goal",
            "status": "running",
            "started_at": _utc_timestamp(),
            "updated_at": _utc_timestamp(),
            "stage_history": [],
            "action_commitment": None,
            "action_result": None,
            "observation": None,
            "criticism": None,
            "improvement": None,
            "promotion": None,
            "executive_attention": _json_safe(executive_attention),
            "executive_work_system": self.executive_skills.compose(
                goal["objective"],
                {
                    "production_failure": goal.get("risk_tier") == "critical",
                    "uncertainty_high": bool(goal.get("unresolved_questions")),
                    "continuous_arrivals": bool(goal.get("continuous")),
                },
            ),
        }
        self.state["active_cycle"] = cycle
        self.state["status"] = "running"
        self._checkpoint(event=f"cycle_started:{cycle['cycle_id']}")
        return cycle

    def _advance_stage(self, cycle: Dict[str, Any], next_stage: str, event: str) -> None:
        cycle.setdefault("stage_history", []).append(
            {"stage": cycle["stage"], "completed_at": _utc_timestamp(), "event": event}
        )
        cycle["stage"] = next_stage
        cycle["updated_at"] = _utc_timestamp()
        self._checkpoint(event=event)

    def _failure(self, cycle: Dict[str, Any], failure_type: str, detail: Mapping[str, Any]) -> None:
        record = {
            "cycle_id": cycle["cycle_id"],
            "goal_id": cycle["goal_id"],
            "failure_type": failure_type,
            "detail": _json_safe(detail),
            "timestamp": _utc_timestamp(),
        }
        self.state.setdefault("failure_queues", {}).setdefault(failure_type, []).append(record)

    @staticmethod
    def _learner_for_failure(failure_type: str) -> str:
        if failure_type in {"perception", "knowledge", "verification", "evidence"}:
            return "knowledge"
        if failure_type in {"reasoning", "model", "world", "outcome"}:
            return "world"
        if failure_type in {
            "planning",
            "tool",
            "execution",
            "interrupted_action",
            "runtime",
        }:
            return "skill"
        return "none"

    def _route_failure_to_learning(
        self,
        cycle: Dict[str, Any],
        failure_type: str,
        criticism: Mapping[str, Any],
    ) -> Dict[str, Any]:
        learner = self._learner_for_failure(failure_type)
        route = {
            "learner": learner,
            "failure_type": failure_type,
            "cycle_id": cycle["cycle_id"],
            "goal_id": cycle["goal_id"],
            "committed": False,
        }
        if learner == "none":
            route["reason"] = "failure_does_not_authorize_learning"
            return route
        snapshot = None
        try:
            snapshot = self.learning.store.prepare_mutation(authority_goal=cycle["goal_id"])
            self.learning.store.state.setdefault("failure_queues", {}).setdefault(
                failure_type, []
            ).append(
                {
                    "cycle_id": cycle["cycle_id"],
                    "goal_id": cycle["goal_id"],
                    "learner": learner,
                    "criticism": _json_safe(criticism),
                    "timestamp": _utc_timestamp(),
                }
            )
            self.learning.store.commit(
                reason=f"canonical_failure_route:{cycle['cycle_id']}:{failure_type}",
                authority_goal=cycle["goal_id"],
            )
            route["committed"] = True
            route["reason"] = "cau_authorized_failure_route"
        except Exception as exc:
            if snapshot is not None:
                self.learning.store.rollback(snapshot)
            route["reason"] = f"failure_route_not_committed:{type(exc).__name__}"
        return route

    def submit_outcome(self, token: str, outcome: Mapping[str, Any]) -> Dict[str, Any]:
        token = str(token or "").strip()
        if not token:
            raise ValueError("outcome token is required")
        cycle = self.state.get("active_cycle") or {}
        expected = str(cycle.get("outcome_token") or "")
        if cycle.get("stage") != "await_outcome" or token != expected:
            raise ValueError("outcome token does not match an active waiting cycle")
        record = {
            "token": token,
            "cycle_id": cycle.get("cycle_id"),
            "outcome": _json_safe(outcome),
            "received_at": _utc_timestamp(),
            "outcome_hash": _canonical_hash(outcome),
        }
        self.state.setdefault("pending_outcomes", {})[token] = record
        self._checkpoint(event=f"delayed_outcome_received:{token}")
        return record

    def _turn_context(self, cycle: Mapping[str, Any]):
        return self.governed.begin_turn(
            turn_id=cycle["cycle_id"],
            session_id="aion-canonical-runtime",
            user_text=cycle["goal"]["objective"],
            request_metadata={
                "authority_goal": cycle["goal_id"],
                "goals": [cycle["goal"]],
                "reasoning_providers": ["aion_hexcore", "tessaris", "theta"],
            },
        )

    def tick(self) -> Dict[str, Any]:
        """Advance exactly one durable stage, making interruption behavior explicit."""
        self.state["last_heartbeat_at"] = _utc_timestamp()
        cycle = self.state.get("active_cycle")
        if not isinstance(cycle, dict):
            cycle = self._start_cycle()
            if cycle is None:
                return self.status()
        elif cycle.get("status") in TERMINAL_STATES and cycle.get("stage") != "complete":
            cycle["stage"] = "complete"
            self._checkpoint(event="terminal_cycle_routed_to_completion")

        try:
            stage = cycle["stage"]
            goal = cycle["goal"]

            if stage == "goal":
                turn = self._turn_context(cycle)
                cycle["governed_context"] = turn.to_dict()
                cycle["recalled_knowledge"] = turn.recalled_knowledge
                self._advance_stage(cycle, "investigate", "goal_context_opened")

            elif stage == "investigate":
                cycle["investigation"] = _json_safe(
                    self.adapter.investigate(goal, cycle.get("governed_context") or {})
                )
                self._advance_stage(cycle, "learn", "investigation_proposed")

            elif stage == "learn":
                cycle["learned_context"] = _json_safe(
                    self.adapter.learn_context(goal, cycle.get("investigation") or {})
                )
                self._advance_stage(cycle, "plan", "candidate_context_built")

            elif stage == "plan":
                plan = _json_safe(
                    self.adapter.plan(
                        goal,
                        cycle.get("investigation") or {},
                        cycle.get("learned_context") or {},
                    )
                )
                if isinstance(plan, Mapping):
                    plan = dict(plan)
                    work_system = dict(cycle.get("executive_work_system") or {})
                    plan["executive_method"] = _json_safe(
                        work_system.get("method_selection") or {}
                    )
                    plan["executive_skill_sequence"] = list(
                        work_system.get("stage_order") or []
                    )
                    plan["executive_authority"] = "proposal_only"
                cycle["plan"] = plan
                actions = list(plan.get("actions") or []) if isinstance(plan, Mapping) else []
                if not actions:
                    self._failure(cycle, "planning", {"reason": "no_action_proposed"})
                    cycle["status"] = "blocked"
                    self._advance_stage(cycle, "complete", "plan_blocked:no_action")
                else:
                    cycle["selected_action"] = _json_safe(actions[0])
                    self._advance_stage(cycle, "metacognitive_review", "plan_selected_for_metacognition")

            elif stage == "metacognitive_review":
                review = self.metacognition.review(
                    goal=goal,
                    investigation=cycle.get("investigation") or {},
                    learned_context=cycle.get("learned_context") or {},
                    plan=cycle.get("plan") or {},
                    action=cycle.get("selected_action") or {},
                    history=self.state.get("metacognitive_history") or [],
                )
                cycle["metacognitive_review"] = _json_safe(review)
                decision = str(review.get("decision") or "abstain")
                if decision == "revise" and isinstance(review.get("revised_action"), Mapping):
                    cycle["selected_action"] = _json_safe(review["revised_action"])
                    self._advance_stage(cycle, "commit_action", "metacognitive_action_revised")
                elif decision == "execute":
                    self._advance_stage(cycle, "commit_action", "metacognitive_review_passed")
                else:
                    failure_type = "authority" if decision == "escalate" else "metacognitive_review"
                    self._failure(cycle, failure_type, review)
                    cycle["status"] = "blocked"
                    self._advance_stage(cycle, "complete", f"metacognitive_{decision}")

            elif stage == "commit_action":
                action = dict(cycle.get("selected_action") or {})
                governance = self.governed.evaluate_action(
                    str(action.get("description") or action.get("type") or ""),
                    context=action,
                )
                cycle["action_governance"] = governance
                if governance.get("allowed") is not True:
                    self._failure(cycle, "authority", governance)
                    cycle["status"] = "blocked"
                    self._advance_stage(cycle, "complete", "action_denied")
                else:
                    cycle["action_commitment"] = {
                        "committed_at": _utc_timestamp(),
                        "action_hash": _canonical_hash(action),
                        "idempotency_key": f"{cycle['cycle_id']}:{action.get('action_id', 'action')}",
                        "execution_started": False,
                    }
                    self._advance_stage(cycle, "act", "action_committed_before_execution")

            elif stage == "act":
                commitment = dict(cycle.get("action_commitment") or {})
                if commitment.get("execution_started") and cycle.get("action_result") is None:
                    cycle["status"] = "blocked"
                    cycle["revalidation_required"] = True
                    self._failure(
                        cycle,
                        "interrupted_action",
                        {"reason": "execution_started_without_durable_outcome"},
                    )
                    self._advance_stage(cycle, "complete", "unsafe_reexecution_blocked")
                else:
                    commitment["execution_started"] = True
                    commitment["execution_started_at"] = _utc_timestamp()
                    cycle["action_commitment"] = commitment
                    self._checkpoint(event="action_execution_started")
                    cycle["action_result"] = _json_safe(
                        self.adapter.act(
                            cycle.get("selected_action") or {},
                            {
                                "cycle_id": cycle["cycle_id"],
                                "idempotency_key": commitment["idempotency_key"],
                                "goal": goal,
                            },
                        )
                    )
                    if cycle["action_result"].get("status") == "awaiting_outcome":
                        token = str(
                            cycle["action_result"].get("outcome_token")
                            or f"outcome:{cycle['cycle_id']}"
                        )
                        cycle["outcome_token"] = token
                        self._advance_stage(
                            cycle,
                            "await_outcome",
                            "action_committed_waiting_for_delayed_outcome",
                        )
                    else:
                        self._advance_stage(cycle, "observe", "action_outcome_committed")

            elif stage == "await_outcome":
                token = str(cycle.get("outcome_token") or "")
                delayed = (self.state.get("pending_outcomes") or {}).get(token)
                if not isinstance(delayed, Mapping):
                    self.state["status"] = "waiting_outcome"
                    self.state["next_wake_at"] = time.time() + self.wake_interval_seconds
                    self._checkpoint(event=f"delayed_outcome_pending:{token}")
                else:
                    cycle["action_result"] = {
                        **dict(cycle.get("action_result") or {}),
                        **dict(delayed.get("outcome") or {}),
                        "delayed_outcome_hash": delayed.get("outcome_hash"),
                        "delayed_outcome_received_at": delayed.get("received_at"),
                    }
                    self.state.setdefault("pending_outcomes", {}).pop(token, None)
                    self.state["status"] = "running"
                    self._advance_stage(cycle, "observe", "delayed_outcome_bound")

            elif stage == "observe":
                cycle["observation"] = _json_safe(
                    self.adapter.observe(
                        cycle.get("action_result") or {},
                        {"cycle_id": cycle["cycle_id"], "goal": goal},
                    )
                )
                self._advance_stage(cycle, "criticise", "outcome_observed")

            elif stage == "criticise":
                criticism = _json_safe(self.adapter.criticise(cycle))
                cycle["criticism"] = criticism
                failure_type = str(criticism.get("failure_type") or "unknown")
                if failure_type != "none":
                    self._failure(cycle, failure_type, criticism)
                    cycle["learner_route"] = self._route_failure_to_learning(
                        cycle,
                        failure_type,
                        criticism,
                    )
                self._advance_stage(cycle, "post_action_reflection", "outcome_criticised")

            elif stage == "post_action_reflection":
                review = dict(cycle.get("metacognitive_review") or {})
                reflection = self.metacognition.reflect_outcome(
                    goal=goal,
                    plan=cycle.get("plan") or {},
                    action=cycle.get("selected_action") or {},
                    review=review,
                    action_result=cycle.get("action_result") or {},
                    observation=cycle.get("observation") or {},
                    criticism=cycle.get("criticism") or {},
                )
                cycle["post_action_reflection"] = _json_safe(reflection)
                if reflection.get("diagnostic_required") is True:
                    from backend.modules.hexcore.autonomous_mastery_runtime import (
                        OpenDiagnosticExperimentInventor,
                    )

                    criticism = dict(cycle.get("criticism") or {})
                    hypotheses = list(criticism.get("competing_hypotheses") or [])
                    contracts = list(criticism.get("observation_contracts") or [])
                    diagnostic = OpenDiagnosticExperimentInventor().invent(
                        hypotheses=hypotheses,
                        observation_contracts=contracts,
                    )
                    cycle["diagnostic_experiment"] = _json_safe(diagnostic)
                    self.state.setdefault("diagnostic_experiments", []).append({
                        "cycle_id": cycle["cycle_id"],
                        "goal_id": cycle["goal_id"],
                        "diagnostic": _json_safe(diagnostic),
                        "created_at": _utc_timestamp(),
                    })
                    self.state["diagnostic_experiments"] = self.state[
                        "diagnostic_experiments"
                    ][-1000:]
                if review:
                    self.state.setdefault("metacognitive_history", []).append({
                        "review_id": review.get("review_id"),
                        "cycle_id": cycle["cycle_id"],
                        "goal_id": cycle["goal_id"],
                        "action_type": (cycle.get("selected_action") or {}).get("type"),
                        "action_signature": review.get("action_signature"),
                        "decision": review.get("decision"),
                        "depth": review.get("depth"),
                        "deliberation_units": review.get("deliberation_units"),
                        "verified": cycle.get("observation", {}).get("verified") is True,
                        "score": float(cycle.get("observation", {}).get("score") or 0.0),
                        "outcome_grade": reflection.get("outcome_grade"),
                        "outcome_reflection": _json_safe(reflection),
                        "recorded_at": _utc_timestamp(),
                    })
                    self.state["metacognitive_history"] = self.state["metacognitive_history"][-1000:]
                self._advance_stage(cycle, "improve", "outcome_reflected")

            elif stage == "improve":
                improvement = _json_safe(
                    self.adapter.improve(cycle, cycle.get("criticism") or {})
                )
                cycle["improvement"] = improvement
                candidate_data = improvement.get("candidate") if isinstance(improvement, Mapping) else None
                if isinstance(candidate_data, Mapping):
                    self.state.setdefault("private_challengers", []).append(_json_safe(candidate_data))
                    if candidate_data.get("verified") is True:
                        candidate = ProcedureCandidate(
                            procedure_id=str(
                                candidate_data.get("procedure_id")
                                or f"procedure_{_canonical_hash(candidate_data)[:16]}"
                            ),
                            goal=str(candidate_data.get("goal") or cycle["goal_id"]),
                            steps=[str(item) for item in candidate_data.get("steps") or []],
                            score=float(candidate_data.get("score") or 0.0),
                            success=bool(candidate_data.get("success") is True),
                            evidence=dict(candidate_data.get("evidence") or {}),
                            source_rules=[str(item) for item in candidate_data.get("source_rules") or []],
                        )
                        cycle["promotion"] = self.learning.skills.promote(candidate)
                self._advance_stage(cycle, "retain", "improvement_evaluated")

            elif stage == "retain":
                observation = dict(cycle.get("observation") or {})
                verified = bool(observation.get("verified") is True)
                response = json.dumps(cycle.get("action_result") or {}, sort_keys=True)
                turn = self._turn_context(cycle)
                learning_meta: Dict[str, Any] = {}
                if verified:
                    learning_meta["learning_outcome"] = {
                        "verified": True,
                        "verifier": str(observation.get("verifier") or "canonical_runtime_adapter"),
                        "verification_method": str(
                            observation.get("verification_method") or "executable"
                        ),
                        "answer": str(
                            observation.get("lesson")
                            or cycle.get("criticism", {}).get("lesson")
                            or response
                        ),
                        "evidence_refs": [
                            str(item.get("source") or item.get("id") or _canonical_hash(item))
                            for item in observation.get("evidence") or []
                            if isinstance(item, Mapping)
                        ],
                    }
                cycle["retention"] = self.governed.complete_turn(
                    context=turn,
                    response_text=response,
                    confidence=float(observation.get("confidence") or (1.0 if verified else 0.0)),
                    mode="canonical_cognitive_cycle",
                    apply_teaching=verified,
                    request_metadata=learning_meta,
                )
                self._advance_stage(cycle, "complete", "cycle_retained")

            elif stage == "complete":
                observation = dict(cycle.get("observation") or {})
                verified = bool(observation.get("verified") is True)
                if cycle.get("status") not in {"blocked", "failed"}:
                    cycle["status"] = "completed" if verified else "blocked"
                cycle["completed_at"] = _utc_timestamp()
                summary = {
                    "cycle_id": cycle["cycle_id"],
                    "goal_id": cycle["goal_id"],
                    "status": cycle["status"],
                    "verified": verified,
                    "score": float(observation.get("score") or 0.0),
                    "promotion": cycle.get("promotion"),
                    "completed_at": cycle["completed_at"],
                    "executive_method": (
                        (cycle.get("executive_work_system") or {})
                        .get("method_selection", {})
                        .get("method")
                    ),
                }
                self.executive_skills.record_outcome(
                    cycle.get("executive_work_system") or {},
                    verified=verified,
                    score=float(observation.get("score") or 0.0),
                )
                mastery_receipt = self._record_mastery_outcome(cycle)
                if mastery_receipt is not None:
                    summary["mastery_receipt_id"] = mastery_receipt["receipt_id"]
                self.state.setdefault("completed_cycles", []).append(summary)
                self.state["completed_cycles"] = self.state["completed_cycles"][-1000:]
                if verified:
                    self.goal_completion(cycle["goal_id"], observation)
                    self.state["mission_goals"] = [
                        item
                        for item in self.state.get("mission_goals") or []
                        if str(item.get("goal_id")) != cycle["goal_id"]
                    ]
                    self.state.setdefault("goal_runtime", {}).pop(cycle["goal_id"], None)
                else:
                    prior = dict(
                        self.state.setdefault("goal_runtime", {}).get(cycle["goal_id"]) or {}
                    )
                    attempts = int(prior.get("attempts") or 0) + 1
                    delay = self.wake_interval_seconds * min(64, 2 ** min(attempts, 6))
                    self.state["goal_runtime"][cycle["goal_id"]] = {
                        "attempts": attempts,
                        "last_status": cycle["status"],
                        "last_cycle_id": cycle["cycle_id"],
                        "next_eligible_at": time.time() + delay,
                    }
                self.state["active_cycle"] = None
                self.state["status"] = "idle"
                self.state["next_wake_at"] = time.time() + self.wake_interval_seconds
                self._checkpoint(event=f"cycle_completed:{summary['status']}")
                if verified and mastery_receipt is not None:
                    self.refresh_curriculum(str(mastery_receipt["mission_id"]))

            else:
                raise ValueError(f"unknown cognitive stage: {stage}")

        except Exception as exc:
            cycle["status"] = "failed"
            cycle["error"] = {"type": type(exc).__name__, "message": str(exc)}
            self.state["last_error"] = cycle["error"]
            self._failure(cycle, "runtime", cycle["error"])
            self._checkpoint(event=f"cycle_error:{type(exc).__name__}")

        return self.status()

    def run_cycle(self, *, max_stage_transitions: int = 32) -> Dict[str, Any]:
        initial_completed = len(self.state.get("completed_cycles") or [])
        for _ in range(max_stage_transitions):
            previous_stage = (self.state.get("active_cycle") or {}).get("stage")
            self.tick()
            if len(self.state.get("completed_cycles") or []) > initial_completed:
                break
            if self.state.get("status") == "idle" and self.state.get("active_cycle") is None:
                break
            current_stage = (self.state.get("active_cycle") or {}).get("stage")
            if current_stage == "await_outcome" and current_stage == previous_stage:
                break
        return self.status()

    def run_forever(self, *, max_cycles: Optional[int] = None) -> None:
        completed_at_start = len(self.state.get("completed_cycles") or [])
        self._stop_requested = False

        def _request_stop(_signum, _frame):
            self._stop_requested = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _request_stop)
            except ValueError:
                pass

        while not self._stop_requested:
            self.run_cycle()
            completed = len(self.state.get("completed_cycles") or []) - completed_at_start
            if max_cycles is not None and completed >= max_cycles:
                break
            next_wake = float(self.state.get("next_wake_at") or 0.0)
            delay = max(0.05, min(self.wake_interval_seconds, next_wake - time.time()))
            time.sleep(delay)

    def status(self) -> Dict[str, Any]:
        cycle = self.state.get("active_cycle") or {}
        missions = self.state.get("authorized_missions") or {}
        capability_map = self.state.get("capability_map") or {}
        return {
            "schema_version": "aion.hexcore.canonical_cognitive_runtime_status.v1",
            "runtime_state": self.state.get("status"),
            "revision": int(self.state.get("revision") or 0),
            "active_cycle_id": cycle.get("cycle_id"),
            "active_goal_id": cycle.get("goal_id"),
            "active_stage": cycle.get("stage"),
            "completed_cycles": len(self.state.get("completed_cycles") or []),
            "queued_mission_goals": len(self.state.get("mission_goals") or []),
            "failure_counts": {
                key: len(value)
                for key, value in (self.state.get("failure_queues") or {}).items()
            },
            "private_challengers": len(self.state.get("private_challengers") or []),
            "pending_outcomes": len(self.state.get("pending_outcomes") or {}),
            "authorized_missions": len(missions),
            "active_missions": sum(item.get("status") == "active" for item in missions.values()),
            "capabilities_tracked": len(capability_map),
            "capabilities_mastered": sum(
                item.get("mastered") is True for item in capability_map.values()
            ),
            "outcome_receipts": len(self.state.get("outcome_receipts") or []),
            "next_wake_at": self.state.get("next_wake_at"),
            "last_heartbeat_at": self.state.get("last_heartbeat_at"),
            "last_error": self.state.get("last_error"),
            "executive_self": self.executive_self.status(),
            "executive_skills": self.executive_skills.status(),
            "executive_attention": self.state.get("executive_attention"),
            "paths": {
                "state": str(self.paths.state),
                "learning": str(self.paths.learning),
                "ledger": str(self.paths.ledger),
            },
        }


def _paths_from_args(args: argparse.Namespace) -> RuntimePaths:
    defaults = RuntimePaths.defaults()
    return RuntimePaths(
        state=Path(args.state) if args.state else defaults.state,
        learning=Path(args.learning_state) if args.learning_state else defaults.learning,
        ledger=Path(args.ledger) if args.ledger else defaults.ledger,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical AION cognitive runtime")
    parser.add_argument("--state")
    parser.add_argument("--learning-state")
    parser.add_argument("--ledger")
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--run-forever", action="store_true")
    parser.add_argument("--max-cycles", type=int)
    parser.add_argument("--enqueue-goal")
    parser.add_argument("--goal-id")
    parser.add_argument("--submit-outcome-token")
    parser.add_argument("--submit-outcome-json")
    parser.add_argument(
        "--approval-policy",
        choices=("dry_run_only", "human_approval_required", "autonomous_allowed"),
        default="dry_run_only",
    )
    args = parser.parse_args()

    runtime = CanonicalAionCognitiveRuntime(
        paths=_paths_from_args(args),
        wake_interval_seconds=args.interval,
    )
    if args.enqueue_goal:
        runtime.enqueue_goal(
            {
                "goal_id": args.goal_id or f"mission_{_canonical_hash(args.enqueue_goal)[:12]}",
                "name": args.enqueue_goal,
                "objective": args.enqueue_goal,
                "priority": 1.0,
                "approval_policy": args.approval_policy,
                "status": "active",
            }
        )
    if args.submit_outcome_token:
        if not args.submit_outcome_json:
            parser.error("--submit-outcome-json is required with --submit-outcome-token")
        runtime.submit_outcome(
            args.submit_outcome_token,
            json.loads(args.submit_outcome_json),
        )
    if args.once:
        runtime.run_cycle()
    elif args.run_forever:
        runtime.run_forever(max_cycles=args.max_cycles)
    print(json.dumps(runtime.status(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
