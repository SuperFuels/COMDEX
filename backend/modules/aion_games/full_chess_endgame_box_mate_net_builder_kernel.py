from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_endgame_box_mate_net_builder_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass(frozen=True)
class MateNetCandidate:
    move: str
    is_legal: bool
    gives_check: bool
    gives_checkmate: bool
    enemy_king_square_after: str
    enemy_king_mobility_after: int
    enemy_king_edge_distance_after: int
    own_king_distance_after: int
    box_score: int
    repeated_move_penalty_applied: bool
    explanation: str


@dataclass(frozen=True)
class EndgameBoxMateNetBuilderResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    endgame_box_mate_net_active: bool
    detected_endgame_type: str
    candidate_count: int
    selected_move: str
    selected_move_is_legal: bool
    selected_score: int
    selected_explanation: str
    enemy_king_square_before: str
    enemy_king_mobility_before: int
    enemy_king_edge_distance_before: int
    own_king_distance_before: int
    top_candidates: List[Dict[str, Any]]
    trace_hash: str
    policy_memory_mutated: bool
    final_mate_net_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionEndgameBoxMateNetBuilderKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "mate_net_run_count": 0,
            "checkmate_selected_count": 0,
            "box_shrink_selected_count": 0,
            "last_selected_move": None,
            "last_detected_endgame_type": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("endgame_box_mate_net_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: EndgameBoxMateNetBuilderResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e31_endgame_box_mate_net_builder_memory_v1",
            "task_name": result.task_name,
            "endgame_box_mate_net_policy": result.final_mate_net_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _material_signature(self, board: chess.Board, side: chess.Color) -> Dict[str, int]:
        return {
            "queens": len(board.pieces(chess.QUEEN, side)),
            "rooks": len(board.pieces(chess.ROOK, side)),
            "bishops": len(board.pieces(chess.BISHOP, side)),
            "knights": len(board.pieces(chess.KNIGHT, side)),
            "pawns": len(board.pieces(chess.PAWN, side)),
        }

    def _detect_endgame_type(self, board: chess.Board, side: chess.Color) -> str:
        own = self._material_signature(board, side)
        enemy = self._material_signature(board, not side)

        enemy_material = sum(enemy.values())
        if own["queens"] >= 1 and enemy_material == 0:
            return "king_queen_vs_king"
        if own["rooks"] >= 1 and enemy_material == 0:
            return "king_rook_vs_king"
        if own["queens"] >= 1 and enemy_material <= 2:
            return "queen_conversion"
        if own["rooks"] >= 1 and enemy_material <= 2:
            return "rook_conversion"
        return "generic_endgame_or_not_forced"

    def _edge_distance(self, square: chess.Square) -> int:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        return min(file_idx, 7 - file_idx, rank_idx, 7 - rank_idx)

    def _king_mobility(self, board: chess.Board, colour: chess.Color) -> int:
        king = board.king(colour)
        if king is None:
            return 0

        count = 0
        for target in chess.SquareSet(chess.BB_KING_ATTACKS[king]):
            move = chess.Move(king, target)
            if move in board.legal_moves:
                count += 1
        return count

    def _own_king_distance_to_enemy(self, board: chess.Board, side: chess.Color) -> int:
        own_king = board.king(side)
        enemy_king = board.king(not side)
        if own_king is None or enemy_king is None:
            return 99
        return chess.square_distance(own_king, enemy_king)

    def _score_candidate(
        self,
        board: chess.Board,
        move: chess.Move,
        side: chess.Color,
        repeated_moves: List[str],
    ) -> MateNetCandidate:
        enemy = not side
        before_enemy_king = board.king(enemy)

        probe = board.copy(stack=False)
        probe.push(move)

        enemy_king = probe.king(enemy)
        enemy_square_name = chess.square_name(enemy_king) if enemy_king is not None else ""

        mobility = self._king_mobility(probe, enemy)
        edge_distance = self._edge_distance(enemy_king) if enemy_king is not None else 0
        own_king_distance = self._own_king_distance_to_enemy(probe, side)

        gives_check = probe.is_check()
        gives_checkmate = probe.is_checkmate()
        repeated = move.uci() in repeated_moves

        score = 0
        reasons: List[str] = []

        if gives_checkmate:
            score += 100000
            reasons.append("checkmate")

        if gives_check:
            score += 1000
            reasons.append("gives check")

        # Mate net objective: reduce king box, push to edge, bring own king closer.
        score += max(0, 8 - mobility) * 220
        reasons.append(f"enemy king mobility={mobility}")

        score += max(0, 4 - edge_distance) * 260
        reasons.append(f"enemy edge distance={edge_distance}")

        score += max(0, 8 - own_king_distance) * 80
        reasons.append(f"own king distance={own_king_distance}")

        # Reward direct reduction from before state.
        if before_enemy_king is not None and enemy_king is not None:
            before_edge = self._edge_distance(before_enemy_king)
            if edge_distance < before_edge:
                score += 500
                reasons.append("shrinks box toward edge")

        if repeated:
            score -= 900
            reasons.append("repeated move penalty")

        # Prefer major-piece moves only when they shrink the box or check.
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in (chess.QUEEN, chess.ROOK):
            score += 120
            reasons.append("major-piece box control")

        score += 10 - (move.from_square % 5) - (move.to_square % 5)

        return MateNetCandidate(
            move=move.uci(),
            is_legal=True,
            gives_check=gives_check,
            gives_checkmate=gives_checkmate,
            enemy_king_square_after=enemy_square_name,
            enemy_king_mobility_after=mobility,
            enemy_king_edge_distance_after=edge_distance,
            own_king_distance_after=own_king_distance,
            box_score=score,
            repeated_move_penalty_applied=repeated,
            explanation="; ".join(reasons),
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        task_name: str = "full_chess_endgame_box_mate_net_builder",
    ) -> EndgameBoxMateNetBuilderResult:
        repeated_moves = list(repeated_moves or [])

        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        enemy = not side
        enemy_king = board.king(enemy)
        enemy_king_square = chess.square_name(enemy_king) if enemy_king is not None else ""

        mobility_before = self._king_mobility(board, enemy)
        edge_before = self._edge_distance(enemy_king) if enemy_king is not None else 0
        own_king_distance_before = self._own_king_distance_to_enemy(board, side)

        endgame_type = self._detect_endgame_type(board, side)

        candidates = [
            self._score_candidate(board, move, side, repeated_moves)
            for move in board.legal_moves
        ]
        candidates.sort(
            key=lambda c: (
                c.box_score,
                -c.enemy_king_mobility_after,
                -c.enemy_king_edge_distance_after,
                c.move,
            ),
            reverse=True,
        )

        selected = candidates[0] if candidates else None

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "detected_endgame_type": endgame_type,
            "selected_move": selected.move if selected else "",
            "selected_score": selected.box_score if selected else 0,
            "enemy_king_mobility_before": mobility_before,
            "enemy_king_edge_distance_before": edge_before,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["mate_net_run_count"] = int(self.policy.get("mate_net_run_count", 0)) + 1
        self.policy["last_selected_move"] = selected.move if selected else ""
        self.policy["last_detected_endgame_type"] = endgame_type
        self.policy["last_trace_hash"] = trace_hash
        if selected and selected.gives_checkmate:
            self.policy["checkmate_selected_count"] = int(self.policy.get("checkmate_selected_count", 0)) + 1
        elif selected:
            self.policy["box_shrink_selected_count"] = int(self.policy.get("box_shrink_selected_count", 0)) + 1

        evidence = {
            "endgame_box_mate_net_active": True,
            "enemy_king_mobility_scored": True,
            "enemy_king_edge_distance_scored": True,
            "own_king_distance_scored": True,
            "box_shrink_scored": True,
            "checkmate_prioritised": True,
            "repetition_penalty_enabled": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = EndgameBoxMateNetBuilderResult(
            kernel_version="phase22e31_full_chess_endgame_box_mate_net_builder_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            endgame_box_mate_net_active=True,
            detected_endgame_type=endgame_type,
            candidate_count=len(candidates),
            selected_move=selected.move if selected else "",
            selected_move_is_legal=bool(selected and selected.is_legal),
            selected_score=selected.box_score if selected else 0,
            selected_explanation=selected.explanation if selected else "",
            enemy_king_square_before=enemy_king_square,
            enemy_king_mobility_before=mobility_before,
            enemy_king_edge_distance_before=edge_before,
            own_king_distance_before=own_king_distance_before,
            top_candidates=[asdict(c) for c in candidates[:8]],
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_mate_net_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements an endgame box and mate-net builder. It scores legal moves by enemy king "
                "mobility reduction, edge pressure, own king support, check pressure, and checkmate priority. It does "
                "not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_endgame_box_mate_net_builder_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_endgame_box_mate_net_builder",
) -> EndgameBoxMateNetBuilderResult:
    return AionEndgameBoxMateNetBuilderKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        repeated_moves=["d6b8", "b8d6"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Endgame box/mate-net memory saved to: {result.memory_path}")
