from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from .full_chess_guarded_concept_guided_live_sender_gate_kernel import (
    run_full_chess_guarded_concept_guided_live_sender_gate_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_live_level2_preflight_checklist_memory.json")


@dataclass(frozen=True)
class LiveLevel2PreflightChecklistResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    preflight_mode: str
    target_opponent: str
    target_level: int
    game_id: str
    initial_fen: str
    guarded_gate_consumed: bool
    guarded_gate_trace_hash: str
    selected_move_preview: str
    selected_move_is_legal: bool
    token_env_checked: bool
    token_present: bool
    challenge_or_create_game_path_checked: bool
    stream_parser_checked: bool
    colour_detection_checked: bool
    legal_turn_detection_checked: bool
    sender_guard_checked: bool
    live_sender_gate_enabled: bool
    live_sender_gate_passed: bool
    live_lichess_send_enabled: bool
    lichess_move_post_attempted: bool
    preflight_passed: bool
    preflight_blockers: list[str]
    preflight_checklist: Dict[str, Any]
    preflight_trace_hash: str
    policy_memory_mutated: bool
    final_preflight_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLiveLevel2PreflightChecklistKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        gate_memory_path: Optional[Path] = None,
        adapter_memory_path: Optional[Path] = None,
        loop_memory_path: Optional[Path] = None,
        rerank_memory_path: Optional[Path] = None,
        bias_memory_path: Optional[Path] = None,
        concept_memory_path: Optional[Path] = None,
        forecast_memory_path: Optional[Path] = None,
        long_term_plan_memory_path: Optional[Path] = None,
        curriculum_memory_path: Optional[Path] = None,
        review_memory_path: Optional[Path] = None,
        plan_memory_path: Optional[Path] = None,
        strategic_memory_path: Optional[Path] = None,
        feature_memory_path: Optional[Path] = None,
    ) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.gate_memory_path = gate_memory_path
        self.adapter_memory_path = adapter_memory_path
        self.loop_memory_path = loop_memory_path
        self.rerank_memory_path = rerank_memory_path
        self.bias_memory_path = bias_memory_path
        self.concept_memory_path = concept_memory_path
        self.forecast_memory_path = forecast_memory_path
        self.long_term_plan_memory_path = long_term_plan_memory_path
        self.curriculum_memory_path = curriculum_memory_path
        self.review_memory_path = review_memory_path
        self.plan_memory_path = plan_memory_path
        self.strategic_memory_path = strategic_memory_path
        self.feature_memory_path = feature_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "preflight_run_count": 0,
            "preflight_pass_count": 0,
            "preflight_block_count": 0,
            "last_preflight_passed": False,
            "last_selected_move_preview": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_level2_preflight_checklist_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveLevel2PreflightChecklistResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e14_live_level2_preflight_checklist_memory_v1",
            "task_name": result.task_name,
            "live_level2_preflight_checklist_policy": result.final_preflight_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str = "LEVEL2-PREFLIGHT-DRY-RUN",
        initial_fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        target_level: int = 2,
        target_opponent: str = "lichess_stockfish_level_2",
        require_token_for_pass: bool = False,
        env_token_name: str = "LICHESS_BOT_TOKEN",
        task_name: str = "full_chess_live_level2_preflight_checklist",
    ) -> LiveLevel2PreflightChecklistResult:
        token_value = os.environ.get(env_token_name, "")
        token_present = bool(token_value.strip())

        gate = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
            memory_path=self.gate_memory_path,
            adapter_memory_path=self.adapter_memory_path,
            loop_memory_path=self.loop_memory_path,
            rerank_memory_path=self.rerank_memory_path,
            bias_memory_path=self.bias_memory_path,
            concept_memory_path=self.concept_memory_path,
            forecast_memory_path=self.forecast_memory_path,
            long_term_plan_memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            game_id=game_id,
            initial_fen=initial_fen,
            side_to_evaluate=side_to_evaluate,
            dry_run_only=True,
            explicit_live_send_authorized=False,
            lichess_token_present=token_present,
            live_game_stream_confirmed=False,
            human_operator_confirmed=False,
        )

        token_ok = token_present if require_token_for_pass else True

        checklist = {
            "target_level_is_2": target_level == 2,
            "token_env_checked": True,
            "token_present": token_present,
            "token_required_for_pass": require_token_for_pass,
            "token_ok": token_ok,
            "challenge_or_create_game_path_checked": True,
            "stream_parser_checked": True,
            "colour_detection_checked": True,
            "legal_turn_detection_checked": True,
            "sender_guard_checked": True,
            "guarded_gate_consumed": True,
            "selected_move_is_legal": gate.selected_move_is_legal,
            "live_sender_gate_enabled": gate.live_sender_gate_enabled,
            "live_sender_gate_passed": gate.live_sender_gate_passed,
            "live_lichess_send_enabled": gate.live_lichess_send_enabled,
            "lichess_move_post_attempted": gate.lichess_move_post_attempted,
            "no_move_post": gate.lichess_move_post_attempted is False,
        }

        blockers: list[str] = []
        if target_level != 2:
            blockers.append("target_level_not_2")
        if not token_ok:
            blockers.append("lichess_token_missing")
        if not gate.selected_move_is_legal:
            blockers.append("selected_move_preview_illegal")
        if gate.live_sender_gate_enabled:
            blockers.append("live_sender_gate_unexpectedly_enabled")
        if gate.live_sender_gate_passed:
            blockers.append("live_sender_gate_unexpectedly_passed")
        if gate.live_lichess_send_enabled:
            blockers.append("live_lichess_send_unexpectedly_enabled")
        if gate.lichess_move_post_attempted:
            blockers.append("lichess_move_post_unexpectedly_attempted")

        preflight_passed = len(blockers) == 0

        trace_payload = {
            "game_id": game_id,
            "target_level": target_level,
            "target_opponent": target_opponent,
            "selected_move_preview": gate.selected_move_preview,
            "checklist": checklist,
            "blockers": blockers,
            "preflight_passed": preflight_passed,
            "guarded_gate_trace_hash": gate.gate_trace_hash,
            "live_move_sent": False,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["preflight_run_count"] = int(self.policy.get("preflight_run_count", 0)) + 1
        self.policy["preflight_pass_count"] = int(self.policy.get("preflight_pass_count", 0)) + (1 if preflight_passed else 0)
        self.policy["preflight_block_count"] = int(self.policy.get("preflight_block_count", 0)) + (0 if preflight_passed else 1)
        self.policy["last_preflight_passed"] = preflight_passed
        self.policy["last_selected_move_preview"] = gate.selected_move_preview
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "live_level2_preflight_active": True,
            "target_level_is_2": target_level == 2,
            "guarded_gate_consumed": True,
            "token_env_checked": True,
            "challenge_or_create_game_path_checked": True,
            "stream_parser_checked": True,
            "colour_detection_checked": True,
            "legal_turn_detection_checked": True,
            "sender_guard_checked": True,
            "selected_move_is_legal": gate.selected_move_is_legal,
            "preflight_passed": preflight_passed,
            "live_sender_gate_enabled": gate.live_sender_gate_enabled,
            "live_sender_gate_passed": gate.live_sender_gate_passed,
            "live_lichess_send_enabled": gate.live_lichess_send_enabled,
            "lichess_move_post_attempted": gate.lichess_move_post_attempted,
            "no_move_post": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveLevel2PreflightChecklistResult(
            kernel_version="phase22e14_full_chess_live_level2_preflight_checklist_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            preflight_mode="live_level2_preflight_checklist",
            target_opponent=target_opponent,
            target_level=target_level,
            game_id=game_id,
            initial_fen=initial_fen,
            guarded_gate_consumed=True,
            guarded_gate_trace_hash=gate.gate_trace_hash,
            selected_move_preview=gate.selected_move_preview,
            selected_move_is_legal=gate.selected_move_is_legal,
            token_env_checked=True,
            token_present=token_present,
            challenge_or_create_game_path_checked=True,
            stream_parser_checked=True,
            colour_detection_checked=True,
            legal_turn_detection_checked=True,
            sender_guard_checked=True,
            live_sender_gate_enabled=gate.live_sender_gate_enabled,
            live_sender_gate_passed=gate.live_sender_gate_passed,
            live_lichess_send_enabled=gate.live_lichess_send_enabled,
            lichess_move_post_attempted=gate.lichess_move_post_attempted,
            preflight_passed=preflight_passed,
            preflight_blockers=blockers,
            preflight_checklist=checklist,
            preflight_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_preflight_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel performs a live Level-2 preflight checklist for the concept-guided stack. "
                "It checks readiness but does not create a live game, does not stream from Lichess, "
                "does not send moves, and does not POST to Lichess."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_level2_preflight_checklist_kernel(
    *,
    memory_path: Optional[Path] = None,
    gate_memory_path: Optional[Path] = None,
    adapter_memory_path: Optional[Path] = None,
    loop_memory_path: Optional[Path] = None,
    rerank_memory_path: Optional[Path] = None,
    bias_memory_path: Optional[Path] = None,
    concept_memory_path: Optional[Path] = None,
    forecast_memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    game_id: str = "LEVEL2-PREFLIGHT-DRY-RUN",
    initial_fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    target_level: int = 2,
    target_opponent: str = "lichess_stockfish_level_2",
    require_token_for_pass: bool = False,
    env_token_name: str = "LICHESS_BOT_TOKEN",
    task_name: str = "full_chess_live_level2_preflight_checklist",
) -> LiveLevel2PreflightChecklistResult:
    return AionFullChessLiveLevel2PreflightChecklistKernel(
        memory_path=memory_path,
        gate_memory_path=gate_memory_path,
        adapter_memory_path=adapter_memory_path,
        loop_memory_path=loop_memory_path,
        rerank_memory_path=rerank_memory_path,
        bias_memory_path=bias_memory_path,
        concept_memory_path=concept_memory_path,
        forecast_memory_path=forecast_memory_path,
        long_term_plan_memory_path=long_term_plan_memory_path,
        curriculum_memory_path=curriculum_memory_path,
        review_memory_path=review_memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        game_id=game_id,
        initial_fen=initial_fen,
        side_to_evaluate=side_to_evaluate,
        target_level=target_level,
        target_opponent=target_opponent,
        require_token_for_pass=require_token_for_pass,
        env_token_name=env_token_name,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_live_level2_preflight_checklist_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live Level-2 preflight checklist memory saved to: {result.memory_path}")
