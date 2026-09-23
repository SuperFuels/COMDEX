import chess


def _mate_replies_after(board: chess.Board, move_uci: str) -> list[str]:
    move = chess.Move.from_uci(move_uci)
    assert move in board.legal_moves
    probe = board.copy(stack=False)
    probe.push(move)

    mates = []
    for reply in probe.legal_moves:
        rp = probe.copy(stack=False)
        rp.push(reply)
        if rp.is_checkmate():
            mates.append(reply.uci())

    return mates


def _safe_evasions(board: chess.Board) -> list[str]:
    return [
        move.uci()
        for move in board.legal_moves
        if not _mate_replies_after(board, move.uci())
    ]


def _shallow_horizon_safe_moves(board: chess.Board) -> list[str]:
    safe = []

    for move in board.legal_moves:
        move_uci = move.uci()

        if _mate_replies_after(board, move_uci):
            continue

        probe = board.copy(stack=False)
        probe.push(move)

        opponent_can_leave_no_immediate_safe_evasion = False
        for reply in probe.legal_moves:
            rp = probe.copy(stack=False)
            rp.push(reply)
            if not _safe_evasions(rp):
                opponent_can_leave_no_immediate_safe_evasion = True
                break

        if not opponent_can_leave_no_immediate_safe_evasion:
            safe.append(move_uci)

    return safe


def _forcing_replies_to_no_horizon_after(board: chess.Board, move_uci: str) -> list[str]:
    move = chess.Move.from_uci(move_uci)
    assert move in board.legal_moves

    probe = board.copy(stack=False)
    probe.push(move)

    forcing = []
    for reply in probe.legal_moves:
        rp = probe.copy(stack=False)
        rp.push(reply)
        if not _shallow_horizon_safe_moves(rp):
            forcing.append(reply.uci())

    return forcing


def test_phase22e68_ply42_b3a4_enters_forced_no_horizon_corridor():
    fen = "rnb3k1/1pp1pp2/6pp/p3b3/1PP1n2P/1K6/P2r2P1/8 w - - 0 22"

    board = chess.Board(fen)

    assert "b3a4" in [m.uci() for m in board.legal_moves]
    assert _mate_replies_after(board, "b3a4") == []

    forcing_replies = _forcing_replies_to_no_horizon_after(board, "b3a4")

    assert forcing_replies
    assert "d2a2" in forcing_replies or "a5b4" in forcing_replies or "b7b5" in forcing_replies

    assert "b4a5" in _shallow_horizon_safe_moves(board)
    assert "c4c5" in _shallow_horizon_safe_moves(board)


def test_phase22e68_ply44_after_b3a4_corridor_has_no_horizon_safe_moves():
    fen = "rnb3k1/1pp1pp2/6pp/p3b3/KPP1n2P/8/r5P1/8 w - - 0 23"

    board = chess.Board(fen)

    assert [m.uci() for m in board.legal_moves] == ["a4b5", "a4b3"]
    assert _shallow_horizon_safe_moves(board) == []
    assert _mate_replies_after(board, "a4b5")
    assert _forcing_replies_to_no_horizon_after(board, "a4b3")
