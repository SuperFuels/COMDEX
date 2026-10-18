from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.vault_store import AionLearningVaultStore
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat


def _learning_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Heartbeat Workshop",
        business_stable_id="heartbeat-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="heartbeat-workshop",
            encryption_key=b"h" * 32,
        ),
        actor_id="heartbeat-boundary-test",
    )
    return layout, AionLearningVaultStore(
        domain_store=domains,
        workspace_id="heartbeat-workshop",
    )


def test_default_heartbeat_is_inert_and_memory_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    heartbeat = ResonanceHeartbeat(namespace="memory-only")

    assert heartbeat.auto_tick is False
    assert heartbeat._running is False
    heartbeat.push_sample(rho=0.8, entropy=0.2, sqi=0.9, delta=0.1)
    pulse = heartbeat.tick()

    assert pulse["storage_boundary"] == "memory"
    assert pulse["Φ_coherence"] == 0.8
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / ".runtime").exists()


def test_guardian_heartbeat_encrypts_state_and_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    layout, learning = _learning_store(tmp_path)
    heartbeat = ResonanceHeartbeat(
        namespace="private/customer namespace",
        vault_store=learning,
        auto_tick=False,
    )
    heartbeat.push_sample(rho=0.7, entropy=0.1, source="PRIVATE-SOURCE")
    pulse = heartbeat.tick()
    heartbeat.event("private_event", customer_text="PRIVATE-CUSTOMER-TEXT")

    assert learning.get_state(heartbeat._state_entity_id, {}) == pulse
    events = learning.list_events(kind="resonance_runtime_event")
    assert events[-1]["customer_text"] == "PRIVATE-CUSTOMER-TEXT"
    assert not (tmp_path / "data").exists()
    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-TEXT" not in encrypted
    assert b"private/customer namespace" not in encrypted


def test_heartbeat_throttles_snapshots_and_protects_event_metadata(tmp_path):
    _, learning = _learning_store(tmp_path)
    heartbeat = ResonanceHeartbeat(
        namespace="protected-metadata",
        vault_store=learning,
        auto_tick=False,
        persist_interval_seconds=60.0,
    )
    first = heartbeat.tick()
    heartbeat.push_sample(rho=0.9)
    heartbeat.tick()
    stored = learning.get_state(heartbeat._state_entity_id, {})
    assert stored["timestamp"] == first["timestamp"]

    heartbeat.event(
        "authoritative-name",
        namespace="attacker-namespace",
        event="attacker-event",
        timestamp=-1,
        event_type="attacker-type",
    )
    event = learning.list_events(kind="resonance_runtime_event")[-1]
    assert event["namespace"] == "protected-metadata"
    assert event["event"] == "authoritative-name"
    assert event["timestamp"] > 0
    assert event["event_type"] == "resonance_runtime_event"


def test_sync_all_uses_live_memory_not_heartbeat_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = ResonanceHeartbeat(namespace="sync-first", auto_tick=False)
    second = ResonanceHeartbeat(namespace="sync-second", auto_tick=False)
    first._last_pulse["Θ_frequency"] = 0.8
    second._last_pulse["Θ_frequency"] = 1.2

    harmony = first.sync_all(emit_pulse=False)

    assert harmony is not None
    assert first.snapshot()["Θ_frequency"] == 1.0
    assert second.snapshot()["Θ_frequency"] == 1.0
    assert not (tmp_path / "data").exists()
