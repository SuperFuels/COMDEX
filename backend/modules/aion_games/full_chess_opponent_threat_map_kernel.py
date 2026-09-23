from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_opponent_threat_map_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 100000,
}


@dataclass(frozen=True)
class OpponentThreat:
    move: str
    threat_type: str
    target_square: str
    captured_piece_type: Optional[str]
    captured_piece_value: int
    gives_check: bool
    gives_checkmate: bool
    promotes: bool
    threat_score: int
    explanation: str


@dataclass(frozen=True)
class OpponentThreatMapResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    aion_side: str
    opponent_side: str
    threat_map_active: bool
    opponent_legal_move_count: int
    threat_count: int
    high_threat_count: int
    critical_threat_found: bool
    highest_threat_score: int
    highest_threat: Optional[Dict[str, Any]]
    top_threats: List[Dict[str, Any]]
    defended_aion_king_square: str
    aion_king_in_check: bool
    recommended_response_mode: str
    trace_hash: str
    policy_memory_mutated: bool
    final_threat_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionOpponentThreatMapKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "threat_map_run_count": 0,
            "critical_threat_seen_count": 0,
            "last_highest_threat_score": None,
            "last_recommended_response_mode": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("opponent_threat_map_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: OpponentThreatMapResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e29_opponent_threat_map_memory_v1",
            "task_name": result.task_name,
            "opponent_threat_map_policy": result.final_threat_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _piece_value(self, piece: Optional[chess.Piece]) -> int:
        if piece is None:
            return 0
        return PIECE_VALUES.get(piece.piece_type, 0)

    def _classify_threat(
        self,
        board: chess.Board,
        move: chess.Move,
        opponent: chess.Color,
        aion: chess.Color,
    ) -> OpponentThreat:
        target_piece = board.piece_at(move.to_square)
        is_capture = board.is_capture(move)
        promotes = move.promotion is not None

        probe = board.copy(stack=False)
        probe.push(move)

        gives_check = probe.is_check()
        gives_checkmate = probe.is_checkmate()

        captured_value = self._piece_value(target_piece)
        captured_name = chess.piece_name(target_piece.piece_type) if target_piece else None

        threat_score = 0
        threat_type = "quiet"
        reasons: List[str] = []

        if gives_checkmate:
            threat_score += 100000
            threat_type = "checkmate"
            reasons.append("immediate checkmate")

        if gives_check:
            threat_score += 1500
            if threat_type == "quiet":
                threat_type = "check"
            reasons.append("gives check")

        if is_capture and target_piece:
            threat_score += captured_value
            if captured_value >= 900:
                threat_type = "queen_capture"
            elif captured_value >= 500 and threat_type == "quiet":
                threat_type = "major_capture"
            elif threat_type == "quiet":
                threat_type = "capture"
            reasons.append(f"captures {captured_name}")

        if promotes:
            promo_value = PIECE_VALUES.get(move.promotion, 900)
            threat_score += 1200 + promo_value
            if threat_type == "quiet":
                threat_type = "promotion"
            reasons.append("promotion threat")

        # Also score attacks created against AION queen/rook after opponent move.
        for sq, piece in probe.piece_map().items():
            if piece.color == aion and piece.piece_type in (chess.QUEEN, chess.ROOK):
                if probe.is_attacked_by(opponent, sq):
                    value = PIECE_VALUES[piece.piece_type]
                    threat_score += value // 2
                    reasons.append(f"attacks {chess.piece_name(piece.piece_type)}")

        if not reasons:
            reasons.append("no immediate tactical threat")

        return OpponentThreat(
            move=move.uci(),
            threat_type=threat_type,
            target_square=chess.square_name(move.to_square),
            captured_piece_type=captured_name,
            captured_piece_value=captured_value,
            gives_check=gives_check,
            gives_checkmate=gives_checkmate,
            promotes=promotes,
            threat_score=threat_score,
            explanation="; ".join(reasons),
        )

    def run(
        self,
        *,
        input_fen: str,
        aion_side: str = "white",
        high_threat_threshold: int = 900,
        critical_threat_threshold: int = 1500,
        task_name: str = "full_chess_opponent_threat_map",
    ) -> OpponentThreatMapResult:
        board = chess.Board(input_fen)

        aion = chess.WHITE if aion_side.lower() == "white" else chess.BLACK
        opponent = not aion

        # Threat map is from the opponent's point of view.
        board.turn = opponent

        threats = [
            self._classify_threat(board, move, opponent, aion)
            for move in board.legal_moves
        ]

        threats.sort(key=lambda t: (t.threat_score, t.move), reverse=True)

        highest = threats[0] if threats else None
        highest_score = highest.threat_score if highest else 0
        high_count = sum(1 for t in threats if t.threat_score >= high_threat_threshold)
        critical = highest_score >= critical_threat_threshold

        aion_king_square = board.king(aion)
        king_square_name = chess.square_name(aion_king_square) if aion_king_square is not None else ""
        aion_king_in_check = board.is_check()

        if critical:
            response_mode = "neutralise_critical_threat"
        elif high_count:
            response_mode = "reduce_opponent_threats"
        else:
            response_mode = "continue_plan"

        trace_payload = {
            "input_fen": input_fen,
            "aion_side": aion_side,
            "opponent_legal_move_count": len(threats),
            "threat_count": len([t for t in threats if t.threat_score > 0]),
            "highest_threat_score": highest_score,
            "recommended_response_mode": response_mode,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["threat_map_run_count"] = int(self.policy.get("threat_map_run_count", 0)) + 1
        self.policy["last_highest_threat_score"] = highest_score
        self.policy["last_recommended_response_mode"] = response_mode
        self.policy["last_trace_hash"] = trace_hash
        if critical:
            self.policy["critical_threat_seen_count"] = int(self.policy.get("critical_threat_seen_count", 0)) + 1

        evidence = {
            "opponent_threat_map_active": True,
            "opponent_legal_moves_scored": True,
            "check_threats_detected": True,
            "checkmate_threats_detected": True,
            "capture_threats_detected": True,
            "promotion_threats_detected": True,
            "major_piece_attack_pressure_scored": True,
            "recommended_response_mode_emitted": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = OpponentThreatMapResult(
            kernel_version="phase22e29_full_chess_opponent_threat_map_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            aion_side=aion_side,
            opponent_side="black" if opponent == chess.BLACK else "white",
            threat_map_active=True,
            opponent_legal_move_count=len(threats),
            threat_count=len([t for t in threats if t.threat_score > 0]),
            high_threat_count=high_count,
            critical_threat_found=critical,
            highest_threat_score=highest_score,
            highest_threat=asdict(highest) if highest else None,
            top_threats=[asdict(t) for t in threats[:8]],
            defended_aion_king_square=king_square_name,
            aion_king_in_check=aion_king_in_check,
            recommended_response_mode=response_mode,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_threat_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel builds an opponent threat map from the current board state. It scores the opponent's "
                "legal replies for checkmate, check, capture, promotion, and attacks on major pieces. It does not "
                "call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_opponent_threat_map_kernel(
    *,
    input_fen: str,
    aion_side: str = "white",
    high_threat_threshold: int = 900,
    critical_threat_threshold: int = 1500,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_opponent_threat_map",
) -> OpponentThreatMapResult:
    return AionOpponentThreatMapKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        aion_side=aion_side,
        high_threat_threshold=high_threat_threshold,
        critical_threat_threshold=critical_threat_threshold,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Opponent threat map memory saved to: {result.memory_path}")
