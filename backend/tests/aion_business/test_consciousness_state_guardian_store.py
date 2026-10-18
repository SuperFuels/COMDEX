from __future__ import annotations

import json

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.vault_store import AionLearningVaultStore
from backend.modules.consciousness.state_guardian_store import (
    AGENT_STATES_ENTITY_ID,
    ConsciousnessStateStore,
    RESONANCE_EVENT_TYPE,
)


def _state_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Consciousness Workshop",
        business_stable_id="consciousness-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="consciousness-workshop",
            encryption_key=b"c" * 32,
        ),
        actor_id="consciousness-boundary-test",
    )
    learning = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="consciousness-workshop",
    )
    return layout, learning, ConsciousnessStateStore(vault_store=learning)


def test_agent_state_survives_restart_inside_guardian(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    layout, learning, store = _state_store(tmp_path)
    private_state = {
        "private-agent": {
            "location": "PRIVATE-CUSTOMER-SITE",
            "teleport_history": ["PRIVATE-CUSTOMER-HISTORY"],
        }
    }

    assert store.save_agent_states(private_state) is True
    restarted = ConsciousnessStateStore(vault_store=learning)

    assert restarted.load_agent_states() == private_state
    assert learning.get_state(AGENT_STATES_ENTITY_ID, {}) == private_state
    assert not (tmp_path / "agent_state.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-SITE" not in database_bytes
    assert b"PRIVATE-CUSTOMER-HISTORY" not in database_bytes


def test_resonance_evidence_is_immutable_guardian_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    layout, learning, store = _state_store(tmp_path)

    assert store.append_resonance_sample(
        {
            "event_id": "caller-cannot-override",
            "event_type": "caller-cannot-override",
            "Φ_coherence": 0.8,
            "private_marker": "PRIVATE-RESONANCE-EVIDENCE",
        }
    ) is True

    events = learning.list_events(kind=RESONANCE_EVENT_TYPE)
    assert len(events) == 1
    assert events[0]["event_id"] != "caller-cannot-override"
    assert events[0]["event_type"] == RESONANCE_EVENT_TYPE
    assert events[0]["private_marker"] == "PRIVATE-RESONANCE-EVIDENCE"
    assert not (tmp_path / "data").exists()
    assert b"PRIVATE-RESONANCE-EVIDENCE" not in (
        layout.records / "guardian.sqlite3"
    ).read_bytes()


def test_unconfigured_store_is_memory_only_and_does_not_create_files(
    tmp_path, monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    store = ConsciousnessStateStore(
        vault_store=AionLearningVaultStore(auto_configure=False),
    )

    assert store.storage_boundary == "memory"
    assert store.load_agent_states() == {}
    assert store.save_agent_states({"agent": {"location": "private"}}) is False
    assert store.append_resonance_sample({"Φ_coherence": 0.5}) is False
    assert not (tmp_path / "agent_state.json").exists()
    assert not (tmp_path / "data").exists()


def test_legacy_files_require_explicit_compatibility_switch(tmp_path):
    state_path = tmp_path / "legacy" / "agent_state.json"
    log_path = tmp_path / "legacy" / "state_resonance_log.jsonl"
    store = ConsciousnessStateStore(
        vault_store=AionLearningVaultStore(auto_configure=False),
        allow_legacy_files=True,
        legacy_agent_state_path=state_path,
        legacy_resonance_log_path=log_path,
    )

    assert store.storage_boundary == "legacy-development-file"
    assert store.save_agent_states({"agent": {"location": "test-only"}}) is True
    assert store.load_agent_states()["agent"]["location"] == "test-only"
    assert store.append_resonance_sample({"Φ_coherence": 0.5}) is True
    row = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert row["event_type"] == RESONANCE_EVENT_TYPE


def test_customer_container_overlay_is_separate_from_application_file(
    tmp_path, monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    layout, learning, store = _state_store(tmp_path)
    application_container = tmp_path / "application" / "base.dc.json"
    application_container.parent.mkdir(parents=True)
    application_container.write_text(
        json.dumps({"id": "PRIVATE-CONTAINER-ID", "cubes": {}}),
        encoding="utf-8",
    )
    base = {"id": "PRIVATE-CONTAINER-ID", "cubes": {}}
    changed = {
        "id": "PRIVATE-CONTAINER-ID",
        "cubes": {"1,0,0,0": {"glyph": "PRIVATE-CUSTOMER-GLYPH"}},
    }

    assert store.save_container_state(changed, legacy_path=application_container) is True
    assert store.load_container_state(base) == changed
    assert json.loads(application_container.read_text(encoding="utf-8")) == base
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CONTAINER-ID" not in database_bytes
    assert b"PRIVATE-CUSTOMER-GLYPH" not in database_bytes


def test_container_mutation_fails_closed_without_guardian(tmp_path):
    application_container = tmp_path / "application" / "base.dc.json"
    application_container.parent.mkdir(parents=True)
    base = {"id": "base", "cubes": {}}
    application_container.write_text(json.dumps(base), encoding="utf-8")
    store = ConsciousnessStateStore(
        vault_store=AionLearningVaultStore(auto_configure=False),
    )

    assert store.save_container_state(
        {"id": "base", "cubes": {"1,0,0,0": {"glyph": "private"}}},
        legacy_path=application_container,
    ) is False
    assert json.loads(application_container.read_text(encoding="utf-8")) == base
