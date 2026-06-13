from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    run_full_chess_live_one_move_strategic_well_sender_kernel,
)
from backend.modules.aion_games.full_chess_level2_live_rematch_runner_with_recovery_kernel import (
    run_full_chess_level2_live_rematch_runner_with_recovery_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_strategic_well_live_rematch_memory.json")


@dataclass(frozen=True)
class StrategicWellLiveRematchResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    dry_run: bool
    network_enabled: bool
    live_env_enabled: bool
    token_present: bool
    challenge_attempted: bool
    challenge_created: bool
    game_id: str
    full_id: str
    aion_colour: str
    target_level: int
    final_status: str
    final_winner: str
    final_moves: List[str]
    final_ply_count: int
    aion_move_count: int
    move_send_ok_count: int
    post_400_recovery_count: int
    strategic_sender_used_count: int
    first_selected_move: str
    first_base_well_move: str
    first_intent_override_applied: bool
    move_records: List[Dict[str, Any]]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionStrategicWellLiveRematchKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "dry_run_count": 0,
            "live_run_count": 0,
            "challenge_created_count": 0,
            "move_send_ok_total": 0,
            "post_400_recovery_total": 0,
            "last_game_id": "",
            "last_final_status": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_well_live_rematch_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicWellLiveRematchResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e39_strategic_well_live_rematch_memory_v1",
            "task_name": result.task_name,
            "strategic_well_live_rematch_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _board_from_moves(self, moves: List[str]) -> chess.Board:
        board = chess.Board()
        for uci in moves:
            board.push(chess.Move.from_uci(uci))
        return board

    def _fetch_latest_game_state(self, *, token: str, game_id: str) -> Dict[str, Any]:
        req = urllib.request.Request(
            f"https://lichess.org/api/bot/game/stream/{game_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/x-ndjson",
            },
            method="GET",
        )
        latest: Dict[str, Any] = {}
        with urllib.request.urlopen(req, timeout=15) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("type") == "gameFull":
                    latest = event.get("state", {}) or {}
                elif event.get("type") == "gameState":
                    latest = event
                if latest:
                    break
        return latest

    def _create_ai_challenge(self, *, token: str, level: int, clock_limit: int, clock_increment: int) -> Dict[str, Any]:
        req = urllib.request.Request(
            "https://lichess.org/api/challenge/ai",
            data=f"level={level}&clock.limit={clock_limit}&clock.increment={clock_increment}&color=white".encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def run(
        self,
        *,
        dry_run: bool = True,
        network_enabled: bool = False,
        target_level: int = 2,
        clock_limit_seconds: int = 300,
        clock_increment_seconds: int = 1,
        max_aion_moves: int = 120,
        token: Optional[str] = None,
        task_name: str = "full_chess_level2_strategic_well_live_rematch",
    ) -> StrategicWellLiveRematchResult:
        token_value = token or os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token_value)
        live_env_enabled = os.environ.get("AION_LICHESS_LIVE", "") == "1"

        challenge_attempted = False
        challenge_created = False
        game_id = ""
        full_id = ""
        aion_colour = "white"
        final_status = "not_started"
        final_winner = ""
        final_moves: List[str] = []
        move_records: List[Dict[str, Any]] = []
        aion_move_count = 0
        move_send_ok_count = 0
        post_400_recovery_count = 0
        strategic_sender_used_count = 0

        if dry_run or not network_enabled:
            sender = run_full_chess_live_one_move_strategic_well_sender_kernel(
                game_id="dry_run_game",
                input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
                side_to_move="white",
                target_level=target_level,
                repeated_moves=["d2d4", "d7d5"],
                repeated_squares=["d4", "d5"],
                memory_path=self.memory_path.parent / "phase22e39_child_sender_memory.json",
            )
            move_records.append(asdict(sender))
            strategic_sender_used_count = 1
            final_status = "dry_run_ready"

        else:
            if not (live_env_enabled and token_present):
                raise RuntimeError("Live rematch requires AION_LICHESS_LIVE=1 and LICHESS_BOT_TOKEN.")

            challenge_attempted = True
            challenge = self._create_ai_challenge(
                token=token_value,
                level=target_level,
                clock_limit=clock_limit_seconds,
                clock_increment=clock_increment_seconds,
            )
            challenge_created = True
            game_id = challenge["id"]
            full_id = challenge.get("fullId") or ""
            aion_colour = challenge.get("player", "white")

            if aion_colour != "white":
                raise RuntimeError(f"Expected AION as white, got {aion_colour}")

            stream_req = urllib.request.Request(
                f"https://lichess.org/api/bot/game/stream/{game_id}",
                headers={
                    "Authorization": f"Bearer {token_value}",
                    "Accept": "application/x-ndjson",
                },
                method="GET",
            )

            with urllib.request.urlopen(stream_req, timeout=900) as stream:
                for raw_line in stream:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue

                    event = json.loads(line)
                    event_type = event.get("type")
                    if event_type == "gameFull":
                        state = event.get("state", {}) or {}
                    elif event_type == "gameState":
                        state = event
                    else:
                        continue

                    moves_text = state.get("moves", "")
                    moves = moves_text.split() if moves_text else []
                    final_moves = moves
                    final_status = state.get("status") or ""
                    final_winner = state.get("winner") or ""

                    print("state:", {
                        "status": final_status,
                        "winner": final_winner,
                        "plies": len(moves),
                        "aion_moves": aion_move_count,
                        "send_ok": move_send_ok_count,
                        "post_400_recoveries": post_400_recovery_count,
                    }, flush=True)

                    if final_status and final_status != "started":
                        break

                    if aion_move_count >= max_aion_moves:
                        break

                    if len(moves) % 2 != 0:
                        continue

                    board = self._board_from_moves(moves)
                    current_fen = board.fen()

                    sender = run_full_chess_live_one_move_strategic_well_sender_kernel(
                        game_id=game_id,
                        input_fen=current_fen,
                        side_to_move=aion_colour,
                        target_level=target_level,
                        repeated_moves=moves[-16:],
                        repeated_squares=[m[2:4] for m in moves[-16:] if len(m) >= 4],
                        explicit_live_send_authorized=True,
                        human_operator_confirmed=True,
                        live_game_stream_confirmed=True,
                        one_move_gate_enabled=True,
                        live_sender_enabled=True,
                        allow_real_post=True,
                        token=token_value,
                        memory_path=self.memory_path.parent / "phase22e39_child_sender_memory.json",
                    )

                    strategic_sender_used_count += 1

                    sender_record = {
                        "aion_move_index": aion_move_count + 1,
                        "ply_before": len(moves),
                        "fen_before": current_fen,
                        "final_selected_move": sender.selected_move,
                        "selected_move": sender.selected_move,
                        "selected_move_is_legal": sender.selected_move_is_legal,
                        "active_intent": sender.active_intent,
                        "base_well_selected_move": sender.base_well_selected_move,
                        "intent_override_applied": sender.intent_override_applied,
                        "selected_source": sender.selected_source,
                        "move_post_attempted": sender.move_post_attempted,
                        "move_post_succeeded": sender.move_post_succeeded,
                        "move_post_status_code": sender.move_post_status_code,
                        "move_post_error": sender.move_post_error,
                        "sender_trace_hash": sender.trace_hash,
                    }

                    latest_state_after_failure = None
                    if sender.move_post_attempted and not sender.move_post_succeeded and sender.move_post_status_code == 400:
                        try:
                            latest_state_after_failure = self._fetch_latest_game_state(token=token_value, game_id=game_id)
                        except Exception as exc:
                            latest_state_after_failure = {
                                "status": "unknown",
                                "moves": " ".join(moves),
                                "fetch_error": str(exc),
                            }

                    runner = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
                        game_id=game_id,
                        full_id=full_id,
                        aion_colour=aion_colour,
                        target_level=target_level,
                        fen_before=current_fen,
                        expected_moves_before=moves,
                        sender_record=sender_record,
                        latest_state_after_failure=latest_state_after_failure,
                        token=token_value,
                    )

                    record = {
                        **sender_record,
                        "runner_continue_live_loop": runner.continue_live_loop,
                        "runner_abort_live_loop": runner.abort_live_loop,
                        "runner_recovery_invoked": runner.recovery_invoked,
                        "runner_recovery_classification": runner.recovery_classification,
                        "runner_recovered_as_nonfatal": runner.recovered_as_nonfatal,
                        "runner_refresh_required": runner.refresh_required,
                        "runner_next_loop_ply_count": runner.next_loop_ply_count,
                        "runner_trace_hash": runner.trace_hash,
                    }

                    print("AION 22E.39 move:", record, flush=True)

                    if runner.abort_live_loop:
                        raise RuntimeError("22E.39 hard abort from recovery runner.")

                    if runner.recovery_invoked:
                        post_400_recovery_count += 1
                    if runner.count_move_as_sent:
                        aion_move_count += 1
                    if runner.count_move_as_successful:
                        move_send_ok_count += 1

                    move_records.append(record)
                    time.sleep(0.5)

        first_record = move_records[0] if move_records else {}
        first_selected_move = str(first_record.get("selected_move") or first_record.get("final_selected_move") or "")
        first_base_well_move = str(first_record.get("base_well_selected_move") or "")
        first_intent_override_applied = bool(first_record.get("intent_override_applied", False))

        trace_payload = {
            "dry_run": dry_run,
            "network_enabled": network_enabled,
            "game_id": game_id,
            "final_status": final_status,
            "final_winner": final_winner,
            "aion_move_count": aion_move_count,
            "move_send_ok_count": move_send_ok_count,
            "first_selected_move": first_selected_move,
            "first_base_well_move": first_base_well_move,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        if dry_run or not network_enabled:
            self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + 1
        else:
            self.policy["live_run_count"] = int(self.policy.get("live_run_count", 0)) + 1
        if challenge_created:
            self.policy["challenge_created_count"] = int(self.policy.get("challenge_created_count", 0)) + 1
        self.policy["move_send_ok_total"] = int(self.policy.get("move_send_ok_total", 0)) + move_send_ok_count
        self.policy["post_400_recovery_total"] = int(self.policy.get("post_400_recovery_total", 0)) + post_400_recovery_count
        self.policy["last_game_id"] = game_id
        self.policy["last_final_status"] = final_status
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e38_sender_used": True,
            "phase22e37_intent_well_inherited": True,
            "phase22e25_recovery_enabled": True,
            "full_stream_loop": bool(network_enabled and not dry_run),
            "creates_challenge_only_when_live": bool(network_enabled and not dry_run),
            "opening_drift_guard_enabled": True,
            "first_move_expected_g1f3_in_dry_run": first_selected_move == "g1f3",
            "first_base_well_h2h4_corrected": first_base_well_move == "h2h4",
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = StrategicWellLiveRematchResult(
            kernel_version="phase22e39_full_chess_level2_strategic_well_live_rematch_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            dry_run=dry_run,
            network_enabled=network_enabled,
            live_env_enabled=live_env_enabled,
            token_present=token_present,
            challenge_attempted=challenge_attempted,
            challenge_created=challenge_created,
            game_id=game_id,
            full_id=full_id,
            aion_colour=aion_colour,
            target_level=target_level,
            final_status=final_status,
            final_winner=final_winner,
            final_moves=final_moves,
            final_ply_count=len(final_moves),
            aion_move_count=aion_move_count,
            move_send_ok_count=move_send_ok_count,
            post_400_recovery_count=post_400_recovery_count,
            strategic_sender_used_count=strategic_sender_used_count,
            first_selected_move=first_selected_move,
            first_base_well_move=first_base_well_move,
            first_intent_override_applied=first_intent_override_applied,
            move_records=move_records,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel runs a full Lichess Level-2 rematch loop using the Phase 22E.38 live one-move Strategic "
                "Well sender and Phase 22E.25 recovery. It creates a challenge and posts moves only when dry_run is false, "
                "network is enabled, AION_LICHESS_LIVE=1, and a token is present. It does not call Stockfish, does not use "
                "LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_strategic_well_live_rematch_kernel(
    *,
    dry_run: bool = True,
    network_enabled: bool = False,
    target_level: int = 2,
    clock_limit_seconds: int = 300,
    clock_increment_seconds: int = 1,
    max_aion_moves: int = 120,
    token: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_strategic_well_live_rematch",
) -> StrategicWellLiveRematchResult:
    return AionStrategicWellLiveRematchKernel(memory_path=memory_path).run(
        dry_run=dry_run,
        network_enabled=network_enabled,
        target_level=target_level,
        clock_limit_seconds=clock_limit_seconds,
        clock_increment_seconds=clock_increment_seconds,
        max_aion_moves=max_aion_moves,
        token=token,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_level2_strategic_well_live_rematch_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic Well live rematch memory saved to: {result.memory_path}")
