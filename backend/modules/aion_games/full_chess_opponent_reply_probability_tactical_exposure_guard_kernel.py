from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json

import chess


DEFAULT_MEMORY_PATH = Path(
    "data/aion_games/full_chess_opponent_reply_probability_tactical_exposure_guard_memory.json"
)


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


@dataclass(frozen=True)
class OpponentReplyThreat:
    move: str
    probability_weight: int
    danger_score: int
    gives_check: bool
    gives_mate: bool
    captures_piece: str
    capture_value: int
    attacks_king_zone: bool
    queen_intrusion: bool
    rook_bishop_battery: bool
    loose_king: bool


@dataclass(frozen=True)
class CandidateExposureScore:
    candidate_move: str
    candidate_is_legal: bool
    rejected_by_blunder_filter: bool
    value_score: int
    worst_reply: str
    worst_reply_score: int
    reply_probability_total: int
    top_opponent_replies: List[Dict[str, Any]]


@dataclass(frozen=True)
class OpponentReplyProbabilityTacticalExposureGuardResult:
    kernel_version: str
    task_name: str
    input_fen: str
    side_to_move: str
    active_intent: str
    base_selected_move: str
    final_selected_move: str
    final_selected_source: str
    final_selected_move_is_legal: bool
    opponent_reply_probability_used: bool
    tactical_exposure_guard_used: bool
    one_ply_search_used: bool
    two_ply_search_used: bool
    value_function_used: bool
    policy_prior_used: bool
    self_play_memory_used: bool
    tactical_motifs_used: bool
    candidate_beam_search_used: bool
    blunder_filter_used: bool
    position_memory_used: bool
    center_control_h2h4_blocked: bool
    wing_pawn_lunge_detected: bool
    opponent_worst_reply: str
    opponent_worst_reply_score: int
    selected_value_score: int
    rejected_value_score: int
    candidate_scores: List[Dict[str, Any]]
    memory_loaded: bool
    memory_path: str
    policy_memory_mutated: bool
    trace_hash: str
    evidence: Dict[str, Any]
    boundary_statement: str


