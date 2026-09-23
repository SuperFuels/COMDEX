from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_zugzwang_choice_architecture_selector_kernel import (
    run_full_chess_zugzwang_choice_architecture_selector_kernel,
)
from backend.modules.aion_games.full_chess_one_ply_blunder_guard_kernel import (
    run_full_chess_one_ply_blunder_guard_kernel,
)
from backend.modules.aion_games.full_chess_opponent_threat_map_kernel import (
    run_full_chess_opponent_threat_map_kernel,
)
from backend.modules.aion_games.full_chess_passed_pawn_conversion_policy_kernel import (
    run_full_chess_passed_pawn_conversion_policy_kernel,
)
from backend.modules.aion_games.full_chess_endgame_box_mate_net_builder_kernel import (
    run_full_chess_endgame_box_mate_net_builder_kernel,
)
from backend.modules.aion_games.full_chess_plan_continuity_memory_kernel import (
    run_full_chess_plan_continuity_memory_kernel,
)
from backend.modules.aion_games.full_chess_rook_bishop_repetition_breaker_kernel import (
    run_full_chess_rook_bishop_repetition_breaker_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_strategic_regression_well_optimiser_memory.json")


@dataclass(frozen=True)
class StrategicRegressionWellResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    strategic_regression_well_active: bool
    selected_move: str
    selected_move_is_legal: bool
    selected_source: str
    regression_well_score: int
    safety_passed: bool
    blunder_rejected: bool
    opponent_response_mode: str
    passed_pawn_policy: str
    mate_net_type: str
    plan: str
    repetition_detected: bool
    component_summary: Dict[str, Any]
    trace_hash: str
    policy_memory_mutated: bool
    final_well_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionStrategicRegressionWellOptimiserKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "well_optimiser_run_count": 0,
            "safe_selection_count": 0,
            "fallback_selection_count": 0,
            "last_selected_move": "",
            "last_selected_source": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_regression_well_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicRegressionWellResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e34_strategic_regression_well_optimiser_memory_v1",
            "task_name": result.task_name,
            "strategic_regression_well_policy": result.final_well_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _is_legal(self, input_fen: str, side_to_move: str, move_uci: str) -> bool:
        if not move_uci:
            return False
        try:
            board = chess.Board(input_fen)
            board.turn = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
            return chess.Move.from_uci(move_uci) in board.legal_moves
        except Exception:
            return False

    def _guard(self, input_fen: str, side_to_move: str, move_uci: str) -> Any:
        return run_full_chess_one_ply_blunder_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_move=move_uci,
            max_allowed_reply_score=900,
            memory_path=self.memory_path.parent / "phase22e34_child_blunder_guard_memory.json",
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        task_name: str = "full_chess_strategic_regression_well_optimiser",
    ) -> StrategicRegressionWellResult:
        repeated_moves = list(repeated_moves or [])
        repeated_squares = list(repeated_squares or [])

        zug = run_full_chess_zugzwang_choice_architecture_selector_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            repeated_to_squares=repeated_squares,
            memory_path=self.memory_path.parent / "phase22e34_child_zugzwang_memory.json",
        )

        threat = run_full_chess_opponent_threat_map_kernel(
            input_fen=input_fen,
            aion_side=side_to_move,
            memory_path=self.memory_path.parent / "phase22e34_child_threat_map_memory.json",
        )

        pawn = run_full_chess_passed_pawn_conversion_policy_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            memory_path=self.memory_path.parent / "phase22e34_child_passed_pawn_memory.json",
        )

        mate = run_full_chess_endgame_box_mate_net_builder_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            memory_path=self.memory_path.parent / "phase22e34_child_mate_net_memory.json",
        )

        repeat = run_full_chess_rook_bishop_repetition_breaker_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            repeated_squares=repeated_squares,
            memory_path=self.memory_path.parent / "phase22e34_child_repetition_breaker_memory.json",
        )

        candidates: List[Dict[str, Any]] = []

        if pawn.recommended_move and pawn.recommended_move_is_legal:
            candidates.append({
                "source": "passed_pawn_conversion_policy",
                "move": pawn.recommended_move,
                "base_score": 8000 if pawn.recommended_policy == "promote_now" else 4200,
            })

        if mate.selected_move and mate.selected_move_is_legal:
            candidates.append({
                "source": "endgame_box_mate_net_builder",
                "move": mate.selected_move,
                "base_score": 5200 + int(mate.selected_score / 10),
            })

        if repeat.selected_breaker_move and repeat.selected_breaker_move_is_legal and repeat.repetition_detected:
            candidates.append({
                "source": "rook_bishop_repetition_breaker",
                "move": repeat.selected_breaker_move,
                "base_score": 4800 + int(repeat.selected_score / 10),
            })

        if zug.selected_move and zug.selected_move_is_legal:
            candidates.append({
                "source": "zugzwang_choice_architecture_selector",
                "move": zug.selected_move,
                "base_score": 4000 + int(zug.selected_score / 10),
            })

        if not candidates:
            for c in zug.top_candidates[:5]:
                if c.get("is_legal"):
                    candidates.append({
                        "source": "zugzwang_top_candidate",
                        "move": c["move"],
                        "base_score": 2500 + int(c.get("score", 0) / 10),
                    })

        scored: List[Dict[str, Any]] = []
        selected: Optional[Dict[str, Any]] = None
        selected_guard = None

        for candidate in candidates:
            move = candidate["move"]
            if not self._is_legal(input_fen, side_to_move, move):
                continue

            guard = self._guard(input_fen, side_to_move, move)
            score = int(candidate["base_score"])

            if guard.safe_to_send:
                score += 3000
            else:
                score -= 100000

            if threat.recommended_response_mode == "neutralise_critical_threat":
                score -= 500

            if pawn.recommended_policy == "stop_enemy_promotion" and candidate["source"] != "passed_pawn_conversion_policy":
                score -= 800

            if repeat.repetition_detected and candidate["source"] == "rook_bishop_repetition_breaker":
                score += 1600

            plan = run_full_chess_plan_continuity_memory_kernel(
                input_fen=input_fen,
                side_to_move=side_to_move,
                candidate_move=move,
                memory_path=self.memory_path.parent / "phase22e34_child_plan_memory.json",
            )
            score += int(plan.continuity_score / 10)

            item = {
                "source": candidate["source"],
                "move": move,
                "base_score": candidate["base_score"],
                "guard_safe_to_send": guard.safe_to_send,
                "guard_worst_reply_score": guard.worst_reply_score,
                "plan": plan.current_plan,
                "plan_continuity_score": plan.continuity_score,
                "final_score": score,
            }
            scored.append(item)

            if selected is None or score > selected["final_score"]:
                selected = item
                selected_guard = guard

        if selected is None and zug.selected_move:
            selected = {
                "source": "emergency_zugzwang_fallback",
                "move": zug.selected_move,
                "base_score": 0,
                "guard_safe_to_send": False,
                "guard_worst_reply_score": 100000,
                "plan": "",
                "plan_continuity_score": 0,
                "final_score": -100000,
            }

        selected_move = selected["move"] if selected else ""
        selected_source = selected["source"] if selected else ""
        selected_score = int(selected["final_score"]) if selected else 0
        legal = self._is_legal(input_fen, side_to_move, selected_move)
        safety_passed = bool(selected and selected.get("guard_safe_to_send"))
        blunder_rejected = bool(selected_guard and selected_guard.move_rejected_as_blunder)

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "selected_move": selected_move,
            "selected_source": selected_source,
            "regression_well_score": selected_score,
            "safety_passed": safety_passed,
            "component_count": len(scored),
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["well_optimiser_run_count"] = int(self.policy.get("well_optimiser_run_count", 0)) + 1
        self.policy["last_selected_move"] = selected_move
        self.policy["last_selected_source"] = selected_source
        self.policy["last_trace_hash"] = trace_hash

        if safety_passed:
            self.policy["safe_selection_count"] = int(self.policy.get("safe_selection_count", 0)) + 1
        else:
            self.policy["fallback_selection_count"] = int(self.policy.get("fallback_selection_count", 0)) + 1

        component_summary = {
            "ranked_candidates": sorted(scored, key=lambda x: x["final_score"], reverse=True)[:8],
            "zugzwang_selected_move": zug.selected_move,
            "zugzwang_score": zug.selected_score,
            "threat_response_mode": threat.recommended_response_mode,
            "highest_opponent_threat_score": threat.highest_threat_score,
            "passed_pawn_policy": pawn.recommended_policy,
            "passed_pawn_move": pawn.recommended_move,
            "mate_net_type": mate.detected_endgame_type,
            "mate_net_move": mate.selected_move,
            "repetition_detected": repeat.repetition_detected,
            "repetition_breaker_move": repeat.selected_breaker_move,
        }

        evidence = {
            "strategic_regression_well_active": True,
            "zugzwang_choice_architecture_consumed": True,
            "one_ply_blunder_guard_consumed": True,
            "opponent_threat_map_consumed": True,
            "passed_pawn_policy_consumed": True,
            "endgame_box_mate_net_consumed": True,
            "plan_continuity_memory_consumed": True,
            "rook_bishop_repetition_breaker_consumed": True,
            "safe_to_send_required": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = StrategicRegressionWellResult(
            kernel_version="phase22e34_full_chess_strategic_regression_well_optimiser_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            strategic_regression_well_active=True,
            selected_move=selected_move,
            selected_move_is_legal=legal,
            selected_source=selected_source,
            regression_well_score=selected_score,
            safety_passed=safety_passed,
            blunder_rejected=blunder_rejected,
            opponent_response_mode=threat.recommended_response_mode,
            passed_pawn_policy=pawn.recommended_policy,
            mate_net_type=mate.detected_endgame_type,
            plan=str(selected.get("plan", "")) if selected else "",
            repetition_detected=repeat.repetition_detected,
            component_summary=component_summary,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_well_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel implements the Strategic Regression Well Optimiser. It combines Zugzwang choice "
                "architecture, one-ply blunder safety, opponent threat mapping, passed-pawn conversion, endgame "
                "mate-net pressure, plan continuity, and repetition breaking into a single deterministic move "
                "selection policy. It does not call Stockfish, does not use LLM move judgement, and does not use "
                "Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_strategic_regression_well_optimiser_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_strategic_regression_well_optimiser",
) -> StrategicRegressionWellResult:
    return AionStrategicRegressionWellOptimiserKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic Regression Well memory saved to: {result.memory_path}")
