from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_queen_endgame_mate_conversion_memory.json")


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass(frozen=True)
class QueenEndgameMoveCandidate:
    move: str
    score: int
    is_checkmate: bool
    gives_check: bool
    is_capture: bool
    captured_piece_type: Optional[str]
    enemy_king_mobility_after: int
    queen_enemy_king_distance_after: int
    repeat_penalty_applied: bool
    explanation: str


@dataclass(frozen=True)
class QueenEndgameMateConversionResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    conversion_mode: str
    input_fen: str
    side_to_move: str
    queen_endgame_conversion_active: bool
    selected_move: str
    selected_move_is_legal: bool
    selected_score: int
    selected_explanation: str
    candidate_count: int
    top_candidates: List[Dict[str, Any]]
    repeated_move_penalty_active: bool
    repeated_queen_square_penalty_active: bool
    clock_pressure_active: bool
    trace_hash: str
    policy_memory_mutated: bool
    final_conversion_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionQueenEndgameMateConversionKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "conversion_run_count": 0,
            "conversion_active_count": 0,
            "last_selected_move": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("queen_endgame_conversion_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: QueenEndgameMateConversionResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e20_queen_endgame_mate_conversion_memory_v1",
            "task_name": result.task_name,
            "queen_endgame_conversion_policy": result.final_conversion_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _material_score(self, board: chess.Board, color: chess.Color) -> int:
        total = 0
        for piece_type, value in PIECE_VALUES.items():
            total += len(board.pieces(piece_type, color)) * value
        return total

    def _square_distance(self, a: chess.Square, b: chess.Square) -> int:
        return max(
            abs(chess.square_file(a) - chess.square_file(b)),
            abs(chess.square_rank(a) - chess.square_rank(b)),
        )

    def _king_square(self, board: chess.Board, color: chess.Color) -> chess.Square:
        king = board.king(color)
        if king is None:
            raise ValueError("Board has no king for requested colour")
        return king

    def _queen_endgame_active(self, board: chess.Board, color: chess.Color) -> bool:
        enemy = not color
        own_queens = len(board.pieces(chess.QUEEN, color))
        enemy_queens = len(board.pieces(chess.QUEEN, enemy))
        own_material = self._material_score(board, color)
        enemy_material = self._material_score(board, enemy)

        return (
            own_queens >= 1
            and enemy_queens == 0
            and own_material >= enemy_material
            and board.turn == color
        )

    def _score_move(
        self,
        board: chess.Board,
        move: chess.Move,
        *,
        color: chess.Color,
        repeated_moves: List[str],
        repeated_queen_squares: List[str],
        recent_fens: List[str],
        clock_pressure_active: bool,
    ) -> QueenEndgameMoveCandidate:
        enemy = not color
        score = 0
        reasons: List[str] = []

        moving_piece = board.piece_at(move.from_square)
        captured_piece = board.piece_at(move.to_square)

        is_capture = board.is_capture(move)
        gives_check = board.gives_check(move)

        if captured_piece:
            capture_score = PIECE_VALUES.get(captured_piece.piece_type, 0)
            score += capture_score
            reasons.append(f"captures {captured_piece.symbol()} worth {capture_score}")

            if captured_piece.piece_type == chess.ROOK:
                score += 900
                reasons.append("high priority rook capture while winning")

        if gives_check:
            score += 550
            reasons.append("gives check")

        if move.promotion == chess.QUEEN:
            score += 800
            reasons.append("promotes to queen")

        board_after = board.copy(stack=False)
        board_after.push(move)

        is_checkmate = board_after.is_checkmate()
        if is_checkmate:
            score += 100000
            reasons.append("checkmate")

        enemy_mobility_after = board_after.legal_moves.count()
        mobility_pressure = max(0, 30 - enemy_mobility_after) * 20
        score += mobility_pressure
        reasons.append(f"enemy king/side mobility after={enemy_mobility_after}")

        enemy_king_after = self._king_square(board_after, enemy)

        queen_squares_after = list(board_after.pieces(chess.QUEEN, color))
        queen_distance_after = 8
        if queen_squares_after:
            queen_distance_after = min(self._square_distance(q, enemy_king_after) for q in queen_squares_after)
            distance_score = max(0, 8 - queen_distance_after) * 35
            score += distance_score
            reasons.append(f"queen enemy-king distance={queen_distance_after}")

        own_king_after = self._king_square(board_after, color)
        own_king_distance_after = self._square_distance(own_king_after, enemy_king_after)
        king_support_score = max(0, 8 - own_king_distance_after) * 15
        score += king_support_score
        reasons.append(f"own king support distance={own_king_distance_after}")

        repeat_penalty = False

        move_uci = move.uci()
        if move_uci in repeated_moves:
            score -= 2000
            repeat_penalty = True
            reasons.append("penalised repeated move")

        if moving_piece and moving_piece.piece_type == chess.QUEEN:
            to_name = chess.square_name(move.to_square)
            if to_name in repeated_queen_squares:
                score -= 1800
                repeat_penalty = True
                reasons.append("penalised repeated queen square")

            if not gives_check and not is_capture and not is_checkmate:
                score -= 200
                reasons.append("queen quiet move penalty")

        fen_key = board_after.board_fen()
        if fen_key in recent_fens:
            score -= 2500
            repeat_penalty = True
            reasons.append("penalised repeated board pattern")

        if clock_pressure_active:
            if gives_check:
                score += 450
                reasons.append("clock pressure check bonus")
            if is_capture:
                score += 300
                reasons.append("clock pressure capture bonus")
            if not gives_check and not is_capture and not is_checkmate:
                score -= 500
                reasons.append("clock pressure quiet move penalty")

        return QueenEndgameMoveCandidate(
            move=move_uci,
            score=score,
            is_checkmate=is_checkmate,
            gives_check=gives_check,
            is_capture=is_capture,
            captured_piece_type=chess.piece_name(captured_piece.piece_type) if captured_piece else None,
            enemy_king_mobility_after=enemy_mobility_after,
            queen_enemy_king_distance_after=queen_distance_after,
            repeat_penalty_applied=repeat_penalty,
            explanation="; ".join(reasons),
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        repeated_queen_squares: Optional[List[str]] = None,
        recent_fens: Optional[List[str]] = None,
        clock_seconds_remaining: Optional[float] = None,
        clock_pressure_threshold_seconds: float = 60.0,
        task_name: str = "full_chess_queen_endgame_mate_conversion",
    ) -> QueenEndgameMateConversionResult:
        board = chess.Board(input_fen)
        color = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK

        repeated_moves = list(repeated_moves or [])
        repeated_queen_squares = list(repeated_queen_squares or [])
        recent_fens = list(recent_fens or [])

        clock_pressure_active = (
            clock_seconds_remaining is not None
            and float(clock_seconds_remaining) <= float(clock_pressure_threshold_seconds)
        )

        active = self._queen_endgame_active(board, color)

        candidates: List[QueenEndgameMoveCandidate] = []
        if active:
            for move in board.legal_moves:
                candidates.append(
                    self._score_move(
                        board,
                        move,
                        color=color,
                        repeated_moves=repeated_moves,
                        repeated_queen_squares=repeated_queen_squares,
                        recent_fens=recent_fens,
                        clock_pressure_active=clock_pressure_active,
                    )
                )

        candidates.sort(key=lambda c: c.score, reverse=True)

        selected = candidates[0] if candidates else QueenEndgameMoveCandidate(
            move="",
            score=0,
            is_checkmate=False,
            gives_check=False,
            is_capture=False,
            captured_piece_type=None,
            enemy_king_mobility_after=0,
            queen_enemy_king_distance_after=0,
            repeat_penalty_applied=False,
            explanation="queen endgame conversion inactive",
        )

        selected_is_legal = bool(selected.move) and chess.Move.from_uci(selected.move) in board.legal_moves

        top_candidates = [asdict(c) for c in candidates[:8]]

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "active": active,
            "selected_move": selected.move,
            "selected_score": selected.score,
            "top_candidates": top_candidates,
            "repeated_moves": repeated_moves,
            "repeated_queen_squares": repeated_queen_squares,
            "clock_pressure_active": clock_pressure_active,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["conversion_run_count"] = int(self.policy.get("conversion_run_count", 0)) + 1
        self.policy["conversion_active_count"] = int(self.policy.get("conversion_active_count", 0)) + (1 if active else 0)
        self.policy["last_selected_move"] = selected.move
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "queen_endgame_conversion_active": active,
            "selected_move_is_legal": selected_is_legal,
            "mate_priority_enabled": True,
            "check_priority_enabled": True,
            "enemy_king_mobility_reduction_enabled": True,
            "queen_king_distance_enabled": True,
            "own_king_support_enabled": True,
            "capture_rook_when_winning_enabled": True,
            "repetition_memory_penalty_enabled": True,
            "clock_pressure_override_enabled": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = QueenEndgameMateConversionResult(
            kernel_version="phase22e20_full_chess_queen_endgame_mate_conversion_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            conversion_mode="queen_endgame_mate_conversion",
            input_fen=input_fen,
            side_to_move=side_to_move,
            queen_endgame_conversion_active=active,
            selected_move=selected.move,
            selected_move_is_legal=selected_is_legal,
            selected_score=selected.score,
            selected_explanation=selected.explanation,
            candidate_count=len(candidates),
            top_candidates=top_candidates,
            repeated_move_penalty_active=bool(repeated_moves),
            repeated_queen_square_penalty_active=bool(repeated_queen_squares),
            clock_pressure_active=clock_pressure_active,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_conversion_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel patches the Phase 22E.18 queen-endgame failure mode. "
                "It performs deterministic local legal-move scoring only. It does not call Lichess, "
                "does not send moves, does not use Stockfish, does not use LLM move judgement, "
                "and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_queen_endgame_mate_conversion_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    repeated_queen_squares: Optional[List[str]] = None,
    recent_fens: Optional[List[str]] = None,
    clock_seconds_remaining: Optional[float] = None,
    clock_pressure_threshold_seconds: float = 60.0,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_queen_endgame_mate_conversion",
) -> QueenEndgameMateConversionResult:
    return AionQueenEndgameMateConversionKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_queen_squares=repeated_queen_squares,
        recent_fens=recent_fens,
        clock_seconds_remaining=clock_seconds_remaining,
        clock_pressure_threshold_seconds=clock_pressure_threshold_seconds,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=["d6b8", "b8d6"],
        repeated_queen_squares=["b8", "d6"],
        clock_seconds_remaining=30,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Queen endgame mate conversion memory saved to: {result.memory_path}")
