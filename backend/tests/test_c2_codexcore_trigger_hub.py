import pytest
from backend.core.plugins.codexcore_trigger_hub import CodexCoreTriggerHub

def test_codexcore_trigger_hub_methods():
    plugin = CodexCoreTriggerHub()

    # Confirm expected methods exist
    assert hasattr(plugin, "register_plugin")
    assert hasattr(plugin, "trigger")
    assert hasattr(plugin, "mutate")
    assert hasattr(plugin, "synthesize")
    assert hasattr(plugin, "broadcast_qfc_update")

    # Check registration runs without error
    plugin.register_plugin()

    # Test trigger with dummy context
    try:
        plugin.trigger({
            "event_type": "test_event",
            "glyph": {"id": "g2"},
            "result": {"value": 42},
            "context": {"container_id": "test_container_2"}
        })
    except Exception as e:
        pytest.fail(f"Trigger method failed: {e}")

    # Test mutate returns a string (even if passthrough)
    mutated = plugin.mutate("⊕(x, y)")
    assert isinstance(mutated, str)

    # Test synthesize returns a valid string
    synthesized = plugin.synthesize("goal=test_trigger_hub")
    assert isinstance(synthesized, str)

    # Test broadcast method executes without error
    try:
        plugin.broadcast_qfc_update()
    except Exception as e:
        pytest.fail(f"broadcast_qfc_update failed: {e}")