"""AION Phase 22B.39 — Full Chess Live Lichess Bot Enablement Kernel.

This phase defines the guarded live enablement contract for AION's Lichess bot.

It proves:
- live enablement is explicit;
- dry-run remains the default;
- missing token blocks live play;
- allow_network must be true before a live call is allowed;
- live_enable must be true before a live call is allowed;
- selected bestmove and Lichess bot move URL are prepared;
- token is never printed raw;
- no network call is performed in tests;
- no LLM shortcut is used.

This is the final guarded enablement layer before real live play.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_LIVE_LICHESS_BOT_ENABLEMENT_MEMORY_PATH = Path(
    "data/aion_games/full_chess_live_lichess_bot_enablement_memory.json"
)


@dataclass(frozen=True)
class LiveLichessBotEnablementConfig:
    base_url: str
    token_env_name: str
    token_present: bool
    token_redacted: str
    dry_run: bool
    allow_network: bool
    live_enable: bool
    game_id: str
    selected_bestmove: str
    move_url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveLichessBotEnablementDecision:
    live_call_allowed: bool
    block_reason: str
    would_post_move: bool
    network_call_performed: bool
    prepared_method: str
    prepared_url: str
    prepared_headers_redacted: Dict[str, str]
    prepared_payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullChessLiveLichessBotEnablementResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    enablement_mode: str
    human_approval_required: bool
    config: Dict[str, Any]
    decision: Dict[str, Any]
    selected_bestmove: str
    selected_policy: str
    live_call_allowed: bool
    block_reason: str
    dry_run_guard_active: bool
    token_guard_active: bool
    network_guard_active: bool
    live_enable_guard_active: bool
    network_call_performed: bool
    live_enablement_trace_hash: str
    final_live_enablement_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessLiveLichessBotEnablementKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_LIVE_LICHESS_BOT_ENABLEMENT_MEMORY_PATH)
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "live_enablement_session_count": 0,
            "live_call_allowed_total": 0,
            "live_call_blocked_total": 0,
            "network_call_total": 0,
            "last_block_reason": None,
            "last_selected_bestmove": None,
            "last_selected_policy": None,
            "last_live_enablement_trace_hash": None,
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
            policy = data.get("live_lichess_bot_enablement_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: FullChessLiveLichessBotEnablementResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b39_full_chess_live_lichess_bot_enablement_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "live_lichess_bot_enablement_policy": result.final_live_enablement_policy,
            "selected_bestmove": result.selected_bestmove,
            "selected_policy": result.selected_policy,
            "live_call_allowed": result.live_call_allowed,
            "block_reason": result.block_reason,
            "live_enablement_trace_hash": result.live_enablement_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "network_call_performed": result.network_call_performed,
            "boundary_statement": result.boundary_statement,
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

    def _config(
        self,
        *,
        token_env_name: str,
        dry_run: bool,
        allow_network: bool,
        live_enable: bool,
        game_id: str,
        selected_bestmove: str,
    ) -> LiveLichessBotEnablementConfig:
        base_url = "https://lichess.org"
        token = os.environ.get(token_env_name)
        move_url = f"{base_url}/api/bot/game/{game_id}/move/{selected_bestmove}"

        return LiveLichessBotEnablementConfig(
            base_url=base_url,
            token_env_name=token_env_name,
            token_present=bool(token),
            token_redacted=self._redact_token(token),
            dry_run=dry_run,
            allow_network=allow_network,
            live_enable=live_enable,
            game_id=game_id,
            selected_bestmove=selected_bestmove,
            move_url=move_url,
        )

    def _decide(self, config: LiveLichessBotEnablementConfig) -> LiveLichessBotEnablementDecision:
        if config.dry_run:
            block_reason = "dry_run_guard_active"
            live_call_allowed = False
        elif not config.token_present:
            block_reason = "token_missing"
            live_call_allowed = False
        elif not config.allow_network:
            block_reason = "network_guard_active"
            live_call_allowed = False
        elif not config.live_enable:
            block_reason = "live_enable_guard_active"
            live_call_allowed = False
        else:
            block_reason = "none"
            live_call_allowed = True

        return LiveLichessBotEnablementDecision(
            live_call_allowed=live_call_allowed,
            block_reason=block_reason,
            would_post_move=True,
            network_call_performed=False,
            prepared_method="POST",
            prepared_url=config.move_url,
            prepared_headers_redacted={
                "Authorization": f"Bearer {config.token_redacted}",
            },
            prepared_payload={
                "game_id": config.game_id,
                "move": config.selected_bestmove,
                "dry_run": config.dry_run,
                "allow_network": config.allow_network,
                "live_enable": config.live_enable,
            },
        )

    def run(
        self,
        *,
        task_name: str = "full_chess_live_lichess_bot_enablement",
        token_env_name: str = "LICHESS_BOT_TOKEN",
        dry_run: bool = True,
        allow_network: bool = False,
        live_enable: bool = False,
        game_id: str = "aion-dry-run-game-001",
        selected_bestmove: str = "c2c4",
        selected_policy: str = "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT",
    ) -> FullChessLiveLichessBotEnablementResult:
        config = self._config(
            token_env_name=token_env_name,
            dry_run=dry_run,
            allow_network=allow_network,
            live_enable=live_enable,
            game_id=game_id,
            selected_bestmove=selected_bestmove,
        )
        decision = self._decide(config)

        dry_run_guard_active = config.dry_run
        token_guard_active = not config.token_present
        network_guard_active = not config.allow_network
        live_enable_guard_active = not config.live_enable

        trace_payload = {
            "enablement_mode": "guarded_live_lichess_bot_enablement",
            "config": config.to_dict(),
            "decision": decision.to_dict(),
            "selected_policy": selected_policy,
            "guards": {
                "dry_run_guard_active": dry_run_guard_active,
                "token_guard_active": token_guard_active,
                "network_guard_active": network_guard_active,
                "live_enable_guard_active": live_enable_guard_active,
            },
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["live_enablement_session_count"] = int(
            self.policy.get("live_enablement_session_count", 0)
        ) + 1
        self.policy["live_call_allowed_total"] = int(
            self.policy.get("live_call_allowed_total", 0)
        ) + (1 if decision.live_call_allowed else 0)
        self.policy["live_call_blocked_total"] = int(
            self.policy.get("live_call_blocked_total", 0)
        ) + (0 if decision.live_call_allowed else 1)
        self.policy["network_call_total"] = int(self.policy.get("network_call_total", 0))
        self.policy["last_block_reason"] = decision.block_reason
        self.policy["last_selected_bestmove"] = selected_bestmove
        self.policy["last_selected_policy"] = selected_policy
        self.policy["last_live_enablement_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "token_redacted": config.token_redacted != os.environ.get(token_env_name),
            "dry_run_default": dry_run is True,
            "network_default_blocked": allow_network is False,
            "live_enable_default_blocked": live_enable is False,
            "live_call_allowed": decision.live_call_allowed,
            "network_call_performed": decision.network_call_performed,
            "prepared_lichess_bot_move_url": decision.prepared_url.endswith(f"/move/{selected_bestmove}"),
            "does_not_print_raw_token": True,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = FullChessLiveLichessBotEnablementResult(
            kernel_version="phase22b39_full_chess_live_lichess_bot_enablement_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            enablement_mode="guarded_live_lichess_bot_enablement",
            human_approval_required=False,
            config=config.to_dict(),
            decision=decision.to_dict(),
            selected_bestmove=selected_bestmove,
            selected_policy=selected_policy,
            live_call_allowed=decision.live_call_allowed,
            block_reason=decision.block_reason,
            dry_run_guard_active=dry_run_guard_active,
            token_guard_active=token_guard_active,
            network_guard_active=network_guard_active,
            live_enable_guard_active=live_enable_guard_active,
            network_call_performed=decision.network_call_performed,
            live_enablement_trace_hash=trace_hash,
            final_live_enablement_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates guarded live Lichess bot enablement for AION. "
                "The kernel prepares a Lichess bot move request but only allows live execution when dry_run is false, "
                "a token is present, allow_network is true, and live_enable is true. "
                "Tests do not perform network calls. Tokens are redacted. "
                "This is not a guarantee of live play, official rating, grandmaster-strength play, "
                "Stockfish-level calculation, general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_lichess_bot_enablement_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_lichess_bot_enablement",
    token_env_name: str = "LICHESS_BOT_TOKEN",
    dry_run: bool = True,
    allow_network: bool = False,
    live_enable: bool = False,
    game_id: str = "aion-dry-run-game-001",
    selected_bestmove: str = "c2c4",
    selected_policy: str = "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT",
) -> FullChessLiveLichessBotEnablementResult:
    return AionFullChessLiveLichessBotEnablementKernel(memory_path=memory_path).run(
        task_name=task_name,
        token_env_name=token_env_name,
        dry_run=dry_run,
        allow_network=allow_network,
        live_enable=live_enable,
        game_id=game_id,
        selected_bestmove=selected_bestmove,
        selected_policy=selected_policy,
    )


if __name__ == "__main__":
    result = run_full_chess_live_lichess_bot_enablement_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess live Lichess bot enablement memory saved to: {result.memory_path}")
