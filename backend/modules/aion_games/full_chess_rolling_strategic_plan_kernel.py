from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_rolling_strategic_plan_memory.json")


@dataclass(frozen=True)
class RollingStrategicPlanResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    phase: str
    primary_plan: str
    secondary_plan: str
    target_weakness: str
    setup_sequence: List[str]
    fallback_plan: str
    opponent_disruption_risk: str
    candidate_plan_moves: List[str]
    selected_plan_move: str
    selected_plan_reason: str
    plan_confidence: float
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionRollingStrategicPlanKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "last_phase": "",
            "last_primary_plan": "",
            "last_selected_plan_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("rolling_strategic_plan_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: RollingStrategicPlanResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "rolling_strategic_plan_policy": self.policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _phase(board: chess.Board) -> str:
        piece_count = len(board.piece_map())
        if board.fullmove_number <= 10 and piece_count >= 26:
            return "opening"
        if piece_count <= 12:
            return "endgame"
        return "middlegame"

    @staticmethod
    def _legal_ucis(board: chess.Board) -> List[str]:
        return [m.uci() for m in board.legal_moves]

    @staticmethod
    def _is_development_move(board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece:
            return False
        if piece.color != side:
            return False
        if piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
            return False
        home_rank = 0 if side == chess.WHITE else 7
        return chess.square_rank(move.from_square) == home_rank

    @staticmethod
    def _is_castle(move: chess.Move) -> bool:
        return move.uci() in {"e1g1", "e1c1", "e8g8", "e8c8"}

    @staticmethod
    def _is_capture_or_check(board: chess.Board, move: chess.Move) -> bool:
        if board.is_capture(move):
            return True
        copy = board.copy(stack=False)
        copy.push(move)
        return copy.is_check()

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        task_name: str = "full_chess_rolling_strategic_plan",
    ) -> RollingStrategicPlanResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        phase = self._phase(board)
        legal_moves = list(board.legal_moves)
        legal_ucis = self._legal_ucis(board)

        development = [m.uci() for m in legal_moves if self._is_development_move(board, m, side)]
        castles = [m.uci() for m in legal_moves if self._is_castle(m)]
        forcing = [m.uci() for m in legal_moves if self._is_capture_or_check(board, m)]

        if phase == "opening":
            primary_plan = "rapid_development"
            secondary_plan = "central_control"
            target_weakness = "undeveloped_position"
            setup_sequence = [
                "develop minor pieces",
                "support centre",
                "prepare king safety",
            ]
            fallback_plan = "king_safety_and_central_consolidation"
            professional_opening_preference = [
                "g1f3", "b1c3", "e2e4", "d2d4", "c2c4",
                "g8f6", "b8c6", "e7e5", "d7d5", "c7c5",
            ]
            ordered = professional_opening_preference + development + castles + legal_ucis
            candidate_plan_moves = list(dict.fromkeys([m for m in ordered if m in legal_ucis]))[:10]
            selected_plan_move = candidate_plan_moves[0] if candidate_plan_moves else (legal_ucis[0] if legal_ucis else "")
            selected_plan_reason = "develops a minor piece or supports opening structure"
            plan_confidence = 0.74 if development else 0.58

        elif phase == "middlegame":
            primary_plan = "improve_piece_activity_and_create_threats"
            secondary_plan = "opponent_king_pressure"
            target_weakness = "king_safety_or_loose_piece"
            setup_sequence = [
                "identify forcing candidate",
                "increase pressure on weakness",
                "preserve fallback defence",
            ]
            fallback_plan = "consolidate_and_reduce_tactical_exposure"
            candidate_plan_moves = forcing[:8] + legal_ucis[:6]
            selected_plan_move = candidate_plan_moves[0] if candidate_plan_moves else (legal_ucis[0] if legal_ucis else "")
            selected_plan_reason = "prioritises forcing move or active improvement"
            plan_confidence = 0.68 if forcing else 0.55

        else:
            primary_plan = "endgame_conversion"
            secondary_plan = "king_activity_and_pawn_promotion"
            target_weakness = "passed_pawn_or_king_distance"
            setup_sequence = [
                "activate king",
                "create or support passed pawn",
                "trade into winning structure",
            ]
            fallback_plan = "avoid_stalemate_and_preserve_material"
            candidate_plan_moves = forcing[:6] + legal_ucis[:6]
            selected_plan_move = candidate_plan_moves[0] if candidate_plan_moves else (legal_ucis[0] if legal_ucis else "")
            selected_plan_reason = "supports conversion, material safety or pawn progress"
            plan_confidence = 0.64

        opponent_disruption_risk = "high" if board.is_check() else ("medium" if forcing else "low")

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "phase": phase,
            "primary_plan": primary_plan,
            "secondary_plan": secondary_plan,
            "target_weakness": target_weakness,
            "setup_sequence": setup_sequence,
            "fallback_plan": fallback_plan,
            "opponent_disruption_risk": opponent_disruption_risk,
            "candidate_plan_moves": candidate_plan_moves,
            "selected_plan_move": selected_plan_move,
            "plan_confidence": plan_confidence,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_phase"] = phase
        self.policy["last_primary_plan"] = primary_plan
        self.policy["last_selected_plan_move"] = selected_plan_move
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "rolling_plan_generated": True,
            "phase_detected": True,
            "primary_plan_selected": bool(primary_plan),
            "setup_sequence_generated": bool(setup_sequence),
            "fallback_plan_generated": bool(fallback_plan),
            "candidate_plan_moves_generated": bool(candidate_plan_moves),
            "selected_plan_move_legal": selected_plan_move in legal_ucis if selected_plan_move else False,
            "opponent_disruption_risk_monitored": True,
            "uses_stockfish": False,
            "uses_lichess_analysis": False,
            "uses_llm_move_judgement": False,
            "uses_trace_hash": True,
        }

        result = RollingStrategicPlanResult(
            kernel_version="phase22e58_full_chess_rolling_strategic_plan_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            phase=phase,
            primary_plan=primary_plan,
            secondary_plan=secondary_plan,
            target_weakness=target_weakness,
            setup_sequence=setup_sequence,
            fallback_plan=fallback_plan,
            opponent_disruption_risk=opponent_disruption_risk,
            candidate_plan_moves=candidate_plan_moves,
            selected_plan_move=selected_plan_move,
            selected_plan_reason=selected_plan_reason,
            plan_confidence=plan_confidence,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel creates a rolling strategic chess plan before move selection. "
                "It does not post moves, does not call Stockfish, does not use Lichess analysis, "
                "and does not use LLM move judgement."
            ),
        )
        self._save_memory(result)
        return result


def run_full_chess_rolling_strategic_plan_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_rolling_strategic_plan",
) -> RollingStrategicPlanResult:
    return AionRollingStrategicPlanKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_rolling_strategic_plan_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
