"""AION Phase 21X — Planning Under Uncertainty Kernel.

This phase handles the case where AION does not yet know whether an entity,
route, or action is safe or dangerous.

The locked behaviour is:
    unknown entity -> uncertainty score -> cautious probe/observe
    -> update threat confidence -> avoid overconfident action.

This is the "bear in the woods" case:
    not automatically safe;
    not automatically hostile;
    gather evidence safely before committing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_UNCERTAINTY_MEMORY_PATH = Path("data/aion_survival/planning_under_uncertainty_memory.json")


@dataclass(frozen=True)
class UncertaintyObservation:
    observation_id: str
    entity: str
    prior_risk: float
    observed_behaviour: str
    evidence: str
    posterior_risk: float
    confidence: float
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanningUnderUncertaintyResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    unknown_entity: str
    initial_risk_estimate: float
    initial_confidence: float
    initial_action: str
    direct_action: str
    direct_action_allowed: bool
    observations: List[Dict[str, Any]]
    final_risk_estimate: float
    final_confidence: float
    final_action: str
    avoided_overconfident_action: bool
    gathered_information_safely: bool
    uncertainty_reduced: bool
    final_uncertainty_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionPlanningUnderUncertaintyKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_UNCERTAINTY_MEMORY_PATH)
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "unknown_prior_risk": 0.50,
            "minimum_confidence_for_direct_action": 0.75,
            "cautious_action": "observe_from_distance",
            "safe_fallback_action": "take_wide_route",
            "direct_action": "approach_entity",
            "safe_information_gathering_count": 0,
            "overconfident_actions_avoided": 0,
            "entity_risk_memory": {},
        }

        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            policy = data.get("uncertainty_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: PlanningUnderUncertaintyResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21x_planning_under_uncertainty_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "uncertainty_policy": result.final_uncertainty_policy,
            "last_unknown_entity": result.unknown_entity,
            "last_final_risk_estimate": result.final_risk_estimate,
            "last_final_confidence": result.final_confidence,
            "last_final_action": result.final_action,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _update_risk(self, prior: float, behaviour: str) -> tuple[float, float, str, str]:
        if behaviour == "moves_toward_agent":
            return 0.82, 0.78, "avoid_and_reroute", "entity moved toward agent; interception risk increased"
        if behaviour == "blocks_direct_route":
            return 0.88, 0.86, "take_wide_route", "entity blocked direct route; route threat increased"
        if behaviour == "moves_away_from_agent":
            return 0.35, 0.62, "continue_observing", "entity moved away; risk reduced but confidence not yet high enough"
        return prior, 0.40, "observe_from_distance", "behaviour unknown; maintain cautious distance"

    def run(self, *, task_name: str = "planning_under_uncertainty") -> PlanningUnderUncertaintyResult:
        unknown_entity = "unknown_agent_bear_analogy"
        direct_action = str(self.policy["direct_action"])

        initial_risk = float(self.policy["unknown_prior_risk"])
        initial_confidence = 0.40
        confidence_threshold = float(self.policy["minimum_confidence_for_direct_action"])

        direct_action_allowed = bool(initial_confidence >= confidence_threshold and initial_risk < 0.35)
        initial_action = direct_action if direct_action_allowed else str(self.policy["cautious_action"])

        observations: List[UncertaintyObservation] = []

        prior = initial_risk
        for idx, behaviour in enumerate(["moves_away_from_agent", "moves_toward_agent", "blocks_direct_route"], start=1):
            posterior, confidence, recommended, evidence = self._update_risk(prior, behaviour)
            observations.append(
                UncertaintyObservation(
                    observation_id=f"OBS-{idx}",
                    entity=unknown_entity,
                    prior_risk=round(prior, 6),
                    observed_behaviour=behaviour,
                    evidence=evidence,
                    posterior_risk=round(posterior, 6),
                    confidence=round(confidence, 6),
                    recommended_action=recommended,
                )
            )
            prior = posterior

        final_risk = observations[-1].posterior_risk
        final_confidence = observations[-1].confidence
        final_action = observations[-1].recommended_action

        avoided_overconfident_action = not direct_action_allowed and initial_action == "observe_from_distance"
        gathered_information_safely = len(observations) >= 3 and all(o.recommended_action != "approach_entity" for o in observations)
        uncertainty_reduced = final_confidence > initial_confidence

        if gathered_information_safely:
            self.policy["safe_information_gathering_count"] = int(self.policy.get("safe_information_gathering_count", 0)) + 1
        if avoided_overconfident_action:
            self.policy["overconfident_actions_avoided"] = int(self.policy.get("overconfident_actions_avoided", 0)) + 1

        entity_memory = dict(self.policy.get("entity_risk_memory", {}))
        entity_memory[unknown_entity] = {
            "final_risk_estimate": final_risk,
            "final_confidence": final_confidence,
            "final_action": final_action,
            "observed_behaviours": [o.observed_behaviour for o in observations],
            "classification": "uncertain_but_high_risk_after_evidence",
        }
        self.policy["entity_risk_memory"] = entity_memory

        evidence = {
            "uses_llm_shortcut": False,
            "uses_uncertainty_score": True,
            "uses_confidence_threshold": True,
            "uses_safe_information_gathering": True,
            "uses_risk_update_from_observation": True,
            "uses_overconfidence_avoidance": True,
            "uses_persistent_uncertainty_memory": True,
            "memory_loaded": self.memory_loaded,
            "direct_action_allowed": direct_action_allowed,
            "observations_count": len(observations),
        }

        result = PlanningUnderUncertaintyResult(
            kernel_version="phase21x_planning_under_uncertainty_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            unknown_entity=unknown_entity,
            initial_risk_estimate=round(initial_risk, 6),
            initial_confidence=round(initial_confidence, 6),
            initial_action=initial_action,
            direct_action=direct_action,
            direct_action_allowed=direct_action_allowed,
            observations=[o.to_dict() for o in observations],
            final_risk_estimate=round(final_risk, 6),
            final_confidence=round(final_confidence, 6),
            final_action=final_action,
            avoided_overconfident_action=avoided_overconfident_action,
            gathered_information_safely=gathered_information_safely,
            uncertainty_reduced=uncertainty_reduced,
            final_uncertainty_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational planning under uncertainty: AION can treat an unknown entity "
                "as neither automatically safe nor automatically hostile, gather evidence safely, update risk, "
                "and avoid overconfident action. It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_planning_under_uncertainty_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "planning_under_uncertainty",
) -> PlanningUnderUncertaintyResult:
    return AionPlanningUnderUncertaintyKernel(memory_path=memory_path).run(task_name=task_name)


if __name__ == "__main__":
    result = run_planning_under_uncertainty_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Planning-under-uncertainty memory saved to: {result.memory_path}")
