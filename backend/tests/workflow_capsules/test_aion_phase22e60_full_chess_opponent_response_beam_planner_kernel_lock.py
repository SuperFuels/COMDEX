import chess

from backend.modules.aion_games.full_chess_opponent_response_beam_planner_kernel import (
    run_full_chess_opponent_response_beam_planner_kernel,
)


def test_phase22e60_generates_real_sqi_connected_opponent_beams(tmp_path):
    result = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_move="g1f3",
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        max_beams=8,
        connect_sqi=True,
        persist_container_record=False,
        memory_path=tmp_path / "beam_memory.json",
        task_name="phase22e60_opening_beam_test",
    )

    assert result.candidate_move_is_legal is True
    assert result.opponent_side == "black"
    assert result.opponent_legal_reply_count > 0
    assert 1 <= result.beam_count <= 8

    assert result.evidence["sqi_beam_packets_emitted"] is True
    assert result.evidence["sqi_beam_kernel_connected"] is True
    assert result.evidence["sqi_propagation_attempted"] is True
    assert result.evidence["sqi_propagation_result_count"] == result.beam_count

    assert result.qqc_control_packet["packet_type"] == "aion_chess_opponent_response_qqc_control"
    assert "control" in result.qqc_control_packet

    assert result.hexcore_field_packet["packet_type"] == "aion_chess_opponent_response_hexcore_field"
    assert result.hexcore_field_packet["container_id"]

    assert result.container_evidence_record["container_id"]
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_llm_move_judgement"] is False


def test_phase22e60_prioritises_mate_or_check_reply_beam(tmp_path):
    fen_after_f3_e5 = "rnbqkbnr/pppp1ppp/8/4p3/8/5P2/PPPPP1PP/RNBQKBNR w KQkq - 0 2"

    result = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=fen_after_f3_e5,
        side_to_move="white",
        candidate_move="g2g4",
        primary_plan="rapid_development",
        target_weakness="king_safety",
        max_beams=8,
        connect_sqi=True,
        persist_container_record=False,
        memory_path=tmp_path / "beam_memory.json",
        task_name="phase22e60_fools_mate_beam_test",
    )

    assert result.candidate_move_is_legal is True
    assert result.top_reply_move == "d8h4"
    assert result.top_beam_mode in {"mate", "check"}
    assert result.beams[0]["gives_check"] is True
    assert result.beams[0]["danger_score"] >= 0.72
    assert result.qqc_control_packet["control"]["control_priority"] == "stabilize"


def test_phase22e60_memory_mutates_and_trace_is_stable_when_persist_disabled(tmp_path):
    memory = tmp_path / "beam_memory.json"

    first = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_move="g1f3",
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        connect_sqi=True,
        persist_container_record=False,
        memory_path=memory,
        task_name="phase22e60_memory_test",
    )
    second = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_move="g1f3",
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        connect_sqi=True,
        persist_container_record=False,
        memory_path=memory,
        task_name="phase22e60_memory_test",
    )

    assert first.policy_memory_mutated is True
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2
    assert first.trace_hash == second.trace_hash


def test_phase22e60_sqi_packets_have_codex_beam_shape(tmp_path):
    result = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_move="g1f3",
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        connect_sqi=False,
        persist_container_record=False,
        memory_path=tmp_path / "beam_memory.json",
        task_name="phase22e60_packet_shape_test",
    )

    packet = result.sqi_beam_packets[0]
    assert packet["id"].startswith("aion-chess-reply-beam-")
    assert isinstance(packet["logic_tree"], dict)
    assert "glyphs" in packet
    assert "metadata" in packet
    assert packet["metadata"]["context"]["container_kind"] == "aion_chess_decision_stack"
    assert packet["origin_trace"] == "aion.phase22e60.opponent_response_beam_planner"
