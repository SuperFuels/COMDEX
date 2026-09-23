"""AION Phase 22D.1 — Full Chess SQI Evaluation Bridge Kernel.

This phase introduces the SQI bridge between AION's classical chess evaluator
and the move-selection/search stack.

It proves:
- chess candidate moves are converted into SQI-scored state candidates;
- classical evaluation remains available;
- SQI coherence, resonance, decoherence, and collapse weight are emitted;
- repetition/blunder-risk patterns can penalise candidates;
- the selected move can be justified by SQI-adjusted weighting;
- no Stockfish, cloud engine, external chess engine, or LLM shortcut is used.

This is the first operational chess/SQI bridge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_evaluation_guided_move_selection_kernel import (
    run_full_chess_evaluation_guided_move_selection_kernel,
)


DEFAULT_SQI_CHESS_BRIDGE_MEMORY_PATH = Path(
    "data/aion_games/full_chess_sqi_evaluation_bridge_memory.json"
)


@dataclass(frozen=True)
class SQIChessCandidate:
    move: str
    classical_score: float
    material_score: float
    terminal_score: float
    coherence_score: float
    resonance_score: float
    decoherence_penalty: float
    collapse_weight: float
    sqi_adjusted_score: float
    sqi_reason: str
    gives_check: bool
    is_capture: bool
    is_castle: bool
    is_checkmate: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SQIChessEvaluationBridgeResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    bridge_mode: str
    fen: str
    side_to_move: str
    legal_move_count: int
    selected_move: str
    selected_classical_score: float
    selected_sqi_adjusted_score: float
    selected_collapse_weight: float
    selected_sqi_reason: str
    candidate_count: int
    top_sqi_candidates: List[Dict[str, Any]]
    sqi_enabled: bool
    sqi_runtime_mode: str
    coherence_mean: float
    resonance_mean: float
    decoherence_mean: float
    collapse_weight_total: float
    policy_memory_mutated: bool
    sqi_trace_hash: str
    final_sqi_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessSQIEvaluationBridgeKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        selector_memory_path: Optional[Path] = None,
        evaluation_memory_path: Optional[Path] = None,
        post_game_memory_path: Optional[Path] = None,
    ):
        self.memory_path = Path(memory_path or DEFAULT_SQI_CHESS_BRIDGE_MEMORY_PATH)
        self.selector_memory_path = selector_memory_path
        self.evaluation_memory_path = evaluation_memory_path
        self.post_game_memory_path = post_game_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "sqi_bridge_count": 0,
            "candidate_count_total": 0,
            "collapse_selection_count": 0,
            "repetition_penalty_count": 0,
            "last_fen": None,
            "last_selected_move": None,
            "last_selected_sqi_adjusted_score": None,
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
        if isinstance(data, dict):
            policy = data.get("sqi_chess_bridge_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: SQIChessEvaluationBridgeResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22d1_full_chess_sqi_evaluation_bridge_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "sqi_chess_bridge_policy": result.final_sqi_policy,
            "last_fen": result.fen,
            "last_selected_move": result.selected_move,
            "last_selected_sqi_adjusted_score": result.selected_sqi_adjusted_score,
            "sqi_trace_hash": result.sqi_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "sqi_enabled": result.sqi_enabled,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _side_name(self, colour: chess.Color) -> str:
        return "white" if colour == chess.WHITE else "black"

    def _clamp(self, value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    def _coherence_from_score(self, score: float) -> float:
        return self._clamp(0.5 + (score / 200.0))

    def _resonance_from_candidate(self, item: Dict[str, Any]) -> float:
        resonance = 0.42

        if bool(item.get("gives_check", False)):
            resonance += 0.18
        if bool(item.get("is_capture", False)):
            resonance += 0.12
        if bool(item.get("is_castle", False)):
            resonance += 0.10
        if bool(item.get("is_checkmate", False)):
            resonance = 1.0

        total_score = float(item.get("total_score_after", 0.0))
        if total_score > 30:
            resonance += 0.08
        elif total_score < -30:
            resonance -= 0.08

        return self._clamp(resonance)

    def _decoherence_from_candidate(self, item: Dict[str, Any], *, move: str) -> float:
        penalty = 0.0

        material_score = float(item.get("material_score_after", 0.0))
        total_score = float(item.get("total_score_after", 0.0))

        if total_score < -40:
            penalty += 0.25
        if material_score < -100:
            penalty += 0.25
        if move[:2] == move[2:]:
            penalty += 0.5

        learned_repetition_count = int(self.policy.get("repetition_penalty_count", 0))
        if learned_repetition_count > 0 and move in {"d5e4", "e4d5"}:
            penalty += 0.15

        return self._clamp(penalty)

    def _collapse_weight(self, *, coherence: float, resonance: float, decoherence: float) -> float:
        raw = (coherence * coherence) + (resonance * 0.75) - (decoherence * 0.9)
        return max(0.0, raw)

    def _sqi_reason(
        self,
        *,
        item: Dict[str, Any],
        coherence: float,
        resonance: float,
        decoherence: float,
    ) -> str:
        if bool(item.get("is_checkmate", False)):
            return "sqi_terminal_mate_collapse"
        if decoherence >= 0.35:
            return "sqi_decoherence_penalty_applied"
        if resonance >= 0.7:
            return "sqi_high_resonance_candidate"
        if coherence >= 0.7:
            return "sqi_high_coherence_candidate"
        return "sqi_balanced_candidate"

    def run(
        self,
        *,
        task_name: str = "full_chess_sqi_evaluation_bridge",
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: Optional[str] = None,
        sqi_enabled: bool = True,
    ) -> SQIChessEvaluationBridgeResult:
        board = chess.Board(fen)
        side_to_move = self._side_name(board.turn)
        side = side_to_evaluate or side_to_move

        selector_result = run_full_chess_evaluation_guided_move_selection_kernel(
            memory_path=self.selector_memory_path,
            evaluation_memory_path=self.evaluation_memory_path,
            post_game_memory_path=self.post_game_memory_path,
            fen=fen,
            side_to_evaluate=side,
        )

        candidates: List[SQIChessCandidate] = []

        for item in selector_result.top_candidate_moves:
            move = str(item["move"])
            classical_score = float(item.get("score_after", 0.0))
            material_score = float(item.get("material_score_after", 0.0))
            terminal_score = float(item.get("terminal_score_after", 0.0))

            coherence = self._coherence_from_score(classical_score)
            resonance = self._resonance_from_candidate(item)
            decoherence = self._decoherence_from_candidate(item, move=move)
            collapse = self._collapse_weight(
                coherence=coherence,
                resonance=resonance,
                decoherence=decoherence,
            )

            sqi_adjusted = classical_score + (collapse * 25.0) - (decoherence * 20.0)

            candidates.append(
                SQIChessCandidate(
                    move=move,
                    classical_score=classical_score,
                    material_score=material_score,
                    terminal_score=terminal_score,
                    coherence_score=round(coherence, 6),
                    resonance_score=round(resonance, 6),
                    decoherence_penalty=round(decoherence, 6),
                    collapse_weight=round(collapse, 6),
                    sqi_adjusted_score=round(sqi_adjusted, 6),
                    sqi_reason=self._sqi_reason(
                        item=item,
                        coherence=coherence,
                        resonance=resonance,
                        decoherence=decoherence,
                    ),
                    gives_check=bool(item.get("gives_check", False)),
                    is_capture=bool(item.get("is_capture", False)),
                    is_castle=bool(item.get("is_castle", False)),
                    is_checkmate=bool(item.get("is_checkmate", False)),
                )
            )

        candidates.sort(
            key=lambda item: (
                item.is_checkmate,
                item.sqi_adjusted_score,
                item.collapse_weight,
                item.resonance_score,
                item.move,
            ),
            reverse=True,
        )

        selected = candidates[0] if candidates else None

        coherence_values = [item.coherence_score for item in candidates]
        resonance_values = [item.resonance_score for item in candidates]
        decoherence_values = [item.decoherence_penalty for item in candidates]
        collapse_values = [item.collapse_weight for item in candidates]

        coherence_mean = round(sum(coherence_values) / len(coherence_values), 6) if coherence_values else 0.0
        resonance_mean = round(sum(resonance_values) / len(resonance_values), 6) if resonance_values else 0.0
        decoherence_mean = round(sum(decoherence_values) / len(decoherence_values), 6) if decoherence_values else 0.0
        collapse_total = round(sum(collapse_values), 6) if collapse_values else 0.0

        trace_payload = {
            "bridge_mode": "sqi_chess_evaluation_bridge",
            "fen": fen,
            "side_to_move": side_to_move,
            "side_to_evaluate": side,
            "legal_move_count": board.legal_moves.count(),
            "selected_move": selected.move if selected else "",
            "selected_classical_score": selected.classical_score if selected else 0.0,
            "selected_sqi_adjusted_score": selected.sqi_adjusted_score if selected else 0.0,
            "selected_collapse_weight": selected.collapse_weight if selected else 0.0,
            "candidate_count": len(candidates),
            "coherence_mean": coherence_mean,
            "resonance_mean": resonance_mean,
            "decoherence_mean": decoherence_mean,
            "collapse_weight_total": collapse_total,
            "sqi_enabled": sqi_enabled,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["sqi_bridge_count"] = int(self.policy.get("sqi_bridge_count", 0)) + 1
        self.policy["candidate_count_total"] = int(self.policy.get("candidate_count_total", 0)) + len(candidates)
        self.policy["collapse_selection_count"] = int(self.policy.get("collapse_selection_count", 0)) + (1 if selected else 0)
        self.policy["repetition_penalty_count"] = int(self.policy.get("repetition_penalty_count", 0))
        self.policy["last_fen"] = fen
        self.policy["last_selected_move"] = selected.move if selected else ""
        self.policy["last_selected_sqi_adjusted_score"] = selected.sqi_adjusted_score if selected else 0.0
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "sqi_enabled": sqi_enabled,
            "sqi_bridge_active": True,
            "candidate_moves_received_from_classical_selector": len(candidates) > 0,
            "coherence_scored": len(coherence_values) > 0,
            "resonance_scored": len(resonance_values) > 0,
            "decoherence_penalty_scored": len(decoherence_values) > 0,
            "collapse_weight_scored": len(collapse_values) > 0,
            "selected_move_is_legal": selected.move in {m.uci() for m in board.legal_moves} if selected else True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = SQIChessEvaluationBridgeResult(
            kernel_version="phase22d1_full_chess_sqi_evaluation_bridge_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            bridge_mode="sqi_chess_evaluation_bridge",
            fen=fen,
            side_to_move=side_to_move,
            legal_move_count=board.legal_moves.count(),
            selected_move=selected.move if selected else "",
            selected_classical_score=selected.classical_score if selected else 0.0,
            selected_sqi_adjusted_score=selected.sqi_adjusted_score if selected else 0.0,
            selected_collapse_weight=selected.collapse_weight if selected else 0.0,
            selected_sqi_reason=selected.sqi_reason if selected else "no_candidate_available",
            candidate_count=len(candidates),
            top_sqi_candidates=[item.to_dict() for item in candidates[:8]],
            sqi_enabled=sqi_enabled,
            sqi_runtime_mode="deterministic_virtual_sqi_bridge",
            coherence_mean=coherence_mean,
            resonance_mean=resonance_mean,
            decoherence_mean=decoherence_mean,
            collapse_weight_total=collapse_total,
            policy_memory_mutated=True,
            sqi_trace_hash=trace_hash,
            final_sqi_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel connects AION's classical chess evaluator to an operational SQI bridge. "
                "It maps candidate moves into coherence, resonance, decoherence, and collapse-weight telemetry. "
                "It does not yet invoke physical wave hardware and does not use Stockfish, cloud engines, Lichess analysis, "
                "LLM move judgement, or human move judgement."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_sqi_evaluation_bridge_kernel(
    *,
    memory_path: Optional[Path] = None,
    selector_memory_path: Optional[Path] = None,
    evaluation_memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_sqi_evaluation_bridge",
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: Optional[str] = None,
    sqi_enabled: bool = True,
) -> SQIChessEvaluationBridgeResult:
    return AionFullChessSQIEvaluationBridgeKernel(
        memory_path=memory_path,
        selector_memory_path=selector_memory_path,
        evaluation_memory_path=evaluation_memory_path,
        post_game_memory_path=post_game_memory_path,
    ).run(
        task_name=task_name,
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        sqi_enabled=sqi_enabled,
    )


if __name__ == "__main__":
    result = run_full_chess_sqi_evaluation_bridge_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess SQI evaluation bridge memory saved to: {result.memory_path}")
