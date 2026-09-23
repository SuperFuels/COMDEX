from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_concept_guided_search_plan_bias_kernel import (
    run_full_chess_concept_guided_search_plan_bias_kernel,
)
from .full_chess_goal_biased_strategic_search_kernel import (
    run_full_chess_goal_biased_strategic_search_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_concept_guided_move_reranking_memory.json")


@dataclass(frozen=True)
class ConceptRerankedMove:
    move_uci: str
    base_rank: int
    reranked_rank: int
    base_score: float
    concept_bias_score: float
    final_score: float
    applied_concepts: List[str]
    is_original_strategic_move: bool
    is_capture: bool
    gives_check: bool
    is_castle: bool
    rerank_reason: str
    rerank_trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConceptGuidedMoveRerankingResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    rerank_mode: str
    fen: str
    side_to_evaluate: str
    original_strategic_selected_move: str
    concept_guided_selected_move: str
    selected_move_changed_by_rerank: bool
    legal_candidate_count: int
    reranked_candidate_count: int
    applied_concept_count: int
    concept_bias_score_total: float
    top_reranked_moves: List[Dict[str, Any]]
    concept_guided_bias_trace_hash: str
    move_rerank_trace_hash: str
    policy_memory_mutated: bool
    final_move_reranking_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessConceptGuidedMoveRerankingKernel:
    def __init__(
        self,
        memory_path: Optional[Path] = None,
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
            "move_reranking_run_count": 0,
            "reranked_move_total": 0,
            "selected_move_change_count": 0,
            "last_original_strategic_selected_move": None,
            "last_concept_guided_selected_move": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("concept_guided_move_reranking_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ConceptGuidedMoveRerankingResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e10_concept_guided_move_reranking_memory_v1",
            "task_name": result.task_name,
            "concept_guided_move_reranking_policy": result.final_move_reranking_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _base_move_score(self, board: chess.Board, move: chess.Move, base_rank: int, original_move: str) -> float:
        score = 100.0 - float(base_rank)

        if move.uci() == original_move:
            score += 10.0
        if board.is_capture(move):
            score += 2.5
        if board.gives_check(move):
            score += 3.0
        if board.is_castling(move):
            score += 4.0

        # Mild deterministic opening heuristics without engine analysis.
        uci = move.uci()
        if uci in {"g1f3", "b1c3", "e2e4", "d2d4", "c2c4"}:
            score += 4.0
        if uci in {"g8f6", "b8c6", "e7e5", "d7d5", "c7c5"}:
            score += 4.0

        return round(score, 6)

    def _concept_move_match(self, move_uci: str, concept: Dict[str, Any]) -> float:
        concept_id = str(concept.get("concept_id", ""))
        primary_goal = str(concept.get("primary_goal", ""))

        development_moves = {"g1f3", "b1c3", "g8f6", "b8c6"}
        centre_moves = {"e2e4", "d2d4", "c2c4", "e7e5", "d7d5", "c7c5"}
        king_safety_moves = {"e1g1", "e1c1", "e8g8", "e8c8", "g1f3", "g8f6"}
        activity_moves = development_moves | centre_moves

        if primary_goal == "develop_inactive_pieces" and move_uci in development_moves:
            return 1.0
        if primary_goal == "improve_centre_control" and move_uci in centre_moves:
            return 1.0
        if primary_goal == "improve_piece_activity" and move_uci in activity_moves:
            return 0.8
        if primary_goal == "stabilise_king" and move_uci in king_safety_moves:
            return 0.7
        if primary_goal == "convert_to_safer_endgame":
            return 0.25
        if "PROMOTION_DEFENCE" in concept_id:
            return 0.4
        if "INVASION_PRESSURE" in concept_id:
            return 0.4

        return 0.0

    def _rerank_moves(
        self,
        *,
        board: chess.Board,
        strategic_candidates: List[Any],
        original_move: str,
        applied_concepts: List[Dict[str, Any]],
    ) -> List[ConceptRerankedMove]:
        legal_moves = list(board.legal_moves)
        strategic_order = [str(getattr(item, "move_uci", "")) for item in strategic_candidates]
        if not strategic_order:
            strategic_order = [move.uci() for move in legal_moves]

        ranked: List[ConceptRerankedMove] = []

        for idx, move in enumerate(legal_moves, start=1):
            move_uci = move.uci()
            base_rank = strategic_order.index(move_uci) + 1 if move_uci in strategic_order else idx
            base_score = self._base_move_score(board, move, base_rank, original_move)

            concept_bias = 0.0
            matched_concepts: List[str] = []
            for concept in applied_concepts:
                match = self._concept_move_match(move_uci, concept)
                if match <= 0:
                    continue
                bias = (
                    float(concept.get("bias_score", 0.0))
                    * float(concept.get("policy_weight", 1.0))
                    * match
                )
                concept_bias += bias
                matched_concepts.append(str(concept.get("concept_id", "")))

            final_score = round(base_score + concept_bias, 6)

            trace_payload = {
                "move_uci": move_uci,
                "base_rank": base_rank,
                "base_score": base_score,
                "concept_bias_score": round(concept_bias, 6),
                "final_score": final_score,
                "applied_concepts": matched_concepts,
                "original_move": original_move,
                "uses_stockfish": False,
                "uses_llm_shortcut": False,
            }

            ranked.append(
                ConceptRerankedMove(
                    move_uci=move_uci,
                    base_rank=base_rank,
                    reranked_rank=0,
                    base_score=base_score,
                    concept_bias_score=round(concept_bias, 6),
                    final_score=final_score,
                    applied_concepts=matched_concepts,
                    is_original_strategic_move=move_uci == original_move,
                    is_capture=board.is_capture(move),
                    gives_check=board.gives_check(move),
                    is_castle=board.is_castling(move),
                    rerank_reason=(
                        f"Move {move_uci} base score {base_score} plus concept bias "
                        f"{round(concept_bias, 6)} gives final score {final_score}."
                    ),
                    rerank_trace_hash=self._hash(trace_payload),
                )
            )

        ranked.sort(key=lambda item: (-item.final_score, item.move_uci))

        final_ranked: List[ConceptRerankedMove] = []
        for rank, item in enumerate(ranked, start=1):
            final_ranked.append(
                ConceptRerankedMove(
                    move_uci=item.move_uci,
                    base_rank=item.base_rank,
                    reranked_rank=rank,
                    base_score=item.base_score,
                    concept_bias_score=item.concept_bias_score,
                    final_score=item.final_score,
                    applied_concepts=item.applied_concepts,
                    is_original_strategic_move=item.is_original_strategic_move,
                    is_capture=item.is_capture,
                    gives_check=item.gives_check,
                    is_castle=item.is_castle,
                    rerank_reason=item.rerank_reason,
                    rerank_trace_hash=item.rerank_trace_hash,
                )
            )

        return final_ranked

    def run(
        self,
        *,
        fen: str = chess.STARTING_FEN,
        side_to_evaluate: str = "white",
        depth_limit: int = 2,
        candidate_limit: int = 8,
        task_name: str = "full_chess_concept_guided_move_reranking",
    ) -> ConceptGuidedMoveRerankingResult:
        side_to_evaluate = side_to_evaluate.lower()
        board = chess.Board(fen)

        strategic = run_full_chess_goal_biased_strategic_search_kernel(
            memory_path=self.strategic_memory_path,
            feature_memory_path=self.feature_memory_path,
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            depth_limit=depth_limit,
        )

        bias = run_full_chess_concept_guided_search_plan_bias_kernel(
            memory_path=self.bias_memory_path,
            concept_memory_path=self.concept_memory_path,
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

        reranked = self._rerank_moves(
            board=board,
            strategic_candidates=getattr(strategic, "candidates", []),
            original_move=strategic.selected_move,
            applied_concepts=bias.applied_concepts,
        )

        top = reranked[:candidate_limit]
        selected = top[0].move_uci if top else strategic.selected_move
        changed = selected != strategic.selected_move

        trace_payload = {
            "fen": fen,
            "side_to_evaluate": side_to_evaluate,
            "original_strategic_selected_move": strategic.selected_move,
            "concept_guided_selected_move": selected,
            "top_reranked_moves": [item.to_dict() for item in top],
            "concept_guided_bias_trace_hash": bias.concept_guided_plan_bias_trace_hash,
            "live_move_sent": False,
            "uses_stockfish": False,
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["move_reranking_run_count"] = int(self.policy.get("move_reranking_run_count", 0)) + 1
        self.policy["reranked_move_total"] = int(self.policy.get("reranked_move_total", 0)) + len(reranked)
        self.policy["selected_move_change_count"] = int(self.policy.get("selected_move_change_count", 0)) + (1 if changed else 0)
        self.policy["last_original_strategic_selected_move"] = strategic.selected_move
        self.policy["last_concept_guided_selected_move"] = selected
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "concept_guided_move_reranking_active": True,
            "concept_guided_search_plan_bias_consumed": True,
            "strategic_search_consumed": True,
            "legal_candidates_reranked": len(reranked) == board.legal_moves.count(),
            "concept_bias_applied_to_candidate_moves": any(item.concept_bias_score > 0 for item in reranked),
            "concept_guided_selected_move_is_legal": chess.Move.from_uci(selected) in board.legal_moves,
            "live_lichess_send_enabled": False,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = ConceptGuidedMoveRerankingResult(
            kernel_version="phase22e10_full_chess_concept_guided_move_reranking_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            rerank_mode="concept_guided_move_reranking",
            fen=fen,
            side_to_evaluate=side_to_evaluate,
            original_strategic_selected_move=strategic.selected_move,
            concept_guided_selected_move=selected,
            selected_move_changed_by_rerank=changed,
            legal_candidate_count=board.legal_moves.count(),
            reranked_candidate_count=len(reranked),
            applied_concept_count=bias.applied_concept_count,
            concept_bias_score_total=bias.concept_bias_score_total,
            top_reranked_moves=[item.to_dict() for item in top],
            concept_guided_bias_trace_hash=bias.concept_guided_plan_bias_trace_hash,
            move_rerank_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_move_reranking_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel re-ranks legal candidate moves using deterministic strategic concept bias. "
                "It does not send live moves, does not use Stockfish, cloud engines, Lichess analysis, "
                "LLM move judgement, or human move scoring."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_concept_guided_move_reranking_kernel(
    *,
    memory_path: Optional[Path] = None,
    bias_memory_path: Optional[Path] = None,
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
    candidate_limit: int = 8,
    task_name: str = "full_chess_concept_guided_move_reranking",
) -> ConceptGuidedMoveRerankingResult:
    return AionFullChessConceptGuidedMoveRerankingKernel(
        memory_path=memory_path,
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
        fen=fen,
        side_to_evaluate=side_to_evaluate,
        depth_limit=depth_limit,
        candidate_limit=candidate_limit,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_concept_guided_move_reranking_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Concept-guided move re-ranking memory saved to: {result.memory_path}")
