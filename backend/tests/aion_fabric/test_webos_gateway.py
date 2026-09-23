from __future__ import annotations

import stat
import json

import pytest

from backend.modules.aion_fabric.webos import WebOsGateway, WebOsPairingReceipt
from backend.modules.aion_fabric.voice import friendly_voice_error, parse_voice_intent


class FakeHelloConnection:
    def __init__(self, response):
        self.response = response
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def send(self, value):
        self.sent.append(json.loads(value))

    def recv(self, timeout=None):
        return json.dumps(self.response)


def test_webos_pairing_key_is_local_private_state_and_never_in_receipt(tmp_path):
    gateway = WebOsGateway(tmp_path / "pairing")
    node_id = "node_discovered_test_webos"
    gateway._save_key(node_id, "192.168.1.40", "secret-client-key")
    path = gateway._state_path(node_id)
    assert gateway._load_key(node_id, "192.168.1.40") == "secret-client-key"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    receipt = WebOsPairingReceipt(
        receipt_id="pair_test",
        node_id=node_id,
        host="192.168.1.40",
        paired=True,
        reused_client_key=False,
        permissions_requested=["READ_SETTINGS"],
        proof_action="ssap://audio/getVolume",
        proof_values={"volume": 10},
        request_hash="a" * 64,
        response_hash="b" * 64,
    )
    assert "secret-client-key" not in str(receipt.to_dict())


def test_webos_pairing_follows_verified_device_to_new_private_host(tmp_path):
    gateway = WebOsGateway(tmp_path / "pairing")
    node_id = "node_discovered_test_webos"
    gateway._save_key(node_id, "192.168.1.40", "secret-client-key")
    gateway.migrate_paired_host(
        node_id=node_id,
        old_host="192.168.1.40",
        new_host="192.168.1.41",
    )
    assert gateway._load_key(node_id, "192.168.1.40") is None
    assert gateway._load_key(node_id, "192.168.1.41") == "secret-client-key"


def test_voice_translates_ssl_handshake_timeout_into_recovery_instruction():
    message = friendly_voice_error(
        TimeoutError("_ssl.c:1011: The handshake operation timed out"),
        action="web_research",
    )
    assert "completed the research" in message
    assert "show my results again" in message
    assert "_ssl.c" not in message


@pytest.mark.parametrize(
    "phrase",
    [
        "Pilot open calendar",
        "Pilot show my files",
        "Pilot connect the device",
        "Pilot switch Netflix profile",
        "Pilot open the Boardroom",
        "Pilot turn on the aircon",
        "Pilot take over TV",
    ],
)
def test_direct_device_commands_never_fall_through_to_planning(phrase):
    intent = parse_voice_intent(phrase)
    assert intent is not None
    assert intent.action != "agent_request"


def test_webos_gateway_rejects_public_hosts(tmp_path):
    gateway = WebOsGateway(tmp_path / "pairing")
    with pytest.raises(ValueError, match="local-network"):
        gateway.validate_host("8.8.8.8")


def test_games_prefers_native_geforce_now_over_lg_gaming_portal():
    assert WebOsGateway.preferred_games_application(
        {"com.twin.app.gamingportal", "com.geforcenow.play"}
    ) == ("com.geforcenow.play", "GeForce NOW")
    assert WebOsGateway.preferred_games_application(
        {"com.twin.app.gamingportal"}
    ) == ("com.twin.app.gamingportal", "LG Gaming Portal")
    assert WebOsGateway.preferred_games_application(set()) is None


def test_health_probe_requires_real_webos_protocol_not_just_open_port(monkeypatch):
    connection = FakeHelloConnection({"type": "hello", "payload": {"deviceUUID": "tv-1"}})
    monkeypatch.setattr(WebOsGateway, "_connect", staticmethod(lambda host, open_timeout=4: connection))
    result = WebOsGateway.probe_endpoint("192.168.1.40")
    assert result == {"connected": True, "host": "192.168.1.40", "protocol": "webos_ssap"}
    assert connection.sent[0]["type"] == "hello"


