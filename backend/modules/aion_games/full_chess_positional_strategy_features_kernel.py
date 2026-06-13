from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_positional_strategy_features_memory.json")


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass(frozen=True)
class PositionalStrategyFeaturesResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    fen: str
    side_to_move: str
    analysed_side: str
    material_balance: int
    king_safety_score: int
    centre_control_score: int
    development_score: int
    piece_activity_score: int
    pawn_structure_score: int
    rook_activity_score: int
    queen_safety_score: int
    passed_pawn_score: int
    weak_square_penalty: int
    repetition_risk_penalty: int
    invasion_risk_penalty: int
    promotion_danger_penalty: int
    positional_score: int
    feature_weights: Dict[str, float]
    feature_summary: Dict[str, Any]
    positional_trace_hash: str
    policy_memory_mutated: bool
    final_positional_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessPositionalStrategyFeaturesKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = memory_path or DEFAULT_MEMORY_PATH
        self.memory_loaded = False
        self.policy = {
            "kernel_run_count": 0,
            "positional_analysis_count": 0,
            "last_positional_score": None,
            "last_trace_hash": None,
            "feature_weights": {
                "material_balance": 1.0,
                "king_safety": 1.2,
                "centre_control": 1.0,
                "development": 1.0,
                "piece_activity": 0.8,
                "pawn_structure": 0.8,
                "rook_activity": 0.8,
                "queen_safety": 1.0,
                "passed_pawns": 1.1,
                "weak_squares": 1.0,
                "repetition_risk": 1.0,
                "invasion_risk": 1.2,
                "promotion_danger": 1.4,
            },
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("positional_strategy_features_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PositionalStrategyFeaturesResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e1_positional_strategy_features_memory_v1",
            "task_name": result.task_name,
            "positional_strategy_features_policy": result.final_positional_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _material_balance(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for square, piece in board.piece_map().items():
            value = PIECE_VALUES[piece.piece_type]
            score += value if piece.color == side else -value
        return score

    def _centre_control(self, board: chess.Board, side: chess.Color) -> int:
        centres = [chess.D4, chess.E4, chess.D5, chess.E5]
        extended = [chess.C3, chess.D3, chess.E3, chess.F3, chess.C4, chess.F4, chess.C5, chess.F5, chess.C6, chess.D6, chess.E6, chess.F6]
        score = 0
        for sq in centres:
            score += len(board.attackers(side, sq)) * 20
            score -= len(board.attackers(not side, sq)) * 15
        for sq in extended:
            score += len(board.attackers(side, sq)) * 5
            score -= len(board.attackers(not side, sq)) * 4
        return score

    def _king_safety(self, board: chess.Board, side: chess.Color) -> int:
        king_sq = board.king(side)
        if king_sq is None:
            return -10000
        score = 0
        if board.is_check() and board.turn == side:
            score -= 250

        enemy_attackers = len(board.attackers(not side, king_sq))
        friendly_defenders = len(board.attackers(side, king_sq))
        score -= enemy_attackers * 90
        score += friendly_defenders * 20

        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)
        shield_rank = king_rank + (1 if side == chess.WHITE else -1)
        if 0 <= shield_rank <= 7:
            for f in [king_file - 1, king_file, king_file + 1]:
                if 0 <= f <= 7:
                    piece = board.piece_at(chess.square(f, shield_rank))
                    if piece and piece.color == side and piece.piece_type == chess.PAWN:
                        score += 25
                    else:
                        score -= 15
        return score

    def _development(self, board: chess.Board, side: chess.Color) -> int:
        back_rank = 0 if side == chess.WHITE else 7
        score = 0
        for piece_type in [chess.KNIGHT, chess.BISHOP]:
            for sq in board.pieces(piece_type, side):
                if chess.square_rank(sq) != back_rank:
                    score += 30
                else:
                    score -= 10
        # Early queen movement penalty.
        queen_start = chess.D1 if side == chess.WHITE else chess.D8
        queens = list(board.pieces(chess.QUEEN, side))
        if queens and queens[0] != queen_start and board.fullmove_number <= 10:
            score -= 45
        return score

    def _piece_activity(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for sq, piece in board.piece_map().items():
            if piece.color != side or piece.piece_type == chess.KING:
                continue
            attacks = len(board.attacks(sq))
            multiplier = 2 if piece.piece_type in (chess.KNIGHT, chess.BISHOP) else 1
            score += attacks * multiplier
        return score

    def _pawn_structure(self, board: chess.Board, side: chess.Color) -> int:
        pawns_by_file = {i: [] for i in range(8)}
        for sq in board.pieces(chess.PAWN, side):
            pawns_by_file[chess.square_file(sq)].append(sq)

        doubled = sum(max(0, len(v) - 1) for v in pawns_by_file.values())
        isolated = 0
        for f, pawns in pawns_by_file.items():
            if not pawns:
                continue
            left = pawns_by_file.get(f - 1, [])
            right = pawns_by_file.get(f + 1, [])
            if not left and not right:
                isolated += len(pawns)

        return -(doubled * 35 + isolated * 25)

    def _rook_activity(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for rook_sq in board.pieces(chess.ROOK, side):
            file_idx = chess.square_file(rook_sq)
            own_pawns = [sq for sq in board.pieces(chess.PAWN, side) if chess.square_file(sq) == file_idx]
            enemy_pawns = [sq for sq in board.pieces(chess.PAWN, not side) if chess.square_file(sq) == file_idx]
            if not own_pawns and not enemy_pawns:
                score += 60
            elif not own_pawns:
                score += 35
            rank = chess.square_rank(rook_sq)
            if (side == chess.WHITE and rank == 6) or (side == chess.BLACK and rank == 1):
                score += 45
        return score

    def _queen_safety(self, board: chess.Board, side: chess.Color) -> int:
        queens = list(board.pieces(chess.QUEEN, side))
        if not queens:
            return -300
        q = queens[0]
        enemy_attackers = len(board.attackers(not side, q))
        defenders = len(board.attackers(side, q))
        return defenders * 20 - enemy_attackers * 80

    def _passed_pawns(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        direction = 1 if side == chess.WHITE else -1
        for pawn_sq in board.pieces(chess.PAWN, side):
            f = chess.square_file(pawn_sq)
            r = chess.square_rank(pawn_sq)
            enemy_blockers = []
            for ff in [f - 1, f, f + 1]:
                if not 0 <= ff <= 7:
                    continue
                rr = r + direction
                while 0 <= rr <= 7:
                    sq = chess.square(ff, rr)
                    piece = board.piece_at(sq)
                    if piece and piece.color != side and piece.piece_type == chess.PAWN:
                        enemy_blockers.append(sq)
                    rr += direction
            if not enemy_blockers:
                advance = r if side == chess.WHITE else 7 - r
                score += 35 + advance * 12
        return score

    def _weak_square_penalty(self, board: chess.Board, side: chess.Color) -> int:
        penalty = 0
        sensitive = [chess.F2, chess.G2, chess.F7, chess.G7, chess.D3, chess.E3, chess.D6, chess.E6]
        for sq in sensitive:
            if len(board.attackers(not side, sq)) > len(board.attackers(side, sq)):
                penalty -= 15
        return penalty

    def _repetition_risk(self, board: chess.Board) -> int:
        if board.can_claim_threefold_repetition() or board.is_repetition(2):
            return -250
        return 0

    def _invasion_risk(self, board: chess.Board, side: chess.Color) -> int:
        penalty = 0
        enemy = not side
        target_ranks = [0, 1] if side == chess.WHITE else [6, 7]
        for sq, piece in board.piece_map().items():
            if piece.color == enemy and piece.piece_type in (chess.QUEEN, chess.ROOK):
                if chess.square_rank(sq) in target_ranks:
                    penalty -= 180 if piece.piece_type == chess.QUEEN else 120
        return penalty

    def _promotion_danger(self, board: chess.Board, side: chess.Color) -> int:
        penalty = 0
        enemy = not side
        for sq in board.pieces(chess.PAWN, enemy):
            rank = chess.square_rank(sq)
            if (enemy == chess.WHITE and rank >= 5) or (enemy == chess.BLACK and rank <= 2):
                penalty -= 120
            if (enemy == chess.WHITE and rank == 6) or (enemy == chess.BLACK and rank == 1):
                penalty -= 250
        return penalty

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        analysed_side: str = "white",
        task_name: str = "full_chess_positional_strategy_features",
    ) -> PositionalStrategyFeaturesResult:
        board = chess.Board(fen)
        side = chess.WHITE if analysed_side.lower() == "white" else chess.BLACK
        weights = dict(self.policy["feature_weights"])

        material = self._material_balance(board, side)
        king = self._king_safety(board, side)
        centre = self._centre_control(board, side)
        development = self._development(board, side)
        activity = self._piece_activity(board, side)
        pawn_structure = self._pawn_structure(board, side)
        rook_activity = self._rook_activity(board, side)
        queen_safety = self._queen_safety(board, side)
        passed_pawns = self._passed_pawns(board, side)
        weak_squares = self._weak_square_penalty(board, side)
        repetition = self._repetition_risk(board)
        invasion = self._invasion_risk(board, side)
        promotion = self._promotion_danger(board, side)

        positional_score = int(round(
            material * weights["material_balance"]
            + king * weights["king_safety"]
            + centre * weights["centre_control"]
            + development * weights["development"]
            + activity * weights["piece_activity"]
            + pawn_structure * weights["pawn_structure"]
            + rook_activity * weights["rook_activity"]
            + queen_safety * weights["queen_safety"]
            + passed_pawns * weights["passed_pawns"]
            + weak_squares * weights["weak_squares"]
            + repetition * weights["repetition_risk"]
            + invasion * weights["invasion_risk"]
            + promotion * weights["promotion_danger"]
        ))

        summary = {
            "material_balance": material,
            "king_safety_score": king,
            "centre_control_score": centre,
            "development_score": development,
            "piece_activity_score": activity,
            "pawn_structure_score": pawn_structure,
            "rook_activity_score": rook_activity,
            "queen_safety_score": queen_safety,
            "passed_pawn_score": passed_pawns,
            "weak_square_penalty": weak_squares,
            "repetition_risk_penalty": repetition,
            "invasion_risk_penalty": invasion,
            "promotion_danger_penalty": promotion,
            "positional_score": positional_score,
        }

        trace_payload = {
            "fen": board.fen(),
            "analysed_side": analysed_side,
            "summary": summary,
            "weights": weights,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
        }
        trace_hash = hashlib.sha256(json.dumps(trace_payload, sort_keys=True).encode("utf-8")).hexdigest()

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["positional_analysis_count"] = int(self.policy.get("positional_analysis_count", 0)) + 1
        self.policy["last_positional_score"] = positional_score
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "positional_strategy_features_active": True,
            "material_balance_active": True,
            "king_safety_feature_active": True,
            "centre_control_feature_active": True,
            "development_feature_active": True,
            "piece_activity_feature_active": True,
            "pawn_structure_feature_active": True,
            "rook_activity_feature_active": True,
            "queen_safety_feature_active": True,
            "passed_pawn_feature_active": True,
            "weak_square_feature_active": True,
            "repetition_risk_feature_active": True,
            "invasion_risk_feature_active": True,
            "promotion_danger_feature_active": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PositionalStrategyFeaturesResult(
            kernel_version="phase22e1_full_chess_positional_strategy_features_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            fen=board.fen(),
            side_to_move="white" if board.turn == chess.WHITE else "black",
            analysed_side=analysed_side,
            material_balance=material,
            king_safety_score=king,
            centre_control_score=centre,
            development_score=development,
            piece_activity_score=activity,
            pawn_structure_score=pawn_structure,
            rook_activity_score=rook_activity,
            queen_safety_score=queen_safety,
            passed_pawn_score=passed_pawns,
            weak_square_penalty=weak_squares,
            repetition_risk_penalty=repetition,
            invasion_risk_penalty=invasion,
            promotion_danger_penalty=promotion,
            positional_score=positional_score,
            feature_weights=weights,
            feature_summary=summary,
            positional_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_positional_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel extracts deterministic positional chess strategy features for AION. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )
        self._save_memory(result)
        return result


def run_full_chess_positional_strategy_features_kernel(
    *,
    memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    analysed_side: str = "white",
    task_name: str = "full_chess_positional_strategy_features",
) -> PositionalStrategyFeaturesResult:
    return AionFullChessPositionalStrategyFeaturesKernel(memory_path=memory_path).run(
        fen=fen,
        analysed_side=analysed_side,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_positional_strategy_features_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Positional strategy feature memory saved to: {result.memory_path}")
