from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_dynamic_intent_switching_plan_strength_kernel import (
    run_full_chess_dynamic_intent_switching_plan_strength_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_promotion_safety_queen_survival_guard_memory.json")


@dataclass(frozen=True)
class PromotionSafetyQueenSurvivalGuardResult:
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
    previous_active_intent: str
    plan_strength_score: int
    intent_switch_applied: bool
    intent_switch_reason: str

    promotion_safety_checked: bool
    promotion_move_detected: bool
    promoted_piece_square: str
    promoted_piece_immediately_capturable: bool
    promotion_survival_override_applied: bool
    promotion_survival_reason: str
    safe_alternative_found: bool

    queen_override_applied: bool
    passed_pawn_scope_override_applied: bool
    anti_shuffling_override_applied: bool
    proactive_override_applied: bool
    dynamic_intent_switching_used: bool
    intent_override_applied: bool
    final_regression_well_score: int

    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionPromotionSafetyQueenSurvivalGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "promotion_checked_count": 0,
            "promotion_survival_override_count": 0,
            "unsafe_promotion_count": 0,
            "safe_promotion_count": 0,
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("promotion_safety_queen_survival_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PromotionSafetyQueenSurvivalGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e48_promotion_safety_queen_survival_memory_v1",
            "task_name": result.task_name,
            "promotion_safety_queen_survival_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _piece_value(self, piece_type: int) -> int:
        return {
            chess.PAWN: 100,
            chess.KNIGHT: 300,
            chess.BISHOP: 320,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }.get(piece_type, 0)

    def _is_promotion_move(self, move_uci: str) -> bool:
        return len(move_uci) == 5 and move_uci[-1].lower() in {"q", "r", "b", "n"}

    def _promoted_piece_capturable(self, board: chess.Board, move: chess.Move) -> bool:
        probe = board.copy(stack=False)
        probe.push(move)

        promoted_square = move.to_square
        opponent = probe.turn

        for reply in probe.legal_moves:
            if reply.to_square == promoted_square:
                attacker = probe.piece_at(reply.from_square)
                if attacker and attacker.color == opponent:
                    return True

        return False

    def _move_allows_immediate_mate(self, board: chess.Board, move: chess.Move) -> bool:
        probe = board.copy(stack=False)
        probe.push(move)

        for reply in probe.legal_moves:
            reply_probe = probe.copy(stack=False)
            reply_probe.push(reply)
            if reply_probe.is_checkmate():
                return True

        return False

    def _safe_move_score(self, board: chess.Board, move: chess.Move) -> int:
        probe = board.copy(stack=False)
        moving_piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)

        score = 0

        if captured:
            score += self._piece_value(captured.piece_type)

        if moving_piece and moving_piece.piece_type == chess.PAWN:
            if moving_piece.color == chess.WHITE:
                score += chess.square_rank(move.to_square) * 20
            else:
                score += (7 - chess.square_rank(move.to_square)) * 20

        if move.promotion == chess.QUEEN:
            score += 250

        probe.push(move)

        if probe.is_check():
            score += 150

        if self._move_allows_immediate_mate(board, move):
            score -= 10000

        if move.promotion and self._promoted_piece_capturable(board, move):
            score -= 3000

        if probe.is_checkmate():
            score += 50000

        return score

    def _find_safe_alternative(self, board: chess.Board, rejected_move: chess.Move) -> Optional[chess.Move]:
        candidates = []

        for move in board.legal_moves:
            if move == rejected_move:
                continue

            if self._move_allows_immediate_mate(board, move):
                continue

            if move.promotion and self._promoted_piece_capturable(board, move):
                continue

            candidates.append((self._safe_move_score(board, move), move))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[list[str]] = None,
        repeated_squares: Optional[list[str]] = None,
        forced_base_selected_move: Optional[str] = None,
        forced_active_intent: Optional[str] = None,
        memory_path: Optional[Path] = None,
        task_name: str = "full_chess_promotion_safety_queen_survival_guard",
    ) -> PromotionSafetyQueenSurvivalGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            forced_active_intent=forced_active_intent,
            memory_path=self.memory_path.parent / "phase22e48_child_dynamic_intent_switching_memory.json",
        )

        base_move_uci = getattr(base, "final_selected_move", "")
        final_move_uci = base_move_uci
        final_source = getattr(base, "final_selected_source", getattr(base, "selected_source", ""))

        promotion_move_detected = self._is_promotion_move(base_move_uci)
        promotion_safety_checked = promotion_move_detected
        promoted_piece_square = ""
        promoted_piece_immediately_capturable = False
        promotion_survival_override_applied = False
        promotion_survival_reason = "not a promotion move"
        safe_alternative_found = False

        try:
            selected_move = chess.Move.from_uci(base_move_uci)
            selected_is_legal = selected_move in board.legal_moves
        except Exception:
            selected_move = None
            selected_is_legal = False

        if selected_move and selected_is_legal and promotion_move_detected:
            self.policy["promotion_checked_count"] = int(self.policy.get("promotion_checked_count", 0)) + 1
            promoted_piece_square = chess.square_name(selected_move.to_square)
            promoted_piece_immediately_capturable = self._promoted_piece_capturable(board, selected_move)

            if promoted_piece_immediately_capturable or self._move_allows_immediate_mate(board, selected_move):
                self.policy["unsafe_promotion_count"] = int(self.policy.get("unsafe_promotion_count", 0)) + 1
                alternative = self._find_safe_alternative(board, selected_move)

                if alternative is not None:
                    final_move_uci = alternative.uci()
                    final_source = "promotion_safety_queen_survival_guard"
                    promotion_survival_override_applied = True
                    safe_alternative_found = True
                    promotion_survival_reason = "promotion would be immediately capturable or allow immediate mate; safe alternative selected"
                    self.policy["promotion_survival_override_count"] = int(self.policy.get("promotion_survival_override_count", 0)) + 1
                else:
                    promotion_survival_reason = "promotion unsafe but no safe legal alternative found"
            else:
                self.policy["safe_promotion_count"] = int(self.policy.get("safe_promotion_count", 0)) + 1
                promotion_survival_reason = "promotion queen survives immediate opponent capture scan"

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move_uci) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_move": base_move_uci,
            "final_move": final_move_uci,
            "promotion_move_detected": promotion_move_detected,
            "promoted_piece_immediately_capturable": promoted_piece_immediately_capturable,
            "promotion_survival_override_applied": promotion_survival_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move_uci
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e46_dynamic_intent_switching_consumed": True,
            "phase22e44_proactive_intent_primacy_inherited": True,
            "phase22e43_anti_shuffling_guard_inherited": True,
            "phase22e42_passed_pawn_scope_guard_inherited": True,
            "phase22e41_queen_first_promotion_guard_inherited": True,
            "promotion_safety_checked": promotion_safety_checked,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PromotionSafetyQueenSurvivalGuardResult(
            kernel_version="phase22e48_full_chess_promotion_safety_queen_survival_guard_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=getattr(base, "base_selected_move", base_move_uci),
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move_uci),
            final_selected_move=final_move_uci,
            final_selected_source=final_source,
            final_selected_move_is_legal=final_selected_move_is_legal,
            active_intent=getattr(base, "active_intent", ""),
            previous_active_intent=getattr(base, "previous_active_intent", ""),
            plan_strength_score=int(getattr(base, "plan_strength_score", 0)),
            intent_switch_applied=bool(getattr(base, "intent_switch_applied", False)),
            intent_switch_reason=getattr(base, "intent_switch_reason", ""),
            promotion_safety_checked=promotion_safety_checked,
            promotion_move_detected=promotion_move_detected,
            promoted_piece_square=promoted_piece_square,
            promoted_piece_immediately_capturable=promoted_piece_immediately_capturable,
            promotion_survival_override_applied=promotion_survival_override_applied,
            promotion_survival_reason=promotion_survival_reason,
            safe_alternative_found=safe_alternative_found,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            proactive_override_applied=bool(getattr(base, "proactive_override_applied", False)),
            dynamic_intent_switching_used=True,
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or promotion_survival_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel prevents unsafe promotion conversion by checking whether a promoted queen can be immediately captured "
                "or whether the promotion permits immediate mate. It wraps Phase 22E.46 and does not call Stockfish, does not use "
                "LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_promotion_safety_queen_survival_guard_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    forced_active_intent: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_promotion_safety_queen_survival_guard",
) -> PromotionSafetyQueenSurvivalGuardResult:
    return AionPromotionSafetyQueenSurvivalGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        forced_active_intent=forced_active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="r7/1pk1p1P1/8/p1P5/3b1Pn1/n4K2/8/6r1 w - - 0 28",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Promotion safety memory saved to: {result.memory_path}")
