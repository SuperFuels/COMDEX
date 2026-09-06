from __future__ import annotations

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.contracts import (
    Capability,
    CapabilityKind,
    DeviceProfile,
    EnrollmentState,
    NodeRecord,
    NodeRole,
    RiskLevel,
    select_role,
)
from backend.modules.aion_fabric.delta import (
    DeltaPacket,
    apply_state_delta,
    new_delta_packet,
    new_glyph_delta_stream,
)
from backend.modules.aion_fabric.demo import run_local_demo
from backend.modules.aion_fabric.identity import DeviceIdentity, IdentityStore
from backend.modules.aion_fabric.runtime import AionFabricRuntime
from backend.modules.aion_fabric.store import FabricStore
from backend.modules.aion_fabric.cli import _dashboard_html, _sovereign_brain_html


def device(**changes):
    base = DeviceProfile(
        node_id="node_test",
        name="Test device",
        device_class="computer",
        platform="test",
        cpu_count=8,
        memory_bytes=16 * 1024**3,
        can_install_runtime=True,
        can_host_model=True,
        is_mains_powered=True,
        transports=("wifi",),
    )
    return replace(base, **changes)


def test_concurrent_audit_appends_keep_one_linear_chain(tmp_path):
    store = FabricStore(tmp_path / "concurrent-audit.sqlite3")
    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(lambda number: store.append_audit("concurrent_test", {"number": number}), range(80)))
    assert store.counts()["audit_ledger"] == 80
    assert store.verify_audit_chain() is True


def test_audit_retention_is_bounded_and_preserves_chain_checkpoint(tmp_path):
    store = FabricStore(
        tmp_path / "bounded-audit.sqlite3",
        audit_max_rows=12,
        audit_prune_to_rows=8,
    )
    store.AUDIT_PRUNE_CHECK_INTERVAL = 1
    for number in range(40):
        store.append_audit("microphone_activity", {"number": number})

    assert store.counts()["audit_ledger"] <= 12
    assert store.verify_audit_chain() is True
    with store.connect() as db:
        checkpoint = db.execute(
            "SELECT pruned_rows,pruned_through_sequence FROM audit_retention_checkpoint WHERE checkpoint_id=1"
        ).fetchone()
    assert checkpoint is not None
    assert checkpoint["pruned_rows"] > 0
    assert checkpoint["pruned_through_sequence"] > 0


def test_audit_retention_does_not_remove_durable_pairing_tables(tmp_path):
    store = FabricStore(
        tmp_path / "durable-state.sqlite3",
        audit_max_rows=8,
        audit_prune_to_rows=4,
    )
    store.AUDIT_PRUNE_CHECK_INTERVAL = 1
    record = NodeRecord(
        profile=device(node_id="paired-tv", name="Living room TV"),
        role=NodeRole.GATEWAY,
        public_key="public-key",
        enrollment=EnrollmentState.ENROLLED,
        mother_id="mother",
        last_seen_at="2026-09-06T00:00:00+00:00",
    )
    store.save_node(record)
    for number in range(30):
        store.append_audit("microphone_activity", {"number": number})

    restored = store.get_node("paired-tv")
    assert restored is not None
    assert restored.profile.name == "Living room TV"
    assert restored.enrollment is EnrollmentState.ENROLLED
    assert store.verify_audit_chain() is True


def test_role_selection_is_capability_based_and_conservative():
    assert select_role(device(), mother_present=False) is NodeRole.MOTHER
    assert select_role(device(), mother_present=True) is NodeRole.COMPUTE_WORKER
    assert select_role(
        device(can_host_model=False, cpu_count=1, memory_bytes=128, controls=("temperature",)),
        mother_present=True,
    ) is NodeRole.EDGE
    assert select_role(device(can_install_runtime=False), mother_present=True) is NodeRole.GATEWAY


