from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from backend.modules.aion_fabric.contracts import EnrollmentState
from backend.modules.aion_fabric.discovery import DiscoveryObservation, SafeDiscoveryEngine, profile_from_observation
from backend.modules.aion_fabric.field_operator import GovernedFieldOperator
from backend.modules.aion_fabric.schema import DeviceSchemaResolver
from backend.modules.aion_fabric.runtime import AionFabricRuntime


DEVICE_XML = b"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0"><device>
<deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
<friendlyName>Test Living Room TV</friendlyName><manufacturer>Test Manufacturer</manufacturer>
<modelName>Model One</modelName><modelNumber>1</modelNumber><serialNumber>serial-redacted</serialNumber>
<serviceList><service><serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
<serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
<SCPDURL>/render.xml</SCPDURL><controlURL>/control</controlURL></service></serviceList>
</device></root>"""

SERVICE_XML = b"""<?xml version="1.0"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0"><actionList>
<action><name>GetVolume</name><argumentList><argument><name>Channel</name><direction>in</direction><relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable></argument></argumentList></action>
<action><name>SetVolume</name><argumentList><argument><name>DesiredVolume</name><direction>in</direction><relatedStateVariable>Volume</relatedStateVariable></argument></argumentList></action>
<action><name>FactoryReset</name></action>
</actionList></scpd>"""


class DescriptorHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        payload = DEVICE_XML if self.path == "/device.xml" else SERVICE_XML
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):  # noqa: N802
        payload = b'''<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
<s:Body><u:GetVolumeResponse xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
<CurrentVolume>17</CurrentVolume></u:GetVolumeResponse></s:Body></s:Envelope>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


@pytest.fixture
def descriptor_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DescriptorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/device.xml"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_observation_becomes_untrusted_gateway_profile():
    observation = DiscoveryObservation(
        observation_id="obs_tv",
        source="ssdp",
        name="Living Room TV",
        addresses=["192.168.1.20"],
        identifiers={"usn": "uuid:test-tv"},
        attributes={"server": "Example TV UPnP"},
    )
    profile = profile_from_observation(observation)
    assert profile.device_class == "television"
    assert profile.can_install_runtime is False
    assert profile.controls == ()
    assert profile.metadata["observation_id"] == "obs_tv"


def test_local_descriptor_download_schema_and_controls_are_evidenced(tmp_path, descriptor_server):
    observation = DiscoveryObservation(
        observation_id="obs_upnp_tv",
        source="ssdp",
        name="UPnP device",
        addresses=["127.0.0.1"],
        identifiers={"usn": "uuid:upnp-tv"},
        attributes={"server": "Test server"},
        descriptor_urls=[descriptor_server],
        confidence=0.75,
    )
    schema = DeviceSchemaResolver(tmp_path / "docs").resolve("node_tv", observation)
    assert schema.friendly_name == "Test Living Room TV"
    assert schema.manufacturer == "Test Manufacturer"
    assert len(schema.documentation) == 2
    controls = {control.name: control for control in schema.controls}
    assert controls["GetVolume"].risk.value == "low"
    assert controls["SetVolume"].risk.value == "medium"
    assert controls["FactoryReset"].risk.value == "high"
    assert all(control.mode == "disabled_until_enrolled" for control in controls.values())

    operator = GovernedFieldOperator()
    blocked = operator.propose(
        schema,
        action_id=controls["SetVolume"].action_id,
        arguments={"DesiredVolume": 10},
        enrollment=EnrollmentState.DISCOVERED,
    )
    assert blocked.state == "blocked_not_enrolled"
    with pytest.raises(PermissionError):
        operator.execute(blocked)


def test_public_descriptor_download_is_rejected(tmp_path):
    observation = DiscoveryObservation(
        observation_id="obs_public",
        source="ssdp",
        name="Untrusted device",
        addresses=["192.168.1.5"],
        identifiers={"usn": "uuid:public"},
        attributes={},
        descriptor_urls=["https://example.com/device.xml"],
    )
    schema = DeviceSchemaResolver(tmp_path / "docs").resolve("node_public", observation)
    assert not schema.documentation
    assert "limited to the local network" in schema.evidence["errors"][0]


def test_bonjour_protocol_advertisements_merge_by_model_identity():
    airplay = DiscoveryObservation(
        observation_id="airplay",
        source="bonjour",
        name="[LG] webOS TV NU8E0B3LA",
        addresses=[],
        identifiers={"service_type": "_airplay._tcp", "service_instance": "LG TV"},
        attributes={"service_types": ["_airplay._tcp"]},
    )
    cast = DiscoveryObservation(
        observation_id="cast",
        source="bonjour",
        name="55NU8E0B3LA.BEUDLJP-device-id",
        addresses=["192.168.1.22"],
        identifiers={"service_type": "_googlecast._tcp", "service_instance": "Cast TV"},
        attributes={"service_types": ["_googlecast._tcp"]},
    )
    merged = SafeDiscoveryEngine._merge([airplay, cast])
    assert len(merged) == 1
    assert merged[0].addresses == ["192.168.1.22"]
    assert merged[0].attributes["service_types"] == ["_airplay._tcp", "_googlecast._tcp"]


def test_owner_can_enroll_gateway_with_only_evidenced_read_capabilities(
    tmp_path, descriptor_server
):
    observation = DiscoveryObservation(
        observation_id="obs_enroll_tv",
        source="ssdp",
        name="Test TV",
        addresses=["127.0.0.1"],
        identifiers={"usn": "uuid:enroll-tv"},
        attributes={"server": "Test server"},
        descriptor_urls=[descriptor_server],
        confidence=0.75,
    )
    runtime = AionFabricRuntime.bootstrap(tmp_path / "fabric")
    profile = profile_from_observation(observation)
    runtime.discover(profile, public_key="")
    schema = DeviceSchemaResolver(tmp_path / "fabric" / "documentation").resolve(
        profile.node_id, observation
    )
    runtime.store.save_schema(schema)
    result = runtime.enroll_gateway_for_read_only_testing(
        node_id=profile.node_id,
        approved_by="test_owner",
    )
    assert result["node"]["enrollment"] == "enrolled"
    assert result["read_only_capabilities"] == 1
    assert result["live_mutating_capabilities"] == 0
    capability = result["capsule"]["capabilities"][0]
    assert capability["kind"] == "observe"
    assert capability["capability_id"] == next(
        control.action_id for control in schema.controls if control.name == "GetVolume"
    )
    receipt = runtime.run_read_only_probe(node_id=profile.node_id)
    assert receipt.action_name == "GetVolume"
    assert receipt.values == {"CurrentVolume": "17"}
    assert receipt.verified_read_only is True
    assert runtime.status()["ledger"]["probe_receipts"] == 1


def test_persistent_device_identity_reconciliation_preserves_and_hides_duplicate(tmp_path):
    runtime = AionFabricRuntime.bootstrap(tmp_path / "fabric")
    observations = [
        DiscoveryObservation(
            observation_id=f"obs_tv_{suffix}",
            source="ssdp",
            name="Living Room TV",
            addresses=[address],
            identifiers={"usn": f"uuid:{suffix}::service"},
            attributes={"txt": {"id": "same-device-id", "model": "TV-1"}},
        )
        for suffix, address in (("first", "192.168.1.20"), ("second", "192.168.1.21"))
    ]
    records = [runtime.discover(profile_from_observation(item), public_key="") for item in observations]
    assert records[0].profile.node_id != records[1].profile.node_id

    result = runtime.reconcile_topology()
    refreshed = [runtime.store.get_node(item.profile.node_id) for item in records]
    visible = [item for item in refreshed if not item.profile.metadata.get("hidden_from_topology")]
    hidden = [item for item in refreshed if item.profile.metadata.get("hidden_from_topology")]
    assert len(visible) == 1
    assert len(hidden) == 1
    assert hidden[0].profile.metadata["superseded_by"] == visible[0].profile.node_id
    assert set(result["changed_node_ids"])
    assert len(runtime.store.list_nodes()) == 3  # mother and both preserved evidence records


def test_local_mother_service_is_hidden_from_topology(tmp_path):
    runtime = AionFabricRuntime.bootstrap(tmp_path / "fabric")
    observation = DiscoveryObservation(
        observation_id="obs_local_mac",
        source="bonjour",
        name="This MacBook Pro",
        addresses=["127.0.0.1"],
        identifiers={"service_type": "_airplay._tcp", "service_instance": "This MacBook Pro"},
        attributes={"txt": {"model": "Mac15,7"}},
    )
    profile = profile_from_observation(observation)
    record = runtime.discover(profile, public_key="")
    runtime.reconcile_topology()
    reconciled = runtime.store.get_node(record.profile.node_id)
    assert reconciled.profile.metadata["hidden_from_topology"] is True
    assert reconciled.profile.metadata["superseded_by"] == runtime.profile.node_id
