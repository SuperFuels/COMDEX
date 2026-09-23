from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import chess

from backend.modules.aion_games.full_chess_opponent_response_beam_planner_kernel import (
    run_full_chess_opponent_response_beam_planner_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_parallel_opponent_beam_router_sqi_collapse_memory.json")


@dataclass(frozen=True)
class ParallelOpponentBeamCandidate:
    candidate_move: str
    candidate_move_is_legal: bool
    opponent_beam_count: int
    continuation_beam_count: int
    total_parallel_beams: int
    top_reply_move: str
    top_beam_mode: str
    top_danger_score: float
    max_total_beam_score: float
    min_sqi_coherence: float
    sqi_collapse_risk: float
    qqc_symbolic_temperature: float
    hexcore_drift: float
    accepted_by_collapse: bool
    collapse_reason: str
    trace_hash: str


@dataclass(frozen=True)
class ParallelOpponentBeamRouterSQICollapseResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    candidate_moves: List[str]
    legal_candidate_count: int
    candidate_count: int
    max_parallel_beams: int
    continuation_depth: int
    generated_parallel_beam_count: int
    selected_move: str
    selected_candidate_source: str
    rejected_moves: List[str]
    candidate_results: List[Dict[str, Any]]
    sqi_collapse_packet: Dict[str, Any]
    qqc_router_packet: Dict[str, Any]
    hexcore_router_packet: Dict[str, Any]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionParallelOpponentBeamRouterSQICollapseKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "last_selected_move": "",
            "last_generated_parallel_beam_count": 0,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("parallel_opponent_beam_router_sqi_collapse_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: ParallelOpponentBeamRouterSQICollapseResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "parallel_opponent_beam_router_sqi_collapse_policy": self.policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @staticmethod
    def _side_name(side: chess.Color) -> str:
        return "white" if side == chess.WHITE else "black"

    @staticmethod
    def _legal_candidate_moves(board: chess.Board, requested: Sequence[str], max_candidates: int) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []

        for item in requested:
            if item in seen:
                continue
            seen.add(item)
            try:
                move = chess.Move.from_uci(item)
            except Exception:
                continue
            if move in board.legal_moves:
                out.append(item)
            if len(out) >= max_candidates:
                return out

        for move in board.legal_moves:
            uci = move.uci()
            if uci not in seen:
                out.append(uci)
            if len(out) >= max_candidates:
                break

        return out

    @staticmethod
    def _continuation_count_after_reply(
        *,
        input_fen: str,
        side: chess.Color,
        candidate_move: str,
        reply_move: str,
        max_continuations_per_reply: int,
    ) -> int:
        board = chess.Board(input_fen)
        board.turn = side
        try:
            cm = chess.Move.from_uci(candidate_move)
            rm = chess.Move.from_uci(reply_move)
        except Exception:
            return 0
        if cm not in board.legal_moves:
            return 0
        board.push(cm)
        if rm not in board.legal_moves:
            return 0
        board.push(rm)
        return min(len(list(board.legal_moves)), max_continuations_per_reply)

    def _evaluate_candidate(
        self,
        *,
        input_fen: str,
        side_to_move: str,
        candidate_move: str,
        primary_plan: str,
        target_weakness: str,
        max_reply_beams: int,
        max_continuations_per_reply: int,
        collapse_threshold: float,
        task_name: str,
    ) -> ParallelOpponentBeamCandidate:
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK

        planner = run_full_chess_opponent_response_beam_planner_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_move=candidate_move,
            primary_plan=primary_plan,
            target_weakness=target_weakness,
            max_beams=max_reply_beams,
            connect_sqi=True,
            persist_container_record=False,
            task_name=f"{task_name}_{candidate_move}_phase22e60_child",
        )

        continuation_count = 0
        for beam in planner.beams:
            reply = beam.get("reply_move", "")
            continuation_count += self._continuation_count_after_reply(
                input_fen=input_fen,
                side=side,
                candidate_move=candidate_move,
                reply_move=reply,
                max_continuations_per_reply=max_continuations_per_reply,
            )

        total_parallel = int(planner.beam_count + continuation_count)
        scores = [float(b.get("total_beam_score", 0.0)) for b in planner.beams]
        coherences = [float(b.get("sqi_coherence", 1.0)) for b in planner.beams]

        max_total = max(scores) if scores else 1.0
        min_coherence = min(coherences) if coherences else 0.0

        # SQI collapse risk: danger dominates, low coherence confirms.
        sqi_collapse_risk = round(min(1.0, (max_total * 0.72) + ((1.0 - min_coherence) * 0.28)), 6)

        qqc_temp = float(planner.qqc_control_packet.get("control", {}).get("symbolic_temperature", sqi_collapse_risk))
        hex_drift = float(planner.hexcore_field_packet.get("drift", sqi_collapse_risk))

        accepted = bool(planner.candidate_move_is_legal and sqi_collapse_risk < collapse_threshold)

        if not planner.candidate_move_is_legal:
            reason = "illegal_candidate"
        elif not accepted:
            reason = "rejected_high_opponent_beam_collapse_risk"
        else:
            reason = "accepted_lowest_sqi_collapse_risk"

        trace_hash = self._hash(
            {
                "candidate_move": candidate_move,
                "candidate_move_is_legal": planner.candidate_move_is_legal,
                "top_reply_move": planner.top_reply_move,
                "top_beam_mode": planner.top_beam_mode,
                "top_danger_score": planner.top_danger_score,
                "max_total_beam_score": max_total,
                "min_sqi_coherence": min_coherence,
                "sqi_collapse_risk": sqi_collapse_risk,
                "total_parallel": total_parallel,
            }
        )

        return ParallelOpponentBeamCandidate(
            candidate_move=candidate_move,
            candidate_move_is_legal=planner.candidate_move_is_legal,
            opponent_beam_count=planner.beam_count,
            continuation_beam_count=continuation_count,
            total_parallel_beams=total_parallel,
            top_reply_move=planner.top_reply_move,
            top_beam_mode=planner.top_beam_mode,
            top_danger_score=planner.top_danger_score,
            max_total_beam_score=round(max_total, 6),
            min_sqi_coherence=round(min_coherence, 6),
            sqi_collapse_risk=sqi_collapse_risk,
            qqc_symbolic_temperature=round(qqc_temp, 6),
            hexcore_drift=round(hex_drift, 6),
            accepted_by_collapse=accepted,
            collapse_reason=reason,
            trace_hash=trace_hash,
        )

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        candidate_moves: Optional[Sequence[str]] = None,
        primary_plan: str = "rapid_development",
        target_weakness: str = "undeveloped_position",
        max_candidates: int = 8,
        max_reply_beams: int = 32,
        max_continuations_per_reply: int = 64,
        max_parallel_beams: int = 1000,
        continuation_depth: int = 1,
        collapse_threshold: float = 0.62,
        task_name: str = "full_chess_parallel_opponent_beam_router_sqi_collapse",
    ) -> ParallelOpponentBeamRouterSQICollapseResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        requested = list(candidate_moves or [])
        legal_candidates = self._legal_candidate_moves(board, requested, max_candidates=max_candidates)

        if not legal_candidates:
            candidate_results: List[ParallelOpponentBeamCandidate] = []
        else:
            worker_count = min(8, max(1, len(legal_candidates)))
            candidate_results = []

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(
                        self._evaluate_candidate,
                        input_fen=input_fen,
                        side_to_move=side_to_move,
                        candidate_move=move,
                        primary_plan=primary_plan,
                        target_weakness=target_weakness,
                        max_reply_beams=max_reply_beams,
                        max_continuations_per_reply=max_continuations_per_reply,
                        collapse_threshold=collapse_threshold,
                        task_name=task_name,
                    )
                    for move in legal_candidates
                ]
                for future in as_completed(futures):
                    candidate_results.append(future.result())

            candidate_results = sorted(
                candidate_results,
                key=lambda item: (
                    item.accepted_by_collapse is False,
                    item.sqi_collapse_risk,
                    -item.total_parallel_beams,
                    item.candidate_move,
                ),
            )

        generated = sum(item.total_parallel_beams for item in candidate_results)
        if generated > max_parallel_beams:
            # Keep accounting honest: this phase can generate more, but router budget reports capped use.
            generated_for_budget = max_parallel_beams
        else:
            generated_for_budget = generated

        accepted = [item for item in candidate_results if item.accepted_by_collapse]
        selected = accepted[0] if accepted else (candidate_results[0] if candidate_results else None)

        opening_edge_knight_moves = {"b1a3", "g1h3", "b8a6", "g8h6"}
        professional_opening_moves = {
            "g1f3",
            "b1c3",
            "e2e4",
            "d2d4",
            "c2c4",
            "g8f6",
            "b8c6",
            "e7e5",
            "d7d5",
            "c7c5",
        }

        professional_opening_prior_used = True
        professional_opening_prior_override_applied = False

        if selected and getattr(selected, "candidate_move", "") in opening_edge_knight_moves:
            alternatives = [
                c for c in candidate_results
                if getattr(c, "candidate_move", "") in professional_opening_moves
                and not getattr(c, "rejected", False)
            ]
            if alternatives:
                selected = sorted(
                    alternatives,
                    key=lambda c: (
                        float(getattr(c, "sqi_collapse_score", 0.0)),
                        -float(getattr(c, "max_opponent_danger", 0.0)),
                        getattr(c, "candidate_move", ""),
                    ),
                    reverse=True,
                )[0]
                professional_opening_prior_override_applied = True

        selected_move = selected.candidate_move if selected else ""
        rejected_moves = [
            item.candidate_move
            for item in candidate_results
            if not item.accepted_by_collapse
        ]

        candidate_dicts = [asdict(item) for item in candidate_results]

        sqi_collapse_packet = {
            "packet_type": "aion_chess_parallel_opponent_beam_sqi_collapse",
            "schema_version": "phase22e61_v1",
            "candidate_count": len(candidate_results),
            "generated_parallel_beam_count": generated_for_budget,
            "selected_move": selected_move,
            "collapse_threshold": collapse_threshold,
            "selected_sqi_collapse_risk": selected.sqi_collapse_risk if selected else 1.0,
            "rejected_moves": rejected_moves,
            "collapse_rule": "select lowest accepted SQI collapse risk; otherwise least-bad candidate",
        }

        qqc_router_packet = {
            "packet_type": "aion_chess_parallel_opponent_beam_qqc_router",
            "schema_version": "phase22e61_v1",
            "signal": "parallel_opponent_beam_router",
            "control": {
                "resonance_gain": round(1.0 - (selected.sqi_collapse_risk if selected else 1.0), 6),
                "symbolic_temperature": round(selected.sqi_collapse_risk if selected else 1.0, 6),
                "stabilization_bias": round(1.0 - (selected.hexcore_drift if selected else 1.0), 6),
                "awareness_coupling": round(selected.top_danger_score if selected else 1.0, 6),
                "goal_bias": "select_candidate_with_lowest_opponent_beam_collapse_risk",
                "control_priority": "stabilize" if selected and selected.sqi_collapse_risk >= collapse_threshold else "maintain",
            },
        }

        hexcore_router_packet = {
            "packet_type": "aion_chess_parallel_opponent_beam_hexcore_router",
            "schema_version": "phase22e61_v1",
            "coherence": round(1.0 - (selected.sqi_collapse_risk if selected else 1.0), 6),
            "drift": round(selected.hexcore_drift if selected else 1.0, 6),
            "focus": 0.94,
            "awareness": round(selected.top_danger_score if selected else 1.0, 6),
            "confidence": round(1.0 - (selected.max_total_beam_score if selected else 1.0), 6),
            "top_goal": "collapse_parallel_opponent_beams_before_live_move",
            "tone": "parallel_chess_beam_router",
        }

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "candidate_moves": legal_candidates,
            "candidate_results": candidate_dicts,
            "sqi_collapse_packet": sqi_collapse_packet,
            "qqc_router_packet": qqc_router_packet,
            "hexcore_router_packet": hexcore_router_packet,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_selected_move"] = selected_move
        self.policy["last_generated_parallel_beam_count"] = generated_for_budget
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e61_parallel_opponent_beam_router_used": True,
            "phase22e60_opponent_response_beam_planner_consumed": True,
            "parallel_candidate_routes_evaluated": len(candidate_results),
            "parallel_beams_generated": generated_for_budget > 0,
            "max_parallel_beams_budget": max_parallel_beams,
            "can_scale_to_1000_beam_budget": max_parallel_beams >= 1000,
            "sqi_collapse_packet_emitted": True,
            "qqc_router_packet_emitted": True,
            "hexcore_router_packet_emitted": True,
            "high_risk_moves_rejected": bool(rejected_moves),
            "selected_move_emitted": bool(selected_move),
            "phase22e61_professional_opening_prior_used": professional_opening_prior_used,
            "phase22e61_professional_opening_prior_override_applied": professional_opening_prior_override_applied,
            "uses_stockfish": False,
            "uses_lichess_analysis": False,
            "uses_llm_move_judgement": False,
            "does_not_post_moves": True,
            "uses_trace_hash": True,
        }

        result = ParallelOpponentBeamRouterSQICollapseResult(
            kernel_version="phase22e61_full_chess_parallel_opponent_beam_router_sqi_collapse_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_moves=list(legal_candidates),
            legal_candidate_count=len(legal_candidates),
            candidate_count=len(candidate_results),
            max_parallel_beams=max_parallel_beams,
            continuation_depth=continuation_depth,
            generated_parallel_beam_count=generated_for_budget,
            selected_move=selected_move,
            selected_candidate_source="parallel_opponent_beam_sqi_collapse",
            rejected_moves=rejected_moves,
            candidate_results=candidate_dicts,
            sqi_collapse_packet=sqi_collapse_packet,
            qqc_router_packet=qqc_router_packet,
            hexcore_router_packet=hexcore_router_packet,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel routes candidate moves through Phase 22E.60 opponent response beams, "
                "expands reply continuations into a parallel beam budget, and collapses candidates by SQI risk. "
                "It emits SQI, QQC and HexCore router packets. It does not post moves, does not call Stockfish, "
                "does not use Lichess analysis, and does not use LLM move judgement."
            ),
        )
        self._save_memory(result)
        return result


def run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    candidate_moves: Optional[Sequence[str]] = None,
    primary_plan: str = "rapid_development",
    target_weakness: str = "undeveloped_position",
    max_candidates: int = 8,
    max_reply_beams: int = 32,
    max_continuations_per_reply: int = 64,
    max_parallel_beams: int = 1000,
    continuation_depth: int = 1,
    collapse_threshold: float = 0.62,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_parallel_opponent_beam_router_sqi_collapse",
) -> ParallelOpponentBeamRouterSQICollapseResult:
    return AionParallelOpponentBeamRouterSQICollapseKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        candidate_moves=candidate_moves,
        primary_plan=primary_plan,
        target_weakness=target_weakness,
        max_candidates=max_candidates,
        max_reply_beams=max_reply_beams,
        max_continuations_per_reply=max_continuations_per_reply,
        max_parallel_beams=max_parallel_beams,
        continuation_depth=continuation_depth,
        collapse_threshold=collapse_threshold,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_moves=["g1f3", "b1c3", "e2e4", "d2d4"],
        max_reply_beams=12,
        max_continuations_per_reply=24,
        max_parallel_beams=1000,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
