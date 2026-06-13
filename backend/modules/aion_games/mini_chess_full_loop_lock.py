"""AION Phase 22B.6 — Mini Chess Full Loop Lock.

This joins Phase 22B.1 through 22B.5 into one deterministic proof run:

- legal move grounding;
- threat map / check detection;
- capture / material learning;
- self-play learning;
- opponent win proof.

This is still mini-chess, not full chess.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .mini_chess_legal_move_kernel import run_mini_chess_legal_move_kernel
from .mini_chess_threat_map_kernel import run_mini_chess_threat_map_kernel
from .mini_chess_capture_material_learning_kernel import run_mini_chess_capture_material_learning_kernel
from .mini_chess_self_play_learning_kernel import run_mini_chess_self_play_learning_kernel
from .mini_chess_opponent_win_kernel import run_mini_chess_opponent_win_kernel


DEFAULT_FULL_LOOP_MEMORY_PATH = Path("data/aion_games/mini_chess_full_loop_memory.json")


@dataclass(frozen=True)
class MiniChessFullLoopResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    legal_move_lock_passed: bool
    threat_map_lock_passed: bool
    capture_material_lock_passed: bool
    self_play_lock_passed: bool
    opponent_win_lock_passed: bool
    full_loop_passed: bool
    combined_summary: Dict[str, Any]
    combined_trace_hash: str
    final_full_loop_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionMiniChessFullLoopLock:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_FULL_LOOP_MEMORY_PATH)
        self.memory_loaded = False

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "full_loop_pass_count": 0,
            "legal_move_pass_count": 0,
            "threat_map_pass_count": 0,
            "capture_material_pass_count": 0,
            "self_play_pass_count": 0,
            "opponent_win_pass_count": 0,
            "last_combined_trace_hash": None,
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
            policy = data.get("full_loop_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: MiniChessFullLoopResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b6_mini_chess_full_loop_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "full_loop_policy": result.final_full_loop_policy,
            "last_combined_trace_hash": result.combined_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def run(self, *, task_name: str = "mini_chess_full_loop_lock") -> MiniChessFullLoopResult:
        base_dir = self.memory_path.parent
        base_dir.mkdir(parents=True, exist_ok=True)

        legal = run_mini_chess_legal_move_kernel(memory_path=base_dir / "phase22b6_legal_move_memory.json")
        threat = run_mini_chess_threat_map_kernel(memory_path=base_dir / "phase22b6_threat_map_memory.json")
        capture = run_mini_chess_capture_material_learning_kernel(memory_path=base_dir / "phase22b6_capture_memory.json")
        self_play = run_mini_chess_self_play_learning_kernel(memory_path=base_dir / "phase22b6_self_play_memory.json")
        opponent = run_mini_chess_opponent_win_kernel(memory_path=base_dir / "phase22b6_opponent_memory.json")

        legal_passed = (
            legal.legal_move_count >= 2
            and legal.illegal_move_count >= 2
            and legal.selected_safe_capture is True
            and legal.evidence["uses_llm_shortcut"] is False
        )

        threat_passed = (
            threat.detected_check is True
            and threat.found_escape_from_check is True
            and threat.avoided_unsafe_capture is True
            and threat.selected_checking_move is True
            and threat.evidence["uses_llm_shortcut"] is False
        )

        capture_passed = (
            capture.learned_safe_capture is True
            and capture.avoided_bad_capture is True
            and capture.protected_high_value_piece is True
            and capture.material_score_delta > 0
            and capture.evidence["uses_llm_shortcut"] is False
        )

        self_play_passed = (
            self_play.policy_improved is True
            and self_play.learned_from_loss is True
            and self_play.win_condition_reached is True
            and self_play.evidence["uses_llm_shortcut"] is False
        )

        opponent_passed = (
            opponent.aion_won is True
            and opponent.opponent_defeated is True
            and opponent.learned_policy_applied is True
            and opponent.avoided_known_bad_capture is True
            and opponent.preserved_king_safety is True
            and opponent.evidence["uses_llm_shortcut"] is False
        )

        full_loop_passed = all([
            legal_passed,
            threat_passed,
            capture_passed,
            self_play_passed,
            opponent_passed,
        ])

        combined_summary = {
            "phase22b1_legal_move": {
                "passed": legal_passed,
                "legal_move_count": legal.legal_move_count,
                "illegal_move_count": legal.illegal_move_count,
                "selected_safe_capture": legal.selected_safe_capture,
                "board_trace_hash": legal.board_trace_hash,
            },
            "phase22b2_threat_map": {
                "passed": threat_passed,
                "white_in_check": threat.white_in_check,
                "checking_pieces": threat.checking_pieces,
                "checking_moves": threat.checking_moves,
                "threat_trace_hash": threat.threat_trace_hash,
            },
            "phase22b3_capture_material": {
                "passed": capture_passed,
                "selected_capture": capture.selected_capture,
                "material_score_delta": capture.material_score_delta,
                "capture_trace_hash": capture.capture_trace_hash,
            },
            "phase22b4_self_play": {
                "passed": self_play_passed,
                "baseline_result": self_play.baseline_result,
                "final_result": self_play.final_result,
                "reward_delta": self_play.reward_delta,
                "self_play_trace_hash": self_play.self_play_trace_hash,
            },
            "phase22b5_opponent_win": {
                "passed": opponent_passed,
                "aion_won": opponent.aion_won,
                "win_condition": opponent.win_condition,
                "material_score_delta": opponent.material_score_delta,
                "opponent_trace_hash": opponent.opponent_trace_hash,
            },
        }

        combined_trace_hash = self._hash({
            "combined_summary": combined_summary,
            "full_loop_passed": full_loop_passed,
            "uses_llm_shortcut": False,
        })

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        if full_loop_passed:
            self.policy["full_loop_pass_count"] = int(self.policy.get("full_loop_pass_count", 0)) + 1
        if legal_passed:
            self.policy["legal_move_pass_count"] = int(self.policy.get("legal_move_pass_count", 0)) + 1
        if threat_passed:
            self.policy["threat_map_pass_count"] = int(self.policy.get("threat_map_pass_count", 0)) + 1
        if capture_passed:
            self.policy["capture_material_pass_count"] = int(self.policy.get("capture_material_pass_count", 0)) + 1
        if self_play_passed:
            self.policy["self_play_pass_count"] = int(self.policy.get("self_play_pass_count", 0)) + 1
        if opponent_passed:
            self.policy["opponent_win_pass_count"] = int(self.policy.get("opponent_win_pass_count", 0)) + 1

        self.policy["last_combined_trace_hash"] = combined_trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_legal_move_kernel": True,
            "uses_threat_map_kernel": True,
            "uses_capture_material_kernel": True,
            "uses_self_play_kernel": True,
            "uses_opponent_win_kernel": True,
            "uses_combined_trace_hash": True,
            "full_loop_passed": full_loop_passed,
            "memory_loaded": self.memory_loaded,
        }

        result = MiniChessFullLoopResult(
            kernel_version="phase22b6_mini_chess_full_loop_lock_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            legal_move_lock_passed=legal_passed,
            threat_map_lock_passed=threat_passed,
            capture_material_lock_passed=capture_passed,
            self_play_lock_passed=self_play_passed,
            opponent_win_lock_passed=opponent_passed,
            full_loop_passed=full_loop_passed,
            combined_summary=combined_summary,
            combined_trace_hash=combined_trace_hash,
            final_full_loop_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates the full operational mini-chess loop from legal move grounding through opponent win. "
                "It does not prove full chess mastery, general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_mini_chess_full_loop_lock(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "mini_chess_full_loop_lock",
) -> MiniChessFullLoopResult:
    return AionMiniChessFullLoopLock(memory_path=memory_path).run(task_name=task_name)


if __name__ == "__main__":
    result = run_mini_chess_full_loop_lock()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Mini chess full loop memory saved to: {result.memory_path}")
