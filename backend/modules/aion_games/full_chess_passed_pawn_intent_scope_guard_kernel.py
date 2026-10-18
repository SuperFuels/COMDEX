from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_promotion_choice_queen_first_guard_kernel import (
    run_full_chess_promotion_choice_queen_first_guard_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_passed_pawn_intent_scope_guard_memory.json")


@dataclass(frozen=True)
class PassedPawnIntentScopeGuardResult:
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
    active_intent_before_scope: str
    active_intent: str
    passed_pawn_scope_checked: bool
    passed_pawn_scope_valid: bool
    passed_pawn_scope_override_applied: bool
    scope_override_reason: str
    queen_override_applied: bool
    intent_override_applied: bool
    final_regression_well_score: int
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionPassedPawnIntentScopeGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "scope_override_count": 0,
            "scope_valid_count": 0,
            "last_base_selected_move": "",
            "last_final_selected_move": "",
            "last_active_intent": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("passed_pawn_intent_scope_guard_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PassedPawnIntentScopeGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e42_passed_pawn_intent_scope_guard_memory_v1",
            "task_name": result.task_name,
            "passed_pawn_intent_scope_guard_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _is_promotion(self, move_uci: str) -> bool:
        return len(move_uci) == 5 and move_uci[-1] in {"q", "r", "b", "n"}

    def _pawn_progresses_toward_promotion(self, board: chess.Board, move_uci: str, side: chess.Color) -> bool:
        try:
            move = chess.Move.from_uci(move_uci)
        except Exception:
            return False

        piece = board.piece_at(move.from_square)
        if piece is None or piece.piece_type != chess.PAWN or piece.color != side:
            return False

        from_rank = chess.square_rank(move.from_square)
        to_rank = chess.square_rank(move.to_square)

        if side == chess.WHITE:
            return to_rank > from_rank and to_rank >= 5
        return to_rank < from_rank and to_rank <= 2

    def _scope_valid(self, board: chess.Board, move_uci: str, side: chess.Color) -> bool:
        return self._is_promotion(move_uci) or self._pawn_progresses_toward_promotion(board, move_uci, side)

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[list[str]] = None,
        repeated_squares: Optional[list[str]] = None,
        forced_base_selected_move: Optional[str] = None,
        task_name: str = "full_chess_passed_pawn_intent_scope_guard",
    ) -> PassedPawnIntentScopeGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_promotion_choice_queen_first_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            memory_path=self.memory_path.parent / "phase22e42_child_promotion_guard_memory.json",
        )

        base_move = base.final_selected_move
        final_move = base_move
        active_intent_before_scope = base.active_intent
        active_intent = active_intent_before_scope

        passed_pawn_scope_checked = active_intent_before_scope == "convert_passed_pawn"
        passed_pawn_scope_valid = True
        passed_pawn_scope_override_applied = False
        scope_override_reason = ""

        if passed_pawn_scope_checked:
            passed_pawn_scope_valid = self._scope_valid(board, final_move, side)
            if not passed_pawn_scope_valid:
                active_intent = "initiative_pressure"
                passed_pawn_scope_override_applied = True
                scope_override_reason = (
                    "convert_passed_pawn intent rejected because selected move is not promotion or direct pawn progress"
                )

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_selected_move": base_move,
            "final_selected_move": final_move,
            "active_intent_before_scope": active_intent_before_scope,
            "active_intent": active_intent,
            "passed_pawn_scope_valid": passed_pawn_scope_valid,
            "passed_pawn_scope_override_applied": passed_pawn_scope_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_base_selected_move"] = base_move
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_active_intent"] = active_intent
        self.policy["last_trace_hash"] = trace_hash

        if passed_pawn_scope_override_applied:
            self.policy["scope_override_count"] = int(self.policy.get("scope_override_count", 0)) + 1
        else:
            self.policy["scope_valid_count"] = int(self.policy.get("scope_valid_count", 0)) + 1

        evidence = {
            "phase22e41_promotion_guard_consumed": True,
            "passed_pawn_scope_checked": passed_pawn_scope_checked,
            "scope_override_requires_invalid_passed_pawn_move": True,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PassedPawnIntentScopeGuardResult(
            kernel_version="phase22e42_full_chess_passed_pawn_intent_scope_guard_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=base_move,
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move),
            final_selected_move=final_move,
            final_selected_source=(
                "passed_pawn_intent_scope_guard"
                if passed_pawn_scope_override_applied
                else getattr(base, "final_selected_source", getattr(base, "selected_source", ""))
            ),
            final_selected_move_is_legal=final_selected_move_is_legal,
            active_intent_before_scope=active_intent_before_scope,
            active_intent=active_intent,
            passed_pawn_scope_checked=passed_pawn_scope_checked,
            passed_pawn_scope_valid=passed_pawn_scope_valid,
            passed_pawn_scope_override_applied=passed_pawn_scope_override_applied,
            scope_override_reason=scope_override_reason,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or passed_pawn_scope_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel prevents convert_passed_pawn intent from hijacking moves that are not promotion "
                "or direct passed-pawn progress. It does not call Stockfish, does not use LLM move judgement, "
                "and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_passed_pawn_intent_scope_guard_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_passed_pawn_intent_scope_guard",
) -> PassedPawnIntentScopeGuardResult:
    return AionPassedPawnIntentScopeGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r3r3/Ppk1N1b1/8/4N1pp/4P1Pp/5P2/P1P1B3/R3K2R w KQ - 1 23",
        side_to_move="white",
        forced_base_selected_move="h1h4",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Passed-pawn scope guard memory saved to: {result.memory_path}")
