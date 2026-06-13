from backend.modules.aion_games import run_full_chess_real_opponent_game_loop_kernel


def test_phase22b23_runs_real_opponent_loop(tmp_path):
    result = run_full_chess_real_opponent_game_loop_kernel(
        memory_path=tmp_path / "real_opponent_loop_memory.json"
    )

    assert result.kernel_version == "phase22b23_full_chess_real_opponent_game_loop_kernel_v1"
    assert result.board_size == 8
    assert result.turn_count == 2
    assert result.aion_turn_count == 1
    assert result.opponent_turn_count == 1
    assert result.opponent_source == "external_uci_input"
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b23_accepts_opponent_uci_and_applies_mutations(tmp_path):
    result = run_full_chess_real_opponent_game_loop_kernel(
        memory_path=tmp_path / "real_opponent_loop_memory.json"
    )

    assert result.accepted_opponent_move_count == 1
    assert result.mutation_applied_count == 2
    assert result.turns[0]["uci_move"] == "c4d5"
    assert result.turns[1]["uci_move"] == "g8f6"
    assert result.turns[0]["mutation_applied"] is True
    assert result.turns[1]["mutation_applied"] is True
    assert result.evidence["accepts_opponent_uci_move"] is True


def test_phase22b23_exports_final_fen_and_pgn(tmp_path):
    result = run_full_chess_real_opponent_game_loop_kernel(
        memory_path=tmp_path / "real_opponent_loop_memory.json"
    )

    assert result.final_fen
    assert result.final_fen != result.initial_fen
    assert result.active_color_after_loop == "w"
    assert result.pgn_export == "1. cxd5 Nf6"
    assert result.pgn_export_ok is True
    assert result.evidence["exports_final_fen"] is True
    assert result.evidence["records_pgn"] is True


def test_phase22b23_preserves_kings_and_trace_hash(tmp_path):
    result = run_full_chess_real_opponent_game_loop_kernel(
        memory_path=tmp_path / "real_opponent_loop_memory.json"
    )

    assert all(turn["king_present_after"] for turn in result.turns)
    assert result.evidence["preserves_kings"] is True
    assert len(result.final_board_hash) == 64
    assert len(result.real_opponent_loop_trace_hash) == 64


def test_phase22b23_persists_real_opponent_loop_memory(tmp_path):
    memory_path = tmp_path / "real_opponent_loop_memory.json"

    first = run_full_chess_real_opponent_game_loop_kernel(memory_path=memory_path)
    second = run_full_chess_real_opponent_game_loop_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_real_opponent_loop_policy["kernel_run_count"] >= 2
    assert second.final_real_opponent_loop_policy["real_opponent_loop_count"] >= 2
    assert second.final_real_opponent_loop_policy["mutation_applied_count"] >= 4
    assert memory_path.exists()
