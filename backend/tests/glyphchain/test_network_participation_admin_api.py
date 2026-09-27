from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.modules.aion_business.api import glyphchain_admin_api as api
from backend.modules.aion_business.runtime.aion_flow_session_authority import AionFlowSessionAuthority


SECRET = b"glyphchain-admin-test-secret-32-bytes-minimum"
NOW = 1_790_000_000
ROOT = Path(__file__).resolve().parents[3]


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("GLYPHCHAIN_PARTICIPATION_DIR", str(tmp_path / "participation"))
    monkeypatch.setenv("GLYPHCHAIN_NETWORK_KEY_DIR", str(tmp_path / "network-identity"))
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-test")
    monkeypatch.setenv("GLYPHCHAIN_NODE_ID", "node-test")
    monkeypatch.setenv("GLYPHCHAIN_HEALTH_DIR", str(tmp_path / "health"))
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_UPGRADE_DIR", str(tmp_path / "protocol-upgrade"))
    api._authority = AionFlowSessionAuthority(secret=SECRET, clock=lambda: NOW)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _post(client, path: str, payload: dict | None = None):
    body = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
    headers = api._authority.sign_for_test(
        method="POST", target=path, body=body,
        device_id="device-1", person_id="owner-1", workspace_id="workspace-a",
        issued_at=NOW,
    )
    return client.post(path, content=body, headers={**headers, "content-type": "application/json"})


def _post_raw(client, path: str, body: bytes, *, content_type: str):
    headers = api._authority.sign_for_test(
        method="POST", target=path, body=body,
        device_id="device-1", person_id="owner-1", workspace_id="workspace-a",
        issued_at=NOW,
    )
    return client.post(path, content=body, headers={**headers, "content-type": content_type})


@pytest.mark.asyncio
async def test_snapshot_body_is_streamed_to_private_file_before_signature_verification(
    monkeypatch, tmp_path
):
    body = b"snapshot-bytes-in-two-chunks"
    path = "/api/aion/business/glyphchain-admin/snapshot/verify"
    authority = AionFlowSessionAuthority(secret=SECRET, clock=lambda: NOW)
    monkeypatch.setattr(api, "_authority", authority)
    monkeypatch.setattr(api, "configured_ledger_limit_bytes", lambda: 1024)
    signed = authority.sign_for_test(
        method="POST", target=path, body=body,
        device_id="device-1", person_id="owner-1", workspace_id="workspace-a",
        issued_at=NOW,
    )
    raw_headers = [
        (key.lower().encode("ascii"), value.encode("ascii"))
        for key, value in signed.items()
    ] + [
        (b"content-type", api.SNAPSHOT_MEDIA_TYPE.encode("ascii")),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    chunks = iter((body[:10], body[10:]))

    async def receive():
        try:
            chunk = next(chunks)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": chunk, "more_body": chunk != body[10:]}

    request = Request({
        "type": "http", "method": "POST", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": raw_headers, "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1),
    }, receive)
    session = await api.require_signed_desktop_admin(request)
    assert session.workspace_id == "workspace-a"
    root, snapshot = request.state.glyphchain_snapshot_upload
    try:
        assert snapshot.read_bytes() == body
        assert snapshot.stat().st_mode & 0o777 == 0o600
        assert root.stat().st_mode & 0o777 == 0o700
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_snapshot_import_cleans_staged_upload_when_confirmation_is_rejected(tmp_path):
    root = tmp_path / "staged-upload"
    root.mkdir()
    snapshot = root / "received.glyphchain-snapshot"
    snapshot.write_bytes(b"bounded-snapshot")
    request = Request({
        "type": "http", "method": "POST",
        "path": "/api/aion/business/glyphchain-admin/snapshot/import",
        "raw_path": b"/api/aion/business/glyphchain-admin/snapshot/import",
        "query_string": b"", "headers": [], "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1),
    })
    request.state.glyphchain_snapshot_upload = (root, snapshot)
    session = SimpleNamespace(workspace_id="workspace-a", person_id="owner-1")

    with pytest.raises(api.HTTPException) as rejected:
        await api.import_snapshot(request, confirmation="wrong", session=session)

    assert rejected.value.status_code == 422
    assert not root.exists()


