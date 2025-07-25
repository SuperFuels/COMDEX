import pytest
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_manager import PORTALS
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.hexcore.memory_engine import MemoryEngine

# Optional: helper to create a dummy payload
def make_payload(glyphs: list[str], avatar_id: str = "test-avatar"):
    return {
        "glyphs": glyphs,
        "event": "dispatch_test",
        "avatar_id": avatar_id
    }

def test_dispatch_with_mutation():
    """Test teleport dispatch that triggers symbolic mutation ripple (⬁)."""
    # Setup
    src = "container-mutation-src"
    dst = "container-mutation-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["⬁"])  # Mutation glyph
    packet = TeleportPacket(portal_id=portal_id, container_id=src, payload=payload)

    # Run
    result = PORTALS.teleport(packet)
    assert result is True

    # Validate mutation memory impact
    memory = MemoryEngine().get_memory(dst)
    assert any("mutation" in m.lower() or "⬁" in m for m in memory), "Mutation not reflected in memory"

def test_dispatch_with_entanglement():
    """Test teleport dispatch that triggers entanglement expansion (↔)."""
    src = "container-entangle-src"
    dst = "container-entangle-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["↔"])  # Entanglement glyph
    packet = TeleportPacket(portal_id=portal_id, container_id=src, payload=payload)

    result = PORTALS.teleport(packet)
    assert result is True

    # Confirm symbolic entanglement tracked (state or link)
    state = ContainerRuntime().get_container_state(dst)
    assert "↔" in state.get("glyph_trace", ""), "Entanglement glyph not traced"
    
    # Optionally validate CodexMetrics or shared logic linkage
    metrics = CodexMetrics().get_latest()
    assert "↔" in str(metrics), "No entanglement logged in metrics"

def test_dispatch_memory_reflection():
    """Test post-teleport dispatch updates shared memory reference."""
    src = "container-memory-src"
    dst = "container-memory-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["✨", "↔"])
    packet = TeleportPacket(portal_id=portal_id, container_id=src, payload=payload)

    result = PORTALS.teleport(packet)
    assert result is True

    # Both containers should now reflect some shared symbol
    src_mem = MemoryEngine().get_memory(src)
    dst_mem = MemoryEngine().get_memory(dst)

    shared = set(src_mem) & set(dst_mem)
    assert shared, "No shared memory detected after symbolic teleport entanglement"