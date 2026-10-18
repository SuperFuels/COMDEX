from __future__ import annotations

import base64

import pytest

from backend.modules.aion_analysis.pal_snapshot import (
    PalSnapshotStore,
    create_snapshot,
)
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.vault_store import AionLearningVaultStore


def _store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Private Workshop",
        business_stable_id="private-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="private-workshop",
            encryption_key=b"p" * 32,
        ),
        actor_id="pal-snapshot-test",
    )
    learning = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    return layout, PalSnapshotStore(vault_store=learning)


def test_pal_snapshot_is_encrypted_and_survives_restart(tmp_path):
    layout, store = _store(tmp_path)
    snapshot = create_snapshot(
        exemplars=[
            {
                "prompt": "PRIVATE-CUSTOMER-PROMPT",
                "option": "PRIVATE-CUSTOMER-OPTION",
                "reward": 0.75,
            }
        ],
        knowledge_links=[
            {
                "subject": "PRIVATE-CUSTOMER-SUBJECT",
                "predicate": "prefers",
                "object": "PRIVATE-CUSTOMER-OBJECT",
                "strength": 0.9,
            }
        ],
        store=store,
    )
    assert snapshot["pal_summary"]["count"] == 1
    restarted = PalSnapshotStore(vault_store=store.vault_store)
    assert restarted.list()[0]["top_kg_links"][0]["subject"] == (
        "PRIVATE-CUSTOMER-SUBJECT"
    )
    assert not (tmp_path / "data" / "analysis" / "pal_snapshots.jsonl").exists()
    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-PROMPT" not in encrypted
    assert b"PRIVATE-CUSTOMER-SUBJECT" not in encrypted


def test_guardian_default_refuses_undeclared_legacy_inputs(tmp_path, monkeypatch):
    env = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "external-vault"),
        "TESSARIS_BUSINESS_NAME": "Environment Workshop",
        "TESSARIS_BUSINESS_STABLE_ID": "environment-workshop",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"q" * 32
        ).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="pal_snapshot_guardian_exemplars_required"):
        create_snapshot()
    assert not (tmp_path / "data").exists()


def test_explicit_legacy_snapshot_log_remains_available_for_migration(tmp_path):
    path = tmp_path / "legacy" / "pal_snapshots.jsonl"
    store = PalSnapshotStore(legacy_log_path=path, auto_configure=False)
    snapshot = create_snapshot(exemplars=[], knowledge_links=[], store=store)
    assert path.exists()
    assert store.list()[0]["event_id"] == snapshot["event_id"]

