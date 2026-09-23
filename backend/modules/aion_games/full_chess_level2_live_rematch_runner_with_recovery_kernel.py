from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .full_chess_level2_live_rematch_recovery_loop_kernel import (
    run_full_chess_level2_live_rematch_recovery_loop_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_live_rematch_runner_with_recovery_memory.json")


@dataclass(frozen=True)
class LiveRematchRunnerWithRecoveryResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    runner_mode: str
    game_id: str
    full_id: Optional[str]
    aion_colour: str
    target_level: int
    fen_before: str
    expected_moves_before: List[str]
    sender_record: Dict[str, Any]
    queen_override_enabled: bool
    queen_endgame_override_active: bool
    final_selected_move: str
    final_selected_move_is_legal: bool
    move_post_attempted: bool
    move_post_succeeded_initially: bool
    move_post_status_code: Optional[int]
    recovery_invoked: bool
    recovery_classification: str
    recovered_as_nonfatal: bool
    continue_live_loop: bool
    abort_live_loop: bool
    count_move_as_sent: bool
    count_move_as_successful: bool
    refresh_required: bool
    refreshed_latest_moves: List[str]
    refreshed_ply_count: int
    next_loop_moves: List[str]
    next_loop_ply_count: int
    trace_hash: str
    policy_memory_mutated: bool
    final_runner_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLevel2LiveRematchRunnerWithRecoveryKernel:
    def __init__(self, memory_path: Optional[Path] = None, recovery_loop_memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.recovery_loop_memory_path = recovery_loop_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "runner_step_count": 0,
            "queen_override_seen_count": 0,
            "post_400_recovery_seen_count": 0,
            "continued_count": 0,
            "aborted_count": 0,
            "last_game_id": None,
            "last_selected_move": None,
            "last_continue_live_loop": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_rematch_runner_with_recovery_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveRematchRunnerWithRecoveryResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e25_live_rematch_runner_with_recovery_memory_v1",
            "task_name": result.task_name,
            "live_rematch_runner_with_recovery_policy": result.final_runner_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str,
        full_id: Optional[str],
        aion_colour: str,
        target_level: int,
        fen_before: str,
        expected_moves_before: Optional[List[str]],
        sender_record: Dict[str, Any],
        latest_state_after_failure: Optional[Dict[str, Any]] = None,
        token: str = "",
        task_name: str = "full_chess_level2_live_rematch_runner_with_recovery",
    ) -> LiveRematchRunnerWithRecoveryResult:
        expected_moves_before = list(expected_moves_before or [])

        final_selected_move = str(
            sender_record.get("final_selected_move")
            or sender_record.get("selected_move")
            or ""
        )
        final_selected_move_is_legal = bool(
            sender_record.get("final_selected_move_is_legal")
            if "final_selected_move_is_legal" in sender_record
            else sender_record.get("selected_move_is_legal")
        )

        move_post_attempted = bool(sender_record.get("move_post_attempted"))
        move_post_succeeded_initially = bool(sender_record.get("move_post_succeeded"))
        move_post_status_code = sender_record.get("move_post_status_code")
        move_post_error = sender_record.get("move_post_error")

        queen_endgame_override_active = bool(sender_record.get("queen_endgame_override_active"))

        recovery = run_full_chess_level2_live_rematch_recovery_loop_kernel(
            game_id=game_id,
            attempted_move=final_selected_move,
            fen_before=fen_before,
            expected_moves_before=expected_moves_before,
            move_post_attempted=move_post_attempted,
            move_post_succeeded=move_post_succeeded_initially,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            token=token,
            latest_state=latest_state_after_failure,
            memory_path=self.recovery_loop_memory_path,
        )

        if recovery.refresh_required:
            next_loop_moves = list(recovery.refreshed_latest_moves)
        elif recovery.count_move_as_successful:
            next_loop_moves = list(expected_moves_before)
            if len(next_loop_moves) == len(expected_moves_before):
                next_loop_moves.append(final_selected_move)
        else:
            next_loop_moves = list(expected_moves_before)

        next_loop_ply_count = len(next_loop_moves)

        trace_payload = {
            "game_id": game_id,
            "full_id": full_id,
            "aion_colour": aion_colour,
            "target_level": target_level,
            "selected_move": final_selected_move,
            "queen_endgame_override_active": queen_endgame_override_active,
            "move_post_status_code": move_post_status_code,
            "recovery_invoked": recovery.recovery_invoked,
            "recovery_classification": recovery.recovery_classification,
            "continue_live_loop": recovery.continue_live_loop,
            "abort_live_loop": recovery.abort_live_loop,
            "next_loop_ply_count": next_loop_ply_count,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["runner_step_count"] = int(self.policy.get("runner_step_count", 0)) + 1
        self.policy["queen_override_seen_count"] = int(self.policy.get("queen_override_seen_count", 0)) + (1 if queen_endgame_override_active else 0)
        self.policy["post_400_recovery_seen_count"] = int(self.policy.get("post_400_recovery_seen_count", 0)) + (1 if recovery.recovery_invoked else 0)
        self.policy["continued_count"] = int(self.policy.get("continued_count", 0)) + (1 if recovery.continue_live_loop else 0)
        self.policy["aborted_count"] = int(self.policy.get("aborted_count", 0)) + (1 if recovery.abort_live_loop else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_selected_move"] = final_selected_move
        self.policy["last_continue_live_loop"] = recovery.continue_live_loop
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "full_level2_live_rematch_runner_with_recovery_enabled": True,
            "queen_override_enabled": True,
            "post_400_recovery_enabled": True,
            "refreshes_loop_moves_after_nonfatal_recovery": recovery.refresh_required,
            "continues_after_nonfatal_recovery": recovery.continue_live_loop,
            "aborts_only_on_hard_failure": recovery.abort_live_loop,
            "counts_recovered_move_as_successful": recovery.count_move_as_successful,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveRematchRunnerWithRecoveryResult(
            kernel_version="phase22e25_full_chess_level2_live_rematch_runner_with_recovery_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            runner_mode="full_level2_live_rematch_runner_with_queen_override_and_post_400_recovery",
            game_id=game_id,
            full_id=full_id,
            aion_colour=aion_colour,
            target_level=target_level,
            fen_before=fen_before,
            expected_moves_before=expected_moves_before,
            sender_record=dict(sender_record),
            queen_override_enabled=True,
            queen_endgame_override_active=queen_endgame_override_active,
            final_selected_move=final_selected_move,
            final_selected_move_is_legal=final_selected_move_is_legal,
            move_post_attempted=move_post_attempted,
            move_post_succeeded_initially=move_post_succeeded_initially,
            move_post_status_code=move_post_status_code,
            recovery_invoked=recovery.recovery_invoked,
            recovery_classification=recovery.recovery_classification,
            recovered_as_nonfatal=recovery.recovered_as_nonfatal,
            continue_live_loop=recovery.continue_live_loop,
            abort_live_loop=recovery.abort_live_loop,
            count_move_as_sent=recovery.count_move_as_sent,
            count_move_as_successful=recovery.count_move_as_successful,
            refresh_required=recovery.refresh_required,
            refreshed_latest_moves=recovery.refreshed_latest_moves,
            refreshed_ply_count=recovery.refreshed_ply_count,
            next_loop_moves=next_loop_moves,
            next_loop_ply_count=next_loop_ply_count,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_runner_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel locks the full Level-2 live rematch runner decision contract using Phase 22E.21 "
                "queen override records and Phase 22E.24 POST-400 recovery. It does not create challenges, "
                "does not send moves, does not call Stockfish, does not use LLM judgement, and does not use "
                "Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
    *,
    game_id: str,
    full_id: Optional[str],
    aion_colour: str,
    target_level: int,
    fen_before: str,
    expected_moves_before: Optional[List[str]],
    sender_record: Dict[str, Any],
    latest_state_after_failure: Optional[Dict[str, Any]] = None,
    token: str = "",
    memory_path: Optional[Path] = None,
    recovery_loop_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_live_rematch_runner_with_recovery",
) -> LiveRematchRunnerWithRecoveryResult:
    return AionFullChessLevel2LiveRematchRunnerWithRecoveryKernel(
        memory_path=memory_path,
        recovery_loop_memory_path=recovery_loop_memory_path,
    ).run(
        game_id=game_id,
        full_id=full_id,
        aion_colour=aion_colour,
        target_level=target_level,
        fen_before=fen_before,
        expected_moves_before=expected_moves_before,
        sender_record=sender_record,
        latest_state_after_failure=latest_state_after_failure,
        token=token,
        task_name=task_name,
    )


if __name__ == "__main__":
    moves_before = [
        "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
        "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "e7e6",
    ]
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before="rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13",
        expected_moves_before=moves_before,
        sender_record={
            "queen_endgame_override_active": False,
            "base_sender_consumed": True,
            "base_selected_move": "e2g4",
            "override_selected_move": "",
            "final_selected_move": "e2g4",
            "final_selected_move_is_legal": True,
            "move_post_attempted": True,
            "move_post_succeeded": False,
            "move_post_status_code": 400,
            "move_post_error": "HTTP Error 400: Bad Request",
        },
        latest_state_after_failure={"status": "started", "moves": " ".join(moves_before + ["e2g4"])},
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live rematch runner with recovery memory saved to: {result.memory_path}")
