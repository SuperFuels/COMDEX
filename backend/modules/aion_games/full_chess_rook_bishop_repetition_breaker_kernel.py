from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_rook_bishop_repetition_breaker_memory.json")


@dataclass(frozen=True)
class RepetitionBreakCandidate:
    move: str
    is_legal: bool
    piece_type: str
    from_square: str
    to_square: str
    is_capture: bool
    gives_check: bool
    is_pawn_move: bool
    changes_piece_square_pattern: bool
    repeated_move_penalty_applied: bool
    repeated_square_penalty_applied: bool
    irreversible_progress: bool
    breaker_score: int
    explanation: str


@dataclass(frozen=True)
class RookBishopRepetitionBreakerResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    repetition_breaker_active: bool
    repeated_moves: List[str]
    repeated_squares: List[str]
    repetition_detected: bool
    candidate_count: int
    selected_breaker_move: str
    selected_breaker_move_is_legal: bool
    selected_score: int
    selected_explanation: str
    top_candidates: List[Dict[str, Any]]
    trace_hash: str
    policy_memory_mutated: bool
    final_breaker_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionRookBishopRepetitionBreakerKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "repetition_breaker_run_count": 0,
            "repetition_detected_count": 0,
            "breaker_move_selected_count": 0,
            "last_selected_breaker_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("rook_bishop_repetition_breaker_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: RookBishopRepetitionBreakerResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e33_rook_bishop_repetition_breaker_memory_v1",
            "task_name": result.task_name,
            "rook_bishop_repetition_breaker_policy": result.final_breaker_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _detect_repetition(self, repeated_moves: List[str], repeated_squares: List[str]) -> bool:
        if len(repeated_moves) >= 4:
            recent = repeated_moves[-4:]
            if recent[0] == recent[2] or recent[1] == recent[3]:
                return True
        if len(repeated_squares) >= 4:
            recent_sq = repeated_squares[-4:]
            if recent_sq[0] == recent_sq[2] or recent_sq[1] == recent_sq[3]:
                return True
        return bool(repeated_moves or repeated_squares)

    def _piece_name(self, piece: Optional[chess.Piece]) -> str:
        if piece is None:
            return "none"
        return chess.piece_name(piece.piece_type)

    def _score_move(
        self,
        board: chess.Board,
        move: chess.Move,
        repeated_moves: List[str],
        repeated_squares: List[str],
    ) -> RepetitionBreakCandidate:
        piece = board.piece_at(move.from_square)
        piece_type = self._piece_name(piece)
        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)

        is_capture = board.is_capture(move)
        is_pawn_move = bool(piece and piece.piece_type == chess.PAWN)

        probe = board.copy(stack=False)
        probe.push(move)

        gives_check = probe.is_check()
        repeated_move = move.uci() in repeated_moves
        repeated_square = to_square in repeated_squares

        changes_pattern = not repeated_move and not repeated_square
        irreversible = is_capture or is_pawn_move

        score = 0
        reasons: List[str] = []

        if irreversible:
            score += 1800
            reasons.append("irreversible progress")

        if is_capture:
            score += 1100
            reasons.append("capture breaks cycle")

        if is_pawn_move:
            score += 900
            reasons.append("pawn move breaks cycle")

        if gives_check:
            score += 800
            reasons.append("check creates forcing progress")

        if changes_pattern:
            score += 600
            reasons.append("changes repeated square pattern")

        if piece and piece.piece_type in {chess.ROOK, chess.BISHOP}:
            if repeated_move or repeated_square:
                score -= 1800
                reasons.append("rook/bishop repetition penalty")
            else:
                score += 250
                reasons.append("rook/bishop redirected")

        if repeated_move:
            score -= 1200
            reasons.append("repeated move penalty")

        if repeated_square:
            score -= 800
            reasons.append("repeated destination penalty")

        if not reasons:
            reasons.append("neutral non-repetition candidate")

        score += 10 - (move.from_square % 5) - (move.to_square % 5)

        return RepetitionBreakCandidate(
            move=move.uci(),
            is_legal=True,
            piece_type=piece_type,
            from_square=from_square,
            to_square=to_square,
            is_capture=is_capture,
            gives_check=gives_check,
            is_pawn_move=is_pawn_move,
            changes_piece_square_pattern=changes_pattern,
            repeated_move_penalty_applied=repeated_move,
            repeated_square_penalty_applied=repeated_square,
            irreversible_progress=irreversible,
            breaker_score=score,
            explanation="; ".join(reasons),
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        task_name: str = "full_chess_rook_bishop_repetition_breaker",
    ) -> RookBishopRepetitionBreakerResult:
        repeated_moves = list(repeated_moves or [])
        repeated_squares = list(repeated_squares or [])

        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        repetition_detected = self._detect_repetition(repeated_moves, repeated_squares)

        candidates = [
            self._score_move(board, move, repeated_moves, repeated_squares)
            for move in board.legal_moves
        ]
        candidates.sort(
            key=lambda c: (
                c.breaker_score,
                c.irreversible_progress,
                c.changes_piece_square_pattern,
                c.move,
            ),
            reverse=True,
        )

        selected = candidates[0] if candidates else None

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "repetition_detected": repetition_detected,
            "selected_breaker_move": selected.move if selected else "",
            "selected_score": selected.breaker_score if selected else 0,
            "repeated_moves": repeated_moves[-8:],
            "repeated_squares": repeated_squares[-8:],
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["repetition_breaker_run_count"] = int(self.policy.get("repetition_breaker_run_count", 0)) + 1
        self.policy["last_selected_breaker_move"] = selected.move if selected else ""
        self.policy["last_trace_hash"] = trace_hash

        if repetition_detected:
            self.policy["repetition_detected_count"] = int(self.policy.get("repetition_detected_count", 0)) + 1
        if selected:
            self.policy["breaker_move_selected_count"] = int(self.policy.get("breaker_move_selected_count", 0)) + 1

        evidence = {
            "rook_bishop_repetition_breaker_active": True,
            "repeated_move_detection_enabled": True,
            "repeated_square_detection_enabled": True,
            "rook_bishop_shuffle_penalty_enabled": True,
            "irreversible_progress_bonus_enabled": True,
            "capture_breaks_cycle_scored": True,
            "pawn_move_breaks_cycle_scored": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = RookBishopRepetitionBreakerResult(
            kernel_version="phase22e33_full_chess_rook_bishop_repetition_breaker_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            repetition_breaker_active=True,
            repeated_moves=repeated_moves,
            repeated_squares=repeated_squares,
            repetition_detected=repetition_detected,
            candidate_count=len(candidates),
            selected_breaker_move=selected.move if selected else "",
            selected_breaker_move_is_legal=bool(selected and selected.is_legal),
            selected_score=selected.breaker_score if selected else 0,
            selected_explanation=selected.explanation if selected else "",
            top_candidates=[asdict(c) for c in candidates[:8]],
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_breaker_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements a rook/bishop repetition breaker. It detects repeated moves and repeated "
                "destination squares, penalises rook/bishop shuffling, and prefers irreversible progress such as pawn "
                "moves, captures, checks, or non-repeating redirections. It does not call Stockfish, does not use LLM "
                "move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_rook_bishop_repetition_breaker_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_rook_bishop_repetition_breaker",
) -> RookBishopRepetitionBreakerResult:
    return AionRookBishopRepetitionBreakerKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Rook/bishop repetition breaker memory saved to: {result.memory_path}")
