from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.infrared_gateway import LocalInfraredClimateGateway
from backend.modules.aion_fabric.voice import parse_voice_intent


class FakeBroadlink:
    host = ("192.168.18.44", 80)
    mac = bytes.fromhex("aabbccddeeff")
    devtype = 0x5F36

    def __init__(self, packet: bytes = b"0123456789abcdef"):
        self.packet = packet
        self.learning = False
        self.sent = []

    def auth(self):
        return True

    def enter_learning(self):
        self.learning = True

    def check_data(self):
        return self.packet if self.learning else None

    def send_data(self, data):
        self.sent.append(data)


def gateway(tmp_path, device, interval=0):
    return LocalInfraredClimateGateway(tmp_path, discover=lambda **_: [device], minimum_send_interval_seconds=interval)


def test_discovers_selects_learns_and_sends_without_claiming_state(tmp_path):
    device = FakeBroadlink()
    bridge = gateway(tmp_path, device)
    discovery = bridge.discover()
    assert discovery["selected"]["host"] == "192.168.18.44"

    bridge.begin_learning("cool_22")
    learned = bridge.capture_learning()
    receipt = bridge.send("cool_22")

    assert learned["bytes"] == 16
    assert device.sent == [b"0123456789abcdef"]
    assert receipt["transport_delivered"] is True
    assert receipt["air_conditioner_state_verified"] is False
    assert bridge.snapshot()["learned_presets"][0]["preset"] == "cool_22"
    assert "data_b64" not in json.dumps(bridge.snapshot())


@pytest.mark.parametrize("preset", ["toggle", "cool_15", "heat_31", "cool_22;rm"])
def test_rejects_unsafe_or_ambiguous_presets(tmp_path, preset):
    with pytest.raises(ValueError):
        gateway(tmp_path, FakeBroadlink()).begin_learning(preset)


def test_rejects_unlearned_and_corrupt_codes(tmp_path):
    bridge = gateway(tmp_path, FakeBroadlink())
    bridge.discover()
    with pytest.raises(LookupError, match="has not been learned"):
        bridge.send("off")
    bridge.codes_path.write_text('{"codes":{"off":{"data_b64":"AA==","sha256":"bad"}}}')
    with pytest.raises(RuntimeError, match="integrity"):
        bridge.send("off")


def test_rate_limits_repeated_transmission(tmp_path):
    bridge = gateway(tmp_path, FakeBroadlink(), interval=60)
    bridge.discover()
    bridge.begin_learning("off")
    bridge.capture_learning()
    bridge.send("off")
    with pytest.raises(RuntimeError, match="wait"):
        bridge.send("off")


def test_missing_driver_or_device_is_reported_without_false_connection(tmp_path):
    bridge = LocalInfraredClimateGateway(tmp_path, discover=lambda **_: [])
    result = bridge.discover()
    assert result["found"] == []
    assert result["requires_initial_wifi_provisioning"] is True
    assert bridge.snapshot()["connected"] is False


def test_voice_routes_explicit_air_conditioner_presets_without_tv_intent():
    cool = parse_voice_intent("Pilot, set the air con to 22 degrees")
    heat = parse_voice_intent("Pilot, heat the room to 20")
    off = parse_voice_intent("Pilot, turn the air con off")
    on = parse_voice_intent("Pilot, turn on the air con")
    assert (cool.action, cool.arguments, cool.device) == ("climate_ir", {"preset": "cool_22"}, "air_conditioner")
    assert heat.arguments == {"preset": "heat_20"}
    assert off.arguments == {"preset": "off"}
    assert on.arguments == {"preset": "last_active"}


@pytest.mark.parametrize(
    "phrase",
    [
        "Pilot turn on air con",
        "Pilot turn on the aircon",
        "Pilot turn the AC on",
        "Pilot turn the A C on",
    ],
)
def test_common_asr_aircon_spellings_never_fall_through_to_planning(phrase):
    intent = parse_voice_intent(phrase)
    assert intent.action == "climate_ir"
    assert intent.arguments == {"preset": "last_active"}
