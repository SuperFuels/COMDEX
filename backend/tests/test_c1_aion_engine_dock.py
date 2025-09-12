import pytest
from backend.core.plugins.aion_engine_dock import AIONEngineDock

def test_aion_engine_dock_methods():
    plugin = AIONEngineDock()

    # Confirm all expected methods exist
    assert hasattr(plugin, "register_plugin")
    assert hasattr(plugin, "trigger")
    assert hasattr(plugin, "mutate")
    assert hasattr(plugin, "synthesize")
    assert hasattr(plugin, "broadcast_qfc_update")

    # Check register runs without error
    plugin.register_plugin()

    # Test trigger with dummy data
    try:
        plugin.trigger({
            "event_type": "test_trigger",
            "glyph": {"id": "g1"},
            "result": {"status": "ok"},
            "context": {"container_id": "test_container"}
        })
    except Exception as e:
        pytest.fail(f"Trigger method failed: {e}")

    # Test mutate returns string
    mutated = plugin.mutate("⊕(a, b)")
    assert isinstance(mutated, str)

    # Test synthesize returns string
    synthesized = plugin.synthesize("goal=optimize")
    assert isinstance(synthesized, str)

    # Test broadcast_qfc_update executes
    try:
        plugin.broadcast_qfc_update()
    except Exception as e:
        pytest.fail(f"broadcast_qfc_update failed: {e}")