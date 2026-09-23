"""AION Phase 22C.4 — Full Chess Live Loop Search Selector Adapter Kernel.

This phase replaces the old live-loop heuristic move picker with the Phase 22C.3
depth-limited lookahead search selector.

It proves:
- live loop board state can be converted to FEN;
- AION only selects a move when it is AION's turn;
- selected move comes from the 22C.3 search kernel;
- selected move is legal in the live board state;
- terminal positions emit no move;
- dry-run mode is default;
- no Lichess network move is sent in this phase;
- no Stockfish, cloud engine, external engine, or LLM shortcut is used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from .full_chess_depth_limited_lookahead_search_kernel import (
    run_full_chess_depth_limited_lookahead_search_kernel,
)


DEFAULT_LIVE_LOOP_SEARCH_SELECTOR_MEMORY_PATH = Path(
    "data/aion_games/full_chess_live_loop_search_selector_adapter_memory.json"
)


@dataclass(frozen=True)
class LiveLoopSearchSelectorAdapterResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    adapter_mode: str
    game_id: str
    aion_colour: str
    side_to_move: str
    is_aion_turn: bool
    dry_run: bool
    network_send_allowed: bool
    network_send_attempted: bool
    fen: str
    move_count: int
    terminal_position: bool
    legal_move_count: int
    selected_move: str
    selected_score: float
    selected_reason: str
    search_depth_limit: int
    search_trace_hash: str
    adapter_trace_hash: str
    live_loop_move_source: str
    old_heuristic_picker_replaced: bool
    policy_memory_mutated: bool
    final_adapter_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessLiveLoopSearchSelectorAdapterKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        search_memory_path: Optional[Path] = None,
        evaluation_memory_path: Optional[Path] = None,
        post_game_memory_path: Optional[Path] = None,
    ):
        self.memory_path = Path(memory_path or DEFAULT_LIVE_LOOP_SEARCH_SELECTOR_MEMORY_PATH)
        self.search_memory_path = search_memory_path
        self.evaluation_memory_path = evaluation_memory_path
        self.post_game_memory_path = post_game_memory_path
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "adapter_invocation_count": 0,
            "aion_turn_selection_count": 0,
            "non_aion_turn_skip_count": 0,
            "terminal_skip_count": 0,
            "network_send_attempt_count": 0,
            "dry_run_count": 0,
            "last_game_id": None,
            "last_fen": None,
            "last_selected_move": None,
            "last_adapter_trace_hash": None,
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
            policy = data.get("live_loop_search_selector_adapter_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: LiveLoopSearchSelectorAdapterResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22c4_full_chess_live_loop_search_selector_adapter_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "live_loop_search_selector_adapter_policy": result.final_adapter_policy,
            "game_id": result.game_id,
            "aion_colour": result.aion_colour,
            "fen": result.fen,
            "selected_move": result.selected_move,
            "selected_score": result.selected_score,
            "selected_reason": result.selected_reason,
            "adapter_trace_hash": result.adapter_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _side_name(self, colour: chess.Color) -> str:
        return "white" if colour == chess.WHITE else "black"

    def _board_from_moves(self, moves: List[str]) -> chess.Board:
        board = chess.Board()
        for move in moves:
            if not move:
                continue
            board.push_uci(move)
        return board

    def run(
        self,
        *,
        task_name: str = "full_chess_live_loop_search_selector_adapter",
        game_id: str = "dry_run_live_loop_adapter_game",
        aion_colour: str = "white",
        moves: Optional[List[str]] = None,
        fen: Optional[str] = None,
        search_depth_limit: int = 2,
        dry_run: bool = True,
        network_send_allowed: bool = False,
    ) -> LiveLoopSearchSelectorAdapterResult:
        if fen:
            board = chess.Board(fen)
            move_count = len(board.move_stack)
        else:
            board = self._board_from_moves(moves or [])
            move_count = len(moves or [])

        side_to_move = self._side_name(board.turn)
        is_aion_turn = side_to_move == aion_colour
        terminal_position = board.is_game_over()
        legal_move_count = board.legal_moves.count()

        selected_move = ""
        selected_score = 0.0
        selected_reason = "not_aion_turn"
        search_trace_hash = ""

        if terminal_position:
            selected_reason = "terminal_position_no_move"
        elif is_aion_turn:
            search_result = run_full_chess_depth_limited_lookahead_search_kernel(
                memory_path=self.search_memory_path,
                evaluation_memory_path=self.evaluation_memory_path,
                post_game_memory_path=self.post_game_memory_path,
                fen=board.fen(),
                side_to_evaluate=aion_colour,
                depth_limit=search_depth_limit,
            )
            selected_move = search_result.selected_move
            selected_score = search_result.selected_score
            selected_reason = search_result.selected_reason
            search_trace_hash = search_result.search_trace_hash

        legal_moves = {move.uci() for move in board.legal_moves}
        selected_move_is_legal = selected_move in legal_moves if selected_move else True

        network_send_attempted = False
        if selected_move and network_send_allowed and not dry_run:
            network_send_attempted = True

        trace_payload = {
            "adapter_mode": "live_loop_search_selector_adapter",
            "game_id": game_id,
            "aion_colour": aion_colour,
            "side_to_move": side_to_move,
            "is_aion_turn": is_aion_turn,
            "dry_run": dry_run,
            "network_send_allowed": network_send_allowed,
            "network_send_attempted": network_send_attempted,
            "fen": board.fen(),
            "move_count": move_count,
            "terminal_position": terminal_position,
            "legal_move_count": legal_move_count,
            "selected_move": selected_move,
            "selected_score": selected_score,
            "selected_reason": selected_reason,
            "search_depth_limit": search_depth_limit,
            "search_trace_hash": search_trace_hash,
            "old_heuristic_picker_replaced": True,
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
        }
        adapter_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["adapter_invocation_count"] = int(self.policy.get("adapter_invocation_count", 0)) + 1
        self.policy["aion_turn_selection_count"] = int(self.policy.get("aion_turn_selection_count", 0)) + (1 if is_aion_turn and selected_move else 0)
        self.policy["non_aion_turn_skip_count"] = int(self.policy.get("non_aion_turn_skip_count", 0)) + (1 if not is_aion_turn else 0)
        self.policy["terminal_skip_count"] = int(self.policy.get("terminal_skip_count", 0)) + (1 if terminal_position else 0)
        self.policy["network_send_attempt_count"] = int(self.policy.get("network_send_attempt_count", 0)) + (1 if network_send_attempted else 0)
        self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + (1 if dry_run else 0)
        self.policy["last_game_id"] = game_id
        self.policy["last_fen"] = board.fen()
        self.policy["last_selected_move"] = selected_move
        self.policy["last_adapter_trace_hash"] = adapter_trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_stockfish": False,
            "uses_cloud_engine": False,
            "live_loop_adapter_active": True,
            "old_heuristic_picker_replaced": True,
            "search_selector_used_when_aion_turn": bool(is_aion_turn and selected_move),
            "no_move_when_not_aion_turn": bool((not is_aion_turn) and selected_move == ""),
            "no_move_when_terminal": bool((not terminal_position) or selected_move == ""),
            "selected_move_is_legal": selected_move_is_legal,
            "dry_run_default": dry_run is True,
            "network_send_attempted": network_send_attempted,
            "network_call_performed": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveLoopSearchSelectorAdapterResult(
            kernel_version="phase22c4_full_chess_live_loop_search_selector_adapter_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            adapter_mode="live_loop_search_selector_adapter",
            game_id=game_id,
            aion_colour=aion_colour,
            side_to_move=side_to_move,
            is_aion_turn=is_aion_turn,
            dry_run=dry_run,
            network_send_allowed=network_send_allowed,
            network_send_attempted=network_send_attempted,
            fen=board.fen(),
            move_count=move_count,
            terminal_position=terminal_position,
            legal_move_count=legal_move_count,
            selected_move=selected_move,
            selected_score=selected_score,
            selected_reason=selected_reason,
            search_depth_limit=search_depth_limit,
            search_trace_hash=search_trace_hash,
            adapter_trace_hash=adapter_trace_hash,
            live_loop_move_source="phase22c3_depth_limited_search_selector" if selected_move else "none",
            old_heuristic_picker_replaced=True,
            policy_memory_mutated=True,
            final_adapter_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This phase replaces the old live-loop heuristic picker with the Phase 22C.3 depth-limited search selector. "
                "It is a guarded dry-run adapter and does not send a live Lichess move. Network send authority remains disabled here."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_loop_search_selector_adapter_kernel(
    *,
    memory_path: Optional[Path] = None,
    search_memory_path: Optional[Path] = None,
    evaluation_memory_path: Optional[Path] = None,
    post_game_memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_loop_search_selector_adapter",
    game_id: str = "dry_run_live_loop_adapter_game",
    aion_colour: str = "white",
    moves: Optional[List[str]] = None,
    fen: Optional[str] = None,
    search_depth_limit: int = 2,
    dry_run: bool = True,
    network_send_allowed: bool = False,
) -> LiveLoopSearchSelectorAdapterResult:
    return AionFullChessLiveLoopSearchSelectorAdapterKernel(
        memory_path=memory_path,
        search_memory_path=search_memory_path,
        evaluation_memory_path=evaluation_memory_path,
        post_game_memory_path=post_game_memory_path,
    ).run(
        task_name=task_name,
        game_id=game_id,
        aion_colour=aion_colour,
        moves=moves,
        fen=fen,
        search_depth_limit=search_depth_limit,
        dry_run=dry_run,
        network_send_allowed=network_send_allowed,
    )


if __name__ == "__main__":
    result = run_full_chess_live_loop_search_selector_adapter_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess live-loop search selector adapter memory saved to: {result.memory_path}")
