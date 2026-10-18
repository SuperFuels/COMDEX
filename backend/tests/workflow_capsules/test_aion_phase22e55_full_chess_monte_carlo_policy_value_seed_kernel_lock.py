import chess

from backend.modules.aion_games.full_chess_monte_carlo_policy_value_seed_kernel import (
    run_full_chess_monte_carlo_policy_value_seed_kernel,
)


LEVEL8_FAILURE_FEN = "r1b1k2r/p4ppp/2p1p3/2P5/2Pq4/5P2/Pb4PP/R3K2R w KQkq - 0 15"


def test_phase22e55_uses_monte_carlo_policy_value_seed(tmp_path):
    result = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=8,
        beam_width=6,
        rollout_depth=4,
        memory_path=tmp_path / "memory.json",
    )

    assert result.monte_carlo_search_used is True
    assert result.mcts_node_scoring_used is True
    assert result.self_play_rollout_used is True
    assert result.policy_prior_used is True
    assert result.value_network_seed_used is True
    assert result.self_play_memory_used is True
    assert result.final_selected_move_is_legal is True
    assert result.final_selected_source == "monte_carlo_policy_value_seed"


def test_phase22e55_rejects_base_wing_move_when_better_mcts_candidate_exists(tmp_path):
    result = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=8,
        beam_width=8,
        rollout_depth=4,
        memory_path=tmp_path / "memory.json",
    )

    board = chess.Board(LEVEL8_FAILURE_FEN)
    assert chess.Move.from_uci(result.final_selected_move) in board.legal_moves
    assert result.final_selected_move != "h2h4"
    assert any(item["selected_by_mcts"] for item in result.candidate_scores)


def test_phase22e55_candidate_scores_have_rollouts_and_ucb(tmp_path):
    result = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=8,
        beam_width=6,
        rollout_depth=4,
        memory_path=tmp_path / "memory.json",
    )

    assert len(result.candidate_scores) > 0
    assert all(item["visits"] == 8 for item in result.candidate_scores)
    assert all("ucb_score" in item for item in result.candidate_scores)
    assert all("policy_prior" in item for item in result.candidate_scores)
    assert all("value_estimate" in item for item in result.candidate_scores)


def test_phase22e55_memory_persists_self_play_policy_prior(tmp_path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=4,
        beam_width=4,
        rollout_depth=3,
        memory_path=memory_path,
    )
    second = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=4,
        beam_width=4,
        rollout_depth=3,
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert memory_path.exists()


def test_phase22e55_boundary_no_stockfish_llm_or_lichess(tmp_path):
    result = run_full_chess_monte_carlo_policy_value_seed_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        base_selected_move="h2h4",
        rollout_count=4,
        beam_width=4,
        rollout_depth=3,
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.trace_hash
