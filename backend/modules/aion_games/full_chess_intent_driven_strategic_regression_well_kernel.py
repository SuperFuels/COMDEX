from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_proactive_plan_primacy_intent_driver_kernel import (
    run_full_chess_proactive_plan_primacy_intent_driver_kernel,
)
from backend.modules.aion_games.full_chess_strategic_regression_well_optimiser_kernel import (
    run_full_chess_strategic_regression_well_optimiser_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_intent_driven_strategic_regression_well_memory.json")


@dataclass(frozen=True)
class IntentDrivenStrategicRegressionWellResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    intent_driven_regression_well_active: bool
    active_intent: str
    previous_intent: str
    intent_changed: bool
    emergency_override_active: bool
    base_well_selected_move: str
    base_well_selected_source: str
    base_well_score: int
    final_selected_move: str
    final_selected_move_is_legal: bool
    final_selected_source: str
    final_regression_well_score: int
    intent_override_applied: bool
    intent_override_reason: str
    intent_move_bias: Dict[str, int]
    intent_candidate_scores: List[Dict[str, Any]]
    strategic_well_summary: Dict[str, Any]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionIntentDrivenStrategicRegressionWellKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "intent_override_count": 0,
            "base_move_kept_count": 0,
            "last_active_intent": "",
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("intent_driven_strategic_regression_well_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: IntentDrivenStrategicRegressionWellResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e37_intent_driven_strategic_regression_well_memory_v1",
            "task_name": result.task_name,
            "intent_driven_strategic_regression_well_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _is_development_move(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if piece is None or piece.color != side:
            return False
        if piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
            return False
        if side == chess.WHITE:
            return move.from_square in {chess.B1, chess.G1, chess.C1, chess.F1}
        return move.from_square in {chess.B8, chess.G8, chess.C8, chess.F8}

    def _is_center_pawn_move(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if piece is None or piece.color != side or piece.piece_type != chess.PAWN:
            return False
        return move.from_square in {chess.C2, chess.D2, chess.E2, chess.C7, chess.D7, chess.E7} and move.to_square in {
            chess.C3, chess.C4, chess.D3, chess.D4, chess.E3, chess.E4,
            chess.C6, chess.C5, chess.D6, chess.D5, chess.E6, chess.E5,
        }

    def _is_bad_opening_wing_pawn_move(self, board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        if board.fullmove_number > 8:
            return False
        piece = board.piece_at(move.from_square)
        if piece is None or piece.color != side or piece.piece_type != chess.PAWN:
            return False
        return chess.square_file(move.from_square) in {0, 7}

    def _is_castle(self, board: chess.Board, move: chess.Move) -> bool:
        return board.is_castling(move)

    def _score_move_for_intent(self, board: chess.Board, move: chess.Move, side: chess.Color, active_intent: str) -> Dict[str, Any]:
        score = 0
        reasons: List[str] = []

        piece = board.piece_at(move.from_square)
        is_capture = board.is_capture(move)
        probe = board.copy(stack=False)
        probe.push(move)
        gives_check = probe.is_check()

        if active_intent in {"rapid_development", "center_control"}:
            if self._is_development_move(board, move, side):
                score += 1800
                reasons.append("develops minor piece")

                if move.uci() in {"g1f3", "b1c3", "g8f6", "b8c6"}:
                    score += 700
                    reasons.append("normal knight development")

                if move.uci() in {"c1f4", "c1g5", "f1e2", "f1d3", "f1c4", "c8f5", "c8g4", "f8e7", "f8d6", "f8c5"}:
                    score += 500
                    reasons.append("normal bishop development")

                if move.uci() in {"g1h3", "b1a3", "g8h6", "b8a6"}:
                    score -= 900
                    reasons.append("rim knight penalty")

                if move.uci() in {"c1h6", "f1a6", "c8h3", "f8a3"}:
                    score -= 800
                    reasons.append("edge bishop penalty")

            if self._is_center_pawn_move(board, move, side):
                score += 1600
                reasons.append("supports center control")

                if move.uci() in {"e2e4", "c2c4", "e7e5", "c7c5"}:
                    score += 500
                    reasons.append("active center break")

            if self._is_castle(board, move):
                score += 1500
                reasons.append("improves king safety")

            if self._is_bad_opening_wing_pawn_move(board, move, side):
                score -= 2500
                reasons.append("opening wing pawn drift penalty")

            if piece and piece.piece_type == chess.QUEEN and board.fullmove_number <= 8:
                score -= 1200
                reasons.append("early queen penalty")

        if active_intent == "king_safety":
            if self._is_castle(board, move):
                score += 2500
                reasons.append("castles")
            if gives_check:
                score += 300
                reasons.append("forcing check")

        if active_intent == "initiative_pressure":
            if gives_check:
                score += 1400
                reasons.append("check")
            if is_capture:
                score += 900
                reasons.append("capture")

        if active_intent == "convert_passed_pawn":
            if move.promotion:
                score += 4000
                reasons.append("promotion")
            if piece and piece.piece_type == chess.PAWN:
                score += 800
                reasons.append("pawn conversion move")

        if active_intent == "build_mate_net":
            if gives_check:
                score += 1600
                reasons.append("check in mate-net mode")
            enemy_king = board.king(not side)
            if enemy_king is not None:
                before = len(list(board.legal_moves))
                after = len(list(probe.legal_moves))
                if after < before:
                    score += 700
                    reasons.append("reduces reply width")

        if active_intent == "simplify_when_ahead" and is_capture:
            score += 900
            reasons.append("simplification capture")

        if active_intent == "neutralise_critical_threat":
            score += 500
            if gives_check:
                score += 500
                reasons.append("forcing emergency response")

        if gives_check:
            score += 250
        if is_capture:
            score += 200

        return {
            "move": move.uci(),
            "intent_score": score,
            "reasons": reasons,
            "is_legal": True,
        }

    def _select_intent_move(self, board: chess.Board, side: chess.Color, active_intent: str) -> List[Dict[str, Any]]:
        scored = [
            self._score_move_for_intent(board, move, side, active_intent)
            for move in board.legal_moves
        ]
        scored.sort(key=lambda item: (item["intent_score"], item["move"]), reverse=True)
        return scored

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        task_name: str = "full_chess_intent_driven_strategic_regression_well",
    ) -> IntentDrivenStrategicRegressionWellResult:
        repeated_moves = list(repeated_moves or [])
        repeated_squares = list(repeated_squares or [])

        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        intent = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            memory_path=self.memory_path.parent / "phase22e37_child_intent_driver_memory.json",
        )

        well = run_full_chess_strategic_regression_well_optimiser_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            repeated_squares=repeated_squares,
            memory_path=self.memory_path.parent / "phase22e37_child_base_well_memory.json",
        )

        base_move = well.selected_move
        base_source = well.selected_source
        base_score = int(well.regression_well_score)
        base_legal = False

        try:
            base_legal = chess.Move.from_uci(base_move) in board.legal_moves
        except Exception:
            base_legal = False

        intent_scores = self._select_intent_move(board, side, intent.active_intent)
        best_intent = intent_scores[0] if intent_scores else {"move": "", "intent_score": -999999, "reasons": []}

        final_move = base_move if base_legal else best_intent["move"]
        final_source = f"base_well:{base_source}"
        final_score = base_score
        override_applied = False
        override_reason = ""

        base_intent_score = next((x["intent_score"] for x in intent_scores if x["move"] == base_move), -999999)
        best_intent_score = int(best_intent.get("intent_score", -999999))

        if intent.emergency_override_active:
            if best_intent["move"] and best_intent_score > base_intent_score:
                final_move = best_intent["move"]
                final_source = "intent_driver:emergency_override"
                final_score = base_score + best_intent_score + 2000
                override_applied = True
                override_reason = "emergency override intent outranked base well move"
        elif intent.active_intent in {"rapid_development", "center_control", "king_safety"}:
            if best_intent["move"] and best_intent_score >= base_intent_score + 1200:
                final_move = best_intent["move"]
                final_source = f"intent_driver:{intent.active_intent}"
                final_score = base_score + best_intent_score
                override_applied = True
                override_reason = "proactive opening intent corrected base well drift"
        elif best_intent["move"] and best_intent_score >= base_intent_score + 1800:
            final_move = best_intent["move"]
            final_source = f"intent_driver:{intent.active_intent}"
            final_score = base_score + best_intent_score
            override_applied = True
            override_reason = "intent progress score exceeded base well move"

        final_legal = False
        try:
            final_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_legal = False

        strategic_well_summary = {
            "base_selected_move": well.selected_move,
            "base_selected_source": well.selected_source,
            "base_regression_well_score": well.regression_well_score,
            "base_safety_passed": well.safety_passed,
            "base_plan": well.plan,
            "base_repetition_detected": well.repetition_detected,
            "base_component_summary": well.component_summary,
        }

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "active_intent": intent.active_intent,
            "base_move": base_move,
            "final_move": final_move,
            "override_applied": override_applied,
            "final_source": final_source,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_active_intent"] = intent.active_intent
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash
        if override_applied:
            self.policy["intent_override_count"] = int(self.policy.get("intent_override_count", 0)) + 1
        else:
            self.policy["base_move_kept_count"] = int(self.policy.get("base_move_kept_count", 0)) + 1

        evidence = {
            "intent_driver_consumed": True,
            "strategic_regression_well_consumed": True,
            "intent_bias_applied": True,
            "opening_drift_guard_enabled": True,
            "final_move_legal_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = IntentDrivenStrategicRegressionWellResult(
            kernel_version="phase22e37_full_chess_intent_driven_strategic_regression_well_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            intent_driven_regression_well_active=True,
            active_intent=intent.active_intent,
            previous_intent=intent.previous_intent,
            intent_changed=intent.intent_changed,
            emergency_override_active=intent.emergency_override_active,
            base_well_selected_move=base_move,
            base_well_selected_source=base_source,
            base_well_score=base_score,
            final_selected_move=final_move,
            final_selected_move_is_legal=final_legal,
            final_selected_source=final_source,
            final_regression_well_score=final_score,
            intent_override_applied=override_applied,
            intent_override_reason=override_reason,
            intent_move_bias=intent.recommended_intent_move_bias,
            intent_candidate_scores=intent_scores[:12],
            strategic_well_summary=strategic_well_summary,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel integrates the Phase 22E.36 Proactive Plan Primacy Intent Driver into the Phase 22E.34 "
                "Strategic Regression Well. It preserves the base well but allows proactive intent to correct drift, "
                "especially in opening positions where development, center control, and king safety should dominate. "
                "It does not send moves, does not call Stockfish, does not use LLM move judgement, and does not use "
                "Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_intent_driven_strategic_regression_well_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_intent_driven_strategic_regression_well",
) -> IntentDrivenStrategicRegressionWellResult:
    return AionIntentDrivenStrategicRegressionWellKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Intent-driven Strategic Regression Well memory saved to: {result.memory_path}")
