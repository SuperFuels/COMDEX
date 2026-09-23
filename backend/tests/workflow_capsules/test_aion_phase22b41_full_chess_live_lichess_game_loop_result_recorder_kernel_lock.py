from backend.modules.aion_games import run_full_chess_live_lichess_game_loop_result_recorder_kernel
from backend.modules.aion_games.full_chess_live_lichess_game_loop_result_recorder_kernel import FIRST_LIVE_GAME_MOVES


def test_phase22b41_records_live_game_identity(tmp_path):
    result = run_full_chess_live_lichess_game_loop_result_recorder_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.kernel_version == "phase22b41_full_chess_live_lichess_game_loop_result_recorder_kernel_v1"
    assert result.result_mode == "recorded_live_lichess_game_loop_result"
    assert result.game_id == "cPv6iyKb"
    assert result.full_id == "cPv6iyKbavrO"
    assert result.platform == "lichess"
    assert result.account_id == "peekoo123"
    assert result.account_title == "BOT"


def test_phase22b41_records_terminal_mate_win(tmp_path):
    result = run_full_chess_live_lichess_game_loop_result_recorder_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.game_completed is True
    assert result.terminal_outcome_reached is True
    assert result.final_status == "mate"
    assert result.winner == "white"
    assert result.aion_colour == "white"
    assert result.aion_result == "win"
    assert result.evidence["aion_won"] is True


def test_phase22b41_records_moves_and_counts(tmp_path):
    result = run_full_chess_live_lichess_game_loop_result_recorder_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.moves == FIRST_LIVE_GAME_MOVES
    assert result.final_move == "e8g7"
    assert result.aion_move_count == 31
    assert result.network_move_send_count == 26
    assert result.response_ok_count == 26
    assert result.live_moves_accepted_by_lichess is True
    assert result.evidence["all_automated_network_moves_accepted"] is True


def test_phase22b41_records_opponent_and_game_type(tmp_path):
    result = run_full_chess_live_lichess_game_loop_result_recorder_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.opponent == "Stockfish level 1"
    assert result.opponent_type == "lichess_ai"
    assert result.opponent_level == 1
    assert result.rated is False
    assert result.variant == "standard"


def test_phase22b41_emits_trace_hash_and_no_llm_shortcut(tmp_path):
    result = run_full_chess_live_lichess_game_loop_result_recorder_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert len(result.trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b41_persists_result_memory(tmp_path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_live_lichess_game_loop_result_recorder_kernel(memory_path=memory_path)
    second = run_full_chess_live_lichess_game_loop_result_recorder_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_result_policy["kernel_run_count"] >= 2
    assert second.final_result_policy["recorded_live_game_count"] >= 2
    assert second.final_result_policy["recorded_live_win_count"] >= 2
    assert second.final_result_policy["recorded_network_move_total"] >= 52
    assert memory_path.exists()
