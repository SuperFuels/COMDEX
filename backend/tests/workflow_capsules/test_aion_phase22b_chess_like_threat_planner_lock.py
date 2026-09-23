from backend.modules.aion_games import run_chess_like_threat_planner


def test_phase22b_detects_chess_like_threats_and_rejects_bait(tmp_path):
    result = run_chess_like_threat_planner(memory_path=tmp_path / "chess_memory.json")

    assert result.planner_version == "phase22b_chess_like_threat_planner_v1"
    assert result.adapter_loaded is True
    assert result.selected_action == "chess_safe_develop"
    assert result.rejected_action == "chess_capture_bait_pawn"
    assert result.rejected_bait is True
    assert result.avoided_mate_line is True
    assert result.avoided_knight_fork is True
    assert result.preserved_king_safety is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b_material_gain_loses_to_future_threat_score(tmp_path):
    result = run_chess_like_threat_planner(memory_path=tmp_path / "chess_memory.json")

    safe = next(e for e in result.action_evaluations if e["action_id"] == "chess_safe_develop")
    bait = next(e for e in result.action_evaluations if e["action_id"] == "chess_capture_bait_pawn")

    assert bait["immediate_gain"] > safe["immediate_gain"]
    assert bait["long_term_risk"] > safe["long_term_risk"]
    assert safe["total_score"] > bait["total_score"]
    assert "LINE-MATE-IN-SIX-1" in bait["threat_lines_triggered"]
    assert "LINE-KNIGHT-FORK-1" in bait["threat_lines_triggered"]


def test_phase22b_trace_hash_and_memory_persist(tmp_path):
    memory_path = tmp_path / "chess_memory.json"

    first = run_chess_like_threat_planner(memory_path=memory_path)
    second = run_chess_like_threat_planner(memory_path=memory_path)

    assert len(first.planner_trace_hash) == 64
    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_chess_threat_policy["planner_run_count"] >= 2
    assert second.final_chess_threat_policy["successful_threat_avoidance_count"] >= 2
    assert "mate_in_six" in second.final_chess_threat_policy["known_chess_threat_types"]
    assert memory_path.exists()
