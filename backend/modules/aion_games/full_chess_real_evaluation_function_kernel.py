"""AION Phase 22C.1 — Full Chess Real Evaluation Function Kernel.

This phase moves AION from simple legal-move heuristics toward a real position
evaluation function.

It scores a board using:
- material balance;
- king safety;
- piece activity;
- centre control;
- development;
- pawn structure;
- repetition-risk penalty;
- check and mate awareness;
- policy weights learned from 22B.42.

It is deterministic, local, and does not use Stockfish, cloud engines, or LLM
move judgement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess


DEFAULT_REAL_EVALUATION_MEMORY_PATH = Path(
    "data/aion_games/full_chess_real_evaluation_function_memory.json"
)

DEFAULT_POST_GAME_MEMORY_PATH = Path(
    "data/aion_games/full_chess_post_game_blunder_review_memory.json"
)

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CENTER_SQUARES = {chess.D4, chess.E4, chess.D5, chess.E5}
EXTENDED_CENTER_SQUARES = {
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C4, chess.D4, chess.E4, chess.F4,
    chess.C5, chess.D5, chess.E5, chess.F5,
    chess.C6, chess.D6, chess.E6, chess.F6,
}


@dataclass(frozen=True)
class RealChessEvaluationBreakdown:
    material_score: int
    king_safety_score: int
    piece_activity_score: int
    centre_control_score: int
    development_score: int
    pawn_structure_score: int
    repetition_risk_penalty: int
    check_pressure_score: int
    terminal_score: int
    total_score: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealChessEvaluationResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    evaluation_mode: str
    fen: str
    side_to_evaluate: str
    legal_move_count: int
    is_check: bool
    is_checkmate: bool
    is_stalemate: bool
    material_score: int
    king_safety_score: int
    piece_activity_score: int
    centre_control_score: int
    development_score: int
    pawn_structure_score: int
    repetition_risk_penalty: int
    check_pressure_score: int
    terminal_score: int
    total_score: int
    weighted_total_score: float
    best_scored_move: str
    best_scored_move_score: float
    top_candidate_moves: List[Dict[str, Any]]
    learned_policy_weights: Dict[str, float]
    evaluation_breakdown: Dict[str, Any]
    evaluation_trace_hash: str
    final_evaluation_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessRealEvaluationFunctionKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        post_game_memory_path: Optional[Path] = None,
    ):
        self.memory_path = Path(memory_path or DEFAULT_REAL_EVALUATION_MEMORY_PATH)
        self.post_game_memory_path = Path(post_game_memory_path or DEFAULT_POST_GAME_MEMORY_PATH)
        self.memory_loaded = False
        self.learned_policy_weights: Dict[str, float] = {
            "strategy_weight_king_safety": 1.0,
            "strategy_weight_piece_activity": 1.0,
            "strategy_weight_repetition_penalty": 1.0,
            "strategy_weight_queen_activity_penalty": 1.0,
        }
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "evaluation_count": 0,
            "candidate_move_evaluation_count": 0,
            "loaded_post_game_learning": False,
            "last_fen": None,
            "last_side_to_evaluate": None,
            "last_total_score": None,
            "last_best_scored_move": None,
            "last_trace_hash": None,
        }
        self._load_memory()
        self._load_post_game_learning()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            policy = data.get("real_evaluation_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _load_post_game_learning(self) -> None:
        if not self.post_game_memory_path.exists():
            return
        try:
            data = json.loads(self.post_game_memory_path.read_text(encoding="utf-8"))
        except Exception:
            return

        policy = data.get("post_game_blunder_review_policy")
        if not isinstance(policy, dict):
            return

        for key in self.learned_policy_weights:
            value = policy.get(key)
            if isinstance(value, (int, float)):
                self.learned_policy_weights[key] = float(value)

        self.policy["loaded_post_game_learning"] = True

    def _save_memory(self, result: RealChessEvaluationResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22c1_full_chess_real_evaluation_function_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "real_evaluation_policy": result.final_evaluation_policy,
            "last_fen": result.fen,
            "last_side_to_evaluate": result.side_to_evaluate,
            "last_total_score": result.total_score,
            "last_weighted_total_score": result.weighted_total_score,
            "last_best_scored_move": result.best_scored_move,
            "last_best_scored_move_score": result.best_scored_move_score,
            "learned_policy_weights": result.learned_policy_weights,
            "evaluation_trace_hash": result.evaluation_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _sign(self, piece: chess.Piece, side: chess.Color) -> int:
        return 1 if piece.color == side else -1

    def _material_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                score += self._sign(piece, side) * PIECE_VALUES[piece.piece_type]
        return score

    def _king_safety_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for colour in [chess.WHITE, chess.BLACK]:
            king_square = board.king(colour)
            if king_square is None:
                continue

            local = 0
            if colour == chess.WHITE:
                if board.has_kingside_castling_rights(colour) or board.has_queenside_castling_rights(colour):
                    local += 8
                if king_square in {chess.G1, chess.C1}:
                    local += 24
            else:
                if board.has_kingside_castling_rights(colour) or board.has_queenside_castling_rights(colour):
                    local += 8
                if king_square in {chess.G8, chess.C8}:
                    local += 24

            attackers = board.attackers(not colour, king_square)
            local -= 12 * len(attackers)

            score += local if colour == side else -local

        return score

    def _piece_activity_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for colour in [chess.WHITE, chess.BLACK]:
            board.turn = colour
            mobility = len(list(board.legal_moves))
            local = mobility * 2
            score += local if colour == side else -local
        board.turn = side
        return score

    def _centre_control_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for colour in [chess.WHITE, chess.BLACK]:
            local = 0
            for square in CENTER_SQUARES:
                local += 8 * len(board.attackers(colour, square))
            for square in EXTENDED_CENTER_SQUARES:
                local += 2 * len(board.attackers(colour, square))
            score += local if colour == side else -local
        return score

    def _development_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        starting_minor_squares = {
            chess.WHITE: [chess.B1, chess.G1, chess.C1, chess.F1],
            chess.BLACK: [chess.B8, chess.G8, chess.C8, chess.F8],
        }

        for colour in [chess.WHITE, chess.BLACK]:
            undeveloped = 0
            for square in starting_minor_squares[colour]:
                piece = board.piece_at(square)
                if piece and piece.color == colour and piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                    undeveloped += 1

            local = 40 - undeveloped * 10
            score += local if colour == side else -local

        return score

    def _pawn_structure_score(self, board: chess.Board, side: chess.Color) -> int:
        score = 0

        for colour in [chess.WHITE, chess.BLACK]:
            pawns_by_file: Dict[int, int] = {i: 0 for i in range(8)}
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.color == colour and piece.piece_type == chess.PAWN:
                    pawns_by_file[chess.square_file(square)] += 1

            doubled = sum(max(0, count - 1) for count in pawns_by_file.values())
            islands = 0
            in_island = False
            for file_index in range(8):
                has_pawn = pawns_by_file[file_index] > 0
                if has_pawn and not in_island:
                    islands += 1
                in_island = has_pawn

            local = -(doubled * 12) - max(0, islands - 2) * 6
            score += local if colour == side else -local

        return score

    def _repetition_risk_penalty(self, board: chess.Board, side: chess.Color) -> int:
        if board.can_claim_threefold_repetition() or board.is_repetition(2):
            return -80
        return 0

    def _check_pressure_score(self, board: chess.Board, side: chess.Color) -> int:
        if board.is_check():
            return -35 if board.turn == side else 35
        return 0

    def _terminal_score(self, board: chess.Board, side: chess.Color) -> int:
        if board.is_checkmate():
            return -100000 if board.turn == side else 100000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        return 0

    def evaluate_board(self, board: chess.Board, *, side_to_evaluate: str) -> RealChessEvaluationBreakdown:
        side = chess.WHITE if side_to_evaluate == "white" else chess.BLACK

        original_turn = board.turn

        material = self._material_score(board, side)
        king_safety = self._king_safety_score(board, side)
        activity = self._piece_activity_score(board, side)
        centre = self._centre_control_score(board, side)
        development = self._development_score(board, side)
        pawn_structure = self._pawn_structure_score(board, side)
        repetition = self._repetition_risk_penalty(board, side)
        check_pressure = self._check_pressure_score(board, side)
        terminal = self._terminal_score(board, side)

        board.turn = original_turn

        total = (
            material
            + king_safety
            + activity
            + centre
            + development
            + pawn_structure
            + repetition
            + check_pressure
            + terminal
        )

        return RealChessEvaluationBreakdown(
            material_score=material,
            king_safety_score=king_safety,
            piece_activity_score=activity,
            centre_control_score=centre,
            development_score=development,
            pawn_structure_score=pawn_structure,
            repetition_risk_penalty=repetition,
            check_pressure_score=check_pressure,
            terminal_score=terminal,
            total_score=total,
        )

    def _weighted_score(self, breakdown: RealChessEvaluationBreakdown) -> float:
        return round(
            breakdown.material_score
            + breakdown.king_safety_score * self.learned_policy_weights["strategy_weight_king_safety"]
            + breakdown.piece_activity_score * self.learned_policy_weights["strategy_weight_piece_activity"]
            + breakdown.centre_control_score
            + breakdown.development_score
            + breakdown.pawn_structure_score
            + breakdown.repetition_risk_penalty * self.learned_policy_weights["strategy_weight_repetition_penalty"]
            + breakdown.check_pressure_score
            + breakdown.terminal_score,
            4,
        )

    def _score_candidate_moves(
        self,
        board: chess.Board,
        *,
        side_to_evaluate: str,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        for move in board.legal_moves:
            board.push(move)
            breakdown = self.evaluate_board(board, side_to_evaluate=side_to_evaluate)
            weighted = self._weighted_score(breakdown)
            board.pop()

            candidates.append(
                {
                    "move": move.uci(),
                    "weighted_score": weighted,
                    "total_score": breakdown.total_score,
                    "material_score": breakdown.material_score,
                    "terminal_score": breakdown.terminal_score,
                }
            )

        candidates.sort(key=lambda item: (item["weighted_score"], item["move"]), reverse=True)
        return candidates[:limit]

    def run(
        self,
        *,
        task_name: str = "full_chess_real_evaluation_function",
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
    ) -> RealChessEvaluationResult:
        board = chess.Board(fen)
        breakdown = self.evaluate_board(board, side_to_evaluate=side_to_evaluate)
        weighted_total = self._weighted_score(breakdown)

        top_candidates = self._score_candidate_moves(
            board,
            side_to_evaluate=side_to_evaluate,
            limit=8,
        )

        best_move = top_candidates[0]["move"] if top_candidates else ""
        best_score = float(top_candidates[0]["weighted_score"]) if top_candidates else weighted_total

        trace_payload = {
            "evaluation_mode": "real_chess_position_evaluation",
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "legal_move_count": len(list(board.legal_moves)),
            "breakdown": breakdown.to_dict(),
            "weighted_total_score": weighted_total,
            "best_scored_move": best_move,
            "best_scored_move_score": best_score,
            "learned_policy_weights": self.learned_policy_weights,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["evaluation_count"] = int(self.policy.get("evaluation_count", 0)) + 1
        self.policy["candidate_move_evaluation_count"] = int(
            self.policy.get("candidate_move_evaluation_count", 0)
        ) + len(list(board.legal_moves))
        self.policy["last_fen"] = fen
        self.policy["last_side_to_evaluate"] = side_to_evaluate
        self.policy["last_total_score"] = breakdown.total_score
        self.policy["last_best_scored_move"] = best_move
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "evaluation_function_active": True,
            "material_scoring_active": True,
            "king_safety_scoring_active": True,
            "piece_activity_scoring_active": True,
            "centre_control_scoring_active": True,
            "development_scoring_active": True,
            "pawn_structure_scoring_active": True,
            "repetition_penalty_active": True,
            "terminal_awareness_active": True,
            "candidate_moves_scored": len(top_candidates) > 0,
            "post_game_learning_loaded": bool(self.policy.get("loaded_post_game_learning", False)),
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = RealChessEvaluationResult(
            kernel_version="phase22c1_full_chess_real_evaluation_function_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            evaluation_mode="real_chess_position_evaluation",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            legal_move_count=len(list(board.legal_moves)),
            is_check=board.is_check(),
            is_checkmate=board.is_checkmate(),
            is_stalemate=board.is_stalemate(),
            material_score=breakdown.material_score,
            king_safety_score=breakdown.king_safety_score,
            piece_activity_score=breakdown.piece_activity_score,
            centre_control_score=breakdown.centre_control_score,
            development_score=breakdown.development_score,
            pawn_structure_score=breakdown.pawn_structure_score,
            repetition_risk_penalty=breakdown.repetition_risk_penalty,
            check_pressure_score=breakdown.check_pressure_score,
            terminal_score=breakdown.terminal_score,
            total_score=breakdown.total_score,
            weighted_total_score=weighted_total,
            best_scored_move=best_move,
            best_scored_move_score=best_score,
            top_candidate_moves=top_candidates,
            learned_policy_weights=dict(self.learned_policy_weights),
            evaluation_breakdown=breakdown.to_dict(),
            evaluation_trace_hash=trace_hash,
            final_evaluation_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This phase implements a deterministic local chess evaluation function. "
                "It scores material, king safety, activity, centre control, development, pawn structure, "
                "repetition risk, checks, and terminal positions. It does not use Stockfish, cloud engines, "
                "external engines, or LLM move judgement."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_real_evaluation_function_kernel(
    *,
    memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_real_evaluation_function",
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
) -> RealChessEvaluationResult:
    return AionFullChessRealEvaluationFunctionKernel(
        memory_path=memory_path,
        post_game_memory_path=post_game_memory_path,
    ).run(
        task_name=task_name,
        fen=fen,
        side_to_evaluate=side_to_evaluate,
    )


if __name__ == "__main__":
    result = run_full_chess_real_evaluation_function_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess real evaluation function memory saved to: {result.memory_path}")