def test_health_probe_rejects_non_webos_response(monkeypatch):
    connection = FakeHelloConnection({"type": "unrelated_service"})
    monkeypatch.setattr(WebOsGateway, "_connect", staticmethod(lambda host, open_timeout=4: connection))
    with pytest.raises(RuntimeError, match="webOS control service"):
        WebOsGateway.probe_endpoint("192.168.1.40")


@pytest.mark.parametrize(
    ("phrase", "action", "arguments"),
    [
        ("Pilot, turn up the TV", "change_volume", {"delta": 2}),
        ("Hey Pilot set the TV volume to 20", "set_volume", {"volume": 20}),
        ("Pilot mute the television", "set_mute", {"muted": True}),
        ("Pilot switch the TV to HDMI 2", "switch_input", {"input_id": "HDMI_2"}),
        ("Pilot turn off the TV", "blocked_power", {}),
        ("Pile it, what is the TV volume?", "get_volume", {}),
        ("Pilot take over the TV", "show_canvas", {"view": "home"}),
        ("Pilot take over TV", "show_canvas", {"view": "home"}),
        ("Pilot takeover TV", "show_canvas", {"view": "home"}),
        ("Pilot open Pilot", "show_canvas", {"view": "home"}),
        ("Pilot show my Pilot home", "show_canvas", {"view": "home"}),
        ("Pilot open calendar", "show_canvas", {"view": "calendar"}),
        ("Pilot open my tasks", "show_canvas", {"view": "tasks"}),
        ("Pilot open my files", "show_canvas", {"view": "files"}),
        ("Pilot open IoT", "show_canvas", {"view": "iot"}),
        ("Pilot open connected devices", "show_canvas", {"view": "iot"}),
        ("Pilot open my workspace", "show_canvas", {"view": "work"}),
        ("Pilot show the device mesh", "show_canvas", {"view": "mesh"}),
        ("Pilot show the Boardroom", "show_canvas", {"view": "boardroom"}),
        ("Pilot give me a briefing", "show_canvas", {"view": "briefing"}),
        ("Pilot show the phone controller", "show_canvas", {"view": "companion"}),
        ("Pilot log me out of the TV", "identity_logout", {}),
        ("Pilot log me out", "identity_logout", {}),
        ("Pilot logout", "identity_logout", {}),
        ("Pilot sign out", "identity_logout", {}),
        ("Pilot lock the TV", "identity_logout", {}),
        ("Pilot open God View", "show_canvas", {"view": "god_view"}),
        ("Pilot fly to Lapland", "show_canvas", {"view": "god_view", "god_action": "fly", "place": "lapland"}),
        ("Pilot flight to Lapland", "show_canvas", {"view": "god_view", "god_action": "fly", "place": "lapland"}),
        ("file open. God. Wee", "show_canvas", {"view": "god_view"}),
        ("Pilot take me to the ISS", "show_canvas", {"view": "god_view", "god_action": "iss_live"}),
        ("Pilot track the ISS", "show_canvas", {"view": "god_view", "god_action": "iss_track"}),
        ("Pilot live view from space", "show_canvas", {"view": "god_view", "god_action": "iss_live"}),
        ("Pilot show Earth from space", "show_canvas", {"view": "god_view", "god_action": "nasa_earth"}),
        ("Pilot open games", "open_games", {}),
        ("Pilot open GeForce Now", "open_games", {}),
        ("Pilot find a game called Fortnite on GeForce Now", "open_games", {"query": "fortnite"}),
        ("Pilot continue my game", "game_continue", {}),
        ("Pilot tell me my tasks", "inbox_summary", {}),
        ("Pilot add buy milk to my task list", "inbox_add_self", {"title": "buy milk"}),
        ("Pilot add collect the dry cleaning tomorrow to my tasks", "inbox_add_self", {"title": "collect the dry cleaning tomorrow"}),
        ("Pilot remind Becca to collect the dry cleaning", "inbox_delegate_spoken", {"recipient_name": "becca", "title": "collect the dry cleaning"}),
        ("Pilot send Becca a task to pick up dry cleaning", "inbox_delegate_spoken", {"recipient_name": "becca", "title": "pick up dry cleaning"}),
        ("Pilot send backup a task to collect the dry cleaning", "inbox_delegate_spoken", {"recipient_name": "backup", "title": "collect the dry cleaning"}),
        ("Pilot's in back at a task to pick up some milk", "inbox_delegate_spoken", {"recipient_name": "back", "title": "pick up some milk"}),
        ("Pilot add lemonade to my text list", "inbox_add_self", {"title": "lemonade"}),
        ("Pilot tell Becca saying I will be home at six", "inbox_message_spoken", {"recipient_name": "becca", "body": "i will be home at six"}),
        ("Pilot start Spanish lesson", "education_start", {"profile_id": "explorer_a"}),
        ("Pilot movie mode", "scene_movie", {"app_id": "netflix", "volume": 20}),
        ("Pilot select the second Netflix profile", "netflix_profile", {"profile_index": 2, "remember": False}),
        ("Pilot open the second profile", "netflix_profile", {"profile_index": 2, "remember": False}),
        ("Pilot switch profile to two", "netflix_profile", {"profile_index": 2, "remember": False}),
        ("Pilot change Netflix profile to third", "netflix_profile", {"profile_index": 3, "remember": False}),
        ("Pilot open Netflix profile chooser", "netflix_profile_menu", {}),
        ("Pilot select visible second Netflix profile", "netflix_profile", {"profile_index": 2, "remember": False, "chooser_visible": True}),
        ("Pilot remember the third profile", "netflix_profile", {"profile_index": 3, "remember": True}),
        ("Pilot select my Netflix profile", "netflix_saved_profile", {}),
        ("Pilot go left", "remote_button", {"button": "LEFT"}),
        ("Pilot press OK", "remote_button", {"button": "ENTER"}),
        ("Pilot go home", "remote_button", {"button": "HOME"}),
        ("Pilot find me a locksmith in Albox", "web_research", {"query": "a locksmith in albox", "mode": "general"}),
        ("Pilot search Netflix for The Crown", "netflix_search", {"query": "the crown"}),
        ("Pilot search for The Crown", "web_research", {"query": "the crown", "mode": "contextual"}),
        ("Pilot search Google for The Crown", "web_research", {"query": "the crown", "mode": "general"}),
        ("Pilot open the second result", "open_research_result", {"result_index": 2}),
        ("Pilot show my results again", "show_research_results", {}),
        ("Pilot show me the evidence", "live_fact_followup", {"kind": "evidence"}),
        ("Pilot who disagrees with that", "live_fact_followup", {"kind": "disagreement"}),
        ("Pilot explain the difference", "live_fact_followup", {"kind": "difference"}),
        ("Pilot accept Google", "google_consent_accept", {"button": "ENTER"}),
        ("Pilot continue what I was watching", "continue_last", {}),
        ("Pilot make this comfortable for tonight", "scene_evening", {"volume": 18}),
        ("Pilot where can we watch Dune Part Two", "entertainment_search", {"query": "dune part two"}),
        ("Pilot search all streaming services for Severance", "entertainment_search", {"query": "severance"}),
        ("Pilot what should we watch under 90 minutes", "entertainment_recommend", {"query": "what should we watch under 90 minutes", "minutes": 90}),
        ("Pilot remember we watched The Crown", "entertainment_feedback", {"title": "the crown", "outcome": "watched"}),
        ("Pilot don't recommend The Crown", "entertainment_feedback", {"title": "the crown", "outcome": "avoid"}),
        ("Pilot we loved Severance", "entertainment_feedback", {"title": "severance", "outcome": "liked"}),
        ("Pilot recommend something funny under 90 minutes", "entertainment_recommend", {"query": "recommend something funny under 90 minutes", "minutes": 90}),
        ("Pilot stop", "exit_content", {"button": "BACK"}),
        ("Pilot exit The Crown", "exit_content", {"button": "BACK"}),
        ("Pilot leave this series", "exit_content", {"button": "BACK"}),
        ("Pilot sleep", "voice_sleep", {}),
        ("Pilot turn off the microphone", "voice_sleep", {}),
        ("Pilot pause this task", "conversation_pause", {}),
        ("Pilot resume the previous task", "conversation_resume", {}),
        ("Pilot what is the best ladder type for uneven ground", "web_research", {"query": "what is the best ladder type for uneven ground", "mode": "general"}),
        ("Pilot fact check that", "live_fact_check", {}),
        ("Pilot what just happened", "live_explain", {"kind": "recap", "spoiler_policy": "observed_evidence_only"}),
        ("Pilot clip the last 30 seconds of that and send it to Mike", "share_moment", {"seconds": 30, "recipient": "mike"}),
        ("Pilot share that", "share_moment", {"seconds": 30}),
        ("Pilot share that moment", "share_moment", {"seconds": 30}),
        ("Pilot what is on the screen", "screen_query", {"kind": "scene"}),
        ("Pilot what is the score", "live_event", {"kind": "score", "question": "what is the score"}),
        ("Pilot read the subtitle", "screen_query", {"kind": "subtitle"}),
        ("Pilot what product is that", "screen_query", {"kind": "product"}),
    ],
)
def test_voice_intents_require_wake_phrase_and_map_to_governed_actions(phrase, action, arguments):
    intent = parse_voice_intent(phrase)
    assert intent is not None
    assert intent.action == action
    assert intent.arguments == arguments
    assert parse_voice_intent("turn up the TV") is None


