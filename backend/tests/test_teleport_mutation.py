import pytest
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_manager import PORTALS
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.symbolic_entangler import entangle_glyphs, get_entangled_for

# === Helpers ===

def make_payload(glyphs: list[str], avatar_id: str = "test-avatar"):
    return {
        "glyphs": glyphs,
        "event": "dispatch_test",
        "avatar_id": avatar_id
    }

def register_entanglement(g1: str, g2: str):
    entangle_glyphs(g1, g2)
    entangle_glyphs(g2, g1)

# === A. Runtime Mutation + Entanglement Tests ===

def test_dispatch_with_mutation():
    """Test teleport dispatch that triggers symbolic mutation ripple (⬁)."""
    src = "container-mutation-src"
    dst = "container-mutation-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["⬁"])  # Mutation glyph
    packet = TeleportPacket(
        portal_id=portal_id,
        container_id=src,
        source=src,
        destination=dst,
        payload=payload
    )

    result = PORTALS.teleport(packet)
    assert result is True

    memory = MemoryEngine().get_memory(dst)
    assert any("mutation" in m.lower() or "⬁" in m for m in memory), "Mutation not reflected in memory"

def test_dispatch_with_entanglement():
    """Test teleport dispatch that triggers entanglement expansion (↔)."""
    src = "container-entangle-src"
    dst = "container-entangle-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["↔"])  # Entanglement glyph
    packet = TeleportPacket(
        portal_id=portal_id,
        container_id=src,
        source=src,
        destination=dst,
        payload=payload
    )

    result = PORTALS.teleport(packet)
    assert result is True

    state = ContainerRuntime().get_container_state(dst)
    assert "↔" in state.get("glyph_trace", ""), "Entanglement glyph not traced"

    metrics = CodexMetrics().get_latest()
    assert "↔" in str(metrics), "No entanglement logged in metrics"

def test_dispatch_memory_reflection():
    """Test post-teleport dispatch updates shared memory reference."""
    src = "container-memory-src"
    dst = "container-memory-dst"
    portal_id = PORTALS.register_portal(src, dst)
    payload = make_payload(["✨", "↔"])
    packet = TeleportPacket(
        portal_id=portal_id,
        container_id=src,
        source=src,
        destination=dst,
        payload=payload
    )

    result = PORTALS.teleport(packet)
    assert result is True

    src_mem = MemoryEngine().get_memory(src)
    dst_mem = MemoryEngine().get_memory(dst)

    shared = set(src_mem) & set(dst_mem)
    assert shared, "No shared memory detected after symbolic teleport entanglement"

# === A9b: Entanglement Propagation via CodexExecutor ===

@pytest.mark.asyncio
async def test_entangled_glyph_propagation():
    """Validate ↔ entanglement triggers linked glyph execution."""
    state_manager = StateManager()
    executor = CodexExecutor()

    glyph_main = "⟦ Logic | X1 : Ping → Reflect ↔ Mirror ⟧"
    glyph_entangled = "⟦ Logic | X2 : Pong → Boot ↔ Sync ⟧"

    register_entanglement(glyph_main, glyph_entangled)

    context = {
        "container": "test_container",
        "coord": "1,2,3",
        "source": "unit_test"
    }

    result = executor.execute(glyph_main, context)

    assert result["status"] == "executed"
    assert "↔" in result["operator_chain"]
    assert len(result["execution_trace"]) >= 1

    entangled_logged = any(entry[0] == glyph_entangled for entry in executor.get_log())
    assert entangled_logged, "Entangled glyph was not triggered by ↔"

    print("[✅] Entangled glyph propagation test passed.")