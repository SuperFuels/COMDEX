from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import chess

from .full_chess_live_level2_one_move_authorized_sender_kernel import (
    run_full_chess_live_level2_one_move_authorized_sender_kernel,
)
from .full_chess_queen_endgame_mate_conversion_kernel import (
    run_full_chess_queen_endgame_mate_conversion_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_queen_endgame_override_live_sender_memory.json")


@dataclass(frozen=True)
class QueenEndgameOverrideLiveSenderResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    sender_mode: str
    game_id: str
    input_fen: str
    side_to_move: str
    target_level: int
    queen_endgame_override_active: bool
    base_sender_consumed: bool
    base_selected_move: str
    override_selected_move: str
    final_selected_move: str
    final_selected_move_is_legal: bool
    move_post_attempted: bool
    move_post_succeeded: bool
    move_post_status_code: Optional[int]
    move_post_error: Optional[str]
    explicit_live_send_authorized: bool
    human_operator_confirmed: bool
    live_game_stream_confirmed: bool
    one_move_gate_enabled: bool
    live_sender_enabled: bool
    allow_real_post: bool
    repeated_moves: List[str]
    repeated_queen_squares: List[str]
    clock_pressure_active: bool
    override_trace_hash: str
    sender_trace_hash: str
    policy_memory_mutated: bool
    final_override_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionQueenEndgameOverrideLiveSenderKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        queen_memory_path: Optional[Path] = None,
        base_sender_memory_path: Optional[Path] = None,
        smoke_memory_path: Optional[Path] = None,
        preflight_memory_path: Optional[Path] = None,
        gate_memory_path: Optional[Path] = None,
        adapter_memory_path: Optional[Path] = None,
        loop_memory_path: Optional[Path] = None,
        rerank_memory_path: Optional[Path] = None,
        bias_memory_path: Optional[Path] = None,
        concept_memory_path: Optional[Path] = None,
        forecast_memory_path: Optional[Path] = None,
        long_term_plan_memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.queen_memory_path = queen_memory_path
        self.base_sender_memory_path = base_sender_memory_path
        self.smoke_memory_path = smoke_memory_path
        self.preflight_memory_path = preflight_memory_path
        self.gate_memory_path = gate_memory_path
        self.adapter_memory_path = adapter_memory_path
        self.loop_memory_path = loop_memory_path
        self.rerank_memory_path = rerank_memory_path
        self.bias_memory_path = bias_memory_path
        self.concept_memory_path = concept_memory_path
        self.forecast_memory_path = forecast_memory_path
        self.long_term_plan_memory_path = long_term_plan_memory_path
        self.curriculum_memory_path = curriculum_memory_path
        self.review_memory_path = review_memory_path
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "override_sender_run_count": 0,
            "queen_override_active_count": 0,
            "send_attempt_count": 0,
            "send_success_count": 0,
            "last_final_selected_move": None,
            "last_override_active": False,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("queen_endgame_override_live_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: QueenEndgameOverrideLiveSenderResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e21_queen_endgame_override_live_sender_memory_v1",
            "task_name": result.task_name,
            "queen_endgame_override_live_sender_policy": result.final_override_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _post_lichess_move(self, *, token: str, game_id: str, move_uci: str) -> tuple[bool, Optional[int], Optional[str]]:
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
            with urllib.request.urlopen(req, timeout=10) as response:
                return 200 <= int(response.status) < 300, int(response.status), None
        except urllib.error.HTTPError as exc:
            return False, int(exc.code), str(exc)
        except Exception as exc:
            return False, None, str(exc)

    def run(
        self,
        *,
        game_id: str,
        input_fen: str,
        side_to_move: str = "white",
        target_level: int = 2,
        repeated_moves: Optional[List[str]] = None,
        repeated_queen_squares: Optional[List[str]] = None,
        recent_fens: Optional[List[str]] = None,
        clock_seconds_remaining: Optional[float] = None,
        env_token_name: str = "LICHESS_BOT_TOKEN",
        explicit_live_send_authorized: bool = False,
        human_operator_confirmed: bool = False,
        live_game_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = False,
        live_sender_enabled: bool = False,
        allow_real_post: bool = False,
        post_move_callable: Optional[Callable[[str, str, str], tuple[bool, Optional[int], Optional[str]]]] = None,
        task_name: str = "full_chess_queen_endgame_override_live_sender",
    ) -> QueenEndgameOverrideLiveSenderResult:
        repeated_moves = list(repeated_moves or [])
        repeated_queen_squares = list(repeated_queen_squares or [])
        recent_fens = list(recent_fens or [])

        board = chess.Board(input_fen)
        token = os.environ.get(env_token_name, "").strip()
        token_present = bool(token)

        queen = run_full_chess_queen_endgame_mate_conversion_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=repeated_moves,
            repeated_queen_squares=repeated_queen_squares,
            recent_fens=recent_fens,
            clock_seconds_remaining=clock_seconds_remaining,
            memory_path=self.queen_memory_path,
        )

        override_active = queen.queen_endgame_conversion_active and queen.selected_move_is_legal

        base_sender_consumed = False
        base_selected_move = ""

        if override_active:
            final_selected_move = queen.selected_move
            final_selected_move_is_legal = chess.Move.from_uci(final_selected_move) in board.legal_moves
        else:
            base = run_full_chess_live_level2_one_move_authorized_sender_kernel(
                memory_path=self.base_sender_memory_path,
                smoke_memory_path=self.smoke_memory_path,
                preflight_memory_path=self.preflight_memory_path,
                gate_memory_path=self.gate_memory_path,
                adapter_memory_path=self.adapter_memory_path,
                loop_memory_path=self.loop_memory_path,
                rerank_memory_path=self.rerank_memory_path,
                bias_memory_path=self.bias_memory_path,
                concept_memory_path=self.concept_memory_path,
                forecast_memory_path=self.forecast_memory_path,
                long_term_plan_memory_path=self.long_term_plan_memory_path,
                curriculum_memory_path=self.curriculum_memory_path,
                review_memory_path=self.review_memory_path,
                plan_memory_path=self.plan_memory_path,
                strategic_memory_path=self.strategic_memory_path,
                feature_memory_path=self.feature_memory_path,
                game_id=game_id,
                initial_fen=input_fen,
                side_to_evaluate=side_to_move,
                target_level=target_level,
                env_token_name=env_token_name,
                explicit_live_send_authorized=False,
                human_operator_confirmed=False,
                live_game_stream_confirmed=False,
                one_move_gate_enabled=False,
                live_sender_enabled=False,
                allow_real_post=False,
            )
            base_sender_consumed = True
            base_selected_move = base.selected_move
            final_selected_move = base.selected_move
            final_selected_move_is_legal = base.selected_move_is_legal

        send_allowed = all(
            [
                token_present,
                target_level == 2,
                final_selected_move_is_legal,
                explicit_live_send_authorized,
                human_operator_confirmed,
                live_game_stream_confirmed,
                one_move_gate_enabled,
                live_sender_enabled,
                allow_real_post,
            ]
        )

        move_post_attempted = False
        move_post_succeeded = False
        move_post_status_code: Optional[int] = None
        move_post_error: Optional[str] = None

        if send_allowed:
            move_post_attempted = True
            if post_move_callable is not None:
                move_post_succeeded, move_post_status_code, move_post_error = post_move_callable(
                    token,
                    game_id,
                    final_selected_move,
                )
            else:
                move_post_succeeded, move_post_status_code, move_post_error = self._post_lichess_move(
                    token=token,
                    game_id=game_id,
                    move_uci=final_selected_move,
                )

        trace_payload = {
            "game_id": game_id,
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "override_active": override_active,
            "base_selected_move": base_selected_move,
            "override_selected_move": queen.selected_move,
            "final_selected_move": final_selected_move,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "queen_trace_hash": queen.trace_hash,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["override_sender_run_count"] = int(self.policy.get("override_sender_run_count", 0)) + 1
        self.policy["queen_override_active_count"] = int(self.policy.get("queen_override_active_count", 0)) + (1 if override_active else 0)
        self.policy["send_attempt_count"] = int(self.policy.get("send_attempt_count", 0)) + (1 if move_post_attempted else 0)
        self.policy["send_success_count"] = int(self.policy.get("send_success_count", 0)) + (1 if move_post_succeeded else 0)
        self.policy["last_final_selected_move"] = final_selected_move
        self.policy["last_override_active"] = override_active
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "queen_endgame_override_live_sender_active": True,
            "queen_endgame_override_active": override_active,
            "base_sender_consumed": base_sender_consumed,
            "final_selected_move_is_legal": final_selected_move_is_legal,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "requires_token": True,
            "requires_explicit_live_send_authorization": True,
            "requires_human_operator_confirmation": True,
            "requires_live_game_stream_confirmation": True,
            "requires_one_move_gate_enabled": True,
            "requires_live_sender_enabled": True,
            "requires_allow_real_post": True,
            "repetition_penalty_available": True,
            "clock_pressure_available": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = QueenEndgameOverrideLiveSenderResult(
            kernel_version="phase22e21_full_chess_queen_endgame_override_live_sender_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            sender_mode="queen_endgame_override_live_sender",
            game_id=game_id,
            input_fen=input_fen,
            side_to_move=side_to_move,
            target_level=target_level,
            queen_endgame_override_active=override_active,
            base_sender_consumed=base_sender_consumed,
            base_selected_move=base_selected_move,
            override_selected_move=queen.selected_move,
            final_selected_move=final_selected_move,
            final_selected_move_is_legal=final_selected_move_is_legal,
            move_post_attempted=move_post_attempted,
            move_post_succeeded=move_post_succeeded,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_gate_enabled=one_move_gate_enabled,
            live_sender_enabled=live_sender_enabled,
            allow_real_post=allow_real_post,
            repeated_moves=repeated_moves,
            repeated_queen_squares=repeated_queen_squares,
            clock_pressure_active=queen.clock_pressure_active,
            override_trace_hash=queen.trace_hash,
            sender_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_override_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel integrates the Phase 22E.20 queen-endgame conversion override into the live sender path. "
                "It only sends a move when all explicit live authorization flags are true. It does not use Stockfish, "
                "LLM move judgement, or Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_queen_endgame_override_live_sender_kernel(
    *,
    game_id: str,
    input_fen: str,
    side_to_move: str = "white",
    target_level: int = 2,
    repeated_moves: Optional[List[str]] = None,
    repeated_queen_squares: Optional[List[str]] = None,
    recent_fens: Optional[List[str]] = None,
    clock_seconds_remaining: Optional[float] = None,
    env_token_name: str = "LICHESS_BOT_TOKEN",
    explicit_live_send_authorized: bool = False,
    human_operator_confirmed: bool = False,
    live_game_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = False,
    live_sender_enabled: bool = False,
    allow_real_post: bool = False,
    post_move_callable: Optional[Callable[[str, str, str], tuple[bool, Optional[int], Optional[str]]]] = None,
    memory_path: Optional[Path] = None,
    queen_memory_path: Optional[Path] = None,
    base_sender_memory_path: Optional[Path] = None,
    smoke_memory_path: Optional[Path] = None,
    preflight_memory_path: Optional[Path] = None,
    gate_memory_path: Optional[Path] = None,
    adapter_memory_path: Optional[Path] = None,
    loop_memory_path: Optional[Path] = None,
    rerank_memory_path: Optional[Path] = None,
    bias_memory_path: Optional[Path] = None,
    concept_memory_path: Optional[Path] = None,
    forecast_memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_queen_endgame_override_live_sender",
) -> QueenEndgameOverrideLiveSenderResult:
    return AionQueenEndgameOverrideLiveSenderKernel(
        memory_path=memory_path,
        queen_memory_path=queen_memory_path,
        base_sender_memory_path=base_sender_memory_path,
        smoke_memory_path=smoke_memory_path,
        preflight_memory_path=preflight_memory_path,
        gate_memory_path=gate_memory_path,
        adapter_memory_path=adapter_memory_path,
        loop_memory_path=loop_memory_path,
        rerank_memory_path=rerank_memory_path,
        bias_memory_path=bias_memory_path,
        concept_memory_path=concept_memory_path,
        forecast_memory_path=forecast_memory_path,
        long_term_plan_memory_path=long_term_plan_memory_path,
        curriculum_memory_path=curriculum_memory_path,
        review_memory_path=review_memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        game_id=game_id,
        input_fen=input_fen,
        side_to_move=side_to_move,
        target_level=target_level,
        repeated_moves=repeated_moves,
        repeated_queen_squares=repeated_queen_squares,
        recent_fens=recent_fens,
        clock_seconds_remaining=clock_seconds_remaining,
        env_token_name=env_token_name,
        explicit_live_send_authorized=explicit_live_send_authorized,
        human_operator_confirmed=human_operator_confirmed,
        live_game_stream_confirmed=live_game_stream_confirmed,
        one_move_gate_enabled=one_move_gate_enabled,
        live_sender_enabled=live_sender_enabled,
        allow_real_post=allow_real_post,
        post_move_callable=post_move_callable,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="QUEEN-ENDGAME-OVERRIDE-PREVIEW",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=["d6b8", "b8d6"],
        repeated_queen_squares=["b8", "d6"],
        clock_seconds_remaining=30,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Queen endgame override live sender memory saved to: {result.memory_path}")
