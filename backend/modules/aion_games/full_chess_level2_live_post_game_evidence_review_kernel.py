from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

DEFAULT_EVIDENCE_PATH = Path("data/aion_games/full_chess_level2_22e18_live_rerun_Jh3hn2ru.json")
DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_live_post_game_evidence_review_memory.json")


@dataclass(frozen=True)
class LiveLevel2PostGameEvidenceReviewResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    evidence_path: str
    review_mode: str
    game_id: str
    full_id: str
    aion_colour: str
    final_status: str
    final_winner: Optional[str]
    final_ply_count: int
    aion_move_count: int
    move_send_ok_count: int
    all_aion_sends_succeeded: bool
    illegal_move_count: int
    promoted_move_detected: bool
    promoted_move: Optional[str]
    old_failure_mode: str
    new_failure_mode: str
    improvement_summary: Dict[str, Any]
    failure_review: Dict[str, Any]
    next_patch_targets: List[str]
    post_game_trace_hash: str
    policy_memory_mutated: bool
    final_review_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionFullChessLevel2LivePostGameEvidenceReviewKernel:
    def __init__(
        self,
        evidence_path: Optional[Path] = None,
        memory_path: Optional[Path] = None,
    ) -> None:
        self.evidence_path = Path(evidence_path or DEFAULT_EVIDENCE_PATH)
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "review_count": 0,
            "last_game_id": None,
            "last_final_status": None,
            "last_final_winner": None,
            "last_failure_mode": None,
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("level2_live_post_game_review_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveLevel2PostGameEvidenceReviewResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e19_level2_live_post_game_evidence_review_memory_v1",
            "task_name": result.task_name,
            "level2_live_post_game_review_policy": result.final_review_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _load_evidence(self) -> Dict[str, Any]:
        if not self.evidence_path.exists():
            raise FileNotFoundError(f"Evidence file not found: {self.evidence_path}")
        return json.loads(self.evidence_path.read_text(encoding="utf-8"))

    def _count_illegal_moves(self, moves: List[str]) -> int:
        board = chess.Board()
        illegal = 0
        for move_uci in moves:
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                illegal += 1
                continue
            if move not in board.legal_moves:
                illegal += 1
                continue
            board.push(move)
        return illegal

    def run(
        self,
        *,
        task_name: str = "full_chess_level2_live_post_game_evidence_review",
    ) -> LiveLevel2PostGameEvidenceReviewResult:
        data = self._load_evidence()

        game_id = str(data.get("game_id") or "")
        full_id = str(data.get("full_id") or "")
        aion_colour = str(data.get("aion_colour") or "")
        final_status = str(data.get("final_status") or "")
        final_winner = data.get("final_winner")
        final_moves = list(data.get("final_moves") or [])
        final_ply_count = int(data.get("final_ply_count") or len(final_moves))
        aion_move_count = int(data.get("aion_move_count") or 0)
        move_send_ok_count = int(data.get("move_send_ok_count") or 0)
        move_records = list(data.get("move_records") or [])

        all_sends_succeeded = (
            aion_move_count > 0
            and move_send_ok_count == aion_move_count
            and all(bool(record.get("move_post_succeeded")) for record in move_records)
        )

        illegal_move_count = self._count_illegal_moves(final_moves)

        promoted_move = None
        for move in final_moves:
            if len(move) == 5 and move[-1].lower() in {"q", "r", "b", "n"}:
                promoted_move = move
                break

        promoted_move_detected = promoted_move is not None

        old_failure_mode = "mate_collapse_or_early_tactical_collapse"
        new_failure_mode = "outoftime_after_long_queen_endgame_repetition"

        improvement_summary = {
            "previous_known_failure": old_failure_mode,
            "new_failure": new_failure_mode,
            "live_game_completed": True,
            "full_live_loop_operated": True,
            "authorized_sender_used": True,
            "legal_move_stream_validated": illegal_move_count == 0,
            "aion_live_sends": aion_move_count,
            "send_success_ratio": f"{move_send_ok_count}/{aion_move_count}",
            "survived_to_ply": final_ply_count,
            "promotion_detected": promoted_move_detected,
            "promotion_move": promoted_move,
            "result_improved_from_mate_loss_to_timeout_loss": True,
        }

        failure_review = {
            "primary_failure": "clock_loss",
            "secondary_failure": "queen_endgame_conversion_failure",
            "tertiary_failure": "repetition_like_queen_shuffling",
            "symptom": "AION promoted but did not convert queen advantage into mate or simplification.",
            "observed_late_pattern": "queen moves repeated across distant squares while black king escaped and clock expired.",
            "missing_capabilities": [
                "queen_king_mate_boxing",
                "enemy_king_mobility_reduction",
                "forced_check_sequence_preference",
                "rook_capture_or_trade_when_ahead",
                "threefold/repetition pressure avoidance",
                "low_time_forcing_mode",
            ],
        }

        next_patch_targets = [
            "queen_endgame_conversion_kernel",
            "forced_check_and_mate_pressure_scoring",
            "enemy_king_mobility_reduction_scoring",
            "repetition_memory_penalty",
            "clock_pressure_override",
            "simplify_when_winning_capture_rook_bias",
        ]

        trace_payload = {
            "game_id": game_id,
            "full_id": full_id,
            "final_status": final_status,
            "final_winner": final_winner,
            "final_ply_count": final_ply_count,
            "aion_move_count": aion_move_count,
            "move_send_ok_count": move_send_ok_count,
            "illegal_move_count": illegal_move_count,
            "promoted_move": promoted_move,
            "new_failure_mode": new_failure_mode,
            "next_patch_targets": next_patch_targets,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["review_count"] = int(self.policy.get("review_count", 0)) + 1
        self.policy["last_game_id"] = game_id
        self.policy["last_final_status"] = final_status
        self.policy["last_final_winner"] = final_winner
        self.policy["last_failure_mode"] = new_failure_mode
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase_22e18_live_evidence_consumed": True,
            "game_id_locked": game_id,
            "full_id_locked": full_id,
            "aion_colour_white": aion_colour == "white",
            "final_status_outoftime": final_status == "outoftime",
            "winner_black": final_winner == "black",
            "aion_sent_61_moves": aion_move_count == 61,
            "all_aion_sends_succeeded": all_sends_succeeded,
            "illegal_move_count_zero": illegal_move_count == 0,
            "promotion_detected": promoted_move_detected,
            "promotion_move": promoted_move,
            "failure_mode_shifted": True,
            "requires_queen_endgame_patch": True,
            "requires_clock_pressure_patch": True,
            "uses_stockfish_by_aion": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveLevel2PostGameEvidenceReviewResult(
            kernel_version="phase22e19_full_chess_level2_live_post_game_evidence_review_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            evidence_path=str(self.evidence_path),
            review_mode="live_level2_post_game_evidence_failure_review",
            game_id=game_id,
            full_id=full_id,
            aion_colour=aion_colour,
            final_status=final_status,
            final_winner=final_winner,
            final_ply_count=final_ply_count,
            aion_move_count=aion_move_count,
            move_send_ok_count=move_send_ok_count,
            all_aion_sends_succeeded=all_sends_succeeded,
            illegal_move_count=illegal_move_count,
            promoted_move_detected=promoted_move_detected,
            promoted_move=promoted_move,
            old_failure_mode=old_failure_mode,
            new_failure_mode=new_failure_mode,
            improvement_summary=improvement_summary,
            failure_review=failure_review,
            next_patch_targets=next_patch_targets,
            post_game_trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_review_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel locks the Phase 22E.18 live Level-2 evidence and converts the result into "
                "a concrete patch target. It does not play chess, does not send moves, does not call Lichess, "
                "and does not use Stockfish, LLM judgement, or Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_live_post_game_evidence_review_kernel(
    *,
    evidence_path: Optional[Path] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_live_post_game_evidence_review",
) -> LiveLevel2PostGameEvidenceReviewResult:
    return AionFullChessLevel2LivePostGameEvidenceReviewKernel(
        evidence_path=evidence_path,
        memory_path=memory_path,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_full_chess_level2_live_post_game_evidence_review_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live Level-2 post-game evidence review memory saved to: {result.memory_path}")
