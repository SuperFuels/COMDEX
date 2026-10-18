from __future__ import annotations

import base64

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_generalization.concept_decay_manager import (
    decay_stale_links,
    export_snapshot,
    parse_reinforcement_log,
)
from backend.modules.aion_knowledge.knowledge_graph_core import AionKnowledgeGraphStore
from backend.modules.aion_learning.vault_store import AionLearningVaultStore


def _stores(tmp_path):
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
            encryption_key=b"d" * 32,
        ),
        actor_id="concept-decay-test",
    )
    return (
        layout,
        AionKnowledgeGraphStore(
            domain_store=domains,
            workspace_id="private-workshop",
        ),
        AionLearningVaultStore(
            domain_store=domains,
            workspace_id="private-workshop",
        ),
    )


def test_concept_decay_and_snapshot_remain_in_guardian(tmp_path):
    layout, graph, learning = _stores(tmp_path)
    graph.put("symbol:PRIVATE-A", "is_a", "concept:PRIVATE-KEEP", strength=1.0)
    graph.put("symbol:PRIVATE-B", "is_a", "concept:PRIVATE-DELETE", strength=0.2)

    updated, deleted = decay_stale_links({}, store=graph, now=100_000.0)
    assert (updated, deleted) == (1, 1)
    assert graph.get("symbol:PRIVATE-A", "is_a", "concept:PRIVATE-KEEP")[
        "strength"
    ] == pytest.approx(0.97)
    assert graph.get("symbol:PRIVATE-B", "is_a", "concept:PRIVATE-DELETE") is None

    snapshot = export_snapshot(store=graph, learning_store=learning)
    assert snapshot["concepts"] == {"PRIVATE-KEEP": 1}
    assert learning.list_events(kind="concept_evolution_snapshot")[0][
        "concepts"
    ] == {"PRIVATE-KEEP": 1}
    assert not (tmp_path / "data").exists()
    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-KEEP" not in encrypted
    assert b"PRIVATE-DELETE" not in encrypted


def test_guardian_mode_rejects_implicit_reinforcement_log(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "guardian")
    monkeypatch.setenv("TESSARIS_BUSINESS_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("TESSARIS_BUSINESS_NAME", "Environment Workshop")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "environment-workshop")
    monkeypatch.setenv(
        "TESSARIS_BUSINESS_VAULT_KEY_B64",
        base64.urlsafe_b64encode(b"r" * 32).decode().rstrip("="),
    )
    monkeypatch.setenv("TESSARIS_APPLICATION_ROOT", str(tmp_path / "application"))
    monkeypatch.setenv("TESSARIS_UPDATE_ROOT", str(tmp_path / "updates"))
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        RuntimeError,
        match="concept_decay_guardian_reinforcement_input_required",
    ):
        parse_reinforcement_log()
    assert not (tmp_path / "data").exists()


def test_explicit_legacy_decay_sources_remain_available(tmp_path):
    reinforcement = tmp_path / "legacy" / "concept_reinforcement.log"
    reinforcement.parent.mkdir(parents=True, exist_ok=True)
    reinforcement.write_text("50 reinforce legacy-concept\n", encoding="utf-8")
    snapshot = tmp_path / "legacy" / "concept_evolution_snapshot.jsonl"
    graph = AionKnowledgeGraphStore(
        legacy_db_path=tmp_path / "legacy" / "knowledge.db",
        auto_configure=False,
    )
    graph.put("symbol:L", "is_a", "concept:legacy-concept", strength=1.0)
    assert parse_reinforcement_log(reinforcement) == {"legacy-concept": 50.0}
    export_snapshot(
        store=graph,
        learning_store=AionLearningVaultStore(auto_configure=False),
        legacy_snapshot_path=snapshot,
    )
    assert snapshot.exists()