def test_old_product_name_is_not_the_voice_wake_phrase():
    assert parse_voice_intent("AION open games") is None


def test_wake_phrase_must_begin_the_utterance_to_reject_tv_dialogue():
    assert parse_voice_intent("the pilot says turn up the television") is None
    assert parse_voice_intent("we should ask Pilot to open Netflix") is None
    assert parse_voice_intent("Hey Pilot, open Netflix") is not None


def test_voice_volume_limit_never_turns_an_above_limit_tv_down_for_turn_up():
    with pytest.raises(PermissionError, match="already above"):
        WebOsGateway.voice_volume_target(
            current=49, action="change_volume", arguments={"delta": 2}, maximum=35
        )
    assert WebOsGateway.voice_volume_target(
        current=49, action="change_volume", arguments={"delta": -2}, maximum=35
    ) == 47


def test_pointer_navigation_rejects_non_tv_socket_before_connecting():
    with pytest.raises(ValueError, match="invalid local pointer socket"):
        WebOsGateway._send_pointer_buttons(
            socket_path="ws://8.8.8.8:3000/resources/input",
            host="192.168.1.40",
            buttons=["ENTER"],
        )


def test_netflix_profile_selection_normalises_current_focus_to_first_profile():
    assert WebOsGateway.netflix_profile_selection_buttons(1) == (["UP"] * 5) + ["ENTER"]
    assert WebOsGateway.netflix_profile_selection_buttons(2) == (["UP"] * 5) + ["DOWN", "ENTER"]
    assert WebOsGateway.netflix_profile_selection_buttons(5) == (["UP"] * 5) + (["DOWN"] * 4) + ["ENTER"]


def test_staged_pointer_navigation_rejects_unbounded_route_before_connecting():
    with pytest.raises(ValueError, match="bounded button policy"):
        WebOsGateway._send_pointer_button_phases(
            socket_path="ws://192.168.1.40:3000/resources/input",
            host="192.168.1.40",
            phases=[(["LEFT"] * 12, 0.1)] * 4,
        )


def test_pointer_touchpad_rejects_unbounded_movement_before_connecting():
    with pytest.raises(ValueError, match="bounded controller policy"):
        WebOsGateway._send_pointer_event(
            socket_path="ws://192.168.1.40:3000/resources/input",
            host="192.168.1.40",
            kind="move",
            dx=241,
            dy=0,
        )
