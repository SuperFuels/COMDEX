from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_anti_shuffling_endgame_conversion_guard_kernel import (
    run_full_chess_anti_shuffling_endgame_conversion_guard_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_proactive_intent_primacy_plan_enforcement_memory.json")


@dataclass(frozen=True)
class ProactiveIntentPrimacyPlanEnforcementResult:
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
    proactive_intent_checked: bool
    proactive_plan_available: bool
    passive_drift_detected: bool
    proactive_override_applied: bool
    proactive_override_reason: str
    queen_override_applied: bool
    passed_pawn_scope_override_applied: bool
    anti_shuffling_override_applied: bool
    intent_override_applied: bool
    final_regression_well_score: int
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionProactiveIntentPrimacyPlanEnforcementKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "proactive_override_count": 0,
            "base_move_kept_count": 0,
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
            policy = payload.get("proactive_intent_primacy_plan_enforcement_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ProactiveIntentPrimacyPlanEnforcementResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e44_proactive_intent_primacy_plan_enforcement_memory_v1",
            "task_name": result.task_name,
            "proactive_intent_primacy_plan_enforcement_policy": result.final_policy,
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

    def _is_development_move(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if piece is None or piece.color != side:
            return False
        if piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
            return False

        rank = chess.square_rank(move.from_square)
        if side == chess.WHITE and rank == 0:
            return True
        if side == chess.BLACK and rank == 7:
            return True
        return False

    def _is_pawn_center_progress(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if piece is None or piece.piece_type != chess.PAWN or piece.color != side:
            return False

        to_file = chess.square_file(move.to_square)
        from_rank = chess.square_rank(move.from_square)
        to_rank = chess.square_rank(move.to_square)

        if to_file not in {2, 3, 4, 5}:
            return False

        if side == chess.WHITE:
            return to_rank > from_rank
        return to_rank < from_rank

    def _is_passive_drift(
        self,
        *,
        board: chess.Board,
        move_uci: str,
        side: chess.Color,
        active_intent: str,
    ) -> bool:
        try:
            move = chess.Move.from_uci(move_uci)
        except Exception:
            return False

        if move not in board.legal_moves:
            return False

        if active_intent in {
            "neutralise_critical_threat",
            "king_safety",
            "convert_passed_pawn",
            "build_mate_net",
        }:
            return False

        if board.is_capture(move):
            return False

        probe = board.copy(stack=False)
        probe.push(move)
        if probe.is_check():
            return False

        if move.promotion:
            return False

        if self._is_development_move(board, move, side):
            return False

        if self._is_pawn_center_progress(board, move, side):
            return False

        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in {chess.ROOK, chess.KING, chess.QUEEN}:
            return True

        return False

    def _score_proactive_move(
        self,
        *,
        board: chess.Board,
        move: chess.Move,
        side: chess.Color,
        active_intent: str,
    ) -> int:
        score = 0

        piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)

        if board.is_capture(move) and captured:
            score += 800 + self._piece_value(captured.piece_type)

        probe = board.copy(stack=False)
        probe.push(move)
        if probe.is_check():
            score += 700

        if move.promotion:
            score += 5000
            if move.promotion == chess.QUEEN:
                score += 500

        if self._is_development_move(board, move, side):
            score += 550

        if self._is_pawn_center_progress(board, move, side):
            score += 450

        if active_intent in {"rapid_development", "center_control"}:
            if self._is_development_move(board, move, side):
                score += 250
            if self._is_pawn_center_progress(board, move, side):
                score += 200

        if active_intent in {"kingside_attack", "initiative_pressure"}:
            to_file = chess.square_file(move.to_square)
            if side == chess.WHITE and to_file >= 4:
                score += 120
            if side == chess.BLACK and to_file <= 3:
                score += 120

        if piece and piece.piece_type in {chess.ROOK, chess.KING} and not board.is_capture(move):
            score -= 300

        score -= int(move.from_square) // 3
        score -= int(move.to_square) // 5
        return score

    def _best_proactive_move(
        self,
        *,
        board: chess.Board,
        side: chess.Color,
        active_intent: str,
        original_move_uci: str,
    ) -> tuple[str, bool, str]:
        candidates: list[tuple[int, str]] = []

        for move in board.legal_moves:
            uci = move.uci()
            if uci == original_move_uci:
                continue

            score = self._score_proactive_move(
                board=board,
                move=move,
                side=side,
                active_intent=active_intent,
            )
            if score <= 0:
                continue

            candidates.append((score, uci))

        if not candidates:
            return original_move_uci, False, ""

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1], True, "selected highest-ranked legal proactive plan move"

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[list[str]] = None,
        repeated_squares: Optional[list[str]] = None,
        forced_base_selected_move: Optional[str] = None,
        task_name: str = "full_chess_proactive_intent_primacy_plan_enforcement",
    ) -> ProactiveIntentPrimacyPlanEnforcementResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            memory_path=self.memory_path.parent / "phase22e44_child_anti_shuffling_guard_memory.json",
        )

        base_move = base.final_selected_move
        final_move = base_move
        active_intent = base.active_intent

        proactive_intent_checked = active_intent in {
            "rapid_development",
            "center_control",
            "initiative_pressure",
            "kingside_attack",
            "queenside_expansion",
            "simplify_when_ahead",
        }

        passive_drift_detected = False
        proactive_plan_available = False
        proactive_override_applied = False
        proactive_override_reason = ""

        if proactive_intent_checked:
            passive_drift_detected = self._is_passive_drift(
                board=board,
                move_uci=base_move,
                side=side,
                active_intent=active_intent,
            )

            if passive_drift_detected:
                alternative, proactive_plan_available, proactive_override_reason = self._best_proactive_move(
                    board=board,
                    side=side,
                    active_intent=active_intent,
                    original_move_uci=base_move,
                )
                if proactive_plan_available:
                    final_move = alternative
                    proactive_override_applied = True

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "active_intent": active_intent,
            "base_selected_move": base_move,
            "final_selected_move": final_move,
            "passive_drift_detected": passive_drift_detected,
            "proactive_override_applied": proactive_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_base_selected_move"] = base_move
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_active_intent"] = active_intent
        self.policy["last_trace_hash"] = trace_hash

        if proactive_override_applied:
            self.policy["proactive_override_count"] = int(self.policy.get("proactive_override_count", 0)) + 1
        else:
            self.policy["base_move_kept_count"] = int(self.policy.get("base_move_kept_count", 0)) + 1

        evidence = {
            "phase22e43_anti_shuffling_guard_consumed": True,
            "proactive_intent_checked": proactive_intent_checked,
            "passive_drift_detection_enabled": True,
            "proactive_alternative_ranked_deterministically": True,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ProactiveIntentPrimacyPlanEnforcementResult(
            kernel_version="phase22e44_full_chess_proactive_intent_primacy_plan_enforcement_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=base_move,
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move),
            final_selected_move=final_move,
            final_selected_source=(
                "proactive_intent_primacy_plan_enforcement"
                if proactive_override_applied
                else getattr(base, "final_selected_source", getattr(base, "selected_source", ""))
            ),
            final_selected_move_is_legal=final_selected_move_is_legal,
            active_intent=active_intent,
            proactive_intent_checked=proactive_intent_checked,
            proactive_plan_available=proactive_plan_available,
            passive_drift_detected=passive_drift_detected,
            proactive_override_applied=proactive_override_applied,
            proactive_override_reason=proactive_override_reason,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or proactive_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel enforces proactive intent primacy by replacing passive drift moves with deterministic legal "
                "plan-forward alternatives when a proactive plan is available. It does not call Stockfish, does not use "
                "LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_proactive_intent_primacy_plan_enforcement",
) -> ProactiveIntentPrimacyPlanEnforcementResult:
    return AionProactiveIntentPrimacyPlanEnforcementKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="d1d2",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Proactive intent primacy memory saved to: {result.memory_path}")
