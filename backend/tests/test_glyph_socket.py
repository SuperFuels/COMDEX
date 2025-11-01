# backend/tests/test_glyph_socket.py

import pytest
from backend.modules.glyphnet.glyph_socket import GlyphSocket
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_manager import PortalManager
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.consciousness.state_manager import state_manager

@pytest.fixture(scope="module")
def setup_environment():
    # ✅ Use shared state manager singleton
    runtime = ContainerRuntime(state_manager=state_manager)

    # ✅ Save containers via runtime's public API
    runtime.save_container(container_id="test_container_source", container_data={
        "id": "test_container_source",
        "glyphs": [],
        "metadata": {},
        "tick": 0
    })

    runtime.save_container(container_id="test_container_dest", container_data={
        "id": "test_container_dest",
        "glyphs": [],
        "metadata": {},
        "tick": 0
    })

    # ✅ Register a portal
    portal_id = PortalManager().register_portal("test_container_source", "test_container_dest")
    return portal_id


@pytest.fixture(scope="module")
def glyph_socket():
    return GlyphSocket()


def test_dispatch_basic_glyph_injection(glyph_socket, setup_environment):
    packet = TeleportPacket(
        source="test_container_source",
        destination="test_container_dest",
        container_id="test_container_dest",
        portal_id=setup_environment,
        payload={
            "glyphs": ["✦", "->", "THINK"],
            "coords": (1, 1, 1, 0),
        }
    ).to_dict()

    result = glyph_socket.dispatch(packet)
    assert result["status"].startswith("✅")
    assert result["container_id"] == "test_container_dest"
    assert result["injected"] is True


def test_dispatch_symbolic_teleport_payload(glyph_socket, setup_environment):
    packet = TeleportPacket(
        source="test_container_source",
        destination="test_container_dest",
        container_id="test_container_dest",
        portal_id=setup_environment,
        payload={
            "glyphs": ["⊕", "↔", "⬁"],
            "event": "teleport_glyph_trigger",
            "avatar_id": "observer_x9",
            "coords": (0, 0, 0, 0),
        }
    ).to_dict()

    result = glyph_socket.dispatch(packet)
    assert result["status"].startswith("✅")
    assert result.get("injected", False) is True


def test_dispatch_event_trigger(glyph_socket, setup_environment):
    packet = TeleportPacket(
        source="test_container_source",
        destination="test_container_dest",
        container_id="test_container_dest",
        portal_id=setup_environment,
        payload={
            "event": "ignite_core",
            "coords": (0, 0, 0, 0),
        }
    ).to_dict()

    result = glyph_socket.dispatch(packet)
    assert result["status"].startswith("✅")
    assert "tick" in result


def test_dispatch_with_avatar(glyph_socket, setup_environment):
    packet = TeleportPacket(
        source="test_container_source",
        destination="test_container_dest",
        container_id="test_container_dest",
        portal_id=setup_environment,
        payload={
            "avatar_id": "avatar_test_123",
            "coords": (2, 2, 2, 0),
        }
    ).to_dict()

    result = glyph_socket.dispatch(packet)
    assert result["status"].startswith("✅")