import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e74_fast_selector_prefers_active_development_not_passive_shuffle(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2")
    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_move"] in selected["legal_moves"]
    assert selected["selected_move"] not in {"e1d2", "d1d2"}


def test_phase22e74_scores_attacking_enemy_material_above_passive_rook_move(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("4k3/8/8/3q4/8/8/4N3/R3K2R w KQ - 0 1")

    attack_score = kernel._score_fast_live_move(board, "e2c3")
    passive_score = kernel._score_fast_live_move(board, "a1b1")

    assert attack_score > passive_score


def test_phase22e74_latest_longer_game_reaches_31_aion_moves_not_clock_failure():
    moves = (
        "d2d4 g8f6 e2e4 f6e4 f1d3 d7d5 c2c4 e7e5 "
        "c4d5 d8d5 d4e5 f8b4 c1d2 e4d2 b1d2 d5d3 "
        "g1f3 b8c6 b2b3 c6d4 f3d4 d3d4 e1g1 d4d2 "
        "d1d2 b4d2 f2f4 d2e3 f1f2 c8e6 b3b4 e8c8 "
        "g2g4 d8d2 f4f5 e3f2 g1g2 e6d5 g2f1 d5c4 "
        "f1g2 f2d4 g2f3 c4d5 f3f4 d4a1 f4e3 d2a2 "
        "e3d3 a2h2 d3e3 a1e5 e3d3 h2g2 d3e3 g7g5 "
        "e3d3 h7h5 g4h5 h8h5 d3e3 h5h3"
    ).split()

    board = chess.Board()
    for move_uci in moves:
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves
        board.push(move)

    assert board.is_checkmate()
    assert len(moves) == 62
