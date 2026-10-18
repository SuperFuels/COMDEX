from __future__ import annotations

import importlib

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.vault_store import AionLearningVaultStore


def _learning_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Private Resonance Workshop",
        business_stable_id="private-resonance-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="private-resonance-workshop",
            encryption_key=b"q" * 32,
        ),
        actor_id="resonant-bridge-test",
    )
    return layout, AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-resonance-workshop",
    )


def test_resonant_bridge_state_round_trips_only_through_guardian(tmp_path):
    module = importlib.import_module("backend.integrations.resonant_integration_bridge")
    layout, learning = _learning_store(tmp_path)
    handed_off = []

    state = module.fuse_resonant_state(
        vault_store=learning,
        harmonic_memory={
            "avg_reflective_stability": 0.8,
            "avg_reflective_drift": 0.125,
            "avg_governance_risk": 0.25,
            "harmony_integral": 0.7,
            "private_customer_marker": "PRIVATE-RESONANCE-MARKER",
        },
        resonance_audit={"status": "PRIVATE-AUDIT-MARKER"},
        theta_frequency=2.5,
        runtime_handoff=handed_off.append,
        now=lambda: 1_234.5,
    )

    assert state == {
        "schema": module.STATE_SCHEMA,
        "timestamp": 1_234.5,
        "coherence_boost": pytest.approx(0.6),
        "entropy_bias": pytest.approx(0.3),
        "harmony_integral": 0.7,
        "theta_frequency": 2.5,
        "reflective_drift": 0.125,
        "audit_present": True,
    }
    assert handed_off == [state]
    assert learning.get_state(module.STATE_ENTITY_ID, {}) == state
    assert not (tmp_path / "data").exists()

    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"resonant-integration-state" not in encrypted
    assert b"PRIVATE-RESONANCE-MARKER" not in encrypted
    assert b"PRIVATE-AUDIT-MARKER" not in encrypted


def test_resonant_bridge_reads_registered_guardian_inputs(tmp_path):
    module = importlib.import_module("backend.integrations.resonant_integration_bridge")
    _, learning = _learning_store(tmp_path)
    learning.put_state(
        module.HARMONIC_MEMORY_ENTITY_ID,
        {
            "avg_reflective_stability": 0.9,
            "avg_governance_risk": 0.1,
            "harmony_integral": 0.75,
        },
    )
    learning.put_state(module.RESONANCE_AUDIT_ENTITY_ID, {"healthy": True})

    state = module.fuse_resonant_state(
        vault_store=learning,
        now=lambda: 5.0,
    )

    assert state["coherence_boost"] == pytest.approx(0.81)
    assert state["entropy_bias"] == pytest.approx(0.25)
    assert state["audit_present"] is True


def test_resonant_bridge_fails_closed_without_guardian(tmp_path, monkeypatch):
    module = importlib.import_module("backend.integrations.resonant_integration_bridge")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        RuntimeError,
        match="resonant_bridge_guardian_store_not_configured",
    ):
        module.fuse_resonant_state(
            vault_store=AionLearningVaultStore(auto_configure=False),
        )

    assert not (tmp_path / "data").exists()
