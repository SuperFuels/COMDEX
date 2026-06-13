"""AION Phase 22D.5 — Real Lichess Level 2 SQI Autoplay Runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple

import chess
import requests

from .full_chess_live_loop_sqi_selector_adapter_kernel import (
    run_full_chess_live_loop_sqi_selector_adapter_kernel,
)


DEFAULT_REAL_LEVEL2_SQI_RUNNER_MEMORY_PATH = Path(
    "data/aion_games/full_chess_real_lichess_level2_sqi_autoplay_runner_memory.json"
)


@dataclass(frozen=True)
class RealLichessLevel2SQIAutoplayRunnerResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    runner_mode: str
    platform: str
    account_id: str
    opponent_type: str
    opponent_level: int
    rated: bool
    variant: str
    aion_colour: str
    dry_run: bool
    network_enabled: bool
    live_env_enabled: bool
    token_required_for_live: bool
    token_present: bool
    live_authorised: bool
    challenge_endpoint: str
    challenge_payload: Dict[str, Any]
    challenge_attempted: bool
    challenge_created: bool
    game_id: str
    full_id: str
    selected_opening_move: str
    selected_opening_move_source: str
    selected_opening_move_is_legal: bool
    selected_classical_score: float
    selected_sqi_adjusted_score: float
    selected_collapse_weight: float
    selected_sqi_reason: str
    sqi_trace_hash: str
    selection_trace_hash: str
    adapter_trace_hash: str
    runner_trace_hash: str
    move_send_attempted: bool
    move_send_response_ok: bool
    final_status: str
    final_winner: str
    result_recorded: bool
    policy_memory_mutated: bool
    final_runner_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessRealLichessLevel2SQIAutoplayRunnerKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        sqi_live_adapter_memory_path: Optional[Path] = None,
        sqi_selector_memory_path: Optional[Path] = None,
        sqi_bridge_memory_path: Optional[Path] = None,
        selector_memory_path: Optional[Path] = None,
        evaluation_memory_path: Optional[Path] = None,
        post_game_memory_path: Optional[Path] = None,
    ):
        self.memory_path = Path(memory_path or DEFAULT_REAL_LEVEL2_SQI_RUNNER_MEMORY_PATH)
        self.sqi_live_adapter_memory_path = sqi_live_adapter_memory_path
        self.sqi_selector_memory_path = sqi_selector_memory_path
        self.sqi_bridge_memory_path = sqi_bridge_memory_path
        self.selector_memory_path = selector_memory_path
        self.evaluation_memory_path = evaluation_memory_path
        self.post_game_memory_path = post_game_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "dry_run_count": 0,
            "live_authorised_count": 0,
            "challenge_attempt_count": 0,
            "challenge_created_count": 0,
            "move_send_attempt_count": 0,
            "move_send_ok_count": 0,
            "result_record_count": 0,
            "last_game_id": None,
            "last_full_id": None,
            "last_selected_opening_move": None,
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
        policy = data.get("real_lichess_level2_sqi_runner_policy") if isinstance(data, dict) else None
        if isinstance(policy, dict):
            self.policy.update(policy)
            self.memory_loaded = True

    def _save_memory(self, result: RealLichessLevel2SQIAutoplayRunnerResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22d5_real_lichess_level2_sqi_autoplay_runner_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "real_lichess_level2_sqi_runner_policy": result.final_runner_policy,
            "game_id": result.game_id,
            "full_id": result.full_id,
            "selected_opening_move": result.selected_opening_move,
            "selected_sqi_adjusted_score": result.selected_sqi_adjusted_score,
            "runner_trace_hash": result.runner_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _headers(self, token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _create_level2_challenge(
        self,
        *,
        token: str,
        endpoint: str,
        payload: Dict[str, Any],
        timeout_seconds: int,
    ) -> Tuple[bool, str, str]:
        response = requests.post(
            endpoint,
            headers=self._headers(token),
            data=payload,
            timeout=timeout_seconds,
        )

        try:
            response_payload = response.json()
        except Exception:
            response_payload = {}

        if not response.ok:
            return False, "", ""

        game_id = str(response_payload.get("id") or response_payload.get("game", {}).get("id") or "")
        full_id = str(response_payload.get("fullId") or response_payload.get("game", {}).get("fullId") or "")
        return True, game_id, full_id

    def _send_move(self, *, token: str, game_id: str, move: str, timeout_seconds: int) -> bool:
        endpoint = f"https://lichess.org/api/bot/game/{game_id}/move/{move}"
        response = requests.post(endpoint, headers=self._headers(token), timeout=timeout_seconds)
        return bool(response.ok)

    def run(
        self,
        *,
        task_name: str = "full_chess_real_lichess_level2_sqi_autoplay_runner",
        account_id: str = "peekoo123",
        aion_colour: str = "white",
        opponent_level: int = 2,
        rated: bool = False,
        variant: str = "standard",
        clock_limit_seconds: int = 600,
        clock_increment_seconds: int = 0,
        dry_run: bool = True,
        network_enabled: bool = False,
        token_value: Optional[str] = None,
        timeout_seconds: int = 20,
        send_opening_move: bool = False,
    ) -> RealLichessLevel2SQIAutoplayRunnerResult:
        token = token_value or os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token)
        live_env_enabled = os.environ.get("AION_LICHESS_LIVE", "") == "1"

        live_authorised = bool(
            not dry_run
            and network_enabled
            and token_present
            and live_env_enabled
            and opponent_level == 2
        )

        board = chess.Board()

        adapter = run_full_chess_live_loop_sqi_selector_adapter_kernel(
            memory_path=self.sqi_live_adapter_memory_path,
            sqi_selector_memory_path=self.sqi_selector_memory_path,
            sqi_bridge_memory_path=self.sqi_bridge_memory_path,
            selector_memory_path=self.selector_memory_path,
            evaluation_memory_path=self.evaluation_memory_path,
            post_game_memory_path=self.post_game_memory_path,
            game_id="real_lichess_level2_sqi_autoplay_runner",
            aion_colour=aion_colour,
            moves=[],
            dry_run=True,
            network_send_allowed=False,
        )

        legal_moves = {move.uci() for move in board.legal_moves}
        selected_move_is_legal = adapter.selected_move in legal_moves if adapter.selected_move else False

        challenge_endpoint = "https://lichess.org/api/challenge/ai"
        challenge_payload = {
            "level": opponent_level,
            "rated": rated,
            "variant": variant,
            "clock.limit": clock_limit_seconds,
            "clock.increment": clock_increment_seconds,
            "color": aion_colour,
        }

        challenge_attempted = False
        challenge_created = False
        move_send_attempted = False
        move_send_response_ok = False
        game_id = ""
        full_id = ""
        final_status = "not_started"
        final_winner = ""
        result_recorded = False

        if live_authorised:
            challenge_attempted = True
            challenge_created, game_id, full_id = self._create_level2_challenge(
                token=token,
                endpoint=challenge_endpoint,
                payload=challenge_payload,
                timeout_seconds=timeout_seconds,
            )

            if challenge_created:
                final_status = "challenge_created"

                if send_opening_move and adapter.selected_move and selected_move_is_legal:
                    time.sleep(1.0)
                    move_send_attempted = True
                    move_send_response_ok = self._send_move(
                        token=token,
                        game_id=game_id,
                        move=adapter.selected_move,
                        timeout_seconds=timeout_seconds,
                    )
                    final_status = "opening_move_sent" if move_send_response_ok else "opening_move_send_failed"
                    result_recorded = bool(move_send_response_ok)
            else:
                final_status = "challenge_failed"

        trace_payload = {
            "runner_mode": "real_lichess_level2_sqi_autoplay_runner",
            "account_id": account_id,
            "opponent_level": opponent_level,
            "dry_run": dry_run,
            "network_enabled": network_enabled,
            "live_env_enabled": live_env_enabled,
            "token_present": token_present,
            "live_authorised": live_authorised,
            "selected_opening_move": adapter.selected_move,
            "selected_sqi_adjusted_score": adapter.selected_sqi_adjusted_score,
            "sqi_trace_hash": adapter.sqi_trace_hash,
            "selection_trace_hash": adapter.selection_trace_hash,
            "adapter_trace_hash": adapter.adapter_trace_hash,
            "challenge_attempted": challenge_attempted,
            "challenge_created": challenge_created,
            "game_id": game_id,
            "move_send_attempted": move_send_attempted,
            "move_send_response_ok": move_send_response_ok,
            "final_status": final_status,
            "uses_llm_shortcut": False,
            "uses_stockfish_local_engine": False,
            "uses_cloud_engine": False,
        }
        runner_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + (1 if dry_run else 0)
        self.policy["live_authorised_count"] = int(self.policy.get("live_authorised_count", 0)) + (1 if live_authorised else 0)
        self.policy["challenge_attempt_count"] = int(self.policy.get("challenge_attempt_count", 0)) + (1 if challenge_attempted else 0)
        self.policy["challenge_created_count"] = int(self.policy.get("challenge_created_count", 0)) + (1 if challenge_created else 0)
        self.policy["move_send_attempt_count"] = int(self.policy.get("move_send_attempt_count", 0)) + (1 if move_send_attempted else 0)
        self.policy["move_send_ok_count"] = int(self.policy.get("move_send_ok_count", 0)) + (1 if move_send_response_ok else 0)
        self.policy["result_record_count"] = int(self.policy.get("result_record_count", 0)) + (1 if result_recorded else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_full_id"] = full_id
        self.policy["last_selected_opening_move"] = adapter.selected_move
        self.policy["last_selected_sqi_adjusted_score"] = adapter.selected_sqi_adjusted_score
        self.policy["last_trace_hash"] = runner_trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_stockfish_local_engine": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "target_is_stockfish_level_2": opponent_level == 2,
            "sqi_live_loop_adapter_used": True,
            "sqi_guided_selector_used": adapter.sqi_guided_selector_used,
            "selected_opening_move_is_legal": selected_move_is_legal,
            "selected_by_sqi_adjusted_score": adapter.selected_sqi_adjusted_score != 0,
            "dry_run_default": dry_run is True,
            "network_enabled": network_enabled,
            "live_env_enabled": live_env_enabled,
            "token_required_for_live": True,
            "token_present": token_present,
            "live_authorised": live_authorised,
            "challenge_attempted": challenge_attempted,
            "challenge_created": challenge_created,
            "move_send_attempted": move_send_attempted,
            "move_send_response_ok": move_send_response_ok,
            "no_payment_created": True,
            "no_booking_created": True,
            "no_chain_write": True,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = RealLichessLevel2SQIAutoplayRunnerResult(
            kernel_version="phase22d5_real_lichess_level2_sqi_autoplay_runner_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            runner_mode="real_lichess_level2_sqi_autoplay_runner",
            platform="lichess",
            account_id=account_id,
            opponent_type="lichess_ai_stockfish",
            opponent_level=opponent_level,
            rated=rated,
            variant=variant,
            aion_colour=aion_colour,
            dry_run=dry_run,
            network_enabled=network_enabled,
            live_env_enabled=live_env_enabled,
            token_required_for_live=True,
            token_present=token_present,
            live_authorised=live_authorised,
            challenge_endpoint=challenge_endpoint,
            challenge_payload=challenge_payload,
            challenge_attempted=challenge_attempted,
            challenge_created=challenge_created,
            game_id=game_id,
            full_id=full_id,
            selected_opening_move=adapter.selected_move,
            selected_opening_move_source=adapter.live_loop_move_source,
            selected_opening_move_is_legal=selected_move_is_legal,
            selected_classical_score=adapter.selected_classical_score,
            selected_sqi_adjusted_score=adapter.selected_sqi_adjusted_score,
            selected_collapse_weight=adapter.selected_collapse_weight,
            selected_sqi_reason=adapter.selected_sqi_reason,
            sqi_trace_hash=adapter.sqi_trace_hash,
            selection_trace_hash=adapter.selection_trace_hash,
            adapter_trace_hash=adapter.adapter_trace_hash,
            runner_trace_hash=runner_trace_hash,
            move_send_attempted=move_send_attempted,
            move_send_response_ok=move_send_response_ok,
            final_status=final_status,
            final_winner=final_winner,
            result_recorded=result_recorded,
            policy_memory_mutated=True,
            final_runner_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel is the real Lichess level 2 SQI autoplay runner. "
                "It can create a live Lichess level 2 game only when dry_run is false, "
                "network is enabled, AION_LICHESS_LIVE=1, and a token is present. "
                "Tests remain dry-run."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
    *,
    memory_path: Optional[Path] = None,
    sqi_live_adapter_memory_path: Optional[Path] = None,
    sqi_selector_memory_path: Optional[Path] = None,
    sqi_bridge_memory_path: Optional[Path] = None,
    selector_memory_path: Optional[Path] = None,
    evaluation_memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_real_lichess_level2_sqi_autoplay_runner",
    account_id: str = "peekoo123",
    aion_colour: str = "white",
    opponent_level: int = 2,
    rated: bool = False,
    variant: str = "standard",
    clock_limit_seconds: int = 600,
    clock_increment_seconds: int = 0,
    dry_run: bool = True,
    network_enabled: bool = False,
    token_value: Optional[str] = None,
    timeout_seconds: int = 20,
    send_opening_move: bool = False,
) -> RealLichessLevel2SQIAutoplayRunnerResult:
    return AionFullChessRealLichessLevel2SQIAutoplayRunnerKernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=sqi_live_adapter_memory_path,
        sqi_selector_memory_path=sqi_selector_memory_path,
        sqi_bridge_memory_path=sqi_bridge_memory_path,
        selector_memory_path=selector_memory_path,
        evaluation_memory_path=evaluation_memory_path,
        post_game_memory_path=post_game_memory_path,
    ).run(
        task_name=task_name,
        account_id=account_id,
        aion_colour=aion_colour,
        opponent_level=opponent_level,
        rated=rated,
        variant=variant,
        clock_limit_seconds=clock_limit_seconds,
        clock_increment_seconds=clock_increment_seconds,
        dry_run=dry_run,
        network_enabled=network_enabled,
        token_value=token_value,
        timeout_seconds=timeout_seconds,
        send_opening_move=send_opening_move,
    )


if __name__ == "__main__":
    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Real Lichess level 2 SQI autoplay runner memory saved to: {result.memory_path}")
