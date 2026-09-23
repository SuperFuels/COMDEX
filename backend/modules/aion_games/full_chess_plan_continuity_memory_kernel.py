from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_plan_continuity_memory.json")


@dataclass(frozen=True)
class PlanContinuityResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    candidate_move: str
    candidate_move_is_legal: bool
    plan_continuity_active: bool
    current_plan: str
    previous_plan: str
    plan_changed: bool
    continuity_score: int
    move_supports_plan: bool
    move_breaks_plan: bool
    plan_reason: str
    recommended_plan: str
    trace_hash: str
    policy_memory_mutated: bool
    final_plan_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionPlanContinuityMemoryKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "plan_memory_run_count": 0,
            "last_plan": "",
            "last_candidate_move": "",
            "plan_change_count": 0,
            "plan_continuity_count": 0,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("plan_continuity_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PlanContinuityResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e32_plan_continuity_memory_v1",
            "task_name": result.task_name,
            "plan_continuity_policy": result.final_plan_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _material_counts(self, board: chess.Board, side: chess.Color) -> Dict[str, int]:
        return {
            "queens": len(board.pieces(chess.QUEEN, side)),
            "rooks": len(board.pieces(chess.ROOK, side)),
            "bishops": len(board.pieces(chess.BISHOP, side)),
            "knights": len(board.pieces(chess.KNIGHT, side)),
            "pawns": len(board.pieces(chess.PAWN, side)),
        }

    def _has_passed_pawn(self, board: chess.Board, side: chess.Color) -> bool:
        enemy = not side
        for sq in board.pieces(chess.PAWN, side):
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            files = [f for f in (file_idx - 1, file_idx, file_idx + 1) if 0 <= f <= 7]
            blocked = False
            for enemy_sq in board.pieces(chess.PAWN, enemy):
                enemy_file = chess.square_file(enemy_sq)
                enemy_rank = chess.square_rank(enemy_sq)
                if enemy_file not in files:
                    continue
                if side == chess.WHITE and enemy_rank > rank_idx:
                    blocked = True
                if side == chess.BLACK and enemy_rank < rank_idx:
                    blocked = True
            if not blocked:
                return True
        return False

    def _infer_plan(self, board: chess.Board, side: chess.Color) -> tuple[str, str]:
        own = self._material_counts(board, side)
        enemy = self._material_counts(board, not side)
        enemy_non_king = sum(enemy.values())
        own_non_king = sum(own.values())

        if board.is_check():
            return "escape_or_neutralise_check", "own king is currently in check"

        if self._has_passed_pawn(board, side):
            return "convert_passed_pawn", "own passed pawn exists"

        if own["queens"] >= 1 and enemy_non_king <= 2:
            return "build_mate_net", "queen conversion material advantage"

        if own["rooks"] >= 1 and enemy_non_king <= 2:
            return "build_rook_box", "rook conversion material advantage"

        if own_non_king > enemy_non_king + 1:
            return "simplify_and_convert", "material advantage exists"

        return "improve_position", "no forced conversion plan detected"

    def _move_supports_plan(self, board: chess.Board, move: chess.Move, plan: str, side: chess.Color) -> tuple[bool, bool, int, str]:
        probe = board.copy(stack=False)
        piece = probe.piece_at(move.from_square)
        is_capture = probe.is_capture(move)
        is_promotion = move.promotion is not None
        probe.push(move)

        supports = False
        breaks = False
        score = 0
        reasons: List[str] = []

        if probe.is_checkmate():
            supports = True
            score += 100000
            reasons.append("checkmate completes any plan")

        if plan == "convert_passed_pawn":
            if piece and piece.piece_type == chess.PAWN:
                supports = True
                score += 1200
                reasons.append("pawn move supports passed-pawn conversion")
            if is_promotion:
                supports = True
                score += 5000
                reasons.append("promotion supports conversion")

        elif plan in {"build_mate_net", "build_rook_box"}:
            if probe.is_check():
                supports = True
                score += 1000
                reasons.append("check supports mate-net pressure")
            enemy_king = probe.king(not side)
            if enemy_king is not None:
                edge_distance = min(
                    chess.square_file(enemy_king),
                    7 - chess.square_file(enemy_king),
                    chess.square_rank(enemy_king),
                    7 - chess.square_rank(enemy_king),
                )
                score += max(0, 4 - edge_distance) * 200
                reasons.append(f"enemy king edge pressure={edge_distance}")
            if piece and piece.piece_type in {chess.QUEEN, chess.ROOK, chess.KING}:
                supports = True
                score += 250
                reasons.append("key conversion piece moved")

        elif plan == "simplify_and_convert":
            if is_capture:
                supports = True
                score += 800
                reasons.append("capture simplifies position")
            if is_promotion:
                supports = True
                score += 2000
                reasons.append("promotion converts material")

        elif plan == "escape_or_neutralise_check":
            if not probe.is_check():
                supports = True
                score += 2000
                reasons.append("move exits check")

        else:
            if is_capture or probe.is_check() or is_promotion:
                supports = True
                score += 500
                reasons.append("forcing improvement")
            else:
                score += 100
                reasons.append("quiet improvement candidate")

        if piece and piece.piece_type in {chess.ROOK, chess.QUEEN} and not supports and not is_capture:
            breaks = True
            score -= 400
            reasons.append("major-piece quiet move without plan support")

        if not reasons:
            reasons.append("neutral continuity")

        return supports, breaks, score, "; ".join(reasons)

    def run(
        self,
        *,
        input_fen: str,
        candidate_move: str,
        side_to_move: str = "white",
        explicit_current_plan: str = "",
        task_name: str = "full_chess_plan_continuity_memory",
    ) -> PlanContinuityResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        previous_plan = str(self.policy.get("last_plan") or "")
        inferred_plan, reason = self._infer_plan(board, side)
        current_plan = explicit_current_plan or inferred_plan

        try:
            move = chess.Move.from_uci(candidate_move)
            legal = move in board.legal_moves
        except Exception:
            move = None
            legal = False

        supports = False
        breaks = True
        continuity_score = -100000 if not legal else 0
        support_reason = "illegal candidate move"

        if legal and move is not None:
            supports, breaks, continuity_score, support_reason = self._move_supports_plan(board, move, current_plan, side)

        plan_changed = bool(previous_plan and previous_plan != current_plan)
        if plan_changed:
            continuity_score -= 250
        elif previous_plan == current_plan and previous_plan:
            continuity_score += 250

        recommended_plan = current_plan

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "candidate_move": candidate_move,
            "current_plan": current_plan,
            "previous_plan": previous_plan,
            "plan_changed": plan_changed,
            "continuity_score": continuity_score,
            "legal": legal,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["plan_memory_run_count"] = int(self.policy.get("plan_memory_run_count", 0)) + 1
        self.policy["last_plan"] = current_plan
        self.policy["last_candidate_move"] = candidate_move
        self.policy["last_trace_hash"] = trace_hash
        if plan_changed:
            self.policy["plan_change_count"] = int(self.policy.get("plan_change_count", 0)) + 1
        else:
            self.policy["plan_continuity_count"] = int(self.policy.get("plan_continuity_count", 0)) + 1

        evidence = {
            "plan_continuity_active": True,
            "previous_plan_loaded": bool(previous_plan),
            "current_plan_inferred": True,
            "candidate_move_scored_against_plan": True,
            "plan_change_penalty_enabled": True,
            "plan_support_bonus_enabled": True,
            "major_piece_shuffle_penalty_enabled": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PlanContinuityResult(
            kernel_version="phase22e32_full_chess_plan_continuity_memory_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_move=candidate_move,
            candidate_move_is_legal=legal,
            plan_continuity_active=True,
            current_plan=current_plan,
            previous_plan=previous_plan,
            plan_changed=plan_changed,
            continuity_score=continuity_score,
            move_supports_plan=supports,
            move_breaks_plan=breaks,
            plan_reason=f"{reason}; {support_reason}",
            recommended_plan=recommended_plan,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_plan_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements plan continuity memory. It remembers the previous strategic plan, infers the "
                "current plan from the board state, scores whether a candidate move supports or breaks that plan, and "
                "penalises unplanned plan switching. It does not call Stockfish, does not use LLM move judgement, and "
                "does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_plan_continuity_memory_kernel(
    *,
    input_fen: str,
    candidate_move: str,
    side_to_move: str = "white",
    explicit_current_plan: str = "",
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_plan_continuity_memory",
) -> PlanContinuityResult:
    return AionPlanContinuityMemoryKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        candidate_move=candidate_move,
        side_to_move=side_to_move,
        explicit_current_plan=explicit_current_plan,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        candidate_move="a7a8q",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Plan continuity memory saved to: {result.memory_path}")
