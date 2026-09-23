"""AION Phase 22D.6 — Full Real Lichess Level 2 SQI Game Loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Optional

import chess
import requests

from .full_chess_live_loop_sqi_selector_adapter_kernel import (
    run_full_chess_live_loop_sqi_selector_adapter_kernel,
)


DEFAULT_REAL_LEVEL2_SQI_GAME_LOOP_MEMORY_PATH = Path(
    "data/aion_games/full_chess_real_lichess_level2_sqi_game_loop_memory.json"
)


@dataclass(frozen=True)
class RealLichessLevel2SQIGameLoopResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    loop_mode: str
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
    token_present: bool
    live_authorised: bool
    challenge_attempted: bool
    challenge_created: bool
    game_id: str
    full_id: str
    stream_attempted: bool
    move_send_attempt_count: int
    move_send_ok_count: int
    aion_move_count: int
    opponent_move_count: int
    final_status: str
    final_winner: str
    final_moves: List[str]
    last_selected_move: str
    last_selected_sqi_adjusted_score: float
    last_sqi_trace_hash: str
    last_selection_trace_hash: str
    loop_trace_hash: str
    result_recorded: bool
    policy_memory_mutated: bool
    final_loop_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessRealLichessLevel2SQIGameLoopKernel:
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
        self.memory_path = Path(memory_path or DEFAULT_REAL_LEVEL2_SQI_GAME_LOOP_MEMORY_PATH)
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
            "challenge_created_count": 0,
            "stream_attempt_count": 0,
            "move_send_attempt_total": 0,
            "move_send_ok_total": 0,
            "result_record_count": 0,
            "last_game_id": None,
            "last_final_status": None,
            "last_final_winner": None,
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
        policy = data.get("real_lichess_level2_sqi_game_loop_policy") if isinstance(data, dict) else None
        if isinstance(policy, dict):
            self.policy.update(policy)
            self.memory_loaded = True

    def _save_memory(self, result: RealLichessLevel2SQIGameLoopResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22d6_real_lichess_level2_sqi_game_loop_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "real_lichess_level2_sqi_game_loop_policy": result.final_loop_policy,
            "game_id": result.game_id,
            "full_id": result.full_id,
            "final_status": result.final_status,
            "final_winner": result.final_winner,
            "final_moves": result.final_moves,
            "loop_trace_hash": result.loop_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/x-ndjson,application/json",
        }

    def _create_challenge(self, *, token: str, payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
        response = requests.post(
            "https://lichess.org/api/challenge/ai",
            headers=self._headers(token),
            data=payload,
            timeout=timeout_seconds,
        )
        try:
            body = response.json()
        except Exception:
            body = {"raw_text": response.text}
        return {"ok": bool(response.ok), "body": body}

    def _send_move(self, *, token: str, game_id: str, move: str, timeout_seconds: int) -> bool:
        response = requests.post(
            f"https://lichess.org/api/bot/game/{game_id}/move/{move}",
            headers=self._headers(token),
            timeout=timeout_seconds,
        )
        return bool(response.ok)

    def _stream_game_events(self, *, token: str, game_id: str, timeout_seconds: int) -> Iterable[Dict[str, Any]]:
        response = requests.get(
            f"https://lichess.org/api/bot/game/stream/{game_id}",
            headers=self._headers(token),
            stream=True,
            timeout=timeout_seconds,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            try:
                yield json.loads(line.decode("utf-8"))
            except Exception:
                continue

    def _moves_from_event(self, event: Dict[str, Any], previous: List[str]) -> List[str]:
        if event.get("type") == "gameFull":
            state = event.get("state") or {}
            raw = str(state.get("moves") or "")
            return raw.split() if raw else []

        if event.get("type") == "gameState":
            raw = str(event.get("moves") or "")
            return raw.split() if raw else previous

        return previous

    def _status_from_event(self, event: Dict[str, Any], current: str) -> str:
        if event.get("type") == "gameFull":
            state = event.get("state") or {}
            return str(state.get("status") or current)
        if event.get("type") == "gameState":
            return str(event.get("status") or current)
        return current

    def _winner_from_event(self, event: Dict[str, Any], current: str) -> str:
        if event.get("type") == "gameFull":
            state = event.get("state") or {}
            return str(state.get("winner") or current)
        if event.get("type") == "gameState":
            return str(event.get("winner") or current)
        return current

    def _is_aion_turn_from_moves(self, moves: List[str], aion_colour: str) -> bool:
        white_to_move = len(moves) % 2 == 0
        return (aion_colour == "white" and white_to_move) or (aion_colour == "black" and not white_to_move)

    def run(
        self,
        *,
        task_name: str = "full_chess_real_lichess_level2_sqi_game_loop",
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
        timeout_seconds: int = 30,
        max_aion_moves: int = 80,
        max_events: int = 300,
    ) -> RealLichessLevel2SQIGameLoopResult:
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
        stream_attempted = False
        game_id = ""
        full_id = ""
        moves: List[str] = []
        move_send_attempt_count = 0
        move_send_ok_count = 0
        aion_move_count = 0
        final_status = "not_started"
        final_winner = ""
        last_selected_move = ""
        last_selected_sqi_adjusted_score = 0.0
        last_sqi_trace_hash = ""
        last_selection_trace_hash = ""
        result_recorded = False

        if live_authorised:
            challenge_attempted = True
            challenge = self._create_challenge(
                token=token,
                payload=challenge_payload,
                timeout_seconds=timeout_seconds,
            )

            challenge_created = bool(challenge["ok"])
            body = challenge["body"]
            game_id = str(body.get("id") or body.get("game", {}).get("id") or "")
            full_id = str(body.get("fullId") or body.get("game", {}).get("fullId") or "")

            if challenge_created and game_id:
                final_status = "started"
                stream_attempted = True

                for index, event in enumerate(self._stream_game_events(token=token, game_id=game_id, timeout_seconds=timeout_seconds)):
                    if index >= max_events:
                        final_status = "event_limit_reached"
                        break

                    moves = self._moves_from_event(event, moves)
                    final_status = self._status_from_event(event, final_status)
                    final_winner = self._winner_from_event(event, final_winner)

                    if final_status not in {"started", "created"}:
                        result_recorded = True
                        break

                    if aion_move_count >= max_aion_moves:
                        final_status = "aion_move_limit_reached"
                        break

                    if not self._is_aion_turn_from_moves(moves, aion_colour):
                        continue

                    adapter = run_full_chess_live_loop_sqi_selector_adapter_kernel(
                        memory_path=self.sqi_live_adapter_memory_path,
                        sqi_selector_memory_path=self.sqi_selector_memory_path,
                        sqi_bridge_memory_path=self.sqi_bridge_memory_path,
                        selector_memory_path=self.selector_memory_path,
                        evaluation_memory_path=self.evaluation_memory_path,
                        post_game_memory_path=self.post_game_memory_path,
                        game_id=game_id,
                        aion_colour=aion_colour,
                        moves=moves,
                        dry_run=True,
                        network_send_allowed=False,
                    )

                    if not adapter.selected_move or not adapter.selected_move_is_legal:
                        final_status = "no_legal_sqi_move"
                        break

                    last_selected_move = adapter.selected_move
                    last_selected_sqi_adjusted_score = adapter.selected_sqi_adjusted_score
                    last_sqi_trace_hash = adapter.sqi_trace_hash
                    last_selection_trace_hash = adapter.selection_trace_hash

                    move_send_attempt_count += 1
                    ok = self._send_move(
                        token=token,
                        game_id=game_id,
                        move=adapter.selected_move,
                        timeout_seconds=timeout_seconds,
                    )
                    if ok:
                        move_send_ok_count += 1
                        aion_move_count += 1
                        moves.append(adapter.selected_move)
                    else:
                        final_status = "move_send_failed"
                        break

                    time.sleep(0.5)

            elif challenge_attempted:
                final_status = "challenge_failed"

        else:
            adapter = run_full_chess_live_loop_sqi_selector_adapter_kernel(
                memory_path=self.sqi_live_adapter_memory_path,
                sqi_selector_memory_path=self.sqi_selector_memory_path,
                sqi_bridge_memory_path=self.sqi_bridge_memory_path,
                selector_memory_path=self.selector_memory_path,
                evaluation_memory_path=self.evaluation_memory_path,
                post_game_memory_path=self.post_game_memory_path,
                game_id="dry_run_real_lichess_level2_sqi_game_loop",
                aion_colour=aion_colour,
                moves=[],
                dry_run=True,
                network_send_allowed=False,
            )
            last_selected_move = adapter.selected_move
            last_selected_sqi_adjusted_score = adapter.selected_sqi_adjusted_score
            last_sqi_trace_hash = adapter.sqi_trace_hash
            last_selection_trace_hash = adapter.selection_trace_hash

        opponent_move_count = max(0, len(moves) - aion_move_count)

        trace_payload = {
            "loop_mode": "real_lichess_level2_sqi_game_loop",
            "opponent_level": opponent_level,
            "dry_run": dry_run,
            "network_enabled": network_enabled,
            "live_env_enabled": live_env_enabled,
            "token_present": token_present,
            "live_authorised": live_authorised,
            "challenge_attempted": challenge_attempted,
            "challenge_created": challenge_created,
            "stream_attempted": stream_attempted,
            "game_id": game_id,
            "move_send_attempt_count": move_send_attempt_count,
            "move_send_ok_count": move_send_ok_count,
            "aion_move_count": aion_move_count,
            "opponent_move_count": opponent_move_count,
            "final_status": final_status,
            "final_winner": final_winner,
            "final_moves": moves,
            "last_selected_move": last_selected_move,
            "last_selected_sqi_adjusted_score": last_selected_sqi_adjusted_score,
        }
        loop_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + (1 if dry_run else 0)
        self.policy["live_authorised_count"] = int(self.policy.get("live_authorised_count", 0)) + (1 if live_authorised else 0)
        self.policy["challenge_created_count"] = int(self.policy.get("challenge_created_count", 0)) + (1 if challenge_created else 0)
        self.policy["stream_attempt_count"] = int(self.policy.get("stream_attempt_count", 0)) + (1 if stream_attempted else 0)
        self.policy["move_send_attempt_total"] = int(self.policy.get("move_send_attempt_total", 0)) + move_send_attempt_count
        self.policy["move_send_ok_total"] = int(self.policy.get("move_send_ok_total", 0)) + move_send_ok_count
        self.policy["result_record_count"] = int(self.policy.get("result_record_count", 0)) + (1 if result_recorded else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_final_status"] = final_status
        self.policy["last_final_winner"] = final_winner
        self.policy["last_trace_hash"] = loop_trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_stockfish_local_engine": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "target_is_stockfish_level_2": opponent_level == 2,
            "sqi_live_loop_adapter_used": True,
            "sqi_guided_selector_used": True,
            "dry_run_default": dry_run is True,
            "network_enabled": network_enabled,
            "live_env_enabled": live_env_enabled,
            "token_present": token_present,
            "live_authorised": live_authorised,
            "challenge_attempted": challenge_attempted,
            "challenge_created": challenge_created,
            "stream_attempted": stream_attempted,
            "moves_sent_only_when_live_authorised": (not move_send_attempt_count) or live_authorised,
            "move_send_ok_count": move_send_ok_count,
            "no_payment_created": True,
            "no_booking_created": True,
            "no_chain_write": True,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = RealLichessLevel2SQIGameLoopResult(
            kernel_version="phase22d6_real_lichess_level2_sqi_game_loop_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            loop_mode="real_lichess_level2_sqi_game_loop",
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
            token_present=token_present,
            live_authorised=live_authorised,
            challenge_attempted=challenge_attempted,
            challenge_created=challenge_created,
            game_id=game_id,
            full_id=full_id,
            stream_attempted=stream_attempted,
            move_send_attempt_count=move_send_attempt_count,
            move_send_ok_count=move_send_ok_count,
            aion_move_count=aion_move_count,
            opponent_move_count=opponent_move_count,
            final_status=final_status,
            final_winner=final_winner,
            final_moves=moves,
            last_selected_move=last_selected_move,
            last_selected_sqi_adjusted_score=last_selected_sqi_adjusted_score,
            last_sqi_trace_hash=last_sqi_trace_hash,
            last_selection_trace_hash=last_selection_trace_hash,
            loop_trace_hash=loop_trace_hash,
            result_recorded=result_recorded,
            policy_memory_mutated=True,
            final_loop_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel plays a full real Lichess level 2 game loop using the SQI-guided selector only when "
                "dry_run is false, network is enabled, AION_LICHESS_LIVE=1, and a token is present. Tests remain dry-run."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_real_lichess_level2_sqi_game_loop_kernel(**kwargs: Any) -> RealLichessLevel2SQIGameLoopResult:
    return AionFullChessRealLichessLevel2SQIGameLoopKernel(
        memory_path=kwargs.pop("memory_path", None),
        sqi_live_adapter_memory_path=kwargs.pop("sqi_live_adapter_memory_path", None),
        sqi_selector_memory_path=kwargs.pop("sqi_selector_memory_path", None),
        sqi_bridge_memory_path=kwargs.pop("sqi_bridge_memory_path", None),
        selector_memory_path=kwargs.pop("selector_memory_path", None),
        evaluation_memory_path=kwargs.pop("evaluation_memory_path", None),
        post_game_memory_path=kwargs.pop("post_game_memory_path", None),
    ).run(**kwargs)


if __name__ == "__main__":
    result = run_full_chess_real_lichess_level2_sqi_game_loop_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full real Lichess level 2 SQI game loop memory saved to: {result.memory_path}")
