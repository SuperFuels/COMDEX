from __future__ import annotations

import glob
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_REVIEW_PATH = Path("data/aion_games/full_chess_level2_strategic_well_live_post_game_review_memory.json")


@dataclass(frozen=True)
class StrategicWellLivePostGameReviewResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    source_path: str
    game_id: str
    final_status: str
    final_winner: str
    final_ply_count: int
    aion_move_count: int
    move_send_ok_count: int
    post_400_recovery_count: int
    opening_correction_confirmed: bool
    first_base_well_move: str
    first_selected_move: str
    h2h4_returned_later: bool
    h2h4_return_ply: int
    non_queen_promotion_detected: bool
    non_queen_promotion_move: str
    passed_pawn_scope_too_broad: bool
    endgame_repetition_detected: bool
    draw_conversion_failure: bool
    failure_map: Dict[str, Any]
    recommended_next_phases: List[str]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionStrategicWellLivePostGameReviewKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_REVIEW_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "last_game_id": "",
            "last_final_status": "",
            "last_trace_hash": None,
            "reviewed_game_count": 0,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_well_live_post_game_review_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicWellLivePostGameReviewResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e40_strategic_well_live_post_game_review_memory_v1",
            "task_name": result.task_name,
            "strategic_well_live_post_game_review_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _latest_22e39_source(self) -> Path:
        candidates = []
        candidates.extend(glob.glob("data/aion_games/full_chess_level2_strategic_well_live_rematch_memory.json"))
        candidates.extend(glob.glob("data/aion_games/full_chess_level2_22e39*.json"))
        candidates = [p for p in candidates if Path(p).exists()]
        if not candidates:
            raise FileNotFoundError("No 22E.39 live rematch memory/source file found.")
        return Path(max(candidates, key=lambda p: Path(p).stat().st_mtime))

    def _extract_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(payload.get("last_result"), dict):
            return payload["last_result"]
        return payload

    def run(
        self,
        *,
        source_path: Optional[Path] = None,
        task_name: str = "full_chess_level2_strategic_well_live_post_game_review",
    ) -> StrategicWellLivePostGameReviewResult:
        src = Path(source_path) if source_path else self._latest_22e39_source()
        payload = json.loads(src.read_text(encoding="utf-8"))
        result_payload = self._extract_result(payload)

        game_id = str(result_payload.get("game_id", ""))
        final_status = str(result_payload.get("final_status", ""))
        final_winner = str(result_payload.get("final_winner", ""))
        final_moves = list(result_payload.get("final_moves", []) or [])
        move_records = list(result_payload.get("move_records", []) or [])

        first_base_well_move = str(result_payload.get("first_base_well_move", ""))
        first_selected_move = str(result_payload.get("first_selected_move", ""))
        opening_correction_confirmed = first_base_well_move == "h2h4" and first_selected_move == "g1f3"

        h2h4_return_ply = 0
        for record in move_records:
            if record.get("selected_move") == "h2h4" or record.get("final_selected_move") == "h2h4":
                ply = int(record.get("ply_before", 0))
                if ply > 0:
                    h2h4_return_ply = ply
                    break

        non_queen_promotion_move = ""
        for move in final_moves:
            if len(move) == 5 and move[-1] in {"r", "b", "n"}:
                non_queen_promotion_move = move
                break

        convert_records = [
            r for r in move_records
            if str(r.get("active_intent", "")) == "convert_passed_pawn"
        ]

        passed_pawn_non_progress = [
            str(r.get("selected_move") or r.get("final_selected_move") or "")
            for r in convert_records
            if str(r.get("selected_move") or r.get("final_selected_move") or "") not in {"", non_queen_promotion_move}
            and not (
                len(str(r.get("selected_move") or r.get("final_selected_move") or "")) == 5
                or str(r.get("selected_move") or r.get("final_selected_move") or "")[1:2] in {"7", "2"}
                or str(r.get("selected_move") or r.get("final_selected_move") or "")[2:3] in {"7", "2", "8", "1"}
            )
        ]

        rook_loop_moves = ["b7b8", "b8b7", "b7a7", "a7b7"]
        endgame_repetition_detected = any(m in final_moves for m in rook_loop_moves) and final_status == "draw"

        h2h4_returned_later = h2h4_return_ply > 0
        non_queen_promotion_detected = bool(non_queen_promotion_move)
        passed_pawn_scope_too_broad = len(passed_pawn_non_progress) >= 3
        draw_conversion_failure = final_status == "draw" and (
            len(convert_records) >= 10 or endgame_repetition_detected
        )

        failure_map = {
            "opening": {
                "status": "improved",
                "first_base_well_move": first_base_well_move,
                "first_selected_move": first_selected_move,
                "opening_correction_confirmed": opening_correction_confirmed,
            },
            "midgame": {
                "status": "needs_guard",
                "h2h4_returned_later": h2h4_returned_later,
                "h2h4_return_ply": h2h4_return_ply,
                "problem": "opening drift guard is not broad enough after intent switches to initiative_pressure",
            },
            "promotion": {
                "status": "needs_fix",
                "non_queen_promotion_detected": non_queen_promotion_detected,
                "non_queen_promotion_move": non_queen_promotion_move,
                "problem": "promotion should default to queen unless underpromotion is proven necessary",
            },
            "passed_pawn": {
                "status": "needs_scope_guard",
                "convert_passed_pawn_record_count": len(convert_records),
                "passed_pawn_scope_too_broad": passed_pawn_scope_too_broad,
                "non_progress_examples": passed_pawn_non_progress[:12],
            },
            "endgame": {
                "status": "needs_conversion_guard",
                "endgame_repetition_detected": endgame_repetition_detected,
                "draw_conversion_failure": draw_conversion_failure,
                "problem": "endgame repeated rook/piece moves instead of forcing conversion",
            },
        }

        recommended_next_phases = [
            "22E.41 — Promotion Choice Fix: Queen First Unless Proven Otherwise",
            "22E.42 — Passed Pawn Intent Scope Guard",
            "22E.43 — Anti-Shuffling / Endgame Conversion Guard",
            "22E.44 — Proactive Intent Primacy & Plan Enforcement",
        ]

        trace_payload = {
            "game_id": game_id,
            "final_status": final_status,
            "first_selected_move": first_selected_move,
            "h2h4_returned_later": h2h4_returned_later,
            "non_queen_promotion_move": non_queen_promotion_move,
            "passed_pawn_scope_too_broad": passed_pawn_scope_too_broad,
            "endgame_repetition_detected": endgame_repetition_detected,
            "draw_conversion_failure": draw_conversion_failure,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["reviewed_game_count"] = int(self.policy.get("reviewed_game_count", 0)) + 1
        self.policy["last_game_id"] = game_id
        self.policy["last_final_status"] = final_status
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "consumes_22e39_live_result": True,
            "opening_correction_reviewed": True,
            "midgame_drift_reviewed": True,
            "promotion_choice_reviewed": True,
            "passed_pawn_scope_reviewed": True,
            "endgame_conversion_reviewed": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        review = StrategicWellLivePostGameReviewResult(
            kernel_version="phase22e40_full_chess_level2_strategic_well_live_post_game_review_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            source_path=str(src),
            game_id=game_id,
            final_status=final_status,
            final_winner=final_winner,
            final_ply_count=int(result_payload.get("final_ply_count", len(final_moves))),
            aion_move_count=int(result_payload.get("aion_move_count", 0)),
            move_send_ok_count=int(result_payload.get("move_send_ok_count", 0)),
            post_400_recovery_count=int(result_payload.get("post_400_recovery_count", 0)),
            opening_correction_confirmed=opening_correction_confirmed,
            first_base_well_move=first_base_well_move,
            first_selected_move=first_selected_move,
            h2h4_returned_later=h2h4_returned_later,
            h2h4_return_ply=h2h4_return_ply,
            non_queen_promotion_detected=non_queen_promotion_detected,
            non_queen_promotion_move=non_queen_promotion_move,
            passed_pawn_scope_too_broad=passed_pawn_scope_too_broad,
            endgame_repetition_detected=endgame_repetition_detected,
            draw_conversion_failure=draw_conversion_failure,
            failure_map=failure_map,
            recommended_next_phases=recommended_next_phases,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel performs a deterministic post-game review of the Phase 22E.39 live Strategic Well rematch. "
                "It extracts a failure map for the next patches. It does not call Stockfish, does not use LLM move "
                "judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(review)
        return review


def run_full_chess_level2_strategic_well_live_post_game_review_kernel(
    *,
    source_path: Optional[Path] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_strategic_well_live_post_game_review",
) -> StrategicWellLivePostGameReviewResult:
    return AionStrategicWellLivePostGameReviewKernel(memory_path=memory_path).run(
        source_path=source_path,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_level2_strategic_well_live_post_game_review_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic Well post-game review saved to: {result.memory_path}")
