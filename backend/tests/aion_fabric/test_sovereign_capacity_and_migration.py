from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignBrainSetup
from backend.modules.aion_business.runtime.sovereign_capacity_planner import SovereignCapacityPlanner
from backend.modules.aion_business.runtime.sovereign_migration_orchestrator import SovereignMigrationOrchestrator


def recommend(**changes):
    values = dict(tenant_id="tenant.acme", observation_days=30, peak_concurrency=1,
                  verified_actions_per_day=20, model_tokens_per_day=100000,
                  visual_frames_per_day=0, private_data_gb=10, p95_latency_ms=800,
                  availability_target=.99, offline_required=False, regulated_data=False,
                  multi_location=False, evidence_ref="observations.1")
    values.update(changes)
    return SovereignCapacityPlanner.recommend(**values)


def test_capacity_recommendation_starts_with_measured_requirements_not_business_size():
    small = recommend()
    complex_business = recommend(peak_concurrency=30, model_tokens_per_day=30_000_000,
                                 availability_target=.9999, regulated_data=True, multi_location=True)
    assert small["recommendation"] == "level_1_existing_machine"
    assert complex_business["recommendation"] == "level_4_private_cluster"
    assert complex_business["vendor_selected"] is False
    assert complex_business["financial_claim"] is None


def test_short_observation_is_provisional_and_offline_requirement_stays_customer_site():
    result = recommend(observation_days=7, peak_concurrency=8, offline_required=True)
    assert result["confidence"] == "provisional"
    assert result["deployment"] == "customer_site"
    assert result["customer_content_included"] is False


def test_migration_preserves_logical_brain_and_keeps_source_recoverable(tmp_path):
    source = SovereignBrainSetup(tmp_path / "source")
    original = source.initialize(owner_display_name="Owner", deployment_profile="personal_computer")
    source.vault.set_secret("provider.customer", "private-value")
    orchestrator = SovereignMigrationOrchestrator(source.root, tmp_path / "journal")
    prepared = orchestrator.prepare(migration_id="move.1", target_kind="customer_rack",
                                    destination=tmp_path / "target", passphrase="long private migration phrase",
                                    actor_id="owner.1", approval_ref="approval.1")
    assert prepared["brain_id"] == original["brain_id"]
    assert prepared["source_remains_active"] is True
    assert source.status()["ok"] is True
    assert SovereignBrainSetup(tmp_path / "target").vault.get_secret("provider.customer") == "private-value"
    active = orchestrator.activate(migration_id="move.1", destination=tmp_path / "target",
                                   actor_id="owner.1", activation_ref="activate.1")
    assert active["state"] == "target_active_source_retained"


def test_migration_rolls_back_without_deleting_either_brain(tmp_path):
    source = SovereignBrainSetup(tmp_path / "source")
    source.initialize(owner_display_name="Owner")
    orchestrator = SovereignMigrationOrchestrator(source.root, tmp_path / "journal")
    orchestrator.prepare(migration_id="move.1", target_kind="aion_box", destination=tmp_path / "target",
                         passphrase="long private migration phrase", actor_id="owner.1", approval_ref="approval.1")
    rolled = orchestrator.rollback(migration_id="move.1", actor_id="owner.1", reason="target qualification incomplete")
    assert rolled["state"] == "rolled_back_to_source"
    assert source.status()["ok"] is True
    assert SovereignBrainSetup(tmp_path / "target").status()["ok"] is True
    assert "target qualification incomplete" not in json.dumps(rolled)


def test_nonempty_destination_fails_before_source_is_changed(tmp_path):
    source = SovereignBrainSetup(tmp_path / "source")
    source.initialize(owner_display_name="Owner")
    destination = tmp_path / "target"
    destination.mkdir(); (destination / "existing").write_text("keep")
    orchestrator = SovereignMigrationOrchestrator(source.root, tmp_path / "journal")
    with pytest.raises(ValueError, match="destination_must_be_empty"):
        orchestrator.prepare(migration_id="move.1", target_kind="aion_box", destination=destination,
                             passphrase="long private migration phrase", actor_id="owner.1", approval_ref="approval.1")
    assert (destination / "existing").read_text() == "keep"
    assert source.status()["ok"] is True
