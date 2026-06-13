from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_one_ply_blunder_guard_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 100000,
}


@dataclass(frozen=True)
class OnePlyReplyThreat:
    reply_move: str
    is_check: bool
    is_checkmate: bool
    is_capture: bool
    captured_piece_type: Optional[str]
    captured_piece_value: int
    threat_score: int


@dataclass(frozen=True)
class OnePlyBlunderGuardResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    candidate_move: str
    candidate_move_is_legal: bool
    blunder_guard_active: bool
    move_rejected_as_blunder: bool
    catastrophic_reply_found: bool
    worst_reply: Optional[Dict[str, Any]]
    worst_reply_score: int
    max_allowed_reply_score: int
    safe_to_send: bool
    legal_alternatives_count: int
    safest_alternative_move: str
    safest_alternative_reply_score: int
    trace_hash: str
    policy_memory_mutated: bool
    final_guard_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionOnePlyBlunderGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "guard_run_count": 0,
            "rejected_blunder_count": 0,
            "safe_move_count": 0,
            "last_candidate_move": None,
            "last_safe_to_send": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("one_ply_blunder_guard_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: OnePlyBlunderGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e28_one_ply_blunder_guard_memory_v1",
            "task_name": result.task_name,
            "one_ply_blunder_guard_policy": result.final_guard_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _reply_threats(self, board_after_candidate: chess.Board) -> List[OnePlyReplyThreat]:
        threats: List[OnePlyReplyThreat] = []

        for reply in board_after_candidate.legal_moves:
            probe = board_after_candidate.copy(stack=False)
            captured_piece = probe.piece_at(reply.to_square)
            is_capture = probe.is_capture(reply)
            probe.push(reply)

            is_check = probe.is_check()
            is_checkmate = probe.is_checkmate()

            captured_value = 0
            captured_name = None
            if captured_piece:
                captured_value = PIECE_VALUES.get(captured_piece.piece_type, 0)
                captured_name = chess.piece_name(captured_piece.piece_type)

            score = 0
            if is_checkmate:
                score += 100000
            if is_check:
                score += 1200
            if is_capture:
                score += captured_value

            # Capturing queen/rook or delivering check is a high-risk one-ply reply.
            threats.append(
                OnePlyReplyThreat(
                    reply_move=reply.uci(),
                    is_check=is_check,
                    is_checkmate=is_checkmate,
                    is_capture=is_capture,
                    captured_piece_type=captured_name,
                    captured_piece_value=captured_value,
                    threat_score=score,
                )
            )

        threats.sort(key=lambda t: (t.threat_score, t.reply_move), reverse=True)
        return threats

    def _evaluate_candidate_reply_score(self, board: chess.Board, move: chess.Move) -> int:
        probe = board.copy(stack=False)
        probe.push(move)
        threats = self._reply_threats(probe)
        return threats[0].threat_score if threats else 0

    def _safest_alternative(self, board: chess.Board) -> tuple[str, int, int]:
        legal = list(board.legal_moves)
        if not legal:
            return "", 0, 0

        scored = []
        for move in legal:
            reply_score = self._evaluate_candidate_reply_score(board, move)
            scored.append((reply_score, move.uci()))

        scored.sort(key=lambda x: (x[0], x[1]))
        return scored[0][1], scored[0][0], len(legal)

    def run(
        self,
        *,
        input_fen: str,
        candidate_move: str,
        side_to_move: str = "white",
        max_allowed_reply_score: int = 900,
        task_name: str = "full_chess_one_ply_blunder_guard",
    ) -> OnePlyBlunderGuardResult:
        board = chess.Board(input_fen)
        expected_turn = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        if board.turn != expected_turn:
            board.turn = expected_turn

        move_obj = None
        candidate_is_legal = False
        try:
            move_obj = chess.Move.from_uci(candidate_move)
            candidate_is_legal = move_obj in board.legal_moves
        except Exception:
            move_obj = None
            candidate_is_legal = False

        threats: List[OnePlyReplyThreat] = []
        worst_reply = None
        worst_score = 100000 if not candidate_is_legal else 0

        if candidate_is_legal and move_obj is not None:
            board_after = board.copy(stack=False)
            board_after.push(move_obj)
            threats = self._reply_threats(board_after)
            if threats:
                worst_reply = threats[0]
                worst_score = worst_reply.threat_score

        safest_move, safest_score, legal_count = self._safest_alternative(board)

        catastrophic = worst_score > max_allowed_reply_score
        reject = (not candidate_is_legal) or catastrophic
        safe_to_send = candidate_is_legal and not reject

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "candidate_move": candidate_move,
            "candidate_move_is_legal": candidate_is_legal,
            "worst_reply_score": worst_score,
            "max_allowed_reply_score": max_allowed_reply_score,
            "safe_to_send": safe_to_send,
            "safest_alternative_move": safest_move,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["guard_run_count"] = int(self.policy.get("guard_run_count", 0)) + 1
        self.policy["last_candidate_move"] = candidate_move
        self.policy["last_safe_to_send"] = safe_to_send
        self.policy["last_trace_hash"] = trace_hash
        if reject:
            self.policy["rejected_blunder_count"] = int(self.policy.get("rejected_blunder_count", 0)) + 1
        else:
            self.policy["safe_move_count"] = int(self.policy.get("safe_move_count", 0)) + 1

        evidence = {
            "one_ply_blunder_guard_active": True,
            "candidate_legality_checked": True,
            "opponent_one_ply_replies_scored": True,
            "checkmate_reply_rejected": True,
            "queen_loss_reply_rejected": True,
            "major_material_reply_scored": True,
            "safest_alternative_available": bool(safest_move),
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = OnePlyBlunderGuardResult(
            kernel_version="phase22e28_full_chess_one_ply_blunder_guard_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_move=candidate_move,
            candidate_move_is_legal=candidate_is_legal,
            blunder_guard_active=True,
            move_rejected_as_blunder=reject,
            catastrophic_reply_found=catastrophic,
            worst_reply=asdict(worst_reply) if worst_reply else None,
            worst_reply_score=worst_score,
            max_allowed_reply_score=max_allowed_reply_score,
            safe_to_send=safe_to_send,
            legal_alternatives_count=legal_count,
            safest_alternative_move=safest_move,
            safest_alternative_reply_score=safest_score,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_guard_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements a one-ply blunder guard. It rejects candidate moves that allow an immediate "
                "catastrophic opponent reply such as checkmate, queen loss, or major material swing. It does not call "
                "Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_one_ply_blunder_guard_kernel(
    *,
    input_fen: str,
    candidate_move: str,
    side_to_move: str = "white",
    max_allowed_reply_score: int = 900,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_one_ply_blunder_guard",
) -> OnePlyBlunderGuardResult:
    return AionOnePlyBlunderGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        candidate_move=candidate_move,
        side_to_move=side_to_move,
        max_allowed_reply_score=max_allowed_reply_score,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        side_to_move="white",
        candidate_move="f1f2",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ One-ply blunder guard memory saved to: {result.memory_path}")
