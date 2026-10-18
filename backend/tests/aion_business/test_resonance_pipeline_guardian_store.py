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
        business_name="Private Governance Workshop",
        business_stable_id="private-governance-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="private-governance-workshop",
            encryption_key=b"g" * 32,
        ),
        actor_id="resonance-pipeline-test",
    )
    return layout, AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-governance-workshop",
    )


def test_governance_and_harmonic_pipeline_round_trip_in_guardian(tmp_path):
    governance = importlib.import_module("backend.tools.resonant_governance_loop")
    harmonic = importlib.import_module("backend.tools.harmonic_memory_fusion")
    layout, learning = _learning_store(tmp_path)
    policies = []
    memories = []

    policy = governance.run_governance(
        vault_store=learning,
        predictions=[
            {"predicted_risk": 0.2, "private": "PRIVATE-PREDICTION"},
            {"predicted_risk": 0.4},
        ],
        runtime_handoff=policies.append,
        ethics_evaluator=lambda _action: 0.95,
        now=lambda: 10.0,
    )
    memory = harmonic.fuse_memories(
        vault_store=learning,
        reflection={
            "avg_delta_stability": 0.8,
            "avg_delta_drift": 0.1,
            "private": "PRIVATE-REFLECTION",
        },
        governance=[policy],
        runtime_handoff=memories.append,
        now=lambda: 11.0,
    )

    assert policy["avg_risk"] == pytest.approx(0.3)
    assert policy["ethics_score"] == pytest.approx(0.95)
    assert policy["ethics_evaluation"] == "completed"
    assert policies == [policy]
    assert memory is not None
    assert memory["avg_reflective_stability"] == pytest.approx(0.8)
    assert memory["avg_governance_risk"] == pytest.approx(0.3)
    assert memories == [memory]
    assert learning.get_state(governance.POLICY_ENTITY_ID, {}) == policy
    assert learning.get_state(harmonic.HARMONIC_MEMORY_ENTITY_ID, {}) == memory
    assert not (tmp_path / "data").exists()

    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-PREDICTION" not in encrypted
    assert b"PRIVATE-REFLECTION" not in encrypted
    assert b"harmonic-memory" not in encrypted


def test_pipeline_can_continue_from_registered_guardian_inputs(tmp_path):
    governance = importlib.import_module("backend.tools.resonant_governance_loop")
    harmonic = importlib.import_module("backend.tools.harmonic_memory_fusion")
    _, learning = _learning_store(tmp_path)
    learning.put_state(
        governance.PREDICTIONS_ENTITY_ID,
        {"predictions": [{"predicted_risk": 0.5}]},
    )
    learning.put_state(
        harmonic.REFLECTION_ENTITY_ID,
        {"avg_delta_stability": 0.9, "avg_delta_drift": 0.2},
    )

    policy = governance.run_governance(vault_store=learning, now=lambda: 20.0)
    memory = harmonic.fuse_memories(vault_store=learning, now=lambda: 21.0)

    assert policy["max_risk"] == pytest.approx(0.5)
    assert policy["ethics_score"] is None
    assert policy["ethics_evaluation"] == "not_run"
    assert memory is not None
    assert memory["avg_gain_mod"] == policy["gain_mod"]


def test_pipeline_fails_closed_without_guardian(tmp_path, monkeypatch):
    governance = importlib.import_module("backend.tools.resonant_governance_loop")
    harmonic = importlib.import_module("backend.tools.harmonic_memory_fusion")
    disabled = AionLearningVaultStore(auto_configure=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="resonant_governance_guardian"):
        governance.run_governance(vault_store=disabled)
    with pytest.raises(RuntimeError, match="harmonic_memory_guardian"):
        harmonic.fuse_memories(vault_store=disabled)
    assert not (tmp_path / "data").exists()


def test_reflection_and_trajectory_producers_feed_guardian_pipeline(tmp_path):
    reflection = importlib.import_module("backend.tools.self_reflection_loop")
    trajectory = importlib.import_module("backend.tools.cognitive_trajectory_learning")
    _, learning = _learning_store(tmp_path)
    proposals = []

    summary = reflection.run_reflection(
        vault_store=learning,
        audit={"engines": [{"engine": "private-engine", "stability": 0.4, "delta_phi": 0.8}]},
        rewrite={"executed": [{"engine": "private-engine", "action": "private-adjustment"}]},
        now=lambda: 30.0,
    )
    result = trajectory.run_trajectory_learning(
        vault_store=learning,
        reflection=summary,
        risk_threshold=0.3,
        proposal_handler=proposals.append,
        now=lambda: 31.0,
    )

    assert summary is not None
    assert summary["avg_delta_stability"] == pytest.approx(0.15)
    assert result["predictions"][0]["engine"] == "private-engine"
    assert result["predictions"][0]["predicted_risk"] >= 0.3
    assert proposals[0]["action"] == "preemptive_tuning"
    assert learning.get_state(trajectory.PREDICTIONS_ENTITY_ID, {}) == result


def test_audit_and_rewrite_producers_are_guardian_backed(tmp_path):
    audit_module = importlib.import_module("backend.tools.audit_resonance_field")
    rewrite_module = importlib.import_module("backend.tools.dna_switch_rewrite")
    _, learning = _learning_store(tmp_path)
    actions = []
    proposals = []

    audit = audit_module.run_resonance_audit(
        vault_store=learning,
        heartbeats=[
            {
                "namespace": "private-engine",
                "Φ_coherence": 0.3,
                "Φ_entropy": 0.2,
                "sqi": 0.7,
                "resonance_delta": 0.2,
            }
        ],
        drift_rows=[{"private": "PRIVATE-DRIFT"}],
    )
    rewrite = rewrite_module.run_rewrite_planning(
        vault_store=learning,
        audit=audit,
        action_handler=actions.append,
        proposal_handler=proposals.append,
        now=lambda: 40.0,
    )

    assert audit is not None
    assert audit["summary"]["engines_audited"] == 1
    assert rewrite is not None
    assert {row["action"] for row in actions} == {
        "recalibrate_resonance",
        "synchronize_phase",
    }
    assert len(proposals) == 2
    assert learning.get_state(audit_module.AUDIT_ENTITY_ID, {}) == audit
    assert learning.get_state(rewrite_module.REWRITE_ENTITY_ID, {}) == rewrite
