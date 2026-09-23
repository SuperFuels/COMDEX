import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e77_strategy_kernel_prefers_forcing_check_over_passive_shuffle(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("6k1/8/8/8/8/8/5PPP/4R1K1 w - - 0 1")

    strategy = kernel._board_strategy_kernel_fast_move(board)

    assert strategy["selected_move"] in {"e1e8", "e1e7"}
    assert "force_check" in strategy["strategy_plan"]


def test_phase22e77_strategy_kernel_finds_material_pressure_plan(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("4k3/8/8/3q4/8/8/4N3/R3K2R w KQ - 0 1")

    strategy = kernel._board_strategy_kernel_fast_move(board)

    assert strategy["selected_move"]
    assert any(bit in strategy["strategy_plan"] for bit in {"attack_enemy_material", "force_check", "pressure_enemy_king"})


def test_phase22e77_selector_emits_strategy_evidence_when_strategy_applies(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("6k1/8/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e77_board_strategy_kernel_fast_selector"
    assert selected["phase22e77_strategy_score"] > 250
    assert "force_check" in selected["phase22e77_strategy_plan"]


def test_phase22e77_opening_book_still_owns_start_position(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board()
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e77_advanced_pawn_guard_still_overrides_strategy(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1bqkb1r/pp3ppp/2n1pn2/3p4/5B2/3BpN2/PPPN1PPP/R2Q1RK1 w kq - 0 8")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "f2e3"
    assert selected["selected_source"] == "phase22e76_advanced_pawn_invasion_fast_selector"
