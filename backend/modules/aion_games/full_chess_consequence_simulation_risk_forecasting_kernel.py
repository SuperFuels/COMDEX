from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_long_term_plan_generation_kernel import (
    run_full_chess_long_term_plan_generation_kernel,
)
from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_consequence_simulation_risk_forecasting_memory.json")


@dataclass(frozen=True)
class ConsequenceRiskForecast:
    stage_index: int
    stage_id: str
    stage_goal: str
    risk_before: float
    risk_after_expected: float
    risk_delta: float
    failure_probability: float
    fallback_required: bool
    fallback_goal: str
    forecast_reason: str
    forecast_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsequenceSimulationRiskForecastingResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    forecast_mode: str
    fen: str
    side_to_evaluate: str
    selected_move: str
    plan_trace_hash: str
    plan_stage_count: int
    forecast_count: int
    average_risk_before: float
    average_risk_after_expected: float
    average_risk_delta: float
    maximum_failure_probability: float
    fallback_required_count: int
    highest_risk_stage_goal: str
    risk_forecasts: List[Dict[str, Any]]
    forecast_trace_hash: str
    policy_memory_mutated: bool
    final_forecast_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessConsequenceSimulationRiskForecastingKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        long_term_plan_memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.long_term_plan_memory_path = long_term_plan_memory_path
        self.curriculum_memory_path = curriculum_memory_path
        self.review_memory_path = review_memory_path
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "forecast_run_count": 0,
            "forecast_total": 0,
            "fallback_required_total": 0,
            "last_highest_risk_stage_goal": None,
            "last_maximum_failure_probability": None,
            "last_trace_hash": None,
            "risk_weights": {
                "king_safety": 1.0,
                "promotion": 1.0,
                "invasion": 1.0,
                "development": 0.7,
                "centre": 0.65,
                "activity": 0.6,
                "endgame": 0.5,
            },
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("consequence_risk_forecast_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ConsequenceSimulationRiskForecastingResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e7_consequence_simulation_risk_forecasting_memory_v1",
            "task_name": result.task_name,
            "consequence_risk_forecast_policy": result.final_forecast_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _base_risk_from_summary(self, summary: Dict[str, Any], stage_goal: str) -> float:
        king = max(0.0, (100.0 - float(summary.get("king_safety_score", 0))) / 100.0)
        promotion = min(1.0, abs(min(0.0, float(summary.get("promotion_danger_penalty", 0)))) / 300.0)
        invasion = min(1.0, abs(min(0.0, float(summary.get("invasion_risk_penalty", 0)))) / 300.0)
        development = min(1.0, abs(min(0.0, float(summary.get("development_score", 0)))) / 100.0)
        centre = max(0.0, (50.0 - float(summary.get("centre_control_score", 0))) / 100.0)
        activity = max(0.0, (60.0 - float(summary.get("piece_activity_score", 0))) / 100.0)
        endgame = max(0.0, -float(summary.get("positional_score", 0)) / 1000.0)

        weights = dict(self.policy["risk_weights"])

        if "king" in stage_goal:
            return round(min(1.0, king * weights["king_safety"] + invasion * 0.35), 6)
        if "promotion" in stage_goal:
            return round(min(1.0, promotion * weights["promotion"] + king * 0.2), 6)
        if "invasion" in stage_goal:
            return round(min(1.0, invasion * weights["invasion"] + king * 0.25), 6)
        if "develop" in stage_goal:
            return round(min(1.0, development * weights["development"] + activity * 0.25), 6)
        if "centre" in stage_goal:
            return round(min(1.0, centre * weights["centre"] + development * 0.15), 6)
        if "activity" in stage_goal:
            return round(min(1.0, activity * weights["activity"] + development * 0.15), 6)
        if "endgame" in stage_goal:
            return round(min(1.0, endgame * weights["endgame"] + king * 0.2), 6)

        return round(min(1.0, (king + promotion + invasion + development + centre + activity + endgame) / 7.0), 6)

    def _expected_risk_after(self, stage_goal: str, risk_before: float, priority: int) -> float:
        priority_factor = min(0.35, max(0.05, priority / 400.0))

        if "king" in stage_goal:
            reduction = 0.28 + priority_factor
        elif "promotion" in stage_goal:
            reduction = 0.32 + priority_factor
        elif "invasion" in stage_goal:
            reduction = 0.30 + priority_factor
        elif "develop" in stage_goal:
            reduction = 0.18 + priority_factor
        elif "centre" in stage_goal:
            reduction = 0.16 + priority_factor
        elif "activity" in stage_goal:
            reduction = 0.15 + priority_factor
        elif "endgame" in stage_goal:
            reduction = 0.12 + priority_factor
        else:
            reduction = 0.10 + priority_factor

        return round(max(0.0, risk_before - reduction), 6)

    def _forecast_stage(self, *, stage: Dict[str, Any], summary: Dict[str, Any], plan_trace_hash: str) -> ConsequenceRiskForecast:
        stage_goal = str(stage["stage_goal"])
        priority = int(stage.get("priority", 0))
        risk_before = self._base_risk_from_summary(summary, stage_goal)
        risk_after = self._expected_risk_after(stage_goal, risk_before, priority)
        risk_delta = round(risk_after - risk_before, 6)
        failure_probability = round(min(1.0, max(0.0, risk_after + (0.18 if priority < 60 else 0.08))), 6)
        fallback_required = failure_probability >= 0.35 or risk_after >= 0.3

        reason = (
            f"Stage {stage_goal} forecast from trigger {stage.get('trigger_feature')} "
            f"expects risk delta {risk_delta} with failure probability {failure_probability}."
        )

        trace_payload = {
            "stage": stage,
            "risk_before": risk_before,
            "risk_after_expected": risk_after,
            "risk_delta": risk_delta,
            "failure_probability": failure_probability,
            "fallback_required": fallback_required,
            "plan_trace_hash": plan_trace_hash,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }

        return ConsequenceRiskForecast(
            stage_index=int(stage["stage_index"]),
            stage_id=str(stage["stage_id"]),
            stage_goal=stage_goal,
            risk_before=risk_before,
            risk_after_expected=risk_after,
            risk_delta=risk_delta,
            failure_probability=failure_probability,
            fallback_required=fallback_required,
            fallback_goal=str(stage["fallback_goal"]),
            forecast_reason=reason,
            forecast_trace_hash=self._hash(trace_payload),
        )

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_consequence_simulation_risk_forecasting",
    ) -> ConsequenceSimulationRiskForecastingResult:
        side_to_evaluate = side_to_evaluate.lower()

        features = run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=fen,
            analysed_side=side_to_evaluate,
        )

        long_term_plan = run_full_chess_long_term_plan_generation_kernel(
            memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        forecasts = [
            self._forecast_stage(
                stage=stage,
                summary=features.feature_summary,
                plan_trace_hash=long_term_plan.plan_trace_hash,
            )
            for stage in long_term_plan.long_term_plan
        ]

        count = len(forecasts)
        avg_before = round(sum(item.risk_before for item in forecasts) / count, 6) if count else 0.0
        avg_after = round(sum(item.risk_after_expected for item in forecasts) / count, 6) if count else 0.0
        avg_delta = round(sum(item.risk_delta for item in forecasts) / count, 6) if count else 0.0
        max_failure = round(max((item.failure_probability for item in forecasts), default=0.0), 6)
        fallback_count = len([item for item in forecasts if item.fallback_required])
        highest = max(forecasts, key=lambda item: item.failure_probability) if forecasts else None

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "selected_move": long_term_plan.selected_move,
            "plan_trace_hash": long_term_plan.plan_trace_hash,
            "risk_forecasts": [item.to_dict() for item in forecasts],
            "average_risk_before": avg_before,
            "average_risk_after_expected": avg_after,
            "maximum_failure_probability": max_failure,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["forecast_run_count"] = int(self.policy.get("forecast_run_count", 0)) + 1
        self.policy["forecast_total"] = int(self.policy.get("forecast_total", 0)) + count
        self.policy["fallback_required_total"] = int(self.policy.get("fallback_required_total", 0)) + fallback_count
        self.policy["last_highest_risk_stage_goal"] = highest.stage_goal if highest else None
        self.policy["last_maximum_failure_probability"] = max_failure
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "consequence_simulation_active": True,
            "risk_forecasting_active": True,
            "long_term_plan_consumed": True,
            "positional_features_consumed": True,
            "forecasts_each_plan_stage": count == long_term_plan.plan_stage_count,
            "risk_delta_computed": True,
            "failure_probability_computed": True,
            "fallback_requirement_computed": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ConsequenceSimulationRiskForecastingResult(
            kernel_version="phase22e7_full_chess_consequence_simulation_risk_forecasting_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            forecast_mode="consequence_simulation_and_risk_forecasting",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            selected_move=long_term_plan.selected_move,
            plan_trace_hash=long_term_plan.plan_trace_hash,
            plan_stage_count=long_term_plan.plan_stage_count,
            forecast_count=count,
            average_risk_before=avg_before,
            average_risk_after_expected=avg_after,
            average_risk_delta=avg_delta,
            maximum_failure_probability=max_failure,
            fallback_required_count=fallback_count,
            highest_risk_stage_goal=highest.stage_goal if highest else "none",
            risk_forecasts=[item.to_dict() for item in forecasts],
            forecast_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_forecast_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel performs deterministic consequence simulation and risk forecasting over AION long-term plan stages. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_consequence_simulation_risk_forecasting_kernel(
    *,
    memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_consequence_simulation_risk_forecasting",
) -> ConsequenceSimulationRiskForecastingResult:
    return AionFullChessConsequenceSimulationRiskForecastingKernel(
        memory_path=memory_path,
        long_term_plan_memory_path=long_term_plan_memory_path,
        curriculum_memory_path=curriculum_memory_path,
        review_memory_path=review_memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        depth_limit=depth_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_consequence_simulation_risk_forecasting_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Consequence simulation risk forecast memory saved to: {result.memory_path}")
