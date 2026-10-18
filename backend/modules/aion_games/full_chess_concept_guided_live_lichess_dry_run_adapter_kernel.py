from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_concept_guided_move_reranking_kernel import (
    run_full_chess_concept_guided_move_reranking_kernel,
)
from .full_chess_local_concept_guided_game_loop_kernel import (
    run_full_chess_local_concept_guided_game_loop_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_concept_guided_live_lichess_dry_run_adapter_memory.json")


@dataclass(frozen=True)
class ConceptGuidedLiveDryRunPreview:
    preview_index: int
    game_id: str
    fen: str
    side_to_move: str
    selected_move: str
    original_strategic_selected_move: str
    selected_move_changed_by_rerank: bool
    selected_move_is_legal: bool
    applied_concept_count: int
    concept_bias_score_total: float
    dry_run_only: bool
    live_lichess_send_enabled: bool
    lichess_move_post_attempted: bool
    adapter_route: str
    preview_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConceptGuidedLiveLichessDryRunAdapterResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    adapter_mode: str
    dry_run_only: bool
    game_id: str
    initial_fen: str
    side_to_evaluate: str
    selected_move_preview: str
    original_strategic_selected_move: str
    selected_move_changed_by_rerank: bool
    selected_move_is_legal: bool
    local_loop_preview_consumed: bool
    local_loop_plies_completed: int
    local_loop_trace_hash: str
    applied_concept_count: int
    concept_bias_score_total: float
    dry_run_previews: List[Dict[str, Any]]
    live_lichess_send_enabled: bool
    lichess_move_post_attempted: bool
    adapter_trace_hash: str
    policy_memory_mutated: bool
    final_dry_run_adapter_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessConceptGuidedLiveLichessDryRunAdapterKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
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
            "dry_run_adapter_run_count": 0,
            "preview_total": 0,
            "move_post_attempt_total": 0,
            "last_selected_move_preview": None,
            "last_game_id": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("concept_guided_live_lichess_dry_run_adapter_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ConceptGuidedLiveLichessDryRunAdapterResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e12_concept_guided_live_lichess_dry_run_adapter_memory_v1",
            "task_name": result.task_name,
            "concept_guided_live_lichess_dry_run_adapter_policy": result.final_dry_run_adapter_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def run(
        self,
        *,
        game_id: str = "DRYRUN-CONCEPT-GUIDED-LICHESS-PREVIEW",
        initial_fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        loop_plies: int = 2,
        depth_limit: int = 2,
        candidate_limit: int = 8,
        task_name: str = "full_chess_concept_guided_live_lichess_dry_run_adapter",
    ) -> ConceptGuidedLiveLichessDryRunAdapterResult:
        side_to_evaluate = side_to_evaluate.lower()
        board = chess.Board(initial_fen)

        rerank = run_full_chess_concept_guided_move_reranking_kernel(
            memory_path=self.rerank_memory_path,
            bias_memory_path=self.bias_memory_path,
            concept_memory_path=self.concept_memory_path,
            forecast_memory_path=self.forecast_memory_path,
            long_term_plan_memory_path=self.long_term_plan_memory_path,
            curriculum_memory_path=self.curriculum_memory_path,
            review_memory_path=self.review_memory_path,
            plan_memory_path=self.plan_memory_path,
            strategic_memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=initial_fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
            candidate_limit=candidate_limit,
        )

        selected_move = rerank.concept_guided_selected_move
        selected_move_is_legal = chess.Move.from_uci(selected_move) in board.legal_moves

        local_loop = run_full_chess_local_concept_guided_game_loop_kernel(
            memory_path=self.loop_memory_path,
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
            initial_fen=initial_fen,
            plies=loop_plies,
            depth_limit=depth_limit,
            candidate_limit=candidate_limit,
        )

        preview_payload = {
            "preview_index": 1,
            "game_id": game_id,
            "fen": initial_fen,
            "side_to_move": side_to_evaluate,
            "selected_move": selected_move,
            "original_strategic_selected_move": rerank.original_strategic_selected_move,
            "selected_move_changed_by_rerank": rerank.selected_move_changed_by_rerank,
            "selected_move_is_legal": selected_move_is_legal,
            "applied_concept_count": rerank.applied_concept_count,
            "concept_bias_score_total": rerank.concept_bias_score_total,
            "dry_run_only": True,
            "live_lichess_send_enabled": False,
            "lichess_move_post_attempted": False,
            "adapter_route": "preview_only_no_post",
        }

        preview = ConceptGuidedLiveDryRunPreview(
            **preview_payload,
            preview_trace_hash=self._hash(preview_payload),
        )

        trace_payload = {
            "game_id": game_id,
            "initial_fen": initial_fen,
            "side_to_evaluate": side_to_evaluate,
            "selected_move_preview": selected_move,
            "selected_move_is_legal": selected_move_is_legal,
            "rerank_trace_hash": rerank.move_rerank_trace_hash,
            "local_loop_trace_hash": local_loop.game_loop_trace_hash,
            "dry_run_previews": [preview.to_dict()],
            "dry_run_only": True,
            "live_lichess_send_enabled": False,
            "lichess_move_post_attempted": False,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["dry_run_adapter_run_count"] = int(self.policy.get("dry_run_adapter_run_count", 0)) + 1
        self.policy["preview_total"] = int(self.policy.get("preview_total", 0)) + 1
        self.policy["move_post_attempt_total"] = int(self.policy.get("move_post_attempt_total", 0)) + 0
        self.policy["last_selected_move_preview"] = selected_move
        self.policy["last_game_id"] = game_id
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "concept_guided_live_adapter_dry_run_active": True,
            "dry_run_only": True,
            "selected_move_preview_only": True,
            "concept_guided_reranking_consumed": True,
            "local_concept_guided_loop_consumed": True,
            "selected_move_is_legal": selected_move_is_legal,
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

        result = ConceptGuidedLiveLichessDryRunAdapterResult(
            kernel_version="phase22e12_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            adapter_mode="concept_guided_live_lichess_dry_run_adapter",
            dry_run_only=True,
            game_id=game_id,
            initial_fen=initial_fen,
            side_to_evaluate=side_to_evaluate,
            selected_move_preview=selected_move,
            original_strategic_selected_move=rerank.original_strategic_selected_move,
            selected_move_changed_by_rerank=rerank.selected_move_changed_by_rerank,
            selected_move_is_legal=selected_move_is_legal,
            local_loop_preview_consumed=True,
            local_loop_plies_completed=local_loop.plies_completed,
            local_loop_trace_hash=local_loop.game_loop_trace_hash,
            applied_concept_count=rerank.applied_concept_count,
            concept_bias_score_total=rerank.concept_bias_score_total,
            dry_run_previews=[preview.to_dict()],
            live_lichess_send_enabled=False,
            lichess_move_post_attempted=False,
            adapter_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_dry_run_adapter_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel adapts concept-guided move selection to a live-Lichess-shaped dry-run preview. "
                "It does not send moves, does not POST to Lichess, does not use Stockfish, cloud engines, "
                "Lichess analysis, LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
    *,
    memory_path: Optional[Path] = None,
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
    game_id: str = "DRYRUN-CONCEPT-GUIDED-LICHESS-PREVIEW",
    initial_fen: str = chess.STARTING_FEN,
    side_to_evaluate: str = "white",
    loop_plies: int = 2,
    depth_limit: int = 2,
    candidate_limit: int = 8,
    task_name: str = "full_chess_concept_guided_live_lichess_dry_run_adapter",
) -> ConceptGuidedLiveLichessDryRunAdapterResult:
    return AionFullChessConceptGuidedLiveLichessDryRunAdapterKernel(
        memory_path=memory_path,
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
        loop_plies=loop_plies,
        depth_limit=depth_limit,
        candidate_limit=candidate_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Concept-guided live Lichess dry-run adapter memory saved to: {result.memory_path}")
