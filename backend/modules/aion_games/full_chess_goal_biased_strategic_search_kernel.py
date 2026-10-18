from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess

from .full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_goal_biased_strategic_search_memory.json")


@dataclass(frozen=True)
class GoalBiasedStrategicCandidate:
    move: str
    strategic_score: float
    positional_score_after_move: int
    positional_delta: int
    goal_bias_score: float
    searched_depth: int
    principal_reply: str
    gives_check: bool
    is_capture: bool
    is_castle: bool
    is_checkmate: bool
    feature_summary_after_move: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoalBiasedStrategicSearchResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    search_mode: str
    fen: str
    side_to_move: str
    side_to_evaluate: str
    depth_limit: int
    legal_move_count: int
    selected_move: str
    selected_strategic_score: float
    selected_reason: str
    searched_node_count: int
    leaf_feature_evaluation_count: int
    terminal_node_count: int
    candidate_count: int
    top_candidate_lines: List[Dict[str, Any]]
    base_positional_score: int
    active_goal_biases: Dict[str, float]
    strategic_trace_hash: str
    policy_memory_mutated: bool
    final_strategic_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessGoalBiasedStrategicSearchKernel:
    def __init__(self, memory_path: Optional[Path] = None, feature_memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "strategic_search_count": 0,
            "searched_node_total": 0,
            "leaf_feature_evaluation_total": 0,
            "terminal_node_total": 0,
            "last_selected_move": None,
            "last_selected_strategic_score": None,
            "last_trace_hash": None,
            "goal_biases": {
                "defend_king": 1.4,
                "stop_promotion": 1.8,
                "reduce_invasion": 1.5,
                "reduce_repetition": 1.0,
                "improve_piece_activity": 0.45,
                "improve_centre_control": 0.35,
                "improve_passed_pawns": 0.55,
            },
        }
        self._load_memory()

        self.searched_node_count = 0
        self.leaf_feature_evaluation_count = 0
        self.terminal_node_count = 0

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("goal_biased_strategic_search_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: GoalBiasedStrategicSearchResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e2_goal_biased_strategic_search_memory_v1",
            "task_name": result.task_name,
            "goal_biased_strategic_search_policy": result.final_strategic_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _side_name(self, colour: chess.Color) -> str:
        return "white" if colour == chess.WHITE else "black"

    def _feature_eval(self, board: chess.Board, side_to_evaluate: str):
        self.leaf_feature_evaluation_count += 1
        return run_full_chess_positional_strategy_features_kernel(
            memory_path=self.feature_memory_path,
            fen=board.fen(),
            analysed_side=side_to_evaluate,
        )

    def _terminal_score(self, board: chess.Board, side_to_evaluate: str) -> Optional[float]:
        side = chess.WHITE if side_to_evaluate == "white" else chess.BLACK
        if board.is_checkmate():
            self.terminal_node_count += 1
            return -100000.0 if board.turn == side else 100000.0
        if board.is_stalemate() or board.is_insufficient_material():
            self.terminal_node_count += 1
            return 0.0
        return None

    def _goal_bias_score(self, feature_summary: Dict[str, Any]) -> float:
        weights = dict(self.policy["goal_biases"])
        return float(
            feature_summary.get("king_safety_score", 0) * weights["defend_king"]
            + feature_summary.get("promotion_danger_penalty", 0) * weights["stop_promotion"]
            + feature_summary.get("invasion_risk_penalty", 0) * weights["reduce_invasion"]
            + feature_summary.get("repetition_risk_penalty", 0) * weights["reduce_repetition"]
            + feature_summary.get("piece_activity_score", 0) * weights["improve_piece_activity"]
            + feature_summary.get("centre_control_score", 0) * weights["improve_centre_control"]
            + feature_summary.get("passed_pawn_score", 0) * weights["improve_passed_pawns"]
        )

    def _leaf_score(self, board: chess.Board, side_to_evaluate: str) -> float:
        features = self._feature_eval(board, side_to_evaluate)
        return float(features.positional_score + self._goal_bias_score(features.feature_summary))

    def _minimax(
        self,
        board: chess.Board,
        *,
        depth: int,
        side_to_evaluate: str,
        alpha: float,
        beta: float,
    ) -> Tuple[float, str]:
        self.searched_node_count += 1

        terminal = self._terminal_score(board, side_to_evaluate)
        if terminal is not None:
            return terminal, ""

        if depth <= 0:
            return self._leaf_score(board, side_to_evaluate), ""

        legal_moves = sorted(list(board.legal_moves), key=lambda m: m.uci())
        if not legal_moves:
            return self._leaf_score(board, side_to_evaluate), ""

        maximizing = self._side_name(board.turn) == side_to_evaluate
        best_move = ""

        if maximizing:
            best_score = -1_000_000.0
            for move in legal_moves:
                board.push(move)
                score, _ = self._minimax(
                    board,
                    depth=depth - 1,
                    side_to_evaluate=side_to_evaluate,
                    alpha=alpha,
                    beta=beta,
                )
                board.pop()

                if score > best_score or (score == best_score and move.uci() > best_move):
                    best_score = score
                    best_move = move.uci()

                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break

            return best_score, best_move

        best_score = 1_000_000.0
        for move in legal_moves:
            board.push(move)
            score, _ = self._minimax(
                board,
                depth=depth - 1,
                side_to_evaluate=side_to_evaluate,
                alpha=alpha,
                beta=beta,
            )
            board.pop()

            if score < best_score or (score == best_score and move.uci() < best_move):
                best_score = score
                best_move = move.uci()

            beta = min(beta, best_score)
            if beta <= alpha:
                break

        return best_score, best_move

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_goal_biased_strategic_search",
    ) -> GoalBiasedStrategicSearchResult:
        board = chess.Board(fen)
        side_to_evaluate = side_to_evaluate.lower()
        base_features = self._feature_eval(board, side_to_evaluate)
        legal_moves = sorted(list(board.legal_moves), key=lambda m: m.uci())

        candidates: List[GoalBiasedStrategicCandidate] = []

        if board.is_game_over() or not legal_moves:
            selected_move = ""
            selected_score = 0.0
            selected_reason = "terminal_or_no_legal_move"
        else:
            for move in legal_moves:
                board.push(move)
                terminal = self._terminal_score(board, side_to_evaluate)
                if terminal is None:
                    line_score, principal_reply = self._minimax(
                        board,
                        depth=max(0, depth_limit - 1),
                        side_to_evaluate=side_to_evaluate,
                        alpha=-1_000_000.0,
                        beta=1_000_000.0,
                    )
                else:
                    line_score, principal_reply = terminal, ""

                after_features = self._feature_eval(board, side_to_evaluate)
                goal_bias = self._goal_bias_score(after_features.feature_summary)
                positional_delta = after_features.positional_score - base_features.positional_score
                strategic_score = float(line_score + goal_bias + positional_delta * 0.4)

                candidates.append(
                    GoalBiasedStrategicCandidate(
                        move=move.uci(),
                        strategic_score=round(strategic_score, 6),
                        positional_score_after_move=after_features.positional_score,
                        positional_delta=positional_delta,
                        goal_bias_score=round(goal_bias, 6),
                        searched_depth=depth_limit,
                        principal_reply=principal_reply,
                        gives_check=board.gives_check(move) if move in board.legal_moves else False,
                        is_capture=board.is_capture(move) if move in board.legal_moves else False,
                        is_castle=board.is_castling(move) if move in board.legal_moves else False,
                        is_checkmate=board.is_checkmate(),
                        feature_summary_after_move=after_features.feature_summary,
                    )
                )
                board.pop()

            candidates.sort(key=lambda c: (c.strategic_score, c.move), reverse=True)
            selected = candidates[0]
            selected_move = selected.move
            selected_score = selected.strategic_score
            selected_reason = "goal_biased_multi_ply_strategic_selection"

        top_lines = [c.to_dict() for c in candidates[:8]]

        trace_payload = {
            "fen": board.fen(),
            "side_to_evaluate": side_to_evaluate,
            "depth_limit": depth_limit,
            "selected_move": selected_move,
            "selected_score": selected_score,
            "top_lines": top_lines,
            "goal_biases": self.policy["goal_biases"],
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = hashlib.sha256(json.dumps(trace_payload, sort_keys=True).encode("utf-8")).hexdigest()

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["strategic_search_count"] = int(self.policy.get("strategic_search_count", 0)) + 1
        self.policy["searched_node_total"] = int(self.policy.get("searched_node_total", 0)) + self.searched_node_count
        self.policy["leaf_feature_evaluation_total"] = int(self.policy.get("leaf_feature_evaluation_total", 0)) + self.leaf_feature_evaluation_count
        self.policy["terminal_node_total"] = int(self.policy.get("terminal_node_total", 0)) + self.terminal_node_count
        self.policy["last_selected_move"] = selected_move
        self.policy["last_selected_strategic_score"] = selected_score
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "goal_biased_strategic_search_active": True,
            "multi_ply_search_active": depth_limit >= 2,
            "positional_features_consumed": True,
            "goal_bias_active": True,
            "king_safety_goal_active": True,
            "promotion_defence_goal_active": True,
            "invasion_reduction_goal_active": True,
            "repetition_reduction_goal_active": True,
            "selected_move_is_legal": selected_move in {m.uci() for m in board.legal_moves} if selected_move else True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = GoalBiasedStrategicSearchResult(
            kernel_version="phase22e2_full_chess_goal_biased_strategic_search_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            search_mode="goal_biased_multi_ply_strategic_search",
            fen=board.fen(),
            side_to_move=self._side_name(board.turn),
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
            legal_move_count=len(legal_moves),
            selected_move=selected_move,
            selected_strategic_score=float(selected_score),
            selected_reason=selected_reason,
            searched_node_count=self.searched_node_count,
            leaf_feature_evaluation_count=self.leaf_feature_evaluation_count,
            terminal_node_count=self.terminal_node_count,
            candidate_count=len(candidates),
            top_candidate_lines=top_lines,
            base_positional_score=base_features.positional_score,
            active_goal_biases=dict(self.policy["goal_biases"]),
            strategic_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_strategic_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel performs deterministic multi-ply strategic search using AION positional features "
                "and local goal bias. It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, "
                "or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_goal_biased_strategic_search_kernel(
    *,
    memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_goal_biased_strategic_search",
) -> GoalBiasedStrategicSearchResult:
    return AionFullChessGoalBiasedStrategicSearchKernel(
        memory_path=memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        depth_limit=depth_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_goal_biased_strategic_search_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Goal-biased strategic search memory saved to: {result.memory_path}")
