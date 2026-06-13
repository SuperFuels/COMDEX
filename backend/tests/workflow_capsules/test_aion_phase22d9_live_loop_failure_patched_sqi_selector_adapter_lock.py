from pathlib import Path

from backend.modules.aion_games.full_chess_live_loop_sqi_selector_adapter_kernel import (
    run_full_chess_live_loop_sqi_selector_adapter_kernel,
)


def test_phase22d9_live_loop_uses_failure_patched_selector_when_aion_turn(tmp_path: Path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.is_aion_turn is True
    assert result.selected_move
    assert result.selected_move_is_legal is True
    assert result.live_loop_move_source == "phase22d8_sqi_failure_patch_selector"
    assert result.selected_sqi_reason == "patched_sqi_failure_guard_selection"

    assert result.evidence["failure_patched_sqi_selector_used_when_aion_turn"] is True
    assert result.evidence["old_sqi_guided_selector_wrapped_by_failure_patch"] is True
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False


def test_phase22d9_live_loop_remains_dry_run_and_no_network(tmp_path: Path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.dry_run is True
    assert result.network_send_allowed is False
    assert result.network_send_attempted is False
    assert result.evidence["network_call_performed"] is False
    assert result.evidence["dry_run_default"] is True


def test_phase22d9_live_loop_no_move_when_not_aion_turn(tmp_path: Path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        aion_colour="black",
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.is_aion_turn is False
    assert result.selected_move == ""
    assert result.evidence["no_move_when_not_aion_turn"] is True


def test_phase22d9_live_loop_persists_adapter_memory(tmp_path: Path):
    memory_path = tmp_path / "adapter_memory.json"

    first = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        dry_run=True,
        network_send_allowed=False,
    )
    second = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        dry_run=True,
        network_send_allowed=False,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_adapter_policy["kernel_run_count"] == 2
    assert second.final_adapter_policy["sqi_live_selection_count"] == 2


def test_phase22d9_live_loop_has_trace_hash(tmp_path: Path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "failure_patch_memory.json",
        selector_memory_path=tmp_path / "base_selector_memory.json",
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.adapter_trace_hash
    assert result.selection_trace_hash
    assert result.sqi_trace_hash
    assert result.evidence["uses_trace_hash"] is True
