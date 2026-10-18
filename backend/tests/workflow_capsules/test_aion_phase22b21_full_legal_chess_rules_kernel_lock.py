from backend.modules.aion_games import run_full_legal_chess_rules_kernel


def test_phase22b21_validates_all_rule_cases(tmp_path):
    result = run_full_legal_chess_rules_kernel(
        memory_path=tmp_path / "full_legal_rules_memory.json"
    )

    assert result.kernel_version == "phase22b21_full_legal_chess_rules_kernel_v1"
    assert result.board_size == 8
    assert result.legal_rule_case_count >= 12
    assert result.passed_rule_case_count == result.legal_rule_case_count
    assert result.failed_rule_case_count == 0
    assert result.all_rule_cases_passed is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b21_validates_special_moves(tmp_path):
    result = run_full_legal_chess_rules_kernel(
        memory_path=tmp_path / "full_legal_rules_memory.json"
    )

    assert result.castling_validated is True
    assert result.en_passant_validated is True
    assert result.promotion_validated is True
    assert result.evidence["validates_castling"] is True
    assert result.evidence["validates_en_passant"] is True
    assert result.evidence["validates_promotion"] is True


def test_phase22b21_validates_end_states_and_draws(tmp_path):
    result = run_full_legal_chess_rules_kernel(
        memory_path=tmp_path / "full_legal_rules_memory.json"
    )

    assert result.checkmate_validated is True
    assert result.stalemate_validated is True
    assert result.repetition_draw_validated is True
    assert result.fifty_move_draw_validated is True
    assert result.evidence["validates_checkmate"] is True
    assert result.evidence["validates_stalemate"] is True
    assert result.evidence["validates_repetition_draw"] is True
    assert result.evidence["validates_fifty_move_draw"] is True


def test_phase22b21_validates_check_escape_and_king_adjacency(tmp_path):
    result = run_full_legal_chess_rules_kernel(
        memory_path=tmp_path / "full_legal_rules_memory.json"
    )

    assert result.legal_check_escape_validated is True
    assert result.illegal_king_adjacency_rejected is True
    assert result.evidence["validates_legal_check_escape"] is True
    assert result.evidence["rejects_illegal_king_adjacency"] is True
    assert len(result.full_legal_rules_trace_hash) == 64


def test_phase22b21_persists_full_legal_rules_memory(tmp_path):
    memory_path = tmp_path / "full_legal_rules_memory.json"

    first = run_full_legal_chess_rules_kernel(memory_path=memory_path)
    second = run_full_legal_chess_rules_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_legal_rules_policy["kernel_run_count"] >= 2
    assert second.final_legal_rules_policy["legal_rule_validation_count"] >= 24
    assert memory_path.exists()
