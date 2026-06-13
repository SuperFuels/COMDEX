from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_proactive_intent_primacy_plan_enforcement_kernel import (
    run_full_chess_proactive_intent_primacy_plan_enforcement_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_live_one_move_strategic_well_sender_memory.json")


@dataclass(frozen=True)
class LiveOneMoveStrategicWellSenderResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    game_id: str
    input_fen: str
    side_to_move: str
    target_level: int
    selected_move: str
    selected_move_is_legal: bool
    selected_source: str
    active_intent: str
    base_well_selected_move: str
    intent_override_applied: bool
    regression_well_score: int
    explicit_live_send_authorized: bool
    human_operator_confirmed: bool
    live_game_stream_confirmed: bool
    one_move_gate_enabled: bool
    live_sender_enabled: bool
    allow_real_post: bool
    token_present: bool
    live_env_enabled: bool
    all_live_gates_passed: bool
    move_post_attempted: bool
    move_post_succeeded: bool
    move_post_status_code: int
    move_post_error: str
    trace_hash: str
    policy_memory_mutated: bool
    final_sender_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionLiveOneMoveStrategicWellSenderKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "post_attempt_count": 0,
            "post_success_count": 0,
            "blocked_count": 0,
            "last_game_id": "",
            "last_selected_move": "",
            "last_active_intent": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_one_move_strategic_well_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveOneMoveStrategicWellSenderResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e38_live_one_move_strategic_well_sender_memory_v1",
            "task_name": result.task_name,
            "live_one_move_strategic_well_sender_policy": result.final_sender_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _post_move(self, *, token: str, game_id: str, move_uci: str, timeout_seconds: int) -> tuple[bool, int, str]:
        url = f"https://lichess.org/api/bot/game/{game_id}/move/{move_uci}"
        req = urllib.request.Request(
            url,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                return 200 <= response.status < 300, int(response.status), ""
        except urllib.error.HTTPError as exc:
            return False, int(exc.code), str(exc)
        except Exception as exc:
            return False, 0, str(exc)

    def run(
        self,
        *,
        game_id: str,
        input_fen: str,
        side_to_move: str = "white",
        target_level: int = 2,
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        explicit_live_send_authorized: bool = False,
        human_operator_confirmed: bool = False,
        live_game_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = False,
        live_sender_enabled: bool = False,
        allow_real_post: bool = False,
        token: Optional[str] = None,
        timeout_seconds: int = 20,
        task_name: str = "full_chess_live_one_move_strategic_well_sender",
    ) -> LiveOneMoveStrategicWellSenderResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        strategic = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            memory_path=self.memory_path.parent / "phase22e38_child_proactive_intent_primacy_memory.json",
        )

        selected_move = strategic.final_selected_move
        try:
            selected_move_is_legal = chess.Move.from_uci(selected_move) in board.legal_moves
        except Exception:
            selected_move_is_legal = False

        token_value = token or os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token_value)
        live_env_enabled = os.environ.get("AION_LICHESS_LIVE", "") == "1"

        all_live_gates_passed = bool(
            game_id
            and target_level == 2
            and selected_move_is_legal
            and explicit_live_send_authorized
            and human_operator_confirmed
            and live_game_stream_confirmed
            and one_move_gate_enabled
            and live_sender_enabled
            and allow_real_post
            and token_present
            and live_env_enabled
        )

        move_post_attempted = False
        move_post_succeeded = False
        move_post_status_code = 0
        move_post_error = ""

        if all_live_gates_passed:
            move_post_attempted = True
            move_post_succeeded, move_post_status_code, move_post_error = self._post_move(
                token=token_value,
                game_id=game_id,
                move_uci=selected_move,
                timeout_seconds=timeout_seconds,
            )

        trace_payload = {
            "game_id": game_id,
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "selected_move": selected_move,
            "selected_move_is_legal": selected_move_is_legal,
            "active_intent": strategic.active_intent,
            "intent_override_applied": bool(getattr(strategic, "queen_override_applied", False)),
            "all_live_gates_passed": all_live_gates_passed,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "move_post_status_code": move_post_status_code,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_game_id"] = game_id
        self.policy["last_selected_move"] = selected_move
        self.policy["last_active_intent"] = strategic.active_intent
        self.policy["last_trace_hash"] = trace_hash

        if move_post_attempted:
            self.policy["post_attempt_count"] = int(self.policy.get("post_attempt_count", 0)) + 1
        if move_post_succeeded:
            self.policy["post_success_count"] = int(self.policy.get("post_success_count", 0)) + 1
        if not all_live_gates_passed:
            self.policy["blocked_count"] = int(self.policy.get("blocked_count", 0)) + 1

        evidence = {
            "phase22e44_proactive_intent_primacy_used": True,
            "phase22e43_anti_shuffling_guard_used": True,
            "phase22e42_passed_pawn_scope_guard_used": True,
            "phase22e41_promotion_choice_guard_used": True,
            "phase22e37_intent_driven_well_used": True,
            "one_move_only": True,
            "live_gates_required": True,
            "move_legality_checked": True,
            "opening_drift_guard_inherited": True,
            "posts_only_when_all_gates_pass": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveOneMoveStrategicWellSenderResult(
            kernel_version="phase22e38_full_chess_live_one_move_strategic_well_sender_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            game_id=game_id,
            input_fen=input_fen,
            side_to_move=side_to_move,
            target_level=target_level,
            selected_move=selected_move,
            selected_move_is_legal=selected_move_is_legal,
            selected_source=getattr(strategic, "final_selected_source", getattr(strategic, "selected_source", "")),
            active_intent=strategic.active_intent,
            base_well_selected_move=strategic.base_well_selected_move,
            intent_override_applied=bool(getattr(strategic, "intent_override_applied", False)) or bool(getattr(strategic, "queen_override_applied", False)),
            regression_well_score=int(getattr(strategic, "final_regression_well_score", 0)),
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_gate_enabled=one_move_gate_enabled,
            live_sender_enabled=live_sender_enabled,
            allow_real_post=allow_real_post,
            token_present=token_present,
            live_env_enabled=live_env_enabled,
            all_live_gates_passed=all_live_gates_passed,
            move_post_attempted=move_post_attempted,
            move_post_succeeded=move_post_succeeded,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_sender_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel sends at most one live Lichess move using the Phase 22E.37 intent-driven Strategic "
                "Regression Well. It posts only when all live gates are explicitly true. It does not call Stockfish, "
                "does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_one_move_strategic_well_sender_kernel(
    *,
    game_id: str,
    input_fen: str,
    side_to_move: str = "white",
    target_level: int = 2,
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    explicit_live_send_authorized: bool = False,
    human_operator_confirmed: bool = False,
    live_game_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = False,
    live_sender_enabled: bool = False,
    allow_real_post: bool = False,
    token: Optional[str] = None,
    timeout_seconds: int = 20,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_one_move_strategic_well_sender",
) -> LiveOneMoveStrategicWellSenderResult:
    return AionLiveOneMoveStrategicWellSenderKernel(memory_path=memory_path).run(
        game_id=game_id,
        input_fen=input_fen,
        side_to_move=side_to_move,
        target_level=target_level,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        explicit_live_send_authorized=explicit_live_send_authorized,
        human_operator_confirmed=human_operator_confirmed,
        live_game_stream_confirmed=live_game_stream_confirmed,
        one_move_gate_enabled=one_move_gate_enabled,
        live_sender_enabled=live_sender_enabled,
        allow_real_post=allow_real_post,
        token=token,
        timeout_seconds=timeout_seconds,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="dry_run_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live one-move strategic well sender memory saved to: {result.memory_path}")
