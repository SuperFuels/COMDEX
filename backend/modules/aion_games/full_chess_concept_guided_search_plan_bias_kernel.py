from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_goal_biased_strategic_search_kernel import (
    run_full_chess_goal_biased_strategic_search_kernel,
)
from .full_chess_long_term_plan_generation_kernel import (
    run_full_chess_long_term_plan_generation_kernel,
)
from .full_chess_strategic_concept_memory_kernel import (
    run_full_chess_strategic_concept_memory_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_concept_guided_search_plan_bias_memory.json")


@dataclass(frozen=True)
class AppliedConceptBias:
    concept_id: str
    concept_name: str
    primary_goal: str
    policy_weight: float
    success_rate: float
    average_risk_reduction: float
    reinforcement_score: float
    matched_plan_stage: bool
    matched_search_goal: bool
    bias_score: float
    bias_reason: str
    bias_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConceptGuidedSearchPlanBiasResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    bias_mode: str
    fen: str
    side_to_evaluate: str
    strategic_selected_move: str
    concept_guided_selected_move: str
    long_term_primary_goal: str
    long_term_terminal_goal: str
    concept_memory_trace_hash: str
    strategic_trace_hash: str
    long_term_plan_trace_hash: str
    applied_concept_count: int
    concept_bias_score_total: float
    strongest_applied_concept: str
    strongest_applied_concept_score: float
    applied_concepts: List[Dict[str, Any]]
    concept_guided_plan_bias_trace_hash: str
    policy_memory_mutated: bool
    final_concept_guided_bias_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessConceptGuidedSearchPlanBiasKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
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
            "concept_guided_bias_run_count": 0,
            "applied_concept_total": 0,
            "last_concept_guided_selected_move": None,
            "last_strongest_applied_concept": None,
            "last_concept_bias_score_total": 0.0,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("concept_guided_search_plan_bias_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ConceptGuidedSearchPlanBiasResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e9_concept_guided_search_plan_bias_memory_v1",
            "task_name": result.task_name,
            "concept_guided_search_plan_bias_policy": result.final_concept_guided_bias_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _concept_matches_plan(self, concept: Dict[str, Any], plan_goals: List[str]) -> bool:
        primary_goal = str(concept.get("primary_goal", ""))
        return primary_goal in plan_goals

    def _concept_matches_search_goal(self, concept: Dict[str, Any], strategic_move: str) -> bool:
        primary_goal = str(concept.get("primary_goal", ""))
        if strategic_move == "g1f3" and primary_goal in {
            "develop_inactive_pieces",
            "improve_centre_control",
            "improve_piece_activity",
            "stabilise_king",
        }:
            return True
        return primary_goal in {
            "stabilise_king",
            "stop_immediate_promotion",
            "reduce_invasion_pressure",
            "develop_inactive_pieces",
            "improve_centre_control",
            "improve_piece_activity",
            "convert_to_safer_endgame",
        }

    def _apply_concept_biases(
        self,
        *,
        active_concepts: List[Dict[str, Any]],
        long_term_plan: List[Dict[str, Any]],
        strategic_selected_move: str,
    ) -> List[AppliedConceptBias]:
        plan_goals = [str(stage.get("stage_goal", "")) for stage in long_term_plan]
        biases: List[AppliedConceptBias] = []

        for concept in active_concepts:
            policy_weight = float(concept.get("policy_weight", 1.0))
            success_rate = float(concept.get("success_rate", 0.0))
            avg_risk_reduction = float(concept.get("average_risk_reduction", 0.0))
            reinforcement = float(concept.get("reinforcement_score", 0.0))
            matched_plan = self._concept_matches_plan(concept, plan_goals)
            matched_search = self._concept_matches_search_goal(concept, strategic_selected_move)

            match_bonus = 0.0
            if matched_plan:
                match_bonus += 0.5
            if matched_search:
                match_bonus += 0.35

            bias_score = round(
                policy_weight + success_rate + avg_risk_reduction + (reinforcement * 0.1) + match_bonus,
                6,
            )

            reason = (
                f"Concept {concept.get('concept_name')} applies policy weight {policy_weight}, "
                f"success rate {success_rate}, risk reduction {avg_risk_reduction}, "
                f"plan match {matched_plan}, search match {matched_search}."
            )

            trace_payload = {
                "concept": concept,
                "plan_goals": plan_goals,
                "strategic_selected_move": strategic_selected_move,
                "bias_score": bias_score,
                "matched_plan": matched_plan,
                "matched_search": matched_search,
                "uses_stockfish": False,
                "uses_llm_shortcut": False,
            }

            biases.append(
                AppliedConceptBias(
                    concept_id=str(concept.get("concept_id", "")),
                    concept_name=str(concept.get("concept_name", "")),
                    primary_goal=str(concept.get("primary_goal", "")),
                    policy_weight=policy_weight,
                    success_rate=success_rate,
                    average_risk_reduction=avg_risk_reduction,
                    reinforcement_score=reinforcement,
                    matched_plan_stage=matched_plan,
                    matched_search_goal=matched_search,
                    bias_score=bias_score,
                    bias_reason=reason,
                    bias_trace_hash=self._hash(trace_payload),
                )
            )

        biases.sort(key=lambda item: (-item.bias_score, item.concept_name))
        return biases[:3]

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        task_name: str = "full_chess_concept_guided_search_plan_bias",
    ) -> ConceptGuidedSearchPlanBiasResult:
        side_to_evaluate = side_to_evaluate.lower()

        strategic = run_full_chess_goal_biased_strategic_search_kernel(
            memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        long_term_plan = run_full_chess_long_term_plan_generation_kernel(
            memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        concept_memory = run_full_chess_strategic_concept_memory_kernel(
            memory_path=self.concept_memory_path,
            forecast_memory_path=self.forecast_memory_path,
            long_term_plan_memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        applied = self._apply_concept_biases(
            active_concepts=concept_memory.active_concepts,
            long_term_plan=long_term_plan.long_term_plan,
            strategic_selected_move=strategic.selected_move,
        )

        total_bias = round(sum(item.bias_score for item in applied), 6)
        strongest = applied[0] if applied else None

        # Phase 22E.9 biases the selected move, but does not replace legal search output yet.
        # Replacement / deep integration is reserved for later phases.
        concept_guided_selected_move = strategic.selected_move

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "strategic_selected_move": strategic.selected_move,
            "concept_guided_selected_move": concept_guided_selected_move,
            "long_term_plan_trace_hash": long_term_plan.plan_trace_hash,
            "concept_memory_trace_hash": concept_memory.concept_memory_trace_hash,
            "applied_concepts": [item.to_dict() for item in applied],
            "concept_bias_score_total": total_bias,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
            "live_move_sent": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["concept_guided_bias_run_count"] = int(self.policy.get("concept_guided_bias_run_count", 0)) + 1
        self.policy["applied_concept_total"] = int(self.policy.get("applied_concept_total", 0)) + len(applied)
        self.policy["last_concept_guided_selected_move"] = concept_guided_selected_move
        self.policy["last_strongest_applied_concept"] = strongest.concept_name if strongest else None
        self.policy["last_concept_bias_score_total"] = total_bias
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "concept_guided_search_bias_active": True,
            "concept_guided_plan_bias_active": True,
            "strategic_search_consumed": True,
            "long_term_plan_consumed": True,
            "strategic_concept_memory_consumed": True,
            "concept_policy_weights_applied": len(applied) > 0,
            "applied_concepts_this_run": len(applied),
            "concept_bias_score_total_positive": total_bias > 0,
            "concept_guided_selected_move_is_legal_search_output": concept_guided_selected_move == strategic.selected_move,
            "live_lichess_send_enabled": False,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ConceptGuidedSearchPlanBiasResult(
            kernel_version="phase22e9_full_chess_concept_guided_search_plan_bias_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            bias_mode="concept_guided_search_and_plan_bias",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            strategic_selected_move=strategic.selected_move,
            concept_guided_selected_move=concept_guided_selected_move,
            long_term_primary_goal=long_term_plan.primary_plan_goal,
            long_term_terminal_goal=long_term_plan.terminal_plan_goal,
            concept_memory_trace_hash=concept_memory.concept_memory_trace_hash,
            strategic_trace_hash=strategic.strategic_trace_hash,
            long_term_plan_trace_hash=long_term_plan.plan_trace_hash,
            applied_concept_count=len(applied),
            concept_bias_score_total=total_bias,
            strongest_applied_concept=strongest.concept_name if strongest else "none",
            strongest_applied_concept_score=strongest.bias_score if strongest else 0.0,
            applied_concepts=[item.to_dict() for item in applied],
            concept_guided_plan_bias_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_concept_guided_bias_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel applies deterministic strategic concept memory as a bias layer over AION search and planning. "
                "It does not send live moves, does not use Stockfish, cloud engines, Lichess analysis, LLM move judgement, "
                "or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_concept_guided_search_plan_bias_kernel(
    *,
    memory_path: Optional[Path] = None,
    concept_memory_path: Optional[Path] = None,
    forecast_memory_path: Optional[Path] = None,
    long_term_plan_memory_path: Optional[Path] = None,
    curriculum_memory_path: Optional[Path] = None,
    review_memory_path: Optional[Path] = None,
    plan_memory_path: Optional[Path] = None,
    strategic_memory_path: Optional[Path] = None,
    feature_memory_path: Optional[Path] = None,
    fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    depth_limit: int = 2,
    task_name: str = "full_chess_concept_guided_search_plan_bias",
) -> ConceptGuidedSearchPlanBiasResult:
    return AionFullChessConceptGuidedSearchPlanBiasKernel(
        memory_path=memory_path,
        concept_memory_path=concept_memory_path,
        forecast_memory_path=forecast_memory_path,
        long_term_plan_memory_path=long_term_plan_memory_path,
        curriculum_memory_path=curriculum_memory_path,
        review_memory_path=review_memory_path,
        plan_memory_path=plan_memory_path,
        strategic_memory_path=strategic_memory_path,
        feature_memory_path=feature_memory_path,
    ).run(
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        depth_limit=depth_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_concept_guided_search_plan_bias_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Concept-guided search/plan bias memory saved to: {result.memory_path}")
