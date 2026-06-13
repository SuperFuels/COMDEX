from backend.modules.aion_games import run_full_chess_knowledge_openings_strategy_book_kernel


def test_phase22b34_loads_structured_chess_knowledge_book(tmp_path):
    result = run_full_chess_knowledge_openings_strategy_book_kernel(
        memory_path=tmp_path / "knowledge_book_memory.json"
    )

    assert result.kernel_version == "phase22b34_full_chess_knowledge_openings_strategy_book_kernel_v1"
    assert result.knowledge_book_loaded is True
    assert result.opening_principle_count >= 3
    assert result.named_opening_count >= 3
    assert result.tactical_motif_count >= 3
    assert result.strategic_pattern_count >= 3
    assert result.endgame_principle_count >= 2
    assert result.avoidance_rule_count >= 2
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b34_exposes_policy_prior_query(tmp_path):
    result = run_full_chess_knowledge_openings_strategy_book_kernel(
        memory_path=tmp_path / "knowledge_book_memory.json"
    )

    assert result.selected_query["query_id"] == "QUERY-OPENING-ENGLISH-001"
    assert result.recommended_move == "c2c4"
    assert result.selected_policy_prior == "KNOWLEDGE-PRIOR-ENGLISH-OPENING-SAFE-DEVELOPMENT"
    assert result.evidence["query_returns_recommended_move"] is True
    assert result.evidence["knowledge_is_policy_prior"] is True


def test_phase22b34_includes_avoidance_rules(tmp_path):
    result = run_full_chess_knowledge_openings_strategy_book_kernel(
        memory_path=tmp_path / "knowledge_book_memory.json"
    )

    names = {entry["name"] for entry in result.avoidance_rules}

    assert "Avoid hanging queen" in names
    assert "Avoid exposing king early" in names
    assert result.evidence["has_avoidance_rules"] is True


def test_phase22b34_emits_trace_hash(tmp_path):
    result = run_full_chess_knowledge_openings_strategy_book_kernel(
        memory_path=tmp_path / "knowledge_book_memory.json"
    )

    assert len(result.chess_knowledge_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b34_persists_knowledge_book_memory(tmp_path):
    memory_path = tmp_path / "knowledge_book_memory.json"

    first = run_full_chess_knowledge_openings_strategy_book_kernel(memory_path=memory_path)
    second = run_full_chess_knowledge_openings_strategy_book_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_chess_knowledge_policy["kernel_run_count"] >= 2
    assert second.final_chess_knowledge_policy["knowledge_book_session_count"] >= 2
    assert second.final_chess_knowledge_policy["policy_prior_weight"] > first.policy_prior_weight
    assert memory_path.exists()
