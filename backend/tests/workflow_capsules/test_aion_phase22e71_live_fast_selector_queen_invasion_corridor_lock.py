import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


LIVE_MOVES = (
    "b1c3 a7a6 c3e4 d7d5 e4d6 c7d6 g1f3 e7e5 "
    "f3e5 d6e5 d2d4 e5d4 d1d4 b8c6 d4d5 d8d5 "
    "c1f4 d5d4 f4e5 c6e5 e2e4 d4b2 f1a6 b2a1 "
    "e1d2 f8b4 c2c3 a1c3 d2e2 c3c2 e2e3 c2d2"
).split()


def test_phase22e71_latest_live_game_ends_in_qd2_mate():
    board = chess.Board()

    for move_uci in LIVE_MOVES:
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves
        board.push(move)

    assert board.is_checkmate()
    assert board.fen() == "r1b1k1nr/1p3ppp/B7/4n3/1b2P3/4K3/P2q1PPP/7R w kq - 4 17"


def test_phase22e72_fast_selector_rejects_f1a6_queen_invasion_corridor(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    fen = "r1b1kbnr/1p3ppp/p7/4n3/4P3/8/PqP2PPP/R3KB1R w KQkq - 0 12"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert "f1a6" in selected["legal_moves"]
    assert selected["selected_move"] != "f1a6"
    assert "f1a6" in selected["horizon_rejects"]
    assert selected["selected_source"] == "phase22e69_fast_live_clock_safe_selector"


def test_phase22e71_final_white_choice_was_already_all_immediate_mate_bad():
    board = chess.Board("r1b1k1nr/1p3ppp/B7/4n3/1b2P3/8/P1q1KPPP/7R w kq - 2 16")

    legal = [m.uci() for m in board.legal_moves]
    assert legal == ["e2e3", "e2f1"]

    immediate_bad = {}
    for move_uci in legal:
        probe = board.copy(stack=False)
        probe.push(chess.Move.from_uci(move_uci))

        mates = []
        for reply in probe.legal_moves:
            rp = probe.copy(stack=False)
            rp.push(reply)
            if rp.is_checkmate():
                mates.append(reply.uci())

        immediate_bad[move_uci] = mates

    assert immediate_bad == {
        "e2e3": ["c2d2"],
        "e2f1": ["c2d1"],
    }
