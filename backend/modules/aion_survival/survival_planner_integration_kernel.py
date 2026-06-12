"""AION Phase 21Z — Survival Planner Integration Kernel.

This phase integrates the survival-planning stack into one proof trace.

It combines:
- difficulty escalation;
- multi-step lookahead;
- hazard semantics;
- adversarial moving predator prediction;
- planning under uncertainty;
- self-generated survival plans.

The output is a single planner receipt proving the integrated survival planner
can classify danger, simulate futures, handle uncertainty, generate a plan,
revise the plan, execute safely, and emit an auditable trace.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_survival.curriculum_difficulty_escalation_kernel import (
    run_curriculum_difficulty_escalation_kernel,
)
from backend.modules.aion_survival.multistep_lookahead_consequence_simulation_kernel import (
    run_multistep_lookahead_consequence_simulation_kernel,
)
from backend.modules.aion_survival.hazard_semantics_threat_model_kernel import (
    run_hazard_semantics_threat_model_kernel,
)
from backend.modules.aion_survival.adversarial_moving_predator_kernel import (
    run_adversarial_moving_predator_kernel,
)
from backend.modules.aion_survival.planning_under_uncertainty_kernel import (
    run_planning_under_uncertainty_kernel,
)
from backend.modules.aion_survival.self_generated_survival_plan_kernel import (
    run_self_generated_survival_plan_kernel,
)


DEFAULT_INTEGRATION_MEMORY_PATH = Path("data/aion_survival/survival_planner_integration_memory.json")


@dataclass(frozen=True)
class SurvivalPlannerIntegrationResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    integrated_phases: List[str]
    difficulty_escalation_passed: bool
    lookahead_passed: bool
    hazard_semantics_passed: bool
    predator_passed: bool
    uncertainty_passed: bool
    self_plan_passed: bool
    integration_passed: bool
    planner_receipt_hash: str
    planner_trace: Dict[str, Any]
    final_integration_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionSurvivalPlannerIntegrationKernel:
    def __init__(self, *, memory_path: Optional[Path] = None, runtime_root: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_INTEGRATION_MEMORY_PATH)
        self.runtime_root = Path(runtime_root or "data/aion_survival/integration_runtime")
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "integration_run_count": 0,
            "successful_integration_count": 0,
            "last_planner_receipt_hash": None,
            "integrated_phase_versions": [],
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
            policy = data.get("integration_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: SurvivalPlannerIntegrationResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21z_survival_planner_integration_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "integration_policy": result.final_integration_policy,
            "last_planner_receipt_hash": result.planner_receipt_hash,
            "last_integration_passed": result.integration_passed,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash_receipt(self, trace: Dict[str, Any]) -> str:
        encoded = json.dumps(trace, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def run(self, *, task_name: str = "survival_planner_integration") -> SurvivalPlannerIntegrationResult:
        self.runtime_root.mkdir(parents=True, exist_ok=True)

        t = run_curriculum_difficulty_escalation_kernel(
            memory_path=self.runtime_root / "21t_curriculum_memory.json"
        )
        u = run_multistep_lookahead_consequence_simulation_kernel(
            memory_path=self.runtime_root / "21u_lookahead_memory.json"
        )
        v = run_hazard_semantics_threat_model_kernel(
            memory_path=self.runtime_root / "21v_threat_memory.json"
        )
        w = run_adversarial_moving_predator_kernel(
            memory_path=self.runtime_root / "21w_predator_memory.json"
        )
        x = run_planning_under_uncertainty_kernel(
            memory_path=self.runtime_root / "21x_uncertainty_memory.json"
        )
        y = run_self_generated_survival_plan_kernel(
            memory_path=self.runtime_root / "21y_plan_memory.json"
        )

        difficulty_passed = bool(t.difficulty_improved and t.escalation_worlds_survived == t.escalation_worlds_run)
        lookahead_passed = bool(u.avoided_future_hazard_before_impact and u.hazards_hit == 0 and u.goal_reached)
        hazard_passed = bool(v.avoided_semantic_threat and v.threats_identified >= 4)
        predator_passed = bool(w.predator_avoided_before_impact and w.predator_intercepts_actual == 0 and w.goal_reached)
        uncertainty_passed = bool(x.avoided_overconfident_action and x.gathered_information_safely and x.final_action == "take_wide_route")
        plan_passed = bool(y.plan_generated and y.plan_updated_when_world_changed and y.goal_reached)

        integrated_phases = [
            "21T_curriculum_difficulty_escalation",
            "21U_multistep_lookahead",
            "21V_hazard_semantics",
            "21W_adversarial_moving_predator",
            "21X_planning_under_uncertainty",
            "21Y_self_generated_survival_plan",
        ]

        planner_trace = {
            "integrated_phases": integrated_phases,
            "phase_results": {
                "21T": {
                    "kernel_version": t.kernel_version,
                    "difficulty_improved": t.difficulty_improved,
                    "difficulty_score_delta": t.difficulty_score_delta,
                    "worlds_survived": t.escalation_worlds_survived,
                },
                "21U": {
                    "kernel_version": u.kernel_version,
                    "shallow_first_action": u.shallow_first_action,
                    "deep_first_action": u.deep_first_action,
                    "avoided_future_hazard_before_impact": u.avoided_future_hazard_before_impact,
                    "hazards_hit": u.hazards_hit,
                    "goal_reached": u.goal_reached,
                },
                "21V": {
                    "kernel_version": v.kernel_version,
                    "threats_identified": v.threats_identified,
                    "highest_severity_threat": v.highest_severity_threat,
                    "safe_action": v.safe_action,
                    "unsafe_action": v.unsafe_action,
                },
                "21W": {
                    "kernel_version": w.kernel_version,
                    "shallow_first_action": w.shallow_first_action,
                    "deep_first_action": w.deep_first_action,
                    "predator_avoided_before_impact": w.predator_avoided_before_impact,
                    "predator_intercepts_actual": w.predator_intercepts_actual,
                    "goal_reached": w.goal_reached,
                },
                "21X": {
                    "kernel_version": x.kernel_version,
                    "initial_action": x.initial_action,
                    "direct_action_allowed": x.direct_action_allowed,
                    "final_action": x.final_action,
                    "final_risk_estimate": x.final_risk_estimate,
                    "final_confidence": x.final_confidence,
                },
                "21Y": {
                    "kernel_version": y.kernel_version,
                    "plan_generated": y.plan_generated,
                    "plan_goal": y.plan_goal,
                    "plan_labels": y.plan_labels,
                    "plan_updated_when_world_changed": y.plan_updated_when_world_changed,
                    "goal_reached": y.goal_reached,
                },
            },
            "execution_claim": (
                "classify danger -> simulate future -> predict moving threat -> handle uncertainty -> "
                "generate/revise plan -> execute safely"
            ),
            "uses_llm_shortcut": False,
        }

        integration_passed = all([
            difficulty_passed,
            lookahead_passed,
            hazard_passed,
            predator_passed,
            uncertainty_passed,
            plan_passed,
        ])

        receipt_hash = self._hash_receipt(planner_trace)

        self.policy["integration_run_count"] = int(self.policy.get("integration_run_count", 0)) + 1
        if integration_passed:
            self.policy["successful_integration_count"] = int(self.policy.get("successful_integration_count", 0)) + 1
        self.policy["last_planner_receipt_hash"] = receipt_hash
        self.policy["integrated_phase_versions"] = [
            t.kernel_version,
            u.kernel_version,
            v.kernel_version,
            w.kernel_version,
            x.kernel_version,
            y.kernel_version,
        ]

        evidence = {
            "uses_llm_shortcut": False,
            "uses_survival_planner_integration": True,
            "uses_curriculum_difficulty_escalation": difficulty_passed,
            "uses_multistep_lookahead": lookahead_passed,
            "uses_hazard_semantics": hazard_passed,
            "uses_adversarial_moving_hazard": predator_passed,
            "uses_uncertainty_planning": uncertainty_passed,
            "uses_self_generated_plan": plan_passed,
            "uses_planner_receipt_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = SurvivalPlannerIntegrationResult(
            kernel_version="phase21z_survival_planner_integration_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            integrated_phases=integrated_phases,
            difficulty_escalation_passed=difficulty_passed,
            lookahead_passed=lookahead_passed,
            hazard_semantics_passed=hazard_passed,
            predator_passed=predator_passed,
            uncertainty_passed=uncertainty_passed,
            self_plan_passed=plan_passed,
            integration_passed=integration_passed,
            planner_receipt_hash=receipt_hash,
            planner_trace=planner_trace,
            final_integration_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational survival planner integration: AION can combine difficulty escalation, "
                "multi-step lookahead, hazard semantics, adversarial moving-hazard prediction, uncertainty handling, "
                "self-generated planning, plan revision, safe execution, and proof hashing. It does not prove general "
                "intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_survival_planner_integration_kernel(
    *,
    memory_path: Optional[Path] = None,
    runtime_root: Optional[Path] = None,
    task_name: str = "survival_planner_integration",
) -> SurvivalPlannerIntegrationResult:
    return AionSurvivalPlannerIntegrationKernel(
        memory_path=memory_path,
        runtime_root=runtime_root,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_survival_planner_integration_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Survival planner integration memory saved to: {result.memory_path}")
