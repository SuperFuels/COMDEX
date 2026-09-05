from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.sovereign_runtime_supervisor import SovereignRuntimeSupervisor
from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.ownership import MotherOwnershipAuthority


def test_healthy_runtime_resets_failures_without_restart(tmp_path):
    supervisor = SovereignRuntimeSupervisor(tmp_path / "supervisor.json")
    supervisor.initialize()
    calls = []
    result = supervisor.check_and_recover(health_check=lambda: True, restart=lambda: calls.append(1) or True)
    assert result["status"] == "healthy"
    assert result["action"] == "none"
    assert calls == []


def test_unhealthy_runtime_recovers_once_and_verifies_health(tmp_path):
    supervisor = SovereignRuntimeSupervisor(tmp_path / "supervisor.json", cooldown_seconds=5)
    supervisor.initialize()
    health = iter([False, True])
    restarts = []
    result = supervisor.check_and_recover(
        health_check=lambda: next(health), restart=lambda: restarts.append("restart") or True
    )
    assert result["status"] == "recovered"
    assert result["action"] == "restarted"
    assert restarts == ["restart"]


def test_recovery_is_cooled_down_and_stops_after_bound(tmp_path):
    supervisor = SovereignRuntimeSupervisor(tmp_path / "supervisor.json", max_attempts=2, cooldown_seconds=10)
    supervisor.initialize()
    instant = datetime.now(timezone.utc)
    first = supervisor.check_and_recover(health_check=lambda: False, restart=lambda: False, now=instant)
    assert first["action"] == "restart_failed"
    waiting = supervisor.check_and_recover(
        health_check=lambda: False, restart=lambda: False, now=instant + timedelta(seconds=2)
    )
    assert waiting["action"] == "wait"
    final = supervisor.check_and_recover(
        health_check=lambda: False, restart=lambda: False, now=instant + timedelta(seconds=11)
    )
    assert final["status"] == "manual_recovery_required"
    assert final["recovery_attempts"] == 2
    stopped = supervisor.check_and_recover(
        health_check=lambda: False, restart=lambda: True, now=instant + timedelta(seconds=22)
    )
    assert stopped["action"] == "stop"


def test_failed_signed_update_rolls_back_and_restarts_previous_runtime(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    authority = MotherOwnershipAuthority(tmp_path / "runtime", identity=identity, mother_id="brain_test")
    artifact = tmp_path / "update.bin"
    artifact.write_bytes(b"candidate")
    digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    authority.stage_update(
        artifact=artifact,
        signature=identity.sign(canonical_bytes({"version": "2.0.0", "sha256": digest})),
        signer_public_key=identity.public_key_b64,
        version="2.0.0",
    )
    supervisor = SovereignRuntimeSupervisor(tmp_path / "supervisor.json")
    restarted = []
    result = supervisor.verify_update(
        authority=authority,
        version="2.0.0",
        health_check=lambda: False,
        restart_previous=lambda: restarted.append(True) or True,
    )
    assert result["status"] == "rolled_back"
    assert result["previous_runtime_restarted"] is True
    assert restarted == [True]
