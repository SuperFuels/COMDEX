from backend.modules.aion_games import run_full_chess_io_interface_kernel


def test_phase22b22_imports_and_exports_fen(tmp_path):
    result = run_full_chess_io_interface_kernel(memory_path=tmp_path / "io_memory.json")

    assert result.kernel_version == "phase22b22_full_chess_io_interface_kernel_v1"
    assert result.board_size == 8
    assert result.fen_input == result.fen_export
    assert result.fen_round_trip_ok is True
    assert result.active_color == "w"
    assert result.castling_rights == "KQkq"
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b22_parses_and_exports_uci(tmp_path):
    result = run_full_chess_io_interface_kernel(memory_path=tmp_path / "io_memory.json")

    assert result.uci_input == "c4d5"
    assert result.uci_move["from_square"] == "c4"
    assert result.uci_move["to_square"] == "d5"
    assert result.uci_move["promotion"] is None
    assert result.uci_move["valid_shape"] is True
    assert result.uci_round_trip_ok is True


def test_phase22b22_records_and_exports_pgn(tmp_path):
    result = run_full_chess_io_interface_kernel(memory_path=tmp_path / "io_memory.json")

    assert len(result.pgn_records) == 2
    assert result.pgn_export == "1. c4 Nf6 2. cxd5"
    assert result.pgn_export_ok is True
    assert result.evidence["records_pgn"] is True
    assert result.evidence["exports_pgn"] is True


def test_phase22b22_emits_trace_hash(tmp_path):
    result = run_full_chess_io_interface_kernel(memory_path=tmp_path / "io_memory.json")

    assert len(result.io_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b22_persists_io_memory(tmp_path):
    memory_path = tmp_path / "io_memory.json"

    first = run_full_chess_io_interface_kernel(memory_path=memory_path)
    second = run_full_chess_io_interface_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_io_policy["kernel_run_count"] >= 2
    assert second.final_io_policy["fen_import_count"] >= 2
    assert second.final_io_policy["uci_parse_count"] >= 2
    assert second.final_io_policy["pgn_export_count"] >= 2
    assert memory_path.exists()
