from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_proactive_intent_primacy_plan_enforcement_kernel import (
    run_full_chess_proactive_intent_primacy_plan_enforcement_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_dynamic_intent_switching_plan_strength_memory.json")


@dataclass(frozen=True)
class DynamicIntentSwitchingPlanStrengthResult:
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

    previous_active_intent: str
    active_intent: str
    dynamic_intent_checked: bool
    plan_strength_score: int
    intent_switch_applied: bool
    intent_switch_reason: str
    opponent_threat_pressure: int
    material_delta_cp: int
    development_complete: bool
    king_safety_pressure: int

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


class AionDynamicIntentSwitchingPlanStrengthKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "intent_switch_count": 0,
            "intent_kept_count": 0,
            "last_previous_intent": "",
            "last_active_intent": "",
            "last_plan_strength_score": 0,
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("dynamic_intent_switching_plan_strength_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: DynamicIntentSwitchingPlanStrengthResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e46_dynamic_intent_switching_plan_strength_memory_v1",
            "task_name": result.task_name,
            "dynamic_intent_switching_plan_strength_policy": result.final_policy,
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

    def _material_delta_cp(self, board: chess.Board, side: chess.Color) -> int:
        delta = 0
        for piece in board.piece_map().values():
            value = self._piece_value(piece.piece_type)
            delta += value if piece.color == side else -value
        return delta

    def _development_complete(self, board: chess.Board, side: chess.Color) -> bool:
        if side == chess.WHITE:
            home = [chess.B1, chess.G1, chess.C1, chess.F1]
        else:
            home = [chess.B8, chess.G8, chess.C8, chess.F8]

        undeveloped = 0
        for square in home:
            piece = board.piece_at(square)
            if piece and piece.color == side and piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                undeveloped += 1

        return undeveloped <= 1

    def _king_safety_pressure(self, board: chess.Board, side: chess.Color) -> int:
        king_square = board.king(side)
        if king_square is None:
            return 999

        opponent = not side
        pressure = 0

        for square in chess.SquareSet(chess.BB_KING_ATTACKS[king_square]):
            if board.is_attacked_by(opponent, square):
                pressure += 1

        if board.is_check():
            pressure += 5

        return pressure

    def _opponent_threat_pressure(self, board: chess.Board, side: chess.Color) -> int:
        opponent = not side
        pressure = 0

        tmp = board.copy(stack=False)
        tmp.turn = opponent

        for move in tmp.legal_moves:
            captured = tmp.piece_at(move.to_square)
            if captured and captured.color == side:
                pressure += self._piece_value(captured.piece_type) // 100

            probe = tmp.copy(stack=False)
            probe.push(move)
            if probe.is_check():
                pressure += 3

        return pressure

    def _has_advanced_attack(self, board: chess.Board, side: chess.Color) -> bool:
        opponent_king = board.king(not side)
        if opponent_king is None:
            return False

        attackers = 0
        for square, piece in board.piece_map().items():
            if piece.color != side:
                continue
            if piece.piece_type in {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}:
                if chess.square_distance(square, opponent_king) <= 3:
                    attackers += 1

        return attackers >= 2

    def _evaluate_intent(
        self,
        *,
        board: chess.Board,
        side: chess.Color,
        previous_intent: str,
    ) -> tuple[str, int, bool, str, int, int, bool, int]:
        material_delta = self._material_delta_cp(board, side)
        development_complete = self._development_complete(board, side)
        king_pressure = self._king_safety_pressure(board, side)
        opponent_pressure = self._opponent_threat_pressure(board, side)

        plan_strength = 50

        if previous_intent == "rapid_development":
            plan_strength += 25 if not development_complete else -35

        if previous_intent in {"initiative_pressure", "kingside_attack"}:
            plan_strength += 30 if self._has_advanced_attack(board, side) else -10

        if material_delta >= 300:
            plan_strength += 20

        if king_pressure >= 4:
            plan_strength -= 60

        if opponent_pressure >= 10:
            plan_strength -= 25

        if king_pressure >= 4:
            return (
                "king_safety",
                plan_strength,
                previous_intent != "king_safety",
                "king safety pressure exceeded switch threshold",
                opponent_pressure,
                material_delta,
                development_complete,
                king_pressure,
            )

        if material_delta >= 500 and previous_intent not in {"simplify_when_ahead", "convert_passed_pawn"}:
            return (
                "simplify_when_ahead",
                plan_strength,
                True,
                "material advantage reached simplification threshold",
                opponent_pressure,
                material_delta,
                development_complete,
                king_pressure,
            )

        if previous_intent == "rapid_development" and development_complete:
            return (
                "initiative_pressure",
                plan_strength,
                True,
                "development phase complete; switch to initiative pressure",
                opponent_pressure,
                material_delta,
                development_complete,
                king_pressure,
            )

        if previous_intent == "initiative_pressure" and not self._has_advanced_attack(board, side) and opponent_pressure >= 10:
            return (
                "neutralise_critical_threat",
                plan_strength,
                True,
                "opponent threat pressure exceeded initiative stability threshold",
                opponent_pressure,
                material_delta,
                development_complete,
                king_pressure,
            )

        return (
            previous_intent,
            plan_strength,
            False,
            "current intent remains above switch threshold",
            opponent_pressure,
            material_delta,
            development_complete,
            king_pressure,
        )

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
        task_name: str = "full_chess_dynamic_intent_switching_plan_strength",
    ) -> DynamicIntentSwitchingPlanStrengthResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            forced_base_selected_move=forced_base_selected_move,
            memory_path=self.memory_path.parent / "phase22e46_child_proactive_intent_primacy_memory.json",
        )

        previous_intent = forced_active_intent or getattr(base, "active_intent", "")
        (
            active_intent,
            plan_strength_score,
            intent_switch_applied,
            intent_switch_reason,
            opponent_threat_pressure,
            material_delta_cp,
            development_complete,
            king_safety_pressure,
        ) = self._evaluate_intent(
            board=board,
            side=side,
            previous_intent=previous_intent,
        )

        final_move = getattr(base, "final_selected_move", "")
        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "previous_intent": previous_intent,
            "active_intent": active_intent,
            "plan_strength_score": plan_strength_score,
            "intent_switch_applied": intent_switch_applied,
            "final_selected_move": final_move,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_previous_intent"] = previous_intent
        self.policy["last_active_intent"] = active_intent
        self.policy["last_plan_strength_score"] = plan_strength_score
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash

        if intent_switch_applied:
            self.policy["intent_switch_count"] = int(self.policy.get("intent_switch_count", 0)) + 1
        else:
            self.policy["intent_kept_count"] = int(self.policy.get("intent_kept_count", 0)) + 1

        evidence = {
            "phase22e44_proactive_intent_primacy_consumed": True,
            "dynamic_intent_checked": True,
            "plan_strength_scored": True,
            "opponent_threat_pressure_scored": True,
            "material_delta_scored": True,
            "king_safety_pressure_scored": True,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = DynamicIntentSwitchingPlanStrengthResult(
            kernel_version="phase22e46_full_chess_dynamic_intent_switching_plan_strength_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=getattr(base, "base_selected_move", final_move),
            base_well_selected_move=getattr(base, "base_well_selected_move", final_move),
            final_selected_move=final_move,
            final_selected_source=(
                "dynamic_intent_switching_plan_strength"
                if intent_switch_applied
                else getattr(base, "final_selected_source", getattr(base, "selected_source", ""))
            ),
            final_selected_move_is_legal=final_selected_move_is_legal,
            previous_active_intent=previous_intent,
            active_intent=active_intent,
            dynamic_intent_checked=True,
            plan_strength_score=plan_strength_score,
            intent_switch_applied=intent_switch_applied,
            intent_switch_reason=intent_switch_reason,
            opponent_threat_pressure=opponent_threat_pressure,
            material_delta_cp=material_delta_cp,
            development_complete=development_complete,
            king_safety_pressure=king_safety_pressure,
            queen_override_applied=bool(getattr(base, "queen_override_applied", False)),
            passed_pawn_scope_override_applied=bool(getattr(base, "passed_pawn_scope_override_applied", False)),
            anti_shuffling_override_applied=bool(getattr(base, "anti_shuffling_override_applied", False)),
            proactive_override_applied=bool(getattr(base, "proactive_override_applied", False)),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or intent_switch_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel scores current plan strength and dynamically switches active intent when development is complete, "
                "king safety pressure rises, material advantage suggests simplification, or opponent threat pressure exceeds "
                "the current plan threshold. It does not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_dynamic_intent_switching_plan_strength_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    forced_base_selected_move: Optional[str] = None,
    forced_active_intent: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_dynamic_intent_switching_plan_strength",
) -> DynamicIntentSwitchingPlanStrengthResult:
    return AionDynamicIntentSwitchingPlanStrengthKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        forced_active_intent=forced_active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="r1b1kbnr/pp3ppp/1qnpp3/2p5/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 6",
        side_to_move="white",
        forced_base_selected_move="c1g5",
        forced_active_intent="rapid_development",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Dynamic intent switching memory saved to: {result.memory_path}")
