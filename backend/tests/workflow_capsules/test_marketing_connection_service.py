from pathlib import Path
from hashlib import sha256
import json
from urllib.parse import parse_qs, urlparse

import pytest

from backend.modules.aion_business.runtime.marketing_connection_service import (
    MarketingConnectionService, MarketingPlatformCredentialStore, MarketingTokenStore, PROVIDERS, _write,
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
    monkeypatch.setattr(MarketingPlatformCredentialStore, "load", lambda provider: {
        "client_id": "", "client_secret": "",
    })
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


def test_tiktok_desktop_pkce_uses_required_hex_digest(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(MarketingPlatformCredentialStore, "load", lambda provider: {
        "client_id": "tiktok-client", "client_secret": "tiktok-secret",
    })
    service = MarketingConnectionService(base_url="http://localhost:8080")

    result = service.begin("demo", "tiktok", tier="analytics", acting_person_id="owner")

    query = parse_qs(urlparse(result["authorization_url"]).query)
    pending = json.loads(service._pending("demo", "tiktok").read_text())
    assert result["expires_in_seconds"] == 3600
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [sha256(pending["verifier"].encode()).hexdigest()]


def test_provider_token_error_diagnostic_never_includes_unrelated_response_fields():
    error = {"error": "invalid_grant", "error_description": "Verifier mismatch", "access_token_hint": "secret"}
    parts = [error.get("error"), error.get("error_description"), error.get("message"), error.get("log_id")]
    detail = " | ".join(str(part) for part in parts if part)
    assert detail == "invalid_grant | Verifier mismatch"
    assert "secret" not in detail


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
    assert "Test connection" in text
    assert "publishing and advertising spend separately approval-gated" in text
    assert "renderAionMarketingConnectionsCentre()" in text


def test_priority_social_connection_catalog_is_ordered_for_marketing(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert list(PROVIDERS) == [
        "meta", "linkedin", "youtube", "tiktok", "x", "pinterest",
        "google_business", "google_ads", "microsoft_ads",
    ]
    assert "tweet.write" in PROVIDERS["x"]["scopes"]["organic"]
    assert "pins:write" in PROVIDERS["pinterest"]["scopes"]["organic"]
    assert PROVIDERS["google_business"]["scopes"]["analytics"] == [
        "https://www.googleapis.com/auth/business.manage"
    ]
    assert "https://ads.microsoft.com/msads.manage" in PROVIDERS["microsoft_ads"]["scopes"]["analytics"]


def test_paid_media_platform_requirements_are_reported_before_oauth(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(MarketingPlatformCredentialStore, "load", lambda provider: {})
    monkeypatch.setenv("MICROSOFT_ADS_CLIENT_ID", "microsoft-client")
    monkeypatch.setenv("MICROSOFT_ADS_CLIENT_SECRET", "microsoft-secret")
    result = MarketingConnectionService().begin(
        "demo", "microsoft_ads", tier="advertising", acting_person_id="owner"
    )
    assert result == {
        "status": "platform_configuration_required",
        "provider": "microsoft_ads",
        "missing": ["MICROSOFT_ADS_DEVELOPER_TOKEN"],
    }


def test_microsoft_ads_developer_token_can_be_loaded_from_keychain(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    stored = {}
    monkeypatch.delenv("MICROSOFT_ADS_DEVELOPER_TOKEN", raising=False)
    monkeypatch.setattr("keyring.set_password", lambda service, account, value: stored.update({(service, account): value}))
    monkeypatch.setattr("keyring.get_password", lambda service, account: stored.get((service, account)))
    MarketingPlatformCredentialStore.save(
        "microsoft_ads", client_id="microsoft-client", client_secret="microsoft-secret",
    )
    MarketingPlatformCredentialStore.save_platform_token(
        "microsoft_ads", name="developer_token", value="developer-token",
    )

    service = MarketingConnectionService(base_url="http://127.0.0.1:8080")
    status = service.status("demo", "microsoft_ads")
    result = service.begin("demo", "microsoft_ads", tier="advertising", acting_person_id="owner")

    assert status["configured"] is True
    assert status["platform_requirements"] == []
    assert result["status"] == "authorization_required"
    assert "developer-token" not in json.dumps(status)
    assert "developer-token" not in result["authorization_url"]


@pytest.mark.asyncio
async def test_microsoft_ads_discovers_read_only_ad_accounts(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    monkeypatch.setattr(
        service, "_platform_token", lambda provider, name: "developer-token",
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "AccountsInfo": [{
                    "Id": 188482566,
                    "Name": "Tessaris AI Limited",
                    "Number": "G120QYMC",
                    "AccountLifeCycleStatus": "Active",
                }]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.headers = kwargs.get("headers") or {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, headers, json):
            assert url.endswith("/CustomerManagement/v13/AccountsInfo/Query")
            assert headers["Authorization"] == "Bearer access-token"
            assert headers["DeveloperToken"] == "developer-token"
            assert json == {"OnlyParentAccounts": False}
            return FakeResponse()

    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.marketing_connection_service.httpx.AsyncClient",
        FakeClient,
    )

    accounts = await service._discover("microsoft_ads", "access-token")

    assert accounts == [{
        "id": "188482566",
        "name": "Tessaris AI Limited",
        "kind": "ad_account",
        "account_number": "G120QYMC",
        "account_status": "Active",
    }]


def test_microsoft_ads_refresh_token_proves_offline_access(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    monkeypatch.setenv("MICROSOFT_ADS_CLIENT_ID", "microsoft-client")
    monkeypatch.setenv("MICROSOFT_ADS_CLIENT_SECRET", "microsoft-secret")
    monkeypatch.setenv("MICROSOFT_ADS_DEVELOPER_TOKEN", "developer-token")
    secret_ref = MarketingTokenStore.save(
        "demo", "microsoft_ads", {"access_token": "secret", "refresh_token": "refresh-secret"},
    )
    _write(service._path("demo", "microsoft_ads"), {
        "status": "connected",
        "permission_tier": "advertising",
        "granted_scopes": ["https://ads.microsoft.com/msads.manage"],
        "accounts": [{"id": "188482566", "name": "Tessaris AI Limited", "kind": "ad_account"}],
        "selected_accounts": {"ad_account": "188482566"},
        "health": "healthy",
        "secret_ref": secret_ref,
    })

    status = service.status("demo", "microsoft_ads")

    assert status["granted_scopes"] == [
        "https://ads.microsoft.com/msads.manage", "offline_access",
    ]
    assert status["advertising"]["state"] == "ready"
    assert "refresh-secret" not in json.dumps(status)


def test_google_ads_uses_cloud_project_access_without_legacy_developer_token(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("GOOGLE_MARKETING_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_MARKETING_CLIENT_SECRET", "google-secret")
    monkeypatch.delenv("GOOGLE_ADS_DEVELOPER_TOKEN", raising=False)
    status = MarketingConnectionService().status("demo", "google_ads")
    assert status["configured"] is True
    assert status["platform_requirements"] == []
    assert status["advertising"]["state"] == "authorization_required"
    assert status["advertising"]["can_authorize"] is True


def test_social_connection_does_not_masquerade_as_advertising_connection(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("META_APP_ID", "meta-client")
    monkeypatch.setenv("META_APP_SECRET", "meta-secret")
    service = MarketingConnectionService()
    _write(service._path("demo", "meta"), {
        "status": "connected",
        "permission_tier": "analytics",
        "granted_scopes": PROVIDERS["meta"]["scopes"]["analytics"],
        "selected_accounts": {"page": "page-1", "instagram": "ig-1"},
        "accounts": [],
        "health": "healthy",
    })
    advertising = service.status("demo", "meta")["advertising"]
    assert advertising["ready"] is False
    assert advertising["state"] == "authorization_required"
    assert advertising["missing_scopes"] == ["ads_read"]
    assert advertising["account_selected"] is False


def test_profile_oauth_is_not_reported_as_tiktok_or_x_ads_ready(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    for provider in ("tiktok", "x"):
        status = MarketingConnectionService().status("demo", provider)
        assert status["advertising"]["state"] == "separate_ads_api_required"
        assert status["advertising"]["can_authorize"] is False


def test_read_only_and_write_permissions_are_not_mixed():
    assert MarketingConnectionService._scopes("meta", "analytics") == [
        "pages_show_list", "pages_read_engagement", "read_insights", "instagram_basic",
        "instagram_manage_insights", "business_management",
    ]
    assert "pages_manage_posts" in MarketingConnectionService._scopes("meta", "organic")
    assert "pages_manage_posts" not in MarketingConnectionService._scopes("meta", "advertising")
    assert MarketingConnectionService._scopes("meta", "advertising")[-1] == "ads_read"
    assert "ads_management" not in MarketingConnectionService._scopes("meta", "advertising")
    assert MarketingConnectionService._scopes("linkedin", "analytics") == [
        "r_organization_admin", "r_organization_social",
    ]
    assert MarketingConnectionService._scopes("linkedin", "organic")[-1] == "w_organization_social"
    assert MarketingConnectionService._scopes("linkedin", "advertising")[-2:] == ["r_ads", "r_ads_reporting"]
    assert MarketingConnectionService._scopes("tiktok", "analytics") == [
        "user.info.basic", "user.info.profile", "user.info.stats", "video.list",
    ]
    assert MarketingConnectionService._scopes("tiktok", "organic")[-1] == "video.upload"
    assert "video.publish" not in MarketingConnectionService._scopes("tiktok", "organic")


def test_linkedin_connection_ui_launches_company_oauth_and_keeps_secret_local():
    text = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert 'data-aion-platform-credentials="linkedin"' in text
    assert "Customers will then click LinkedIn, sign in on LinkedIn, approve Tessaris" in text
    assert "http://127.0.0.1:8080/api/aion/marketing/connections/linkedin/callback" in text
    assert 'data-aion-save-platform-credentials="linkedin"' in text
    assert "LINKEDIN COMPANY PAGE" in text
    assert 'data-aion-sync-marketing-metrics="linkedin"' in text


def test_tiktok_connection_ui_launches_customer_oauth_and_keeps_secret_local():
    text = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert 'data-aion-platform-credentials="tiktok"' in text
    assert "Customers can then click TikTok, approve read-only profile and video access" in text
    assert "http://127.0.0.1:8080/api/aion/marketing/connections/tiktok/callback" in text
    assert 'data-aion-save-platform-credentials="tiktok"' in text
    assert "TIKTOK ACCOUNT" in text
    assert 'data-aion-sync-marketing-metrics="tiktok"' in text


@pytest.mark.asyncio
async def test_tiktok_metric_sync_persists_creator_evidence(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "tiktok", {"access_token": "secret-token"})
    _write(service._path("demo", "tiktok"), {
        "status": "connected", "provider": "tiktok", "secret_ref": secret_ref,
        "accounts": [{"id": "creator-1", "name": "Tessaris", "kind": "creator"}],
        "selected_accounts": {},
    })
    expected = {
        "schema_version": "aion.marketing.channel_metrics.v1", "provider": "tiktok",
        "collected_at": "2026-10-11T08:00:00+00:00", "summary": {"tiktok_videos_published": 0},
        "channels": [], "read_only": True, "external_writes_enabled": False,
    }

    async def fake_sync(**kwargs):
        assert kwargs["creator_id"] == "creator-1"
        assert kwargs["token"]["access_token"] == "secret-token"
        return expected

    monkeypatch.setattr(service, "_sync_tiktok_metrics", fake_sync)
    result = await service.sync_metrics("demo", "tiktok", days=28, acting_person_id="owner")
    assert result == expected
    public = service.status("demo", "tiktok")
    assert public["selected_accounts"] == {"creator": "creator-1"}
    assert public["metrics_status"] == "ready"
    assert "secret-token" not in json.dumps(public)


@pytest.mark.asyncio
async def test_linkedin_metric_sync_persists_company_page_evidence(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "linkedin", {"access_token": "secret-token"})
    _write(service._path("demo", "linkedin"), {
        "status": "connected", "provider": "linkedin", "secret_ref": secret_ref,
        "accounts": [{"id": "123", "name": "Tessaris AI Ltd", "kind": "organization"}],
        "selected_accounts": {},
    })
    expected = {
        "schema_version": "aion.marketing.channel_metrics.v1", "provider": "linkedin",
        "collected_at": "2026-10-11T08:00:00+00:00", "summary": {"linkedin_posts": 0},
        "channels": [], "read_only": True, "external_writes_enabled": False,
    }

    async def fake_sync(**kwargs):
        assert kwargs["organization_id"] == "123"
        assert kwargs["token"]["access_token"] == "secret-token"
        return expected

    monkeypatch.setattr(service, "_sync_linkedin_metrics", fake_sync)
    result = await service.sync_metrics("demo", "linkedin", days=28, acting_person_id="owner")
    assert result == expected
    public = service.status("demo", "linkedin")
    assert public["selected_accounts"] == {"organization": "123"}
    assert public["metrics_status"] == "ready"
    assert "secret-token" not in json.dumps(public)


def test_linkedin_statistics_are_normalised_for_marketing_analysis():
    summary = MarketingConnectionService._summarise_linkedin_statistics([{
        "totalShareStatistics": {
            "impressionCount": 100, "uniqueImpressionsCount": 80, "clickCount": 7,
            "likeCount": 4, "commentCount": 2, "shareCount": 1,
        },
    }])
    assert summary["linkedin_impressions"] == 100
    assert summary["linkedin_engagement_rate"] == pytest.approx(0.14)


def test_google_social_connections_reuse_existing_google_oauth_credentials(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "google-secret")
    service = MarketingConnectionService(base_url="http://127.0.0.1:8080")
    result = service.begin("demo", "google_business", tier="analytics", acting_person_id="owner")
    assert result["status"] == "authorization_required"
    assert "business.manage" in result["authorization_url"]


def test_platform_app_secret_is_saved_to_keychain_but_never_returned(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    stored = {}
    monkeypatch.setattr("keyring.set_password", lambda service, account, value: stored.update({(service, account): value}))
    monkeypatch.setattr("keyring.get_password", lambda service, account: stored.get((service, account)))
    service = MarketingConnectionService(base_url="http://127.0.0.1:8080")
    status = service.configure_platform("meta", client_id="meta-app", client_secret="never-public")
    assert status["configured"] is True
    assert status["callback_url"].endswith("/api/aion/marketing/connections/meta/callback")
    assert "never-public" not in json.dumps(status)
    assert MarketingPlatformCredentialStore.load("meta")["client_secret"] == "never-public"


def test_microsoft_ads_uses_localhost_callback_required_by_entra(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService(base_url="http://127.0.0.1:8080")

    status = service.platform_status("microsoft_ads")

    assert status["callback_url"] == (
        "http://localhost:8080/api/aion/marketing/connections/microsoft_ads/callback"
    )


@pytest.mark.asyncio
async def test_meta_metric_sync_persists_normalised_read_only_evidence(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "meta", {"access_token": "secret-token", "page_tokens": {"page-1": "page-secret"}})
    _write(service._path("demo", "meta"), {
        "status": "connected", "provider": "meta", "secret_ref": secret_ref,
        "selected_accounts": {"page": "page-1", "instagram": "ig-1", "ad_account": "ad-1"},
    })
    expected = {
        "schema_version": "aion.marketing.channel_metrics.v1", "provider": "meta",
        "collected_at": "2026-10-10T18:00:00+00:00", "summary": {"organic_interactions": 12},
        "channels": [], "read_only": True, "external_writes_enabled": False,
    }

    async def fake_sync(**kwargs):
        assert kwargs["page_id"] == "page-1"
        assert kwargs["instagram_id"] == "ig-1"
        assert kwargs["ad_account_id"] == "ad-1"
        assert kwargs["token"]["page_tokens"]["page-1"] == "page-secret"
        return expected

    monkeypatch.setattr(service, "_sync_meta_metrics", fake_sync)
    result = await service.sync_metrics("demo", "meta", days=28, acting_person_id="owner")
    assert result == expected
    assert service.metrics("demo", "meta")["summary"]["organic_interactions"] == 12
    public = service.status("demo", "meta")
    assert public["metrics_status"] == "ready"
    assert "secret-token" not in json.dumps(public)


def test_meta_rows_are_normalised_for_cross_channel_analysis():
    page = MarketingConnectionService._normalise_meta_page_post({
        "id": "post-1", "message": "A result", "reactions": {"summary": {"total_count": 7}},
        "comments": {"summary": {"total_count": 2}}, "shares": {"count": 1},
    })
    instagram = MarketingConnectionService._normalise_instagram_media({
        "id": "media-1", "caption": "Proof", "like_count": 9, "comments_count": 3,
    })
    ad = MarketingConnectionService._normalise_meta_ad_row({
        "campaign_id": "campaign-1", "impressions": "100", "clicks": "4", "spend": "12.50",
    })
    assert page["reactions"] + page["comments"] + page["shares"] == 10
    assert instagram["likes"] + instagram["comments"] == 12
    assert ad["impressions"] == 100.0
    assert ad["spend"] == 12.5


@pytest.mark.asyncio
async def test_meta_connection_exam_keeps_page_tokens_out_of_business_evidence(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "meta", {"access_token": "user-secret"})
    _write(service._path("demo", "meta"), {
        "status": "connected", "provider": "meta", "secret_ref": secret_ref,
        "accounts": [], "selected_accounts": {},
    })

    async def fake_discover(provider, access_token):
        assert provider == "meta"
        assert access_token == "user-secret"
        return [{
            "id": "page-1", "name": "Demo Page", "kind": "page",
            "_page_access_token": "page-secret",
        }]

    monkeypatch.setattr(service, "_discover", fake_discover)
    result = await service.exam("demo", "meta", acting_person_id="owner")
    assert result["status"] == "passed"
    public = service.status("demo", "meta")
    assert "page-secret" not in json.dumps(public)
    assert public["accounts"] == [{"id": "page-1", "name": "Demo Page", "kind": "page"}]
    assert MarketingTokenStore.load("demo", "meta")["page_tokens"] == {"page-1": "page-secret"}


@pytest.mark.asyncio
async def test_youtube_metric_sync_persists_read_only_channel_and_video_evidence(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "youtube", {"access_token": "secret-token"})
    _write(service._path("demo", "youtube"), {
        "status": "connected", "provider": "youtube", "secret_ref": secret_ref,
        "accounts": [{"id": "channel-1", "name": "Tessaris Ai", "kind": "channel"}],
        "selected_accounts": {},
    })
    expected = {
        "schema_version": "aion.marketing.channel_metrics.v1", "provider": "youtube",
        "collected_at": "2026-10-10T18:00:00+00:00",
        "summary": {"youtube_videos_published": 0}, "channels": [],
        "read_only": True, "external_writes_enabled": False,
    }

    async def fake_sync(**kwargs):
        assert kwargs["channel_id"] == "channel-1"
        assert kwargs["token"]["access_token"] == "secret-token"
        return expected

    monkeypatch.setattr(service, "_sync_youtube_metrics", fake_sync)
    result = await service.sync_metrics("demo", "youtube", days=28, acting_person_id="owner")
    assert result == expected
    public = service.status("demo", "youtube")
    assert public["selected_accounts"] == {"channel": "channel-1"}
    assert public["metrics_status"] == "ready"
    assert "secret-token" not in json.dumps(public)


@pytest.mark.asyncio
async def test_connection_exam_auto_selects_a_single_visible_account(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    service = MarketingConnectionService()
    from backend.modules.aion_business.runtime.marketing_connection_service import _write
    secret_ref = MarketingTokenStore.save("demo", "youtube", {"access_token": "secret-token"})
    _write(service._path("demo", "youtube"), {
        "status": "connected", "provider": "youtube", "secret_ref": secret_ref,
        "accounts": [], "selected_accounts": {},
    })

    async def fake_discover(provider, access_token):
        return [{"id": "channel-1", "name": "Tessaris Ai", "kind": "channel"}]

    monkeypatch.setattr(service, "_discover", fake_discover)
    result = await service.exam("demo", "youtube", acting_person_id="owner")
    assert result["accounts_visible"] == 1
    assert service.status("demo", "youtube")["selected_accounts"] == {"channel": "channel-1"}
