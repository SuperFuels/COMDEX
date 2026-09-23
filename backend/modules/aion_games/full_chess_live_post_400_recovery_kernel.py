from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import chess

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_live_post_400_recovery_memory.json")


@dataclass(frozen=True)
class LivePost400RecoveryResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    recovery_mode: str
    game_id: str
    attempted_move: str
    attempted_move_was_locally_legal: bool
    move_post_succeeded_initially: bool
    move_post_status_code: Optional[int]
    move_post_error: Optional[str]
    recovery_triggered: bool
    latest_state_fetch_attempted: bool
    latest_state_fetch_succeeded: bool
    latest_state_status_code: Optional[int]
    latest_state_error: Optional[str]
    latest_status: Optional[str]
    latest_winner: Optional[str]
    latest_moves: List[str]
    latest_ply_count: int
    expected_ply_before: int
    server_ply_advanced: bool
    attempted_move_already_present: bool
    stale_state_detected: bool
    retry_recommended: bool
    abort_recommended: bool
    recovered_as_nonfatal: bool
    failure_classification: str
    trace_hash: str
    policy_memory_mutated: bool
    final_recovery_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionLivePost400RecoveryKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "recovery_run_count": 0,
            "recovery_triggered_count": 0,
            "stale_state_detected_count": 0,
            "nonfatal_recovery_count": 0,
            "hard_abort_count": 0,
            "last_game_id": None,
            "last_attempted_move": None,
            "last_failure_classification": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_post_400_recovery_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LivePost400RecoveryResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e23_live_post_400_recovery_memory_v1",
            "task_name": result.task_name,
            "live_post_400_recovery_policy": result.final_recovery_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _fetch_latest_state_from_lichess(self, *, token: str, game_id: str) -> Tuple[bool, Optional[int], Optional[str], Dict[str, Any]]:
        url = f"https://lichess.org/api/bot/game/stream/{game_id}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/x-ndjson",
            },
        )

        latest: Dict[str, Any] = {}
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status = int(response.status)
                for raw in response:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("type") == "gameFull":
                        latest = event.get("state", {}) or {}
                    elif event.get("type") == "gameState":
                        latest = event
                    if latest:
                        break
                return True, status, None, latest
        except urllib.error.HTTPError as exc:
            return False, int(exc.code), str(exc), {}
        except Exception as exc:
            return False, None, str(exc), {}

    def _moves_from_state(self, state: Dict[str, Any]) -> List[str]:
        moves_text = str(state.get("moves") or "").strip()
        return moves_text.split() if moves_text else []

    def run(
        self,
        *,
        game_id: str,
        attempted_move: str,
        fen_before: str,
        expected_moves_before: Optional[List[str]] = None,
        move_post_succeeded_initially: bool = False,
        move_post_status_code: Optional[int] = None,
        move_post_error: Optional[str] = None,
        token: str = "",
        latest_state: Optional[Dict[str, Any]] = None,
        latest_state_fetch_callable: Optional[Callable[[str, str], Tuple[bool, Optional[int], Optional[str], Dict[str, Any]]]] = None,
        task_name: str = "full_chess_live_post_400_recovery",
    ) -> LivePost400RecoveryResult:
        expected_moves_before = list(expected_moves_before or [])
        expected_ply_before = len(expected_moves_before)

        board = chess.Board(fen_before)
        try:
            attempted_chess_move = chess.Move.from_uci(attempted_move)
            attempted_move_was_locally_legal = attempted_chess_move in board.legal_moves
        except ValueError:
            attempted_move_was_locally_legal = False

        recovery_triggered = (
            not move_post_succeeded_initially
            and move_post_status_code == 400
        )

        latest_state_fetch_attempted = False
        latest_state_fetch_succeeded = False
        latest_state_status_code: Optional[int] = None
        latest_state_error: Optional[str] = None
        resolved_latest_state: Dict[str, Any] = dict(latest_state or {})

        if recovery_triggered:
            if resolved_latest_state:
                latest_state_fetch_attempted = True
                latest_state_fetch_succeeded = True
                latest_state_status_code = 200
            else:
                latest_state_fetch_attempted = True
                if latest_state_fetch_callable is not None:
                    latest_state_fetch_succeeded, latest_state_status_code, latest_state_error, resolved_latest_state = latest_state_fetch_callable(
                        token,
                        game_id,
                    )
                else:
                    latest_state_fetch_succeeded, latest_state_status_code, latest_state_error, resolved_latest_state = self._fetch_latest_state_from_lichess(
                        token=token,
                        game_id=game_id,
                    )

        latest_moves = self._moves_from_state(resolved_latest_state)
        latest_ply_count = len(latest_moves)
        latest_status = resolved_latest_state.get("status")
        latest_winner = resolved_latest_state.get("winner")

        server_ply_advanced = latest_ply_count > expected_ply_before
        attempted_move_already_present = (
            latest_ply_count > expected_ply_before
            and latest_moves[expected_ply_before] == attempted_move
        )

        stale_state_detected = (
            recovery_triggered
            and latest_state_fetch_succeeded
            and server_ply_advanced
        )

        game_already_finished = latest_status is not None and latest_status != "started"

        if move_post_succeeded_initially:
            failure_classification = "no_failure"
            retry_recommended = False
            abort_recommended = False
            recovered_as_nonfatal = True
        elif not recovery_triggered:
            failure_classification = "non_400_post_failure"
            retry_recommended = False
            abort_recommended = True
            recovered_as_nonfatal = False
        elif attempted_move_already_present:
            failure_classification = "post_400_but_move_already_applied"
            retry_recommended = False
            abort_recommended = False
            recovered_as_nonfatal = True
        elif stale_state_detected:
            failure_classification = "post_400_due_stale_state_server_already_advanced"
            retry_recommended = False
            abort_recommended = False
            recovered_as_nonfatal = True
        elif game_already_finished:
            failure_classification = "post_400_because_game_already_finished"
            retry_recommended = False
            abort_recommended = False
            recovered_as_nonfatal = True
        elif latest_state_fetch_succeeded:
            failure_classification = "post_400_confirmed_current_state_rejected_move"
            retry_recommended = False
            abort_recommended = True
            recovered_as_nonfatal = False
        else:
            failure_classification = "post_400_unresolved_latest_state_fetch_failed"
            retry_recommended = True
            abort_recommended = False
            recovered_as_nonfatal = False

        trace_payload = {
            "game_id": game_id,
            "attempted_move": attempted_move,
            "expected_ply_before": expected_ply_before,
            "move_post_status_code": move_post_status_code,
            "recovery_triggered": recovery_triggered,
            "latest_ply_count": latest_ply_count,
            "latest_status": latest_status,
            "latest_winner": latest_winner,
            "server_ply_advanced": server_ply_advanced,
            "attempted_move_already_present": attempted_move_already_present,
            "failure_classification": failure_classification,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["recovery_run_count"] = int(self.policy.get("recovery_run_count", 0)) + 1
        self.policy["recovery_triggered_count"] = int(self.policy.get("recovery_triggered_count", 0)) + (1 if recovery_triggered else 0)
        self.policy["stale_state_detected_count"] = int(self.policy.get("stale_state_detected_count", 0)) + (1 if stale_state_detected else 0)
        self.policy["nonfatal_recovery_count"] = int(self.policy.get("nonfatal_recovery_count", 0)) + (1 if recovered_as_nonfatal else 0)
        self.policy["hard_abort_count"] = int(self.policy.get("hard_abort_count", 0)) + (1 if abort_recommended else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_attempted_move"] = attempted_move
        self.policy["last_failure_classification"] = failure_classification
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "post_400_recovery_enabled": True,
            "latest_state_fetch_enabled": True,
            "stale_state_guard_enabled": True,
            "attempted_move_local_legality_checked": True,
            "server_ply_advance_checked": True,
            "move_already_present_checked": True,
            "game_finished_checked": True,
            "hard_abort_only_after_confirmed_current_state_rejection": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LivePost400RecoveryResult(
            kernel_version="phase22e23_full_chess_live_post_400_recovery_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            recovery_mode="live_post_400_recovery_stale_state_guard",
            game_id=game_id,
            attempted_move=attempted_move,
            attempted_move_was_locally_legal=attempted_move_was_locally_legal,
            move_post_succeeded_initially=move_post_succeeded_initially,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            recovery_triggered=recovery_triggered,
            latest_state_fetch_attempted=latest_state_fetch_attempted,
            latest_state_fetch_succeeded=latest_state_fetch_succeeded,
            latest_state_status_code=latest_state_status_code,
            latest_state_error=latest_state_error,
            latest_status=latest_status,
            latest_winner=latest_winner,
            latest_moves=latest_moves,
            latest_ply_count=latest_ply_count,
            expected_ply_before=expected_ply_before,
            server_ply_advanced=server_ply_advanced,
            attempted_move_already_present=attempted_move_already_present,
            stale_state_detected=stale_state_detected,
            retry_recommended=retry_recommended,
            abort_recommended=abort_recommended,
            recovered_as_nonfatal=recovered_as_nonfatal,
            failure_classification=failure_classification,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_recovery_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel handles live POST 400 recovery. It fetches or consumes the latest game state, "
                "checks whether the server already advanced, and prevents aborting on stale local state. "
                "It does not select chess moves, does not call Stockfish, does not use LLM judgement, "
                "and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_post_400_recovery_kernel(
    *,
    game_id: str,
    attempted_move: str,
    fen_before: str,
    expected_moves_before: Optional[List[str]] = None,
    move_post_succeeded_initially: bool = False,
    move_post_status_code: Optional[int] = None,
    move_post_error: Optional[str] = None,
    token: str = "",
    latest_state: Optional[Dict[str, Any]] = None,
    latest_state_fetch_callable: Optional[Callable[[str, str], Tuple[bool, Optional[int], Optional[str], Dict[str, Any]]]] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_post_400_recovery",
) -> LivePost400RecoveryResult:
    return AionLivePost400RecoveryKernel(memory_path=memory_path).run(
        game_id=game_id,
        attempted_move=attempted_move,
        fen_before=fen_before,
        expected_moves_before=expected_moves_before,
        move_post_succeeded_initially=move_post_succeeded_initially,
        move_post_status_code=move_post_status_code,
        move_post_error=move_post_error,
        token=token,
        latest_state=latest_state,
        latest_state_fetch_callable=latest_state_fetch_callable,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before="rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13",
        expected_moves_before=[
            "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
            "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "g8h6",
        ],
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        move_post_error="HTTP Error 400: Bad Request",
        latest_state={
            "status": "started",
            "moves": "g1f3 c7c6 b1c3 d7d5 f3g5 f7f6 e2e4 g8h6 g5f3 d8d6 d2d4 g8h6 e2g4"
        },
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live POST 400 recovery memory saved to: {result.memory_path}")
