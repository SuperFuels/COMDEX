"""AION Phase 22D.8 — Patch SQI Selector Against Level 2 Failure Modes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_sqi_guided_move_selection_kernel import (
    run_full_chess_sqi_guided_move_selection_kernel,
)
from .full_chess_level2_sqi_loss_post_game_review_kernel import (
    DEFAULT_LEVEL2_SQI_LOSS_REVIEW_MEMORY_PATH,
)


DEFAULT_SQI_FAILURE_PATCH_SELECTOR_MEMORY_PATH = Path(
    "data/aion_games/full_chess_sqi_failure_patch_selector_memory.json"
)


@dataclass(frozen=True)
class SQIFailurePatchSelectorResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    selection_mode: str
    fen: str
    side_to_move: str
    legal_move_count: int
    selected_move: str
    selected_base_sqi_score: float
    selected_patched_score: float
    selected_patch_reason: str
    selected_move_is_legal: bool
    candidate_count: int
    top_patched_candidates: List[Dict[str, Any]]
    active_policy_updates: Dict[str, Any]
    repetition_penalty_applied_count: int
    king_shuffle_penalty_applied_count: int
    invasion_penalty_applied_count: int
    promotion_penalty_applied_count: int
    negative_spiral_guard_applied: bool
    patch_trace_hash: str
    policy_memory_mutated: bool
    final_patch_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessSQIFailurePatchSelectorKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        sqi_selector_memory_path: Optional[Path] = None,
        sqi_bridge_memory_path: Optional[Path] = None,
        selector_memory_path: Optional[Path] = None,
        evaluation_memory_path: Optional[Path] = None,
        post_game_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
    ):
        self.memory_path = Path(memory_path or DEFAULT_SQI_FAILURE_PATCH_SELECTOR_MEMORY_PATH)
        self.sqi_selector_memory_path = sqi_selector_memory_path
        self.sqi_bridge_memory_path = sqi_bridge_memory_path
        self.selector_memory_path = selector_memory_path
        self.evaluation_memory_path = evaluation_memory_path
        self.post_game_memory_path = post_game_memory_path
        self.review_memory_path = Path(review_memory_path or DEFAULT_LEVEL2_SQI_LOSS_REVIEW_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "patched_selection_count": 0,
            "repetition_penalty_total": 0,
            "king_shuffle_penalty_total": 0,
            "invasion_penalty_total": 0,
            "promotion_penalty_total": 0,
            "negative_spiral_guard_count": 0,
            "last_selected_move": None,
            "last_selected_patched_score": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        policy = data.get("sqi_failure_patch_selector_policy") if isinstance(data, dict) else None
        if isinstance(policy, dict):
            self.policy.update(policy)
            self.memory_loaded = True

    def _load_policy_updates(self) -> Dict[str, Any]:
        if not self.review_memory_path.exists():
            return {}
        try:
            data = json.loads(self.review_memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        updates = data.get("policy_updates") if isinstance(data, dict) else None
        return updates if isinstance(updates, dict) else {}

    def _save_memory(self, result: SQIFailurePatchSelectorResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22d8_sqi_failure_patch_selector_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "sqi_failure_patch_selector_policy": result.final_patch_policy,
            "active_policy_updates": result.active_policy_updates,
            "selected_move": result.selected_move,
            "selected_patched_score": result.selected_patched_score,
            "patch_trace_hash": result.patch_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _board_from_moves(self, moves: List[str]) -> chess.Board:
        board = chess.Board()
        for move in moves:
            board.push_uci(move)
        return board

    def _side_name(self, colour: chess.Color) -> str:
        return "white" if colour == chess.WHITE else "black"

    def _material_score(self, board: chess.Board, colour: chess.Color) -> int:
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
        }
        score = 0
        for piece_type, value in values.items():
            score += len(board.pieces(piece_type, colour)) * value
            score -= len(board.pieces(piece_type, not colour)) * value
        return score

    def _move_repetition_count(self, move: str, aion_moves: List[str]) -> int:
        return sum(1 for item in aion_moves if item == move)

    def _is_back_and_forth(self, move: str, aion_moves: List[str]) -> bool:
        if not aion_moves:
            return False
        last = aion_moves[-1]
        return last[:2] == move[2:4] and last[2:4] == move[:2]

    def _opponent_has_invasion(self, board: chess.Board, aion_colour: chess.Color) -> bool:
        enemy = not aion_colour
        own_back_ranks = {0, 1} if aion_colour == chess.WHITE else {6, 7}
        for piece_type in [chess.QUEEN, chess.ROOK]:
            for square in board.pieces(piece_type, enemy):
                if chess.square_rank(square) in own_back_ranks:
                    return True
        return False

    def _opponent_has_promotion_threat(self, board: chess.Board, aion_colour: chess.Color) -> bool:
        enemy = not aion_colour
        threat_rank = 1 if enemy == chess.BLACK else 6
        for square in board.pieces(chess.PAWN, enemy):
            if chess.square_rank(square) == threat_rank:
                return True
        return False

    def _move_is_king_shuffle(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.from_square)
        return bool(piece and piece.piece_type == chess.KING and not board.is_castling(move))

    def _move_addresses_invasion(self, board: chess.Board, move: chess.Move, aion_colour: chess.Color) -> bool:
        enemy = not aion_colour
        target_piece = board.piece_at(move.to_square)
        if target_piece and target_piece.color == enemy and target_piece.piece_type in {chess.QUEEN, chess.ROOK}:
            return True
        return board.gives_check(move)

    def _move_addresses_promotion(self, board: chess.Board, move: chess.Move, aion_colour: chess.Color) -> bool:
        enemy = not aion_colour
        target_piece = board.piece_at(move.to_square)
        if target_piece and target_piece.color == enemy and target_piece.piece_type == chess.PAWN:
            return True
        return board.gives_check(move)

    def run(
        self,
        *,
        task_name: str = "full_chess_sqi_failure_patch_selector",
        moves: Optional[List[str]] = None,
        fen: Optional[str] = None,
        side_to_evaluate: str = "white",
        sqi_enabled: bool = True,
    ) -> SQIFailurePatchSelectorResult:
        board = chess.Board(fen) if fen else self._board_from_moves(moves or [])
        side_to_move = self._side_name(board.turn)
        aion_colour = chess.WHITE if side_to_evaluate == "white" else chess.BLACK

        legal_move_count = board.legal_moves.count()

        base = run_full_chess_sqi_guided_move_selection_kernel(
            memory_path=self.sqi_selector_memory_path,
            sqi_bridge_memory_path=self.sqi_bridge_memory_path,
            selector_memory_path=self.selector_memory_path,
            evaluation_memory_path=self.evaluation_memory_path,
            post_game_memory_path=self.post_game_memory_path,
            fen=board.fen(),
            side_to_evaluate=side_to_evaluate,
            sqi_enabled=sqi_enabled,
        )

        active_policy_updates = self._load_policy_updates()
        if not active_policy_updates:
            active_policy_updates = {
                "block_repetition_loops": True,
                "raise_king_safety_weight_when_losing": True,
                "detect_queen_rook_invasion": True,
                "detect_promotion_race_threats": True,
                "avoid_back_and_forth_king_moves": True,
                "stand_down_from_bad_sqi_collapse_when_all_candidates_negative": True,
                "prefer_check_evasion_and_mate_threat_defence": True,
                "prefer_simplification_when_material_losing": True,
            }

        move_history = moves or []
        aion_moves = move_history[0::2] if side_to_evaluate == "white" else move_history[1::2]
        material_delta = self._material_score(board, aion_colour)
        invasion_active = self._opponent_has_invasion(board, aion_colour)
        promotion_active = self._opponent_has_promotion_threat(board, aion_colour)

        repeated_history_signal = False
        if len(aion_moves) >= 2:
            seen_history = {}
            for history_move in aion_moves:
                seen_history[history_move] = seen_history.get(history_move, 0) + 1
            repeated_history_signal = any(count >= 2 for count in seen_history.values())

        back_and_forth_history_signal = False
        if len(aion_moves) >= 2:
            previous_move = aion_moves[-2]
            last_move = aion_moves[-1]
            back_and_forth_history_signal = (
                previous_move[:2] == last_move[2:4]
                and previous_move[2:4] == last_move[:2]
            )

        patched: List[Dict[str, Any]] = []
        repetition_penalty_count = 1 if (repeated_history_signal or back_and_forth_history_signal) else 0
        king_shuffle_penalty_count = 0
        invasion_penalty_count = 0
        promotion_penalty_count = 0

        base_candidates = list(getattr(base, "top_sqi_candidates", []) or [])

        for item in base_candidates:
            move_uci = item["move"]
            move = chess.Move.from_uci(move_uci)
            score = float(item["sqi_adjusted_score"])
            penalties: List[str] = []
            bonus = 0.0

            repetition_count = self._move_repetition_count(move_uci, aion_moves)
            if active_policy_updates.get("block_repetition_loops") and repetition_count:
                penalty = 400.0 * repetition_count
                score -= penalty
                repetition_penalty_count += 1
                penalties.append(f"repetition_penalty_{int(penalty)}")

            if active_policy_updates.get("avoid_back_and_forth_king_moves") and self._is_back_and_forth(move_uci, aion_moves):
                score -= 900.0
                repetition_penalty_count += 1
                penalties.append("back_and_forth_cycle_penalty")

            if active_policy_updates.get("raise_king_safety_weight_when_losing") and material_delta < 0 and self._move_is_king_shuffle(board, move):
                score -= 550.0
                king_shuffle_penalty_count += 1
                penalties.append("king_shuffle_penalty")

            if active_policy_updates.get("detect_queen_rook_invasion") and invasion_active and not self._move_addresses_invasion(board, move, aion_colour):
                score -= 450.0
                invasion_penalty_count += 1
                penalties.append("invasion_not_addressed_penalty")

            if active_policy_updates.get("detect_promotion_race_threats") and promotion_active and not self._move_addresses_promotion(board, move, aion_colour):
                score -= 500.0
                promotion_penalty_count += 1
                penalties.append("promotion_threat_not_addressed_penalty")

            if active_policy_updates.get("prefer_simplification_when_material_losing") and material_delta < 0 and item.get("is_capture"):
                bonus += 180.0
                penalties.append("simplification_capture_bonus")

            if active_policy_updates.get("prefer_check_evasion_and_mate_threat_defence") and item.get("gives_check"):
                bonus += 120.0
                penalties.append("checking_pressure_bonus")

            patched_score = round(score + bonus, 6)

            patched.append({
                **item,
                "base_sqi_score": item["sqi_adjusted_score"],
                "patched_score": patched_score,
                "patch_penalties": penalties,
                "material_delta_for_aion": material_delta,
                "invasion_active": invasion_active,
                "promotion_active": promotion_active,
            })

        all_base_negative = bool(patched) and all(float(item["base_sqi_score"]) < 0 for item in patched)
        severe_loss_position = material_delta <= -1500 or board.is_checkmate() or invasion_active or promotion_active
        negative_spiral_guard_applied = False
        if active_policy_updates.get("stand_down_from_bad_sqi_collapse_when_all_candidates_negative") and (all_base_negative or severe_loss_position):
            negative_spiral_guard_applied = True
            for item in patched:
                if item.get("is_capture"):
                    item["patched_score"] += 250.0
                    item["patch_penalties"].append("negative_spiral_capture_survival_bonus")
                if item.get("gives_check"):
                    item["patched_score"] += 150.0
                    item["patch_penalties"].append("negative_spiral_check_survival_bonus")

        patched.sort(
            key=lambda item: (
                item.get("is_checkmate", False),
                item["patched_score"],
                item.get("is_capture", False),
                item.get("gives_check", False),
                item["move"],
            ),
            reverse=True,
        )

        selected = patched[0] if patched else {}
        selected_move = str(selected.get("move", ""))
        selected_move_is_legal = selected_move in {m.uci() for m in board.legal_moves} if selected_move else False
        selected_reason = "patched_sqi_failure_guard_selection" if selected else "no_candidate"

        trace_payload = {
            "fen": board.fen(),
            "side_to_evaluate": side_to_evaluate,
            "selected_move": selected_move,
            "selected_patched_score": selected.get("patched_score", 0.0),
            "repetition_penalty_count": repetition_penalty_count,
            "king_shuffle_penalty_count": king_shuffle_penalty_count,
            "invasion_penalty_count": invasion_penalty_count,
            "promotion_penalty_count": promotion_penalty_count,
            "negative_spiral_guard_applied": negative_spiral_guard_applied,
            "active_policy_updates": active_policy_updates,
        }
        patch_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["patched_selection_count"] = int(self.policy.get("patched_selection_count", 0)) + (1 if selected_move else 0)
        self.policy["repetition_penalty_total"] = int(self.policy.get("repetition_penalty_total", 0)) + repetition_penalty_count
        self.policy["king_shuffle_penalty_total"] = int(self.policy.get("king_shuffle_penalty_total", 0)) + king_shuffle_penalty_count
        self.policy["invasion_penalty_total"] = int(self.policy.get("invasion_penalty_total", 0)) + invasion_penalty_count
        self.policy["promotion_penalty_total"] = int(self.policy.get("promotion_penalty_total", 0)) + promotion_penalty_count
        self.policy["negative_spiral_guard_count"] = int(self.policy.get("negative_spiral_guard_count", 0)) + (1 if negative_spiral_guard_applied else 0)
        self.policy["last_selected_move"] = selected_move
        self.policy["last_selected_patched_score"] = selected.get("patched_score", 0.0)
        self.policy["last_trace_hash"] = patch_trace_hash

        result = SQIFailurePatchSelectorResult(
            kernel_version="phase22d8_full_chess_sqi_failure_patch_selector_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            selection_mode="sqi_failure_patch_selector",
            fen=board.fen(),
            side_to_move=side_to_move,
            legal_move_count=legal_move_count,
            selected_move=selected_move,
            selected_base_sqi_score=float(selected.get("base_sqi_score", 0.0)),
            selected_patched_score=float(selected.get("patched_score", 0.0)),
            selected_patch_reason=selected_reason,
            selected_move_is_legal=selected_move_is_legal,
            candidate_count=len(patched),
            top_patched_candidates=patched[:8],
            active_policy_updates=active_policy_updates,
            repetition_penalty_applied_count=repetition_penalty_count,
            king_shuffle_penalty_applied_count=king_shuffle_penalty_count,
            invasion_penalty_applied_count=invasion_penalty_count,
            promotion_penalty_applied_count=promotion_penalty_count,
            negative_spiral_guard_applied=negative_spiral_guard_applied,
            patch_trace_hash=patch_trace_hash,
            policy_memory_mutated=True,
            final_patch_policy=dict(self.policy),
            evidence={
                "sqi_failure_patch_active": True,
                "policy_updates_loaded": bool(active_policy_updates),
                "repetition_guard_active": True,
                "king_shuffle_guard_active": True,
                "invasion_guard_active": True,
                "promotion_guard_active": True,
                "negative_spiral_guard_active": True,
                "selected_move_is_legal": selected_move_is_legal,
                "uses_llm_shortcut": False,
                "uses_stockfish": False,
                "uses_cloud_engine": False,
                "uses_lichess_analysis": False,
                "uses_trace_hash": True,
                "memory_loaded": self.memory_loaded,
            },
            boundary_statement=(
                "This kernel patches SQI-guided chess selection against the real level 2 loss failure modes. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_sqi_failure_patch_selector_kernel(
    *,
    memory_path: Optional[Path] = None,
    sqi_selector_memory_path: Optional[Path] = None,
    sqi_bridge_memory_path: Optional[Path] = None,
    selector_memory_path: Optional[Path] = None,
    evaluation_memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_sqi_failure_patch_selector",
    moves: Optional[List[str]] = None,
    fen: Optional[str] = None,
    side_to_evaluate: str = "white",
    sqi_enabled: bool = True,
) -> SQIFailurePatchSelectorResult:
    return AionFullChessSQIFailurePatchSelectorKernel(
        memory_path=memory_path,
        sqi_selector_memory_path=sqi_selector_memory_path,
        sqi_bridge_memory_path=sqi_bridge_memory_path,
        selector_memory_path=selector_memory_path,
        evaluation_memory_path=evaluation_memory_path,
        post_game_memory_path=post_game_memory_path,
        review_memory_path=review_memory_path,
    ).run(
        task_name=task_name,
        moves=moves,
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        sqi_enabled=sqi_enabled,
    )


if __name__ == "__main__":
    result = run_full_chess_sqi_failure_patch_selector_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ SQI failure patch selector memory saved to: {result.memory_path}")
