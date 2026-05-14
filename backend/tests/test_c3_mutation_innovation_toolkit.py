import pytest
from backend.core.plugins.mutation_innovation_toolkit import MutationInnovationToolkit

def test_mutation_innovation_toolkit_methods():
    plugin = MutationInnovationToolkit()

    # Ensure required methods exist
    assert hasattr(plugin, "register_plugin")
    assert hasattr(plugin, "trigger")
    assert hasattr(plugin, "mutate")
    assert hasattr(plugin, "synthesize")
    assert hasattr(plugin, "broadcast_qfc_update")

    # Register without errors
    plugin.register_plugin()

    # Trigger should run with dummy input
    try:
        plugin.trigger({
            "event_type": "test_mutation_trigger",
            "glyph": {"id": "g3"},
            "result": {"status": "ok"},
            "context": {"container_id": "mutation_container"}
        })
    except Exception as e:
        pytest.fail(f"Trigger method failed: {e}")

    # Mutate a logic string and check output
    mutated = plugin.mutate("->(x, y)")
    assert isinstance(mutated, str)

    # Test synthesize logic string
    synthesized = plugin.synthesize("goal=evolve")
    assert isinstance(synthesized, str)

    # Test QFC broadcast call
    try:
        plugin.broadcast_qfc_update()
    except Exception as e:
        pytest.fail(f"broadcast_qfc_update failed: {e}")