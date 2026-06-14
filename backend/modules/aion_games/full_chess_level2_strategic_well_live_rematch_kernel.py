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
