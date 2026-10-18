from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_simple_plan_following_kernel import (
    run_full_chess_simple_plan_following_kernel,
)
from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_post_game_strategic_review_policy_memory.json")


@dataclass(frozen=True)
class PostGameStrategicReviewPolicyResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    review_mode: str
    game_id: str
    final_status: str
    winner: str
    aion_colour: str
    initial_fen: str
    final_fen: str
    analysed_side: str
    selected_move: str
    plan_followed: bool
    plan_alignment_score: float
    active_plan: List[str]
    strategic_failure_modes: List[str]
    policy_updates: Dict[str, Any]
    policy_update_count: int
    initial_positional_score: int
    final_positional_score: int
    positional_delta: int
    review_trace_hash: str
    policy_memory_mutated: bool
    final_review_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessPostGameStrategicReviewPolicyKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "strategic_review_count": 0,
            "policy_update_total": 0,
            "mate_loss_review_count": 0,
            "plan_break_review_count": 0,
            "positional_decline_review_count": 0,
            "last_game_id": None,
            "last_policy_updates": {},
            "last_trace_hash": None,
            "learned_policy_updates": {
                "increase_king_safety_goal_bias_after_mate_loss": False,
                "increase_promotion_defence_after_unstopped_pawn": False,
                "increase_invasion_reduction_after_back_rank_penetration": False,
                "increase_plan_following_penalty_after_plan_break": False,
                "increase_positional_delta_weight_after_decline": False,
                "prefer_simplification_when_losing": True,
            },
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("post_game_strategic_review_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PostGameStrategicReviewPolicyResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e4_post_game_strategic_review_policy_memory_v1",
            "task_name": result.task_name,
            "post_game_strategic_review_policy": result.final_review_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _detect_failure_modes(
        self,
        *,
        final_status: str,
        winner: str,
        aion_colour: str,
        plan_followed: bool,
        plan_alignment_score: float,
        positional_delta: int,
        final_summary: Dict[str, Any],
    ) -> List[str]:
        failures: List[str] = []
        aion_lost = bool(winner) and winner.lower() != aion_colour.lower()

        if final_status.lower() == "mate" and aion_lost:
            failures.append("mate_loss")

        if not plan_followed or plan_alignment_score <= 0:
            failures.append("plan_not_followed")

        if positional_delta < -100:
            failures.append("positional_decline")

        if final_summary.get("king_safety_score", 0) < 40:
            failures.append("king_safety_failure")

        if final_summary.get("promotion_danger_penalty", 0) < 0:
            failures.append("promotion_danger_unresolved")

        if final_summary.get("invasion_risk_penalty", 0) < 0:
            failures.append("invasion_risk_unresolved")

        if final_summary.get("repetition_risk_penalty", 0) < 0:
            failures.append("repetition_risk_unresolved")

        if not failures:
            failures.append("no_major_strategic_failure_detected")

        return failures

    def _policy_updates_from_failures(self, failures: List[str]) -> Dict[str, Any]:
        updates = dict(self.policy["learned_policy_updates"])

        if "mate_loss" in failures or "king_safety_failure" in failures:
            updates["increase_king_safety_goal_bias_after_mate_loss"] = True

        if "promotion_danger_unresolved" in failures:
            updates["increase_promotion_defence_after_unstopped_pawn"] = True

        if "invasion_risk_unresolved" in failures:
            updates["increase_invasion_reduction_after_back_rank_penetration"] = True

        if "plan_not_followed" in failures:
            updates["increase_plan_following_penalty_after_plan_break"] = True

        if "positional_decline" in failures:
            updates["increase_positional_delta_weight_after_decline"] = True

        updates["prefer_simplification_when_losing"] = True
        return updates

    def run(
        self,
        *,
        game_id: str = "phase22e4_synthetic_review_game",
        initial_fen: str = chess.STARTING_FEN,
        final_fen: str = "4k3/8/8/8/8/8/6q1/4K3 w - - 0 1",
        final_status: str = "mate",
        winner: str = "black",
        aion_colour: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_post_game_strategic_review_policy",
    ) -> PostGameStrategicReviewPolicyResult:
        analysed_side = aion_colour.lower()

        initial_features = run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=initial_fen,
            analysed_side=analysed_side,
        )

        final_features = run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=final_fen,
            analysed_side=analysed_side,
        )

        plan = run_full_chess_simple_plan_following_kernel(
            memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=initial_fen,
            side_to_evaluate=analysed_side,
            depth_limit=depth_limit,
        )

        positional_delta = final_features.positional_score - initial_features.positional_score

        failures = self._detect_failure_modes(
            final_status=final_status,
            winner=winner,
            aion_colour=aion_colour,
            plan_followed=plan.plan_followed,
            plan_alignment_score=plan.plan_alignment_score,
            positional_delta=positional_delta,
            final_summary=final_features.feature_summary,
        )

        policy_updates = self._policy_updates_from_failures(failures)
        update_count = sum(1 for value in policy_updates.values() if bool(value))

        trace_payload = {
            "game_id": game_id,
            "initial_fen": initial_fen,
            "final_fen": final_fen,
            "final_status": final_status,
            "winner": winner,
            "aion_colour": aion_colour,
            "selected_move": plan.selected_move,
            "active_plan": plan.active_plan,
            "plan_followed": plan.plan_followed,
            "positional_delta": positional_delta,
            "failures": failures,
            "policy_updates": policy_updates,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = hashlib.sha256(json.dumps(trace_payload, sort_keys=True).encode("utf-8")).hexdigest()

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["strategic_review_count"] = int(self.policy.get("strategic_review_count", 0)) + 1
        self.policy["policy_update_total"] = int(self.policy.get("policy_update_total", 0)) + update_count
        self.policy["mate_loss_review_count"] = int(self.policy.get("mate_loss_review_count", 0)) + (1 if "mate_loss" in failures else 0)
        self.policy["plan_break_review_count"] = int(self.policy.get("plan_break_review_count", 0)) + (1 if "plan_not_followed" in failures else 0)
        self.policy["positional_decline_review_count"] = int(self.policy.get("positional_decline_review_count", 0)) + (1 if "positional_decline" in failures else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_policy_updates"] = policy_updates
        self.policy["learned_policy_updates"] = policy_updates
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "post_game_strategic_review_active": True,
            "policy_update_active": True,
            "plan_following_reviewed": True,
            "positional_delta_reviewed": True,
            "failure_modes_detected": True,
            "selected_move_reviewed": bool(plan.selected_move),
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PostGameStrategicReviewPolicyResult(
            kernel_version="phase22e4_full_chess_post_game_strategic_review_policy_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            review_mode="post_game_strategic_review_and_policy_update",
            game_id=game_id,
            final_status=final_status,
            winner=winner,
            aion_colour=aion_colour,
            initial_fen=initial_fen,
            final_fen=final_fen,
            analysed_side=analysed_side,
            selected_move=plan.selected_move,
            plan_followed=plan.plan_followed,
            plan_alignment_score=plan.plan_alignment_score,
            active_plan=plan.active_plan,
            strategic_failure_modes=failures,
            policy_updates=policy_updates,
            policy_update_count=update_count,
            initial_positional_score=initial_features.positional_score,
            final_positional_score=final_features.positional_score,
            positional_delta=positional_delta,
            review_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_review_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel performs post-game strategic review and emits local policy updates from AION chess telemetry. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_post_game_strategic_review_policy_kernel(
    *,
    memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    game_id: str = "phase22e4_synthetic_review_game",
    initial_fen: str = chess.STARTING_FEN,
    final_fen: str = "4k3/8/8/8/8/8/6q1/4K3 w - - 0 1",
    final_status: str = "mate",
    winner: str = "black",
    aion_colour: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_post_game_strategic_review_policy",
) -> PostGameStrategicReviewPolicyResult:
    return AionFullChessPostGameStrategicReviewPolicyKernel(
        memory_path=memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        game_id=game_id,
        initial_fen=initial_fen,
        final_fen=final_fen,
        final_status=final_status,
        winner=winner,
        aion_colour=aion_colour,
        depth_limit=depth_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_post_game_strategic_review_policy_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Post-game strategic review policy memory saved to: {result.memory_path}")
