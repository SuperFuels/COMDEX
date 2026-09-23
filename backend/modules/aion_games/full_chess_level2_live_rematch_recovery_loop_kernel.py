from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .full_chess_live_post_400_recovery_kernel import (
    run_full_chess_live_post_400_recovery_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_live_rematch_recovery_loop_memory.json")


@dataclass(frozen=True)
class LiveRematchRecoveryLoopResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    loop_mode: str
    game_id: str
    attempted_move: str
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
    trace_hash: str
    policy_memory_mutated: bool
    final_loop_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLevel2LiveRematchRecoveryLoopKernel:
    def __init__(self, memory_path: Optional[Path] = None, recovery_memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.recovery_memory_path = recovery_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "loop_recovery_count": 0,
            "nonfatal_recovery_count": 0,
            "hard_abort_count": 0,
            "last_game_id": None,
            "last_attempted_move": None,
            "last_continue_live_loop": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_rematch_recovery_loop_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveRematchRecoveryLoopResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e24_live_rematch_recovery_loop_memory_v1",
            "task_name": result.task_name,
            "live_rematch_recovery_loop_policy": result.final_loop_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str,
        attempted_move: str,
        fen_before: str,
        expected_moves_before: Optional[List[str]] = None,
        move_post_attempted: bool,
        move_post_succeeded: bool,
        move_post_status_code: Optional[int],
        move_post_error: Optional[str] = None,
        token: str = "",
        latest_state: Optional[Dict[str, Any]] = None,
        task_name: str = "full_chess_level2_live_rematch_recovery_loop",
    ) -> LiveRematchRecoveryLoopResult:
        expected_moves_before = list(expected_moves_before or [])

        recovery_invoked = False
        recovery_classification = "not_needed"
        recovered_as_nonfatal = False
        refreshed_latest_moves: List[str] = []
        refreshed_ply_count = len(expected_moves_before)

        if move_post_attempted and not move_post_succeeded and move_post_status_code == 400:
            recovery_invoked = True
            recovery = run_full_chess_live_post_400_recovery_kernel(
                game_id=game_id,
                attempted_move=attempted_move,
                fen_before=fen_before,
                expected_moves_before=expected_moves_before,
                move_post_succeeded_initially=False,
                move_post_status_code=move_post_status_code,
                move_post_error=move_post_error,
                token=token,
                latest_state=latest_state,
                memory_path=self.recovery_memory_path,
            )
            recovery_classification = recovery.failure_classification
            recovered_as_nonfatal = recovery.recovered_as_nonfatal
            refreshed_latest_moves = recovery.latest_moves
            refreshed_ply_count = recovery.latest_ply_count

        elif move_post_succeeded:
            recovered_as_nonfatal = True
            refreshed_latest_moves = expected_moves_before + [attempted_move]
            refreshed_ply_count = len(refreshed_latest_moves)

        continue_live_loop = move_post_succeeded or recovered_as_nonfatal
        abort_live_loop = not continue_live_loop

        count_move_as_sent = move_post_attempted
        count_move_as_successful = move_post_succeeded or recovered_as_nonfatal
        refresh_required = recovery_invoked and recovered_as_nonfatal

        trace_payload = {
            "game_id": game_id,
            "attempted_move": attempted_move,
            "move_post_status_code": move_post_status_code,
            "recovery_invoked": recovery_invoked,
            "recovery_classification": recovery_classification,
            "recovered_as_nonfatal": recovered_as_nonfatal,
            "continue_live_loop": continue_live_loop,
            "abort_live_loop": abort_live_loop,
            "refreshed_ply_count": refreshed_ply_count,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["loop_recovery_count"] = int(self.policy.get("loop_recovery_count", 0)) + (1 if recovery_invoked else 0)
        self.policy["nonfatal_recovery_count"] = int(self.policy.get("nonfatal_recovery_count", 0)) + (1 if recovered_as_nonfatal else 0)
        self.policy["hard_abort_count"] = int(self.policy.get("hard_abort_count", 0)) + (1 if abort_live_loop else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_attempted_move"] = attempted_move
        self.policy["last_continue_live_loop"] = continue_live_loop
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "post_400_recovery_integrated_into_live_loop": True,
            "live_loop_continues_after_nonfatal_400": continue_live_loop,
            "live_loop_aborts_only_on_hard_failure": abort_live_loop,
            "refresh_required_after_recovery": refresh_required,
            "count_recovered_move_as_successful": count_move_as_successful,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveRematchRecoveryLoopResult(
            kernel_version="phase22e24_full_chess_level2_live_rematch_recovery_loop_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            loop_mode="level2_live_rematch_post_400_recovery_loop",
            game_id=game_id,
            attempted_move=attempted_move,
            move_post_attempted=move_post_attempted,
            move_post_succeeded_initially=move_post_succeeded,
            move_post_status_code=move_post_status_code,
            recovery_invoked=recovery_invoked,
            recovery_classification=recovery_classification,
            recovered_as_nonfatal=recovered_as_nonfatal,
            continue_live_loop=continue_live_loop,
            abort_live_loop=abort_live_loop,
            count_move_as_sent=count_move_as_sent,
            count_move_as_successful=count_move_as_successful,
            refresh_required=refresh_required,
            refreshed_latest_moves=refreshed_latest_moves,
            refreshed_ply_count=refreshed_ply_count,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_loop_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel integrates Phase 22E.23 POST 400 recovery into the Phase 22E.22 live rematch loop. "
                "It does not select chess moves, does not send moves, does not call Stockfish, "
                "does not use LLM judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_live_rematch_recovery_loop_kernel(
    *,
    game_id: str,
    attempted_move: str,
    fen_before: str,
    expected_moves_before: Optional[List[str]] = None,
    move_post_attempted: bool,
    move_post_succeeded: bool,
    move_post_status_code: Optional[int],
    move_post_error: Optional[str] = None,
    token: str = "",
    latest_state: Optional[Dict[str, Any]] = None,
    memory_path: Optional[Path] = None,
    recovery_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_live_rematch_recovery_loop",
) -> LiveRematchRecoveryLoopResult:
    return AionFullChessLevel2LiveRematchRecoveryLoopKernel(
        memory_path=memory_path,
        recovery_memory_path=recovery_memory_path,
    ).run(
        game_id=game_id,
        attempted_move=attempted_move,
        fen_before=fen_before,
        expected_moves_before=expected_moves_before,
        move_post_attempted=move_post_attempted,
        move_post_succeeded=move_post_succeeded,
        move_post_status_code=move_post_status_code,
        move_post_error=move_post_error,
        token=token,
        latest_state=latest_state,
        task_name=task_name,
    )


if __name__ == "__main__":
    moves_before = [
        "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
        "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "e7e6",
    ]
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before="rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13",
        expected_moves_before=moves_before,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        move_post_error="HTTP Error 400: Bad Request",
        latest_state={"status": "started", "moves": " ".join(moves_before + ["e2g4"])},
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live rematch recovery loop memory saved to: {result.memory_path}")
