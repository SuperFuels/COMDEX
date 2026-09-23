"""AION Phase 22B.40 — Real Lichess Network Move Sender Kernel.

This phase is the guarded live network sender for Lichess Bot API moves.

It proves:
- token is read only from the shell environment;
- token is never printed raw;
- move URL is prepared for the Bot API;
- dry-run blocks network sending by default;
- missing game id blocks sending;
- missing token blocks sending;
- live send requires dry_run=False, allow_network=True, live_enable=True;
- tests mock the network call;
- real sending can be triggered only by explicit runtime parameters.

Endpoint:
POST https://lichess.org/api/bot/game/{gameId}/move/{move}
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import request, error


DEFAULT_REAL_LICHESS_NETWORK_MOVE_SENDER_MEMORY_PATH = Path(
    "data/aion_games/full_chess_real_lichess_network_move_sender_memory.json"
)


@dataclass(frozen=True)
class RealLichessMoveSendRequest:
    base_url: str
    token_env_name: str
    token_present: bool
    token_redacted: str
    game_id: str
    move: str
    dry_run: bool
    allow_network: bool
    live_enable: bool
    method: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealLichessMoveSendResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    sender_mode: str
    request: Dict[str, Any]
    selected_bestmove: str
    selected_policy: str
    send_allowed: bool
    send_attempted: bool
    send_success: bool
    block_reason: str
    http_status: Optional[int]
    response_preview: str
    token_guard_active: bool
    game_id_guard_active: bool
    dry_run_guard_active: bool
    network_guard_active: bool
    live_enable_guard_active: bool
    network_call_performed: bool
    real_send_trace_hash: str
    final_real_send_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessRealLichessNetworkMoveSenderKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_REAL_LICHESS_NETWORK_MOVE_SENDER_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "send_session_count": 0,
            "send_allowed_total": 0,
            "send_attempted_total": 0,
            "send_success_total": 0,
            "send_blocked_total": 0,
            "last_block_reason": None,
            "last_game_id": None,
            "last_move": None,
            "last_http_status": None,
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
        if isinstance(data, dict):
            policy = data.get("real_lichess_network_move_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: RealLichessMoveSendResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b40_full_chess_real_lichess_network_move_sender_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "real_lichess_network_move_sender_policy": result.final_real_send_policy,
            "selected_bestmove": result.selected_bestmove,
            "selected_policy": result.selected_policy,
            "send_allowed": result.send_allowed,
            "send_attempted": result.send_attempted,
            "send_success": result.send_success,
            "block_reason": result.block_reason,
            "http_status": result.http_status,
            "real_send_trace_hash": result.real_send_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _redact_token(self, token: str | None) -> str:
        if not token:
            return "missing"
        if len(token) <= 8:
            return "present_redacted"
        return f"{token[:4]}...{token[-4:]}"

    def _build_request(
        self,
        *,
        token_env_name: str,
        game_id: str,
        move: str,
        dry_run: bool,
        allow_network: bool,
        live_enable: bool,
    ) -> RealLichessMoveSendRequest:
        base_url = "https://lichess.org"
        token = os.environ.get(token_env_name)
        clean_game_id = (game_id or "").strip()
        clean_move = (move or "").strip()
        url = f"{base_url}/api/bot/game/{clean_game_id}/move/{clean_move}"

        return RealLichessMoveSendRequest(
            base_url=base_url,
            token_env_name=token_env_name,
            token_present=bool(token),
            token_redacted=self._redact_token(token),
            game_id=clean_game_id,
            move=clean_move,
            dry_run=dry_run,
            allow_network=allow_network,
            live_enable=live_enable,
            method="POST",
            url=url,
        )

    def _guard(self, req: RealLichessMoveSendRequest) -> tuple[bool, str]:
        if req.dry_run:
            return False, "dry_run_guard_active"
        if not req.token_present:
            return False, "token_missing"
        if not req.game_id:
            return False, "game_id_missing"
        if not req.move:
            return False, "move_missing"
        if not req.allow_network:
            return False, "network_guard_active"
        if not req.live_enable:
            return False, "live_enable_guard_active"
        return True, "none"

    def _perform_post(self, *, url: str, token: str, timeout_seconds: float) -> tuple[int, str]:
        http_request = request.Request(
            url=url,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "AION-Lichess-Bot/phase22b40",
            },
        )

        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                return int(response.status), body[:500]
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return int(exc.code), body[:500]
        except Exception as exc:
            return 0, f"{type(exc).__name__}: {exc}"

    def run(
        self,
        *,
        task_name: str = "full_chess_real_lichess_network_move_sender",
        token_env_name: str = "LICHESS_BOT_TOKEN",
        game_id: str = "",
        move: str = "c2c4",
        selected_policy: str = "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT",
        dry_run: bool = True,
        allow_network: bool = False,
        live_enable: bool = False,
        timeout_seconds: float = 10.0,
    ) -> RealLichessMoveSendResult:
        req = self._build_request(
            token_env_name=token_env_name,
            game_id=game_id,
            move=move,
            dry_run=dry_run,
            allow_network=allow_network,
            live_enable=live_enable,
        )

        send_allowed, block_reason = self._guard(req)
        send_attempted = False
        send_success = False
        network_call_performed = False
        http_status: Optional[int] = None
        response_preview = ""

        if send_allowed:
            token = os.environ.get(token_env_name, "")
            send_attempted = True
            network_call_performed = True
            http_status, response_preview = self._perform_post(
                url=req.url,
                token=token,
                timeout_seconds=timeout_seconds,
            )
            send_success = http_status in (200, 201)

        trace_payload = {
            "sender_mode": "guarded_real_lichess_network_move_sender",
            "request": req.to_dict(),
            "selected_policy": selected_policy,
            "send_allowed": send_allowed,
            "send_attempted": send_attempted,
            "send_success": send_success,
            "block_reason": block_reason,
            "http_status": http_status,
            "network_call_performed": network_call_performed,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["send_session_count"] = int(self.policy.get("send_session_count", 0)) + 1
        self.policy["send_allowed_total"] = int(self.policy.get("send_allowed_total", 0)) + (1 if send_allowed else 0)
        self.policy["send_attempted_total"] = int(self.policy.get("send_attempted_total", 0)) + (1 if send_attempted else 0)
        self.policy["send_success_total"] = int(self.policy.get("send_success_total", 0)) + (1 if send_success else 0)
        self.policy["send_blocked_total"] = int(self.policy.get("send_blocked_total", 0)) + (0 if send_allowed else 1)
        self.policy["last_block_reason"] = block_reason
        self.policy["last_game_id"] = req.game_id
        self.policy["last_move"] = req.move
        self.policy["last_http_status"] = http_status
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "token_redacted": req.token_redacted != os.environ.get(token_env_name),
            "bot_api_move_endpoint": "/api/bot/game/{gameId}/move/{move}",
            "dry_run_blocks_by_default": dry_run is True and not send_allowed,
            "missing_game_id_blocks": not bool(req.game_id),
            "network_call_performed": network_call_performed,
            "send_allowed": send_allowed,
            "send_attempted": send_attempted,
            "send_success": send_success,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = RealLichessMoveSendResult(
            kernel_version="phase22b40_full_chess_real_lichess_network_move_sender_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            sender_mode="guarded_real_lichess_network_move_sender",
            request=req.to_dict(),
            selected_bestmove=req.move,
            selected_policy=selected_policy,
            send_allowed=send_allowed,
            send_attempted=send_attempted,
            send_success=send_success,
            block_reason=block_reason,
            http_status=http_status,
            response_preview=response_preview,
            token_guard_active=not req.token_present,
            game_id_guard_active=not bool(req.game_id),
            dry_run_guard_active=req.dry_run,
            network_guard_active=not req.allow_network,
            live_enable_guard_active=not req.live_enable,
            network_call_performed=network_call_performed,
            real_send_trace_hash=trace_hash,
            final_real_send_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This is the guarded real Lichess network move sender for AION. "
                "It can post a move to the Lichess Bot API only when dry_run is false, "
                "a token is present, a game id is present, allow_network is true, and live_enable is true. "
                "Tests mock network sending. Real sending must be used carefully and only on the dedicated BOT account."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_real_lichess_network_move_sender_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_real_lichess_network_move_sender",
    token_env_name: str = "LICHESS_BOT_TOKEN",
    game_id: str = "",
    move: str = "c2c4",
    selected_policy: str = "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT",
    dry_run: bool = True,
    allow_network: bool = False,
    live_enable: bool = False,
    timeout_seconds: float = 10.0,
) -> RealLichessMoveSendResult:
    return AionFullChessRealLichessNetworkMoveSenderKernel(memory_path=memory_path).run(
        task_name=task_name,
        token_env_name=token_env_name,
        game_id=game_id,
        move=move,
        selected_policy=selected_policy,
        dry_run=dry_run,
        allow_network=allow_network,
        live_enable=live_enable,
        timeout_seconds=timeout_seconds,
    )


if __name__ == "__main__":
    result = run_full_chess_real_lichess_network_move_sender_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess real Lichess network move sender memory saved to: {result.memory_path}")
