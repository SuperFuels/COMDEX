from backend.modules.aion_games import run_full_chess_knowledge_guided_move_selection_kernel


def test_phase22b35_scores_legal_candidate_moves(tmp_path):
    result = run_full_chess_knowledge_guided_move_selection_kernel(
        memory_path=tmp_path / "move_selection_memory.json"
    )

    assert result.kernel_version == "phase22b35_full_chess_knowledge_guided_move_selection_kernel_v1"
    assert result.legal_candidate_count == 6
    assert result.knowledge_prior_count >= 16
    assert result.avoidance_rule_count >= 2
    assert result.evidence["scores_legal_candidates"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b35_selects_knowledge_guided_bestmove(tmp_path):
    result = run_full_chess_knowledge_guided_move_selection_kernel(
        memory_path=tmp_path / "move_selection_memory.json"
    )

    assert result.selected_bestmove == "c2c4"
    assert result.selected_policy == "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT"
    assert result.selected_score > 0
    assert result.evidence["selects_knowledge_guided_move"] is True
    assert result.evidence["selected_move_is_legal"] is True


def test_phase22b35_penalises_bad_moves(tmp_path):
    result = run_full_chess_knowledge_guided_move_selection_kernel(
        memory_path=tmp_path / "move_selection_memory.json"
    )

    scores = {item["move"]: item for item in result.candidate_scores}

    assert scores["d1a4"]["avoidance_penalty"] > 0
    assert scores["e1e2"]["avoidance_penalty"] > 0
    assert result.highest_penalised_move == "e1e2"
    assert result.evidence["penalises_bad_queen_move"] is True
    assert result.evidence["penalises_early_king_move"] is True


def test_phase22b35_emits_trace_hash(tmp_path):
    result = run_full_chess_knowledge_guided_move_selection_kernel(
        memory_path=tmp_path / "move_selection_memory.json"
    )

    assert len(result.knowledge_guided_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b35_persists_move_selection_memory(tmp_path):
    memory_path = tmp_path / "move_selection_memory.json"

    first = run_full_chess_knowledge_guided_move_selection_kernel(memory_path=memory_path)
    second = run_full_chess_knowledge_guided_move_selection_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_move_selection_policy["kernel_run_count"] >= 2
    assert second.final_move_selection_policy["knowledge_guided_selection_session_count"] >= 2
    assert second.final_move_selection_policy["candidate_scored_total"] >= 12
    assert memory_path.exists()
