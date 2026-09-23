from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_zugzwang_choice_architecture_selector_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass(frozen=True)
class ZugzwangCandidate:
    move: str
    score: int
    is_legal: bool
    gives_check: bool
    is_capture: bool
    captured_piece_type: Optional[str]
    is_promotion: bool
    is_checkmate: bool
    opponent_choice_width_after: int
    opponent_check_reply_count: int
    opponent_capture_reply_count: int
    enemy_king_mobility_after: int
    own_material_after: int
    opponent_material_after: int
    material_delta_after: int
    repeated_move_penalty_applied: bool
    repeated_to_square_penalty_applied: bool
    explanation: str


@dataclass(frozen=True)
class ZugzwangChoiceArchitectureResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    candidate_count: int
    selected_move: str
    selected_move_is_legal: bool
    selected_score: int
    selected_explanation: str
    top_candidates: List[Dict[str, Any]]
    choice_architecture_active: bool
    opponent_choice_width_after: int
    trace_hash: str
    policy_memory_mutated: bool
    final_choice_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionZugzwangChoiceArchitectureSelectorKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "choice_architecture_run_count": 0,
            "last_selected_move": None,
            "last_opponent_choice_width_after": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("zugzwang_choice_architecture_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ZugzwangChoiceArchitectureResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e27_zugzwang_choice_architecture_memory_v1",
            "task_name": result.task_name,
            "zugzwang_choice_architecture_policy": result.final_choice_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _material(self, board: chess.Board, colour: chess.Color) -> int:
        total = 0
        for piece_type, value in PIECE_VALUES.items():
            total += len(board.pieces(piece_type, colour)) * value
        return total

    def _enemy_king_mobility(self, board: chess.Board, enemy: chess.Color) -> int:
        king_square = board.king(enemy)
        if king_square is None:
            return 0

        count = 0
        for target in chess.SquareSet(chess.BB_KING_ATTACKS[king_square]):
            test = board.copy(stack=False)
            move = chess.Move(king_square, target)
            if move in test.legal_moves:
                count += 1
        return count

    def _opponent_reply_profile(self, board_after: chess.Board) -> Dict[str, int]:
        legal_replies = list(board_after.legal_moves)
        check_count = 0
        capture_count = 0

        for reply in legal_replies:
            probe = board_after.copy(stack=False)
            is_capture = probe.is_capture(reply)
            probe.push(reply)
            if probe.is_check():
                check_count += 1
            if is_capture:
                capture_count += 1

        return {
            "choice_width": len(legal_replies),
            "check_replies": check_count,
            "capture_replies": capture_count,
        }

    def _score_candidate(
        self,
        board: chess.Board,
        move: chess.Move,
        repeated_moves: List[str],
        repeated_to_squares: List[str],
    ) -> ZugzwangCandidate:
        mover = board.turn
        enemy = not mover
        captured_piece = board.piece_at(move.to_square)
        is_capture = board.is_capture(move)

        board_after = board.copy(stack=False)
        board_after.push(move)

        gives_check = board_after.is_check()
        is_checkmate = board_after.is_checkmate()
        is_promotion = move.promotion is not None

        own_material = self._material(board_after, mover)
        opponent_material = self._material(board_after, enemy)
        material_delta = own_material - opponent_material

        reply_profile = self._opponent_reply_profile(board_after)
        opponent_choice_width = reply_profile["choice_width"]
        opponent_check_reply_count = reply_profile["check_replies"]
        opponent_capture_reply_count = reply_profile["capture_replies"]
        enemy_king_mobility = self._enemy_king_mobility(board_after, enemy)

        move_uci = move.uci()
        to_square = chess.square_name(move.to_square)

        repeated_move_penalty = move_uci in repeated_moves
        repeated_to_square_penalty = to_square in repeated_to_squares

        score = 0
        reasons: List[str] = []

        if is_checkmate:
            score += 100000
            reasons.append("checkmate")

        if gives_check:
            score += 900
            reasons.append("gives check")

        if is_capture and captured_piece:
            capture_value = PIECE_VALUES.get(captured_piece.piece_type, 0)
            score += 350 + capture_value
            reasons.append(f"captures {captured_piece.symbol()}")

        if is_promotion:
            score += 1600
            reasons.append("promotion")

        # Core choice architecture: make opponent's reply set smaller and worse.
        score += max(0, 40 - opponent_choice_width) * 35
        reasons.append(f"opponent replies={opponent_choice_width}")

        score += max(0, 8 - enemy_king_mobility) * 45
        reasons.append(f"enemy king mobility={enemy_king_mobility}")

        # Replies that check/capture are dangerous, so reduce score.
        score -= opponent_check_reply_count * 150
        score -= opponent_capture_reply_count * 55

        if opponent_check_reply_count:
            reasons.append(f"opponent check replies={opponent_check_reply_count}")

        if opponent_capture_reply_count:
            reasons.append(f"opponent capture replies={opponent_capture_reply_count}")

        # Prefer positions where our material relation improves.
        score += material_delta // 4
        reasons.append(f"material delta={material_delta}")

        # Strongly penalise oscillation and returning to known squares.
        if repeated_move_penalty:
            score -= 900
            reasons.append("repeated move penalty")

        if repeated_to_square_penalty:
            score -= 300
            reasons.append("repeated destination penalty")

        # Tiny deterministic tie-breaker so output is stable.
        score += 10 - (move.from_square % 5) - (move.to_square % 5)

        captured_name = None
        if captured_piece:
            captured_name = chess.piece_name(captured_piece.piece_type)

        return ZugzwangCandidate(
            move=move_uci,
            score=score,
            is_legal=True,
            gives_check=gives_check,
            is_capture=is_capture,
            captured_piece_type=captured_name,
            is_promotion=is_promotion,
            is_checkmate=is_checkmate,
            opponent_choice_width_after=opponent_choice_width,
            opponent_check_reply_count=opponent_check_reply_count,
            opponent_capture_reply_count=opponent_capture_reply_count,
            enemy_king_mobility_after=enemy_king_mobility,
            own_material_after=own_material,
            opponent_material_after=opponent_material,
            material_delta_after=material_delta,
            repeated_move_penalty_applied=repeated_move_penalty,
            repeated_to_square_penalty_applied=repeated_to_square_penalty,
            explanation="; ".join(reasons),
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        repeated_to_squares: Optional[List[str]] = None,
        task_name: str = "full_chess_zugzwang_choice_architecture_selector",
    ) -> ZugzwangChoiceArchitectureResult:
        repeated_moves = list(repeated_moves or [])
        repeated_to_squares = list(repeated_to_squares or [])

        board = chess.Board(input_fen)
        expected_turn = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        if board.turn != expected_turn:
            board.turn = expected_turn

        candidates = [
            self._score_candidate(board, move, repeated_moves, repeated_to_squares)
            for move in board.legal_moves
        ]

        candidates.sort(
            key=lambda c: (
                c.score,
                -c.opponent_choice_width_after,
                -c.opponent_check_reply_count,
                -c.opponent_capture_reply_count,
                c.move,
            ),
            reverse=True,
        )

        selected = candidates[0] if candidates else None

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "selected_move": selected.move if selected else "",
            "selected_score": selected.score if selected else 0,
            "opponent_choice_width_after": selected.opponent_choice_width_after if selected else 0,
            "candidate_count": len(candidates),
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["choice_architecture_run_count"] = int(self.policy.get("choice_architecture_run_count", 0)) + 1
        self.policy["last_selected_move"] = selected.move if selected else ""
        self.policy["last_opponent_choice_width_after"] = selected.opponent_choice_width_after if selected else None
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "zugzwang_choice_architecture_active": True,
            "opponent_choice_width_scored": True,
            "opponent_check_replies_penalised": True,
            "opponent_capture_replies_penalised": True,
            "enemy_king_mobility_scored": True,
            "repetition_penalty_enabled": True,
            "material_delta_scored": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ZugzwangChoiceArchitectureResult(
            kernel_version="phase22e27_full_chess_zugzwang_choice_architecture_selector_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_count=len(candidates),
            selected_move=selected.move if selected else "",
            selected_move_is_legal=bool(selected and selected.is_legal),
            selected_score=selected.score if selected else 0,
            selected_explanation=selected.explanation if selected else "",
            top_candidates=[asdict(c) for c in candidates[:8]],
            choice_architecture_active=True,
            opponent_choice_width_after=selected.opponent_choice_width_after if selected else 0,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_choice_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements Zugzwang choice architecture scoring. It scores moves by how strongly "
                "they narrow and degrade the opponent reply set. It does not call Stockfish, does not use LLM "
                "move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_zugzwang_choice_architecture_selector_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    repeated_to_squares: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_zugzwang_choice_architecture_selector",
) -> ZugzwangChoiceArchitectureResult:
    return AionZugzwangChoiceArchitectureSelectorKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_to_squares=repeated_to_squares,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=["d6b8", "b8d6"],
        repeated_to_squares=["b8", "d6"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Zugzwang choice architecture memory saved to: {result.memory_path}")
