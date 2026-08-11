from pathlib import Path

from backend.modules.aion_business.runtime.marketing_connection_service import (
    MarketingConnectionService, MarketingTokenStore,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _isolate(monkeypatch, tmp_path):
    root = tmp_path / "business"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")
    monkeypatch.setattr(AIONBusinessPaths, "CONTAINER_BINDINGS", root / "bindings")
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "containers")
    monkeypatch.setattr(AIONBusinessPaths, "ROLES", root / "roles")
    monkeypatch.setattr(AIONBusinessPaths, "AGENTS", root / "agents")
    monkeypatch.setattr(AIONBusinessPaths, "TASKS", root / "tasks")
    monkeypatch.setattr(AIONBusinessPaths, "LEARNING", root / "learning")
    monkeypatch.setattr(AIONBusinessPaths, "AUDIT", root / "audit")
    monkeypatch.setattr(AIONBusinessPaths, "FOUNDER_REVIEW", root / "founder")
    monkeypatch.setattr(AIONBusinessPaths, "EXTERNAL_SPECIALISTS", root / "specialists")
    monkeypatch.setattr(AIONBusinessPaths, "EXTERNAL_WORK_ORDERS", root / "orders")
    monkeypatch.setattr(AIONBusinessPaths, "TOPOLOGIES", root / "topologies")
    monkeypatch.setattr(AIONBusinessPaths, "DEPARTMENT_PILOT_RUNTIME", root / "pilots")
    monkeypatch.setenv("AION_MARKETING_TOKEN_STORE_DIR", str(tmp_path / "secrets"))


def test_connection_begin_is_pkce_and_missing_platform_config_is_honest(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService(base_url="http://127.0.0.1:8080")
    missing = service.begin("demo", "meta", tier="analytics", acting_person_id="desktop_user")
    assert missing["status"] == "platform_configuration_required"
    monkeypatch.setenv("META_APP_ID", "public-app-id")
    monkeypatch.setenv("META_APP_SECRET", "private-app-secret")
    result = service.begin("demo", "meta", tier="organic", acting_person_id="owner")
    assert result["status"] == "authorization_required"
    assert "code_challenge=" in result["authorization_url"]
    pending = service._pending("demo", "meta").read_text()
    assert "private-app-secret" not in pending


def test_tokens_are_not_exposed_and_account_selection_is_bounded(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    secret_ref = MarketingTokenStore.save("demo", "meta", {"access_token": "never-public"})
    record = {"status": "connected", "provider": "meta", "permission_tier": "organic",
              "granted_scopes": ["pages_manage_posts"], "accounts": [{"id": "page-1", "name": "Demo", "kind": "page"}],
              "selected_accounts": {}, "secret_ref": secret_ref}
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    _write(service._path("demo", "meta"), record)
    public = service.status("demo", "meta")
    assert "never-public" not in str(public)
    selected = service.select_accounts("demo", "meta", {"primary": "page-1"}, acting_person_id="owner")
    assert selected["selected_accounts"] == {"primary": "page-1"}
    disconnected = service.disconnect("demo", "meta", acting_person_id="owner")
    assert disconnected["connected"] is False
    assert MarketingTokenStore.load("demo", "meta") == {}


def test_marketing_ui_has_customer_owned_connection_controls():
    text = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert "MARKETING CONNECTIONS CENTRE" in text
    assert "Run read-only exam" in text
    assert "Connecting an account never authorises a post or spend" in text
    assert "renderAionMarketingConnectionsCentre()" in text
