import pytest
from backend.core.plugins.tranquility_auto_iteration import TranquilityAutoIteration

def test_tranquility_runner_methods():
    plugin = TranquilityAutoIteration()

    # Check required methods
    assert hasattr(plugin, "register_plugin")
    assert hasattr(plugin, "trigger")
    assert hasattr(plugin, "mutate")
    assert hasattr(plugin, "synthesize")
    assert hasattr(plugin, "broadcast_qfc_update")

    # Safe registration
    plugin.register_plugin()

    # Trigger method test
    try:
        plugin.trigger({
            "event_type": "tranquil_trigger",
            "glyph": {"id": "calm1"},
            "result": {"state": "tranquil"},
            "context": {"container_id": "zen_container"}
        })
    except Exception as e:
        pytest.fail(f"Trigger method failed: {e}")

    # Mutation check
    mutated = plugin.mutate("⊗(peace, chaos)")
    assert isinstance(mutated, str)

    # Synthesis check
    synthesized = plugin.synthesize("goal=stabilize")
    assert isinstance(synthesized, str)

    # QFC Broadcast check
    try:
        plugin.broadcast_qfc_update()
    except Exception as e:
        pytest.fail(f"broadcast_qfc_update failed: {e}")