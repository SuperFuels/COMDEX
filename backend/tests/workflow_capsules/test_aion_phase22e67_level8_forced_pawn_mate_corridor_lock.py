import chess


def _mate_replies_after_move(fen: str, move_uci: str) -> list[str]:
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    assert move in board.legal_moves

    board.push(move)

    mates = []
    for reply in board.legal_moves:
        probe = board.copy(stack=False)
        probe.push(reply)
        if probe.is_checkmate():
            mates.append(reply.uci())
    return mates


def _safe_evasions(fen: str) -> list[str]:
    board = chess.Board(fen)
    safe = []

    for move in board.legal_moves:
        probe = board.copy(stack=False)
        probe.push(move)

        allows_mate = False
        for reply in probe.legal_moves:
            reply_probe = probe.copy(stack=False)
            reply_probe.push(reply)
            if reply_probe.is_checkmate():
                allows_mate = True
                break

        if not allows_mate:
            safe.append(move.uci())

    return safe


def test_phase22e67_level8_final_position_has_no_safe_evasion():
    fen = "rnb3k1/1pp1pp2/6pp/p3b3/1PP4P/1K6/r2n2P1/8 w - - 2 24"

    assert _mate_replies_after_move(fen, "b3a2") == ["a5b4"]
    assert _safe_evasions(fen) == []


def test_phase22e67_final_live_line_reaches_forced_pawn_mate():
    moves = "g1f3 g8f6 e2e4 g7g6 f3g5 f8g7 d1e2 e8g8 d2d4 d7d5 c2c4 h7h6 b2b3 d5e4 g5e4 f6e4 c1a3 d8d4 a3b4 d4a1 b4d2 a1b1 e2d1 b1d1 e1d1 e4f2 d1c1 f2h1 d2c3 g7c3 f1d3 h1f2 c1c2 c3e5 d3e4 f2e4 h2h4 f8d8 b3b4 d8d2 c2b3 a7a5 b3a4 d2a2 a4b3 e4d2".split()

    board = chess.Board()
    for uci in moves:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)

    assert board.fen() == "rnb3k1/1pp1pp2/6pp/p3b3/1PP4P/1K6/r2n2P1/8 w - - 2 24"
    assert _safe_evasions(board.fen()) == []
