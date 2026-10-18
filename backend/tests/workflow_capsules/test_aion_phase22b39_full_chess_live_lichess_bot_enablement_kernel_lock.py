from backend.modules.aion_games import run_full_chess_live_lichess_bot_enablement_kernel


def test_phase22b39_defaults_to_blocked_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_lichess_bot_enablement_kernel(
        memory_path=tmp_path / "live_enablement_memory.json"
    )

    assert result.kernel_version == "phase22b39_full_chess_live_lichess_bot_enablement_kernel_v1"
    assert result.enablement_mode == "guarded_live_lichess_bot_enablement"
    assert result.human_approval_required is False
    assert result.live_call_allowed is False
    assert result.block_reason == "dry_run_guard_active"
    assert result.dry_run_guard_active is True
    assert result.network_call_performed is False
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b39_blocks_missing_token_when_dry_run_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_lichess_bot_enablement_kernel(
        memory_path=tmp_path / "live_enablement_memory.json",
        dry_run=False,
        allow_network=True,
        live_enable=True,
    )

    assert result.live_call_allowed is False
    assert result.block_reason == "token_missing"
    assert result.token_guard_active is True
    assert result.network_call_performed is False


def test_phase22b39_allows_only_when_all_live_guards_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test_token_1234567890")

    result = run_full_chess_live_lichess_bot_enablement_kernel(
        memory_path=tmp_path / "live_enablement_memory.json",
        dry_run=False,
        allow_network=True,
        live_enable=True,
    )

    assert result.live_call_allowed is True
    assert result.block_reason == "none"
    assert result.dry_run_guard_active is False
    assert result.token_guard_active is False
    assert result.network_guard_active is False
    assert result.live_enable_guard_active is False
    assert result.network_call_performed is False


def test_phase22b39_redacts_token_and_prepares_move_url(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "abcd1234secret5678")

    result = run_full_chess_live_lichess_bot_enablement_kernel(
        memory_path=tmp_path / "live_enablement_memory.json",
        dry_run=False,
        allow_network=True,
        live_enable=True,
    )

    assert result.config["token_present"] is True
    assert result.config["token_redacted"] == "abcd...5678"
    assert "abcd1234secret5678" not in str(result.to_dict())
    assert result.decision["prepared_url"].endswith("/move/c2c4")
    assert result.evidence["does_not_print_raw_token"] is True


def test_phase22b39_emits_trace_hash(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_lichess_bot_enablement_kernel(
        memory_path=tmp_path / "live_enablement_memory.json"
    )

    assert len(result.live_enablement_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b39_persists_live_enablement_memory(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)
    memory_path = tmp_path / "live_enablement_memory.json"

    first = run_full_chess_live_lichess_bot_enablement_kernel(memory_path=memory_path)
    second = run_full_chess_live_lichess_bot_enablement_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_live_enablement_policy["kernel_run_count"] >= 2
    assert second.final_live_enablement_policy["live_enablement_session_count"] >= 2
    assert second.final_live_enablement_policy["network_call_total"] == 0
    assert memory_path.exists()