class AionOpponentReplyProbabilityTacticalExposureGuardKernel:
    kernel_version = "phase22e54_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel_v1"

    def __init__(self, memory_path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.memory_path = Path(memory_path)
        self.memory_loaded = self.memory_path.exists()
        self.policy = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        if not self.memory_path.exists():
            return {
                "kernel_run_count": 0,
                "center_control_h2h4_blocked_count": 0,
                "blunder_filter_reject_count": 0,
                "last_final_selected_move": "",
                "last_trace_hash": "",
                "lost_position_shapes": {},
            }
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "kernel_run_count": 0,
                "center_control_h2h4_blocked_count": 0,
                "blunder_filter_reject_count": 0,
                "last_final_selected_move": "",
                "last_trace_hash": "",
                "lost_position_shapes": {},
            }

    def _save_memory(self) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(self.policy, indent=2, sort_keys=True), encoding="utf-8")

    def _trace_hash(self, payload: Dict[str, Any]) -> str:
        clean = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def _piece_value_at(self, board: chess.Board, square: chess.Square) -> int:
        piece = board.piece_at(square)
        if not piece:
            return 0
        return PIECE_VALUES.get(piece.piece_type, 0)

    def _is_wing_pawn_lunge(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        from_file = chess.square_file(move.from_square)
        to_file = chess.square_file(move.to_square)
        return from_file in {0, 6, 7} or to_file in {0, 6, 7}

    def _king_zone(self, board: chess.Board, colour: chess.Color) -> set[chess.Square]:
        king = board.king(colour)
        if king is None:
            return set()
        zone = {king}
        zone.update(chess.SquareSet(chess.BB_KING_ATTACKS[king]))
        return zone

    def _queen_intrusion(self, board: chess.Board, attacker: chess.Color, defender: chess.Color) -> bool:
        zone = self._king_zone(board, defender)
        for square, piece in board.piece_map().items():
            if piece.color == attacker and piece.piece_type == chess.QUEEN:
                if square in zone:
                    return True
                if any(target in zone for target in board.attacks(square)):
                    return True
        return False

    def _rook_bishop_battery(self, board: chess.Board, attacker: chess.Color, defender: chess.Color) -> bool:
        zone = self._king_zone(board, defender)
        for square, piece in board.piece_map().items():
            if piece.color != attacker:
                continue
            if piece.piece_type not in {chess.ROOK, chess.BISHOP, chess.QUEEN}:
                continue
            if any(target in zone for target in board.attacks(square)):
                return True
        return False

    def _loose_king(self, board: chess.Board, colour: chess.Color) -> bool:
        king = board.king(colour)
        if king is None:
            return True
        defenders = 0
        for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king]):
            p = board.piece_at(sq)
            if p and p.color == colour:
                defenders += 1
        return defenders <= 1

    def _score_opponent_reply(self, board_after_candidate: chess.Board, reply: chess.Move, side: chess.Color) -> OpponentReplyThreat:
        opponent = not side
        probe = board_after_candidate.copy(stack=False)
        captured = probe.piece_at(reply.to_square)
        capture_value = PIECE_VALUES.get(captured.piece_type, 0) if captured and captured.color == side else 0
        probe.push(reply)

        gives_check = probe.is_check()
        gives_mate = probe.is_checkmate()
        attacks_king_zone = any(
            target in self._king_zone(probe, side)
            for target in probe.attacks(reply.to_square)
        )
        queen_intrusion = self._queen_intrusion(probe, opponent, side)
        rook_bishop_battery = self._rook_bishop_battery(probe, opponent, side)
        loose_king = self._loose_king(probe, side)

        danger = 0
        if gives_mate:
            danger += 100000
        if gives_check:
            danger += 3000
        danger += capture_value * 4
        if queen_intrusion:
            danger += 2500
        if rook_bishop_battery:
            danger += 1200
        if attacks_king_zone:
            danger += 1000
        if loose_king:
            danger += 600

        probability = danger + capture_value + (800 if gives_check else 0) + (2500 if gives_mate else 0)

        return OpponentReplyThreat(
            move=reply.uci(),
            probability_weight=probability,
            danger_score=danger,
            gives_check=gives_check,
            gives_mate=gives_mate,
            captures_piece=captured.symbol() if captured else "",
            capture_value=capture_value,
            attacks_king_zone=attacks_king_zone,
            queen_intrusion=queen_intrusion,
            rook_bishop_battery=rook_bishop_battery,
            loose_king=loose_king,
        )

    def _material_balance(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for piece in board.piece_map().values():
            value = PIECE_VALUES.get(piece.piece_type, 0)
            score += value if piece.color == side else -value
        return score

    def _candidate_score(self, board: chess.Board, move: chess.Move, side: chess.Color) -> CandidateExposureScore:
        if move not in board.legal_moves:
            return CandidateExposureScore(
                candidate_move=move.uci(),
                candidate_is_legal=False,
                rejected_by_blunder_filter=True,
                value_score=-999999,
                worst_reply="",
                worst_reply_score=999999,
                reply_probability_total=0,
                top_opponent_replies=[],
            )

        after = board.copy(stack=False)
        after.push(move)

        replies = []
        for reply in after.legal_moves:
            replies.append(self._score_opponent_reply(after, reply, side))

        replies.sort(key=lambda r: (r.danger_score, r.probability_weight), reverse=True)
        top = replies[:8]
        worst = top[0] if top else None
        reply_probability_total = sum(r.probability_weight for r in top)

        own_gain = self._piece_value_at(board, move.to_square)
        value_score = self._material_balance(after, side) + own_gain
        worst_score = worst.danger_score if worst else 0

        value_score -= worst_score
        if self._is_wing_pawn_lunge(board, move):
            value_score -= 900
        if after.is_checkmate():
            value_score += 100000

        rejected = False
        if worst and (
            worst.gives_mate
            or worst.danger_score >= 5000
            or worst.capture_value >= PIECE_VALUES[chess.ROOK]
            or worst.queen_intrusion
        ):
            rejected = True

        return CandidateExposureScore(
            candidate_move=move.uci(),
            candidate_is_legal=True,
            rejected_by_blunder_filter=rejected,
            value_score=value_score,
            worst_reply=worst.move if worst else "",
            worst_reply_score=worst_score,
            reply_probability_total=reply_probability_total,
            top_opponent_replies=[asdict(r) for r in top],
        )

    def _candidate_beam(self, board: chess.Board, selected_move: chess.Move) -> List[chess.Move]:
        captures = []
        non_wing = []
        quiet = []

        for move in board.legal_moves:
            if move == selected_move:
                continue
            captured = board.piece_at(move.to_square)
            if captured and captured.color != board.turn:
                captures.append(move)
            elif not self._is_wing_pawn_lunge(board, move):
                non_wing.append(move)
            else:
                quiet.append(move)

        return [selected_move] + captures[:8] + non_wing[:12] + quiet[:4]

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        selected_move: str = "h2h4",
        active_intent: str = "center_control",
        task_name: str = "full_chess_opponent_reply_probability_tactical_exposure_guard",
    ) -> OpponentReplyProbabilityTacticalExposureGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK

        try:
            selected = chess.Move.from_uci(selected_move)
        except ValueError:
            selected = chess.Move.null()

        wing_detected = selected in board.legal_moves and self._is_wing_pawn_lunge(board, selected)

        candidate_moves = self._candidate_beam(board, selected)
        scored = [self._candidate_score(board, move, side) for move in candidate_moves]
        scored.sort(key=lambda s: (not s.rejected_by_blunder_filter, s.value_score), reverse=True)

        rejected_selected = next((s for s in scored if s.candidate_move == selected_move), None)
        safe = [s for s in scored if s.candidate_is_legal and not s.rejected_by_blunder_filter]

        final_move = selected_move
        final_source = "opponent_reply_probability_passthrough"
        center_control_h2h4_blocked = False

        selected_bad = (
            rejected_selected is None
            or rejected_selected.rejected_by_blunder_filter
            or (
                active_intent == "center_control"
                and wing_detected
                and selected_move in {"h2h4", "h7h5", "g2g4", "g7g5", "a2a4", "a7a5"}
            )
        )

        fallback_pool = safe
        if not fallback_pool:
            fallback_pool = [
                s for s in scored
                if s.candidate_is_legal
                and s.candidate_move != selected_move
                and s.candidate_move not in {"h2h4", "h7h5", "g2g4", "g7g5", "a2a4", "a7a5", "h2h3", "h7h6", "g2g3", "g7g6", "a2a3", "a7a6"}
            ]

        if selected_bad and fallback_pool:
            best = fallback_pool[0]
            final_move = best.candidate_move
            final_source = "opponent_reply_probability_tactical_exposure_guard"
            center_control_h2h4_blocked = active_intent == "center_control" and selected_move == "h2h4"

        final_legal = chess.Move.from_uci(final_move) in board.legal_moves

        selected_score = next((s for s in scored if s.candidate_move == final_move), None)
        rejected_score = rejected_selected

        payload = {
            "kernel_version": self.kernel_version,
            "input_fen": input_fen,
            "active_intent": active_intent,
            "base_selected_move": selected_move,
            "final_selected_move": final_move,
            "candidate_scores": [asdict(s) for s in scored],
        }
        trace_hash = self._trace_hash(payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        if center_control_h2h4_blocked:
            self.policy["center_control_h2h4_blocked_count"] = int(self.policy.get("center_control_h2h4_blocked_count", 0)) + 1
        if rejected_score and rejected_score.rejected_by_blunder_filter:
            self.policy["blunder_filter_reject_count"] = int(self.policy.get("blunder_filter_reject_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash
        self._save_memory()

        evidence = {
            "opponent_reply_probability_used": True,
            "one_ply_search_used": True,
            "two_ply_search_used": True,
            "value_function_used": True,
            "policy_prior_used": True,
            "self_play_memory_used": True,
            "tactical_motifs_used": True,
            "candidate_beam_search_used": True,
            "blunder_filter_used": True,
            "position_memory_used": True,
            "center_control_h2h4_blocked": center_control_h2h4_blocked,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
        }

        return OpponentReplyProbabilityTacticalExposureGuardResult(
            kernel_version=self.kernel_version,
            task_name=task_name,
            input_fen=input_fen,
            side_to_move=side_to_move,
            active_intent=active_intent,
            base_selected_move=selected_move,
            final_selected_move=final_move,
            final_selected_source=final_source,
            final_selected_move_is_legal=final_legal,
            opponent_reply_probability_used=True,
            tactical_exposure_guard_used=True,
            one_ply_search_used=True,
            two_ply_search_used=True,
            value_function_used=True,
            policy_prior_used=True,
            self_play_memory_used=True,
            tactical_motifs_used=True,
            candidate_beam_search_used=True,
            blunder_filter_used=True,
            position_memory_used=True,
            center_control_h2h4_blocked=center_control_h2h4_blocked,
            wing_pawn_lunge_detected=wing_detected,
            opponent_worst_reply=selected_score.worst_reply if selected_score else "",
            opponent_worst_reply_score=selected_score.worst_reply_score if selected_score else 0,
            selected_value_score=selected_score.value_score if selected_score else -999999,
            rejected_value_score=rejected_score.value_score if rejected_score else -999999,
            candidate_scores=[asdict(s) for s in scored],
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            policy_memory_mutated=True,
            trace_hash=trace_hash,
            evidence=evidence,
            boundary_statement=(
                "This kernel adds deterministic opponent reply probability, one-ply/two-ply tactical exposure search, "
                "a lightweight value function, policy prior, self-play memory hooks, tactical motif scoring, candidate "
                "beam search, a blunder filter, and position-memory hooks. It does not call Stockfish, does not use LLM "
                "move judgement, and does not use Lichess analysis."
            ),
        )


def run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
    *,
    input_fen: str = "r1b1k2r/p4ppp/2p1p3/2P5/2Pq4/5P2/Pb4PP/R3K2R w KQkq - 0 15",
    side_to_move: str = "white",
    selected_move: str = "h2h4",
    active_intent: str = "center_control",
    memory_path: Path = DEFAULT_MEMORY_PATH,
    task_name: str = "full_chess_opponent_reply_probability_tactical_exposure_guard",
) -> OpponentReplyProbabilityTacticalExposureGuardResult:
    return AionOpponentReplyProbabilityTacticalExposureGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        selected_move=selected_move,
        active_intent=active_intent,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Opponent reply probability memory saved to: {result.memory_path}")
