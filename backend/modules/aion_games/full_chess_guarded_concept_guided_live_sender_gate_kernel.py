from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import chess

from .full_chess_concept_guided_live_lichess_dry_run_adapter_kernel import (
    run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_guarded_concept_guided_live_sender_gate_memory.json")


@dataclass(frozen=True)
class GuardedConceptGuidedLiveSenderGateResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    gate_mode: str
    game_id: str
    initial_fen: str
    selected_move_preview: str
    selected_move_is_legal: bool
    dry_run_adapter_consumed: bool
    dry_run_adapter_trace_hash: str
    dry_run_only: bool
    live_sender_gate_enabled: bool
    live_sender_gate_passed: bool
    live_lichess_send_enabled: bool
    lichess_move_post_attempted: bool
    guard_reason: str
    guard_conditions: Dict[str, Any]
    gate_trace_hash: str
    policy_memory_mutated: bool
    final_live_sender_gate_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessGuardedConceptGuidedLiveSenderGateKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
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
            "live_sender_gate_run_count": 0,
            "gate_pass_count": 0,
            "gate_block_count": 0,
            "move_post_attempt_total": 0,
            "last_selected_move_preview": None,
            "last_gate_passed": False,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("guarded_concept_guided_live_sender_gate_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: GuardedConceptGuidedLiveSenderGateResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e13_guarded_concept_guided_live_sender_gate_memory_v1",
            "task_name": result.task_name,
            "guarded_concept_guided_live_sender_gate_policy": result.final_live_sender_gate_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str = "GUARDED-CONCEPT-GUIDED-LICHESS-GATE-PREVIEW",
        initial_fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        dry_run_only: bool = True,
        explicit_live_send_authorized: bool = False,
        lichess_token_present: bool = False,
        live_game_stream_confirmed: bool = False,
        human_operator_confirmed: bool = False,
        loop_plies: int = 2,
        depth_limit: int = 2,
        candidate_limit: int = 8,
        task_name: str = "full_chess_guarded_concept_guided_live_sender_gate",
    ) -> GuardedConceptGuidedLiveSenderGateResult:
        adapter = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
            memory_path=self.adapter_memory_path,
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
            loop_plies=loop_plies,
            depth_limit=depth_limit,
            candidate_limit=candidate_limit,
        )

        guard_conditions = {
            "selected_move_is_legal": adapter.selected_move_is_legal,
            "dry_run_adapter_consumed": True,
            "dry_run_only": dry_run_only,
            "explicit_live_send_authorized": explicit_live_send_authorized,
            "lichess_token_present": lichess_token_present,
            "live_game_stream_confirmed": live_game_stream_confirmed,
            "human_operator_confirmed": human_operator_confirmed,
            "adapter_no_move_post": adapter.lichess_move_post_attempted is False,
            "adapter_live_send_disabled": adapter.live_lichess_send_enabled is False,
        }

        # Phase 22E.13 intentionally blocks live send by default.
        # A later phase may set these flags true under a separate locked contract.
        live_sender_gate_enabled = False

        live_sender_gate_passed = all(
            [
                guard_conditions["selected_move_is_legal"],
                guard_conditions["dry_run_adapter_consumed"],
                not guard_conditions["dry_run_only"],
                guard_conditions["explicit_live_send_authorized"],
                guard_conditions["lichess_token_present"],
                guard_conditions["live_game_stream_confirmed"],
                guard_conditions["human_operator_confirmed"],
                live_sender_gate_enabled,
            ]
        )

        lichess_move_post_attempted = False
        live_lichess_send_enabled = False

        if live_sender_gate_passed:
            guard_reason = "Gate would permit live send, but Phase 22E.13 keeps live sender disabled by contract."
            live_sender_gate_passed = False
        else:
            guard_reason = "Live send blocked: Phase 22E.13 is a guarded dry-run gate with live sender disabled."

        trace_payload = {
            "game_id": game_id,
            "initial_fen": initial_fen,
            "selected_move_preview": adapter.selected_move_preview,
            "guard_conditions": guard_conditions,
            "live_sender_gate_enabled": live_sender_gate_enabled,
            "live_sender_gate_passed": live_sender_gate_passed,
            "live_lichess_send_enabled": live_lichess_send_enabled,
            "lichess_move_post_attempted": lichess_move_post_attempted,
            "adapter_trace_hash": adapter.adapter_trace_hash,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["live_sender_gate_run_count"] = int(self.policy.get("live_sender_gate_run_count", 0)) + 1
        self.policy["gate_pass_count"] = int(self.policy.get("gate_pass_count", 0)) + (1 if live_sender_gate_passed else 0)
        self.policy["gate_block_count"] = int(self.policy.get("gate_block_count", 0)) + (0 if live_sender_gate_passed else 1)
        self.policy["move_post_attempt_total"] = int(self.policy.get("move_post_attempt_total", 0)) + 0
        self.policy["last_selected_move_preview"] = adapter.selected_move_preview
        self.policy["last_gate_passed"] = live_sender_gate_passed
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "guarded_live_sender_gate_active": True,
            "dry_run_adapter_consumed": True,
            "selected_move_is_legal": adapter.selected_move_is_legal,
            "live_sender_gate_enabled": live_sender_gate_enabled,
            "live_sender_gate_passed": live_sender_gate_passed,
            "live_lichess_send_enabled": live_lichess_send_enabled,
            "lichess_move_post_attempted": lichess_move_post_attempted,
            "no_move_post": True,
            "send_blocked_by_guard": True,
            "requires_explicit_live_send_authorization": True,
            "requires_lichess_token": True,
            "requires_live_game_stream_confirmation": True,
            "requires_human_operator_confirmation": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = GuardedConceptGuidedLiveSenderGateResult(
            kernel_version="phase22e13_full_chess_guarded_concept_guided_live_sender_gate_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            gate_mode="guarded_concept_guided_live_sender_gate",
            game_id=game_id,
            initial_fen=initial_fen,
            selected_move_preview=adapter.selected_move_preview,
            selected_move_is_legal=adapter.selected_move_is_legal,
            dry_run_adapter_consumed=True,
            dry_run_adapter_trace_hash=adapter.adapter_trace_hash,
            dry_run_only=dry_run_only,
            live_sender_gate_enabled=live_sender_gate_enabled,
            live_sender_gate_passed=live_sender_gate_passed,
            live_lichess_send_enabled=live_lichess_send_enabled,
            lichess_move_post_attempted=lichess_move_post_attempted,
            guard_reason=guard_reason,
            guard_conditions=guard_conditions,
            gate_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_live_sender_gate_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel creates the guarded concept-guided live sender gate. "
                "Phase 22E.13 does not send moves, does not POST to Lichess, and keeps live sending disabled. "
                "It does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
    *,
    memory_path: Optional[Path] = None,
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
    game_id: str = "GUARDED-CONCEPT-GUIDED-LICHESS-GATE-PREVIEW",
    initial_fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    dry_run_only: bool = True,
    explicit_live_send_authorized: bool = False,
    lichess_token_present: bool = False,
    live_game_stream_confirmed: bool = False,
    human_operator_confirmed: bool = False,
    loop_plies: int = 2,
    depth_limit: int = 2,
    candidate_limit: int = 8,
    task_name: str = "full_chess_guarded_concept_guided_live_sender_gate",
) -> GuardedConceptGuidedLiveSenderGateResult:
    return AionFullChessGuardedConceptGuidedLiveSenderGateKernel(
        memory_path=memory_path,
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
        dry_run_only=dry_run_only,
        explicit_live_send_authorized=explicit_live_send_authorized,
        lichess_token_present=lichess_token_present,
        live_game_stream_confirmed=live_game_stream_confirmed,
        human_operator_confirmed=human_operator_confirmed,
        loop_plies=loop_plies,
        depth_limit=depth_limit,
        candidate_limit=candidate_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_guarded_concept_guided_live_sender_gate_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Guarded concept-guided live sender gate memory saved to: {result.memory_path}")
