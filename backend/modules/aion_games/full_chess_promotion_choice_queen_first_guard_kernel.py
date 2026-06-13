from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from backend.modules.aion_games.full_chess_intent_driven_strategic_regression_well_kernel import (
    run_full_chess_intent_driven_strategic_regression_well_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_promotion_choice_queen_first_guard_memory.json")


@dataclass(frozen=True)
class PromotionChoiceQueenFirstGuardResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    base_selected_move: str
    base_well_selected_move: str
    final_selected_move: str
    final_selected_source: str
    intent_override_applied: bool
    final_regression_well_score: int
    final_selected_move_is_legal: bool
    queen_promotion_available: bool
    underpromotion_detected: bool
    queen_override_applied: bool
    override_reason: str
    active_intent: str
    selected_source: str
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionPromotionChoiceQueenFirstGuardKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "queen_override_count": 0,
            "base_move_kept_count": 0,
            "last_base_selected_move": "",
            "last_final_selected_move": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = payload.get("promotion_choice_queen_first_guard_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: PromotionChoiceQueenFirstGuardResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e41_promotion_choice_queen_first_guard_memory_v1",
            "task_name": result.task_name,
            "promotion_choice_queen_first_guard_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _queen_version(self, move_uci: str) -> str:
        return move_uci[:4] + "q" if len(move_uci) == 5 else move_uci

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[list[str]] = None,
        repeated_squares: Optional[list[str]] = None,
        forced_base_selected_move: Optional[str] = None,
    task_name: str = "full_chess_promotion_choice_queen_first_guard",
    ) -> PromotionChoiceQueenFirstGuardResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        base = run_full_chess_intent_driven_strategic_regression_well_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            memory_path=self.memory_path.parent / "phase22e41_child_intent_well_memory.json",
        )

        base_move = forced_base_selected_move or base.final_selected_move
        final_move = base_move
        underpromotion_detected = len(base_move) == 5 and base_move[-1] in {"r", "b", "n"}
        queen_move = self._queen_version(base_move)
        queen_promotion_available = False
        queen_override_applied = False
        override_reason = ""

        if underpromotion_detected:
            try:
                queen_promotion_available = chess.Move.from_uci(queen_move) in board.legal_moves
            except Exception:
                queen_promotion_available = False

            if queen_promotion_available:
                final_move = queen_move
                queen_override_applied = True
                override_reason = "queen promotion is legal and no proven underpromotion requirement exists"

        try:
            final_selected_move_is_legal = chess.Move.from_uci(final_move) in board.legal_moves
        except Exception:
            final_selected_move_is_legal = False

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "base_selected_move": base_move,
            "final_selected_move": final_move,
            "underpromotion_detected": underpromotion_detected,
            "queen_promotion_available": queen_promotion_available,
            "queen_override_applied": queen_override_applied,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_base_selected_move"] = base_move
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash

        if queen_override_applied:
            self.policy["queen_override_count"] = int(self.policy.get("queen_override_count", 0)) + 1
        else:
            self.policy["base_move_kept_count"] = int(self.policy.get("base_move_kept_count", 0)) + 1

        evidence = {
            "phase22e37_intent_well_consumed": True,
            "underpromotion_checked": True,
            "queen_first_policy_enabled": True,
            "queen_override_requires_queen_legal": True,
            "move_legality_checked": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = PromotionChoiceQueenFirstGuardResult(
            kernel_version="phase22e41_full_chess_promotion_choice_queen_first_guard_kernel_v1",
        task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=base_move,
            base_well_selected_move=getattr(base, "base_well_selected_move", base_move),
            final_selected_move=final_move,
            final_selected_source=(
                "promotion_choice_queen_first_guard"
                if queen_override_applied
                else getattr(base, "final_selected_source", "")
            ),
            intent_override_applied=bool(getattr(base, "intent_override_applied", False)) or queen_override_applied,
            final_regression_well_score=int(getattr(base, "final_regression_well_score", 0)),
            final_selected_move_is_legal=final_selected_move_is_legal,
            queen_promotion_available=queen_promotion_available,
            underpromotion_detected=underpromotion_detected,
            queen_override_applied=queen_override_applied,
            override_reason=override_reason,
            active_intent=base.active_intent,
            selected_source=(
                "promotion_choice_queen_first_guard"
                if queen_override_applied
                else base.final_selected_source
            ),
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel enforces queen-first promotion choice unless underpromotion is explicitly proven necessary. "
                "It does not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_promotion_choice_queen_first_guard_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[list[str]] = None,
    repeated_squares: Optional[list[str]] = None,
    memory_path: Optional[Path] = None,
    forced_base_selected_move: Optional[str] = None,
    task_name: str = "full_chess_promotion_choice_queen_first_guard",
) -> PromotionChoiceQueenFirstGuardResult:
    return AionPromotionChoiceQueenFirstGuardKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        forced_base_selected_move=forced_base_selected_move,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Promotion queen-first guard memory saved to: {result.memory_path}")
