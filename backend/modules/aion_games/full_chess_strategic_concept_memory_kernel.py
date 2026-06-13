from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_consequence_simulation_risk_forecasting_kernel import (
    run_full_chess_consequence_simulation_risk_forecasting_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_strategic_concept_memory.json")


@dataclass(frozen=True)
class StrategicConcept:
    concept_id: str
    concept_name: str
    source_stage_goal: str
    source_trigger_feature: str
    trigger_features: List[str]
    primary_goal: str
    preferred_actions: List[str]
    success_rate: float
    usage_count: int
    average_risk_reduction: float
    policy_weight: float
    last_used_episode: int
    fallback_concepts: List[str]
    concept_reason: str
    use_condition: str
    preferred_response: str
    fallback_response: str
    reinforcement_score: float
    observed_count: int
    concept_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategicConceptMemoryResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    concept_memory_mode: str
    fen: str
    side_to_evaluate: str
    selected_move: str
    forecast_trace_hash: str
    concept_count: int
    new_concept_count: int
    reinforced_concept_count: int
    active_concepts: List[Dict[str, Any]]
    concept_names: List[str]
    strongest_concept: str
    strongest_reinforcement_score: float
    concept_memory_trace_hash: str
    policy_memory_mutated: bool
    final_concept_memory_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessStrategicConceptMemoryKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        forecast_memory_path: Optional[Path] = None,
        long_term_plan_memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.forecast_memory_path = forecast_memory_path
        self.long_term_plan_memory_path = long_term_plan_memory_path
        self.curriculum_memory_path = curriculum_memory_path
        self.review_memory_path = review_memory_path
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "concept_memory_run_count": 0,
            "concept_observation_total": 0,
            "last_strongest_concept": None,
            "last_trace_hash": None,
            "concept_library": {},
            "applied_concepts_total": 0,
            "last_applied_concepts": [],
            "last_plan_alignment_with_concepts": 0.0,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_concept_memory_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicConceptMemoryResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e8_strategic_concept_memory_v1",
            "task_name": result.task_name,
            "strategic_concept_memory_policy": result.final_concept_memory_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _concept_from_stage_goal(self, stage_goal: str) -> Dict[str, str]:
        if "king" in stage_goal:
            return {
                "concept_id": "KING_SAFETY_RECOVERY_v1",
                "concept_name": "king_safety_recovery",
                "trigger_features": ["king_safety_low", "back_rank_threat", "invasion_risk_high"],
                "primary_goal": "stabilise_king",
                "preferred_actions": ["castling", "defensive_piece_reposition", "pawn_shield_reinforce"],
                "fallback_concepts": ["DEVELOPMENT_FIRST_v1", "SIMPLIFY_WHEN_LOSING_v1"],
                "use_condition": "king safety pressure, mate-loss memory, or back-rank collapse risk is active",
                "preferred_response": "stabilise king before expansion or attack",
                "fallback_response": "simplify if losing or trade attacking material",
            }
        if "invasion" in stage_goal:
            return {
                "concept_id": "INVASION_PRESSURE_REDUCTION_v1",
                "concept_name": "invasion_pressure_reduction",
                "trigger_features": ["invasion_risk_high", "queen_penetration", "rook_penetration"],
                "primary_goal": "reduce_invasion_pressure",
                "preferred_actions": ["block_invasion_file", "trade_attacking_piece", "force_major_piece_retreat"],
                "fallback_concepts": ["KING_SAFETY_RECOVERY_v1", "SIMPLIFY_WHEN_LOSING_v1"],
                "use_condition": "queen or rook invasion risk is detected",
                "preferred_response": "close invasion files and remove penetrated major pieces",
                "fallback_response": "force queen trade or retreat king to safer square",
            }
        if "promotion" in stage_goal:
            return {
                "concept_id": "PROMOTION_DEFENCE_PROTOCOL_v1",
                "concept_name": "promotion_defence_protocol",
                "trigger_features": ["promotion_danger_high", "passed_pawn_near_promotion"],
                "primary_goal": "stop_immediate_promotion",
                "preferred_actions": ["blockade_passed_pawn", "capture_dangerous_pawn", "king_stop_square_control"],
                "fallback_concepts": ["SAFE_ENDGAME_CONVERSION_v1", "KING_SAFETY_RECOVERY_v1"],
                "use_condition": "passed pawn or promotion danger is detected",
                "preferred_response": "blockade or capture the dangerous pawn before unrelated development",
                "fallback_response": "force perpetual defence or simplify into stoppable endgame",
            }
        if "develop" in stage_goal:
            return {
                "concept_id": "DEVELOPMENT_FIRST_v1",
                "concept_name": "development_before_attack",
                "trigger_features": ["development_low", "inactive_minor_pieces", "opening_phase"],
                "primary_goal": "develop_inactive_pieces",
                "preferred_actions": ["develop_minor_piece", "connect_rooks", "avoid_premature_queen_activity"],
                "fallback_concepts": ["CENTRE_CONTROL_BEFORE_CONVERSION_v1", "PIECE_ACTIVITY_RECOVERY_v1"],
                "use_condition": "development score is low or pieces are inactive",
                "preferred_response": "develop inactive pieces before speculative attack",
                "fallback_response": "improve piece activity with the safest legal move",
            }
        if "centre" in stage_goal:
            return {
                "concept_id": "CENTRE_CONTROL_BEFORE_CONVERSION_v1",
                "concept_name": "centre_control_before_conversion",
                "trigger_features": ["centre_control_low", "conversion_attempt", "mobility_constraint"],
                "primary_goal": "improve_centre_control",
                "preferred_actions": ["occupy_centre", "challenge_centre", "increase_central_piece_pressure"],
                "fallback_concepts": ["PIECE_ACTIVITY_RECOVERY_v1", "DEVELOPMENT_FIRST_v1"],
                "use_condition": "centre control is weak before conversion attempt",
                "preferred_response": "increase centre control before endgame conversion",
                "fallback_response": "improve piece activity toward central squares",
            }
        if "activity" in stage_goal:
            return {
                "concept_id": "PIECE_ACTIVITY_RECOVERY_v1",
                "concept_name": "piece_activity_recovery",
                "trigger_features": ["piece_activity_low", "low_mobility", "inactive_piece_cluster"],
                "primary_goal": "improve_piece_activity",
                "preferred_actions": ["increase_mobility", "activate_worst_piece", "create_useful_pressure"],
                "fallback_concepts": ["DEVELOPMENT_FIRST_v1", "CENTRE_CONTROL_BEFORE_CONVERSION_v1"],
                "use_condition": "piece activity score is below target",
                "preferred_response": "increase legal mobility and pressure before committing",
                "fallback_response": "develop inactive pieces",
            }
        if "endgame" in stage_goal:
            return {
                "concept_id": "SAFE_ENDGAME_CONVERSION_v1",
                "concept_name": "safe_endgame_conversion",
                "trigger_features": ["risks_reduced", "simplification_available", "positional_trend_stable"],
                "primary_goal": "convert_to_safer_endgame",
                "preferred_actions": ["trade_when_safe", "reduce_tactical_volatility", "centralise_king_late"],
                "fallback_concepts": ["KING_SAFETY_RECOVERY_v1", "CENTRE_CONTROL_BEFORE_CONVERSION_v1"],
                "use_condition": "immediate risks are reduced and position can be simplified",
                "preferred_response": "convert toward lower-risk endgame structure",
                "fallback_response": "repeat plan review before conversion",
            }

        return {
            "concept_id": "GENERAL_PLAN_REVIEW_v1",
            "concept_name": "general_plan_review",
            "trigger_features": ["unknown_stage_goal"],
            "primary_goal": "repeat_plan_review",
            "preferred_actions": ["review_plan", "forecast_again"],
            "fallback_concepts": ["KING_SAFETY_RECOVERY_v1"],
            "use_condition": "no specialised concept matched",
            "preferred_response": "review plan stage and forecast again",
            "fallback_response": "return to king safety and material preservation",
        }

    def _concept_from_forecast(self, forecast: Dict[str, Any]) -> StrategicConcept:
        stage_goal = str(forecast["stage_goal"])
        concept = self._concept_from_stage_goal(stage_goal)
        concept_id = concept["concept_id"]

        risk_before = float(forecast.get("risk_before", 0.0))
        risk_delta = abs(float(forecast.get("risk_delta", 0.0)))
        failure_probability = float(forecast.get("failure_probability", 0.0))

        library = self.policy.get("concept_library", {})
        existing = library.get(concept_id, {}) if isinstance(library, dict) else {}
        observed_count = int(existing.get("observed_count", 0)) + 1
        previous_score = float(existing.get("reinforcement_score", 0.0))

        average_risk_reduction = round(
            (
                float(existing.get("average_risk_reduction", 0.0)) * max(0, observed_count - 1)
                + risk_delta
            )
            / observed_count,
            6,
        )

        success_rate = round(min(0.99, max(0.01, 1.0 - failure_probability)), 6)
        policy_weight = round(1.0 + average_risk_reduction + success_rate + (observed_count * 0.03), 6)

        reinforcement_score = round(
            previous_score + 1.0 + risk_before + risk_delta + failure_probability + policy_weight,
            6,
        )

        trace_payload = {
            "concept_id": concept_id,
            "stage_goal": stage_goal,
            "risk_before": risk_before,
            "risk_delta": risk_delta,
            "failure_probability": failure_probability,
            "observed_count": observed_count,
            "reinforcement_score": reinforcement_score,
            "success_rate": success_rate,
            "policy_weight": policy_weight,
            "average_risk_reduction": average_risk_reduction,
            "forecast_trace_hash": forecast.get("forecast_trace_hash"),
        }

        return StrategicConcept(
            concept_id=concept_id,
            concept_name=concept["concept_name"],
            source_stage_goal=stage_goal,
            source_trigger_feature=str(forecast.get("stage_id", "")),
            trigger_features=list(concept["trigger_features"]),
            primary_goal=concept["primary_goal"],
            preferred_actions=list(concept["preferred_actions"]),
            success_rate=success_rate,
            usage_count=observed_count,
            average_risk_reduction=average_risk_reduction,
            policy_weight=policy_weight,
            last_used_episode=observed_count,
            fallback_concepts=list(concept["fallback_concepts"]),
            concept_reason=(
                f"Concept {concept['concept_name']} reinforced from stage {stage_goal} "
                f"with failure probability {failure_probability} and risk delta {risk_delta}."
            ),
            use_condition=concept["use_condition"],
            preferred_response=concept["preferred_response"],
            fallback_response=concept["fallback_response"],
            reinforcement_score=reinforcement_score,
            observed_count=observed_count,
            concept_trace_hash=self._hash(trace_payload),
        )

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_strategic_concept_memory",
    ) -> StrategicConceptMemoryResult:
        side_to_evaluate = side_to_evaluate.lower()

        forecast = run_full_chess_consequence_simulation_risk_forecasting_kernel(
            memory_path=self.forecast_memory_path,
            long_term_plan_memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        concepts_by_id: Dict[str, StrategicConcept] = {}
        for item in forecast.risk_forecasts:
            concept = self._concept_from_forecast(item)
            concepts_by_id[concept.concept_id] = concept

        active_concepts = list(concepts_by_id.values())
        active_concepts.sort(key=lambda item: (-item.reinforcement_score, item.concept_name))

        library = dict(self.policy.get("concept_library", {}))
        new_count = 0
        reinforced_count = 0

        for concept in active_concepts:
            if concept.concept_id in library:
                reinforced_count += 1
            else:
                new_count += 1
            library[concept.concept_id] = concept.to_dict()

        strongest = active_concepts[0] if active_concepts else None

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "selected_move": forecast.selected_move,
            "forecast_trace_hash": forecast.forecast_trace_hash,
            "active_concepts": [concept.to_dict() for concept in active_concepts],
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["concept_memory_run_count"] = int(self.policy.get("concept_memory_run_count", 0)) + 1
        applied_concepts = [concept.concept_id for concept in active_concepts[:3]]
        plan_alignment_with_concepts = round(
            min(1.0, len(applied_concepts) / max(1, len(active_concepts))) if active_concepts else 0.0,
            6,
        )

        self.policy["concept_observation_total"] = int(self.policy.get("concept_observation_total", 0)) + len(active_concepts)
        self.policy["applied_concepts_total"] = int(self.policy.get("applied_concepts_total", 0)) + len(applied_concepts)
        self.policy["last_applied_concepts"] = applied_concepts
        self.policy["last_plan_alignment_with_concepts"] = plan_alignment_with_concepts
        self.policy["last_strongest_concept"] = strongest.concept_name if strongest else None
        self.policy["last_trace_hash"] = trace_hash
        self.policy["concept_library"] = library

        evidence = {
            "strategic_concept_memory_active": True,
            "risk_forecast_consumed": True,
            "concepts_generated": len(active_concepts) > 0,
            "concept_library_mutated": True,
            "concept_reinforcement_scores_computed": True,
            "strongest_concept_selected": strongest is not None,
            "applied_concepts_this_run": len(active_concepts[:3]),
            "plan_alignment_with_concepts": round(min(1.0, len(active_concepts[:3]) / max(1, len(active_concepts))) if active_concepts else 0.0, 6),
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = StrategicConceptMemoryResult(
            kernel_version="phase22e8_full_chess_strategic_concept_memory_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            concept_memory_mode="strategic_concept_memory",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            selected_move=forecast.selected_move,
            forecast_trace_hash=forecast.forecast_trace_hash,
            concept_count=len(active_concepts),
            new_concept_count=new_count,
            reinforced_concept_count=reinforced_count,
            active_concepts=[concept.to_dict() for concept in active_concepts],
            concept_names=[concept.concept_name for concept in active_concepts],
            strongest_concept=strongest.concept_name if strongest else "none",
            strongest_reinforcement_score=strongest.reinforcement_score if strongest else 0.0,
            concept_memory_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_concept_memory_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel converts recurring AION plan and risk patterns into deterministic named strategic concepts. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_strategic_concept_memory_kernel(
    *,
    memory_path: Optional[Path] = None,
    forecast_memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_strategic_concept_memory",
) -> StrategicConceptMemoryResult:
    return AionFullChessStrategicConceptMemoryKernel(
        memory_path=memory_path,
        forecast_memory_path=forecast_memory_path,
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
    result = run_full_chess_strategic_concept_memory_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic concept memory saved to: {result.memory_path}")
