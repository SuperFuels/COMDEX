import chess


FINAL_MOVES = [
    "g1f3", "g8f6",
    "e2e4", "f6e4",
    "c2c4", "b8c6",
    "d2d4", "e7e5",
    "f3d2", "e4d2",
    "b1d2", "c6d4",
    "b2b3", "d7d5",
    "c4d5", "c8f5",
    "d2e4", "f5e4",
    "f1c4", "e4g2",
    "c4b5", "c7c6",
    "b5c6", "b7c6",
    "d1h5", "d8d5",
    "h5d1", "f8b4",
    "c1d2", "d5e4",
    "d1e2", "e4e2",
]


MATE_CORRIDOR_RECORDS = [
    {
        "aion_move_index": 13,
        "fen_before": "r2qkb1r/p4ppp/2p5/3Pp3/3n4/1P6/P4PbP/R1BQK2R w KQkq - 0 13",
        "selected_move": "d1h5",
        "selected_source": "phase22e61_parallel_opponent_beam_router_sqi_collapse",
        "active_intent": "center_control",
    },
    {
        "aion_move_index": 14,
        "fen_before": "r3kb1r/p4ppp/2p5/3qp2Q/3n4/1P6/P4PbP/R1B1K2R w KQkq - 0 14",
        "selected_move": "h5d1",
        "selected_source": "monte_carlo_policy_value_seed",
        "active_intent": "center_control",
    },
    {
        "aion_move_index": 15,
        "fen_before": "r3k2r/p4ppp/2p5/3qp3/1b1n4/1P6/P4PbP/R1BQK2R w KQkq - 2 15",
        "selected_move": "c1d2",
        "selected_source": "monte_carlo_policy_value_seed",
        "active_intent": "king_safety",
    },
    {
        "aion_move_index": 16,
        "fen_before": "r3k2r/p4ppp/2p5/4p3/1b1nq3/1P6/P2B1PbP/R2QK2R w KQkq - 4 16",
        "selected_move": "d1e2",
        "selected_source": "monte_carlo_policy_value_seed",
        "active_intent": "king_safety",
    },
]


def test_phase22e64_live_level8_game_replays_to_black_mate():
    board = chess.Board()

    for uci in FINAL_MOVES:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)

    assert len(FINAL_MOVES) == 32
    assert board.is_checkmate()
    assert board.outcome().winner is False


def test_phase22e64_live_level8_mate_corridor_is_locked():
    record_by_index = {r["aion_move_index"]: r for r in MATE_CORRIDOR_RECORDS}

    assert record_by_index[13]["selected_move"] == "d1h5"
    assert record_by_index[13]["selected_source"] == "phase22e61_parallel_opponent_beam_router_sqi_collapse"

    assert record_by_index[14]["selected_move"] == "h5d1"
    assert record_by_index[14]["selected_source"] == "monte_carlo_policy_value_seed"

    assert record_by_index[15]["selected_move"] == "c1d2"
    assert record_by_index[15]["active_intent"] == "king_safety"

    assert record_by_index[16]["selected_move"] == "d1e2"
    assert record_by_index[16]["active_intent"] == "king_safety"


def test_phase22e64_live_level8_qd5_qe4_qe2_corridor_reproduces_mate():
    board = chess.Board(
        "r3kb1r/p4ppp/2p5/3qp2Q/3n4/1P6/P4PbP/R1B1K2R w KQkq - 0 14"
    )

    corridor = [
        "h5d1",  # passive queen retreat
        "f8b4",  # black pins / develops attack
        "c1d2",  # late king-safety response
        "d5e4",  # queen central penetration
        "d1e2",  # attempted block / response
        "e4e2",  # mate
    ]

    for uci in corridor:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)

    assert board.is_checkmate()
    assert board.outcome().winner is False
