from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel import (
    run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel,
)
from backend.modules.aion_games.full_chess_opponent_reply_probability_tactical_exposure_guard_kernel import (
    run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel,
)
from backend.modules.aion_games.full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel import run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel
from backend.modules.aion_games.full_chess_monte_carlo_policy_value_seed_kernel import (
    run_full_chess_monte_carlo_policy_value_seed_kernel,
)
from backend.modules.aion_games.full_chess_rolling_strategic_plan_kernel import (
    run_full_chess_rolling_strategic_plan_kernel,
)
from backend.modules.aion_games.full_chess_parallel_opponent_beam_router_sqi_collapse_kernel import (
    run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_live_one_move_strategic_well_sender_memory.json")


@dataclass(frozen=True)
class LiveOneMoveStrategicWellSenderResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    game_id: str
    input_fen: str
    side_to_move: str
    target_level: int
    selected_move: str
    selected_move_is_legal: bool
    selected_source: str
    active_intent: str
    base_well_selected_move: str
    intent_override_applied: bool
    regression_well_score: int
    explicit_live_send_authorized: bool
    human_operator_confirmed: bool
    live_game_stream_confirmed: bool
    one_move_gate_enabled: bool
    live_sender_enabled: bool
    allow_real_post: bool
    token_present: bool
    live_env_enabled: bool
    all_live_gates_passed: bool
    move_post_attempted: bool
    move_post_succeeded: bool
    move_post_status_code: int
    move_post_error: str
    trace_hash: str
    policy_memory_mutated: bool
    final_sender_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionLiveOneMoveStrategicWellSenderKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "post_attempt_count": 0,
            "post_success_count": 0,
            "blocked_count": 0,
            "last_game_id": "",
            "last_selected_move": "",
            "last_active_intent": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("live_one_move_strategic_well_sender_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: LiveOneMoveStrategicWellSenderResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e38_live_one_move_strategic_well_sender_memory_v1",
            "task_name": result.task_name,
            "live_one_move_strategic_well_sender_policy": result.final_sender_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _post_move(self, *, token: str, game_id: str, move_uci: str, timeout_seconds: int) -> tuple[bool, int, str]:
        url = f"https://lichess.org/api/bot/game/{game_id}/move/{move_uci}"
        req = urllib.request.Request(
            url,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                return 200 <= response.status < 300, int(response.status), ""
        except urllib.error.HTTPError as exc:
            return False, int(exc.code), str(exc)
        except Exception as exc:
            return False, 0, str(exc)

    def run(
        self,
        *,
        game_id: str,
        input_fen: str,
        side_to_move: str = "white",
        target_level: int = 2,
        repeated_moves: Optional[List[str]] = None,
        repeated_squares: Optional[List[str]] = None,
        explicit_live_send_authorized: bool = False,
        human_operator_confirmed: bool = False,
        live_game_stream_confirmed: bool = False,
        one_move_gate_enabled: bool = False,
        live_sender_enabled: bool = False,
        allow_real_post: bool = False,
        token: Optional[str] = None,
        timeout_seconds: int = 20,
        task_name: str = "full_chess_live_one_move_strategic_well_sender",
    ) -> LiveOneMoveStrategicWellSenderResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        strategic = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            repeated_moves=list(repeated_moves or []),
            repeated_squares=list(repeated_squares or []),
            memory_path=self.memory_path.parent / "phase22e38_child_critical_threat_hygiene_queen_intrusion_memory.json",
        )

        rolling_plan = run_full_chess_rolling_strategic_plan_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            memory_path=self.memory_path.parent / "phase22e58_child_rolling_strategic_plan_memory.json",
            task_name=f"{task_name}_phase22e58_child_rolling_plan",
        )

        active_intent = strategic.active_intent
        strategic_selected_move = strategic.final_selected_move
        plan_selected_move = rolling_plan.selected_plan_move
        plan_filtered_move = strategic_selected_move
        rolling_plan_override_applied = False

        opening_edge_knight_moves = {"b1a3", "g1h3", "b8a6", "g8h6"}
        early_drift_moves = {"h2h4", "a2a4", "h7h5", "a7a5"}

        if rolling_plan.phase == "opening" and plan_selected_move:
            try:
                plan_move_is_legal = chess.Move.from_uci(plan_selected_move) in board.legal_moves
            except Exception:
                plan_move_is_legal = False

            base_well_move = getattr(strategic, "base_well_selected_move", "")
            should_prefer_plan = (
                strategic_selected_move in opening_edge_knight_moves
                or strategic_selected_move in early_drift_moves
                or base_well_move in early_drift_moves
                or (
                    active_intent == "rapid_development"
                    and strategic_selected_move not in rolling_plan.candidate_plan_moves[:5]
                )
            )

            if plan_move_is_legal and should_prefer_plan:
                plan_filtered_move = plan_selected_move
                rolling_plan_override_applied = plan_filtered_move != strategic_selected_move

        phase22e61_router_used = False
        phase22e61_router_override_applied = False
        phase22e61_selected_move = ""
        phase22e61_trace_hash = ""

        router_candidates = []
        for move in [
            plan_filtered_move,
            plan_selected_move,
            strategic_selected_move,
            getattr(strategic, "base_well_selected_move", ""),
        ]:
            if move and move not in router_candidates:
                router_candidates.append(move)

        for move in getattr(rolling_plan, "candidate_plan_moves", [])[:8]:
            if move and move not in router_candidates:
                router_candidates.append(move)

        router_candidates = [
            move for move in router_candidates
            if move and chess.Move.from_uci(move) in board.legal_moves
        ]

        if router_candidates:
            phase22e61 = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
                input_fen=input_fen,
                side_to_move=side_to_move,
                candidate_moves=router_candidates,
                primary_plan=getattr(rolling_plan, "primary_plan", active_intent),
                target_weakness=getattr(rolling_plan, "target_weakness", ""),
                max_reply_beams=8,
                max_continuations_per_reply=16,
                max_parallel_beams=1000,
                memory_path=self.memory_path.parent / "phase22e61_child_parallel_opponent_beam_router_memory.json",
                task_name=f"{task_name}_phase22e61_child_parallel_opponent_beam_router",
            )
            phase22e61_router_used = True
            phase22e61_selected_move = phase22e61.selected_move
            phase22e61_trace_hash = phase22e61.trace_hash

            if (
                phase22e61_selected_move
                and chess.Move.from_uci(phase22e61_selected_move) in board.legal_moves
                and phase22e61_selected_move != plan_filtered_move
            ):
                plan_filtered_move = phase22e61_selected_move
                phase22e61_router_override_applied = True

        phase22e54 = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            selected_move=plan_filtered_move,
            active_intent=active_intent,
            memory_path=self.memory_path.parent / "phase22e54_child_opponent_reply_probability_tactical_exposure_memory.json",
        )

        phase22e55 = run_full_chess_monte_carlo_policy_value_seed_kernel(
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=phase22e54.final_selected_move,
            rollout_count=16,
            beam_width=8,
            rollout_depth=4,
            memory_path=self.memory_path.parent / "phase22e55_child_monte_carlo_policy_value_seed_memory.json",
        )

        selected_move = phase22e55.final_selected_move
        selected_source = phase22e55.final_selected_source

        # Phase 22E.63:
        # A validated Phase 22E.61 SQI-collapsed router override MUST survive
        # the later Monte Carlo policy-value seed layer in the live sender path.
        phase22e63_router_survived_monte_carlo = False
        if (
            phase22e61_router_override_applied
            and phase22e61_selected_move
            and selected_move != phase22e61_selected_move
        ):
            try:
                phase22e63_router_move_is_legal = chess.Move.from_uci(phase22e61_selected_move) in board.legal_moves
            except Exception:
                phase22e63_router_move_is_legal = False

            if phase22e63_router_move_is_legal:
                selected_move = phase22e61_selected_move
                selected_source = "phase22e61_parallel_opponent_beam_router_sqi_collapse"
                phase22e63_router_survived_monte_carlo = True

        monte_carlo_plan_guard_applied = False
        if (
            rolling_plan.phase == "opening"
            and rolling_plan.selected_plan_move
            and selected_move in opening_edge_knight_moves
        ):
            try:
                rolling_plan_move_is_legal = chess.Move.from_uci(rolling_plan.selected_plan_move) in board.legal_moves
            except Exception:
                rolling_plan_move_is_legal = False

            if rolling_plan_move_is_legal:
                selected_move = rolling_plan.selected_plan_move
                selected_source = "rolling_plan_monte_carlo_edge_knight_guard"
                monte_carlo_plan_guard_applied = True

        # Phase 22E.65:
        # Final live-sender queen intrusion / mate-corridor guard.
        # This runs after Monte Carlo and after the 22E.63 router survival check,
        # so a passive or mate-losing final selected move cannot be posted when
        # the opponent queen has entered the king corridor.
        phase22e65_queen_intrusion_final_guard_used = False
        phase22e65_queen_intrusion_override_applied = False
        phase22e65_queen_intrusion_square = ""
        phase22e65_guard_selected_move = ""
        phase22e65_guard_selected_source = ""

        if active_intent in {"center_control", "initiative_pressure", "king_safety", "neutralise_critical_threat"}:
            try:
                phase22e65_guard_intent = active_intent
                if active_intent in {"center_control", "initiative_pressure"}:
                    phase22e65_guard_intent = "king_safety"

                phase22e65_guard = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
                    input_fen=input_fen,
                    side_to_move=side_to_move,
                    forced_base_selected_move=selected_move,
                    forced_active_intent=phase22e65_guard_intent,
                    memory_path=self.memory_path.parent / "phase22e65_child_queen_intrusion_final_guard_memory.json",
                    task_name=f"{task_name}_phase22e65_child_queen_intrusion_final_guard",
                )
                phase22e65_queen_intrusion_final_guard_used = True
                phase22e65_queen_intrusion_square = getattr(phase22e65_guard, "queen_intrusion_square", "")
                phase22e65_guard_selected_move = getattr(phase22e65_guard, "final_selected_move", "")
                phase22e65_guard_selected_source = getattr(phase22e65_guard, "final_selected_source", "")

                if (
                    getattr(phase22e65_guard, "queen_intrusion_detected", False)
                    and phase22e65_guard_selected_move
                    and phase22e65_guard_selected_move != selected_move
                    and chess.Move.from_uci(phase22e65_guard_selected_move) in board.legal_moves
                ):
                    selected_move = phase22e65_guard_selected_move
                    selected_source = "phase22e65_queen_intrusion_final_guard"
                    phase22e65_queen_intrusion_override_applied = True
            except Exception:
                phase22e65_queen_intrusion_final_guard_used = False

        # Phase 22E.68:
        # Forced-mate horizon guard.
        # This rejects a selected move if the opponent has a reply that leaves AION
        # with no legal move that avoids immediate mate on the next turn.
        phase22e68_forced_mate_horizon_guard_used = False
        phase22e68_forced_mate_horizon_detected = False
        phase22e68_forcing_reply = ""
        phase22e68_guard_selected_move = ""
        phase22e68_guard_override_applied = False

        def _phase22e68_mate_replies_after(board_obj, move_uci):
            try:
                candidate = chess.Move.from_uci(move_uci)
                if candidate not in board_obj.legal_moves:
                    return []
                probe = board_obj.copy(stack=False)
                probe.push(candidate)
                mates = []
                for reply in probe.legal_moves:
                    reply_probe = probe.copy(stack=False)
                    reply_probe.push(reply)
                    if reply_probe.is_checkmate():
                        mates.append(reply.uci())
                return mates
            except Exception:
                return []

        def _phase22e68_safe_evasions(board_obj):
            safe = []
            for candidate in board_obj.legal_moves:
                if not _phase22e68_mate_replies_after(board_obj, candidate.uci()):
                    safe.append(candidate.uci())
            return safe

        def _phase22e68_shallow_horizon_safe_moves(board_obj):
            safe = []
            for candidate in board_obj.legal_moves:
                cuci = candidate.uci()
                if _phase22e68_mate_replies_after(board_obj, cuci):
                    continue

                probe = board_obj.copy(stack=False)
                probe.push(candidate)

                opponent_can_leave_no_immediate_safe_evasion = False
                for reply in probe.legal_moves:
                    reply_probe = probe.copy(stack=False)
                    reply_probe.push(reply)
                    if not _phase22e68_safe_evasions(reply_probe):
                        opponent_can_leave_no_immediate_safe_evasion = True
                        break

                if not opponent_can_leave_no_immediate_safe_evasion:
                    safe.append(cuci)

            return safe

        def _phase22e68_forcing_replies_after(board_obj, move_uci):
            try:
                candidate = chess.Move.from_uci(move_uci)
                if candidate not in board_obj.legal_moves:
                    return []
                probe = board_obj.copy(stack=False)
                probe.push(candidate)
                forcing = []
                for reply in probe.legal_moves:
                    reply_probe = probe.copy(stack=False)
                    reply_probe.push(reply)
                    if not _phase22e68_shallow_horizon_safe_moves(reply_probe):
                        forcing.append(reply.uci())
                return forcing
            except Exception:
                return []

        def _phase22e68_score_safe_horizon_move(board_obj, move_uci):
            try:
                move_obj = chess.Move.from_uci(move_uci)
                score = 0
                captured = board_obj.piece_at(move_obj.to_square)
                moving_piece = board_obj.piece_at(move_obj.from_square)

                if captured and captured.color != board_obj.turn:
                    piece_values = {
                        chess.PAWN: 100,
                        chess.KNIGHT: 320,
                        chess.BISHOP: 330,
                        chess.ROOK: 500,
                        chess.QUEEN: 900,
                        chess.KING: 20000,
                    }
                    score += piece_values.get(captured.piece_type, 0) + 500

                probe = board_obj.copy(stack=False)
                probe.push(move_obj)
                if probe.is_check():
                    score += 500

                if moving_piece and moving_piece.piece_type == chess.KING:
                    score -= 150

                return score
            except Exception:
                return -999999

        phase22e68_forced_mate_horizon_guard_used = True
        phase22e68_forcing_replies = _phase22e68_forcing_replies_after(board, selected_move)

        if phase22e68_forcing_replies:
            phase22e68_forced_mate_horizon_detected = True
            phase22e68_forcing_reply = phase22e68_forcing_replies[0]

            horizon_safe = []
            for candidate in board.legal_moves:
                cuci = candidate.uci()
                if _phase22e68_mate_replies_after(board, cuci):
                    continue
                if _phase22e68_forcing_replies_after(board, cuci):
                    continue
                horizon_safe.append((_phase22e68_score_safe_horizon_move(board, cuci), cuci))

            if horizon_safe:
                horizon_safe.sort(reverse=True)
                phase22e68_guard_selected_move = horizon_safe[0][1]
                if phase22e68_guard_selected_move != selected_move:
                    selected_move = phase22e68_guard_selected_move
                    selected_source = "phase22e68_forced_mate_horizon_guard"
                    phase22e68_guard_override_applied = True

        # Phase 22E.66:
        # Final immediate-mate reply guard.
        # This is the final safety net after Monte Carlo, router survival, opening guards,
        # and queen-intrusion hygiene. It rejects any selected move that allows the
        # opponent to mate in one reply.
        phase22e66_immediate_mate_reply_guard_used = False
        phase22e66_immediate_mate_reply_detected = False
        phase22e66_immediate_mate_reply_move = ""
        phase22e66_guard_selected_move = ""
        phase22e66_guard_override_applied = False

        def _phase22e66_allows_immediate_mate_reply(board_obj, move_uci):
            try:
                candidate = chess.Move.from_uci(move_uci)
                if candidate not in board_obj.legal_moves:
                    return False, ""
                probe = board_obj.copy(stack=False)
                probe.push(candidate)
                for reply in probe.legal_moves:
                    reply_probe = probe.copy(stack=False)
                    reply_probe.push(reply)
                    if reply_probe.is_checkmate():
                        return True, reply.uci()
            except Exception:
                return False, ""
            return False, ""

        def _phase22e66_safe_move_score(board_obj, move_obj):
            score = 0
            captured = board_obj.piece_at(move_obj.to_square)
            moving_piece = board_obj.piece_at(move_obj.from_square)

            if captured and captured.color != board_obj.turn:
                piece_values = {
                    chess.PAWN: 100,
                    chess.KNIGHT: 320,
                    chess.BISHOP: 330,
                    chess.ROOK: 500,
                    chess.QUEEN: 900,
                    chess.KING: 20000,
                }
                score += piece_values.get(captured.piece_type, 0) + 500
                if captured.piece_type == chess.QUEEN:
                    score += 10000

            probe = board_obj.copy(stack=False)
            probe.push(move_obj)

            if probe.is_checkmate():
                score += 50000
            elif probe.is_check():
                score += 900

            own_king = probe.king(board_obj.turn)
            enemy_queen_sq = None
            for sq, piece in probe.piece_map().items():
                if piece.color != board_obj.turn and piece.piece_type == chess.QUEEN:
                    enemy_queen_sq = sq
                    break

            if own_king is not None and enemy_queen_sq is not None:
                distance = max(
                    abs(chess.square_file(enemy_queen_sq) - chess.square_file(own_king)),
                    abs(chess.square_rank(enemy_queen_sq) - chess.square_rank(own_king)),
                )
                score -= max(0, 8 - distance) * 200

            if moving_piece and moving_piece.piece_type == chess.KING:
                score -= 200

            return score

        phase22e66_immediate_mate_reply_guard_used = True
        phase22e66_bad, phase22e66_reply = _phase22e66_allows_immediate_mate_reply(board, selected_move)
        if phase22e66_bad:
            phase22e66_immediate_mate_reply_detected = True
            phase22e66_immediate_mate_reply_move = phase22e66_reply

            safe_candidates = []
            for candidate in board.legal_moves:
                allows_mate, _ = _phase22e66_allows_immediate_mate_reply(board, candidate.uci())
                if allows_mate:
                    continue
                safe_candidates.append((_phase22e66_safe_move_score(board, candidate), candidate.uci()))

            if safe_candidates:
                safe_candidates.sort(reverse=True)
                phase22e66_guard_selected_move = safe_candidates[0][1]
                if phase22e66_guard_selected_move != selected_move:
                    selected_move = phase22e66_guard_selected_move
                    selected_source = "phase22e66_immediate_mate_reply_guard"
                    phase22e66_guard_override_applied = True

        base_well_selected_move = strategic.base_well_selected_move
        intent_override_applied = bool(getattr(strategic, "queen_override_applied", False)) or bool(
            getattr(strategic, "intent_override_applied", False)
        )
        regression_well_score = int(getattr(strategic, "regression_well_score", 0))

        try:
            selected_move_is_legal = chess.Move.from_uci(selected_move) in board.legal_moves
        except Exception:
            selected_move_is_legal = False

        token_value = token or os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token_value)
        live_env_enabled = os.environ.get("AION_LICHESS_LIVE", "") == "1"

        all_live_gates_passed = bool(
            game_id
            and target_level in {2, 3, 8}
            and selected_move_is_legal
            and explicit_live_send_authorized
            and human_operator_confirmed
            and live_game_stream_confirmed
            and one_move_gate_enabled
            and live_sender_enabled
            and allow_real_post
            and token_present
            and live_env_enabled
        )

        move_post_attempted = False
        move_post_succeeded = False
        move_post_status_code = 0
        move_post_error = ""

        if all_live_gates_passed:
            move_post_attempted = True
            move_post_succeeded, move_post_status_code, move_post_error = self._post_move(
                token=token_value,
                game_id=game_id,
                move_uci=selected_move,
                timeout_seconds=timeout_seconds,
            )

        trace_payload = {
            "game_id": game_id,
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "selected_move": selected_move,
            "selected_move_is_legal": selected_move_is_legal,
            "active_intent": active_intent,
            "intent_override_applied": intent_override_applied,
            "all_live_gates_passed": all_live_gates_passed,
            "move_post_attempted": move_post_attempted,
            "move_post_succeeded": move_post_succeeded,
            "move_post_status_code": move_post_status_code,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_game_id"] = game_id
        self.policy["last_selected_move"] = selected_move
        self.policy["last_active_intent"] = active_intent
        self.policy["last_trace_hash"] = trace_hash

        if move_post_attempted:
            self.policy["post_attempt_count"] = int(self.policy.get("post_attempt_count", 0)) + 1
        if move_post_succeeded:
            self.policy["post_success_count"] = int(self.policy.get("post_success_count", 0)) + 1
        if not all_live_gates_passed:
            self.policy["blocked_count"] = int(self.policy.get("blocked_count", 0)) + 1

        evidence = {
            "phase22e59_rolling_plan_live_sender_integration_used": True,
            "phase22e58_rolling_strategic_plan_used": True,
            "phase22e58_phase": rolling_plan.phase,
            "phase22e58_primary_plan": rolling_plan.primary_plan,
            "phase22e58_selected_plan_move": rolling_plan.selected_plan_move,
            "phase22e59_plan_filtered_move": plan_filtered_move,
            "phase22e59_rolling_plan_override_applied": rolling_plan_override_applied,
            "phase22e59_monte_carlo_plan_guard_applied": monte_carlo_plan_guard_applied,
            "phase22e62_parallel_opponent_beam_router_live_sender_integration_used": True,
            "phase22e61_parallel_opponent_beam_router_used": phase22e61_router_used,
            "phase22e61_selected_move": phase22e61_selected_move,
            "phase22e61_trace_hash": phase22e61_trace_hash,
            "phase22e62_router_override_applied": phase22e61_router_override_applied,
            "phase22e63_router_survived_monte_carlo": phase22e63_router_survived_monte_carlo,
            "phase22e65_queen_intrusion_final_guard_used": phase22e65_queen_intrusion_final_guard_used,
            "phase22e65_queen_intrusion_override_applied": phase22e65_queen_intrusion_override_applied,
            "phase22e65_queen_intrusion_square": phase22e65_queen_intrusion_square,
            "phase22e65_guard_selected_move": phase22e65_guard_selected_move,
            "phase22e65_guard_selected_source": phase22e65_guard_selected_source,
            "phase22e68_forced_mate_horizon_guard_used": phase22e68_forced_mate_horizon_guard_used,
            "phase22e68_forced_mate_horizon_detected": phase22e68_forced_mate_horizon_detected,
            "phase22e68_forcing_reply": phase22e68_forcing_reply,
            "phase22e68_guard_selected_move": phase22e68_guard_selected_move,
            "phase22e68_guard_override_applied": phase22e68_guard_override_applied,
            "phase22e66_immediate_mate_reply_guard_used": phase22e66_immediate_mate_reply_guard_used,
            "phase22e66_immediate_mate_reply_detected": phase22e66_immediate_mate_reply_detected,
            "phase22e66_immediate_mate_reply_move": phase22e66_immediate_mate_reply_move,
            "phase22e66_guard_selected_move": phase22e66_guard_selected_move,
            "phase22e66_guard_override_applied": phase22e66_guard_override_applied,
            "phase22e56_live_sender_decision_stack_used": True,
            "phase22e55_monte_carlo_policy_value_seed_used": True,
            "phase22e54_opponent_reply_probability_tactical_exposure_guard_used": True,
            "phase22e54_center_control_h2h4_blocked": phase22e54.center_control_h2h4_blocked,
            "phase22e55_final_selected_move": phase22e55.final_selected_move,
            "phase22e52_critical_threat_hygiene_queen_intrusion_used": True,
            "phase22e50_king_safety_threat_removal_used": True,
            "phase22e49_initiative_hygiene_used": True,
            "phase22e48_promotion_safety_queen_survival_used": True,
            "phase22e46_dynamic_intent_switching_used": True,
            "phase22e44_proactive_intent_primacy_used": True,
            "phase22e43_anti_shuffling_guard_used": True,
            "phase22e42_passed_pawn_scope_guard_used": True,
            "phase22e41_promotion_choice_guard_used": True,
            "phase22e37_intent_driven_well_used": True,
            "one_move_only": True,
            "live_gates_required": True,
            "move_legality_checked": True,
            "opening_drift_guard_inherited": True,
            "posts_only_when_all_gates_pass": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = LiveOneMoveStrategicWellSenderResult(
            kernel_version="phase22e38_full_chess_live_one_move_strategic_well_sender_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            game_id=game_id,
            input_fen=input_fen,
            side_to_move=side_to_move,
            target_level=target_level,
            selected_move=selected_move,
            selected_move_is_legal=selected_move_is_legal,
            selected_source=selected_source,
            active_intent=active_intent,
            base_well_selected_move=base_well_selected_move,
            intent_override_applied=bool(getattr(strategic, "intent_override_applied", False)) or bool(getattr(strategic, "queen_override_applied", False)),
            regression_well_score=int(getattr(strategic, "final_regression_well_score", 0)),
            explicit_live_send_authorized=explicit_live_send_authorized,
            human_operator_confirmed=human_operator_confirmed,
            live_game_stream_confirmed=live_game_stream_confirmed,
            one_move_gate_enabled=one_move_gate_enabled,
            live_sender_enabled=live_sender_enabled,
            allow_real_post=allow_real_post,
            token_present=token_present,
            live_env_enabled=live_env_enabled,
            all_live_gates_passed=all_live_gates_passed,
            move_post_attempted=move_post_attempted,
            move_post_succeeded=move_post_succeeded,
            move_post_status_code=move_post_status_code,
            move_post_error=move_post_error,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_sender_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel sends at most one live Lichess move using the Phase 22E.37 intent-driven Strategic "
                "Regression Well. It runs the Phase 22E.59 rolling-plan and Phase 22E.56 decision stack before posting and posts only when all live gates are explicitly true. It does not call Stockfish, "
                "does not use LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_live_one_move_strategic_well_sender_kernel(
    *,
    game_id: str,
    input_fen: str,
    side_to_move: str = "white",
    target_level: int = 2,
    repeated_moves: Optional[List[str]] = None,
    repeated_squares: Optional[List[str]] = None,
    explicit_live_send_authorized: bool = False,
    human_operator_confirmed: bool = False,
    live_game_stream_confirmed: bool = False,
    one_move_gate_enabled: bool = False,
    live_sender_enabled: bool = False,
    allow_real_post: bool = False,
    token: Optional[str] = None,
    timeout_seconds: int = 20,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_live_one_move_strategic_well_sender",
) -> LiveOneMoveStrategicWellSenderResult:
    return AionLiveOneMoveStrategicWellSenderKernel(memory_path=memory_path).run(
        game_id=game_id,
        input_fen=input_fen,
        side_to_move=side_to_move,
        target_level=target_level,
        repeated_moves=repeated_moves,
        repeated_squares=repeated_squares,
        explicit_live_send_authorized=explicit_live_send_authorized,
        human_operator_confirmed=human_operator_confirmed,
        live_game_stream_confirmed=live_game_stream_confirmed,
        one_move_gate_enabled=one_move_gate_enabled,
        live_sender_enabled=live_sender_enabled,
        allow_real_post=allow_real_post,
        token=token,
        timeout_seconds=timeout_seconds,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="dry_run_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Live one-move strategic well sender memory saved to: {result.memory_path}")