def test_device_identity_signs_and_rejects_tampering(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    payload = b"aion-fabric"
    signature = identity.sign(payload)
    assert DeviceIdentity.verify(identity.public_key_b64, payload, signature)
    assert not DeviceIdentity.verify(identity.public_key_b64, b"tampered", signature)
    assert (tmp_path / "identity" / "device_ed25519.pem").stat().st_mode & 0o777 == 0o600


def test_delta_roundtrip_is_signed_and_replayable(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    previous = {"temperature": 4.0, "door": False, "unchanged": "kept"}
    current = {"temperature": 4.2, "door": False, "sample": 2}
    packet = new_delta_packet(
        node_id="fridge",
        sequence=1,
        previous=previous,
        current=current,
        identity=identity,
    )
    assert packet.verify(identity.public_key_b64)
    assert apply_state_delta(previous, packet.changes) == current
    decoded = DeltaPacket.from_transport_envelope(packet.transport_envelope())
    assert decoded.to_dict() == packet.to_dict()
    decoded.changes["temperature"]["value"] = 99
    assert not decoded.verify(identity.public_key_b64)


def test_enrollment_and_high_risk_capabilities_fail_closed(tmp_path):
    mother = AionFabricRuntime.bootstrap(tmp_path / "fabric", profile=device(node_id="mother"))
    node_identity = IdentityStore(tmp_path / "node_identity").load_or_create()
    node = device(
        node_id="fridge",
        can_host_model=False,
        cpu_count=1,
        memory_bytes=128,
        controls=("setpoint",),
    )
    discovered = mother.discover(node, node_identity.public_key_b64)
    assert discovered.enrollment is EnrollmentState.DISCOVERED
    with pytest.raises(PermissionError):
        mother.issue_capabilities(
            node.node_id,
            [Capability("observe", CapabilityKind.OBSERVE, "Observe")],
            approved_by="owner",
        )
    mother.enroll(node.node_id, approved_by="owner")
    with pytest.raises(ValueError):
        mother.issue_capabilities(
            node.node_id,
            [Capability("unlock", CapabilityKind.CONTROL, "Unlock", risk=RiskLevel.HIGH)],
            approved_by="owner",
        )


def test_end_to_end_demo_builds_mother_edge_gateway_and_ledger(tmp_path):
    result = run_local_demo(tmp_path / "demo")
    assert result["status"]["role"] == "mother"
    assert result["fridge_role"] == "edge"
    assert result["tv_role"] == "gateway"
    assert result["latest_fridge_state"]["sample_count"] == 1002
    assert result["status"]["ledger"]["nodes"] == 3
    assert result["status"]["ledger"]["delta_ledger"] == 2
    assert result["status"]["ledger"]["stream_ledger"] == 1
    assert result["status"]["audit_chain_valid"] is True
    assert result["transport"]["verified"] is True
    assert result["transport"]["saving_vs_repeated_raw_snapshots_percent"] > 90
    assert result["capability_capsule"]["signature"]


def test_glyph_stream_reconstructs_sparse_updates_and_rejects_tampering(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    states = [{"temperature": 4.0, "door": False, "sample": 0}]
    for sample in range(1, 1001):
        states.append({"temperature": 4.0 + (sample % 5) / 10, "door": False, "sample": sample})
    stream = new_glyph_delta_stream(
        node_id="fridge",
        start_sequence=1,
        states=states,
        identity=identity,
    )
    assert stream.verify(identity.public_key_b64)
    assert stream.states() == states
    full_bytes = sum(len(canonical_bytes(state)) for state in states[1:])
    assert len(canonical_bytes(stream.transport_envelope())) < full_bytes * 0.1
    stream.deltas[0][0][-1] = 999
    assert not stream.verify(identity.public_key_b64)


def test_demo_is_restart_safe_and_dashboard_is_human_readable(tmp_path):
    first = run_local_demo(tmp_path / "demo")
    second = run_local_demo(tmp_path / "demo")
    assert second["latest_fridge_state"] == first["latest_fridge_state"]
    runtime = AionFabricRuntime.bootstrap(tmp_path / "demo" / "mother")
    page = _dashboard_html(runtime, second).decode("utf-8")
    assert "<h1>Pilot</h1>" in page
    assert "Games" in page
    assert "AI TV" in page
    assert "AI Learning" in page
    assert "AI Shopping" in page
    assert "Your workspace" in page
    assert "Personal" in page
    assert "Household" in page
    assert "Workspace" in page
    assert "Boardroom" in page
    assert "Private workspace locked" in page
    assert 'data-launch="tasks"' not in page
    assert 'data-launch="calendar"' not in page
    assert 'data-launch="boardroom"' not in page
    assert 'data-launch="files"' not in page
    assert 'data-local-view="nodes-view"' not in page
    assert 'data-local-view="home-view"' in page
    assert 'data-launch="work"' not in page
    assert "Ask Pilot anything" in page
    assert "God View" in page
    assert 'href="/brain"' in page
    assert "How the second brain works" in page
    assert 'data-launch="god_view"' in page
    assert 'data-view="nodes-view"' not in page
    assert "/api/dashboard/action" in page
    assert "AION Native" in page
    assert "AION + Gemini" in page
    assert "Pilot Boost" in page
    assert "/api/intelligence/mode" in page
    assert "Demo Fridge" in page
    assert "Restricted Demo TV" in page
    assert "95." in page


def test_public_sovereign_brain_explainer_is_provider_independent():
    page = _sovereign_brain_html().decode("utf-8")
    assert "Your AI is not the model" in page
    assert "AION Flow" in page
    assert "A model output is a proposal, never authority" in page
    assert "Customer cloud" in page
    assert "Remove a provider and your brain still boots" in page
    assert "<script" not in page
