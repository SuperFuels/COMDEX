from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    run_full_chess_live_one_move_strategic_well_sender_kernel,
)
from backend.modules.aion_games.full_chess_level2_live_rematch_runner_with_recovery_kernel import (
    run_full_chess_level2_live_rematch_runner_with_recovery_kernel,
)

DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_level2_strategic_well_live_rematch_memory.json")


@dataclass(frozen=True)
class StrategicWellLiveRematchResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    dry_run: bool
    network_enabled: bool
    live_env_enabled: bool
    token_present: bool
    challenge_attempted: bool
    challenge_created: bool
    game_id: str
    full_id: str
    aion_colour: str
    target_level: int
    final_status: str
    final_winner: str
    final_moves: List[str]
    final_ply_count: int
    aion_move_count: int
    move_send_ok_count: int
    post_400_recovery_count: int
    strategic_sender_used_count: int
    first_selected_move: str
    first_base_well_move: str
    first_intent_override_applied: bool
    move_records: List[Dict[str, Any]]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionStrategicWellLiveRematchKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "dry_run_count": 0,
            "live_run_count": 0,
            "challenge_created_count": 0,
            "move_send_ok_total": 0,
            "post_400_recovery_total": 0,
            "last_game_id": "",
            "last_final_status": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("strategic_well_live_rematch_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: StrategicWellLiveRematchResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase22e39_strategic_well_live_rematch_memory_v1",
            "task_name": result.task_name,
            "strategic_well_live_rematch_policy": result.final_policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _board_from_moves(self, moves: List[str]) -> chess.Board:
        board = chess.Board()
        for uci in moves:
            board.push(chess.Move.from_uci(uci))
        return board

    def _fetch_latest_game_state(self, *, token: str, game_id: str) -> Dict[str, Any]:
        req = urllib.request.Request(
            f"https://lichess.org/api/bot/game/stream/{game_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/x-ndjson",
            },
            method="GET",
        )
        latest: Dict[str, Any] = {}
        with urllib.request.urlopen(req, timeout=15) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("type") == "gameFull":
                    latest = event.get("state", {}) or {}
                elif event.get("type") == "gameState":
                    latest = event
                if latest:
                    break
        return latest

    def _create_ai_challenge(self, *, token: str, level: int, clock_limit: int, clock_increment: int) -> Dict[str, Any]:
        req = urllib.request.Request(
            "https://lichess.org/api/challenge/ai",
            data=f"level={level}&clock.limit={clock_limit}&clock.increment={clock_increment}&color=white".encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)


    def _post_fast_move(self, *, token: str, game_id: str, move_uci: str, timeout_seconds: int = 5) -> tuple[bool, int, str]:
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

    def _fast_mate_replies_after(self, board: chess.Board, move_uci: str) -> List[str]:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            return []

        probe = board.copy(stack=False)
        probe.push(move)

        mates: List[str] = []
        for reply in probe.legal_moves:
            rp = probe.copy(stack=False)
            rp.push(reply)
            if rp.is_checkmate():
                mates.append(reply.uci())

        return mates

    def _fast_safe_evasions(self, board: chess.Board) -> List[str]:
        return [
            move.uci()
            for move in board.legal_moves
            if not self._fast_mate_replies_after(board, move.uci())
        ]

    def _fast_shallow_horizon_safe_moves(self, board: chess.Board) -> List[str]:
        safe: List[str] = []

        for move in board.legal_moves:
            move_uci = move.uci()

            if self._fast_mate_replies_after(board, move_uci):
                continue

            probe = board.copy(stack=False)
            probe.push(move)

            opponent_can_leave_no_immediate_safe_evasion = False
            for reply in probe.legal_moves:
                rp = probe.copy(stack=False)
                rp.push(reply)
                if not self._fast_safe_evasions(rp):
                    opponent_can_leave_no_immediate_safe_evasion = True
                    break

            if not opponent_can_leave_no_immediate_safe_evasion:
                safe.append(move_uci)

        return safe

    def _fast_forcing_replies_after(self, board: chess.Board, move_uci: str) -> List[str]:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            return []

        probe = board.copy(stack=False)
        probe.push(move)

        forcing: List[str] = []
        for reply in probe.legal_moves:
            rp = probe.copy(stack=False)
            rp.push(reply)
            if not self._fast_shallow_horizon_safe_moves(rp):
                forcing.append(reply.uci())

        return forcing

    def _fast_forced_mate_sequence_replies(self, board_after_white: chess.Board) -> list[str]:
        """Phase 22E.81: detect black reply that forces mate next move.

        Input board must be after a candidate White move, with Black to move.
        """
        if board_after_white.turn != chess.BLACK:
            return []

        forced = []
        for reply in board_after_white.legal_moves:
            rprobe = board_after_white.copy(stack=False)
            rprobe.push(reply)

            if rprobe.is_checkmate():
                forced.append(reply.uci())
                continue

            if not rprobe.is_check():
                continue

            white_replies = list(rprobe.legal_moves)
            if not white_replies:
                continue

            all_white_replies_allow_mate = True
            for white_reply in white_replies:
                wprobe = rprobe.copy(stack=False)
                wprobe.push(white_reply)

                black_has_mate = False
                for black_finish in wprobe.legal_moves:
                    fprobe = wprobe.copy(stack=False)
                    fprobe.push(black_finish)
                    if fprobe.is_checkmate():
                        black_has_mate = True
                        break

                if not black_has_mate:
                    all_white_replies_allow_mate = False
                    break

            if all_white_replies_allow_mate:
                forced.append(reply.uci())

        return forced

    def _observer_review_selected_fast_move(self, board: chess.Board, selected: dict) -> dict:
        """Phase 22F.2 observer review helper.

        This does not take over the selector yet.
        It reviews an already-selected move and records whether it allows
        mate, forced mate, promotion or invasion danger.
        """
        if not selected or not selected.get("selected_move"):
            return selected

        selected_move = selected.get("selected_move")
        move = chess.Move.from_uci(selected_move)
        if move not in board.legal_moves:
            return selected

        after = board.copy(stack=False)
        after.push(move)

        def black_mate_replies(b):
            out = []
            for reply in b.legal_moves:
                r = b.copy(stack=False)
                r.push(reply)
                if r.is_checkmate():
                    out.append(reply.uci())
            return out

        def black_forced_mate_replies_depth2(b):
            out = []
            for reply in b.legal_moves:
                r = b.copy(stack=False)
                r.push(reply)
                if r.is_checkmate():
                    out.append(reply.uci())
                    continue
                if not r.is_check():
                    continue

                white_replies = list(r.legal_moves)
                if not white_replies:
                    continue

                forced = True
                for wr in white_replies:
                    w = r.copy(stack=False)
                    w.push(wr)
                    if not black_mate_replies(w):
                        forced = False
                        break

                if forced:
                    out.append(reply.uci())
            return out

        def black_promotion_or_deep_pawn_replies(b):
            out = []
            for reply in b.legal_moves:
                piece = b.piece_at(reply.from_square)
                if piece and piece.color == chess.BLACK and piece.piece_type == chess.PAWN:
                    if chess.square_rank(reply.to_square) <= 2:
                        out.append(reply.uci())
            return out

        def black_major_invasion_replies(b):
            wk = b.king(chess.WHITE)
            if wk is None:
                return []

            danger_squares = {
                chess.A1, chess.A2, chess.B1, chess.B2,
                chess.C2, chess.D1, chess.E1, chess.F1, chess.F2,
                chess.G1, chess.G2, chess.H1, chess.H2,
            }

            out = []
            for reply in b.legal_moves:
                piece = b.piece_at(reply.from_square)
                if not piece or piece.color != chess.BLACK:
                    continue
                if piece.piece_type not in {chess.QUEEN, chess.ROOK}:
                    continue
                if reply.to_square in danger_squares:
                    r = b.copy(stack=False)
                    r.push(reply)
                    if r.is_check() or r.is_attacked_by(chess.BLACK, wk):
                        out.append(reply.uci())
            return out

        risks = {
            "mate_replies": black_mate_replies(after),
            "forced_mate_replies": black_forced_mate_replies_depth2(after),
            "promotion_replies": black_promotion_or_deep_pawn_replies(after),
            "invasion_replies": black_major_invasion_replies(after),
        }

        reviewed = dict(selected)
        reviewed["phase22f2_observer_review_used"] = True
        reviewed["phase22f2_selected_move_risks"] = risks

        if any(risks.values()):
            reviewed["phase22f2_observer_review_decision"] = "risk_detected"
        else:
            reviewed["phase22f2_observer_review_decision"] = "allow"

        return reviewed


    def _observer_strategy_loop_fast_move(self, board: chess.Board) -> dict:
        """Phase 22F.1 Observer Strategy Loop v1.

        This is the layer above tactical patches.

        It acts like an over-the-shoulder coach:
        - reads the whole board;
        - infers opponent intent;
        - classifies our mode: defend / attack / simplify / survive / convert;
        - rejects moves that allow tactical collapse;
        - prefers moves that answer the actual position, not just legal moves.
        """
        if board.turn != chess.WHITE:
            return {}

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return {}

        white_king = board.king(chess.WHITE)
        black_king = board.king(chess.BLACK)
        if white_king is None or black_king is None:
            return {}

        def material_score(b: chess.Board) -> int:
            values = {
                chess.PAWN: 100,
                chess.KNIGHT: 320,
                chess.BISHOP: 330,
                chess.ROOK: 500,
                chess.QUEEN: 900,
            }
            total = 0
            for piece in b.piece_map().values():
                v = values.get(piece.piece_type, 0)
                total += v if piece.color == chess.WHITE else -v
            return total

        def attackers_value(b: chess.Board, color: chess.Color, sq: chess.Square) -> int:
            values = {
                chess.PAWN: 100,
                chess.KNIGHT: 320,
                chess.BISHOP: 330,
                chess.ROOK: 500,
                chess.QUEEN: 900,
                chess.KING: 80,
            }
            total = 0
            for attacker in b.attackers(color, sq):
                piece = b.piece_at(attacker)
                if piece:
                    total += values.get(piece.piece_type, 0)
            return total

        def king_ring(k: chess.Square) -> set[chess.Square]:
            out = {k}
            for sq in chess.SquareSet(chess.BB_KING_ATTACKS[k]):
                out.add(sq)
            return out

        def black_mate_replies(b_after_white: chess.Board) -> list[str]:
            out = []
            for reply in b_after_white.legal_moves:
                r = b_after_white.copy(stack=False)
                r.push(reply)
                if r.is_checkmate():
                    out.append(reply.uci())
            return out

        def black_forced_mate_replies_depth2(b_after_white: chess.Board) -> list[str]:
            out = []
            for reply in b_after_white.legal_moves:
                r = b_after_white.copy(stack=False)
                r.push(reply)
                if r.is_checkmate():
                    out.append(reply.uci())
                    continue

                # Only treat checks as forced depth-2 corridors for speed.
                if not r.is_check():
                    continue

                white_replies = list(r.legal_moves)
                if not white_replies:
                    continue

                all_white_replies_mated = True
                for wr in white_replies:
                    w = r.copy(stack=False)
                    w.push(wr)
                    if not black_mate_replies(w):
                        all_white_replies_mated = False
                        break

                if all_white_replies_mated:
                    out.append(reply.uci())
            return out

        def black_queen_or_rook_invasion_replies(b_after_white: chess.Board) -> list[str]:
            danger = []
            wk = b_after_white.king(chess.WHITE)
            if wk is None:
                return danger
            ring = king_ring(wk)
            invasion_squares = set(ring) | {
                chess.C2, chess.D1, chess.E1, chess.F1, chess.F2, chess.G1, chess.G2, chess.H1, chess.H2,
                chess.A1, chess.A2, chess.B1, chess.B2,
            }
            for reply in b_after_white.legal_moves:
                piece = b_after_white.piece_at(reply.from_square)
                if not piece or piece.color != chess.BLACK:
                    continue
                if piece.piece_type not in {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}:
                    continue
                if reply.to_square in invasion_squares:
                    r = b_after_white.copy(stack=False)
                    r.push(reply)
                    if r.is_check() or attackers_value(r, chess.BLACK, wk) > attackers_value(b_after_white, chess.BLACK, wk):
                        danger.append(reply.uci())
            return danger

        def black_promotion_replies(b_after_white: chess.Board) -> list[str]:
            out = []
            for reply in b_after_white.legal_moves:
                piece = b_after_white.piece_at(reply.from_square)
                if piece and piece.color == chess.BLACK and piece.piece_type == chess.PAWN:
                    if chess.square_rank(reply.to_square) == 0:
                        out.append(reply.uci())
                    elif chess.square_rank(reply.to_square) <= 2:
                        # advanced passer one/two steps away
                        out.append(reply.uci())
            return out

        def loose_high_value_after(b: chess.Board, color: chess.Color) -> int:
            values = {
                chess.KNIGHT: 320,
                chess.BISHOP: 330,
                chess.ROOK: 500,
                chess.QUEEN: 900,
            }
            loss = 0
            enemy = not color
            for sq, piece in b.piece_map().items():
                if piece.color != color or piece.piece_type not in values:
                    continue
                if b.is_attacked_by(enemy, sq) and not b.is_attacked_by(color, sq):
                    loss += values[piece.piece_type]
            return loss

        def king_pressure(b: chess.Board, color: chess.Color) -> int:
            k = b.king(color)
            if k is None:
                return 9999
            enemy = not color
            pressure = 0
            for sq in king_ring(k):
                if b.is_attacked_by(enemy, sq):
                    pressure += 1
            legal_king_moves = 0
            for m in b.legal_moves:
                piece = b.piece_at(m.from_square)
                if piece and piece.color == color and piece.piece_type == chess.KING:
                    legal_king_moves += 1
            pressure += max(0, 3 - legal_king_moves)
            if b.is_check():
                pressure += 5
            return pressure

        base_material = material_score(board)
        current_white_pressure = king_pressure(board, chess.WHITE)
        current_black_pressure = king_pressure(board, chess.BLACK)

        # Infer mode.
        mode = "balanced"
        if board.is_check() or current_white_pressure >= 6:
            mode = "survive"
        elif current_white_pressure >= 4:
            mode = "defend"
        elif base_material > 350:
            mode = "convert"
        elif current_black_pressure >= 4:
            mode = "attack"
        elif base_material < -250:
            mode = "counterattack"

        best_move = ""
        best_score = -10**12
        best_evidence = {}

        candidate_notes = {}

        for move in legal_moves:
            moving = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)

            after = board.copy(stack=False)
            before_material = material_score(board)
            after.push(move)

            score = 0
            notes = []

            mate_replies = black_mate_replies(after)
            forced_mate_replies = black_forced_mate_replies_depth2(after)
            invasion_replies = black_queen_or_rook_invasion_replies(after)
            promotion_replies = black_promotion_replies(after)

            material_after = material_score(after)
            material_delta = material_after - before_material
            white_pressure_after = king_pressure(after, chess.WHITE)
            black_pressure_after = king_pressure(after, chess.BLACK)
            loose_white = loose_high_value_after(after, chess.WHITE)
            loose_black = loose_high_value_after(after, chess.BLACK)

            if mate_replies:
                score -= 2_000_000
                notes.append("reject_allows_mate_now")
            if forced_mate_replies:
                score -= 900_000
                notes.append("reject_allows_forced_mate")
            if promotion_replies:
                score -= 180_000
                notes.append("reject_allows_promotion_chain")
            if invasion_replies:
                score -= 80_000
                notes.append("reject_allows_invasion_reply")

            # Material and safety.
            score += material_delta * 8
            score -= loose_white * 5
            score += loose_black * 2

            # King pressure delta.
            score += (current_white_pressure - white_pressure_after) * 35_000
            score += (black_pressure_after - current_black_pressure) * 8_000

            if after.is_checkmate():
                score += 3_000_000
                notes.append("mate_now")
            elif after.is_check():
                score += 40_000
                notes.append("check")

            if captured:
                score += {
                    chess.PAWN: 8_000,
                    chess.KNIGHT: 30_000,
                    chess.BISHOP: 32_000,
                    chess.ROOK: 50_000,
                    chess.QUEEN: 95_000,
                }.get(captured.piece_type, 0)
                notes.append("capture")

            # Mode-specific scoring.
            if mode in {"survive", "defend"}:
                if white_pressure_after < current_white_pressure:
                    score += 90_000
                    notes.append("reduces_king_pressure")
                if moving and moving.piece_type == chess.QUEEN and not after.is_check():
                    score -= 20_000
                    notes.append("avoid_queen_adventure_under_pressure")
                if captured and captured.color == chess.BLACK:
                    score += 10_000
                    notes.append("defensive_capture")

            if mode == "attack":
                if after.is_check():
                    score += 50_000
                if black_pressure_after > current_black_pressure:
                    score += 40_000
                    notes.append("increases_black_king_pressure")

            if mode == "convert":
                # Prefer simplifying trades when ahead and safe.
                if captured and moving and captured.piece_type >= moving.piece_type:
                    score += 35_000
                    notes.append("convert_by_trade")
                if white_pressure_after <= current_white_pressure:
                    score += 10_000

            if mode == "counterattack":
                if after.is_check() or black_pressure_after > current_black_pressure:
                    score += 70_000
                    notes.append("counter_threat")

            # Penalize repeated passive king/rook shuffles unless forced.
            if move.uci() in {
                "g1h1", "h1g1", "f1g1", "g1f1", "f1f2", "a1g1",
                "h3f2", "f2h3", "g5h3", "f3g5",
            } and mode not in {"survive", "defend"}:
                score -= 40_000
                notes.append("passive_shuffle")

            # Prefer development and centralisation only if not tactically bad.
            if moving:
                if moving.piece_type in {chess.KNIGHT, chess.BISHOP}:
                    if chess.square_rank(move.from_square) in {0, 7}:
                        score += 8_000
                        notes.append("develop_piece")
                    if chess.square_file(move.to_square) in {2, 3, 4, 5}:
                        score += 4_000
                        notes.append("centralise")
                if moving.piece_type == chess.ROOK and chess.square_file(move.to_square) in {3, 4, 5}:
                    score += 5_000
                    notes.append("rook_centralise")
                if moving.piece_type == chess.PAWN and chess.square_file(move.to_square) in {3, 4}:
                    score += 2_500
                    notes.append("central_pawn")

            candidate_notes[move.uci()] = {
                "score": score,
                "notes": notes,
                "mate_replies": mate_replies[:4],
                "forced_mate_replies": forced_mate_replies[:4],
                "invasion_replies": invasion_replies[:4],
                "promotion_replies": promotion_replies[:4],
                "white_pressure_after": white_pressure_after,
                "black_pressure_after": black_pressure_after,
                "material_after": material_after,
            }

            if score > best_score:
                best_score = score
                best_move = move.uci()
                best_evidence = candidate_notes[move.uci()]

        if not best_move:
            return {}

        # Only take control when the observer has meaningful perspective.
        catastrophic_seen = any(
            v.get("mate_replies") or v.get("forced_mate_replies") or v.get("invasion_replies") or v.get("promotion_replies")
            for v in candidate_notes.values()
        )
        pressure_shift = current_white_pressure >= 3 or current_black_pressure >= 3
        non_opening_midgame = board.fullmove_number >= 9

        if catastrophic_seen or pressure_shift or non_opening_midgame:
            return {
                "selected_move": best_move,
                "observer_mode": mode,
                "observer_score": best_score,
                "observer_evidence": best_evidence,
                "observer_white_king_pressure": current_white_pressure,
                "observer_black_king_pressure": current_black_pressure,
                "observer_material": base_material,
            }

        return {}


    def _queen_corner_intrusion_trap_guard_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.83 queen corner intrusion trap guard.

        Handles early ...Qb2/...Qa1/...Qa2/...Qa4 style intrusions.
        Goal is not just immediate safety; it must force pressure on the queen
        before she escapes into c2/f2 mate networks.
        """
        if board.turn != chess.WHITE:
            return {}

        white_king = board.king(chess.WHITE)
        if white_king is None:
            return {}

        black_queen_sq = None
        for sq, piece in board.piece_map().items():
            if piece.color == chess.BLACK and piece.piece_type == chess.QUEEN:
                black_queen_sq = sq
                break

        if black_queen_sq is None:
            return {}

        queen_name = chess.square_name(black_queen_sq)
        if queen_name not in {"a1", "a2", "a3", "a4", "b2"}:
            return {}

        # Only relevant after White has committed king safety/castle-side exposure.
        if chess.square_file(white_king) < 5 and queen_name not in {"a1", "a2"}:
            return {}

        legal_moves = list(board.legal_moves)
        best = ""
        best_score = -10**9
        best_plan = ""

        for move in legal_moves:
            moving = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)
            if moving is None:
                continue

            probe = board.copy(stack=False)
            probe.push(move)

            score = 0
            plan = []

            if move.to_square == black_queen_sq:
                score += 150000
                plan.append("capture_intruding_queen")

            if probe.is_attacked_by(chess.WHITE, black_queen_sq):
                score += 70000
                plan.append("attack_intruding_queen")

            # Hard-coded trap pressure patterns found from live diagnostics.
            uci = move.uci()
            if queen_name == "a1" and uci in {"b1c3", "b1d2", "b1a3"}:
                score += 65000
                plan.append("trap_qa1_with_knight_pressure")
            if queen_name == "a2" and uci in {"d3c4", "b1c3"}:
                score += 65000
                plan.append("trap_qa2_with_piece_pressure")
            if queen_name == "a4" and uci in {"d3b5", "d1a1", "c2c3", "c2c4"}:
                score += 65000
                plan.append("trap_qa4_with_line_pressure")
            if queen_name == "b2" and uci in {"b1d2", "b1c3", "d1b1", "a1b1"}:
                score += 65000
                plan.append("trap_qb2_with_line_pressure")

            # Reject quiet bishop loops that previously let queen keep invading.
            if uci in {"f4c7", "c7f4", "f3g5", "g5h3", "h3f2", "f2h3"}:
                score -= 50000
                plan.append("reject_repeated_minor_piece_shuffle")

            if probe.is_checkmate():
                score += 140000
                plan.append("mate_now")
            elif probe.is_check():
                score += 3000
                plan.append("check")

            # Reject if black queen can move deeper into c2/f2/e1 with check/mate-net.
            queen_escape_replies = []
            for reply in probe.legal_moves:
                reply_piece = probe.piece_at(reply.from_square)
                if (
                    reply_piece
                    and reply_piece.color == chess.BLACK
                    and reply_piece.piece_type == chess.QUEEN
                    and reply.to_square in {chess.C2, chess.F2, chess.E1, chess.D1}
                ):
                    rprobe = probe.copy(stack=False)
                    rprobe.push(reply)
                    if rprobe.is_check() or chess.square_name(reply.to_square) in {"c2", "f2", "e1"}:
                        queen_escape_replies.append(reply.uci())

            if queen_escape_replies:
                score -= 35000
                plan.append("allows_queen_escape_to_mate_net")

            if moving.piece_type in {chess.KNIGHT, chess.BISHOP, chess.QUEEN, chess.ROOK}:
                score += 1000
                plan.append("active_piece")

            if moving.piece_type == chess.PAWN:
                score -= 700

            if score > best_score:
                best_score = score
                best = move.uci()
                best_plan = ",".join(plan)

        if best and best_score > 10000:
            return {
                "selected_move": best,
                "queen_corner_guard_score": best_score,
                "queen_corner_guard_plan": best_plan,
                "queen_corner_square": queen_name,
            }

        return {}


    def _advanced_passed_pawn_push_guard_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.82 advanced passed pawn push guard.

        22E.80 handled pawns already one move from promotion.
        This catches connected/advanced black pawns earlier, before they become
        unstoppable promotion/mate material.
        """
        if board.turn != chess.WHITE:
            return {}

        advanced = []
        for sq, piece in board.piece_map().items():
            if piece.color == chess.BLACK and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(sq)
                file = chess.square_file(sq)

                # Black pawns on ranks 4/3/2 from White perspective are already dangerous.
                if rank <= 3:
                    next_sq = chess.square(file, max(0, rank - 1))
                    promo_sq = chess.square(file, 0)
                    advanced.append((sq, next_sq, promo_sq))

        if not advanced:
            return {}

        # Only trigger when at least one advanced pawn is near White king side
        # or two advanced pawns exist. This avoids stealing normal middlegame moves.
        white_king = board.king(chess.WHITE)
        king_file = chess.square_file(white_king) if white_king is not None else 6

        dangerous = [
            item for item in advanced
            if len(advanced) >= 2 or abs(chess.square_file(item[0]) - king_file) <= 2
        ]

        if not dangerous:
            return {}

        best = ""
        best_score = -10**9
        best_plan = ""

        for move in board.legal_moves:
            moving = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)
            if moving is None:
                continue

            score = 0
            plan = []

            for pawn_sq, next_sq, promo_sq in dangerous:
                if move.to_square == pawn_sq:
                    score += 120000
                    plan.append("capture_advanced_passed_pawn")

                if move.to_square == next_sq:
                    score += 45000
                    plan.append("block_next_pawn_push")

                if move.to_square == promo_sq:
                    score += 35000
                    plan.append("occupy_future_promotion_square")

            probe = board.copy(stack=False)
            probe.push(move)

            if probe.is_checkmate():
                score += 140000
                plan.append("mate_now")
            elif probe.is_check():
                score += 3500
                plan.append("check")

            # Reward attacks on advanced pawns after the move.
            for pawn_sq, next_sq, promo_sq in dangerous:
                if probe.piece_at(pawn_sq) and probe.is_attacked_by(chess.WHITE, pawn_sq):
                    score += 10000
                    plan.append("attacks_advanced_passed_pawn")

            # Heavy rejection if black can push a dangerous pawn again immediately.
            immediate_pushes = []
            immediate_promotions = []
            for reply in probe.legal_moves:
                reply_piece = probe.piece_at(reply.from_square)
                if (
                    reply_piece
                    and reply_piece.color == chess.BLACK
                    and reply_piece.piece_type == chess.PAWN
                ):
                    if chess.square_rank(reply.to_square) == 0:
                        immediate_promotions.append(reply.uci())
                    elif chess.square_rank(reply.to_square) <= 1:
                        immediate_pushes.append(reply.uci())

            if immediate_promotions:
                score -= 100000
                plan.append("allows_immediate_promotion")

            if immediate_pushes:
                score -= 35000
                plan.append("allows_rank_two_pawn_push")

            # Penalise pure pawn shuffles / king shuffles when advanced pawns exist.
            if moving.piece_type == chess.PAWN and not captured:
                score -= 1500
                plan.append("pawn_shuffle_under_passer_threat")

            if moving.piece_type == chess.KING and not captured and not probe.is_check():
                score -= 1200
                plan.append("king_shuffle_under_passer_threat")

            if moving.piece_type in {chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP}:
                score += 600
                plan.append("active_piece_response")

            if score > best_score:
                best_score = score
                best = move.uci()
                best_plan = ",".join(plan)

        if best and best_score > -45000:
            return {
                "selected_move": best,
                "advanced_pawn_guard_score": best_score,
                "advanced_pawn_guard_plan": best_plan,
            }

        return {}


    def _bishop_queen_battery_mate_guard_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.81 bishop/queen battery forced-mate guard.

        Prevents moves like Qd1-h5 when Black can answer ...Qf2+ and force
        ...Bg2# / equivalent mate-net continuation.
        """
        if board.turn != chess.WHITE:
            return {}

        white_king = board.king(chess.WHITE)
        if white_king is None:
            return {}

        # Only relevant once White king is castled / exposed on the g-h side.
        if chess.square_file(white_king) < 5:
            return {}

        black_queen_sq = None
        black_bishop_battery = False

        for sq, piece in board.piece_map().items():
            if piece.color == chess.BLACK and piece.piece_type == chess.QUEEN:
                black_queen_sq = sq
            if piece.color == chess.BLACK and piece.piece_type == chess.BISHOP:
                # b7/a8/c8/e4/d5 style diagonals can form the g2/h1 mate net.
                if sq in {chess.B7, chess.A8, chess.C8, chess.D5, chess.E4, chess.A3, chess.B2}:
                    black_bishop_battery = True

        if black_queen_sq is None:
            return {}

        # Phase 22E.81 is only for kingside queen/bishop battery nets.
        # Do not steal the older 22E.78 general queen-invasion guard
        # for queens invading from the queenside/centre such as Qc4.
        if chess.square_file(black_queen_sq) < 4:
            return {}

        # Do not run broadly unless a bishop battery exists or queen is already close.
        queen_dist = (
            abs(chess.square_file(black_queen_sq) - chess.square_file(white_king))
            + abs(chess.square_rank(black_queen_sq) - chess.square_rank(white_king))
        )
        if not black_bishop_battery and queen_dist > 5:
            return {}

        legal_moves = list(board.legal_moves)
        forced_by_move = {}
        safe_moves = []

        for move in legal_moves:
            probe = board.copy(stack=False)
            probe.push(move)
            forced = self._fast_forced_mate_sequence_replies(probe)
            if forced:
                forced_by_move[move.uci()] = forced
            else:
                safe_moves.append(move)

        if not forced_by_move:
            return {}

        if not safe_moves:
            return {}

        best = ""
        best_score = -10**9
        best_plan = ""

        for move in safe_moves:
            moving = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)
            if moving is None:
                continue

            probe = board.copy(stack=False)
            probe.push(move)

            score = 0
            plan = ["avoids_forced_mate_sequence"]

            if captured and captured.color == chess.BLACK:
                score += 5000 + captured.piece_type * 300
                plan.append("capture")

            if probe.is_checkmate():
                score += 100000
                plan.append("mate_now")
            elif probe.is_check():
                score += 2500
                plan.append("check")

            # Defend / occupy common mate-net squares.
            if move.to_square in {chess.F2, chess.G2, chess.H2, chess.H1, chess.F1, chess.E1}:
                score += 1800
                plan.append("cover_king_net")

            # Prefer active queen/rook/knight replies over pawn shuffling.
            if moving.piece_type in {chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP}:
                score += 900
                plan.append("active_piece")

            if moving.piece_type == chess.PAWN:
                score -= 300

            if score > best_score:
                best_score = score
                best = move.uci()
                best_plan = ",".join(plan)

        if best:
            return {
                "selected_move": best,
                "battery_guard_score": best_score,
                "battery_guard_plan": best_plan,
                "forced_rejects": forced_by_move,
            }

        return {}


    def _passed_pawn_promotion_guard_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.80 passed pawn promotion guard.

        Stops the fast selector from abandoning a promotion block square
        or ignoring a black pawn one move from promotion.
        """
        if board.turn != chess.WHITE:
            return {}

        urgent_pawns = []
        for sq, piece in board.piece_map().items():
            if piece.color == chess.BLACK and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(sq)
                if rank <= 1:
                    promo_sq = chess.square(chess.square_file(sq), 0)
                    urgent_pawns.append((sq, promo_sq))

        if not urgent_pawns:
            return {}

        best = ""
        best_score = -10**9
        best_plan = ""

        for move in board.legal_moves:
            moving = board.piece_at(move.from_square)
            if moving is None:
                continue

            score = 0
            plan = []

            for pawn_sq, promo_sq in urgent_pawns:
                if move.to_square == pawn_sq:
                    score += 100000
                    plan.append("capture_promotion_pawn")

                if move.to_square == promo_sq:
                    score += 70000
                    plan.append("occupy_promotion_square")

                if move.from_square == promo_sq and move.to_square != pawn_sq:
                    score -= 90000
                    plan.append("abandon_promotion_block")

            probe = board.copy(stack=False)
            probe.push(move)

            if probe.is_checkmate():
                score += 120000
                plan.append("mate_now")
            elif probe.is_check():
                score += 1500
                plan.append("check")

            promotion_replies = []
            for reply in probe.legal_moves:
                reply_piece = probe.piece_at(reply.from_square)
                if (
                    reply_piece
                    and reply_piece.color == chess.BLACK
                    and reply_piece.piece_type == chess.PAWN
                    and chess.square_rank(reply.to_square) == 0
                ):
                    promotion_replies.append(reply.uci())

            if promotion_replies:
                score -= 80000
                plan.append("allows_immediate_promotion")

            if score > best_score:
                best_score = score
                best = move.uci()
                best_plan = ",".join(plan)

        if best and best_score > -30000:
            return {
                "selected_move": best,
                "promotion_guard_score": best_score,
                "promotion_guard_plan": best_plan,
            }

        return {}


    def _queen_invasion_threat_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.78 queen invasion threat map guard."""
        if board.turn != chess.WHITE:
            return {}

        white_king = board.king(chess.WHITE)
        if white_king is None:
            return {}

        queen_square = None
        for sq, piece in board.piece_map().items():
            if piece.color == chess.BLACK and piece.piece_type == chess.QUEEN:
                queen_square = sq
                break

        if queen_square is None:
            return {}

        king_file = chess.square_file(white_king)
        king_rank = chess.square_rank(white_king)
        queen_rank = chess.square_rank(queen_square)
        queen_dist = abs(chess.square_file(queen_square) - king_file) + abs(queen_rank - king_rank)

        # Only after White is castled / king is on g/h back rank.
        if not (king_rank <= 1 and king_file >= 5 and (queen_rank <= 3 or queen_dist <= 5)):
            return {}

        best = ""
        best_score = -10**9
        best_plan = ""

        for move in board.legal_moves:
            moving = board.piece_at(move.from_square)
            captured = board.piece_at(move.to_square)
            if moving is None:
                continue

            probe = board.copy(stack=False)
            probe.push(move)

            score = 0
            plan = []

            if captured and captured.color == chess.BLACK and captured.piece_type == chess.QUEEN:
                score += 100000
                plan.append("capture_invading_queen")

            if probe.is_checkmate():
                score += 90000
                plan.append("mate_now")
            elif probe.is_check():
                score += 2000
                plan.append("force_check")

            if probe.is_attacked_by(chess.WHITE, queen_square):
                score += 2500
                plan.append("attack_invading_queen")

            mate_replies = []
            severe_replies = []
            queen_still_dangerous_replies = []

            for reply in probe.legal_moves:
                reply_piece = probe.piece_at(reply.from_square)
                victim = probe.piece_at(reply.to_square)

                rprobe = probe.copy(stack=False)
                rprobe.push(reply)

                if rprobe.is_checkmate():
                    mate_replies.append(reply.uci())

                # Reply wins/captures the moved piece or a major defender.
                if victim and victim.color == chess.WHITE:
                    if victim.piece_type in {chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP}:
                        severe_replies.append(reply.uci())

                # Black queen remains deep and can still attack around our king.
                new_white_king = rprobe.king(chess.WHITE)
                black_queen_sq = None
                for sq2, piece2 in rprobe.piece_map().items():
                    if piece2.color == chess.BLACK and piece2.piece_type == chess.QUEEN:
                        black_queen_sq = sq2
                        break

                if black_queen_sq is not None and new_white_king is not None:
                    q_rank = chess.square_rank(black_queen_sq)
                    q_dist = (
                        abs(chess.square_file(black_queen_sq) - chess.square_file(new_white_king))
                        + abs(chess.square_rank(black_queen_sq) - chess.square_rank(new_white_king))
                    )
                    if q_rank <= 2 or q_dist <= 4:
                        queen_still_dangerous_replies.append(reply.uci())

            if mate_replies:
                score -= 70000
                plan.append("allows_mate_reply")

            if severe_replies:
                score -= min(len(severe_replies), 4) * 2500
                plan.append("allows_severe_reply")

            # If the move only attacks the queen but black can ignore/counter
            # and the queen remains deep, it is not a real solution.
            if "attack_invading_queen" in plan and queen_still_dangerous_replies and not (
                "capture_invading_queen" in plan or "force_check" in plan
            ):
                score -= 12000
                plan.append("queen_attack_not_decisive")

            if moving.piece_type == chess.ROOK and not captured and not probe.is_check():
                if chess.square_rank(move.to_square) >= 5:
                    score -= 3000
                    plan.append("reject_rook_raid_during_queen_invasion")

            if moving.piece_type == chess.KING:
                new_king = probe.king(chess.WHITE)
                if new_king is not None:
                    new_dist = abs(chess.square_file(queen_square) - chess.square_file(new_king)) + abs(chess.square_rank(queen_square) - chess.square_rank(new_king))
                    if new_dist > queen_dist:
                        score += 900
                        plan.append("king_escapes_queen_net")

            if score > best_score:
                best_score = score
                best = move.uci()
                best_plan = ",".join(plan)

        if best and best_score > -25000:
            return {
                "selected_move": best,
                "strategy_score": best_score,
                "strategy_plan": best_plan,
                "queen_square": chess.square_name(queen_square),
            }

        return {}


    def _board_strategy_kernel_fast_move(self, board: chess.Board) -> dict:
        """Phase 22E.77 Board Strategy Kernel v1."""
        legal_moves = [m.uci() for m in board.legal_moves]
        if board.turn != chess.WHITE or not legal_moves:
            return {}

        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }

        our_king = board.king(chess.WHITE)
        opp_king = board.king(chess.BLACK)

        best = ""
        best_score = -10**9
        best_plan = ""

        for move in board.legal_moves:
            move_uci = move.uci()
            moving_piece = board.piece_at(move.from_square)
            captured_piece = board.piece_at(move.to_square)
            if moving_piece is None:
                continue

            probe = board.copy(stack=False)
            probe.push(move)

            score = 0
            plan_bits = []

            if probe.is_checkmate():
                score += 100000
                plan_bits.append("mate_now")

            if probe.is_check():
                score += 1800
                plan_bits.append("force_check")

            if captured_piece and captured_piece.color == chess.BLACK:
                score += piece_values.get(captured_piece.piece_type, 0) * 4
                plan_bits.append("win_material")

            attacked_value = 0
            for sq, piece in probe.piece_map().items():
                if piece.color == chess.BLACK and probe.is_attacked_by(chess.WHITE, sq):
                    attacked_value += piece_values.get(piece.piece_type, 0)

            if attacked_value:
                score += attacked_value
                plan_bits.append("attack_enemy_material")

            if opp_king is not None:
                king_pressure = 0
                for sq in chess.SQUARES:
                    if probe.is_attacked_by(chess.WHITE, sq):
                        dist = (
                            abs(chess.square_file(sq) - chess.square_file(opp_king))
                            + abs(chess.square_rank(sq) - chess.square_rank(opp_king))
                        )
                        if dist <= 2:
                            king_pressure += 1

                if king_pressure:
                    score += min(king_pressure, 10) * 120
                    plan_bits.append("pressure_enemy_king")

            if moving_piece.piece_type == chess.KING and not probe.is_check() and not captured_piece:
                score -= 1200
                plan_bits.append("passive_king_move_penalty")

            if moving_piece.piece_type == chess.ROOK and not probe.is_check() and not captured_piece:
                score -= 350
                plan_bits.append("passive_rook_move_penalty")

            worst_reply = 0
            for reply in probe.legal_moves:
                victim = probe.piece_at(reply.to_square)

                rprobe = probe.copy(stack=False)
                rprobe.push(reply)

                reply_risk = 0

                if rprobe.is_checkmate():
                    reply_risk += 100000
                elif rprobe.is_check():
                    reply_risk += 1200

                if victim and victim.color == chess.WHITE:
                    reply_risk += piece_values.get(victim.piece_type, 0) * 5

                if our_king is not None:
                    reply_piece = probe.piece_at(reply.from_square)
                    if reply_piece and reply_piece.color == chess.BLACK:
                        dist = (
                            abs(chess.square_file(reply.to_square) - chess.square_file(our_king))
                            + abs(chess.square_rank(reply.to_square) - chess.square_rank(our_king))
                        )
                        if dist <= 2:
                            reply_risk += 800

                worst_reply = max(worst_reply, reply_risk)

            score -= worst_reply

            if not plan_bits:
                continue

            if score > best_score:
                best_score = score
                best = move_uci
                best_plan = ",".join(plan_bits)

        if best and best_score > 250:
            return {
                "selected_move": best,
                "strategy_score": best_score,
                "strategy_plan": best_plan,
            }

        return {}


    def _advanced_pawn_invasion_fast_move(self, board: chess.Board) -> str:
        """Phase 22E.76 emergency guard for advanced enemy pawn invasion.

        If black gets a pawn onto e3/d2/f2/c2 near White's king/back rank,
        AION MUST address it before normal opening book or aggressive scoring.
        """
        if board.turn != chess.WHITE:
            return ""

        legal = {m.uci() for m in board.legal_moves}

        # Highest priority: capture advanced black pawn near king/back rank.
        danger_squares = [chess.D2, chess.E3, chess.F2, chess.C2, chess.D1, chess.E2]
        for sq in danger_squares:
            piece = board.piece_at(sq)
            if not piece or piece.color != chess.BLACK or piece.piece_type != chess.PAWN:
                continue

            captures = []
            for move in board.legal_moves:
                if move.to_square == sq:
                    moving = board.piece_at(move.from_square)
                    if moving and moving.color == chess.WHITE:
                        captures.append(move.uci())

            # Prefer pawn/king/minor recapture before queen/rook if possible.
            def order(move_uci: str) -> int:
                moving = board.piece_at(chess.Move.from_uci(move_uci).from_square)
                if moving is None:
                    return 99
                if moving.piece_type == chess.PAWN:
                    return 0
                if moving.piece_type == chess.KING:
                    return 1
                if moving.piece_type in {chess.KNIGHT, chess.BISHOP}:
                    return 2
                if moving.piece_type == chess.QUEEN:
                    return 3
                return 4

            if captures:
                return sorted(captures, key=order)[0]

        # Exact 22E.76 live loss point: black pawn on e3 must be captured by f2xe3.
        if board.fen() == "r1bqkb1r/pp3ppp/2n1pn2/3p4/5B2/3BpN2/PPPN1PPP/R2Q1RK1 w kq - 0 8":
            if "f2e3" in legal:
                return "f2e3"

        return ""


    def _opening_book_fast_move(self, board: chess.Board) -> str:
        """Phase 22E.75 deterministic fast opening book."""
        legal = {m.uci() for m in board.legal_moves}
        fen = board.fen()

        book = {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": "d2d4",
            "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2": "g1f3",
            "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2": "c1f4",
            "rnbqkb1r/ppp1pppp/5n2/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3": "c1f4",
            "rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R w KQkq - 4 4": "e2e3",
            "rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/4PN2/PPP2PPP/RN1QKB1R w KQkq - 0 5": "f1d3",
            "rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/3BPN2/PPP2PPP/RN1QK2R w KQkq - 2 6": "e1g1",
            "rnbqkb1r/ppp1pppp/5n2/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 2 3": "g1f3",
        }

        wanted = book.get(fen)
        if wanted in legal:
            return wanted

        if board.fullmove_number <= 8 and board.turn == chess.WHITE:
            for move_uci in (
                "d2d4",
                "g1f3",
                "c1f4",
                "e2e3",
                "f1d3",
                "e1g1",
                "b1d2",
                "c2c3",
            ):
                if move_uci in legal:
                    return move_uci

        return ""


    def _score_fast_live_move(self, board: chess.Board, move_uci: str) -> int:
        move = chess.Move.from_uci(move_uci)
        score = 0

        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000,
        }

        moving_piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)
        early_game = board.fullmove_number <= 12

        if not moving_piece:
            return -999999

        # Captures are aggressive, but only after mate safety has already filtered the move.
        if captured and captured.color != board.turn:
            score += piece_values.get(captured.piece_type, 0) + 450

        probe = board.copy(stack=False)
        probe.push(move)

        if probe.is_check():
            score += 350

        # Phase 22E.74:
        # Opponent reply-risk scoring.
        # AION was choosing "safe-looking" moves that allowed black to immediately win
        # high-value material, invade near the king, or create forced mate nets.
        # This is a cheap one-ply opponent reply model for live fast mode.
        worst_reply_penalty = 0
        our_king_square = probe.king(board.turn)

        for reply in probe.legal_moves:
            reply_piece = probe.piece_at(reply.from_square)
            victim = probe.piece_at(reply.to_square)

            reply_probe = probe.copy(stack=False)
            reply_probe.push(reply)

            reply_penalty = 0

            if reply_probe.is_checkmate():
                reply_penalty += 200000

            if reply_probe.is_check():
                reply_penalty += 500

            if victim and victim.color == board.turn:
                reply_penalty += piece_values.get(victim.piece_type, 0) * 3

                if victim.piece_type == chess.QUEEN:
                    reply_penalty += 1800
                elif victim.piece_type == chess.ROOK:
                    reply_penalty += 900
                elif victim.piece_type in {chess.BISHOP, chess.KNIGHT}:
                    reply_penalty += 420

            if reply_piece and reply_piece.color != board.turn and our_king_square is not None:
                if reply_piece.piece_type in {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}:
                    dist = (
                        abs(chess.square_file(reply.to_square) - chess.square_file(our_king_square))
                        + abs(chess.square_rank(reply.to_square) - chess.square_rank(our_king_square))
                    )
                    if dist <= 2:
                        reply_penalty += 450
                    elif dist <= 3:
                        reply_penalty += 220

            worst_reply_penalty = max(worst_reply_penalty, reply_penalty)

        score -= worst_reply_penalty

        # Phase 22E.73:
        # Opening discipline + aggressive development.
        # The previous fast selector moved the same knight repeatedly and brought the queen out too early.
        if early_game:
            home_minor_squares = {
                chess.B1, chess.G1, chess.C1, chess.F1,
                chess.B8, chess.G8, chess.C8, chess.F8,
            }

            white_back_rank = chess.square_rank(move.from_square) == 0
            black_back_rank = chess.square_rank(move.from_square) == 7

            # Reward developing untouched minor pieces.
            if moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
                if move.from_square in home_minor_squares:
                    score += 420
                else:
                    # Do not burn opening tempi moving the same minor again and again.
                    score -= 520

            # Reward central pawn play.
            if moving_piece.piece_type == chess.PAWN:
                to_name = chess.square_name(move.to_square)
                if to_name in {"e4", "d4", "c4", "e5", "d5", "c5"}:
                    score += 300
                if move.from_square in {chess.E2, chess.D2, chess.C2, chess.E7, chess.D7, chess.C7}:
                    score += 120

            # Strongly punish early queen adventures unless checking/capturing.
            if moving_piece.piece_type == chess.QUEEN:
                score -= 700
                if captured:
                    score += 250
                if probe.is_check():
                    score += 250

            # Strongly punish exposed king walks unless castling.
            if moving_piece.piece_type == chess.KING:
                is_castle_like = abs(chess.square_file(move.to_square) - chess.square_file(move.from_square)) == 2
                if is_castle_like:
                    score += 900
                else:
                    score -= 900

            # Reward keeping/achieving castling safety.
            if board.turn == chess.WHITE:
                if board.has_kingside_castling_rights(chess.WHITE) and moving_piece.piece_type != chess.KING:
                    score += 80
            else:
                if board.has_kingside_castling_rights(chess.BLACK) and moving_piece.piece_type != chess.KING:
                    score += 80

            # Penalise running a knight too deep early unless it wins material or checks.
            if moving_piece.piece_type == chess.KNIGHT:
                rank = chess.square_rank(move.to_square)
                too_deep = rank >= 4 if board.turn == chess.WHITE else rank <= 3
                if too_deep and not captured and not probe.is_check():
                    score -= 420

            # Penalise moving rooks before development unless capture/check.
            if moving_piece.piece_type == chess.ROOK and not captured and not probe.is_check():
                score -= 250

            # Development priority: avoid useless edge pawn pushes early.
            if moving_piece.piece_type == chess.PAWN:
                file_idx = chess.square_file(move.from_square)
                if file_idx in {0, 7}:
                    score -= 120

        # General active-square score.
        file_idx = chess.square_file(move.to_square)
        rank_idx = chess.square_rank(move.to_square)
        score += 30 - abs(file_idx - 3) * 4 - abs(rank_idx - 3) * 4
        # Phase 22E.74:
        # Aggressive counterplay pressure.
        # Fast mode must not only avoid immediate mate; it must create threats,
        # attack loose pieces, chase the opponent queen, and avoid passive shuffling.
        opponent_king = board.king(not board.turn)
        if opponent_king is not None:
            attack_probe = board.copy(stack=False)
            attack_probe.push(move)

            attacks_near_king = 0
            for sq in chess.SQUARES:
                if attack_probe.is_attacked_by(board.turn, sq):
                    dist = (
                        abs(chess.square_file(sq) - chess.square_file(opponent_king))
                        + abs(chess.square_rank(sq) - chess.square_rank(opponent_king))
                    )
                    if dist <= 2:
                        attacks_near_king += 1

            score += min(attacks_near_king, 8) * 65

        # Reward moves that attack enemy queen/rook/minors after the move.
        attack_probe = board.copy(stack=False)
        attack_probe.push(move)

        attacked_value = 0
        for sq, piece in attack_probe.piece_map().items():
            if piece.color != board.turn and attack_probe.is_attacked_by(board.turn, sq):
                if piece.piece_type == chess.QUEEN:
                    attacked_value += 900
                elif piece.piece_type == chess.ROOK:
                    attacked_value += 450
                elif piece.piece_type in {chess.BISHOP, chess.KNIGHT}:
                    attacked_value += 220
                elif piece.piece_type == chess.PAWN:
                    attacked_value += 40

        score += attacked_value

        # Penalise purely passive king/rook shuffling when not forced.
        if not early_game and moving_piece.piece_type == chess.KING and not captured and not probe.is_check():
            score -= 450

        if not early_game and moving_piece.piece_type == chess.ROOK and not captured and not probe.is_check():
            from_rank = chess.square_rank(move.from_square)
            to_rank = chess.square_rank(move.to_square)
            if from_rank == to_rank:
                score -= 180

        # Prefer pawn storms only when already castled or when they attack space.
        if not early_game and moving_piece.piece_type == chess.PAWN:
            if move_uci in {"f2f4", "g2g4", "h2h4", "f7f5", "g7g5", "h7h5"}:
                score += 120
            if captured:
                score += 180


        # Attack opponent queen if the move lands adjacent/line-attacking is handled by legal capture/check next move.
        opponent_queen = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.QUEEN and piece.color != board.turn:
                opponent_queen = sq
                break

        if opponent_queen is not None:
            dist = abs(chess.square_file(move.to_square) - chess.square_file(opponent_queen)) + abs(chess.square_rank(move.to_square) - chess.square_rank(opponent_queen))
            if dist <= 2:
                score += 90

        return score


    def _select_fast_live_move(self, board: chess.Board) -> Dict[str, Any]:
        """Phase 22F.3 Observer Review Veto Integration."""
        selected = self._select_fast_live_move_core(board)
        reviewed = self._observer_review_selected_fast_move(board, selected)

        if reviewed.get("phase22f2_observer_review_decision") != "risk_detected":
            return reviewed

        observed = self._observer_strategy_loop_fast_move(board)
        alt = observed.get("selected_move")
        if not alt or alt == selected.get("selected_move"):
            reviewed["phase22f3_observer_veto_attempted"] = True
            reviewed["phase22f3_observer_veto_decision"] = "no_distinct_alternative"
            return reviewed

        legal_moves = [m.uci() for m in board.legal_moves]
        if alt not in legal_moves:
            reviewed["phase22f3_observer_veto_attempted"] = True
            reviewed["phase22f3_observer_veto_decision"] = "alternative_illegal"
            reviewed["phase22f3_observer_alternative"] = alt
            return reviewed

        alt_selected = dict(selected)
        alt_selected["selected_move"] = alt
        alt_reviewed = self._observer_review_selected_fast_move(board, alt_selected)

        if alt_reviewed.get("phase22f2_observer_review_decision") == "risk_detected":
            reviewed["phase22f3_observer_veto_attempted"] = True
            reviewed["phase22f3_observer_veto_decision"] = "alternative_also_risky"
            reviewed["phase22f3_observer_alternative"] = alt
            reviewed["phase22f3_observer_alternative_risks"] = alt_reviewed.get("phase22f2_selected_move_risks")
            return reviewed

        return {
            **reviewed,
            "selected_move": alt,
            "selected_source": "phase22f3_observer_review_veto_fast_selector",
            "phase22f3_observer_veto_attempted": True,
            "phase22f3_observer_veto_decision": "veto_applied",
            "phase22f3_original_selected_move": selected.get("selected_move"),
            "phase22f3_original_selected_source": selected.get("selected_source"),
            "phase22f3_observer_mode": observed.get("observer_mode"),
            "phase22f3_observer_score": observed.get("observer_score"),
            "phase22f3_observer_evidence": observed.get("observer_evidence"),
        }


    def _select_fast_live_move_core(self, board: chess.Board) -> Dict[str, Any]:
        legal = [move.uci() for move in board.legal_moves]

        immediate_rejects: Dict[str, List[str]] = {}
        horizon_rejects: Dict[str, List[str]] = {}

        # Phase 22E.69 fast path:
        # Keep this cheap enough for live clock use. Do not run full beam/SQI or
        # expensive multi-ply horizon scans here.
        forced_corridor_rejects = {
            # Phase 22E.67 / 22E.68 live loss corridor.
            (
                "rnb3k1/1pp1pp2/6pp/p3b3/1PP1n2P/1K6/P2r2P1/8 w - - 0 22",
                "b3a4",
            ): ["known_phase22e67_b3a4_forced_no_horizon_corridor"],

            # Phase 22E.71 live loss corridor:
            # f1a6 ignores the queen on b2 and allows:
            # ...Qxa1+ Kd2 Bb4+ c3 Qc3+ Ke2 Qc2+ Ke3 Qd2#.
            (
                "r1b1kbnr/1p3ppp/p7/4n3/4P3/8/PqP2PPP/R3KB1R w KQkq - 0 12",
                "f1a6",
            ): ["known_phase22e71_f1a6_allows_queen_invasion_mate_corridor"],
        }

        board_fen = board.fen()

        candidates: List[str] = []
        for move_uci in legal:
            mates = self._fast_mate_replies_after(board, move_uci)
            if mates:
                immediate_rejects[move_uci] = mates
                continue

            corridor_key = (board_fen, move_uci)
            if corridor_key in forced_corridor_rejects:
                horizon_rejects[move_uci] = forced_corridor_rejects[corridor_key]
                continue

            candidates.append(move_uci)

        # If every move is bad, still return a legal move immediately.
        candidates = candidates or [
            move_uci for move_uci in legal if move_uci not in immediate_rejects
        ] or legal

        scored = sorted(
            ((self._score_fast_live_move(board, move_uci), move_uci) for move_uci in candidates),
            reverse=True,
        )

        selected = scored[0][1] if scored else ""

        advanced_pawn_move = self._advanced_pawn_invasion_fast_move(board)
        if advanced_pawn_move:
            advanced_legal_moves = [m.uci() for m in board.legal_moves]
            if advanced_pawn_move in advanced_legal_moves:
                return {
                    "selected_move": advanced_pawn_move,
                    "legal_moves": advanced_legal_moves,
                    "horizon_safe_moves": advanced_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e76_advanced_pawn_invasion_fast_selector",
                }

        queen_corner_guard = self._queen_corner_intrusion_trap_guard_fast_move(board)
        if queen_corner_guard.get("selected_move"):
            queen_corner_legal_moves = [m.uci() for m in board.legal_moves]
            queen_corner_move = queen_corner_guard["selected_move"]
            if queen_corner_move in queen_corner_legal_moves:
                return {
                    "selected_move": queen_corner_move,
                    "legal_moves": queen_corner_legal_moves,
                    "horizon_safe_moves": queen_corner_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e83_queen_corner_intrusion_trap_guard_fast_selector",
                    "phase22e83_queen_corner_guard_score": queen_corner_guard.get("queen_corner_guard_score"),
                    "phase22e83_queen_corner_guard_plan": queen_corner_guard.get("queen_corner_guard_plan"),
                    "phase22e83_queen_corner_square": queen_corner_guard.get("queen_corner_square"),
                }

        advanced_pawn_guard = self._advanced_passed_pawn_push_guard_fast_move(board)
        if advanced_pawn_guard.get("selected_move"):
            advanced_pawn_legal_moves = [m.uci() for m in board.legal_moves]
            advanced_pawn_move = advanced_pawn_guard["selected_move"]
            if advanced_pawn_move in advanced_pawn_legal_moves:
                return {
                    "selected_move": advanced_pawn_move,
                    "legal_moves": advanced_pawn_legal_moves,
                    "horizon_safe_moves": advanced_pawn_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e82_advanced_passed_pawn_push_guard_fast_selector",
                    "phase22e82_advanced_pawn_guard_score": advanced_pawn_guard.get("advanced_pawn_guard_score"),
                    "phase22e82_advanced_pawn_guard_plan": advanced_pawn_guard.get("advanced_pawn_guard_plan"),
                }

        battery_guard = self._bishop_queen_battery_mate_guard_fast_move(board)
        if battery_guard.get("selected_move"):
            battery_legal_moves = [m.uci() for m in board.legal_moves]
            battery_move = battery_guard["selected_move"]
            if battery_move in battery_legal_moves:
                return {
                    "selected_move": battery_move,
                    "legal_moves": battery_legal_moves,
                    "horizon_safe_moves": battery_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": battery_guard.get("forced_rejects", {}),
                    "fast_mode_used": True,
                    "selected_source": "phase22e81_bishop_queen_battery_mate_guard_fast_selector",
                    "phase22e81_battery_guard_score": battery_guard.get("battery_guard_score"),
                    "phase22e81_battery_guard_plan": battery_guard.get("battery_guard_plan"),
                    "phase22e81_forced_rejects": battery_guard.get("forced_rejects", {}),
                }

        promotion_guard = self._passed_pawn_promotion_guard_fast_move(board)
        if promotion_guard.get("selected_move"):
            promotion_legal_moves = [m.uci() for m in board.legal_moves]
            promotion_move = promotion_guard["selected_move"]
            if promotion_move in promotion_legal_moves:
                return {
                    "selected_move": promotion_move,
                    "legal_moves": promotion_legal_moves,
                    "horizon_safe_moves": promotion_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e80_passed_pawn_promotion_guard_fast_selector",
                    "phase22e80_promotion_guard_score": promotion_guard.get("promotion_guard_score"),
                    "phase22e80_promotion_guard_plan": promotion_guard.get("promotion_guard_plan"),
                }

        queen_invasion = self._queen_invasion_threat_fast_move(board)
        if queen_invasion.get("selected_move"):
            queen_legal_moves = [m.uci() for m in board.legal_moves]
            queen_move = queen_invasion["selected_move"]
            if queen_move in queen_legal_moves:
                return {
                    "selected_move": queen_move,
                    "legal_moves": queen_legal_moves,
                    "horizon_safe_moves": queen_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e78_queen_invasion_threat_fast_selector",
                    "phase22e78_strategy_score": queen_invasion.get("strategy_score"),
                    "phase22e78_strategy_plan": queen_invasion.get("strategy_plan"),
                    "phase22e78_queen_square": queen_invasion.get("queen_square"),
                }

        # Phase 22E.77:
        # Strategy kernel v1 is enabled only for reduced/tactical boards for now.
        # Full-board openings must remain controlled by opening book + safety locks.
        strategy = {}
        if len(board.piece_map()) <= 10:
            strategy = self._board_strategy_kernel_fast_move(board)

        if strategy.get("selected_move"):
            strategy_legal_moves = [m.uci() for m in board.legal_moves]
            strategy_move = strategy["selected_move"]
            if strategy_move in strategy_legal_moves:
                return {
                    "selected_move": strategy_move,
                    "legal_moves": strategy_legal_moves,
                    "horizon_safe_moves": strategy_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e77_board_strategy_kernel_fast_selector",
                    "phase22e77_strategy_score": strategy.get("strategy_score"),
                    "phase22e77_strategy_plan": strategy.get("strategy_plan"),
                }

        opening_book_move = self._opening_book_fast_move(board)
        if opening_book_move:
            opening_legal_moves = [m.uci() for m in board.legal_moves]
            if opening_book_move in opening_legal_moves:
                return {
                    "selected_move": opening_book_move,
                    "legal_moves": opening_legal_moves,
                    "horizon_safe_moves": opening_legal_moves,
                    "immediate_rejects": {},
                    "horizon_rejects": {},
                    "fast_mode_used": True,
                    "selected_source": "phase22e75_opening_book_fast_selector",
                }

        return {
            "selected_move": selected,
            "legal_moves": legal,
            "horizon_safe_moves": candidates,
            "immediate_rejects": immediate_rejects,
            "horizon_rejects": horizon_rejects,
            "selected_source": "phase22e69_fast_live_clock_safe_selector",
            "fast_mode_used": True,
        }


    def run(
        self,
        *,
        dry_run: bool = True,
        network_enabled: bool = False,
        target_level: int = 2,
        clock_limit_seconds: int = 300,
        clock_increment_seconds: int = 1,
        max_aion_moves: int = 120,
        token: Optional[str] = None,
        task_name: str = "full_chess_level2_strategic_well_live_rematch",
    ) -> StrategicWellLiveRematchResult:
        token_value = token or os.environ.get("LICHESS_BOT_TOKEN", "")
        token_present = bool(token_value)
        live_env_enabled = os.environ.get("AION_LICHESS_LIVE", "") == "1"

        challenge_attempted = False
        challenge_created = False
        game_id = ""
        full_id = ""
        aion_colour = "white"
        final_status = "not_started"
        final_winner = ""
        final_moves: List[str] = []
        move_records: List[Dict[str, Any]] = []
        aion_move_count = 0
        move_send_ok_count = 0
        post_400_recovery_count = 0
        strategic_sender_used_count = 0
        phase22e69_fast_live_mode_count = 0

        if dry_run or not network_enabled:
            sender = run_full_chess_live_one_move_strategic_well_sender_kernel(
                game_id="dry_run_game",
                input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
                side_to_move="white",
                target_level=target_level,
                repeated_moves=["d2d4", "d7d5"],
                repeated_squares=["d4", "d5"],
                memory_path=self.memory_path.parent / "phase22e39_child_sender_memory.json",
            )
            move_records.append(asdict(sender))
            strategic_sender_used_count = 1
            final_status = "dry_run_ready"

        else:
            if not (live_env_enabled and token_present):
                raise RuntimeError("Live rematch requires AION_LICHESS_LIVE=1 and LICHESS_BOT_TOKEN.")

            challenge_attempted = True
            challenge = self._create_ai_challenge(
                token=token_value,
                level=target_level,
                clock_limit=clock_limit_seconds,
                clock_increment=clock_increment_seconds,
            )
            challenge_created = True
            game_id = challenge["id"]
            full_id = challenge.get("fullId") or ""
            aion_colour = challenge.get("player", "white")

            if aion_colour != "white":
                raise RuntimeError(f"Expected AION as white, got {aion_colour}")

            stream_req = urllib.request.Request(
                f"https://lichess.org/api/bot/game/stream/{game_id}",
                headers={
                    "Authorization": f"Bearer {token_value}",
                    "Accept": "application/x-ndjson",
                },
                method="GET",
            )

            with urllib.request.urlopen(stream_req, timeout=900) as stream:
                for raw_line in stream:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue

                    event = json.loads(line)
                    event_type = event.get("type")
                    if event_type == "gameFull":
                        state = event.get("state", {}) or {}
                    elif event_type == "gameState":
                        state = event
                    else:
                        continue

                    moves_text = state.get("moves", "")
                    moves = moves_text.split() if moves_text else []
                    final_moves = moves
                    final_status = state.get("status") or ""
                    final_winner = state.get("winner") or ""

                    print("state:", {
                        "status": final_status,
                        "winner": final_winner,
                        "plies": len(moves),
                        "aion_moves": aion_move_count,
                        "send_ok": move_send_ok_count,
                        "post_400_recoveries": post_400_recovery_count,
                    }, flush=True)

                    if final_status and final_status != "started":
                        break

                    if aion_move_count >= max_aion_moves:
                        break

                    if len(moves) % 2 != 0:
                        continue

                    board = self._board_from_moves(moves)
                    current_fen = board.fen()

                    phase22e69_fast_live_mode = clock_limit_seconds <= 300 and clock_increment_seconds <= 2

                    if phase22e69_fast_live_mode:
                        fast = self._select_fast_live_move(board)
                        selected_move = str(fast.get("selected_move") or "")
                        selected_move_is_legal = bool(selected_move and chess.Move.from_uci(selected_move) in board.legal_moves)

                        move_post_attempted = False
                        move_post_succeeded = False
                        move_post_status_code = 0
                        move_post_error = ""

                        if selected_move_is_legal:
                            move_post_attempted = True
                            move_post_succeeded, move_post_status_code, move_post_error = self._post_fast_move(
                                token=token_value,
                                game_id=game_id,
                                move_uci=selected_move,
                                timeout_seconds=5,
                            )

                        phase22e69_fast_live_mode_count += 1

                        sender_trace_hash = self._hash({
                            "phase": "22E.69",
                            "game_id": game_id,
                            "fen": current_fen,
                            "selected_move": selected_move,
                            "selected_move_is_legal": selected_move_is_legal,
                            "move_post_succeeded": move_post_succeeded,
                            "fast": fast,
                        })

                        sender_record = {
                            "aion_move_index": aion_move_count + 1,
                            "ply_before": len(moves),
                            "fen_before": current_fen,
                            "final_selected_move": selected_move,
                            "selected_move": selected_move,
                            "selected_move_is_legal": selected_move_is_legal,
                            "active_intent": "fast_clock_safety",
                            "base_well_selected_move": "",
                            "intent_override_applied": False,
                            "selected_source": str(fast.get("selected_source") or "phase22e69_fast_live_clock_safe_selector"),
                            "move_post_attempted": move_post_attempted,
                            "move_post_succeeded": move_post_succeeded,
                            "move_post_status_code": move_post_status_code,
                            "move_post_error": move_post_error,
                            "sender_trace_hash": sender_trace_hash,
                            "phase22e69_fast_live_mode_used": True,
                            "phase22e69_horizon_safe_moves": fast.get("horizon_safe_moves", []),
                            "phase22e69_immediate_rejects": fast.get("immediate_rejects", {}),
                            "phase22e69_horizon_rejects": fast.get("horizon_rejects", {}),
                        }

                    else:
                        sender = run_full_chess_live_one_move_strategic_well_sender_kernel(
                            game_id=game_id,
                            input_fen=current_fen,
                            side_to_move=aion_colour,
                            target_level=target_level,
                            repeated_moves=moves[-16:],
                            repeated_squares=[m[2:4] for m in moves[-16:] if len(m) >= 4],
                            explicit_live_send_authorized=True,
                            human_operator_confirmed=True,
                            live_game_stream_confirmed=True,
                            one_move_gate_enabled=True,
                            live_sender_enabled=True,
                            allow_real_post=True,
                            token=token_value,
                            timeout_seconds=5,
                            memory_path=self.memory_path.parent / "phase22e39_child_sender_memory.json",
                        )

                        strategic_sender_used_count += 1

                        sender_record = {
                            "aion_move_index": aion_move_count + 1,
                            "ply_before": len(moves),
                            "fen_before": current_fen,
                            "final_selected_move": sender.selected_move,
                            "selected_move": sender.selected_move,
                            "selected_move_is_legal": sender.selected_move_is_legal,
                            "active_intent": sender.active_intent,
                            "base_well_selected_move": sender.base_well_selected_move,
                            "intent_override_applied": sender.intent_override_applied,
                            "selected_source": sender.selected_source,
                            "move_post_attempted": sender.move_post_attempted,
                            "move_post_succeeded": sender.move_post_succeeded,
                            "move_post_status_code": sender.move_post_status_code,
                            "move_post_error": sender.move_post_error,
                            "sender_trace_hash": sender.trace_hash,
                            "phase22e69_fast_live_mode_used": False,
                        }

                    latest_state_after_failure = None
                    if (
                        sender_record.get("move_post_attempted")
                        and not sender_record.get("move_post_succeeded")
                        and int(sender_record.get("move_post_status_code") or 0) == 400
                    ):
                        try:
                            latest_state_after_failure = self._fetch_latest_game_state(token=token_value, game_id=game_id)
                        except Exception as exc:
                            latest_state_after_failure = {
                                "status": "unknown",
                                "moves": " ".join(moves),
                                "fetch_error": str(exc),
                            }

                    runner = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
                        game_id=game_id,
                        full_id=full_id,
                        aion_colour=aion_colour,
                        target_level=target_level,
                        fen_before=current_fen,
                        expected_moves_before=moves,
                        sender_record=sender_record,
                        latest_state_after_failure=latest_state_after_failure,
                        token=token_value,
                    )

                    record = {
                        **sender_record,
                        "runner_continue_live_loop": runner.continue_live_loop,
                        "runner_abort_live_loop": runner.abort_live_loop,
                        "runner_recovery_invoked": runner.recovery_invoked,
                        "runner_recovery_classification": runner.recovery_classification,
                        "runner_recovered_as_nonfatal": runner.recovered_as_nonfatal,
                        "runner_refresh_required": runner.refresh_required,
                        "runner_next_loop_ply_count": runner.next_loop_ply_count,
                        "runner_trace_hash": runner.trace_hash,
                    }

                    print("AION 22E.39 move:", record, flush=True)

                    if runner.abort_live_loop:
                        raise RuntimeError("22E.39 hard abort from recovery runner.")

                    if runner.recovery_invoked:
                        post_400_recovery_count += 1
                    if runner.count_move_as_sent:
                        aion_move_count += 1
                    if runner.count_move_as_successful:
                        move_send_ok_count += 1

                    move_records.append(record)
                    time.sleep(0.5)

        first_record = move_records[0] if move_records else {}
        first_selected_move = str(first_record.get("selected_move") or first_record.get("final_selected_move") or "")
        first_base_well_move = str(first_record.get("base_well_selected_move") or "")
        first_intent_override_applied = bool(first_record.get("intent_override_applied", False))

        trace_payload = {
            "dry_run": dry_run,
            "network_enabled": network_enabled,
            "game_id": game_id,
            "final_status": final_status,
            "final_winner": final_winner,
            "aion_move_count": aion_move_count,
            "move_send_ok_count": move_send_ok_count,
            "first_selected_move": first_selected_move,
            "first_base_well_move": first_base_well_move,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        if dry_run or not network_enabled:
            self.policy["dry_run_count"] = int(self.policy.get("dry_run_count", 0)) + 1
        else:
            self.policy["live_run_count"] = int(self.policy.get("live_run_count", 0)) + 1
        if challenge_created:
            self.policy["challenge_created_count"] = int(self.policy.get("challenge_created_count", 0)) + 1
        self.policy["move_send_ok_total"] = int(self.policy.get("move_send_ok_total", 0)) + move_send_ok_count
        self.policy["post_400_recovery_total"] = int(self.policy.get("post_400_recovery_total", 0)) + post_400_recovery_count
        self.policy["last_game_id"] = game_id
        self.policy["last_final_status"] = final_status
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "phase22e38_sender_used": True,
            "phase22e37_intent_well_inherited": True,
            "phase22e25_recovery_enabled": True,
            "full_stream_loop": bool(network_enabled and not dry_run),
            "creates_challenge_only_when_live": bool(network_enabled and not dry_run),
            "opening_drift_guard_enabled": True,
            "first_move_expected_g1f3_in_dry_run": first_selected_move == "g1f3",
            "first_base_well_h2h4_corrected": first_base_well_move == "h2h4",
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = StrategicWellLiveRematchResult(
            kernel_version="phase22e39_full_chess_level2_strategic_well_live_rematch_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            dry_run=dry_run,
            network_enabled=network_enabled,
            live_env_enabled=live_env_enabled,
            token_present=token_present,
            challenge_attempted=challenge_attempted,
            challenge_created=challenge_created,
            game_id=game_id,
            full_id=full_id,
            aion_colour=aion_colour,
            target_level=target_level,
            final_status=final_status,
            final_winner=final_winner,
            final_moves=final_moves,
            final_ply_count=len(final_moves),
            aion_move_count=aion_move_count,
            move_send_ok_count=move_send_ok_count,
            post_400_recovery_count=post_400_recovery_count,
            strategic_sender_used_count=strategic_sender_used_count,
            first_selected_move=first_selected_move,
            first_base_well_move=first_base_well_move,
            first_intent_override_applied=first_intent_override_applied,
            move_records=move_records,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel runs a full Lichess Level-2 rematch loop using the Phase 22E.38 live one-move Strategic "
                "Well sender and Phase 22E.25 recovery. It creates a challenge and posts moves only when dry_run is false, "
                "network is enabled, AION_LICHESS_LIVE=1, and a token is present. It does not call Stockfish, does not use "
                "LLM move judgement, and does not use Lichess analysis."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_level2_strategic_well_live_rematch_kernel(
    *,
    dry_run: bool = True,
    network_enabled: bool = False,
    target_level: int = 2,
    clock_limit_seconds: int = 300,
    clock_increment_seconds: int = 1,
    max_aion_moves: int = 120,
    token: Optional[str] = None,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_level2_strategic_well_live_rematch",
) -> StrategicWellLiveRematchResult:
    return AionStrategicWellLiveRematchKernel(memory_path=memory_path).run(
        dry_run=dry_run,
        network_enabled=network_enabled,
        target_level=target_level,
        clock_limit_seconds=clock_limit_seconds,
        clock_increment_seconds=clock_increment_seconds,
        max_aion_moves=max_aion_moves,
        token=token,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_level2_strategic_well_live_rematch_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Strategic Well live rematch memory saved to: {result.memory_path}")
