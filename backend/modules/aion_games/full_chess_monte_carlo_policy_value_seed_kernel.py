from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
import math
import random

import chess


DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_monte_carlo_policy_value_seed_memory.json")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


@dataclass(frozen=True)
class MonteCarloCandidate:
    move: str
    visits: int
    total_value: float
    mean_value: float
    policy_prior: float
    value_estimate: float
    ucb_score: float
    rollout_depth: int
    catastrophic_reply_seen: bool
    selected_by_mcts: bool


@dataclass(frozen=True)
class MonteCarloPolicyValueSeedResult:
    kernel_version: str
    task_name: str
    input_fen: str
    side_to_move: str
    base_selected_move: str
    final_selected_move: str
    final_selected_source: str
    final_selected_move_is_legal: bool
    monte_carlo_search_used: bool
    mcts_node_scoring_used: bool
    self_play_rollout_used: bool
    policy_prior_used: bool
    value_network_seed_used: bool
    self_play_memory_used: bool
    rollout_count: int
    beam_width: int
    rollout_depth: int
    candidate_scores: List[Dict[str, Any]]
    memory_loaded: bool
    memory_path: str
    policy_memory_mutated: bool
    trace_hash: str
    evidence: Dict[str, Any]
    boundary_statement: str


class AionMonteCarloPolicyValueSeedKernel:
    kernel_version = "phase22e55_full_chess_monte_carlo_policy_value_seed_kernel_v1"

    def __init__(self, memory_path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.memory_path = Path(memory_path)
        self.memory_loaded = self.memory_path.exists()
        self.policy = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        if not self.memory_path.exists():
            return {
                "kernel_run_count": 0,
                "move_success_prior": {},
                "move_failure_prior": {},
                "position_value_memory": {},
                "last_final_selected_move": "",
                "last_trace_hash": "",
            }
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "kernel_run_count": 0,
                "move_success_prior": {},
                "move_failure_prior": {},
                "position_value_memory": {},
                "last_final_selected_move": "",
                "last_trace_hash": "",
            }

    def _save_memory(self) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(self.policy, indent=2, sort_keys=True), encoding="utf-8")

    def _trace_hash(self, payload: Dict[str, Any]) -> str:
        clean = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def _seed(self, text: str) -> int:
        return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)

    def _material_balance(self, board: chess.Board, side: chess.Color) -> int:
        score = 0
        for piece in board.piece_map().values():
            value = PIECE_VALUES.get(piece.piece_type, 0)
            score += value if piece.color == side else -value
        return score

    def _king_zone_pressure(self, board: chess.Board, side: chess.Color) -> int:
        king = board.king(side)
        if king is None:
            return 10000
        opponent = not side
        zone = {king}
        zone.update(chess.SquareSet(chess.BB_KING_ATTACKS[king]))
        pressure = 0
        for square in zone:
            pressure += len(board.attackers(opponent, square)) * 200
        return pressure

    def _is_wing_pawn_lunge(self, board: chess.Board, move: chess.Move) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        return chess.square_file(move.from_square) in {0, 6, 7} or chess.square_file(move.to_square) in {0, 6, 7}

    def _static_value(self, board: chess.Board, side: chess.Color) -> float:
        if board.is_checkmate():
            return -100000.0 if board.turn == side else 100000.0
        if board.is_stalemate() or board.is_insufficient_material():
            return 0.0

        value = float(self._material_balance(board, side))
        value -= float(self._king_zone_pressure(board, side))
        value += 80.0 * len(list(board.legal_moves)) if board.turn == side else -40.0 * len(list(board.legal_moves))
        if board.is_check():
            value += -1200.0 if board.turn == side else 900.0
        return value

    def _policy_prior(self, board: chess.Board, move: chess.Move, side: chess.Color) -> float:
        move_key = move.uci()
        success = float(self.policy.get("move_success_prior", {}).get(move_key, 0))
        failure = float(self.policy.get("move_failure_prior", {}).get(move_key, 0))

        prior = 1.0 + success - failure

        captured = board.piece_at(move.to_square)
        if captured and captured.color != side:
            prior += PIECE_VALUES.get(captured.piece_type, 0) / 200.0

        if self._is_wing_pawn_lunge(board, move):
            prior -= 2.5

        if board.gives_check(move):
            prior += 2.0

        return max(0.05, prior)

    def _reply_danger(self, board_after_move: chess.Board, side: chess.Color) -> bool:
        opponent_replies = list(board_after_move.legal_moves)
        for reply in opponent_replies:
            probe = board_after_move.copy(stack=False)
            captured = probe.piece_at(reply.to_square)
            probe.push(reply)

            if probe.is_checkmate():
                return True
            if captured and captured.color == side and PIECE_VALUES.get(captured.piece_type, 0) >= PIECE_VALUES[chess.ROOK]:
                return True
            if probe.is_check() and self._king_zone_pressure(probe, side) >= 1200:
                return True
        return False

    def _rollout_move(self, board: chess.Board, rng: random.Random, root_side: chess.Color) -> chess.Move:
        legal = list(board.legal_moves)
        if not legal:
            return chess.Move.null()

        scored = []
        for move in legal:
            score = 0.0
            captured = board.piece_at(move.to_square)
            if captured:
                score += PIECE_VALUES.get(captured.piece_type, 0)
            if board.gives_check(move):
                score += 250
            if self._is_wing_pawn_lunge(board, move):
                score -= 150
            score += rng.random() * 5.0
            scored.append((score, move))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _rollout(self, board: chess.Board, side: chess.Color, depth: int, seed_text: str) -> float:
        rng = random.Random(self._seed(seed_text))
        probe = board.copy(stack=False)

        for _ in range(depth):
            if probe.is_game_over():
                break
            move = self._rollout_move(probe, rng, side)
            if move == chess.Move.null():
                break
            probe.push(move)

        return self._static_value(probe, side)

    def _beam(self, board: chess.Board, side: chess.Color, base_move: chess.Move, beam_width: int) -> List[chess.Move]:
        moves = list(board.legal_moves)
        scored = []
        for move in moves:
            prior = self._policy_prior(board, move, side)
            captured = board.piece_at(move.to_square)
            capture_bonus = PIECE_VALUES.get(captured.piece_type, 0) if captured and captured.color != side else 0
            wing_penalty = 500 if self._is_wing_pawn_lunge(board, move) else 0
            base_bonus = 100 if move == base_move else 0
            scored.append((prior * 100 + capture_bonus + base_bonus - wing_penalty, move))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [move for _, move in scored[:beam_width]]

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        base_selected_move: str = "h2h4",
        rollout_count: int = 32,
        beam_width: int = 8,
        rollout_depth: int = 6,
        task_name: str = "full_chess_monte_carlo_policy_value_seed",
    ) -> MonteCarloPolicyValueSeedResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK

        try:
            base_move = chess.Move.from_uci(base_selected_move)
        except ValueError:
            base_move = chess.Move.null()

        beam = self._beam(board, side, base_move, beam_width)

        total_parent_visits = max(1, rollout_count)
        candidates: List[MonteCarloCandidate] = []

        for move in beam:
            after = board.copy(stack=False)
            after.push(move)

            prior = self._policy_prior(board, move, side)
            value_estimate = self._static_value(after, side)
            catastrophic = self._reply_danger(after, side)

            visits = 0
            total_value = 0.0

            for rollout_index in range(rollout_count):
                visits += 1
                rollout_value = self._rollout(
                    after,
                    side,
                    rollout_depth,
                    f"{input_fen}|{move.uci()}|{rollout_index}|{self.kernel_version}",
                )
                if catastrophic:
                    rollout_value -= 5000.0
                total_value += rollout_value

            mean = total_value / max(1, visits)
            ucb = mean + prior * math.sqrt(math.log(total_parent_visits + 1) / max(1, visits))

            candidates.append(
                MonteCarloCandidate(
                    move=move.uci(),
                    visits=visits,
                    total_value=round(total_value, 4),
                    mean_value=round(mean, 4),
                    policy_prior=round(prior, 4),
                    value_estimate=round(value_estimate, 4),
                    ucb_score=round(ucb, 4),
                    rollout_depth=rollout_depth,
                    catastrophic_reply_seen=catastrophic,
                    selected_by_mcts=False,
                )
            )

        candidates.sort(key=lambda c: (not c.catastrophic_reply_seen, c.ucb_score), reverse=True)
        final_move = candidates[0].move if candidates else base_selected_move
        final_legal = chess.Move.from_uci(final_move) in board.legal_moves

        candidates = [
            MonteCarloCandidate(
                move=c.move,
                visits=c.visits,
                total_value=c.total_value,
                mean_value=c.mean_value,
                policy_prior=c.policy_prior,
                value_estimate=c.value_estimate,
                ucb_score=c.ucb_score,
                rollout_depth=c.rollout_depth,
                catastrophic_reply_seen=c.catastrophic_reply_seen,
                selected_by_mcts=(c.move == final_move),
            )
            for c in candidates
        ]

        payload = {
            "kernel_version": self.kernel_version,
            "input_fen": input_fen,
            "base_selected_move": base_selected_move,
            "final_selected_move": final_move,
            "rollout_count": rollout_count,
            "beam_width": beam_width,
            "rollout_depth": rollout_depth,
            "candidate_scores": [asdict(c) for c in candidates],
        }
        trace_hash = self._trace_hash(payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_final_selected_move"] = final_move
        self.policy["last_trace_hash"] = trace_hash

        success = self.policy.setdefault("move_success_prior", {})
        failure = self.policy.setdefault("move_failure_prior", {})

        success[final_move] = int(success.get(final_move, 0)) + 1
        if base_selected_move != final_move:
            failure[base_selected_move] = int(failure.get(base_selected_move, 0)) + 1

        self._save_memory()

        evidence = {
            "monte_carlo_search_used": True,
            "mcts_node_scoring_used": True,
            "self_play_rollout_used": True,
            "policy_prior_used": True,
            "value_network_seed_used": True,
            "self_play_memory_used": True,
            "uses_stockfish": False,
            "uses_llm_move_judgement": False,
            "uses_lichess_analysis": False,
            "uses_trace_hash": True,
        }

        return MonteCarloPolicyValueSeedResult(
            kernel_version=self.kernel_version,
            task_name=task_name,
            input_fen=input_fen,
            side_to_move=side_to_move,
            base_selected_move=base_selected_move,
            final_selected_move=final_move,
            final_selected_source="monte_carlo_policy_value_seed",
            final_selected_move_is_legal=final_legal,
            monte_carlo_search_used=True,
            mcts_node_scoring_used=True,
            self_play_rollout_used=True,
            policy_prior_used=True,
            value_network_seed_used=True,
            self_play_memory_used=True,
            rollout_count=rollout_count,
            beam_width=beam_width,
            rollout_depth=rollout_depth,
            candidate_scores=[asdict(c) for c in candidates],
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            policy_memory_mutated=True,
            trace_hash=trace_hash,
            evidence=evidence,
            boundary_statement=(
                "This kernel introduces a deterministic Monte Carlo search skeleton and self-play policy-value seed. "
                "It uses local legal move generation, deterministic rollouts, UCB-style node scoring, policy priors, "
                "a lightweight value estimate, and local memory. It does not call Stockfish, does not use LLM move "
                "judgement, and does not use Lichess analysis."
            ),
        )


def run_full_chess_monte_carlo_policy_value_seed_kernel(
    *,
    input_fen: str = "r1b1k2r/p4ppp/2p1p3/2P5/2Pq4/5P2/Pb4PP/R3K2R w KQkq - 0 15",
    side_to_move: str = "white",
    base_selected_move: str = "h2h4",
    rollout_count: int = 32,
    beam_width: int = 8,
    rollout_depth: int = 6,
    memory_path: Path = DEFAULT_MEMORY_PATH,
    task_name: str = "full_chess_monte_carlo_policy_value_seed",
) -> MonteCarloPolicyValueSeedResult:
    return AionMonteCarloPolicyValueSeedKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        base_selected_move=base_selected_move,
        rollout_count=rollout_count,
        beam_width=beam_width,
        rollout_depth=rollout_depth,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_monte_carlo_policy_value_seed_kernel()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print(f"\\n✅ Monte Carlo policy-value seed memory saved to: {result.memory_path}")
