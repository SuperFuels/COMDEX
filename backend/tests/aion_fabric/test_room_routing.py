from __future__ import annotations

import pytest

from backend.modules.aion_fabric.room_routing import TelevisionRoomRouter


def test_room_registry_resolves_this_named_and_default_tv(tmp_path):
    router = TelevisionRoomRouter(tmp_path)
    living = router.register(node_id="node_tv_living", device_name="LG", room_name="Living Room")
    router.register(node_id="node_tv_bedroom", device_name="Samsung", room_name="Bedroom")

    assert living["default"] is True
    assert router.resolve("this TV", current_node_id="node_tv_bedroom")["room_name"] == "Bedroom"
    assert router.resolve("living room")["node_id"] == "node_tv_living"
    assert router.resolve("")["node_id"] == "node_tv_living"


def test_room_registry_rejects_ambiguous_room_names(tmp_path):
    router = TelevisionRoomRouter(tmp_path)
    router.register(node_id="node_one", device_name="One", room_name="Kitchen")
    with pytest.raises(ValueError, match="already"):
        router.register(node_id="node_two", device_name="Two", room_name="Kitchen")


def test_handoff_requires_verified_playback_and_private_confirmation(tmp_path):
    router = TelevisionRoomRouter(tmp_path)
    router.register(node_id="node_source", device_name="LG", room_name="Living Room")
    router.register(node_id="node_destination", device_name="Samsung", room_name="Bedroom")
    with pytest.raises(PermissionError, match="verified"):
        router.prepare_handoff(
            source_node_id="node_source", destination_room="Bedroom", persona_id="persona_one",
            playback={"title": "Film", "playback_verified": False},
        )

    handoff = router.prepare_handoff(
        source_node_id="node_source", destination_room="Bedroom", persona_id="persona_one",
        playback={"title": "Film", "provider": "netflix", "playback_verified": True, "position_seconds": 630},
    )
    assert handoff["status"] == "awaiting_private_confirmation"
    assert handoff["credentials_projected"] is False
    confirmed = router.confirm_handoff(
        handoff["handoff_id"], persona_id="persona_one", confirmation_hash=handoff["confirmation_hash"]
    )
    assert confirmed["status"] == "approved_pending_destination_adapter"
    assert confirmed["playback_claimed_on_destination"] is False


def test_handoff_cannot_cross_personas_or_replay(tmp_path):
    router = TelevisionRoomRouter(tmp_path)
    router.register(node_id="node_source", device_name="LG", room_name="Living Room")
    router.register(node_id="node_destination", device_name="LG", room_name="Office")
    handoff = router.prepare_handoff(
        source_node_id="node_source", destination_room="Office", persona_id="persona_one",
        playback={"title": "Series", "playback_verified": True},
    )
    with pytest.raises(LookupError):
        router.confirm_handoff(handoff["handoff_id"], persona_id="persona_two", confirmation_hash=handoff["confirmation_hash"])
    router.confirm_handoff(handoff["handoff_id"], persona_id="persona_one", confirmation_hash=handoff["confirmation_hash"])
    with pytest.raises(PermissionError):
        router.confirm_handoff(handoff["handoff_id"], persona_id="persona_one", confirmation_hash=handoff["confirmation_hash"])
