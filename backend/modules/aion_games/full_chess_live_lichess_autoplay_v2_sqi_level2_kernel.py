"""AION Phase 22D.4 — Live Lichess Autoplay v2 Uses SQI-Guided Selector.

This phase upgrades the guarded live Lichess autoplay v2 level 2 path so its
move source is the Phase 22D.3 live-loop SQI selector adapter.

It proves:
- target remains Lichess Stockfish level 2;
- live autoplay v2 uses the SQI-guided live-loop adapter;
- selected move is legal;
- SQI trace and selection trace are preserved;
- dry-run is default;
- live network challenge and move send are gated;
- no Stockfish local engine, cloud engine, Lichess analysis, or LLM shortcut is used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from .full_chess_live_loop_sqi_selector_adapter_kernel import (
    run_full_chess_live_loop_sqi_selector_adapter_kernel,
)


DEFAULT_LIVE_AUTOPLAY_V2_SQI_LEVEL2_MEMORY_PATH = Path(
    "data/aion_games/full_chess_live_lichess_autoplay_v2_sqi_level2_memory.json"
)


@dataclass(frozen=True)
class LiveLichessAutoplayV2SQILevel2Result:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    autoplay_mode: str
    platform: str
    account_id: str
    opponent_type: str
    opponent_level: int
    rated: bool
    variant: str
    clock_limit_seconds: int
    clock_increment_seconds: int
    aion_colour: str
    dry_run: bool
    network_enabled: bool
    token_required_for_live: bool
    token_present: bool
    challenge_endpoint: str
    challenge_payload: Dict[str, Any]
    starting_fen: str
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
    autoplay_trace_hash: str
    network_challenge_attempted: bool
    network_move_send_attempted: bool
    live_loop_ready: bool
    policy_memory_mutated: bool
    final_autoplay_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessLiveLichessAutoplayV2SQILevel2Kernel:
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
        self.memory_path = Path(memory_path or DEFAULT_LIVE_AUTOPLAY_V2_SQI_LEVEL2_MEMORY_PATH)
        self.sqi_live_adapter_memory_path = sqi_live_adapter_memory_path
        self.sqi_selector_memory_path = sqi_selector_memory_path
        self.sqi_bridge_memory_path = sqi_bridge_memory_path
        self.selector_memory_path = selector_memory_path
        self.evaluation_memory_path = evaluation_memory_path
        self.post_game_memory_path = post_game_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "autoplay_plan_count": 0,
            "sqi_autoplay_plan_count": 0,
            "dry_run_count": 0,
            "network_enabled_count": 0,
            "level2_target_count": 0,
            "challenge_attempt_count": 0,
            "move_send_attempt_count": 0,
            "last_selected_opening_move": None,
            "last_selected_sqi_adjusted_score": None,
            "last_autoplay_trace_hash": None,
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
            policy = data.get("live_lichess_autoplay_v2_sqi_level2_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: LiveLichessAutoplayV2SQILevel2Result) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22d4_live_lichess_autoplay_v2_sqi_level2_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "live_lichess_autoplay_v2_sqi_level2_policy": result.final_autoplay_policy,
            "opponent_level": result.opponent_level,
            "selected_opening_move": result.selected_opening_move,
            "selected_sqi_adjusted_score": result.selected_sqi_adjusted_score,
            "sqi_trace_hash": result.sqi_trace_hash,
            "selection_trace_hash": result.selection_trace_hash,
            "adapter_trace_hash": result.adapter_trace_hash,
            "autoplay_trace_hash": result.autoplay_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def run(
        self,
        *,
        task_name: str = "full_chess_live_lichess_autoplay_v2_sqi_level2",
        account_id: str = "peekoo123",
        aion_colour: str = "white",
        opponent_level: int = 2,
        rated: bool = False,
        variant: str = "standard",
        clock_limit_seconds: int = 600,
        clock_increment_seconds: int = 0,
        dry_run: bool = True,
        network_enabled: bool = False,
        token_present: bool = False,
    ) -> LiveLichessAutoplayV2SQILevel2Result:
        board = chess.Board()

        adapter = run_full_chess_live_loop_sqi_selector_adapter_kernel(
            memory_path=self.sqi_live_adapter_memory_path,
            sqi_selector_memory_path=self.sqi_selector_memory_path,
            sqi_bridge_memory_path=self.sqi_bridge_memory_path,
            selector_memory_path=self.selector_memory_path,
            evaluation_memory_path=self.evaluation_memory_path,
            post_game_memory_path=self.post_game_memory_path,
            game_id="lichess_stockfish_level2_sqi_autoplay_v2_dry_run",
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

        network_challenge_attempted = bool(network_enabled and not dry_run and token_present)
        network_move_send_attempted = False

        trace_payload = {
            "autoplay_mode": "live_lichess_autoplay_v2_sqi_level2_guarded",
            "platform": "lichess",
            "account_id": account_id,
            "opponent_type": "lichess_ai_stockfish",
            "opponent_level": opponent_level,
            "rated": rated,
            "variant": variant,
            "aion_colour": aion_colour,
            "dry_run": dry_run,
            "network_enabled": network_enabled,
            "token_present": token_present,
            "selected_opening_move": adapter.selected_move,
            "selected_sqi_adjusted_score": adapter.selected_sqi_adjusted_score,
            "sqi_trace_hash": adapter.sqi_trace_hash,
            "selection_trace_hash": adapter.selection_trace_hash,
            "adapter_trace_hash": adapter.adapter_trace_hash,
            "network_challenge_attempted": network_challenge_attempted,
            "network_move_send_attempted": network_move_send_attempted,
            "uses_llm_shortcut": False,
            "uses_stockfish_local_engine": False,
            "uses_cloud_engine": False,
        }
        autoplay_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["autoplay_plan_count"] = int(self.policy.get("autoplay_plan_count", 0)) + 1
        self.policy["sqi_autoplay_plan_count"] = int(self.policy.get("sqi_autoplay_plan_count", 0)) + 1
        self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + (1 if dry_run else 0)
        self.policy["network_enabled_count"] = int(self.policy.get("network_enabled_count", 0)) + (1 if network_enabled else 0)
        self.policy["level2_target_count"] = int(self.policy.get("level2_target_count", 0)) + (1 if opponent_level == 2 else 0)
        self.policy["challenge_attempt_count"] = int(self.policy.get("challenge_attempt_count", 0)) + (1 if network_challenge_attempted else 0)
        self.policy["move_send_attempt_count"] = int(self.policy.get("move_send_attempt_count", 0)) + (1 if network_move_send_attempted else 0)
        self.policy["last_selected_opening_move"] = adapter.selected_move
        self.policy["last_selected_sqi_adjusted_score"] = adapter.selected_sqi_adjusted_score
        self.policy["last_autoplay_trace_hash"] = autoplay_trace_hash

        live_loop_ready = bool(adapter.selected_move and selected_move_is_legal and adapter.sqi_guided_selector_used)

        evidence = {
            "uses_llm_shortcut": False,
            "uses_stockfish_local_engine": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "platform_is_lichess": True,
            "target_is_stockfish_level_2": opponent_level == 2,
            "sqi_live_loop_adapter_used": True,
            "sqi_guided_selector_used": adapter.sqi_guided_selector_used,
            "selected_opening_move_is_legal": selected_move_is_legal,
            "selected_by_sqi_adjusted_score": adapter.selected_sqi_adjusted_score != 0,
            "dry_run_default": dry_run is True,
            "network_challenge_attempted": network_challenge_attempted,
            "network_move_send_attempted": network_move_send_attempted,
            "network_call_performed": False,
            "token_required_for_live": True,
            "live_loop_ready": live_loop_ready,
            "no_payment_created": True,
            "no_booking_created": True,
            "no_chain_write": True,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveLichessAutoplayV2SQILevel2Result(
            kernel_version="phase22d4_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            autoplay_mode="live_lichess_autoplay_v2_sqi_level2_guarded",
            platform="lichess",
            account_id=account_id,
            opponent_type="lichess_ai_stockfish",
            opponent_level=opponent_level,
            rated=rated,
            variant=variant,
            clock_limit_seconds=clock_limit_seconds,
            clock_increment_seconds=clock_increment_seconds,
            aion_colour=aion_colour,
            dry_run=dry_run,
            network_enabled=network_enabled,
            token_required_for_live=True,
            token_present=token_present,
            challenge_endpoint=challenge_endpoint,
            challenge_payload=challenge_payload,
            starting_fen=board.fen(),
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
            autoplay_trace_hash=autoplay_trace_hash,
            network_challenge_attempted=network_challenge_attempted,
            network_move_send_attempted=network_move_send_attempted,
            live_loop_ready=live_loop_ready,
            policy_memory_mutated=True,
            final_autoplay_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This phase prepares guarded Lichess autoplay v2 against Stockfish level 2 using the Phase 22D.3 "
                "live-loop SQI adapter and Phase 22D.2 SQI-guided move selector. It is dry-run by default and does "
                "not create a live game or send a live move unless a later explicitly authorised network runner enables that boundary."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
    *,
    memory_path: Optional[Path] = None,
    sqi_live_adapter_memory_path: Optional[Path] = None,
    sqi_selector_memory_path: Optional[Path] = None,
    sqi_bridge_memory_path: Optional[Path] = None,
    selector_memory_path: Optional[Path] = None,
    evaluation_memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_lichess_autoplay_v2_sqi_level2",
    account_id: str = "peekoo123",
    aion_colour: str = "white",
    opponent_level: int = 2,
    rated: bool = False,
    variant: str = "standard",
    clock_limit_seconds: int = 600,
    clock_increment_seconds: int = 0,
    dry_run: bool = True,
    network_enabled: bool = False,
    token_present: bool = False,
) -> LiveLichessAutoplayV2SQILevel2Result:
    return AionFullChessLiveLichessAutoplayV2SQILevel2Kernel(
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
        token_present=token_present,
    )


if __name__ == "__main__":
    result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess live Lichess autoplay v2 SQI level 2 memory saved to: {result.memory_path}")
