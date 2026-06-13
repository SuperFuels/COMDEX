from backend.modules.aion_games import run_full_chess_uci_engine_wrapper_kernel


def test_phase22b28_accepts_uci_and_ready_commands(tmp_path):
    result = run_full_chess_uci_engine_wrapper_kernel(
        memory_path=tmp_path / "uci_wrapper_memory.json"
    )

    assert result.kernel_version == "phase22b28_full_chess_uci_engine_wrapper_kernel_v1"
    assert result.engine_name == "AION Chess Scaffold"
    assert result.emitted_uciok is True
    assert result.emitted_readyok is True
    assert "uciok" in result.uci_stdout_lines
    assert "readyok" in result.uci_stdout_lines
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b28_accepts_position_fen_and_go(tmp_path):
    result = run_full_chess_uci_engine_wrapper_kernel(
        memory_path=tmp_path / "uci_wrapper_memory.json"
    )

    assert result.accepted_position_fen is True
    assert result.accepted_go_command is True
    assert result.accepted_command_count == 4
    assert result.uci_command_count == 4
    assert result.evidence["accepts_position_fen"] is True
    assert result.evidence["accepts_go_command"] is True


def test_phase22b28_emits_bestmove(tmp_path):
    result = run_full_chess_uci_engine_wrapper_kernel(
        memory_path=tmp_path / "uci_wrapper_memory.json"
    )

    assert result.selected_bestmove == "c4d5"
    assert result.emitted_bestmove is True
    assert "bestmove c4d5" in result.uci_stdout_lines
    assert result.evidence["emits_bestmove"] is True
    assert result.evidence["selected_bestmove_is_uci"] is True


def test_phase22b28_emits_trace_hash(tmp_path):
    result = run_full_chess_uci_engine_wrapper_kernel(
        memory_path=tmp_path / "uci_wrapper_memory.json"
    )

    assert len(result.uci_wrapper_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b28_persists_uci_wrapper_memory(tmp_path):
    memory_path = tmp_path / "uci_wrapper_memory.json"

    first = run_full_chess_uci_engine_wrapper_kernel(memory_path=memory_path)
    second = run_full_chess_uci_engine_wrapper_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_uci_wrapper_policy["kernel_run_count"] >= 2
    assert second.final_uci_wrapper_policy["uci_session_count"] >= 2
    assert second.final_uci_wrapper_policy["accepted_command_total"] >= 8
    assert second.final_uci_wrapper_policy["bestmove_total"] >= 2
    assert memory_path.exists()
