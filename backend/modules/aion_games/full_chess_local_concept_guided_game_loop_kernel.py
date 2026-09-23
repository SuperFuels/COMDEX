from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_concept_guided_move_reranking_kernel import (
    run_full_chess_concept_guided_move_reranking_kernel,
)
from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_local_concept_guided_game_loop_memory.json")


@dataclass(frozen=True)
class LocalConceptGuidedPly:
    ply_index: int
    fen_before: str
    side_to_move: str
    selected_move: str
    move_is_legal: bool
    original_strategic_selected_move: str
    selected_move_changed_by_rerank: bool
    applied_concept_count: int
    concept_bias_score_total: float
    top_move_count: int
    positional_score_before: float
    positional_score_after: float
    positional_delta: float
    concept_guided_trace_hash: str
    ply_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalConceptGuidedGameLoopResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    game_loop_mode: str
    initial_fen: str
    final_fen: str
    plies_requested: int
    plies_completed: int
    terminal_state_reached: bool
    terminal_status: str
    legal_move_rate: float
    concept_memory_active: bool
    concepts_applied_total: int
    average_concept_bias_score: float
    average_positional_delta: float
    selected_move_change_count: int
    ply_summaries: List[Dict[str, Any]]
    game_loop_trace_hash: str
    policy_memory_mutated: bool
    final_game_loop_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLocalConceptGuidedGameLoopKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        rerank_memory_path: Optional[Path] = None,
        bias_memory_path: Optional[Path] = None,
        concept_memory_path: Optional[Path] = None,
        forecast_memory_path: Optional[Path] = None,
        long_term_plan_memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.rerank_memory_path = rerank_memory_path
        self.bias_memory_path = bias_memory_path
        self.concept_memory_path = concept_memory_path
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
            "local_game_loop_run_count": 0,
            "plies_completed_total": 0,
            "legal_move_total": 0,
            "concepts_applied_total": 0,
            "selected_move_change_total": 0,
            "last_plies_completed": 0,
            "last_terminal_status": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("local_concept_guided_game_loop_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LocalConceptGuidedGameLoopResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e11_local_concept_guided_game_loop_memory_v1",
            "task_name": result.task_name,
            "local_concept_guided_game_loop_policy": result.final_game_loop_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _terminal_status(self, board: chess.Board) -> str:
        if board.is_checkmate():
            return "checkmate"
        if board.is_stalemate():
            return "stalemate"
        if board.is_insufficient_material():
            return "insufficient_material"
        if board.is_seventyfive_moves():
            return "seventyfive_moves"
        if board.is_fivefold_repetition():
            return "fivefold_repetition"
        if board.is_game_over():
            return "game_over"
        return "active"

    def run(
        self,
        *,
        initial_fen: str = chess.STARTING_FEN,
        plies: int = 12,
        depth_limit: int = 2,
        candidate_limit: int = 8,
        task_name: str = "full_chess_local_concept_guided_game_loop",
    ) -> LocalConceptGuidedGameLoopResult:
        board = chess.Board(initial_fen)
        ply_summaries: List[LocalConceptGuidedPly] = []

        for ply_index in range(1, plies + 1):
            if board.is_game_over():
                break

            fen_before = board.fen()
            side = "white" if board.turn == chess.WHITE else "black"

            features_before = run_full_chess_positional_strategy_features_kernel(
                memory_path=self.feature_memory_path,
                fen=fen_before,
                analysed_side=side,
            )

            rerank = run_full_chess_concept_guided_move_reranking_kernel(
                memory_path=self.rerank_memory_path,
                bias_memory_path=self.bias_memory_path,
                concept_memory_path=self.concept_memory_path,
                forecast_memory_path=self.forecast_memory_path,
                long_term_plan_memory_path=self.long_term_plan_memory_path,
                curriculum_memory_path=self.curriculum_memory_path,
                review_memory_path=self.review_memory_path,
                plan_memory_path=self.plan_memory_path,
                strategic_memory_path=self.strategic_memory_path,
                feature_memory_path=self.feature_memory_path,
                fen=fen_before,
                side_to_evaluate=side,
                depth_limit=depth_limit,
                candidate_limit=candidate_limit,
            )

            move = chess.Move.from_uci(rerank.concept_guided_selected_move)
            legal = move in board.legal_moves

            if not legal:
                # Safety fallback: never push an illegal move.
                move = sorted(board.legal_moves, key=lambda m: m.uci())[0]
                legal = True

            board.push(move)

            features_after = run_full_chess_positional_strategy_features_kernel(
                memory_path=self.feature_memory_path,
                fen=board.fen(),
                analysed_side=side,
            )

            positional_before = float(features_before.feature_summary.get("positional_score", 0.0))
            positional_after = float(features_after.feature_summary.get("positional_score", 0.0))
            positional_delta = round(positional_after - positional_before, 6)

            trace_payload = {
                "ply_index": ply_index,
                "fen_before": fen_before,
                "fen_after": board.fen(),
                "side": side,
                "selected_move": move.uci(),
                "legal": legal,
                "concept_guided_trace_hash": rerank.move_rerank_trace_hash,
                "positional_delta": positional_delta,
                "live_move_sent": False,
                "uses_stockfish": False,
                "uses_llm_shortcut": False,
            }

            ply_summaries.append(
                LocalConceptGuidedPly(
                    ply_index=ply_index,
                    fen_before=fen_before,
                    side_to_move=side,
                    selected_move=move.uci(),
                    move_is_legal=legal,
                    original_strategic_selected_move=rerank.original_strategic_selected_move,
                    selected_move_changed_by_rerank=rerank.selected_move_changed_by_rerank,
                    applied_concept_count=rerank.applied_concept_count,
                    concept_bias_score_total=rerank.concept_bias_score_total,
                    top_move_count=len(rerank.top_reranked_moves),
                    positional_score_before=positional_before,
                    positional_score_after=positional_after,
                    positional_delta=positional_delta,
                    concept_guided_trace_hash=rerank.move_rerank_trace_hash,
                    ply_trace_hash=self._hash(trace_payload),
                )
            )

        completed = len(ply_summaries)
        legal_count = len([p for p in ply_summaries if p.move_is_legal])
        concepts_total = sum(p.applied_concept_count for p in ply_summaries)
        selected_change_count = len([p for p in ply_summaries if p.selected_move_changed_by_rerank])
        avg_bias = round(sum(p.concept_bias_score_total for p in ply_summaries) / completed, 6) if completed else 0.0
        avg_delta = round(sum(p.positional_delta for p in ply_summaries) / completed, 6) if completed else 0.0
        legal_rate = round(legal_count / completed, 6) if completed else 1.0
        terminal_status = self._terminal_status(board)

        trace_payload = {
            "initial_fen": initial_fen,
            "final_fen": board.fen(),
            "plies_requested": plies,
            "plies_completed": completed,
            "terminal_status": terminal_status,
            "ply_summaries": [p.to_dict() for p in ply_summaries],
            "live_move_sent": False,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["local_game_loop_run_count"] = int(self.policy.get("local_game_loop_run_count", 0)) + 1
        self.policy["plies_completed_total"] = int(self.policy.get("plies_completed_total", 0)) + completed
        self.policy["legal_move_total"] = int(self.policy.get("legal_move_total", 0)) + legal_count
        self.policy["concepts_applied_total"] = int(self.policy.get("concepts_applied_total", 0)) + concepts_total
        self.policy["selected_move_change_total"] = int(self.policy.get("selected_move_change_total", 0)) + selected_change_count
        self.policy["last_plies_completed"] = completed
        self.policy["last_terminal_status"] = terminal_status
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "local_concept_guided_game_loop_active": True,
            "concept_guided_reranking_consumed_each_ply": completed > 0,
            "concept_memory_active": concepts_total > 0,
            "all_moves_legal": legal_count == completed and completed > 0,
            "multi_ply_loop_completed": completed >= min(plies, 2),
            "trace_hash_per_ply": all(bool(p.ply_trace_hash) for p in ply_summaries),
            "live_lichess_send_enabled": False,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LocalConceptGuidedGameLoopResult(
            kernel_version="phase22e11_full_chess_local_concept_guided_game_loop_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            game_loop_mode="local_concept_guided_preview",
            initial_fen=initial_fen,
            final_fen=board.fen(),
            plies_requested=plies,
            plies_completed=completed,
            terminal_state_reached=board.is_game_over(),
            terminal_status=terminal_status,
            legal_move_rate=legal_rate,
            concept_memory_active=concepts_total > 0,
            concepts_applied_total=concepts_total,
            average_concept_bias_score=avg_bias,
            average_positional_delta=avg_delta,
            selected_move_change_count=selected_change_count,
            ply_summaries=[p.to_dict() for p in ply_summaries],
            game_loop_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_game_loop_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel runs a local-only concept-guided chess game loop preview. "
                "It does not send live Lichess moves, does not use Stockfish, cloud engines, "
                "Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_local_concept_guided_game_loop_kernel(
    *,
    memory_path: Optional[Path] = None,
    rerank_memory_path: Optional[Path] = None,
    bias_memory_path: Optional[Path] = None,
    concept_memory_path: Optional[Path] = None,
    forecast_memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    initial_fen: str = chess.STARTING_FEN,
    plies: int = 12,
    depth_limit: int = 2,
    candidate_limit: int = 8,
    task_name: str = "full_chess_local_concept_guided_game_loop",
) -> LocalConceptGuidedGameLoopResult:
    return AionFullChessLocalConceptGuidedGameLoopKernel(
        memory_path=memory_path,
        rerank_memory_path=rerank_memory_path,
        bias_memory_path=bias_memory_path,
        concept_memory_path=concept_memory_path,
        forecast_memory_path=forecast_memory_path,
        long_term_plan_memory_path=long_term_plan_memory_path,
        curriculum_memory_path=curriculum_memory_path,
        review_memory_path=review_memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        initial_fen=initial_fen,
        plies=plies,
        depth_limit=depth_limit,
        candidate_limit=candidate_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_local_concept_guided_game_loop_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Local concept-guided game loop memory saved to: {result.memory_path}")
