from __future__ import annotations

import base64

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_knowledge import knowledge_graph_core as graph


def _domain_store(tmp_path):
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
            encryption_key=b"k" * 32,
        ),
        actor_id="knowledge-graph-test",
    )
    return layout, domains


def test_aion_knowledge_graph_uses_encrypted_workspace_records(tmp_path):
    layout, domains = _domain_store(tmp_path)
    store = graph.AionKnowledgeGraphStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    store.put(
        "PRIVATE-CUSTOMER-PROMPT",
        "elicited_choice",
        "PRIVATE-CUSTOMER-GLYPH",
        vec=[0.1, 0.2],
        strength=0.8,
    )
    restarted = graph.AionKnowledgeGraphStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    rows = restarted.search(subject="PRIVATE-CUSTOMER-PROMPT")
    assert rows[0]["object"] == "PRIVATE-CUSTOMER-GLYPH"
    assert rows[0]["vec"] == [0.1, 0.2]
    assert not (tmp_path / "data" / "knowledge" / "aion_knowledge_graph.db").exists()
    encrypted = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-PROMPT" not in encrypted
    assert b"PRIVATE-CUSTOMER-GLYPH" not in encrypted


def test_module_api_obeys_guardian_and_forbids_direct_sql(tmp_path, monkeypatch):
    env = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "external-vault"),
        "TESSARIS_BUSINESS_NAME": "Environment Workshop",
        "TESSARIS_BUSINESS_STABLE_ID": "environment-workshop",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"z" * 32
        ).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    graph.triplets.clear()

    graph.add_triplet(
        "symbol:PRIVATE-SYMBOL",
        "is_a",
        "concept:PRIVATE-CONCEPT",
        strength=1.0,
    )
    assert graph.export_concepts() == {"PRIVATE-CONCEPT": ["PRIVATE-SYMBOL"]}
    assert graph.related("concept:PRIVATE-CONCEPT")[0]["subject"] == (
        "symbol:PRIVATE-SYMBOL"
    )
    with pytest.raises(
        RuntimeError,
        match="aion_knowledge_direct_sql_forbidden_in_guardian_mode",
    ):
        graph._connect()
    assert not (tmp_path / "data").exists()


def test_explicit_sqlite_path_remains_available_for_copy_migration(tmp_path):
    path = tmp_path / "legacy" / "aion_knowledge_graph.db"
    store = graph.AionKnowledgeGraphStore(
        legacy_db_path=path,
        auto_configure=False,
    )
    store.put("legacy-subject", "legacy-predicate", "legacy-object", strength=0.5)
    assert path.exists()
    assert store.search(subject="legacy-subject")[0]["strength"] == 0.5