def test_status_requires_a_signed_desktop_session(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    path = "/api/aion/business/glyphchain-admin/status"
    assert client.post(path, json={}).status_code == 401
    response = _post(client, path)
    assert response.status_code == 200
    value = response.json()
    assert value["participation"]["role"] == "light"
    assert value["authenticated_by"] == "signed_desktop_session"


def test_relay_configuration_uses_authenticated_person_as_operator(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    path = "/api/aion/business/glyphchain-admin/configure"
    response = _post(client, path, {
        "role": "relay",
        "confirmation": "ENABLE GLYPHCHAIN RELAY",
        "public_connectivity_acknowledged": True,
        "storage_limit_bytes": 128 * 1024 * 1024,
    })
    assert response.status_code == 200
    value = response.json()
    assert value["participation"]["operator_id"] == "owner-1"
    assert value["participation"]["role"] == "relay"
    assert value["restart_required"] is True


def test_validator_configuration_preserves_all_release_gates(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    path = "/api/aion/business/glyphchain-admin/configure"
    incomplete = _post(client, path, {
        "role": "validator",
        "confirmation": "ENABLE GLYPHCHAIN VALIDATOR",
        "public_connectivity_acknowledged": True,
    })
    assert incomplete.status_code == 422
    assert "availability" in incomplete.json()["detail"]

    configured = _post(client, path, {
        "role": "validator",
        "confirmation": "ENABLE GLYPHCHAIN VALIDATOR",
        "public_connectivity_acknowledged": True,
        "availability_acknowledged": True,
        "key_custody_acknowledged": True,
        "governance_approval_id": "admission-42",
        "validator_set_checkpoint_id": "checkpoint-42",
    })
    assert configured.status_code == 200
    assert configured.json()["participation"]["capabilities"]["vote"] is True


def test_disable_requires_exact_confirmation_and_retains_audit(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _post(client, "/api/aion/business/glyphchain-admin/configure", {
        "role": "relay", "confirmation": "ENABLE GLYPHCHAIN RELAY",
        "public_connectivity_acknowledged": True,
    })
    path = "/api/aion/business/glyphchain-admin/disable"
    rejected = _post(client, path, {"reason": "Device retired", "confirmation": "disable"})
    assert rejected.status_code == 422
    disabled = _post(client, path, {
        "reason": "Device retired", "confirmation": "DISABLE GLYPHCHAIN PARTICIPATION",
    })
    assert disabled.status_code == 200
    assert disabled.json()["participation"]["role"] == "light"
    status = _post(client, "/api/aion/business/glyphchain-admin/status").json()
    assert status["audit_chain_valid"] is True


def test_vault_exposes_signed_explicit_participation_controls():
    source = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    for marker in (
        'data-aion-glyphchain-admin="true"',
        "Choose what this device contributes",
        "Normal installations remain light nodes",
        "ENABLE GLYPHCHAIN RELAY",
        "ENABLE GLYPHCHAIN VALIDATOR",
        "DISABLE GLYPHCHAIN PARTICIPATION",
        "PRUNE_GLYPHCHAIN_HISTORY_WITH_VERIFIED_ARCHIVE",
        "Proof-preserving storage maintenance",
        "signAionFlowRequest",
        "Saving requires an application restart",
    ):
        assert marker in source


def test_signed_admin_rotates_network_identity_with_explicit_confirmation(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    status_path = "/api/aion/business/glyphchain-admin/network-identity/status"
    first = _post(client, status_path).json()["identity"]
    rejected = _post(client, "/api/aion/business/glyphchain-admin/network-identity/rotate", {
        "reason": "Scheduled rotation", "confirmation": "rotate",
    })
    assert rejected.status_code == 422
    rotated = _post(client, "/api/aion/business/glyphchain-admin/network-identity/rotate", {
        "reason": "Scheduled rotation", "confirmation": "ROTATE GLYPHCHAIN NETWORK KEY",
    })
    assert rotated.status_code == 200
    assert rotated.json()["identity"]["active_version"] == 2
    assert rotated.json()["identity"]["public_key_hex"] != first["public_key_hex"]
    assert rotated.json()["restart_required"] is True
    assert _post(client, status_path).json()["rotation_chain_valid"] is True


def test_signed_admin_exports_and_restores_encrypted_network_recovery(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    export_path = "/api/aion/business/glyphchain-admin/network-identity/recovery/export"
    exported = _post(client, export_path, {"password": "correct horse battery staple"})
    assert exported.status_code == 200
    bundle = exported.json()["recovery_bundle"]
    missing_ack = _post(client, "/api/aion/business/glyphchain-admin/network-identity/recovery/import", {
        "password": "correct horse battery staple", "recovery_bundle": bundle,
    })
    assert missing_ack.status_code == 422
    restored = _post(client, "/api/aion/business/glyphchain-admin/network-identity/recovery/import", {
        "password": "correct horse battery staple", "recovery_bundle": bundle,
        "acknowledge_device_key_restore": True,
    })
    assert restored.status_code == 200
    assert restored.json()["restored_key_versions"] == 1
    assert restored.json()["restart_required"] is True


def test_signed_admin_captures_privacy_safe_health_and_history(monkeypatch, tmp_path):
    from backend.modules.consensus import engine
    from backend.modules.p2p import ingress

    consensus = SimpleNamespace(status=lambda: {
        "chain_id": "private-chain-name",
        "network_participation": {"role": "light"},
        "finalized_height": 7,
        "height": 8,
        "round": 0,
        "last_qc": {"height": 7, "block_id": "hidden-block", "ts_ms": 9_999_999_999_999},
        "recent_qcs": [{"height": 7, "block_id": "hidden-block"}],
        "quorum_finality": {"enabled": True, "latest_certificate": {"version": 2}},
    })
    lanes = SimpleNamespace(snapshot=lambda: {"lanes": {}})
    monkeypatch.setattr(engine, "get_engine", lambda: consensus)
    monkeypatch.setattr(ingress, "get_lanes", lambda: lanes)
    monkeypatch.setattr(api, "list_peers", lambda: [SimpleNamespace(
        node_id="private-peer", base_url="https://private-peer.example", role="relay",
        hello_ok=True, banned=False, last_seen_ms=NOW * 1000,
    )])
    monkeypatch.setattr(api, "peer_store_status", lambda: {"peer_count": 1, "peer_limit": 8})
    monkeypatch.setattr(api, "persist_ledger_storage_status", lambda: {
        "persistence_enabled": True, "max_bytes": 1000, "used_bytes": 100,
        "remaining_bytes": 900, "utilization_percent": 10.0,
        "near_capacity": False, "at_capacity": False,
        "policy": "fail_closed_no_automatic_pruning",
    })

    client = _client(monkeypatch, tmp_path)
    captured = _post(client, "/api/aion/business/glyphchain-admin/health/snapshot")
    assert captured.status_code == 200
    value = captured.json()
    assert value["history_chain_valid"] is True
    assert value["health"]["status"] == "healthy"
    assert value["health"]["peers"]["verified"] == 1
    assert value["health"]["ledger_storage"]["remaining_bytes"] == 900
    encoded = json.dumps(value)
    assert "private-peer" not in encoded
    assert "private-chain-name" not in encoded

    history = _post(client, "/api/aion/business/glyphchain-admin/health/history", {"limit": 10})
    assert history.status_code == 200
    assert len(history.json()["history"]) == 1
    assert history.json()["history_chain_valid"] is True

    storage = _post(client, "/api/aion/business/glyphchain-admin/storage/status")
    assert storage.status_code == 200
    assert storage.json()["ledger_storage"]["policy"] == "fail_closed_no_automatic_pruning"
    assert storage.json()["peer_storage"]["peer_limit"] == 8


def test_partition_safety_halt_clearance_requires_signed_admin_and_exact_evidence(monkeypatch, tmp_path):
    from backend.modules.consensus import engine

    seen = {}

    class FakeEngine:
        def status(self):
            return {"partition_recovery": {"phase": "SAFETY_HALT", "halt_id": "sha256:halt-1"}}

        def clear_partition_safety_halt(self, **kwargs):
            seen.update(kwargs)
            if kwargs["confirmation"] != "CLEAR GLYPHCHAIN PARTITION SAFETY HALT":
                raise ValueError("partition recovery clearance confirmation required")
            if kwargs["halt_id"] != "sha256:halt-1":
                raise ValueError("partition recovery halt identifier mismatch")
            return {"phase": "REJOIN_ASSESSING", "halt_id": ""}

    monkeypatch.setattr(engine, "get_engine", lambda: FakeEngine())
    client = _client(monkeypatch, tmp_path)
    status_path = "/api/aion/business/glyphchain-admin/partition-recovery/status"
    assert client.post(status_path, json={}).status_code == 401
    assert _post(client, status_path).json()["partition_recovery"]["phase"] == "SAFETY_HALT"

    clear_path = "/api/aion/business/glyphchain-admin/partition-recovery/clear-safety-halt"
    rejected = _post(client, clear_path, {
        "halt_id": "sha256:halt-1",
        "reason": "Independent checkpoint review completed",
        "confirmation": "clear",
    })
    assert rejected.status_code == 422
    cleared = _post(client, clear_path, {
        "halt_id": "sha256:halt-1",
        "reason": "Independent checkpoint review completed",
        "confirmation": "CLEAR GLYPHCHAIN PARTITION SAFETY HALT",
    })
    assert cleared.status_code == 200
    assert cleared.json()["partition_recovery"]["phase"] == "REJOIN_ASSESSING"
    assert seen["operator_id"] == "owner-1"


def test_signed_snapshot_verify_accepts_raw_bound_archive(monkeypatch, tmp_path):
    from backend.modules.consensus import engine
    from backend.modules.chain_sim.ledger_snapshot import SNAPSHOT_MEDIA_TYPE

    class Verified:
        cleaned = False

        def summary(self):
            return {"snapshot_id": "ab" * 32, "ledger": {"height": 7}, "verified": True}

        def cleanup(self):
            self.cleaned = True

    verified = Verified()
    monkeypatch.setattr(engine, "get_engine", lambda: SimpleNamespace(
        chain_id="glyphchain-test", network_id="snapshotnet",
    ))
    monkeypatch.setattr(api, "_trusted_checkpoint", lambda: object())
    monkeypatch.setattr(api, "verify_ledger_snapshot", lambda *args, **kwargs: verified)
    client = _client(monkeypatch, tmp_path)
    path = "/api/aion/business/glyphchain-admin/snapshot/verify"
    response = _post_raw(client, path, b"signed-raw-snapshot", content_type=SNAPSHOT_MEDIA_TYPE)
    assert response.status_code == 200
    assert response.json()["snapshot"]["ledger"]["height"] == 7
    assert response.json()["installed"] is False
    assert verified.cleaned is True


def test_snapshot_import_requires_exact_confirmation_and_light_role(monkeypatch, tmp_path):
    from backend.modules.chain_sim.ledger_snapshot import SNAPSHOT_MEDIA_TYPE

    client = _client(monkeypatch, tmp_path)
    missing_path = "/api/aion/business/glyphchain-admin/snapshot/import"
    missing = _post_raw(client, missing_path, b"snapshot", content_type=SNAPSHOT_MEDIA_TYPE)
    assert missing.status_code == 422
    assert missing.json()["detail"] == "glyphchain_snapshot_install_confirmation_required"

    _post(client, "/api/aion/business/glyphchain-admin/configure", {
        "role": "relay", "confirmation": "ENABLE GLYPHCHAIN RELAY",
        "public_connectivity_acknowledged": True,
    })
    monkeypatch.setattr(api, "participation_from_env", lambda: {"role": "relay"})
    path = (
        "/api/aion/business/glyphchain-admin/snapshot/import"
        "?confirmation=INSTALL_VERIFIED_GLYPHCHAIN_SNAPSHOT"
    )
    elevated = _post_raw(client, path, b"snapshot", content_type=SNAPSHOT_MEDIA_TYPE)
    assert elevated.status_code == 409
    assert elevated.json()["detail"] == "glyphchain_snapshot_import_requires_light_role"


def test_snapshot_import_installs_only_after_verified_light_node_check(monkeypatch, tmp_path):
    from backend.modules.consensus import engine
    from backend.modules.chain_sim.ledger_snapshot import SNAPSHOT_MEDIA_TYPE

    class Verified:
        database_path = tmp_path / "verified.sqlite3"
        cleaned = False

        def summary(self):
            return {
                "snapshot_id": "cd" * 32,
                "ledger": {"height": 9, "database_sha256": "ef" * 32},
                "verified": True,
            }

        def cleanup(self):
            self.cleaned = True

    verified = Verified()
    verified.database_path.write_bytes(b"verified")
    monkeypatch.setattr(engine, "get_engine", lambda: SimpleNamespace(
        chain_id="glyphchain-test", network_id="snapshotnet",
    ))
    monkeypatch.setattr(api, "_trusted_checkpoint", lambda: object())
    monkeypatch.setattr(api, "persist_get_checkpoint", lambda: {"last_height": 7})
    seen = {}

    def verify(*args, **kwargs):
        seen["minimum_height"] = kwargs["minimum_height"]
        return verified

    monkeypatch.setattr(api, "verify_ledger_snapshot", verify)
    monkeypatch.setattr(api, "install_verified_ledger_database", lambda path, **kwargs: {
        "installed": True, "backup_retained": True, "restart_required": True,
    })
    client = _client(monkeypatch, tmp_path)
    path = (
        "/api/aion/business/glyphchain-admin/snapshot/import"
        "?confirmation=INSTALL_VERIFIED_GLYPHCHAIN_SNAPSHOT"
    )
    response = _post_raw(client, path, b"snapshot", content_type=SNAPSHOT_MEDIA_TYPE)
    assert response.status_code == 200
    assert response.json()["restart_required"] is True
    assert seen["minimum_height"] == 7
    assert verified.cleaned is True


def test_signed_admin_syncs_newer_snapshot_from_verified_peer(monkeypatch, tmp_path):
    from backend.modules.consensus import engine

    class Verified:
        database_path = tmp_path / "verified-peer.sqlite3"
        cleaned = False

        def summary(self):
            return {
                "snapshot_id": "12" * 32,
                "ledger": {"height": 12, "database_sha256": "34" * 32},
                "verified": True,
            }

        def cleanup(self):
            self.cleaned = True

    verified = Verified()
    verified.database_path.write_bytes(b"verified-peer")
    monkeypatch.setattr(engine, "get_engine", lambda: SimpleNamespace(
        chain_id="glyphchain-test", network_id="snapshotnet",
    ))
    monkeypatch.setattr(api, "persist_get_checkpoint", lambda: {"last_height": 9})
    monkeypatch.setenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", "11" * 32)
    monkeypatch.setattr(api, "get_peer_by_node_id", lambda node_id: SimpleNamespace(
        node_id=node_id, base_url="https://relay.example", banned=False, hello_ok=True,
    ))
    monkeypatch.setattr(api, "_trusted_checkpoint", lambda: object())
    seen = {}

    async def download(base_url, path, body, **kwargs):
        seen["base_url"] = base_url
        seen["path"] = path
        seen["envelope"] = body
        Path(kwargs["output_path"]).write_bytes(b"archive")
        return {"bytes": 7, "snapshot_id": "12" * 32, "snapshot_height": "12"}

    def verify(*args, **kwargs):
        seen["minimum_height"] = kwargs["minimum_height"]
        return verified

    monkeypatch.setattr(api, "post_file", download)
    monkeypatch.setattr(api, "verify_ledger_snapshot", verify)
    monkeypatch.setattr(api, "install_verified_ledger_database", lambda path, **kwargs: {
        "installed": True, "backup_retained": True, "restart_required": True,
    })
    client = _client(monkeypatch, tmp_path)
    response = _post(client, "/api/aion/business/glyphchain-admin/snapshot/sync-from-peer", {
        "peer_node_id": "relay-1",
        "confirmation": "SYNC_VERIFIED_GLYPHCHAIN_SNAPSHOT",
    })
    assert response.status_code == 200
    assert response.json()["snapshot"]["ledger"]["height"] == 12
    assert response.json()["transport_bytes"] == 7
    assert response.json()["restart_required"] is True
    assert seen["base_url"] == "https://relay.example"
    assert seen["path"] == "/api/p2p/snapshot_req"
    assert seen["minimum_height"] == 10
    assert seen["envelope"]["type"] == "SNAPSHOT_REQ"
    assert seen["envelope"]["payload"]["sig_hex"]
    assert verified.cleaned is True


def test_pruning_requires_exact_confirmation_and_light_role(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    path = "/api/aion/business/glyphchain-admin/storage/prune-with-archive"
    rejected = _post(client, path, {"confirmation": "prune", "reason": "bounded storage"})
    assert rejected.status_code == 422
    monkeypatch.setattr(api, "participation_from_env", lambda: {"role": "validator"})
    elevated = _post(client, path, {
        "confirmation": "PRUNE_GLYPHCHAIN_HISTORY_WITH_VERIFIED_ARCHIVE",
        "reason": "bounded storage",
    })
    assert elevated.status_code == 409
    assert elevated.json()["detail"] == "glyphchain_pruning_requires_light_role"


def test_pruning_archives_verifies_rechecks_and_installs(monkeypatch, tmp_path):
    from backend.modules.consensus import engine
    from backend.modules.chain_sim import chain_sim_state

    database = tmp_path / "live.sqlite3"
    database.write_bytes(b"live-ledger")
    verified_database = tmp_path / "verified.sqlite3"
    verified_database.write_bytes(b"verified-ledger")

    class Verified:
        database_path = verified_database
        cleaned = False

        def cleanup(self):
            self.cleaned = True

    verified = Verified()
    fake_engine = SimpleNamespace(
        chain_id="glyphchain-test", network_id="snapshotnet",
        finality_receipt=lambda height: {"quorum_finality_certificate": {"version": 2}},
    )
    monkeypatch.setattr(engine, "get_engine", lambda: fake_engine)
    monkeypatch.setattr(api, "participation_from_env", lambda: {"role": "light"})
    monkeypatch.setattr(api, "persist_database_path", lambda: database)
    monkeypatch.setattr(api, "persist_get_checkpoint", lambda: {
        "last_height": 7, "last_state_root": "aa" * 32,
    })
    monkeypatch.setattr(api, "_trusted_checkpoint", lambda: SimpleNamespace(value={"checkpoint": True}))
    monkeypatch.setattr(api, "_pruning_archive_root", lambda: tmp_path / "archives")
    (tmp_path / "archives").mkdir()
    exports = []

    def export(**kwargs):
        Path(kwargs["output_path"]).write_bytes(b"snapshot")
        exports.append(Path(kwargs["output_path"]))
        return {
            "snapshot_id": "12" * 32,
            "ledger": {"height": 7, "database_sha256": "34" * 32},
        }

    monkeypatch.setattr(api, "export_ledger_snapshot", export)
    monkeypatch.setattr(api, "verify_ledger_snapshot", lambda *args, **kwargs: verified)
    monkeypatch.setattr(chain_sim_state, "export_chain_state", lambda **kwargs: {
        "state": {"config": {}, "bank": {}, "staking": {}},
        "state_root": "aa" * 32,
    })
    monkeypatch.setattr(api, "compact_ledger_copy", lambda **kwargs: {
        "database_sha256": "56" * 32,
        "base_height": 7,
        "blocks_removed": 6,
        "transactions_removed": 6,
    })
    monkeypatch.setattr(api, "install_verified_ledger_database", lambda *args, **kwargs: {
        "installed": True, "backup_retained": True, "restart_required": True,
    })
    client = _client(monkeypatch, tmp_path)
    response = _post(client, "/api/aion/business/glyphchain-admin/storage/prune-with-archive", {
        "confirmation": "PRUNE_GLYPHCHAIN_HISTORY_WITH_VERIFIED_ARCHIVE",
        "reason": "Owner-approved bounded storage maintenance",
    })
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["archive"]["retained"] is True
    assert value["pruning"]["blocks_removed"] == 6
    assert value["restart_required"] is True
    assert len(exports) == 2
    assert exports[0].exists()
    assert verified.cleaned is True


def test_protocol_upgrade_admin_schedule_status_cancel_and_complete(monkeypatch, tmp_path):
    from backend.modules.consensus import engine

    height = {"value": 10}
    fake_engine = SimpleNamespace(status=lambda: {
        "finalized_height": height["value"],
        "protocol_upgrade": {"phase": "SCHEDULED", "consensus_allowed": True},
    })
    monkeypatch.setattr(engine, "get_engine", lambda: fake_engine)
    monkeypatch.setattr(api, "_trusted_checkpoint", lambda: SimpleNamespace(checkpoint_id="checkpoint-1"))
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_UPGRADE_MIN_LEAD_BLOCKS", "1")
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED", "2")
    client = _client(monkeypatch, tmp_path)

    scheduled = _post(client, "/api/aion/business/glyphchain-admin/protocol-upgrade/schedule", {
        "target_version": 2,
        "activation_height": 20,
        "release_manifest_sha256": "ab" * 32,
        "validator_checkpoint_id": "checkpoint-1",
        "governance_approval_id": "governance-1",
        "confirmation": "SCHEDULE GLYPHCHAIN PROTOCOL UPGRADE",
    })
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["protocol_upgrade"]["plan"]["target_version"] == 2
    status = _post(client, "/api/aion/business/glyphchain-admin/protocol-upgrade/status")
    assert status.status_code == 200

    cancelled = _post(client, "/api/aion/business/glyphchain-admin/protocol-upgrade/cancel", {
        "reason": "release withdrawn",
        "confirmation": "CANCEL GLYPHCHAIN PROTOCOL UPGRADE",
    })
    assert cancelled.status_code == 200

    rescheduled = _post(client, "/api/aion/business/glyphchain-admin/protocol-upgrade/schedule", {
        "target_version": 2,
        "activation_height": 20,
        "release_manifest_sha256": "cd" * 32,
        "validator_checkpoint_id": "checkpoint-1",
        "governance_approval_id": "governance-2",
        "confirmation": "SCHEDULE GLYPHCHAIN PROTOCOL UPGRADE",
    })
    assert rescheduled.status_code == 200
    height["value"] = 20
    completed = _post(client, "/api/aion/business/glyphchain-admin/protocol-upgrade/complete", {
        "confirmation": "COMPLETE GLYPHCHAIN PROTOCOL UPGRADE",
    })
    assert completed.status_code == 200, completed.text
    assert completed.json()["protocol_upgrade"]["current_protocol_version"] == 2
