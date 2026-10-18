from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_goal_biased_strategic_search_kernel import (
    run_full_chess_goal_biased_strategic_search_kernel,
)
from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_simple_plan_following_memory.json")


@dataclass(frozen=True)
class SimplePlanFollowingResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    planning_mode: str
    fen: str
    side_to_move: str
    side_to_evaluate: str
    selected_move: str
    selected_move_is_legal: bool
    selected_strategic_score: float
    selected_reason: str
    active_plan: List[str]
    plan_reason: str
    plan_followed: bool
    plan_alignment_score: float
    plan_alignment_reasons: List[str]
    base_positional_score: int
    feature_summary: Dict[str, Any]
    strategic_search_trace_hash: str
    plan_trace_hash: str
    policy_memory_mutated: bool
    final_plan_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessSimplePlanFollowingKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "plan_generation_count": 0,
            "plan_follow_count": 0,
            "plan_break_count": 0,
            "last_selected_move": None,
            "last_active_plan": [],
            "last_plan_followed": None,
            "last_plan_alignment_score": None,
            "last_trace_hash": None,
            "plan_thresholds": {
                "king_danger": 40,
                "promotion_danger": -100,
                "invasion_danger": -100,
                "development_lag": -20,
                "low_activity": 45,
                "weak_centre": 20,
                "repetition_danger": -100,
            },
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("simple_plan_following_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: SimplePlanFollowingResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e3_simple_plan_following_memory_v1",
            "task_name": result.task_name,
            "simple_plan_following_policy": result.final_plan_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _side_name(self, colour: chess.Color) -> str:
        return "white" if colour == chess.WHITE else "black"

    def _form_plan(self, summary: Dict[str, Any]) -> tuple[List[str], str]:
        thresholds = dict(self.policy["plan_thresholds"])
        plan: List[str] = []
        reasons: List[str] = []

        if summary.get("promotion_danger_penalty", 0) <= thresholds["promotion_danger"]:
            plan.append("stop_promotion")
            reasons.append("enemy promotion danger detected")

        if summary.get("invasion_risk_penalty", 0) <= thresholds["invasion_danger"]:
            plan.append("reduce_invasion")
            reasons.append("queen or rook invasion risk detected")

        if summary.get("king_safety_score", 0) <= thresholds["king_danger"]:
            plan.append("defend_king")
            reasons.append("king safety is weak")

        if summary.get("repetition_risk_penalty", 0) <= thresholds["repetition_danger"]:
            plan.append("avoid_repetition")
            reasons.append("repetition risk detected")

        if summary.get("development_score", 0) <= thresholds["development_lag"]:
            plan.append("develop_pieces")
            reasons.append("development is incomplete")

        if summary.get("centre_control_score", 0) <= thresholds["weak_centre"]:
            plan.append("improve_centre")
            reasons.append("centre control is weak")

        if summary.get("piece_activity_score", 0) <= thresholds["low_activity"]:
            plan.append("improve_piece_activity")
            reasons.append("piece activity is low")

        if not plan:
            plan = ["improve_position"]
            reasons.append("no emergency detected; improve overall position")

        return plan[:4], "; ".join(reasons)

    def _move_alignment(
        self,
        *,
        board: chess.Board,
        move_uci: str,
        active_plan: List[str],
        before_summary: Dict[str, Any],
        after_summary: Dict[str, Any],
    ) -> tuple[bool, float, List[str]]:
        move = chess.Move.from_uci(move_uci)
        reasons: List[str] = []
        score = 0.0

        if "stop_promotion" in active_plan:
            before = before_summary.get("promotion_danger_penalty", 0)
            after = after_summary.get("promotion_danger_penalty", 0)
            if after > before:
                score += 2.0
                reasons.append("promotion danger reduced")
            else:
                score -= 1.0
                reasons.append("promotion danger not reduced")

        if "reduce_invasion" in active_plan:
            before = before_summary.get("invasion_risk_penalty", 0)
            after = after_summary.get("invasion_risk_penalty", 0)
            if after > before:
                score += 2.0
                reasons.append("invasion risk reduced")
            else:
                score -= 1.0
                reasons.append("invasion risk not reduced")

        if "defend_king" in active_plan:
            before = before_summary.get("king_safety_score", 0)
            after = after_summary.get("king_safety_score", 0)
            if after >= before:
                score += 1.5
                reasons.append("king safety maintained or improved")
            else:
                score -= 1.0
                reasons.append("king safety worsened")

        if "avoid_repetition" in active_plan:
            before = before_summary.get("repetition_risk_penalty", 0)
            after = after_summary.get("repetition_risk_penalty", 0)
            if after >= before:
                score += 1.0
                reasons.append("repetition risk not worsened")
            else:
                score -= 1.0
                reasons.append("repetition risk worsened")

        if "develop_pieces" in active_plan:
            before = before_summary.get("development_score", 0)
            after = after_summary.get("development_score", 0)
            if after > before:
                score += 1.5
                reasons.append("development improved")
            elif board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type in (chess.KNIGHT, chess.BISHOP):
                score += 1.0
                reasons.append("minor piece developed")
            else:
                score -= 0.5
                reasons.append("development not improved")

        if "improve_centre" in active_plan:
            before = before_summary.get("centre_control_score", 0)
            after = after_summary.get("centre_control_score", 0)
            if after > before:
                score += 1.0
                reasons.append("centre control improved")
            else:
                score -= 0.25
                reasons.append("centre control not improved")

        if "improve_piece_activity" in active_plan:
            before = before_summary.get("piece_activity_score", 0)
            after = after_summary.get("piece_activity_score", 0)
            if after > before:
                score += 1.0
                reasons.append("piece activity improved")
            else:
                score -= 0.25
                reasons.append("piece activity not improved")

        if "improve_position" in active_plan:
            before = before_summary.get("positional_score", 0)
            after = after_summary.get("positional_score", 0)
            if after >= before:
                score += 1.0
                reasons.append("overall position maintained or improved")
            else:
                score -= 0.5
                reasons.append("overall position worsened")

        plan_followed = score > 0
        return plan_followed, round(score, 6), reasons

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_simple_plan_following",
    ) -> SimplePlanFollowingResult:
        board = chess.Board(fen)
        side_to_evaluate = side_to_evaluate.lower()

        features = run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=fen,
            analysed_side=side_to_evaluate,
        )

        active_plan, plan_reason = self._form_plan(features.feature_summary)

        strategic = run_full_chess_goal_biased_strategic_search_kernel(
            memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        selected_move = strategic.selected_move
        selected_move_is_legal = selected_move in {m.uci() for m in board.legal_moves} if selected_move else True

        after_summary: Dict[str, Any] = {}
        if selected_move:
            board.push(chess.Move.from_uci(selected_move))
            after_features = run_full_chess_positional_strategy_features_kernel(
                memory_path=self.feature_memory_path,
                fen=board.fen(),
                analysed_side=side_to_evaluate,
            )
            after_summary = after_features.feature_summary
            board.pop()
        else:
            after_summary = dict(features.feature_summary)

        plan_followed, alignment_score, alignment_reasons = self._move_alignment(
            board=board,
            move_uci=selected_move,
            active_plan=active_plan,
            before_summary=features.feature_summary,
            after_summary=after_summary,
        ) if selected_move else (False, 0.0, ["no selected move"])

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "selected_move": selected_move,
            "active_plan": active_plan,
            "plan_reason": plan_reason,
            "plan_followed": plan_followed,
            "plan_alignment_score": alignment_score,
            "strategic_trace_hash": strategic.strategic_trace_hash,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = hashlib.sha256(json.dumps(trace_payload, sort_keys=True).encode("utf-8")).hexdigest()

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["plan_generation_count"] = int(self.policy.get("plan_generation_count", 0)) + 1
        self.policy["plan_follow_count"] = int(self.policy.get("plan_follow_count", 0)) + (1 if plan_followed else 0)
        self.policy["plan_break_count"] = int(self.policy.get("plan_break_count", 0)) + (0 if plan_followed else 1)
        self.policy["last_selected_move"] = selected_move
        self.policy["last_active_plan"] = active_plan
        self.policy["last_plan_followed"] = plan_followed
        self.policy["last_plan_alignment_score"] = alignment_score
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "simple_plan_formation_active": True,
            "plan_following_check_active": True,
            "strategic_search_consumed": True,
            "positional_features_consumed": True,
            "selected_move_is_legal": selected_move_is_legal,
            "plan_followed": plan_followed,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = SimplePlanFollowingResult(
            kernel_version="phase22e3_full_chess_simple_plan_following_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            planning_mode="simple_plan_formation_and_following",
            fen=fen,
            side_to_move=self._side_name(board.turn),
            side_to_evaluate=side_to_evaluate,
            selected_move=selected_move,
            selected_move_is_legal=selected_move_is_legal,
            selected_strategic_score=float(strategic.selected_strategic_score),
            selected_reason=strategic.selected_reason,
            active_plan=active_plan,
            plan_reason=plan_reason,
            plan_followed=plan_followed,
            plan_alignment_score=alignment_score,
            plan_alignment_reasons=alignment_reasons,
            base_positional_score=features.positional_score,
            feature_summary=features.feature_summary,
            strategic_search_trace_hash=strategic.strategic_trace_hash,
            plan_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_plan_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel forms a simple local chess plan from AION positional features and checks whether "
                "the goal-biased strategic move follows that plan. It does not use Stockfish, cloud engines, "
                "Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_simple_plan_following_kernel(
    *,
    memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_simple_plan_following",
) -> SimplePlanFollowingResult:
    return AionFullChessSimplePlanFollowingKernel(
        memory_path=memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        depth_limit=depth_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_simple_plan_following_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Simple plan-following memory saved to: {result.memory_path}")
