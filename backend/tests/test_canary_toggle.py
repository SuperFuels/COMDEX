import pytest
import types

# ✅ Import the target module directly
import backend.modules.holograms.ghx_replay_broadcast as ghx_broadcast


@pytest.mark.asyncio
async def test_canary_toggle_broadcast(monkeypatch):
    """
    Test that when GW_ENABLED is False, the fallback broadcast ('sqi_event') is used
    in stream_symbolic_tree_replay().
    """

    # ✅ Minimal mock symbolic tree
    mock_tree = types.SimpleNamespace()
    mock_tree.trace = types.SimpleNamespace()
    mock_tree.trace.replayPaths = [["a", "b", "c"]]
    mock_tree.trace.entropyOverlay = {}
    mock_tree.node_index = {}

    # ✅ Track emitted events
    called_events = []

    # ✅ Fake broadcast function
    async def mock_broadcast(event, payload):
        called_events.append(event)

    # ✅ Patch the locally imported broadcast_event in ghx_replay_broadcast
    monkeypatch.setattr(ghx_broadcast, "broadcast_event", mock_broadcast)

    # ✅ Patch the locally imported GW_ENABLED flag inside ghx_replay_broadcast
    monkeypatch.setattr(ghx_broadcast, "GW_ENABLED", False)

    # ✅ Run the function (directly from the module)
    await ghx_broadcast.stream_symbolic_tree_replay(mock_tree, container_id="fallback_test")

    # ✅ Assert that fallback broadcast occurred
    assert "sqi_event" in called_events, \
        f"Expected 'sqi_event' to be broadcast when GW_ENABLED is False. Got: {called_events}"


@pytest.mark.asyncio
async def test_ghx_broadcast_triggered(monkeypatch):
    """
    Test that when GW_ENABLED is True, the GHX broadcast ('ghx_replay') is used
    in stream_symbolic_tree_replay().
    """

    # ✅ Minimal mock symbolic tree
    mock_tree = types.SimpleNamespace()
    mock_tree.trace = types.SimpleNamespace()
    mock_tree.trace.replayPaths = [["x", "y", "z"]]
    mock_tree.trace.entropyOverlay = {}
    mock_tree.node_index = {}

    # ✅ Track emitted events
    called_events = []

    # ✅ Fake broadcast function
    async def mock_broadcast(event, payload):
        called_events.append(event)

    # ✅ Patch the locally imported broadcast_event in ghx_replay_broadcast
    monkeypatch.setattr(ghx_broadcast, "broadcast_event", mock_broadcast)

    # ✅ Patch GW_ENABLED to True
    monkeypatch.setattr(ghx_broadcast, "GW_ENABLED", True)

    # ✅ Run the function
    await ghx_broadcast.stream_symbolic_tree_replay(mock_tree, container_id="ghx_test")

    # ✅ Assert that GHX broadcast occurred
    assert "ghx_replay" in called_events, \
        f"Expected 'ghx_replay' to be broadcast when GW_ENABLED is True. Got: {called_events}"