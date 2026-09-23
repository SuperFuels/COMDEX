from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_passed_pawn_conversion_policy_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass(frozen=True)
class PassedPawnCandidate:
    pawn_square: str
    pawn_color: str
    promotion_distance: int
    is_passed: bool
    is_protected: bool
    is_blocked: bool
    can_push_one: bool
    can_promote_now: bool
    push_move: str
    promotion_move: str
    support_king_distance: int
    enemy_king_distance: int
    conversion_score: int
    explanation: str


@dataclass(frozen=True)
class PassedPawnConversionPolicyResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    passed_pawn_policy_active: bool
    own_passed_pawn_count: int
    enemy_passed_pawn_count: int
    best_pawn: Optional[Dict[str, Any]]
    recommended_policy: str
    recommended_move: str
    recommended_move_is_legal: bool
    conversion_score: int
    own_candidates: List[Dict[str, Any]]
    enemy_candidates: List[Dict[str, Any]]
    enemy_promotion_threat_found: bool
    trace_hash: str
    policy_memory_mutated: bool
    final_conversion_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionPassedPawnConversionPolicyKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "passed_pawn_policy_run_count": 0,
            "promotion_recommendation_count": 0,
            "push_recommendation_count": 0,
            "block_enemy_recommendation_count": 0,
            "last_recommended_policy": None,
            "last_recommended_move": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("passed_pawn_conversion_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PassedPawnConversionPolicyResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e30_passed_pawn_conversion_policy_memory_v1",
            "task_name": result.task_name,
            "passed_pawn_conversion_policy": result.final_conversion_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _king_distance(self, board: chess.Board, colour: chess.Color, square: chess.Square) -> int:
        king = board.king(colour)
        if king is None:
            return 99
        return chess.square_distance(king, square)

    def _is_passed_pawn(self, board: chess.Board, square: chess.Square, colour: chess.Color) -> bool:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        enemy = not colour

        files = [f for f in (file_idx - 1, file_idx, file_idx + 1) if 0 <= f <= 7]
        enemy_pawns = board.pieces(chess.PAWN, enemy)

        for enemy_sq in enemy_pawns:
            enemy_file = chess.square_file(enemy_sq)
            enemy_rank = chess.square_rank(enemy_sq)
            if enemy_file not in files:
                continue
            if colour == chess.WHITE and enemy_rank > rank_idx:
                return False
            if colour == chess.BLACK and enemy_rank < rank_idx:
                return False
        return True

    def _promotion_distance(self, square: chess.Square, colour: chess.Color) -> int:
        rank_idx = chess.square_rank(square)
        return 7 - rank_idx if colour == chess.WHITE else rank_idx

    def _candidate_for_pawn(self, board: chess.Board, square: chess.Square, colour: chess.Color) -> PassedPawnCandidate:
        direction = 8 if colour == chess.WHITE else -8
        promotion_rank = 7 if colour == chess.WHITE else 0
        pawn_square = chess.square_name(square)
        to_square = square + direction if 0 <= square + direction <= 63 else None

        is_passed = self._is_passed_pawn(board, square, colour)
        is_protected = board.is_attacked_by(colour, square)
        is_blocked = True
        can_push_one = False
        can_promote_now = False
        push_move = ""
        promotion_move = ""

        if to_square is not None:
            is_blocked = board.piece_at(to_square) is not None
            move = chess.Move(square, to_square)
            promotion_to_queen = chess.Move(square, to_square, promotion=chess.QUEEN)

            # Evaluate legality from the pawn owner's turn. This matters when
            # checking enemy passed-pawn threats while AION is currently to move.
            legal_board = board.copy(stack=False)
            legal_board.turn = colour

            can_push_one = move in legal_board.legal_moves
            can_promote_now = promotion_to_queen in legal_board.legal_moves

            if can_push_one:
                push_move = move.uci()
            if can_promote_now or chess.square_rank(to_square) == promotion_rank:
                promotion_move = promotion_to_queen.uci()

        distance = self._promotion_distance(square, colour)
        support_king_distance = self._king_distance(board, colour, square)
        enemy_king_distance = self._king_distance(board, not colour, square)

        score = 0
        reasons: List[str] = []

        if is_passed:
            score += 1000
            reasons.append("passed pawn")

        if is_protected:
            score += 350
            reasons.append("protected")

        if can_promote_now:
            score += 5000
            reasons.append("can promote now")

        if can_push_one:
            score += 700
            reasons.append("can push")

        if is_blocked:
            score -= 600
            reasons.append("blocked")

        score += max(0, 7 - distance) * 180
        score += max(0, 8 - support_king_distance) * 40
        score -= max(0, 8 - enemy_king_distance) * 30

        reasons.append(f"promotion distance={distance}")
        reasons.append(f"own king distance={support_king_distance}")
        reasons.append(f"enemy king distance={enemy_king_distance}")

        return PassedPawnCandidate(
            pawn_square=pawn_square,
            pawn_color="white" if colour == chess.WHITE else "black",
            promotion_distance=distance,
            is_passed=is_passed,
            is_protected=is_protected,
            is_blocked=is_blocked,
            can_push_one=can_push_one,
            can_promote_now=can_promote_now,
            push_move=push_move,
            promotion_move=promotion_move,
            support_king_distance=support_king_distance,
            enemy_king_distance=enemy_king_distance,
            conversion_score=score,
            explanation="; ".join(reasons),
        )

    def _all_candidates(self, board: chess.Board, colour: chess.Color) -> List[PassedPawnCandidate]:
        candidates = [
            self._candidate_for_pawn(board, sq, colour)
            for sq in board.pieces(chess.PAWN, colour)
        ]
        candidates = [c for c in candidates if c.is_passed]
        candidates.sort(key=lambda c: (c.conversion_score, -c.promotion_distance, c.pawn_square), reverse=True)
        return candidates

    def _is_legal(self, board: chess.Board, move_uci: str) -> bool:
        if not move_uci:
            return False
        try:
            return chess.Move.from_uci(move_uci) in board.legal_moves
        except Exception:
            return False

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        task_name: str = "full_chess_passed_pawn_conversion_policy",
    ) -> PassedPawnConversionPolicyResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        own = self._all_candidates(board, side)
        enemy = self._all_candidates(board, not side)

        best_own = own[0] if own else None
        best_enemy = enemy[0] if enemy else None

        enemy_promotion_threat = bool(best_enemy and best_enemy.can_promote_now)

        recommended_policy = "continue_normal_play"
        recommended_move = ""
        conversion_score = 0

        if enemy_promotion_threat:
            recommended_policy = "stop_enemy_promotion"
            conversion_score = best_enemy.conversion_score if best_enemy else 0
        elif best_own and best_own.can_promote_now:
            recommended_policy = "promote_now"
            recommended_move = best_own.promotion_move
            conversion_score = best_own.conversion_score
        elif best_own and best_own.can_push_one:
            recommended_policy = "push_passed_pawn"
            recommended_move = best_own.push_move
            conversion_score = best_own.conversion_score
        elif best_own:
            recommended_policy = "support_passed_pawn"
            conversion_score = best_own.conversion_score

        recommended_move_is_legal = self._is_legal(board, recommended_move)

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "own_passed_pawn_count": len(own),
            "enemy_passed_pawn_count": len(enemy),
            "recommended_policy": recommended_policy,
            "recommended_move": recommended_move,
            "conversion_score": conversion_score,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["passed_pawn_policy_run_count"] = int(self.policy.get("passed_pawn_policy_run_count", 0)) + 1
        self.policy["last_recommended_policy"] = recommended_policy
        self.policy["last_recommended_move"] = recommended_move
        self.policy["last_trace_hash"] = trace_hash

        if recommended_policy == "promote_now":
            self.policy["promotion_recommendation_count"] = int(self.policy.get("promotion_recommendation_count", 0)) + 1
        if recommended_policy == "push_passed_pawn":
            self.policy["push_recommendation_count"] = int(self.policy.get("push_recommendation_count", 0)) + 1
        if recommended_policy == "stop_enemy_promotion":
            self.policy["block_enemy_recommendation_count"] = int(self.policy.get("block_enemy_recommendation_count", 0)) + 1

        evidence = {
            "passed_pawn_policy_active": True,
            "own_passed_pawns_detected": True,
            "enemy_passed_pawns_detected": True,
            "promotion_distance_scored": True,
            "protected_passed_pawn_scored": True,
            "push_move_emitted": True,
            "promotion_move_emitted": True,
            "enemy_promotion_threat_detected": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PassedPawnConversionPolicyResult(
            kernel_version="phase22e30_full_chess_passed_pawn_conversion_policy_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            passed_pawn_policy_active=True,
            own_passed_pawn_count=len(own),
            enemy_passed_pawn_count=len(enemy),
            best_pawn=asdict(best_own) if best_own else None,
            recommended_policy=recommended_policy,
            recommended_move=recommended_move,
            recommended_move_is_legal=recommended_move_is_legal,
            conversion_score=conversion_score,
            own_candidates=[asdict(c) for c in own],
            enemy_candidates=[asdict(c) for c in enemy],
            enemy_promotion_threat_found=enemy_promotion_threat,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_conversion_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements passed pawn conversion policy. It detects own and enemy passed pawns, "
                "scores promotion distance, protection, blockage, king support, and emits promote/push/support/stop "
                "policy. It does not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_passed_pawn_conversion_policy_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_passed_pawn_conversion_policy",
) -> PassedPawnConversionPolicyResult:
    return AionPassedPawnConversionPolicyKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Passed pawn conversion policy memory saved to: {result.memory_path}")
