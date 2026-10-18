"""AION Phase 22B.31 — Full Chess Guarded Live Move Execution Kernel.

This phase proves AION can guard a live Lichess move execution request.

It proves:
- live move execution requests are represented;
- dry-run execution is allowed;
- live network writes are blocked unless every guard passes;
- token state is checked without exposing secrets;
- move payload is validated before execution;
- guarded execution emits a trace hash;
- no LLM shortcut is used.

This is the execution safety boundary before any real online move write.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_GUARDED_LIVE_MOVE_MEMORY_PATH = Path(
    "data/aion_games/full_chess_guarded_live_move_execution_memory.json"
)


@dataclass(frozen=True)
class GuardedLiveMoveRequest:
    game_id: str
    move: str
    endpoint: str
    method: str
    dry_run: bool
    allow_network: bool
    require_human_approval: bool
    human_approved: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GuardDecision:
    token_present: bool
    token_redacted: str
    valid_move_shape: bool
    valid_endpoint: bool
    valid_method: bool
    dry_run_guard_active: bool
    network_allowed: bool
    human_approval_required: bool
    human_approved: bool
    execution_allowed: bool
    block_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullChessGuardedLiveMoveExecutionResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    execution_mode: str
    request: Dict[str, Any]
    guard_decision: Dict[str, Any]
    prepared_request: Dict[str, Any]
    would_post_move: bool
    network_call_performed: bool
    live_write_blocked: bool
    dry_run_preview_emitted: bool
    selected_bestmove: str
    game_id: str
    guarded_execution_trace_hash: str
    final_guarded_execution_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessGuardedLiveMoveExecutionKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_GUARDED_LIVE_MOVE_MEMORY_PATH)
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "guarded_execution_session_count": 0,
            "dry_run_preview_count": 0,
            "blocked_live_write_count": 0,
            "network_call_count": 0,
            "last_game_id": None,
            "last_move": None,
            "last_block_reason": None,
            "last_guarded_execution_trace_hash": None,
        }

        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return

        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if isinstance(data, dict):
            policy = data.get("guarded_execution_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: FullChessGuardedLiveMoveExecutionResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b31_full_chess_guarded_live_move_execution_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "guarded_execution_policy": result.final_guarded_execution_policy,
            "last_game_id": result.game_id,
            "last_move": result.selected_bestmove,
            "network_call_performed": result.network_call_performed,
            "live_write_blocked": result.live_write_blocked,
            "guarded_execution_trace_hash": result.guarded_execution_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _redact_token(self, token: str) -> str:
        if not token:
            return "missing"
        if len(token) <= 8:
            return "present-redacted"
        return f"{token[:4]}...{token[-4:]}"

    def _valid_uci_move_shape(self, move: str) -> bool:
        move = move.lower().strip()
        files = "abcdefgh"
        ranks = "12345678"
        return (
            len(move) in {4, 5}
            and move[0] in files
            and move[1] in ranks
            and move[2] in files
            and move[3] in ranks
            and (len(move) == 4 or move[4] in "qrbn")
        )

    def _default_request(
        self,
        *,
        dry_run: bool,
        allow_network: bool,
        require_human_approval: bool,
        human_approved: bool,
        game_id: str,
        move: str,
    ) -> GuardedLiveMoveRequest:
        endpoint = f"https://lichess.org/api/bot/game/{game_id}/move/{move}"
        return GuardedLiveMoveRequest(
            game_id=game_id,
            move=move,
            endpoint=endpoint,
            method="POST",
            dry_run=dry_run,
            allow_network=allow_network,
            require_human_approval=require_human_approval,
            human_approved=human_approved,
        )

    def _guard(self, request: GuardedLiveMoveRequest) -> GuardDecision:
        token = os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token)

        valid_move_shape = self._valid_uci_move_shape(request.move)
        valid_endpoint = (
            request.endpoint.startswith("https://lichess.org/api/bot/game/")
            and f"/move/{request.move}" in request.endpoint
            and request.game_id in request.endpoint
        )
        valid_method = request.method == "POST"

        dry_run_guard_active = request.dry_run is True
        network_allowed = request.allow_network is True and dry_run_guard_active is False
        human_required = request.require_human_approval is True

        execution_allowed = (
            token_present
            and valid_move_shape
            and valid_endpoint
            and valid_method
            and network_allowed
            and (not human_required or request.human_approved)
        )

        if execution_allowed:
            block_reason = "none"
        elif dry_run_guard_active:
            block_reason = "dry_run_guard_active"
        elif not token_present:
            block_reason = "missing_lichess_bot_token"
        elif not request.allow_network:
            block_reason = "network_not_allowed"
        elif human_required and not request.human_approved:
            block_reason = "human_approval_required"
        elif not valid_move_shape:
            block_reason = "invalid_uci_move_shape"
        elif not valid_endpoint:
            block_reason = "invalid_lichess_endpoint"
        elif not valid_method:
            block_reason = "invalid_http_method"
        else:
            block_reason = "unknown_guard_block"

        return GuardDecision(
            token_present=token_present,
            token_redacted=self._redact_token(token),
            valid_move_shape=valid_move_shape,
            valid_endpoint=valid_endpoint,
            valid_method=valid_method,
            dry_run_guard_active=dry_run_guard_active,
            network_allowed=network_allowed,
            human_approval_required=human_required,
            human_approved=request.human_approved,
            execution_allowed=execution_allowed,
            block_reason=block_reason,
        )

    def run(
        self,
        *,
        task_name: str = "full_chess_guarded_live_move_execution",
        dry_run: bool = True,
        allow_network: bool = False,
        require_human_approval: bool = True,
        human_approved: bool = False,
        game_id: str = "aion-demo-game-001",
        move: str = "c4d5",
    ) -> FullChessGuardedLiveMoveExecutionResult:
        request = self._default_request(
            dry_run=dry_run,
            allow_network=allow_network,
            require_human_approval=require_human_approval,
            human_approved=human_approved,
            game_id=game_id,
            move=move,
        )
        guard_decision = self._guard(request)

        prepared_request = {
            "method": request.method,
            "url": request.endpoint,
            "headers": {
                "Authorization": "Bearer <redacted>",
            },
            "payload": {
                "game_id": request.game_id,
                "move": request.move,
                "offering_draw": False,
            },
        }

        would_post_move = (
            guard_decision.valid_move_shape
            and guard_decision.valid_endpoint
            and guard_decision.valid_method
        )

        network_call_performed = False
        if guard_decision.execution_allowed:
            # Intentionally not implemented in this lock.
            # A later phase may perform the real POST under explicit operator approval.
            network_call_performed = False

        live_write_blocked = not network_call_performed
        dry_run_preview_emitted = request.dry_run and would_post_move

        trace_payload = {
            "request": request.to_dict(),
            "guard_decision": guard_decision.to_dict(),
            "prepared_request": prepared_request,
            "would_post_move": would_post_move,
            "network_call_performed": network_call_performed,
            "live_write_blocked": live_write_blocked,
            "dry_run_preview_emitted": dry_run_preview_emitted,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["guarded_execution_session_count"] = int(
            self.policy.get("guarded_execution_session_count", 0)
        ) + 1
        self.policy["dry_run_preview_count"] = int(
            self.policy.get("dry_run_preview_count", 0)
        ) + (1 if dry_run_preview_emitted else 0)
        self.policy["blocked_live_write_count"] = int(
            self.policy.get("blocked_live_write_count", 0)
        ) + (1 if live_write_blocked else 0)
        self.policy["network_call_count"] = int(
            self.policy.get("network_call_count", 0)
        ) + (1 if network_call_performed else 0)
        self.policy["last_game_id"] = request.game_id
        self.policy["last_move"] = request.move
        self.policy["last_block_reason"] = guard_decision.block_reason
        self.policy["last_guarded_execution_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "builds_live_move_request": True,
            "validates_uci_move_shape": guard_decision.valid_move_shape,
            "validates_lichess_endpoint": guard_decision.valid_endpoint,
            "validates_http_method": guard_decision.valid_method,
            "checks_token_without_exposing_secret": guard_decision.token_redacted != os.environ.get("LICHESS_BOT_TOKEN", ""),
            "dry_run_guard_active": guard_decision.dry_run_guard_active,
            "human_approval_required": guard_decision.human_approval_required,
            "execution_not_allowed_without_all_guards": guard_decision.execution_allowed is False,
            "does_not_perform_network_call": network_call_performed is False,
            "emits_dry_run_preview": dry_run_preview_emitted is True,
            "live_write_blocked": live_write_blocked is True,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = FullChessGuardedLiveMoveExecutionResult(
            kernel_version="phase22b31_full_chess_guarded_live_move_execution_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            execution_mode="guarded_dry_run_live_move_execution",
            request=request.to_dict(),
            guard_decision=guard_decision.to_dict(),
            prepared_request=prepared_request,
            would_post_move=would_post_move,
            network_call_performed=network_call_performed,
            live_write_blocked=live_write_blocked,
            dry_run_preview_emitted=dry_run_preview_emitted,
            selected_bestmove=request.move,
            game_id=request.game_id,
            guarded_execution_trace_hash=trace_hash,
            final_guarded_execution_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates guarded live move execution for the AION chess scaffold. "
                "AION validates the move request, endpoint, token state, network flag, dry-run flag, and human approval requirement. "
                "By default it emits only a dry-run preview and blocks live writes. It does not yet perform a real Lichess POST, "
                "enter live games autonomously, expose OAuth secrets, claim official rating, prove engine-strength play, "
                "general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_guarded_live_move_execution_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_guarded_live_move_execution",
    dry_run: bool = True,
    allow_network: bool = False,
    require_human_approval: bool = True,
    human_approved: bool = False,
    game_id: str = "aion-demo-game-001",
    move: str = "c4d5",
) -> FullChessGuardedLiveMoveExecutionResult:
    return AionFullChessGuardedLiveMoveExecutionKernel(memory_path=memory_path).run(
        task_name=task_name,
        dry_run=dry_run,
        allow_network=allow_network,
        require_human_approval=require_human_approval,
        human_approved=human_approved,
        game_id=game_id,
        move=move,
    )


if __name__ == "__main__":
    result = run_full_chess_guarded_live_move_execution_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess guarded live move execution memory saved to: {result.memory_path}")
