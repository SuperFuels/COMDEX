from backend.modules.aion_games import run_full_chess_tournament_learning_integration_kernel


def test_phase22b19_reads_tournament_result(tmp_path):
    result = run_full_chess_tournament_learning_integration_kernel(
        memory_path=tmp_path / "tournament_learning_memory.json"
    )

    assert result.kernel_version == "phase22b19_full_chess_tournament_learning_integration_kernel_v1"
    assert result.board_size == 8
    assert result.tournament_winner_policy_id == "POLICY-LEARNED"
    assert result.tournament_winner_strategy == "STRAT-1 / LINE-1"
    assert result.evidence["reads_tournament_result"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b19_reinforces_winner_and_penalises_losers(tmp_path):
    result = run_full_chess_tournament_learning_integration_kernel(
        memory_path=tmp_path / "tournament_learning_memory.json"
    )

    assert result.tournament_learning_update_count == 5
    assert result.positive_update_count >= 2
    assert result.penalty_update_count >= 3
    assert result.learned_policy_reinforced is True
    assert result.greedy_policy_penalised is True
    assert result.king_exposure_policy_penalised is True
    assert result.material_loss_policy_penalised is True


def test_phase22b19_prepares_next_tournament_policy(tmp_path):
    result = run_full_chess_tournament_learning_integration_kernel(
        memory_path=tmp_path / "tournament_learning_memory.json"
    )

    assert result.updated_learned_weight > result.previous_learned_weight
    assert result.updated_greedy_penalty > result.previous_greedy_penalty
    assert result.integrated_policy["next_tournament_seed_policy"] == "POLICY-LEARNED"
    assert result.next_tournament_ready is True
    assert result.evidence["prepares_next_tournament"] is True
    assert len(result.tournament_learning_trace_hash) == 64


def test_phase22b19_persists_tournament_learning_memory(tmp_path):
    memory_path = tmp_path / "tournament_learning_memory.json"

    first = run_full_chess_tournament_learning_integration_kernel(memory_path=memory_path)
    second = run_full_chess_tournament_learning_integration_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_tournament_learning_policy["kernel_run_count"] >= 2
    assert second.final_tournament_learning_policy["tournament_learning_integration_count"] >= 2
    assert second.updated_learned_weight > first.updated_learned_weight
    assert second.updated_greedy_penalty > first.updated_greedy_penalty
    assert memory_path.exists()
