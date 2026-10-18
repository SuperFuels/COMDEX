from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)
from .full_chess_simple_plan_following_kernel import (
    run_full_chess_simple_plan_following_kernel,
)
from .full_chess_self_play_curriculum_kernel import (
    run_full_chess_self_play_curriculum_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_long_term_plan_generation_memory.json")


@dataclass(frozen=True)
class LongTermPlanStage:
    stage_index: int
    stage_id: str
    stage_goal: str
    stage_reason: str
    priority: int
    trigger_feature: str
    expected_effect: str
    success_metric: str
    fallback_goal: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongTermPlanGenerationResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    plan_mode: str
    fen: str
    side_to_evaluate: str
    selected_move: str
    simple_active_plan: List[str]
    curriculum_level: int
    selected_policy_profile: str
    feature_summary: Dict[str, Any]
    long_term_plan: List[Dict[str, Any]]
    plan_stage_count: int
    primary_plan_goal: str
    terminal_plan_goal: str
    plan_horizon: str
    plan_trace_hash: str
    policy_memory_mutated: bool
    final_long_term_plan_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLongTermPlanGenerationKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.curriculum_memory_path = curriculum_memory_path
        self.review_memory_path = review_memory_path
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "long_term_plan_generation_count": 0,
            "last_primary_plan_goal": None,
            "last_terminal_plan_goal": None,
            "last_plan_stage_count": 0,
            "last_trace_hash": None,
            "plan_templates_used": {
                "king_safety": 0,
                "promotion_defence": 0,
                "invasion_reduction": 0,
                "development": 0,
                "centre_control": 0,
                "simplification": 0,
                "safe_endgame": 0,
            },
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("long_term_plan_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LongTermPlanGenerationResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e6_long_term_plan_generation_memory_v1",
            "task_name": result.task_name,
            "long_term_plan_policy": result.final_long_term_plan_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _make_stage(
        self,
        *,
        index: int,
        stage_id: str,
        goal: str,
        reason: str,
        priority: int,
        trigger: str,
        effect: str,
        metric: str,
        fallback: str,
    ) -> LongTermPlanStage:
        return LongTermPlanStage(
            stage_index=index,
            stage_id=stage_id,
            stage_goal=goal,
            stage_reason=reason,
            priority=priority,
            trigger_feature=trigger,
            expected_effect=effect,
            success_metric=metric,
            fallback_goal=fallback,
        )

    def _generate_stages(
        self,
        *,
        summary: Dict[str, Any],
        simple_plan: List[str],
        curriculum_policy_profile: str,
    ) -> List[LongTermPlanStage]:
        stages: List[LongTermPlanStage] = []
        index = 1

        def add(stage_id: str, goal: str, reason: str, priority: int, trigger: str, effect: str, metric: str, fallback: str) -> None:
            nonlocal index
            stages.append(
                self._make_stage(
                    index=index,
                    stage_id=stage_id,
                    goal=goal,
                    reason=reason,
                    priority=priority,
                    trigger=trigger,
                    effect=effect,
                    metric=metric,
                    fallback=fallback,
                )
            )
            index += 1

        king_score = int(summary.get("king_safety_score", 0))
        promotion_penalty = int(summary.get("promotion_danger_penalty", 0))
        invasion_penalty = int(summary.get("invasion_risk_penalty", 0))
        development_score = int(summary.get("development_score", 0))
        centre_score = int(summary.get("centre_control_score", 0))
        activity_score = int(summary.get("piece_activity_score", 0))
        material_balance = int(summary.get("material_balance", 0))

        if king_score < 60 or curriculum_policy_profile == "CURRICULUM-KING-SAFETY":
            add(
                "stage_1_stabilise_king",
                "stabilise_king",
                "king safety is below desired strategic threshold or curriculum is king-safety biased",
                100,
                "king_safety_score",
                "reduce immediate mate and back-rank collapse risk",
                "king_safety_score increases or remains above danger threshold",
                "simplify_if_losing",
            )

        if promotion_penalty < 0 or "stop_promotion" in simple_plan:
            add(
                "stage_2_stop_promotion",
                "stop_immediate_promotion",
                "promotion danger is active or simple plan requested promotion defence",
                95,
                "promotion_danger_penalty",
                "remove or blockade dangerous passed pawn",
                "promotion_danger_penalty improves toward zero",
                "stabilise_king",
            )

        if invasion_penalty < 0 or "reduce_invasion" in simple_plan:
            add(
                "stage_3_reduce_invasion",
                "reduce_invasion_pressure",
                "queen or rook invasion risk is present",
                90,
                "invasion_risk_penalty",
                "close invasion files and remove penetrated major pieces",
                "invasion_risk_penalty improves toward zero",
                "trade_attacking_piece",
            )

        if development_score < 0 or "develop_pieces" in simple_plan:
            add(
                "stage_4_develop_inactive_pieces",
                "develop_inactive_pieces",
                "development is incomplete",
                70,
                "development_score",
                "bring minor pieces into active squares",
                "development_score improves",
                "improve_piece_activity",
            )

        if centre_score < 25 or "improve_centre" in simple_plan:
            add(
                "stage_5_improve_centre_control",
                "improve_centre_control",
                "centre control is below target",
                65,
                "centre_control_score",
                "increase central control and reduce opponent freedom",
                "centre_control_score improves",
                "improve_piece_activity",
            )

        if activity_score < 50 or "improve_piece_activity" in simple_plan:
            add(
                "stage_6_improve_piece_activity",
                "improve_piece_activity",
                "piece activity is low",
                60,
                "piece_activity_score",
                "increase legal mobility and useful pressure",
                "piece_activity_score improves",
                "improve_centre_control",
            )

        if material_balance < 0:
            add(
                "stage_7_simplify_if_losing",
                "simplify_if_losing",
                "material balance is negative",
                55,
                "material_balance",
                "reduce tactical volatility and seek safer endgame",
                "material deficit stops increasing",
                "stabilise_king",
            )

        add(
            "stage_8_convert_to_safer_endgame",
            "convert_to_safer_endgame",
            "terminal strategic objective after immediate risks are reduced",
            40,
            "overall_positional_score",
            "move toward lower-risk endgame structure",
            "positional_score trend is non-negative",
            "repeat_plan_review",
        )

        stages.sort(key=lambda item: (-item.priority, item.stage_index))

        for new_index, stage in enumerate(stages, start=1):
            object.__setattr__(stage, "stage_index", new_index)

        return stages

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_long_term_plan_generation",
    ) -> LongTermPlanGenerationResult:
        side_to_evaluate = side_to_evaluate.lower()

        features = run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=fen,
            analysed_side=side_to_evaluate,
        )

        simple_plan = run_full_chess_simple_plan_following_kernel(
            memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        curriculum = run_full_chess_self_play_curriculum_kernel(
            memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            episode_count=4,
        )

        stages = self._generate_stages(
            summary=features.feature_summary,
            simple_plan=simple_plan.active_plan,
            curriculum_policy_profile=curriculum.selected_policy_profile,
        )

        primary_goal = stages[0].stage_goal if stages else "no_plan"
        terminal_goal = stages[-1].stage_goal if stages else "no_plan"

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "selected_move": simple_plan.selected_move,
            "simple_active_plan": simple_plan.active_plan,
            "curriculum_level": curriculum.final_curriculum_level,
            "selected_policy_profile": curriculum.selected_policy_profile,
            "feature_summary": features.feature_summary,
            "long_term_plan": [stage.to_dict() for stage in stages],
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        templates = dict(self.policy["plan_templates_used"])
        for stage in stages:
            if "king" in stage.stage_goal:
                templates["king_safety"] += 1
            if "promotion" in stage.stage_goal:
                templates["promotion_defence"] += 1
            if "invasion" in stage.stage_goal:
                templates["invasion_reduction"] += 1
            if "develop" in stage.stage_goal:
                templates["development"] += 1
            if "centre" in stage.stage_goal:
                templates["centre_control"] += 1
            if "simplify" in stage.stage_goal:
                templates["simplification"] += 1
            if "endgame" in stage.stage_goal:
                templates["safe_endgame"] += 1

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["long_term_plan_generation_count"] = int(self.policy.get("long_term_plan_generation_count", 0)) + 1
        self.policy["last_primary_plan_goal"] = primary_goal
        self.policy["last_terminal_plan_goal"] = terminal_goal
        self.policy["last_plan_stage_count"] = len(stages)
        self.policy["last_trace_hash"] = trace_hash
        self.policy["plan_templates_used"] = templates

        evidence = {
            "long_term_plan_generation_active": True,
            "multi_stage_plan_active": len(stages) >= 3,
            "positional_features_consumed": True,
            "simple_plan_consumed": True,
            "curriculum_policy_consumed": True,
            "selected_move_reviewed": bool(simple_plan.selected_move),
            "contains_terminal_endgame_goal": terminal_goal == "convert_to_safer_endgame",
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LongTermPlanGenerationResult(
            kernel_version="phase22e6_full_chess_long_term_plan_generation_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            plan_mode="long_term_multi_stage_plan_generation",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            selected_move=simple_plan.selected_move,
            simple_active_plan=simple_plan.active_plan,
            curriculum_level=curriculum.final_curriculum_level,
            selected_policy_profile=curriculum.selected_policy_profile,
            feature_summary=features.feature_summary,
            long_term_plan=[stage.to_dict() for stage in stages],
            plan_stage_count=len(stages),
            primary_plan_goal=primary_goal,
            terminal_plan_goal=terminal_goal,
            plan_horizon="multi_stage_strategic_plan",
            plan_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_long_term_plan_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel generates deterministic multi-stage long-term plans from AION positional features, "
                "simple plan telemetry, and curriculum policy pressure. It does not use Stockfish, cloud engines, "
                "Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_long_term_plan_generation_kernel(
    *,
    memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_long_term_plan_generation",
) -> LongTermPlanGenerationResult:
    return AionFullChessLongTermPlanGenerationKernel(
        memory_path=memory_path,
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
    result = run_full_chess_long_term_plan_generation_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Long-term plan generation memory saved to: {result.memory_path}")
