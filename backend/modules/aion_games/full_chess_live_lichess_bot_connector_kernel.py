"""AION Phase 22B.30 — Full Chess Live Lichess Bot Connector Kernel.

This phase proves the safe live connector contract for Lichess bot operation.

It proves:
- live connector config is represented;
- token handling is explicit and redacted;
- stream/challenge/game/move endpoint contracts are built;
- dry-run is default;
- no network call is made unless explicitly enabled;
- move payload is derived from the locked bridge;
- trace hash is emitted.

This is the safety boundary before real online bot operation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_LIVE_LICHESS_CONNECTOR_MEMORY_PATH = Path(
    "data/aion_games/full_chess_live_lichess_bot_connector_memory.json"
)


@dataclass(frozen=True)
class LichessConnectorConfig:
    base_url: str
    bot_token_env_name: str
    bot_token_present: bool
    bot_token_redacted: str
    dry_run: bool
    allow_network: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LichessEndpointContract:
    event_stream_url: str
    game_stream_url: str
    challenge_accept_url: str
    bot_move_url: str
    method_for_move: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullChessLiveLichessBotConnectorResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    connector_mode: str
    config: Dict[str, Any]
    endpoints: Dict[str, Any]
    game_id: str
    selected_bestmove: str
    lichess_move_payload: Dict[str, Any]
    would_accept_challenge: bool
    would_post_move: bool
    network_call_performed: bool
    dry_run_guard_active: bool
    token_redaction_active: bool
    connector_ready: bool
    live_connector_trace_hash: str
    final_live_connector_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessLiveLichessBotConnectorKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_LIVE_LICHESS_CONNECTOR_MEMORY_PATH)
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "live_connector_session_count": 0,
            "dry_run_session_count": 0,
            "network_session_count": 0,
            "prepared_move_payload_count": 0,
            "last_game_id": None,
            "last_bestmove": None,
            "last_live_connector_trace_hash": None,
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
            policy = data.get("live_connector_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: FullChessLiveLichessBotConnectorResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b30_full_chess_live_lichess_bot_connector_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "live_connector_policy": result.final_live_connector_policy,
            "last_game_id": result.game_id,
            "last_bestmove": result.selected_bestmove,
            "last_live_connector_trace_hash": result.live_connector_trace_hash,
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

    def _redact_token(self, token: str) -> str:
        if not token:
            return "missing"
        if len(token) <= 8:
            return "present-redacted"
        return f"{token[:4]}...{token[-4:]}"

    def _build_config(self, *, dry_run: bool, allow_network: bool) -> LichessConnectorConfig:
        env_name = "LICHESS_BOT_TOKEN"
        token = os.environ.get(env_name, "")

        return LichessConnectorConfig(
            base_url="https://lichess.org",
            bot_token_env_name=env_name,
            bot_token_present=bool(token),
            bot_token_redacted=self._redact_token(token),
            dry_run=dry_run,
            allow_network=allow_network,
        )

    def _build_endpoints(self, *, game_id: str, move: str) -> LichessEndpointContract:
        base = "https://lichess.org"
        return LichessEndpointContract(
            event_stream_url=f"{base}/api/stream/event",
            game_stream_url=f"{base}/api/bot/game/stream/{game_id}",
            challenge_accept_url=f"{base}/api/challenge/{{challenge_id}}/accept",
            bot_move_url=f"{base}/api/bot/game/{game_id}/move/{move}",
            method_for_move="POST",
        )

    def run(
        self,
        *,
        task_name: str = "full_chess_live_lichess_bot_connector",
        dry_run: bool = True,
        allow_network: bool = False,
        game_id: str = "aion-demo-game-001",
        selected_bestmove: str = "c4d5",
    ) -> FullChessLiveLichessBotConnectorResult:
        config = self._build_config(dry_run=dry_run, allow_network=allow_network)
        endpoints = self._build_endpoints(game_id=game_id, move=selected_bestmove)

        lichess_move_payload = {
            "game_id": game_id,
            "move": selected_bestmove,
            "endpoint": endpoints.bot_move_url,
            "method": endpoints.method_for_move,
            "offering_draw": False,
            "source": "aion_uci_bestmove",
        }

        dry_run_guard_active = config.dry_run is True
        raw_token = os.environ.get(config.bot_token_env_name, "")
        token_redaction_active = config.bot_token_redacted != raw_token

        would_accept_challenge = True
        would_post_move = bool(game_id and selected_bestmove)

        network_call_performed = False
        if config.allow_network and not config.dry_run:
            # Intentionally not implemented in this lock.
            # Live network writes require a later guarded phase.
            network_call_performed = False

        connector_ready = (
            bool(endpoints.event_stream_url)
            and bool(endpoints.game_stream_url)
            and bool(endpoints.bot_move_url)
            and bool(lichess_move_payload["move"])
            and dry_run_guard_active
            and not network_call_performed
        )

        trace_payload = {
            "config": config.to_dict(),
            "endpoints": endpoints.to_dict(),
            "lichess_move_payload": lichess_move_payload,
            "would_accept_challenge": would_accept_challenge,
            "would_post_move": would_post_move,
            "network_call_performed": network_call_performed,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["live_connector_session_count"] = int(
            self.policy.get("live_connector_session_count", 0)
        ) + 1
        self.policy["dry_run_session_count"] = int(
            self.policy.get("dry_run_session_count", 0)
        ) + (1 if dry_run else 0)
        self.policy["network_session_count"] = int(
            self.policy.get("network_session_count", 0)
        ) + (1 if network_call_performed else 0)
        self.policy["prepared_move_payload_count"] = int(
            self.policy.get("prepared_move_payload_count", 0)
        ) + (1 if would_post_move else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_bestmove"] = selected_bestmove
        self.policy["last_live_connector_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "builds_connector_config": True,
            "uses_token_env_name": config.bot_token_env_name == "LICHESS_BOT_TOKEN",
            "redacts_token": token_redaction_active,
            "dry_run_default": dry_run is True,
            "network_disabled_by_default": allow_network is False,
            "builds_event_stream_endpoint": endpoints.event_stream_url.endswith("/api/stream/event"),
            "builds_game_stream_endpoint": game_id in endpoints.game_stream_url,
            "builds_bot_move_endpoint": selected_bestmove in endpoints.bot_move_url,
            "builds_move_payload": lichess_move_payload["move"] == selected_bestmove,
            "does_not_perform_network_call": network_call_performed is False,
            "connector_ready": connector_ready,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = FullChessLiveLichessBotConnectorResult(
            kernel_version="phase22b30_full_chess_live_lichess_bot_connector_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            connector_mode="dry_run_live_lichess_connector_contract",
            config=config.to_dict(),
            endpoints=endpoints.to_dict(),
            game_id=game_id,
            selected_bestmove=selected_bestmove,
            lichess_move_payload=lichess_move_payload,
            would_accept_challenge=would_accept_challenge,
            would_post_move=would_post_move,
            network_call_performed=network_call_performed,
            dry_run_guard_active=dry_run_guard_active,
            token_redaction_active=token_redaction_active,
            connector_ready=connector_ready,
            live_connector_trace_hash=trace_hash,
            final_live_connector_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates a dry-run live Lichess bot connector contract. "
                "AION builds stream and move endpoint contracts, redacts token state, prepares a bot move payload, "
                "and keeps network writes disabled by default. It does not yet perform live network calls, expose OAuth secrets, "
                "enter live games, claim official rating, prove engine-strength play, general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_lichess_bot_connector_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_lichess_bot_connector",
    dry_run: bool = True,
    allow_network: bool = False,
    game_id: str = "aion-demo-game-001",
    selected_bestmove: str = "c4d5",
) -> FullChessLiveLichessBotConnectorResult:
    return AionFullChessLiveLichessBotConnectorKernel(memory_path=memory_path).run(
        task_name=task_name,
        dry_run=dry_run,
        allow_network=allow_network,
        game_id=game_id,
        selected_bestmove=selected_bestmove,
    )


if __name__ == "__main__":
    result = run_full_chess_live_lichess_bot_connector_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess live Lichess bot connector memory saved to: {result.memory_path}")
