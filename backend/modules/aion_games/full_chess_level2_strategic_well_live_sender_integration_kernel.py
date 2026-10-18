from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_strategic_regression_well_optimiser_kernel import (
    run_full_chess_strategic_regression_well_optimiser_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_strategic_well_live_sender_integration_memory.json")


@dataclass(frozen=True)
class StrategicWellLiveSenderIntegrationResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    game_id: str
    live_sender_integration_active: bool
    selected_move: str
    selected_move_is_legal: bool
    selected_source: str
    regression_well_score: int
    safety_passed: bool
    safe_to_send: bool
    live_post_allowed: bool
    live_post_attempted: bool
    live_post_succeeded: bool
    sender_mode: str
    sender_reason: str
    repeated_moves: List[str]
    repeated_squares: List[str]
    strategic_well_summary: Dict[str, Any]
    sender_envelope: Dict[str, Any]
    trace_hash: str
    policy_memory_mutated: bool
    final_sender_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionStrategicWellLiveSenderIntegrationKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "integration_run_count": 0,
            "safe_to_send_count": 0,
            "blocked_send_count": 0,
            "last_selected_move": "",
            "last_sender_mode": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_well_live_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicWellLiveSenderIntegrationResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e35_strategic_well_live_sender_integration_memory_v1",
            "task_name": result.task_name,
            "strategic_well_live_sender_policy": result.final_sender_policy,
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

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        game_id: str = "",
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        allow_live_post: bool = False,
        human_confirmed: bool = False,
        live_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = True,
        task_name: str = "full_chess_level2_strategic_well_live_sender_integration",
    ) -> StrategicWellLiveSenderIntegrationResult:
        repeated_moves = list(repeated_moves or [])
        repeated_squares = list(repeated_squares or [])

        well = run_full_chess_strategic_regression_well_optimiser_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            repeated_squares=repeated_squares,
            memory_path=self.memory_path.parent / "phase22e35_child_strategic_well_memory.json",
        )

        selected_move = well.selected_move
        legal = self._is_legal(input_fen, side_to_move, selected_move)
        safe_to_send = bool(legal and well.safety_passed and selected_move)

        live_post_allowed = bool(
            allow_live_post
            and human_confirmed
            and live_stream_confirmed
            and one_move_gate_enabled
            and safe_to_send
            and game_id
        )

        # Phase 22E.35 is integration-only. It prepares the sender envelope but does not POST.
        live_post_attempted = False
        live_post_succeeded = False

        if live_post_allowed:
            sender_mode = "ready_for_authorised_live_sender"
            sender_reason = "strategic well selected a legal safe move and all live gates are true"
        elif safe_to_send:
            sender_mode = "dry_run_ready"
            sender_reason = "strategic well selected a legal safe move but live post gates are not all enabled"
        else:
            sender_mode = "blocked"
            sender_reason = "strategic well move failed legality or safety gate"

        sender_envelope = {
            "phase": "22E.35",
            "game_id": game_id,
            "move_uci": selected_move,
            "side_to_move": side_to_move,
            "safe_to_send": safe_to_send,
            "live_post_allowed": live_post_allowed,
            "allow_live_post": allow_live_post,
            "human_confirmed": human_confirmed,
            "live_stream_confirmed": live_stream_confirmed,
            "one_move_gate_enabled": one_move_gate_enabled,
            "selected_source": well.selected_source,
            "regression_well_score": well.regression_well_score,
            "sender_mode": sender_mode,
        }

        strategic_well_summary = {
            "selected_move": well.selected_move,
            "selected_source": well.selected_source,
            "regression_well_score": well.regression_well_score,
            "safety_passed": well.safety_passed,
            "opponent_response_mode": well.opponent_response_mode,
            "passed_pawn_policy": well.passed_pawn_policy,
            "mate_net_type": well.mate_net_type,
            "plan": well.plan,
            "repetition_detected": well.repetition_detected,
            "component_summary": well.component_summary,
        }

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "game_id": game_id,
            "selected_move": selected_move,
            "selected_source": well.selected_source,
            "safe_to_send": safe_to_send,
            "live_post_allowed": live_post_allowed,
            "sender_mode": sender_mode,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["integration_run_count"] = int(self.policy.get("integration_run_count", 0)) + 1
        self.policy["last_selected_move"] = selected_move
        self.policy["last_sender_mode"] = sender_mode
        self.policy["last_trace_hash"] = trace_hash

        if safe_to_send:
            self.policy["safe_to_send_count"] = int(self.policy.get("safe_to_send_count", 0)) + 1
        else:
            self.policy["blocked_send_count"] = int(self.policy.get("blocked_send_count", 0)) + 1

        evidence = {
            "strategic_regression_well_consumed": True,
            "live_sender_integration_active": True,
            "legality_gate_checked": True,
            "safety_gate_checked": True,
            "human_confirmation_gate_checked": True,
            "live_stream_gate_checked": True,
            "one_move_gate_checked": True,
            "sender_envelope_emitted": True,
            "integration_only_no_post_attempted": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = StrategicWellLiveSenderIntegrationResult(
            kernel_version="phase22e35_full_chess_level2_strategic_well_live_sender_integration_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            game_id=game_id,
            live_sender_integration_active=True,
            selected_move=selected_move,
            selected_move_is_legal=legal,
            selected_source=well.selected_source,
            regression_well_score=well.regression_well_score,
            safety_passed=well.safety_passed,
            safe_to_send=safe_to_send,
            live_post_allowed=live_post_allowed,
            live_post_attempted=live_post_attempted,
            live_post_succeeded=live_post_succeeded,
            sender_mode=sender_mode,
            sender_reason=sender_reason,
            repeated_moves=repeated_moves,
            repeated_squares=repeated_squares,
            strategic_well_summary=strategic_well_summary,
            sender_envelope=sender_envelope,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_sender_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel integrates the Phase 22E.34 Strategic Regression Well Optimiser into the live Level-2 "
                "sender path. It emits a sender-ready envelope only after legality, safety, human confirmation, live "
                "stream, and one-move gates are checked. Phase 22E.35 is integration-only and does not POST to Lichess. "
                "It does not call Stockfish, does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_strategic_well_live_sender_integration_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    game_id: str = "",
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    allow_live_post: bool = False,
    human_confirmed: bool = False,
    live_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = True,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_strategic_well_live_sender_integration",
) -> StrategicWellLiveSenderIntegrationResult:
    return AionStrategicWellLiveSenderIntegrationKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        game_id=game_id,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        allow_live_post=allow_live_post,
        human_confirmed=human_confirmed,
        live_stream_confirmed=live_stream_confirmed,
        one_move_gate_enabled=one_move_gate_enabled,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        game_id="dry_run_game",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
        allow_live_post=False,
        human_confirmed=False,
        live_stream_confirmed=False,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic Well live sender integration memory saved to: {result.memory_path}")
