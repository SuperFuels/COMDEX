from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_initiative_hygiene_guard_kernel import (
    run_full_chess_initiative_hygiene_guard_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_king_safety_threat_removal_policy_memory.json")


@dataclass(frozen=True)
class KingSafetyThreatRemovalPolicyResult:
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

    king_safety_threat_removal_checked: bool
    passive_king_walk_detected: bool
    threat_removal_alternative_found: bool
    threat_removal_override_applied: bool
    threat_removal_reason: str
    selected_move_threat_score: int
    alternative_threat_score: int
    king_pressure_before: int
    king_pressure_after_selected: int
    king_pressure_after_final: int

    initiative_hygiene_used: bool
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


class AionKingSafetyThreatRemovalPolicyKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "king_safety_checked_count": 0,
            "passive_king_walk_detected_count": 0,
            "threat_removal_override_count": 0,
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("king_safety_threat_removal_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: KingSafetyThreatRemovalPolicyResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e50_king_safety_threat_removal_memory_v1",
            "task_name": result.task_name,
            "king_safety_threat_removal_policy": result.final_policy,
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

    def _king_pressure(self, board: chess.Board, side: chess.Color) -> int:
        king_square = board.king(side)
        if king_square is None:
            return 999

        opponent = not side
        pressure = 0

        if board.is_check():
            pressure += 10

        for square in chess.SquareSet(chess.BB_KING_ATTACKS[king_square]):
            if board.is_attacked_by(opponent, square):
                pressure += 2

        attackers = board.attackers(opponent, king_square)
        pressure += 5 * len(attackers)

        return pressure

    def _allows_immediate_mate(self, board: chess.Board, move: chess.Move) -> bool:
        probe = board.copy(stack=False)
        probe.push(move)

        for reply in probe.legal_moves:
            reply_probe = probe.copy(stack=False)
            reply_probe.push(reply)
            if reply_probe.is_checkmate():
                return True

        return False

    def _move_score(self, board: chess.Board, move: chess.Move, side: chess.Color) -> int:
        moving_piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)

        score = 0

        if captured and captured.color != side:
            score += self._piece_value(captured.piece_type) + 500

        probe = board.copy(stack=False)
        before_pressure = self._king_pressure(board, side)
        probe.push(move)
        after_pressure = self._king_pressure(probe, side)

        score += (before_pressure - after_pressure) * 120

        if probe.is_checkmate():
            score += 50000
        elif probe.is_check():
            score += 300

        if moving_piece and moving_piece.piece_type == chess.KING and not captured:
            score -= 350

        if self._allows_immediate_mate(board, move):
            score -= 10000

        return score

    def _is_passive_king_walk(self, board: chess.Board, move: chess.Move, active_intent: str) -> bool:
        if active_intent != "king_safety":
            return False

        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.KING:
            return False

        captured = board.piece_at(move.to_square)
        return captured is None

    def _find_threat_removal_alternative(self, board: chess.Board, rejected_move: chess.Move, side: chess.Color) -> Optional[chess.Move]:
        selected_score = self._move_score(board, rejected_move, side)
        candidates = []

        for move in board.legal_moves:
            if move == rejected_move:
                continue

            piece = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)

            if not piece or piece.color != side:
                continue

            is_threat_removal_shape = (
                captured is not None
                or piece.piece_type != chess.KING
                or self._king_pressure(board.copy(stack=False), side) > 0
            )

            if not is_threat_removal_shape:
                continue

            score = self._move_score(board, move, side)
            if score > selected_score + 150:
                candidates.append((score, move))

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
        task_name: str = "full_chess_king_safety_threat_removal_policy",
    ) -> KingSafetyThreatRemovalPolicyResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_initiative_hygiene_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            forced_active_intent=forced_active_intent,
            memory_path=self.memory_path.parent / "phase22e50_child_initiative_hygiene_memory.json",
        )

        base_move_uci = getattr(base, "final_selected_move", "")
        final_source = getattr(base, "final_selected_source", getattr(base, "selected_source", ""))

        # Test/fixture hook:
        # lower guards may already correct a passive king walk before this layer sees it.
        # When explicitly forced in a 22E.50 unit test, evaluate the forced move at this layer.
        if forced_base_selected_move and forced_active_intent == "king_safety":
            base_move_uci = forced_base_selected_move
            final_source = "forced_king_safety_fixture"

        final_move_uci = base_move_uci
        active_intent = forced_active_intent or getattr(base, "active_intent", "")

        king_safety_threat_removal_checked = active_intent == "king_safety"
        passive_king_walk_detected = False
        threat_removal_alternative_found = False
        threat_removal_override_applied = False
        threat_removal_reason = "not king safety mode"

        king_pressure_before = self._king_pressure(board, side)
        king_pressure_after_selected = king_pressure_before
        king_pressure_after_final = king_pressure_before
        selected_move_threat_score = 0
        alternative_threat_score = 0

        try:
            selected_move = chess.Move.from_uci(base_move_uci)
            selected_is_legal = selected_move in board.legal_moves
        except Exception:
            selected_move = None
            selected_is_legal = False

        if king_safety_threat_removal_checked and selected_move and selected_is_legal:
            self.policy["king_safety_checked_count"] = int(self.policy.get("king_safety_checked_count", 0)) + 1

            passive_king_walk_detected = self._is_passive_king_walk(board, selected_move, active_intent)
            selected_move_threat_score = self._move_score(board, selected_move, side)

            selected_probe = board.copy(stack=False)
            selected_probe.push(selected_move)
            king_pressure_after_selected = self._king_pressure(selected_probe, side)

            if passive_king_walk_detected:
                self.policy["passive_king_walk_detected_count"] = int(self.policy.get("passive_king_walk_detected_count", 0)) + 1

                alternative = self._find_threat_removal_alternative(board, selected_move, side)

                if alternative is not None:
                    final_move_uci = alternative.uci()
                    final_source = "king_safety_threat_removal_policy"
                    threat_removal_alternative_found = True
                    threat_removal_override_applied = True
                    alternative_threat_score = self._move_score(board, alternative, side)
                    threat_removal_reason = "passive king walk replaced by capture/block/threat-removal alternative"
                    self.policy["threat_removal_override_count"] = int(self.policy.get("threat_removal_override_count", 0)) + 1
                else:
                    threat_removal_reason = "passive king walk detected but no stronger legal threat-removal alternative found"
            else:
                threat_removal_reason = "king safety move is not passive king walking"

        try:
            final_move = chess.Move.from_uci(final_move_uci)
            final_selected_move_is_legal = final_move in board.legal_moves
            final_probe = board.copy(stack=False)
            final_probe.push(final_move)
            king_pressure_after_final = self._king_pressure(final_probe, side)
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_move": base_move_uci,
            "final_move": final_move_uci,
            "active_intent": active_intent,
            "passive_king_walk_detected": passive_king_walk_detected,
            "threat_removal_override_applied": threat_removal_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move_uci
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e49_initiative_hygiene_consumed": True,
            "phase22e48_promotion_safety_inherited": True,
            "phase22e46_dynamic_intent_switching_inherited": True,
            "king_safety_threat_removal_checked": king_safety_threat_removal_checked,
            "passive_king_walk_detected": passive_king_walk_detected,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = KingSafetyThreatRemovalPolicyResult(
            kernel_version="phase22e50_full_chess_king_safety_threat_removal_policy_kernel_v1",
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
            king_safety_threat_removal_checked=king_safety_threat_removal_checked,
            passive_king_walk_detected=passive_king_walk_detected,
            threat_removal_alternative_found=threat_removal_alternative_found,
            threat_removal_override_applied=threat_removal_override_applied,
            threat_removal_reason=threat_removal_reason,
            selected_move_threat_score=selected_move_threat_score,
            alternative_threat_score=alternative_threat_score,
            king_pressure_before=king_pressure_before,
            king_pressure_after_selected=king_pressure_after_selected,
            king_pressure_after_final=king_pressure_after_final,
            initiative_hygiene_used=True,
            promotion_safety_used=True,
            dynamic_intent_switching_used=True,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            proactive_override_applied=bool(getattr(base, "proactive_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or threat_removal_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel prevents king-safety mode from degenerating into passive king-walking. "
                "When a stronger capture, block, check, or threat-removal alternative exists, it replaces the passive king move. "
                "It wraps Phase 22E.49 and does not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_king_safety_threat_removal_policy_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    forced_active_intent: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_king_safety_threat_removal_policy",
) -> KingSafetyThreatRemovalPolicyResult:
    return AionKingSafetyThreatRemovalPolicyKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        forced_active_intent=forced_active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ King safety threat-removal memory saved to: {result.memory_path}")
