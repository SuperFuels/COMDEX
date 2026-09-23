from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_proactive_plan_primacy_intent_driver_memory.json")


@dataclass(frozen=True)
class IntentCandidate:
    intent_name: str
    priority: int
    active: bool
    reason: str
    progress_targets: List[str]


@dataclass(frozen=True)
class ProactivePlanPrimacyIntentDriverResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    proactive_intent_driver_active: bool
    active_intent: str
    previous_intent: str
    intent_changed: bool
    emergency_override_active: bool
    emergency_override_reason: str
    intent_commitment_score: int
    intent_progress_score: int
    opponent_forced_to_react: bool
    recommended_intent_move_bias: Dict[str, int]
    intent_candidates: List[Dict[str, Any]]
    trace_hash: str
    policy_memory_mutated: bool
    final_intent_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionProactivePlanPrimacyIntentDriverKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "intent_driver_run_count": 0,
            "last_active_intent": "",
            "last_trace_hash": None,
            "intent_change_count": 0,
            "intent_continuity_count": 0,
            "emergency_override_count": 0,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("proactive_plan_primacy_intent_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ProactivePlanPrimacyIntentDriverResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e36_proactive_plan_primacy_intent_driver_memory_v1",
            "task_name": result.task_name,
            "proactive_plan_primacy_intent_policy": result.final_intent_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _material_score(self, board: chess.Board, side: chess.Color) -> int:
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
        }
        score = 0
        for piece_type, value in values.items():
            score += len(board.pieces(piece_type, side)) * value
            score -= len(board.pieces(piece_type, not side)) * value
        return score

    def _has_passed_pawn(self, board: chess.Board, side: chess.Color) -> bool:
        enemy = not side
        for sq in board.pieces(chess.PAWN, side):
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            adjacent_files = [f for f in (file_idx - 1, file_idx, file_idx + 1) if 0 <= f <= 7]
            blocked = False
            for enemy_sq in board.pieces(chess.PAWN, enemy):
                enemy_file = chess.square_file(enemy_sq)
                enemy_rank = chess.square_rank(enemy_sq)
                if enemy_file not in adjacent_files:
                    continue
                if side == chess.WHITE and enemy_rank > rank_idx:
                    blocked = True
                if side == chess.BLACK and enemy_rank < rank_idx:
                    blocked = True
            if not blocked:
                return True
        return False

    def _king_safe(self, board: chess.Board, side: chess.Color) -> bool:
        king = board.king(side)
        if king is None:
            return False
        if side == chess.WHITE and king in {chess.G1, chess.C1}:
            return True
        if side == chess.BLACK and king in {chess.G8, chess.C8}:
            return True
        return not board.is_attacked_by(not side, king)

    def _development_count(self, board: chess.Board, side: chess.Color) -> int:
        home = {chess.B1, chess.G1, chess.C1, chess.F1} if side == chess.WHITE else {chess.B8, chess.G8, chess.C8, chess.F8}
        developed = 0
        for sq in home:
            piece = board.piece_at(sq)
            if piece is None or piece.color != side:
                developed += 1
        return developed

    def _center_control_count(self, board: chess.Board, side: chess.Color) -> int:
        center = [chess.D4, chess.E4, chess.D5, chess.E5]
        return sum(
            1
            for sq in center
            if board.is_attacked_by(side, sq) or (board.piece_at(sq) and board.piece_at(sq).color == side)
        )

    def _legal_forcing_moves(self, board: chess.Board) -> int:
        count = 0
        for move in board.legal_moves:
            probe = board.copy(stack=False)
            is_capture = board.is_capture(move)
            probe.push(move)
            if is_capture or probe.is_check():
                count += 1
        return count

    def _candidate(self, name: str, priority: int, active: bool, reason: str, targets: List[str]) -> IntentCandidate:
        return IntentCandidate(name, priority, active, reason, targets)

    def _infer_intents(self, board: chess.Board, side: chess.Color) -> List[IntentCandidate]:
        material = self._material_score(board, side)
        developed = self._development_count(board, side)
        center = self._center_control_count(board, side)
        king_safe = self._king_safe(board, side)
        forcing = self._legal_forcing_moves(board)
        fullmove = board.fullmove_number

        own_queens = len(board.pieces(chess.QUEEN, side))
        enemy_units = sum(
            len(board.pieces(pt, not side))
            for pt in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
        )

        candidates = [
            self._candidate(
                "neutralise_critical_threat",
                10000 if board.is_check() else 0,
                board.is_check(),
                "own king is in check" if board.is_check() else "no immediate king check",
                ["escape_check", "capture_checking_piece", "block_check"],
            ),
            self._candidate(
                "convert_passed_pawn",
                8500 if self._has_passed_pawn(board, side) else 0,
                self._has_passed_pawn(board, side),
                "own passed pawn exists" if self._has_passed_pawn(board, side) else "no passed pawn priority",
                ["push_passed_pawn", "support_passed_pawn", "promote"],
            ),
            self._candidate(
                "build_mate_net",
                8000 if own_queens >= 1 and enemy_units <= 2 else 0,
                own_queens >= 1 and enemy_units <= 2,
                "queen conversion material permits mate-net" if own_queens >= 1 and enemy_units <= 2 else "not a queen mate-net position",
                ["reduce_enemy_king_mobility", "force_edge", "bring_king", "check"],
            ),
            self._candidate(
                "king_safety",
                7600 if not king_safe else 1200,
                not king_safe,
                "king is not yet safely placed" if not king_safe else "king currently safe",
                ["castle", "improve_pawn_shield", "avoid_open_file_near_king"],
            ),
            self._candidate(
                "rapid_development",
                7000 if fullmove <= 12 and developed < 4 else 1000,
                fullmove <= 12 and developed < 4,
                f"opening development incomplete: developed={developed}",
                ["develop_knights", "develop_bishops", "connect_rooks"],
            ),
            self._candidate(
                "center_control",
                6800 if fullmove <= 15 and center < 3 else 1300,
                fullmove <= 15 and center < 3,
                f"center control count={center}",
                ["occupy_center", "attack_center", "support_center"],
            ),
            self._candidate(
                "simplify_when_ahead",
                6500 if material >= 500 else 0,
                material >= 500,
                f"material advantage={material}",
                ["trade_major_pieces", "reduce_counterplay", "enter_winning_endgame"],
            ),
            self._candidate(
                "initiative_pressure",
                6100 if forcing >= 3 else 1600,
                forcing >= 3,
                f"forcing moves available={forcing}",
                ["checks", "captures", "threats", "reduce_opponent_choice_width"],
            ),
            self._candidate(
                "improve_position",
                1000,
                True,
                "fallback proactive improvement intent",
                ["improve_piece_activity", "reduce_weaknesses", "prepare_future_threat"],
            ),
        ]

        candidates.sort(key=lambda c: (c.priority, c.intent_name), reverse=True)
        return candidates

    def _bias_for_intent(self, intent: str) -> Dict[str, int]:
        return {
            "center_control": {"center_pawn_move": 900, "develop_minor_piece": 700, "queen_early_move": -500},
            "rapid_development": {"develop_minor_piece": 1000, "castle": 900, "queen_early_move": -700},
            "king_safety": {"castle": 1400, "king_escape": 1200, "pawn_shield": 800},
            "initiative_pressure": {"check": 1000, "capture": 700, "threat": 600, "reduce_choice_width": 900},
            "simplify_when_ahead": {"trade_piece": 1200, "avoid_complication": 800, "queen_trade": 1300},
            "convert_passed_pawn": {"promote": 3000, "push_passed_pawn": 1800, "support_passed_pawn": 1100},
            "build_mate_net": {"check": 1200, "reduce_king_mobility": 1600, "force_king_edge": 1400},
            "neutralise_critical_threat": {"escape_check": 3000, "capture_threat": 2200, "block_threat": 1800},
            "improve_position": {"piece_activity": 600, "king_safety": 500, "space_gain": 400},
        }.get(intent, {"piece_activity": 300})

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        emergency_override_signal: bool = False,
        emergency_override_reason: str = "",
        task_name: str = "full_chess_proactive_plan_primacy_intent_driver",
    ) -> ProactivePlanPrimacyIntentDriverResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        previous_intent = str(self.policy.get("last_active_intent") or "")
        candidates = self._infer_intents(board, side)

        emergency_override_active = bool(emergency_override_signal or board.is_check())
        if board.is_check() and not emergency_override_reason:
            emergency_override_reason = "own king is in check"

        active_intent = "neutralise_critical_threat" if emergency_override_active else candidates[0].intent_name
        intent_changed = bool(previous_intent and previous_intent != active_intent)

        intent_commitment_score = 1000
        if previous_intent == active_intent and previous_intent:
            intent_commitment_score += 1500
        if intent_changed:
            intent_commitment_score -= 700
        if emergency_override_active:
            intent_commitment_score -= 300

        intent_progress_score = candidates[0].priority + intent_commitment_score
        forcing = self._legal_forcing_moves(board)
        opponent_forced_to_react = forcing >= 3 or active_intent in {
            "initiative_pressure",
            "build_mate_net",
            "convert_passed_pawn",
            "neutralise_critical_threat",
        }

        move_bias = self._bias_for_intent(active_intent)

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "active_intent": active_intent,
            "previous_intent": previous_intent,
            "intent_changed": intent_changed,
            "emergency_override_active": emergency_override_active,
            "intent_progress_score": intent_progress_score,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["intent_driver_run_count"] = int(self.policy.get("intent_driver_run_count", 0)) + 1
        self.policy["last_active_intent"] = active_intent
        self.policy["last_trace_hash"] = trace_hash

        if intent_changed:
            self.policy["intent_change_count"] = int(self.policy.get("intent_change_count", 0)) + 1
        else:
            self.policy["intent_continuity_count"] = int(self.policy.get("intent_continuity_count", 0)) + 1
        if emergency_override_active:
            self.policy["emergency_override_count"] = int(self.policy.get("emergency_override_count", 0)) + 1

        evidence = {
            "proactive_intent_driver_active": True,
            "plan_primacy_enabled": True,
            "previous_intent_loaded": bool(previous_intent),
            "intent_candidates_ranked": True,
            "emergency_override_enabled": True,
            "intent_move_bias_emitted": True,
            "opponent_forced_to_react_signal_emitted": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ProactivePlanPrimacyIntentDriverResult(
            kernel_version="phase22e36_full_chess_proactive_plan_primacy_intent_driver_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            proactive_intent_driver_active=True,
            active_intent=active_intent,
            previous_intent=previous_intent,
            intent_changed=intent_changed,
            emergency_override_active=emergency_override_active,
            emergency_override_reason=emergency_override_reason,
            intent_commitment_score=intent_commitment_score,
            intent_progress_score=intent_progress_score,
            opponent_forced_to_react=opponent_forced_to_react,
            recommended_intent_move_bias=move_bias,
            intent_candidates=[asdict(c) for c in candidates],
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_intent_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements proactive plan primacy and intent driving. AION chooses an active strategic "
                "intent and prefers moves that advance that intent, while allowing emergency tactical override for "
                "checks, critical threats, or safety failures. It does not call Stockfish, does not use LLM move "
                "judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_proactive_plan_primacy_intent_driver_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    emergency_override_signal: bool = False,
    emergency_override_reason: str = "",
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_proactive_plan_primacy_intent_driver",
) -> ProactivePlanPrimacyIntentDriverResult:
    return AionProactivePlanPrimacyIntentDriverKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        emergency_override_signal=emergency_override_signal,
        emergency_override_reason=emergency_override_reason,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Proactive plan primacy intent memory saved to: {result.memory_path}")
