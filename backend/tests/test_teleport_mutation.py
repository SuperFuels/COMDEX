import pytest
from datetime import datetime

from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_manager import PortalManager
from backend.modules.glyphos.symbolic_entangler import get_entangled_targets, entangle_containers
from backend.modules.codex.codex_metrics import get_latest_memory


def ensure_container_loaded(container_id: str):
    """Create container if it doesn't exist."""
    sm = StateManager()
    if not sm.container_exists(container_id):
        sm.save_container({
            "id": container_id,
            "glyphs": [],
            "memory": [],
            "links": [],
            "metadata": {
                "created_by": "test",
                "created_on": datetime.utcnow().isoformat() + "Z",
            }
        })


def test_dispatch_with_mutation():
    src = "container-mutation-src"
    dst = "container-mutation-dst"
    ensure_container_loaded(src)
    ensure_container_loaded(dst)

    packet = TeleportPacket(
        src=src,
        dst=dst,
        glyph="⬁",
        metadata={"test": True}
    )

    portal = PortalManager()
    result = portal.dispatch(packet)

    assert result["status"] == "ok"
    assert any("mutation" in str(step) for step in result.get("trace", []))


def test_dispatch_with_entanglement():
    src = "container-entangle-src"
    dst = "container-entangle-dst"
    ensure_container_loaded(src)
    ensure_container_loaded(dst)

    packet = TeleportPacket(
        src=src,
        dst=dst,
        glyph="↔",
        metadata={"test": True}
    )

    portal = PortalManager()
    result = portal.dispatch(packet)

    assert result["status"] == "ok"
    assert any("entangle" in str(step) for step in result.get("trace", []))


def test_dispatch_memory_reflection():
    src = "container-memory-src"
    dst = "container-memory-dst"
    ensure_container_loaded(src)
    ensure_container_loaded(dst)

    packet = TeleportPacket(
        src=src,
        dst=dst,
        glyph="🧠",
        metadata={"test": True, "note": "memory test"}
    )

    portal = PortalManager()
    result = portal.dispatch(packet)

    assert result["status"] == "ok"
    memory = get_latest_memory(dst)
    assert memory is not None
    assert memory.get("metadata", {}).get("note") == "memory test"


@pytest.mark.asyncio
async def test_entangled_glyph_propagation():
    container = "test_container"
    entangled = "linked_container"

    ensure_container_loaded(container)
    ensure_container_loaded(entangled)

    # ✅ Use symbolic entangler to formally register entanglement
    entangle_containers(container, entangled)

    executor = CodexExecutor()
    glyph = "⚛"

    await executor.execute_glyph(container, glyph)

    targets = get_entangled_targets(container)
    assert entangled in targets

    linked_memory = get_latest_memory(entangled)
    assert linked_memory is not None
    assert linked_memory.get("glyph") == glyph