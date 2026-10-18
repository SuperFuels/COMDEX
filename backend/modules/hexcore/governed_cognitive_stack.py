"""Canonical bridge across AION's legacy consciousness engines.

This is intentionally a thin composition layer.  It preserves the specialised
engines while making the canonical goal/capability/authority/outcome contract
the only route for real missions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.governed_cognitive_contract import canonical_hash, utc_now
from backend.modules.hexcore.metacognitive_control import MetacognitiveController
from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness


class GovernedCognitiveStack:
    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root or Path.cwd()).resolve()
        self.capabilities = MissionCapabilityActionHarness(repo_root=self.repo_root)
        self.metacognition = MetacognitiveController()

    @staticmethod
    def _objective(mission: Mapping[str, Any] | str) -> str:
        if isinstance(mission, str):
            return mission.strip()
        return str(mission.get("objective") or mission.get("goal") or mission.get("what") or "").strip()

    def deliberate(self, mission: Mapping[str, Any] | str, *, register_learning: bool = True) -> dict[str, Any]:
        from backend.modules.consciousness.ethics_engine import EthicsEngine
        from backend.modules.consciousness.planning_engine import PlanningEngine
        from backend.modules.consciousness.prediction_engine import PredictionEngineBase

        request = dict(mission) if isinstance(mission, Mapping) else {"objective": mission}
        objective = self._objective(request)
        request["objective"] = objective
        capability = self.capabilities.evaluate(request, register_learning=register_learning)
        plan = PlanningEngine.__new__(PlanningEngine).generate_governed_plan(request, capability)
        feasibility = PredictionEngineBase.assess_feasibility(
            object(), {**request, "capability_decision": capability}
        )
        action = {
            "action_id": "candidate_" + canonical_hash([objective, plan])[:16],
            "type": request.get("action_type") or "governed_mission_step",
            "description": objective,
            "risk_tier": request.get("risk_tier") or "low",
            "requires_consent": bool(request.get("requires_consent")),
            "consent_granted": bool(request.get("consent_granted")),
            "reversible": bool(request.get("reversible", True)),
            "rollback_plan": request.get("rollback_plan"),
            "verification_plan": request.get("verification_plan") or plan.get("success_criteria") or [],
            "assumptions": request.get("assumptions") or [],
            "predicted_success": feasibility,
            "executable": capability.get("decision") in {"execute", "execute_with_strong_verification"},
        }
        ethics = EthicsEngine().evaluate_action({
            **request,
            "capability_decision": capability,
        })
        review = self.metacognition.review(
            goal={"goal_id": request.get("goal_id") or "unassigned", **request},
            investigation={
                "unresolved_questions": capability.get("unresolved_questions") or [],
                "native_specialist_route": request.get("native_specialist_route") or {},
            },
            learned_context={"evidence_refs": request.get("evidence_refs") or []},
            plan={
                **plan,
                "assumptions": request.get("assumptions") or [],
                "counterfactuals": request.get("counterfactuals") or [],
                "contradictions": request.get("contradictions") or [],
            },
            action=action,
            history=request.get("decision_history") or [],
        )
        if capability.get("decision") in {"learn_then_execute", "clarify", "blocked"}:
            disposition = capability["decision"]
        elif not ethics.get("allowed"):
            disposition = "deny_or_escalate"
        else:
            disposition = review.get("decision") or "propose"
        record = {
            "schema_version": "aion.governed_cognitive_stack.v1",
            "deliberation_id": "delib_" + canonical_hash([request, capability, plan, review])[:20],
            "deliberated_at": utc_now(),
            "objective": objective,
            "disposition": disposition,
            "capability": capability,
            "plan": plan,
            "candidate_action": action,
            "feasibility": feasibility,
            "ethics": ethics,
            "metacognitive_review": review,
            "proposal_only": True,
            "execution_authority": False,
            "personality_authority": "communication_style_only",
            "resonance_authority": "telemetry_only",
        }
        record["record_hash"] = canonical_hash(record)
        return record

    def execute(self, deliberation: Mapping[str, Any], *, execution_adapter=None) -> dict[str, Any]:
        from backend.modules.hexcore.strategy_engine import StrategyEngine

        if deliberation.get("disposition") not in {"execute", "propose"}:
            return {
                "status": "not_executed",
                "reason": "deliberation_not_execution_ready",
                "disposition": deliberation.get("disposition"),
                "proposal_only": True,
            }
        plan = dict(deliberation.get("plan") or {})
        plan.update({
            "objective": deliberation.get("objective"),
            "capability_decision": (deliberation.get("capability") or {}).get("decision"),
        })
        return StrategyEngine.__new__(StrategyEngine).execute_plan(plan, execution_adapter)

