from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_promotion_safety_queen_survival_guard_kernel import (
    run_full_chess_promotion_safety_queen_survival_guard_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_initiative_hygiene_guard_memory.json")


@dataclass(frozen=True)
class InitiativeHygieneGuardResult:
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

    initiative_hygiene_checked: bool
    wing_pawn_lunge_detected: bool
    wing_pawn_lunge_allowed: bool
    initiative_hygiene_override_applied: bool
    initiative_hygiene_reason: str
    safe_alternative_found: bool

    promotion_safety_used: bool
    dynamic_intent_switching_used: bool
    queen_override_applied: bool
    passed_pawn_scope_override_applied: bool
    anti_shuffling_override_applied: bool
    proactive_override_applied: bool
    intent_override_applied: bool
    final_regression_well_score: int

    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionInitiativeHygieneGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "wing_pawn_lunge_checked_count": 0,
            "wing_pawn_lunge_blocked_count": 0,
            "wing_pawn_lunge_allowed_count": 0,
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("initiative_hygiene_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: InitiativeHygieneGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e49_initiative_hygiene_memory_v1",
            "task_name": result.task_name,
            "initiative_hygiene_policy": result.final_policy,
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

    def _is_wing_pawn_lunge(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False

        from_file = chess.square_file(move.from_square)
        to_file = chess.square_file(move.to_square)

        if from_file != to_file:
            return False

        wing_files = {0, 1, 6, 7}
        if from_file not in wing_files:
            return False

        rank_delta = abs(chess.square_rank(move.to_square) - chess.square_rank(move.from_square))
        return rank_delta >= 1

    def _move_gives_check_or_mate(self, board: chess.Board, move: chess.Move) -> bool:
        probe = board.copy(stack=False)
        probe.push(move)
        return probe.is_check() or probe.is_checkmate()

    def _is_capture(self, board: chess.Board, move: chess.Move) -> bool:
        return board.piece_at(move.to_square) is not None or board.is_en_passant(move)

    def _is_promotion_or_promotion_progress(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False

        if move.promotion:
            return True

        to_rank = chess.square_rank(move.to_square)
        if piece.color == chess.WHITE:
            return to_rank >= 5
        return to_rank <= 2

    def _allows_wing_pawn_lunge(self, board: chess.Board, move: chess.Move, active_intent: str) -> tuple[bool, str]:
        if not self._is_wing_pawn_lunge(board, move):
            return True, "not a wing-pawn lunge"

        if active_intent in {"king_safety", "convert_passed_pawn"}:
            return True, "wing pawn allowed because active intent is concrete safety or promotion conversion"

        if self._is_capture(board, move):
            return True, "wing pawn allowed because move captures"

        if self._move_gives_check_or_mate(board, move):
            return True, "wing pawn allowed because move gives check or mate"

        if self._is_promotion_or_promotion_progress(board, move):
            return True, "wing pawn allowed because move advances a promotion path"

        return False, "wing-pawn lunge rejected under initiative hygiene: no capture, check, mate, promotion path, or safety necessity"

    def _move_score(self, board: chess.Board, move: chess.Move) -> int:
        piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)

        score = 0

        if captured:
            score += self._piece_value(captured.piece_type) + 100

        probe = board.copy(stack=False)
        probe.push(move)

        if probe.is_checkmate():
            score += 50000
        elif probe.is_check():
            score += 500

        if piece:
            if piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                score += 80
            if piece.piece_type == chess.PAWN:
                from_file = chess.square_file(move.from_square)
                if from_file in {2, 3, 4, 5}:
                    score += 50

        if self._is_wing_pawn_lunge(board, move):
            score -= 500

        if probe.is_check():
            score += 250

        return score

    def _find_safe_alternative(self, board: chess.Board, rejected_move: chess.Move) -> Optional[chess.Move]:
        candidates = []
        for move in board.legal_moves:
            if move == rejected_move:
                continue
            allowed, _ = self._allows_wing_pawn_lunge(board, move, "initiative_pressure")
            if not allowed:
                continue
            candidates.append((self._move_score(board, move), move))

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
        task_name: str = "full_chess_initiative_hygiene_guard",
    ) -> InitiativeHygieneGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_promotion_safety_queen_survival_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            forced_active_intent=forced_active_intent,
            memory_path=self.memory_path.parent / "phase22e49_child_promotion_safety_memory.json",
        )

        base_move_uci = getattr(base, "final_selected_move", "")
        final_move_uci = base_move_uci
        final_source = getattr(base, "final_selected_source", getattr(base, "selected_source", ""))
        active_intent = getattr(base, "active_intent", "")

        initiative_hygiene_checked = active_intent == "initiative_pressure"
        wing_pawn_lunge_detected = False
        wing_pawn_lunge_allowed = True
        initiative_hygiene_override_applied = False
        initiative_hygiene_reason = "not initiative pressure"
        safe_alternative_found = False

        try:
            selected_move = chess.Move.from_uci(base_move_uci)
            selected_is_legal = selected_move in board.legal_moves
        except Exception:
            selected_move = None
            selected_is_legal = False

        if initiative_hygiene_checked and selected_move and selected_is_legal:
            wing_pawn_lunge_detected = self._is_wing_pawn_lunge(board, selected_move)
            wing_pawn_lunge_allowed, initiative_hygiene_reason = self._allows_wing_pawn_lunge(
                board, selected_move, active_intent
            )

            if wing_pawn_lunge_detected:
                self.policy["wing_pawn_lunge_checked_count"] = int(self.policy.get("wing_pawn_lunge_checked_count", 0)) + 1

            if wing_pawn_lunge_detected and not wing_pawn_lunge_allowed:
                alternative = self._find_safe_alternative(board, selected_move)
                if alternative is not None:
                    final_move_uci = alternative.uci()
                    final_source = "initiative_hygiene_guard"
                    initiative_hygiene_override_applied = True
                    safe_alternative_found = True
                    self.policy["wing_pawn_lunge_blocked_count"] = int(self.policy.get("wing_pawn_lunge_blocked_count", 0)) + 1
                else:
                    initiative_hygiene_reason = "wing-pawn lunge rejected but no safe alternative found"
            elif wing_pawn_lunge_detected:
                self.policy["wing_pawn_lunge_allowed_count"] = int(self.policy.get("wing_pawn_lunge_allowed_count", 0)) + 1

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move_uci) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_move": base_move_uci,
            "final_move": final_move_uci,
            "active_intent": active_intent,
            "wing_pawn_lunge_detected": wing_pawn_lunge_detected,
            "initiative_hygiene_override_applied": initiative_hygiene_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move_uci
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e48_promotion_safety_consumed": True,
            "phase22e46_dynamic_intent_switching_inherited": True,
            "initiative_hygiene_checked": initiative_hygiene_checked,
            "wing_pawn_lunge_detected": wing_pawn_lunge_detected,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = InitiativeHygieneGuardResult(
            kernel_version="phase22e49_full_chess_initiative_hygiene_guard_kernel_v1",
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
            active_intent=active_intent,
            previous_active_intent=getattr(base, "previous_active_intent", ""),
            plan_strength_score=int(getattr(base, "plan_strength_score", 0)),
            initiative_hygiene_checked=initiative_hygiene_checked,
            wing_pawn_lunge_detected=wing_pawn_lunge_detected,
            wing_pawn_lunge_allowed=wing_pawn_lunge_allowed,
            initiative_hygiene_override_applied=initiative_hygiene_override_applied,
            initiative_hygiene_reason=initiative_hygiene_reason,
            safe_alternative_found=safe_alternative_found,
            promotion_safety_used=True,
            dynamic_intent_switching_used=True,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            proactive_override_applied=bool(getattr(base, "proactive_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or initiative_hygiene_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel rejects wing-pawn lunges under initiative_pressure unless the move is concrete: capture, check, mate, "
                "promotion path, or king-safety necessity. It wraps Phase 22E.48 and does not call Stockfish, does not use LLM "
                "move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_initiative_hygiene_guard_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    forced_active_intent: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_initiative_hygiene_guard",
) -> InitiativeHygieneGuardResult:
    return AionInitiativeHygieneGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        forced_active_intent=forced_active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="initiative_pressure",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Initiative hygiene memory saved to: {result.memory_path}")
