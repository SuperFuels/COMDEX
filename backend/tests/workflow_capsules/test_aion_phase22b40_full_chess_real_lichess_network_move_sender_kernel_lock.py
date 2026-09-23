from backend.modules.aion_games.full_chess_real_lichess_network_move_sender_kernel import (
    AionFullChessRealLichessNetworkMoveSenderKernel,
    run_full_chess_real_lichess_network_move_sender_kernel,
)


def test_phase22b40_defaults_to_safe_dry_run_block(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_123456")

    result = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=tmp_path / "memory.json",
        game_id="abc123",
    )

    assert result.kernel_version == "phase22b40_full_chess_real_lichess_network_move_sender_kernel_v1"
    assert result.sender_mode == "guarded_real_lichess_network_move_sender"
    assert result.send_allowed is False
    assert result.block_reason == "dry_run_guard_active"
    assert result.send_attempted is False
    assert result.network_call_performed is False
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b40_blocks_missing_token(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=tmp_path / "memory.json",
        dry_run=False,
        allow_network=True,
        live_enable=True,
        game_id="abc123",
    )

    assert result.send_allowed is False
    assert result.block_reason == "token_missing"
    assert result.token_guard_active is True
    assert result.network_call_performed is False


def test_phase22b40_blocks_missing_game_id(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_123456")

    result = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=tmp_path / "memory.json",
        dry_run=False,
        allow_network=True,
        live_enable=True,
        game_id="",
    )

    assert result.send_allowed is False
    assert result.block_reason == "game_id_missing"
    assert result.game_id_guard_active is True
    assert result.network_call_performed is False


def test_phase22b40_mocks_successful_network_send(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_123456")

    def fake_post(*, url, token, timeout_seconds):
        assert url == "https://lichess.org/api/bot/game/abc123/move/c2c4"
        assert token == "test_token_123456"
        return 200, '{"ok":true}'

    kernel = AionFullChessRealLichessNetworkMoveSenderKernel(memory_path=tmp_path / "memory.json")
    monkeypatch.setattr(kernel, "_perform_post", fake_post)

    result = kernel.run(
        dry_run=False,
        allow_network=True,
        live_enable=True,
        game_id="abc123",
        move="c2c4",
    )

    assert result.send_allowed is True
    assert result.block_reason == "none"
    assert result.send_attempted is True
    assert result.network_call_performed is True
    assert result.send_success is True
    assert result.http_status == 200


def test_phase22b40_redacts_token(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "abcd1234secret5678")

    result = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=tmp_path / "memory.json",
        game_id="abc123",
    )

    assert result.request["token_redacted"] == "abcd...5678"
    assert "abcd1234secret5678" not in str(result.to_dict())
    assert result.evidence["token_redacted"] is True


def test_phase22b40_emits_trace_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_123456")

    result = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=tmp_path / "memory.json",
        game_id="abc123",
    )

    assert len(result.real_send_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b40_persists_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_123456")
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=memory_path,
        game_id="abc123",
    )
    second = run_full_chess_real_lichess_network_move_sender_kernel(
        memory_path=memory_path,
        game_id="abc123",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_real_send_policy["kernel_run_count"] >= 2
    assert memory_path.exists()
