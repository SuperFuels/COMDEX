from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_king_safety_threat_removal_policy_kernel import (
    run_full_chess_king_safety_threat_removal_policy_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_memory.json")


@dataclass(frozen=True)
class CriticalThreatHygieneQueenIntrusionTrapPolicyResult:
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
    critical_threat_hygiene_checked: bool
    wing_pawn_lunge_detected: bool
    wing_pawn_lunge_blocked: bool
    queen_intrusion_detected: bool
    queen_intrusion_square: str
    queen_capture_available: bool
    queen_trap_or_expel_available: bool
    queen_intrusion_override_applied: bool
    threat_hygiene_override_applied: bool
    threat_hygiene_reason: str
    king_safety_threat_removal_used: bool
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


class AionCriticalThreatHygieneQueenIntrusionTrapPolicyKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "critical_threat_checked_count": 0,
            "queen_intrusion_detected_count": 0,
            "queen_intrusion_override_count": 0,
            "wing_pawn_lunge_blocked_count": 0,
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("critical_threat_hygiene_queen_intrusion_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: CriticalThreatHygieneQueenIntrusionTrapPolicyResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(
            json.dumps(
                {
                    "memory_version": "phase22e52_critical_threat_hygiene_queen_intrusion_memory_v1",
                    "task_name": result.task_name,
                    "critical_threat_hygiene_queen_intrusion_policy": result.final_policy,
                    "last_result": asdict(result),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

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
        return chess.square_file(move.from_square) == chess.square_file(move.to_square) and chess.square_file(move.from_square) in {0, 1, 6, 7}

    def _opponent_queen_square(self, board: chess.Board, side: chess.Color) -> Optional[int]:
        for sq, piece in board.piece_map().items():
            if piece.color != side and piece.piece_type == chess.QUEEN:
                return sq
        return None

    def _queen_intrusion_score(self, board: chess.Board, side: chess.Color) -> tuple[bool, str, int]:
        queen_sq = self._opponent_queen_square(board, side)
        king_sq = board.king(side)
        if queen_sq is None or king_sq is None:
            return False, "", 0

        distance = max(
            abs(chess.square_file(queen_sq) - chess.square_file(king_sq)),
            abs(chess.square_rank(queen_sq) - chess.square_rank(king_sq)),
        )
        attacks_zone = any(
            board.is_attacked_by(not side, sq)
            for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king_sq])
        )
        intrusion = distance <= 3 or attacks_zone
        return intrusion, chess.square_name(queen_sq), max(0, 8 - distance) + (5 if attacks_zone else 0)

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
            if captured.piece_type == chess.QUEEN:
                score += 10000

        probe = board.copy(stack=False)
        probe.push(move)

        if probe.is_checkmate():
            score += 50000
        elif probe.is_check():
            score += 600

        before_intrusion, _, before_q_score = self._queen_intrusion_score(board, side)
        after_intrusion, _, after_q_score = self._queen_intrusion_score(probe, side)

        if before_intrusion and not after_intrusion:
            score += 1800
        score += (before_q_score - after_q_score) * 250

        if moving_piece and moving_piece.piece_type == chess.KING and captured is None:
            score -= 500

        if self._is_wing_pawn_lunge(board, move):
            score -= 1200

        if self._allows_immediate_mate(board, move):
            score -= 20000

        return score

    def _find_best_response(self, board: chess.Board, rejected_move: chess.Move, side: chess.Color, queen_intrusion: bool) -> Optional[chess.Move]:
        queen_captures = []
        candidates = []
        fallback_non_wing = []

        for move in board.legal_moves:
            if move == rejected_move:
                continue

            if self._is_wing_pawn_lunge(board, move):
                continue

            score = self._move_score(board, move, side)
            captured = board.piece_at(move.to_square)

            if captured and captured.color != side and captured.piece_type == chess.QUEEN:
                queen_captures.append((score + 50000, move))
                continue

            fallback_non_wing.append((score, move))

            if queen_intrusion:
                probe = board.copy(stack=False)
                probe.push(move)
                after_intrusion, _, _ = self._queen_intrusion_score(probe, side)
                if not after_intrusion or probe.is_check():
                    candidates.append((score, move))
            else:
                candidates.append((score, move))

        if queen_captures:
            queen_captures.sort(key=lambda item: item[0], reverse=True)
            return queen_captures[0][1]

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]

        if fallback_non_wing:
            fallback_non_wing.sort(key=lambda item: item[0], reverse=True)
            return fallback_non_wing[0][1]

        return None

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
        task_name: str = "full_chess_critical_threat_hygiene_queen_intrusion_trap_policy",
    ) -> CriticalThreatHygieneQueenIntrusionTrapPolicyResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_king_safety_threat_removal_policy_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            forced_active_intent=forced_active_intent,
            memory_path=self.memory_path.parent / "phase22e52_child_king_safety_threat_removal_memory.json",
        )

        active_intent = forced_active_intent or getattr(base, "active_intent", "")
        base_move_uci = getattr(base, "final_selected_move", "")
        final_source = getattr(base, "final_selected_source", getattr(base, "selected_source", ""))

        if forced_base_selected_move and active_intent in {"neutralise_critical_threat", "king_safety"}:
            base_move_uci = forced_base_selected_move
            final_source = "forced_critical_threat_fixture"

        final_move_uci = base_move_uci

        critical_checked = active_intent in {"neutralise_critical_threat", "king_safety"}
        queen_intrusion_detected, queen_square, _ = self._queen_intrusion_score(board, side)

        wing_detected = False
        wing_blocked = False
        queen_capture_available = False
        queen_trap_or_expel_available = False
        queen_override = False
        override = False
        reason = "not critical-threat or king-safety mode"

        try:
            selected_move = chess.Move.from_uci(base_move_uci)
            selected_legal = selected_move in board.legal_moves
        except Exception:
            selected_move = None
            selected_legal = False

        if critical_checked and selected_move:
            self.policy["critical_threat_checked_count"] = int(self.policy.get("critical_threat_checked_count", 0)) + 1
            wing_detected = self._is_wing_pawn_lunge(board, selected_move) if selected_legal else False

            if queen_intrusion_detected:
                self.policy["queen_intrusion_detected_count"] = int(self.policy.get("queen_intrusion_detected_count", 0)) + 1

            if wing_detected or queen_intrusion_detected:
                alt = self._find_best_response(board, selected_move, side, queen_intrusion_detected)

                must_override_wing = wing_detected and alt is not None
                must_override_queen = queen_intrusion_detected and alt is not None

                if must_override_wing or must_override_queen:
                    final_move_uci = alt.uci()
                    final_source = "critical_threat_hygiene_queen_intrusion_trap_policy"
                    override = True
                    captured = board.piece_at(alt.to_square)
                    queen_capture_available = bool(captured and captured.color != side and captured.piece_type == chess.QUEEN)
                    queen_trap_or_expel_available = queen_intrusion_detected
                    queen_override = queen_intrusion_detected
                    wing_blocked = wing_detected
                    reason = "critical threat hygiene selected non-wing queen/trap/expel response"
                    if wing_blocked:
                        self.policy["wing_pawn_lunge_blocked_count"] = int(self.policy.get("wing_pawn_lunge_blocked_count", 0)) + 1
                    if queen_override:
                        self.policy["queen_intrusion_override_count"] = int(self.policy.get("queen_intrusion_override_count", 0)) + 1
                else:
                    reason = "critical threat hygiene checked; no stronger override found"
            else:
                reason = "critical threat hygiene checked; no wing lunge or queen intrusion"

        try:
            final_legal = chess.Move.from_uci(final_move_uci) in board.legal_moves
        except Exception:
            final_legal = False

        trace_hash = self._hash(
            {
                "input_fen": input_fen,
                "side_to_move": side_to_move,
                "base_move": base_move_uci,
                "final_move": final_move_uci,
                "active_intent": active_intent,
                "queen_intrusion_detected": queen_intrusion_detected,
                "wing_pawn_lunge_detected": wing_detected,
                "override": override,
            }
        )

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move_uci
        self.policy["last_trace_hash"] = trace_hash

        result = CriticalThreatHygieneQueenIntrusionTrapPolicyResult(
            kernel_version="phase22e52_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=getattr(base, "base_selected_move", base_move_uci),
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move_uci),
            final_selected_move=final_move_uci,
            final_selected_source=final_source,
            final_selected_move_is_legal=final_legal,
            active_intent=active_intent,
            previous_active_intent=getattr(base, "previous_active_intent", ""),
            plan_strength_score=int(getattr(base, "plan_strength_score", 0)),
            critical_threat_hygiene_checked=critical_checked,
            wing_pawn_lunge_detected=wing_detected,
            wing_pawn_lunge_blocked=wing_blocked,
            queen_intrusion_detected=queen_intrusion_detected,
            queen_intrusion_square=queen_square,
            queen_capture_available=queen_capture_available,
            queen_trap_or_expel_available=queen_trap_or_expel_available,
            queen_intrusion_override_applied=queen_override,
            threat_hygiene_override_applied=override,
            threat_hygiene_reason=reason,
            king_safety_threat_removal_used=True,
            initiative_hygiene_used=True,
            promotion_safety_used=True,
            dynamic_intent_switching_used=True,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            proactive_override_applied=bool(getattr(base, "proactive_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or override,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence={
                "phase22e50_king_safety_threat_removal_consumed": True,
                "phase22e49_initiative_hygiene_inherited": True,
                "phase22e48_promotion_safety_inherited": True,
                "critical_threat_hygiene_checked": critical_checked,
                "queen_intrusion_detected": queen_intrusion_detected,
                "wing_pawn_lunge_detected": wing_detected,
                "move_legality_checked": True,
                "uses_stockfish": False,
                "uses_llm_move_judgement": False,
                "uses_lichess_analysis": False,
                "uses_trace_hash": True,
                "memory_loaded": self.memory_loaded,
            },
            boundary_statement=(
                "This kernel extends critical-threat hygiene beyond initiative_pressure and prioritises trapping, capturing, "
                "or expelling queen intrusions near the king. It wraps Phase 22E.50 and does not call Stockfish, does not use "
                "LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    forced_active_intent: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_critical_threat_hygiene_queen_intrusion_trap_policy",
) -> CriticalThreatHygieneQueenIntrusionTrapPolicyResult:
    return AionCriticalThreatHygieneQueenIntrusionTrapPolicyKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        forced_active_intent=forced_active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="r1b2rk1/p1Pn1p1p/1p2p1p1/8/3P4/2P2P2/P1P4P/R2QKBq1 w Q - 0 15",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="neutralise_critical_threat",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Critical threat hygiene memory saved to: {result.memory_path}")
