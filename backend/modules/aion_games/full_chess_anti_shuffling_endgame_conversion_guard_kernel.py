from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_passed_pawn_intent_scope_guard_kernel import (
    run_full_chess_passed_pawn_intent_scope_guard_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_anti_shuffling_endgame_conversion_guard_memory.json")


@dataclass(frozen=True)
class AntiShufflingEndgameConversionGuardResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    base_selected_move: str
    base_well_selected_move: str
    final_selected_move: str
    final_selected_source: str
    final_selected_move_is_legal: bool
    active_intent: str
    anti_shuffling_checked: bool
    shuffle_detected: bool
    conversion_alternative_found: bool
    anti_shuffling_override_applied: bool
    shuffle_reason: str
    conversion_reason: str
    queen_override_applied: bool
    passed_pawn_scope_override_applied: bool
    intent_override_applied: bool
    final_regression_well_score: int
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionAntiShufflingEndgameConversionGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "shuffle_override_count": 0,
            "shuffle_kept_count": 0,
            "last_base_selected_move": "",
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("anti_shuffling_endgame_conversion_guard_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: AntiShufflingEndgameConversionGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e43_anti_shuffling_endgame_conversion_guard_memory_v1",
            "task_name": result.task_name,
            "anti_shuffling_endgame_conversion_guard_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _reverse_move(self, move_uci: str) -> str:
        if len(move_uci) < 4:
            return move_uci
        return move_uci[2:4] + move_uci[0:2] + move_uci[4:]

    def _is_promotion(self, move: chess.Move) -> bool:
        return move.promotion is not None

    def _is_pawn_progress(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if piece is None or piece.piece_type != chess.PAWN or piece.color != side:
            return False

        from_rank = chess.square_rank(move.from_square)
        to_rank = chess.square_rank(move.to_square)

        if side == chess.WHITE:
            return to_rank > from_rank
        return to_rank < from_rank

    def _is_shuffle(
        self,
        *,
        board: chess.Board,
        move_uci: str,
        side: chess.Color,
        repeated_moves: list[str],
        repeated_squares: list[str],
    ) -> tuple[bool, str]:
        try:
            move = chess.Move.from_uci(move_uci)
        except Exception:
            return False, ""

        if move not in board.legal_moves:
            return False, ""

        if self._is_promotion(move):
            return False, ""

        if board.is_capture(move):
            return False, ""

        if self._is_pawn_progress(board, move, side):
            return False, ""

        probe = board.copy(stack=False)
        probe.push(move)
        if probe.is_check():
            return False, ""

        recent = list(repeated_moves or [])[-12:]
        reverse = self._reverse_move(move_uci)

        if move_uci in recent:
            return True, "selected move already appears in recent move memory"

        if reverse in recent:
            return True, "selected move reverses a recent move"

        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        recent_squares = list(repeated_squares or [])[-16:]

        if from_sq in recent_squares and to_sq in recent_squares:
            return True, "selected move cycles between repeated squares"

        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in {chess.ROOK, chess.QUEEN, chess.BISHOP, chess.KNIGHT, chess.KING}:
            if len(recent_squares) >= 6 and (from_sq in recent_squares or to_sq in recent_squares):
                return True, "piece move touches repeated square memory without capture, check, promotion, or pawn progress"

        return False, ""

    def _score_conversion_move(self, board: chess.Board, move: chess.Move, side: chess.Color) -> int:
        score = 0

        if self._is_promotion(move):
            score += 10000
            if move.promotion == chess.QUEEN:
                score += 1000

        if board.is_capture(move):
            score += 700

        if self._is_pawn_progress(board, move, side):
            score += 600

        probe = board.copy(stack=False)
        probe.push(move)
        if probe.is_check():
            score += 500

        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.KING:
            to_file = chess.square_file(move.to_square)
            to_rank = chess.square_rank(move.to_square)
            score += 40 - (abs(to_file - 3) + abs(to_file - 4) + abs(to_rank - 3) + abs(to_rank - 4))

        if piece and piece.piece_type == chess.ROOK:
            score += 40

        if piece and piece.piece_type == chess.QUEEN:
            score += 35

        score -= int(move.from_square)
        score -= int(move.to_square) // 2
        return score

    def _best_conversion_alternative(
        self,
        *,
        board: chess.Board,
        side: chess.Color,
        original_move_uci: str,
        repeated_moves: list[str],
        repeated_squares: list[str],
    ) -> tuple[str, bool, str]:
        candidates: list[tuple[int, str]] = []

        for move in board.legal_moves:
            uci = move.uci()
            if uci == original_move_uci:
                continue

            is_shuffle, _ = self._is_shuffle(
                board=board,
                move_uci=uci,
                side=side,
                repeated_moves=repeated_moves,
                repeated_squares=repeated_squares,
            )
            if is_shuffle:
                continue

            score = self._score_conversion_move(board, move, side)
            if score <= 0:
                continue

            candidates.append((score, uci))

        if not candidates:
            return original_move_uci, False, ""

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1], True, "selected highest-ranked legal conversion/progress alternative"

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[list[str]] = None,
        repeated_squares: Optional[list[str]] = None,
        forced_base_selected_move: Optional[str] = None,
        task_name: str = "full_chess_anti_shuffling_endgame_conversion_guard",
    ) -> AntiShufflingEndgameConversionGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_passed_pawn_intent_scope_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            memory_path=self.memory_path.parent / "phase22e43_child_passed_pawn_scope_guard_memory.json",
        )

        base_move = base.final_selected_move
        final_move = base_move

        shuffle_detected, shuffle_reason = self._is_shuffle(
            board=board,
            move_uci=base_move,
            side=side,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
        )

        conversion_alternative_found = False
        anti_shuffling_override_applied = False
        conversion_reason = ""

        if shuffle_detected:
            alternative, conversion_alternative_found, conversion_reason = self._best_conversion_alternative(
                board=board,
                side=side,
                original_move_uci=base_move,
                repeated_moves=list(repeated_moves or []),
                repeated_squares=list(repeated_squares or []),
            )
            if conversion_alternative_found:
                final_move = alternative
                anti_shuffling_override_applied = True

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_selected_move": base_move,
            "final_selected_move": final_move,
            "shuffle_detected": shuffle_detected,
            "anti_shuffling_override_applied": anti_shuffling_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_base_selected_move"] = base_move
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash

        if anti_shuffling_override_applied:
            self.policy["shuffle_override_count"] = int(self.policy.get("shuffle_override_count", 0)) + 1
        else:
            self.policy["shuffle_kept_count"] = int(self.policy.get("shuffle_kept_count", 0)) + 1

        evidence = {
            "phase22e42_passed_pawn_scope_guard_consumed": True,
            "anti_shuffling_checked": True,
            "shuffle_detection_uses_recent_move_memory": True,
            "conversion_alternative_ranked_deterministically": True,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = AntiShufflingEndgameConversionGuardResult(
            kernel_version="phase22e43_full_chess_anti_shuffling_endgame_conversion_guard_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=base_move,
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move),
            final_selected_move=final_move,
            final_selected_source=(
                "anti_shuffling_endgame_conversion_guard"
                if anti_shuffling_override_applied
                else getattr(base, "final_selected_source", getattr(base, "selected_source", ""))
            ),
            final_selected_move_is_legal=final_selected_move_is_legal,
            active_intent=base.active_intent,
            anti_shuffling_checked=True,
            shuffle_detected=shuffle_detected,
            conversion_alternative_found=conversion_alternative_found,
            anti_shuffling_override_applied=anti_shuffling_override_applied,
            shuffle_reason=shuffle_reason,
            conversion_reason=conversion_reason,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or anti_shuffling_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel prevents repeated rook/piece shuffling in endgame conversion positions and replaces "
                "shuffle moves with deterministic legal progress alternatives when available. It does not call Stockfish, "
                "does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_anti_shuffling_endgame_conversion_guard",
) -> AntiShufflingEndgameConversionGuardResult:
    return AionAntiShufflingEndgameConversionGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="1R6/k5b1/2P3P1/4r2p/4P3/P7/4B2p/4K3 w - - 3 40",
        side_to_move="white",
        repeated_moves=["d7b7", "b8a8", "b7b8", "a8a7", "b8b7"],
        repeated_squares=["b7", "b8", "a8", "a7", "b8", "b7"],
        forced_base_selected_move="b8c8",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Anti-shuffling guard memory saved to: {result.memory_path}")
