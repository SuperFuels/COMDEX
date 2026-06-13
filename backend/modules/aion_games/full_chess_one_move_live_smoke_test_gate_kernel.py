from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from .full_chess_live_level2_preflight_checklist_kernel import (
    run_full_chess_live_level2_preflight_checklist_kernel,
)
from .full_chess_guarded_concept_guided_live_sender_gate_kernel import (
    run_full_chess_guarded_concept_guided_live_sender_gate_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_one_move_live_smoke_test_gate_memory.json")


@dataclass(frozen=True)
class OneMoveLiveSmokeTestGateResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    smoke_test_mode: str
    game_id: str
    initial_fen: str
    target_level: int
    selected_move_preview: str
    selected_move_is_legal: bool
    preflight_consumed: bool
    preflight_passed: bool
    preflight_trace_hash: str
    guarded_gate_consumed: bool
    guarded_gate_trace_hash: str
    token_present: bool
    explicit_live_send_authorized: bool
    human_operator_confirmed: bool
    live_game_stream_confirmed: bool
    one_move_limit_enabled: bool
    one_move_gate_enabled: bool
    one_move_gate_passed: bool
    live_lichess_send_enabled: bool
    lichess_move_post_attempted: bool
    send_blocked_by_smoke_gate: bool
    smoke_gate_reason: str
    smoke_gate_conditions: Dict[str, Any]
    smoke_gate_trace_hash: str
    policy_memory_mutated: bool
    final_smoke_gate_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessOneMoveLiveSmokeTestGateKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
        preflight_memory_path: Optional[Path] = None,
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
        self.preflight_memory_path = preflight_memory_path
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
            "one_move_smoke_gate_run_count": 0,
            "one_move_gate_pass_count": 0,
            "one_move_gate_block_count": 0,
            "move_post_attempt_total": 0,
            "last_selected_move_preview": None,
            "last_one_move_gate_passed": False,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("one_move_live_smoke_test_gate_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: OneMoveLiveSmokeTestGateResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e15_one_move_live_smoke_test_gate_memory_v1",
            "task_name": result.task_name,
            "one_move_live_smoke_test_gate_policy": result.final_smoke_gate_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str = "ONE-MOVE-LIVE-SMOKE-TEST-GATE-PREVIEW",
        initial_fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        target_level: int = 2,
        require_token_for_pass: bool = True,
        env_token_name: str = "LICHESS_BOT_TOKEN",
        explicit_live_send_authorized: bool = False,
        human_operator_confirmed: bool = False,
        live_game_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = False,
        task_name: str = "full_chess_one_move_live_smoke_test_gate",
    ) -> OneMoveLiveSmokeTestGateResult:
        token_present = bool(os.environ.get(env_token_name, "").strip())

        preflight = run_full_chess_live_level2_preflight_checklist_kernel(
            memory_path=self.preflight_memory_path,
            gate_memory_path=self.gate_memory_path,
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
            target_level=target_level,
            require_token_for_pass=require_token_for_pass,
            env_token_name=env_token_name,
        )

        guarded_gate = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
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
            explicit_live_send_authorized=explicit_live_send_authorized,
            lichess_token_present=token_present,
            live_game_stream_confirmed=live_game_stream_confirmed,
            human_operator_confirmed=human_operator_confirmed,
        )

        conditions = {
            "target_level_is_2": target_level == 2,
            "preflight_passed": preflight.preflight_passed,
            "selected_move_is_legal": preflight.selected_move_is_legal,
            "token_present": token_present,
            "require_token_for_pass": require_token_for_pass,
            "explicit_live_send_authorized": explicit_live_send_authorized,
            "human_operator_confirmed": human_operator_confirmed,
            "live_game_stream_confirmed": live_game_stream_confirmed,
            "one_move_limit_enabled": True,
            "one_move_gate_enabled": one_move_gate_enabled,
            "guarded_sender_gate_passed": guarded_gate.live_sender_gate_passed,
            "guarded_sender_gate_enabled": guarded_gate.live_sender_gate_enabled,
        }

        one_move_gate_passed = all(
            [
                conditions["target_level_is_2"],
                conditions["preflight_passed"],
                conditions["selected_move_is_legal"],
                token_present,
                explicit_live_send_authorized,
                human_operator_confirmed,
                live_game_stream_confirmed,
                one_move_gate_enabled,
                guarded_gate.live_sender_gate_passed,
            ]
        )

        # Phase 22E.15 never sends. It only proves the one-move smoke-test gate contract.
        live_lichess_send_enabled = False
        lichess_move_post_attempted = False

        if one_move_gate_passed:
            smoke_gate_reason = "One-move gate conditions are satisfied, but Phase 22E.15 keeps send disabled by contract."
            one_move_gate_passed = False
        else:
            smoke_gate_reason = "One-move live smoke test blocked until token, live stream, human confirmation, explicit live flag, and later sender enablement are all present."

        trace_payload = {
            "game_id": game_id,
            "initial_fen": initial_fen,
            "selected_move_preview": preflight.selected_move_preview,
            "conditions": conditions,
            "one_move_gate_passed": one_move_gate_passed,
            "live_lichess_send_enabled": live_lichess_send_enabled,
            "lichess_move_post_attempted": lichess_move_post_attempted,
            "preflight_trace_hash": preflight.preflight_trace_hash,
            "guarded_gate_trace_hash": guarded_gate.gate_trace_hash,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["one_move_smoke_gate_run_count"] = int(self.policy.get("one_move_smoke_gate_run_count", 0)) + 1
        self.policy["one_move_gate_pass_count"] = int(self.policy.get("one_move_gate_pass_count", 0)) + (1 if one_move_gate_passed else 0)
        self.policy["one_move_gate_block_count"] = int(self.policy.get("one_move_gate_block_count", 0)) + (0 if one_move_gate_passed else 1)
        self.policy["move_post_attempt_total"] = int(self.policy.get("move_post_attempt_total", 0)) + 0
        self.policy["last_selected_move_preview"] = preflight.selected_move_preview
        self.policy["last_one_move_gate_passed"] = one_move_gate_passed
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "one_move_live_smoke_test_gate_active": True,
            "preflight_consumed": True,
            "guarded_gate_consumed": True,
            "target_level_is_2": target_level == 2,
            "selected_move_is_legal": preflight.selected_move_is_legal,
            "requires_token": True,
            "requires_explicit_live_send_authorization": True,
            "requires_human_operator_confirmation": True,
            "requires_live_game_stream_confirmation": True,
            "one_move_limit_enabled": True,
            "one_move_gate_enabled": one_move_gate_enabled,
            "one_move_gate_passed": one_move_gate_passed,
            "send_blocked_by_smoke_gate": True,
            "live_lichess_send_enabled": False,
            "lichess_move_post_attempted": False,
            "no_move_post": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = OneMoveLiveSmokeTestGateResult(
            kernel_version="phase22e15_full_chess_one_move_live_smoke_test_gate_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            smoke_test_mode="one_move_live_smoke_test_gate",
            game_id=game_id,
            initial_fen=initial_fen,
            target_level=target_level,
            selected_move_preview=preflight.selected_move_preview,
            selected_move_is_legal=preflight.selected_move_is_legal,
            preflight_consumed=True,
            preflight_passed=preflight.preflight_passed,
            preflight_trace_hash=preflight.preflight_trace_hash,
            guarded_gate_consumed=True,
            guarded_gate_trace_hash=guarded_gate.gate_trace_hash,
            token_present=token_present,
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_limit_enabled=True,
            one_move_gate_enabled=one_move_gate_enabled,
            one_move_gate_passed=one_move_gate_passed,
            live_lichess_send_enabled=live_lichess_send_enabled,
            lichess_move_post_attempted=lichess_move_post_attempted,
            send_blocked_by_smoke_gate=True,
            smoke_gate_reason=smoke_gate_reason,
            smoke_gate_conditions=conditions,
            smoke_gate_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_smoke_gate_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel creates the one-move live smoke test gate. "
                "Phase 22E.15 does not send moves and does not POST to Lichess. "
                "A later phase must separately enable live sending under explicit human confirmation."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_one_move_live_smoke_test_gate_kernel(
    *,
    memory_path: Optional[Path] = None,
    preflight_memory_path: Optional[Path] = None,
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
    game_id: str = "ONE-MOVE-LIVE-SMOKE-TEST-GATE-PREVIEW",
    initial_fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    target_level: int = 2,
    require_token_for_pass: bool = True,
    env_token_name: str = "LICHESS_BOT_TOKEN",
    explicit_live_send_authorized: bool = False,
    human_operator_confirmed: bool = False,
    live_game_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = False,
    task_name: str = "full_chess_one_move_live_smoke_test_gate",
) -> OneMoveLiveSmokeTestGateResult:
    return AionFullChessOneMoveLiveSmokeTestGateKernel(
        memory_path=memory_path,
        preflight_memory_path=preflight_memory_path,
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
        require_token_for_pass=require_token_for_pass,
        env_token_name=env_token_name,
        explicit_live_send_authorized=explicit_live_send_authorized,
        human_operator_confirmed=human_operator_confirmed,
        live_game_stream_confirmed=live_game_stream_confirmed,
        one_move_gate_enabled=one_move_gate_enabled,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_one_move_live_smoke_test_gate_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ One-move live smoke test gate memory saved to: {result.memory_path}")
