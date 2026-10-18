from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import chess

from .full_chess_one_move_live_smoke_test_gate_kernel import (
    run_full_chess_one_move_live_smoke_test_gate_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_live_level2_one_move_authorized_sender_memory.json")


@dataclass(frozen=True)
class LiveLevel2OneMoveAuthorizedSenderResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    sender_mode: str
    game_id: str
    initial_fen: str
    target_level: int
    selected_move: str
    selected_move_is_legal: bool
    smoke_gate_consumed: bool
    smoke_gate_trace_hash: str
    token_present: bool
    explicit_live_send_authorized: bool
    human_operator_confirmed: bool
    live_game_stream_confirmed: bool
    one_move_gate_enabled: bool
    one_move_gate_passed: bool
    live_sender_enabled: bool
    move_post_attempted: bool
    move_post_succeeded: bool
    move_post_status_code: Optional[int]
    move_post_error: Optional[str]
    send_blocked_reason: str
    sender_conditions: Dict[str, Any]
    sender_trace_hash: str
    policy_memory_mutated: bool
    final_sender_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLiveLevel2OneMoveAuthorizedSenderKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
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
            "authorized_sender_run_count": 0,
            "send_block_count": 0,
            "send_attempt_count": 0,
            "send_success_count": 0,
            "last_selected_move": None,
            "last_move_post_attempted": False,
            "last_move_post_succeeded": False,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_level2_one_move_authorized_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveLevel2OneMoveAuthorizedSenderResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e16_live_level2_one_move_authorized_sender_memory_v1",
            "task_name": result.task_name,
            "live_level2_one_move_authorized_sender_policy": result.final_sender_policy,
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
        game_id: str = "ONE-MOVE-AUTHORIZED-SENDER-PREVIEW",
        initial_fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        target_level: int = 2,
        env_token_name: str = "LICHESS_BOT_TOKEN",
        explicit_live_send_authorized: bool = False,
        human_operator_confirmed: bool = False,
        live_game_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = False,
        live_sender_enabled: bool = False,
        allow_real_post: bool = False,
        post_move_callable: Optional[Callable[[str, str, str], tuple[bool, Optional[int], Optional[str]]]] = None,
        task_name: str = "full_chess_live_level2_one_move_authorized_sender",
    ) -> LiveLevel2OneMoveAuthorizedSenderResult:
        token = os.environ.get(env_token_name, "").strip()
        token_present = bool(token)

        smoke = run_full_chess_one_move_live_smoke_test_gate_kernel(
            memory_path=self.smoke_memory_path,
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
            initial_fen=initial_fen,
            side_to_evaluate=side_to_evaluate,
            target_level=target_level,
            require_token_for_pass=True,
            env_token_name=env_token_name,
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_gate_enabled=one_move_gate_enabled,
        )

        selected_move = smoke.selected_move_preview
        selected_move_is_legal = chess.Move.from_uci(selected_move) in chess.Board(initial_fen).legal_moves

        conditions = {
            "target_level_is_2": target_level == 2,
            "token_present": token_present,
            "selected_move_is_legal": selected_move_is_legal,
            "smoke_gate_consumed": True,
            "explicit_live_send_authorized": explicit_live_send_authorized,
            "human_operator_confirmed": human_operator_confirmed,
            "live_game_stream_confirmed": live_game_stream_confirmed,
            "one_move_gate_enabled": one_move_gate_enabled,
            "live_sender_enabled": live_sender_enabled,
            "allow_real_post": allow_real_post,
            "one_move_limit": True,
        }

        send_allowed = all(
            [
                conditions["target_level_is_2"],
                conditions["token_present"],
                conditions["selected_move_is_legal"],
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
                move_post_succeeded, move_post_status_code, move_post_error = post_move_callable(token, game_id, selected_move)
            else:
                move_post_succeeded, move_post_status_code, move_post_error = self._post_lichess_move(
                    token=token,
                    game_id=game_id,
                    move_uci=selected_move,
                )
            send_blocked_reason = "Send allowed and one move POST attempted."
        else:
            missing = [key for key, value in conditions.items() if value is False]
            send_blocked_reason = "Send blocked by authorized sender conditions: " + ", ".join(missing)

        trace_payload = {
            "game_id": game_id,
            "initial_fen": initial_fen,
            "selected_move": selected_move,
            "conditions": conditions,
            "send_allowed": send_allowed,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "move_post_status_code": move_post_status_code,
            "smoke_gate_trace_hash": smoke.smoke_gate_trace_hash,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["authorized_sender_run_count"] = int(self.policy.get("authorized_sender_run_count", 0)) + 1
        self.policy["send_block_count"] = int(self.policy.get("send_block_count", 0)) + (0 if move_post_attempted else 1)
        self.policy["send_attempt_count"] = int(self.policy.get("send_attempt_count", 0)) + (1 if move_post_attempted else 0)
        self.policy["send_success_count"] = int(self.policy.get("send_success_count", 0)) + (1 if move_post_succeeded else 0)
        self.policy["last_selected_move"] = selected_move
        self.policy["last_move_post_attempted"] = move_post_attempted
        self.policy["last_move_post_succeeded"] = move_post_succeeded
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "live_level2_one_move_authorized_sender_active": True,
            "smoke_gate_consumed": True,
            "target_level_is_2": target_level == 2,
            "selected_move_is_legal": selected_move_is_legal,
            "requires_token": True,
            "requires_explicit_live_send_authorization": True,
            "requires_human_operator_confirmation": True,
            "requires_live_game_stream_confirmation": True,
            "requires_one_move_gate_enabled": True,
            "requires_live_sender_enabled": True,
            "requires_allow_real_post": True,
            "one_move_limit": True,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveLevel2OneMoveAuthorizedSenderResult(
            kernel_version="phase22e16_full_chess_live_level2_one_move_authorized_sender_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            sender_mode="live_level2_one_move_authorized_sender",
            game_id=game_id,
            initial_fen=initial_fen,
            target_level=target_level,
            selected_move=selected_move,
            selected_move_is_legal=selected_move_is_legal,
            smoke_gate_consumed=True,
            smoke_gate_trace_hash=smoke.smoke_gate_trace_hash,
            token_present=token_present,
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_gate_enabled=one_move_gate_enabled,
            one_move_gate_passed=smoke.one_move_gate_passed,
            live_sender_enabled=live_sender_enabled,
            move_post_attempted=move_post_attempted,
            move_post_succeeded=move_post_succeeded,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            send_blocked_reason=send_blocked_reason,
            sender_conditions=conditions,
            sender_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_sender_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel is the one-move authorized sender for a Level 2 live path. "
                "By default it does not POST. A real POST can occur only when token, explicit live authorization, "
                "human confirmation, live stream confirmation, one-move gate enablement, live sender enablement, "
                "and allow_real_post are all true."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_level2_one_move_authorized_sender_kernel(
    *,
    memory_path: Optional[Path] = None,
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
    game_id: str = "ONE-MOVE-AUTHORIZED-SENDER-PREVIEW",
    initial_fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    target_level: int = 2,
    env_token_name: str = "LICHESS_BOT_TOKEN",
    explicit_live_send_authorized: bool = False,
    human_operator_confirmed: bool = False,
    live_game_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = False,
    live_sender_enabled: bool = False,
    allow_real_post: bool = False,
    post_move_callable: Optional[Callable[[str, str, str], tuple[bool, Optional[int], Optional[str]]]] = None,
    task_name: str = "full_chess_live_level2_one_move_authorized_sender",
) -> LiveLevel2OneMoveAuthorizedSenderResult:
    return AionFullChessLiveLevel2OneMoveAuthorizedSenderKernel(
        memory_path=memory_path,
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
        initial_fen=initial_fen,
        side_to_evaluate=side_to_evaluate,
        target_level=target_level,
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
    result = run_full_chess_live_level2_one_move_authorized_sender_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live Level-2 one-move authorized sender memory saved to: {result.memory_path}")
