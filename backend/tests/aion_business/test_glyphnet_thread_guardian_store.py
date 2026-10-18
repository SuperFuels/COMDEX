from __future__ import annotations

import base64

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.glyphnet.thread_logger import (
    GlyphThreadStore,
    log_thread_event,
    read_thread,
)


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
            encryption_key=b"g" * 32,
        ),
        actor_id="glyphnet-test",
    )
    return layout, GlyphThreadStore(
        domain_store=domains, workspace_id="private-workshop"
    )


def test_glyphnet_thread_content_uses_guardian_and_survives_restart(tmp_path):
    layout, store = _store(tmp_path)
    store.append(
        "private-customer-thread",
        {
            "graph": "work",
            "type": "text",
            "ts": 10.0,
            "from": "PRIVATE-SENDER",
            "to": "PRIVATE-RECIPIENT",
            "payload": {"text": "PRIVATE-CUSTOMER-MESSAGE"},
        },
        direction="in",
        user_id="private-user",
    )

    restarted = GlyphThreadStore(
        domain_store=store.domain_store, workspace_id="private-workshop"
    )
    rows = restarted.read("private-customer-thread", graph="work")
    assert len(rows) == 1
    assert rows[0]["payload"]["text"] == "PRIVATE-CUSTOMER-MESSAGE"
    assert rows[0]["from"] == "PRIVATE-SENDER"
    assert restarted.read("private-customer-thread", graph="work", limit=0) == []
    assert not (tmp_path / "data" / "threadlog.sqlite").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-MESSAGE" not in database_bytes
    assert b"PRIVATE-SENDER" not in database_bytes


def test_explicit_glyphnet_sqlite_path_remains_a_migration_source(tmp_path):
    database = tmp_path / "legacy" / "threadlog.sqlite"
    legacy = GlyphThreadStore(legacy_db_path=database)
    legacy.append(
        "legacy-topic",
        {
            "graph": "personal",
            "type": "voice",
            "ts": 20.0,
            "from": "legacy-sender",
            "payload": {"mime": "audio/webm", "bytes_b64": "PRIVATE-AUDIO"},
        },
        user_id="legacy-user",
    )
    assert database.exists()
    rows = GlyphThreadStore(legacy_db_path=database).read("legacy-topic")
    assert rows[0]["type"] == "voice"
    assert rows[0]["payload"]["bytes_b64"] == "PRIVATE-AUDIO"


def test_glyphnet_module_api_obeys_guardian_environment(tmp_path, monkeypatch):
    env = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "external-vault"),
        "TESSARIS_BUSINESS_NAME": "Environment Workshop",
        "TESSARIS_BUSINESS_STABLE_ID": "environment-workshop",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"h" * 32
        ).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)

    log_thread_event(
        "environment-thread",
        {
            "graph": "work",
            "type": "text",
            "ts": 30.0,
            "payload": {"text": "environment private message"},
        },
    )
    assert read_thread("environment-thread", "work")[0]["payload"]["text"] == (
        "environment private message"
    )
    assert not (tmp_path / "data" / "threadlog.sqlite").exists()
