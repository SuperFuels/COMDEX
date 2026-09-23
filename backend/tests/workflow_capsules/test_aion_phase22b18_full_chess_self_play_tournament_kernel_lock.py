from backend.modules.aion_games import run_full_chess_self_play_tournament_kernel


def test_phase22b18_runs_policy_tournament(tmp_path):
    result = run_full_chess_self_play_tournament_kernel(memory_path=tmp_path / "tournament_memory.json")

    assert result.kernel_version == "phase22b18_full_chess_self_play_tournament_kernel_v1"
    assert result.board_size == 8
    assert result.policy_count >= 5
    assert result.match_count >= 5
    assert result.completed_match_count == result.match_count
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b18_learned_policy_wins_tournament(tmp_path):
    result = run_full_chess_self_play_tournament_kernel(memory_path=tmp_path / "tournament_memory.json")

    assert result.tournament_winner_policy_id == "POLICY-LEARNED"
    assert result.tournament_winner_strategy == "STRAT-1 / LINE-1"
    assert result.learned_policy_win_count >= 4
    assert result.evidence["learned_policy_wins_tournament"] is True
    assert result.evidence["retains_preferred_strategy"] is True


def test_phase22b18_bad_policies_lose(tmp_path):
    result = run_full_chess_self_play_tournament_kernel(memory_path=tmp_path / "tournament_memory.json")

    assert result.greedy_policy_loss_count >= 1
    assert result.king_exposure_policy_loss_count >= 1
    assert result.material_loss_policy_loss_count >= 1
    assert result.evidence["learned_policy_beats_greedy_policy"] is True
    assert result.evidence["learned_policy_beats_king_exposure_policy"] is True
    assert result.evidence["learned_policy_beats_material_loss_policy"] is True


def test_phase22b18_outputs_standings_and_trace_hash(tmp_path):
    result = run_full_chess_self_play_tournament_kernel(memory_path=tmp_path / "tournament_memory.json")

    assert result.tournament_standings[0]["policy_id"] == "POLICY-LEARNED"
    assert len(result.tournament_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b18_persists_tournament_memory(tmp_path):
    memory_path = tmp_path / "tournament_memory.json"

    first = run_full_chess_self_play_tournament_kernel(memory_path=memory_path)
    second = run_full_chess_self_play_tournament_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_tournament_policy["kernel_run_count"] >= 2
    assert second.final_tournament_policy["tournament_run_count"] >= 2
    assert second.final_tournament_policy["completed_match_count"] >= 10
    assert second.final_tournament_policy["learned_policy_win_count"] >= 8
    assert memory_path.exists()
