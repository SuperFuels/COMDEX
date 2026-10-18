"""Customer-owned marketing channel connections.

OAuth credentials are stored outside business evidence (Keychain in production,
an isolated file store in tests).  Business files contain only safe metadata.
No method in this service publishes content or spends money.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime, guardian_mode_requested
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


PROVIDERS: dict[str, dict[str, Any]] = {
    "meta": {
        "label": "Meta · Facebook & Instagram", "client_id": "META_APP_ID", "client_secret": "META_APP_SECRET",
        "authorize": "https://www.facebook.com/{version}/dialog/oauth",
        "token": "https://graph.facebook.com/{version}/oauth/access_token",
        "scopes": {"analytics": ["pages_show_list", "pages_read_engagement", "read_insights", "instagram_basic", "instagram_manage_insights", "business_management"],
                   "organic": ["pages_manage_posts", "instagram_content_publish"],
                   "advertising": ["ads_read"]},
        "advertising": {"strategy": "shared_oauth", "account_kind": "ad_account"},
    },
    "linkedin": {
        "label": "LinkedIn", "client_id": "LINKEDIN_CLIENT_ID", "client_secret": "LINKEDIN_CLIENT_SECRET",
        "authorize": "https://www.linkedin.com/oauth/v2/authorization", "token": "https://www.linkedin.com/oauth/v2/accessToken",
        # Tessaris connects the customer's administered Company Page, not the
        # customer's personal profile.  LinkedIn provisions these permissions
        # through the separately-vetted Community Management application.
        "scopes": {"analytics": ["r_organization_admin", "r_organization_social"],
                   "organic": ["w_organization_social"], "advertising": ["r_ads", "r_ads_reporting"]},
        "advertising": {"strategy": "approval_required", "account_kind": "ad_account",
                        "approval_env": "LINKEDIN_ADS_ACCESS_APPROVED"},
    },
    "youtube": {
        "label": "YouTube", "client_id": "GOOGLE_MARKETING_CLIENT_ID", "client_secret": "GOOGLE_MARKETING_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
        "scopes": {"analytics": ["https://www.googleapis.com/auth/youtube.readonly"],
                   "organic": ["https://www.googleapis.com/auth/youtube.upload"], "advertising": []},
        "advertising": {"strategy": "not_applicable"},
    },
    "tiktok": {
        "label": "TikTok", "client_id": "TIKTOK_CLIENT_KEY", "client_secret": "TIKTOK_CLIENT_SECRET",
        "authorize": "https://www.tiktok.com/v2/auth/authorize/", "token": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": {"analytics": ["user.info.basic", "user.info.profile", "user.info.stats", "video.list"],
                   "organic": ["video.upload"], "advertising": []},
        "advertising": {"strategy": "separate_ads_app_required"},
    },
    "x": {
        "label": "X", "client_id": "X_CLIENT_ID", "client_secret": "X_CLIENT_SECRET",
        "authorize": "https://twitter.com/i/oauth2/authorize", "token": "https://api.x.com/2/oauth2/token",
        "scopes": {"analytics": ["tweet.read", "users.read", "offline.access"],
                   "organic": ["tweet.write"], "advertising": []},
        "advertising": {"strategy": "separate_ads_app_required"},
    },
    "pinterest": {
        "label": "Pinterest", "client_id": "PINTEREST_APP_ID", "client_secret": "PINTEREST_APP_SECRET",
        "authorize": "https://www.pinterest.com/oauth/", "token": "https://api.pinterest.com/v5/oauth/token",
        "scopes": {"analytics": ["user_accounts:read", "boards:read", "pins:read"],
                   "organic": ["boards:write", "pins:write"], "advertising": ["ads:read"]},
        "advertising": {"strategy": "shared_oauth", "account_kind": "ad_account"},
    },
    "google_business": {
        "label": "Google Business Profile", "client_id": "GOOGLE_MARKETING_CLIENT_ID", "client_secret": "GOOGLE_MARKETING_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
        "scopes": {"analytics": ["https://www.googleapis.com/auth/business.manage"], "organic": [], "advertising": []},
        "advertising": {"strategy": "not_applicable"},
    },
    "google_ads": {
        "label": "Google Ads", "client_id": "GOOGLE_MARKETING_CLIENT_ID", "client_secret": "GOOGLE_MARKETING_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
        "scopes": {"analytics": ["https://www.googleapis.com/auth/adwords"], "organic": [], "advertising": []},
        "advertising": {"strategy": "dedicated_provider", "account_kind": "customer"},
    },
    "microsoft_ads": {
        "label": "Microsoft Advertising", "client_id": "MICROSOFT_ADS_CLIENT_ID", "client_secret": "MICROSOFT_ADS_CLIENT_SECRET",
        "authorize": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": {"analytics": ["https://ads.microsoft.com/msads.manage", "offline_access"], "organic": [], "advertising": []},
        "advertising": {"strategy": "dedicated_provider", "account_kind": "ad_account"},
    },
}


class MarketingTokenStore:
    SERVICE = "com.tessaris.marketing.oauth"

    @classmethod
    def _account(cls, workspace_id: str, provider: str) -> str:
        return f"{canonical_business_id(workspace_id)}:{provider}"

    @classmethod
    def save(cls, workspace_id: str, provider: str, payload: dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_MARKETING_TOKEN_STORE_DIR") or "").strip()
        account = cls._account(workspace_id, provider)
        if test_dir:
            path = Path(test_dir) / f"{sha256(account.encode()).hexdigest()}.json"
            _write(path, payload)
            return f"test-secret-file://{path}"
        import keyring
        keyring.set_password(cls.SERVICE, account, json.dumps(payload))
        return f"keychain://{cls.SERVICE}/{account}"

    @classmethod
    def load(cls, workspace_id: str, provider: str) -> dict[str, Any]:
        test_dir = str(os.getenv("AION_MARKETING_TOKEN_STORE_DIR") or "").strip()
        account = cls._account(workspace_id, provider)
        if test_dir:
            return _read(Path(test_dir) / f"{sha256(account.encode()).hexdigest()}.json", {})
        import keyring
        raw = keyring.get_password(cls.SERVICE, account)
        return json.loads(raw) if raw else {}

    @classmethod
    def delete(cls, workspace_id: str, provider: str) -> None:
        test_dir = str(os.getenv("AION_MARKETING_TOKEN_STORE_DIR") or "").strip()
        account = cls._account(workspace_id, provider)
        if test_dir:
            path = Path(test_dir) / f"{sha256(account.encode()).hexdigest()}.json"
            path.unlink(missing_ok=True)
            return
        import keyring
        try:
            keyring.delete_password(cls.SERVICE, account)
        except Exception:
            pass


class MarketingPlatformCredentialStore:
    """Local platform-app credentials used to start customer OAuth safely."""

    SERVICE = "com.tessaris.marketing.platform-app"

    @classmethod
    def _load_payload(cls, provider: str) -> dict[str, Any]:
        try:
            import keyring
            raw = keyring.get_password(cls.SERVICE, provider)
            value = json.loads(raw) if raw else {}
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    @classmethod
    def _save_payload(cls, provider: str, payload: dict[str, Any]) -> None:
        import keyring
        keyring.set_password(cls.SERVICE, provider, json.dumps(payload))

    @classmethod
    def save(cls, provider: str, *, client_id: str, client_secret: str) -> None:
        payload = cls._load_payload(provider)
        payload.update({
            "client_id": str(client_id).strip(), "client_secret": str(client_secret).strip(),
            "updated_at": _now(),
        })
        cls._save_payload(provider, payload)

    @classmethod
    def save_platform_token(cls, provider: str, *, name: str, value: str) -> None:
        token = str(value or "").strip()
        if not token:
            raise ValueError("platform_token_required")
        payload = cls._load_payload(provider)
        payload[str(name)] = token
        payload["updated_at"] = _now()
        cls._save_payload(provider, payload)

    @classmethod
    def load(cls, provider: str) -> dict[str, str]:
        value = cls._load_payload(provider)
        return {
            "client_id": str(value.get("client_id") or ""),
            "client_secret": str(value.get("client_secret") or ""),
            "developer_token": str(value.get("developer_token") or ""),
        }


class MarketingConnectionService:
    DOMAIN_ID = "departments.operational_records"

    def __init__(self, *, base_url: str | None = None,
                 domain_store: VaultDomainStore | None = None) -> None:
        self.base_url = (base_url or os.getenv("AION_PUBLIC_BACKEND_URL") or "http://127.0.0.1:8080").rstrip("/")
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="marketing-connections-runtime"
            )

    @staticmethod
    def _entity_id(provider: str, kind: str) -> str:
        if provider not in PROVIDERS or kind not in {"connection", "metrics", "pending"}:
            raise ValueError("invalid_marketing_record_identity")
        return f"marketing/connections/{provider}/{kind}"

    def _load_record(self, workspace_id: str, provider: str, kind: str) -> dict[str, Any]:
        if self.domain_store is not None:
            row = self.domain_store.get_optional(
                self.DOMAIN_ID, workspace_id=canonical_business_id(workspace_id),
                entity_id=self._entity_id(provider, kind),
            )
            return dict(row["payload"]) if row is not None else {}
        paths = {
            "connection": self._path, "metrics": self._metrics_path, "pending": self._pending,
        }
        return _read(paths[kind](workspace_id, provider), {})

    def _write_record(self, workspace_id: str, provider: str, kind: str,
                      value: dict[str, Any], *, actor_id: str) -> None:
        workspace_id = canonical_business_id(workspace_id)
        if self.domain_store is not None:
            entity_id = self._entity_id(provider, kind)
            current = self.domain_store.get_optional(
                self.DOMAIN_ID, workspace_id=workspace_id, entity_id=entity_id,
            )
            self.domain_store.put(
                self.DOMAIN_ID, workspace_id=workspace_id, entity_id=entity_id,
                payload=value, expected_version=int(current["version"]) if current else None,
                actor_id=actor_id,
            )
            return
        paths = {
            "connection": self._path, "metrics": self._metrics_path, "pending": self._pending,
        }
        _write(paths[kind](workspace_id, provider), value)

    def _dir(self, workspace_id: str, provider: str) -> Path:
        if self.domain_store is not None:
            return Path("/__tessaris_guardian_marketing_connections__") / canonical_business_id(workspace_id) / provider
        path = AIONBusinessPaths.business_container_dir(canonical_business_id(workspace_id)) / "integrations" / "marketing" / provider
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str, provider: str) -> Path:
        return self._dir(workspace_id, provider) / "connection.json"

    def _metrics_path(self, workspace_id: str, provider: str) -> Path:
        return self._dir(workspace_id, provider) / "metrics.json"

    def _pending(self, workspace_id: str, provider: str) -> Path:
        return self._dir(workspace_id, provider) / "pending.json"

    def _redirect_uri(self, provider: str) -> str:
        base_url = self.base_url
        # Microsoft Entra accepts plain HTTP web callbacks only on localhost;
        # the equivalent 127.0.0.1 URL is rejected during app registration.
        if provider == "microsoft_ads" and base_url.startswith("http://127.0.0.1"):
            base_url = "http://localhost" + base_url.removeprefix("http://127.0.0.1")
        return f"{base_url}/api/aion/marketing/connections/{provider}/callback"

    @staticmethod
    def _credentials(provider: str) -> tuple[str, str]:
        spec = PROVIDERS[provider]
        saved = MarketingPlatformCredentialStore.load(provider)
        client_id = str(os.getenv(spec["client_id"]) or saved.get("client_id") or "").strip()
        client_secret = str(os.getenv(spec["client_secret"]) or saved.get("client_secret") or "").strip()
        if provider in {"google_ads", "youtube", "google_business"}:
            client_id = client_id or str(os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or "").strip()
            client_secret = client_secret or str(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
        return client_id, client_secret

    @staticmethod
    def _platform_token(provider: str, environment_name: str) -> str:
        environment_value = str(os.getenv(environment_name) or "").strip()
        if environment_value:
            return environment_value
        saved = MarketingPlatformCredentialStore.load(provider)
        token_names = {"MICROSOFT_ADS_DEVELOPER_TOKEN": "developer_token"}
        return str(saved.get(token_names.get(environment_name, "")) or "").strip()

    def platform_status(self, provider: str) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError("unsupported_marketing_provider")
        client_id, client_secret = self._credentials(provider)
        return {
            "provider": provider, "label": PROVIDERS[provider]["label"],
            "configured": bool(client_id and client_secret),
            "client_id_present": bool(client_id), "client_secret_present": bool(client_secret),
            "callback_url": self._redirect_uri(provider),
        }

    def configure_platform(self, provider: str, *, client_id: str, client_secret: str) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError("unsupported_marketing_provider")
        if not str(client_id).strip() or not str(client_secret).strip():
            raise ValueError("platform_client_id_and_secret_required")
        MarketingPlatformCredentialStore.save(
            provider, client_id=str(client_id).strip(), client_secret=str(client_secret).strip(),
        )
        return self.platform_status(provider)

    @staticmethod
    def _scopes(provider: str, tier: str) -> list[str]:
        levels = ["analytics"] + ([tier] if tier in {"organic", "advertising"} else [])
        return list(dict.fromkeys(scope for level in levels for scope in PROVIDERS[provider]["scopes"][level]))

    def catalog(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.status(workspace_id, provider) for provider in PROVIDERS]

    def status(self, workspace_id: str, provider: str) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError("unsupported_marketing_provider")
        value = self._load_record(workspace_id, provider, "connection")
        granted_scopes = list(value.get("granted_scopes", []))
        if provider == "microsoft_ads" and "offline_access" not in granted_scopes:
            # Microsoft often returns a refresh token without echoing the
            # ``offline_access`` pseudo-scope.  The refresh token is the
            # authoritative proof of durable access; expose only that fact.
            token = MarketingTokenStore.load(workspace_id, provider)
            if token.get("refresh_token"):
                granted_scopes.append("offline_access")
        client_id, client_secret = self._credentials(provider)
        configured = bool(client_id and client_secret)
        platform_requirements: list[str] = []
        required_platform_tokens = {"microsoft_ads": "MICROSOFT_ADS_DEVELOPER_TOKEN"}
        required_token = required_platform_tokens.get(provider)
        if required_token and not self._platform_token(provider, required_token):
            configured = False; platform_requirements.append(required_token)
        result = {
            "provider": provider, "label": PROVIDERS[provider]["label"],
            "configured": configured, "platform_requirements": platform_requirements,
            "status": value.get("status", "not_connected"),
            "connected": value.get("status") == "connected", "permission_tier": value.get("permission_tier", "analytics"),
            "granted_scopes": granted_scopes, "accounts": value.get("accounts", []),
            "selected_accounts": value.get("selected_accounts", {}), "connected_at": value.get("connected_at"),
            "connected_by": value.get("connected_by"), "last_exam": value.get("last_exam"),
            "health": value.get("health", "not_examined"), "reconnect_required": bool(value.get("reconnect_required")),
            "metrics_status": value.get("metrics_status", "not_synced"),
            "metrics_last_synced_at": value.get("metrics_last_synced_at"),
            "metrics_schema_version": value.get("metrics_schema_version"),
            "secret_storage": value.get("secret_ref", "") .split("://", 1)[0] if value.get("secret_ref") else None,
            "external_writes_enabled": False,
            "boundary": "Connection and read-only validation only; publishing and spend require separate exact approval.",
        }
        result["advertising"] = self._advertising_status(provider, result)
        return result

    @staticmethod
    def _advertising_status(provider: str, connection: dict[str, Any]) -> dict[str, Any]:
        """Describe paid-media readiness without confusing it with social access."""
        specification = PROVIDERS[provider].get("advertising") or {"strategy": "not_applicable"}
        strategy = str(specification.get("strategy") or "not_applicable")
        required_scopes = list(PROVIDERS[provider]["scopes"].get("advertising") or [])
        if strategy == "dedicated_provider":
            required_scopes = list(PROVIDERS[provider]["scopes"].get("analytics") or [])
        granted_scopes = {str(scope) for scope in connection.get("granted_scopes") or []}
        missing_scopes = [scope for scope in required_scopes if scope not in granted_scopes]
        account_kind = str(specification.get("account_kind") or "")
        selected_accounts = connection.get("selected_accounts") or {}
        account_selected = bool(account_kind and selected_accounts.get(account_kind))
        configured = bool(connection.get("configured"))
        connected = bool(connection.get("connected"))
        healthy = connection.get("health") == "healthy"

        approval_env = str(specification.get("approval_env") or "")
        approved = not approval_env or str(os.getenv(approval_env) or "").strip().lower() in {"1", "true", "yes", "approved"}
        if strategy == "not_applicable":
            state, can_authorize = "not_applicable", False
        elif strategy == "separate_ads_app_required":
            state, can_authorize = "separate_ads_api_required", False
        elif strategy == "approval_required" and not approved:
            state, can_authorize = "provider_approval_required", False
        elif not configured:
            state, can_authorize = "platform_setup_required", False
        elif connected and not missing_scopes and account_selected and healthy:
            state, can_authorize = "ready", True
        elif connected and not missing_scopes and account_selected:
            state, can_authorize = "test_required", True
        else:
            state, can_authorize = "authorization_required", True
        return {
            "state": state,
            "ready": state == "ready",
            "can_authorize": can_authorize,
            "strategy": strategy,
            "required_scopes": required_scopes,
            "missing_scopes": missing_scopes,
            "account_kind": account_kind or None,
            "account_selected": account_selected,
            "approval_requirement": approval_env or None,
        }

    def begin(self, workspace_id: str, provider: str, *, tier: str, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS or tier not in {"analytics", "organic", "advertising"}:
            raise ValueError("invalid_marketing_connection_request")
        client_id, client_secret = self._credentials(provider)
        if not client_id or not client_secret:
            return {"status": "platform_configuration_required", "provider": provider,
                    "missing": [name for name, value in ((PROVIDERS[provider]["client_id"], client_id), (PROVIDERS[provider]["client_secret"], client_secret)) if not value]}
        required_platform_tokens = {"microsoft_ads": "MICROSOFT_ADS_DEVELOPER_TOKEN"}
        required_token = required_platform_tokens.get(provider)
        if required_token and not self._platform_token(provider, required_token):
            return {"status": "platform_configuration_required", "provider": provider,
                    "missing": [required_token]}
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        digest = sha256(verifier.encode())
        # TikTok's Desktop Login Kit differs from the usual RFC 7636 wire
        # representation: it requires the SHA-256 digest as lowercase hex.
        # The other providers continue to use the standard base64url value.
        challenge = digest.hexdigest() if provider == "tiktok" else base64.urlsafe_b64encode(digest.digest()).decode().rstrip("=")
        redirect_uri = self._redirect_uri(provider)
        pending = {"workspace_id": canonical_business_id(workspace_id), "provider": provider, "state": state,
                   "verifier": verifier, "tier": tier, "acting_person_id": acting_person_id,
                   "redirect_uri": redirect_uri, "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}
        pending["status"] = "pending"
        self._write_record(
            workspace_id, provider, "pending", pending,
            actor_id=acting_person_id,
        )
        spec = PROVIDERS[provider]
        version = str(os.getenv("META_GRAPH_API_VERSION") or "v26.0")
        params: dict[str, Any] = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state,
                                  "scope": " ".join(self._scopes(provider, tier)), "code_challenge": challenge, "code_challenge_method": "S256"}
        if provider in {"google_ads", "youtube", "google_business"}:
            params.update({"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"})
        if provider == "tiktok":
            params["client_key"] = params.pop("client_id"); params["scope"] = ",".join(self._scopes(provider, tier))
        if provider == "pinterest":
            params["scope"] = ",".join(self._scopes(provider, tier))
        return {"status": "authorization_required", "provider": provider,
                "authorization_url": spec["authorize"].format(version=version) + "?" + urlencode(params),
                "expires_in_seconds": 3600, "permission_tier": tier}

    def _locate_pending(self, provider: str, state: str) -> dict[str, Any]:
        if self.domain_store is not None:
            entity_id = self._entity_id(provider, "pending")
            for row in self.domain_store.list_all(self.DOMAIN_ID):
                if row.get("entity_id") != entity_id:
                    continue
                value = dict(row["payload"])
                if value.get("status", "pending") != "pending":
                    continue
                if secrets.compare_digest(str(value.get("state") or ""), state):
                    value["_vault_workspace_id"] = str(row["workspace_id"])
                    return value
            raise ValueError("oauth_state_invalid_or_expired")
        root = AIONBusinessPaths.BUSINESS_CONTAINERS
        for path in root.glob(f"*/integrations/marketing/{provider}/pending.json"):
            value = _read(path, {})
            if secrets.compare_digest(str(value.get("state") or ""), state):
                value["_path"] = str(path)
                return value
        raise ValueError("oauth_state_invalid_or_expired")

    def _consume_pending(self, provider: str, pending: dict[str, Any]) -> None:
        if self.domain_store is not None:
            workspace_id = str(pending.get("_vault_workspace_id") or pending["workspace_id"])
            consumed = {key: value for key, value in pending.items() if not key.startswith("_")}
            consumed.update({"status": "consumed", "consumed_at": _now(), "verifier": None})
            self._write_record(
                workspace_id, provider, "pending", consumed,
                actor_id=str(pending.get("acting_person_id") or "marketing-oauth-callback"),
            )
            return
        Path(pending["_path"]).unlink(missing_ok=True)

    async def complete(self, provider: str, *, state: str, code: str) -> dict[str, Any]:
        pending = self._locate_pending(provider, state)
        if datetime.fromisoformat(pending["expires_at"]) < datetime.now(UTC):
            raise ValueError("oauth_state_expired")
        client_id, client_secret = self._credentials(provider)
        spec = PROVIDERS[provider]; version = str(os.getenv("META_GRAPH_API_VERSION") or "v26.0")
        body = {"client_id": client_id, "client_secret": client_secret, "code": code,
                "redirect_uri": pending["redirect_uri"], "grant_type": "authorization_code", "code_verifier": pending["verifier"]}
        if provider == "tiktok":
            body["client_key"] = body.pop("client_id"); body["client_secret"] = body.pop("client_secret")
        token_auth = None
        if provider in {"x", "pinterest"}:
            token_auth = (client_id, client_secret)
            body.pop("client_id", None); body.pop("client_secret", None)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(spec["token"].format(version=version), data=body, auth=token_auth)
            response.raise_for_status(); token = response.json()
        if "access_token" not in token:
            # OAuth providers often return a 200 response containing an error
            # object. Surface only the provider's safe diagnostic fields so a
            # failed setup can be corrected without exposing tokens or secrets.
            error = token.get("error")
            if isinstance(error, dict):
                parts = [error.get("code"), error.get("message"), error.get("log_id")]
            else:
                parts = [error, token.get("error_description"), token.get("message"), token.get("log_id")]
            detail = " | ".join(str(part) for part in parts if part)
            raise ValueError(f"provider_token_error: {detail}" if detail else "provider_did_not_return_access_token")
        if provider == "meta":
            token = await self._exchange_meta_long_lived_token(token, client_id, client_secret, version)
        if token.get("expires_in"):
            token["expires_at"] = (datetime.now(UTC) + timedelta(seconds=int(token["expires_in"]))).isoformat()
        workspace_id = pending["workspace_id"]
        accounts = await self._discover(provider, token["access_token"])
        if provider == "meta":
            page_tokens: dict[str, str] = {}
            for account in accounts:
                page_access_token = account.pop("_page_access_token", None)
                if account.get("kind") == "page" and page_access_token:
                    page_tokens[str(account["id"])] = str(page_access_token)
            token["page_tokens"] = page_tokens
        secret_ref = MarketingTokenStore.save(workspace_id, provider, token)
        selected_accounts = {}
        for kind in {str(account.get("kind") or "primary") for account in accounts}:
            candidates = [account for account in accounts if str(account.get("kind") or "primary") == kind]
            if len(candidates) == 1 and candidates[0].get("id"):
                selected_accounts[kind] = str(candidates[0]["id"])
        granted_scopes = str(
            token.get("scope") or " ".join(self._scopes(provider, pending["tier"]))
        ).replace(",", " ").split()
        # Microsoft commonly omits ``offline_access`` from the returned scope
        # string even though a refresh token proves that durable access was
        # granted.  Preserve that fact in the public readiness record without
        # exposing the refresh token itself.
        if provider == "microsoft_ads" and token.get("refresh_token") and "offline_access" not in granted_scopes:
            granted_scopes.append("offline_access")
        record = {"status": "connected", "provider": provider, "permission_tier": pending["tier"],
                  "granted_scopes": granted_scopes,
                  "accounts": accounts, "selected_accounts": selected_accounts, "connected_at": _now(),
                  "connected_by": pending["acting_person_id"], "secret_ref": secret_ref, "health": "connected_not_examined"}
        self._write_record(
            workspace_id, provider, "connection", record,
            actor_id=str(pending["acting_person_id"]),
        )
        self._consume_pending(provider, pending)
        return self.status(workspace_id, provider)

    async def _exchange_meta_long_lived_token(
        self, token: dict[str, Any], client_id: str, client_secret: str, version: str,
    ) -> dict[str, Any]:
        """Exchange Meta's short-lived user token without exposing it to business evidence."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"https://graph.facebook.com/{version}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "fb_exchange_token": token["access_token"],
                    },
                )
                response.raise_for_status()
                exchanged = response.json()
            if exchanged.get("access_token"):
                token = {**token, **exchanged}
        except Exception:
            # A valid short-lived token is still usable for discovery and can be
            # re-authorised.  The read-only exam records failures explicitly.
            pass
        return token

    async def _discover(self, provider: str, access_token: str) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}; version = str(os.getenv("META_GRAPH_API_VERSION") or "v26.0")
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            if provider == "meta":
                page_response = await client.get(
                    f"https://graph.facebook.com/{version}/me/accounts",
                    params={"fields": "id,name,tasks,access_token,instagram_business_account{id,username,name}"},
                )
                page_response.raise_for_status(); pages = page_response.json().get("data", [])
                accounts = [{"id": x.get("id"), "name": x.get("name"), "kind": "page",
                             "tasks": x.get("tasks") or [], "_page_access_token": x.get("access_token")} for x in pages]
                for page in pages:
                    ig = page.get("instagram_business_account") or {}
                    if ig.get("id"):
                        accounts.append({"id": ig["id"], "name": ig.get("username") or ig.get("name") or ig["id"], "kind": "instagram", "page_id": page.get("id")})
                ads_response = await client.get(f"https://graph.facebook.com/{version}/me/adaccounts", params={"fields": "id,name,account_status,currency,timezone_name"})
                if ads_response.is_success:
                    accounts.extend({"id": x.get("id"), "name": x.get("name") or x.get("id"), "kind": "ad_account",
                                     "currency": x.get("currency"), "account_status": x.get("account_status")} for x in ads_response.json().get("data", []))
                return accounts
            if provider == "google_ads":
                api_version = str(os.getenv("GOOGLE_ADS_API_VERSION") or "v24")
                response = await client.get(f"https://googleads.googleapis.com/{api_version}/customers:listAccessibleCustomers")
                response.raise_for_status()
                accounts: list[dict[str, Any]] = []
                for resource_name in response.json().get("resourceNames", []):
                    customer_id = str(resource_name).split("/")[-1]
                    account = {"id": customer_id, "name": str(resource_name), "kind": "customer"}
                    # listAccessibleCustomers intentionally returns identifiers only.
                    # Resolve each directly accessible customer so the owner can select
                    # the correct business instead of choosing an opaque number.
                    detail_response = await client.post(
                        f"https://googleads.googleapis.com/{api_version}/customers/{customer_id}/googleAds:searchStream",
                        json={
                            "query": (
                                "SELECT customer.id, customer.descriptive_name, "
                                "customer.currency_code, customer.time_zone, customer.manager, "
                                "customer.test_account, customer.status FROM customer LIMIT 1"
                            )
                        },
                    )
                    if detail_response.is_success:
                        batches = detail_response.json()
                        if isinstance(batches, dict):
                            batches = [batches]
                        first_result = next(
                            (
                                result
                                for batch in batches if isinstance(batch, dict)
                                for result in batch.get("results", []) if isinstance(result, dict)
                            ),
                            {},
                        )
                        customer = first_result.get("customer") or {}
                        account.update({
                            "name": customer.get("descriptiveName") or str(resource_name),
                            "currency": customer.get("currencyCode"),
                            "time_zone": customer.get("timeZone"),
                            "manager": bool(customer.get("manager")),
                            "test_account": bool(customer.get("testAccount")),
                            "account_status": customer.get("status"),
                        })
                    accounts.append(account)
                return accounts
            if provider == "youtube":
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "id,snippet", "mine": "true"},
                )
                response.raise_for_status()
                data = response.json()
                return [{"id": x.get("id"), "name": (x.get("snippet") or {}).get("title"), "kind": "channel"} for x in data.get("items", [])]
            if provider == "linkedin":
                linkedin_headers = {
                    **headers,
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Linkedin-Version": str(os.getenv("LINKEDIN_API_VERSION") or "202609"),
                    "Content-Type": "application/json",
                }
                acl_response = await client.get(
                    "https://api.linkedin.com/rest/organizationAcls",
                    params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED", "count": 100},
                    headers=linkedin_headers,
                )
                acl_response.raise_for_status()
                organization_ids: list[str] = []
                for row in acl_response.json().get("elements", []):
                    urn = str(row.get("organizationTarget") or row.get("organization") or "")
                    organization_id = urn.rsplit(":", 1)[-1] if urn.startswith("urn:li:organization:") else ""
                    if organization_id and organization_id not in organization_ids:
                        organization_ids.append(organization_id)
                accounts: list[dict[str, Any]] = []
                for organization_id in organization_ids:
                    organization_response = await client.get(
                        f"https://api.linkedin.com/rest/organizations/{organization_id}",
                        headers=linkedin_headers,
                    )
                    if not organization_response.is_success:
                        continue
                    organization = organization_response.json()
                    accounts.append({
                        "id": organization_id,
                        "name": organization.get("localizedName") or organization.get("vanityName") or organization_id,
                        "kind": "organization",
                        "urn": f"urn:li:organization:{organization_id}",
                        "vanity_name": organization.get("vanityName"),
                    })
                return accounts
            if provider == "tiktok":
                response = await client.get(
                    "https://open.tiktokapis.com/v2/user/info/",
                    params={"fields": "open_id,display_name,avatar_url,profile_deep_link,bio_description,is_verified,follower_count,following_count,likes_count,video_count"},
                )
                response.raise_for_status()
                data = response.json().get("data", {}).get("user", {})
                return [{
                    "id": data.get("open_id"), "name": data.get("display_name") or data.get("open_id"),
                    "kind": "creator", "profile_deep_link": data.get("profile_deep_link"),
                    "is_verified": bool(data.get("is_verified")),
                }]
            if provider == "x":
                data = (await client.get("https://api.x.com/2/users/me", params={"user.fields": "id,name,username"})).json().get("data", {})
                return [{"id": data.get("id"), "name": data.get("username") or data.get("name"), "kind": "profile"}]
            if provider == "pinterest":
                data = (await client.get("https://api.pinterest.com/v5/user_account")).json()
                return [{"id": data.get("username") or data.get("id"), "name": data.get("username") or data.get("business_name"), "kind": "profile"}]
            if provider == "google_business":
                data = (await client.get("https://mybusinessaccountmanagement.googleapis.com/v1/accounts")).json()
                return [{"id": str(x.get("name") or "").split("/")[-1], "name": x.get("accountName") or x.get("name"), "kind": "business_account"} for x in data.get("accounts", [])]
            if provider == "microsoft_ads":
                developer_token = self._platform_token(
                    "microsoft_ads", "MICROSOFT_ADS_DEVELOPER_TOKEN",
                )
                if not developer_token:
                    raise ValueError("microsoft_ads_developer_token_required")
                response = await client.post(
                    "https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13/AccountsInfo/Query",
                    headers={**headers, "DeveloperToken": developer_token, "Content-Type": "application/json"},
                    json={"OnlyParentAccounts": False},
                )
                response.raise_for_status()
                return [
                    {
                        "id": str(item.get("Id") or ""),
                        "name": item.get("Name") or item.get("Number") or str(item.get("Id") or ""),
                        "kind": "ad_account",
                        "account_number": item.get("Number"),
                        "account_status": item.get("AccountLifeCycleStatus"),
                    }
                    for item in response.json().get("AccountsInfo", [])
                    if item.get("Id")
                ]
            return []

    def metrics(self, workspace_id: str, provider: str) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError("unsupported_marketing_provider")
        return self._load_record(workspace_id, provider, "metrics")

    async def sync_metrics(
        self, workspace_id: str, provider: str, *, days: int = 28, acting_person_id: str,
    ) -> dict[str, Any]:
        if provider not in {"meta", "youtube", "linkedin", "tiktok"}:
            raise ValueError("provider_metrics_sync_not_implemented")
        record = self._load_record(workspace_id, provider, "connection")
        token = MarketingTokenStore.load(workspace_id, provider)
        if record.get("status") != "connected" or not token.get("access_token"):
            raise ValueError("provider_not_connected")
        selected = record.get("selected_accounts") or {}
        if provider == "youtube":
            channel_id = str(selected.get("channel") or "")
            if not channel_id:
                channels = [item for item in record.get("accounts", []) if item.get("kind") == "channel"]
                if len(channels) == 1:
                    channel_id = str(channels[0].get("id") or "")
                    selected = {**selected, "channel": channel_id}
                    record["selected_accounts"] = selected
            if not channel_id:
                raise ValueError("provider_account_not_selected")
            bounded_days = max(1, min(int(days or 28), 90))
            until = datetime.now(UTC).date()
            since = until - timedelta(days=bounded_days - 1)
            snapshot = await self._sync_youtube_metrics(
                workspace_id=canonical_business_id(workspace_id), token=token,
                channel_id=channel_id, since=since.isoformat(), until=until.isoformat(),
                acting_person_id=acting_person_id,
            )
            self._write_record(workspace_id, provider, "metrics", snapshot, actor_id=acting_person_id)
            record.update({"metrics_status": "ready", "metrics_last_synced_at": snapshot["collected_at"],
                           "metrics_schema_version": snapshot["schema_version"]})
            self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
            return snapshot

        if provider == "linkedin":
            organization_id = str(selected.get("organization") or "")
            if not organization_id:
                organizations = [item for item in record.get("accounts", []) if item.get("kind") == "organization"]
                if len(organizations) == 1:
                    organization_id = str(organizations[0].get("id") or "")
                    selected = {**selected, "organization": organization_id}
                    record["selected_accounts"] = selected
            if not organization_id:
                raise ValueError("provider_account_not_selected")
            bounded_days = max(1, min(int(days or 28), 90))
            until = datetime.now(UTC).date()
            since = until - timedelta(days=bounded_days - 1)
            snapshot = await self._sync_linkedin_metrics(
                workspace_id=canonical_business_id(workspace_id), token=token,
                organization_id=organization_id, since=since.isoformat(), until=until.isoformat(),
                acting_person_id=acting_person_id,
            )
            self._write_record(workspace_id, provider, "metrics", snapshot, actor_id=acting_person_id)
            record.update({"metrics_status": "ready", "metrics_last_synced_at": snapshot["collected_at"],
                           "metrics_schema_version": snapshot["schema_version"]})
            self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
            return snapshot

        if provider == "tiktok":
            creator_id = str(selected.get("creator") or "")
            if not creator_id:
                creators = [item for item in record.get("accounts", []) if item.get("kind") == "creator"]
                if len(creators) == 1:
                    creator_id = str(creators[0].get("id") or "")
                    selected = {**selected, "creator": creator_id}
                    record["selected_accounts"] = selected
            if not creator_id:
                raise ValueError("provider_account_not_selected")
            bounded_days = max(1, min(int(days or 28), 90))
            until = datetime.now(UTC).date()
            since = until - timedelta(days=bounded_days - 1)
            snapshot = await self._sync_tiktok_metrics(
                workspace_id=canonical_business_id(workspace_id), token=token,
                creator_id=creator_id, since=since.isoformat(), until=until.isoformat(),
                acting_person_id=acting_person_id,
            )
            self._write_record(workspace_id, provider, "metrics", snapshot, actor_id=acting_person_id)
            record.update({"metrics_status": "ready", "metrics_last_synced_at": snapshot["collected_at"],
                           "metrics_schema_version": snapshot["schema_version"]})
            self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
            return snapshot

        page_id = str(selected.get("page") or "")
        instagram_id = str(selected.get("instagram") or "")
        ad_account_id = str(selected.get("ad_account") or "")
        if not any((page_id, instagram_id, ad_account_id)):
            raise ValueError("provider_account_not_selected")
        bounded_days = max(1, min(int(days or 28), 90))
        until = datetime.now(UTC).date()
        since = until - timedelta(days=bounded_days - 1)
        snapshot = await self._sync_meta_metrics(
            workspace_id=canonical_business_id(workspace_id), token=token,
            page_id=page_id, instagram_id=instagram_id, ad_account_id=ad_account_id,
            since=since.isoformat(), until=until.isoformat(), acting_person_id=acting_person_id,
        )
        self._write_record(workspace_id, provider, "metrics", snapshot, actor_id=acting_person_id)
        record.update({"metrics_status": "ready", "metrics_last_synced_at": snapshot["collected_at"],
                       "metrics_schema_version": snapshot["schema_version"]})
        self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
        return snapshot

    async def _sync_youtube_metrics(
        self, *, workspace_id: str, token: dict[str, Any], channel_id: str,
        since: str, until: str, acting_person_id: str,
    ) -> dict[str, Any]:
        """Collect a bounded read-only channel and recent-video snapshot."""
        headers = {"Authorization": f"Bearer {str(token.get('access_token') or '')}"}
        receipts: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            async def fetch(label: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
                try:
                    response = await client.get(f"https://www.googleapis.com/youtube/v3/{path}", params=params)
                    response.raise_for_status()
                    receipts.append({"source": label, "fetched_at": _now(), "api": "youtube-data-v3"})
                    return response.json()
                except Exception as exc:
                    errors.append({"source": label, "error": type(exc).__name__})
                    return {}

            channel_data = await fetch("youtube_channel", "channels", {
                "part": "id,snippet,statistics,contentDetails", "id": channel_id,
            })
            channel = next(iter(channel_data.get("items") or []), {})
            uploads_id = str(
                (((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")) or ""
            )

            uploads: list[dict[str, Any]] = []
            next_page = ""
            # Four inexpensive playlist pages cover up to 200 recent uploads while
            # keeping every sync bounded and predictable.
            for _ in range(4):
                if not uploads_id:
                    break
                params = {"part": "snippet,contentDetails", "playlistId": uploads_id, "maxResults": 50}
                if next_page:
                    params["pageToken"] = next_page
                page = await fetch("youtube_uploads", "playlistItems", params)
                items = page.get("items") or []
                uploads.extend(items)
                next_page = str(page.get("nextPageToken") or "")
                oldest = min(
                    (str((item.get("contentDetails") or {}).get("videoPublishedAt") or
                         (item.get("snippet") or {}).get("publishedAt") or "")[:10] for item in items),
                    default="",
                )
                if not next_page or (oldest and oldest < since):
                    break

            recent_uploads = []
            for item in uploads:
                details = item.get("contentDetails") or {}
                snippet = item.get("snippet") or {}
                published_at = str(details.get("videoPublishedAt") or snippet.get("publishedAt") or "")
                video_id = str(details.get("videoId") or (snippet.get("resourceId") or {}).get("videoId") or "")
                if video_id and since <= published_at[:10] <= until:
                    recent_uploads.append({"id": video_id, "published_at": published_at})

            video_rows: list[dict[str, Any]] = []
            for offset in range(0, len(recent_uploads), 50):
                chunk = recent_uploads[offset:offset + 50]
                videos = await fetch("youtube_videos", "videos", {
                    "part": "id,snippet,statistics", "id": ",".join(item["id"] for item in chunk),
                    "maxResults": 50,
                })
                for item in videos.get("items") or []:
                    snippet = item.get("snippet") or {}
                    stats = item.get("statistics") or {}
                    video_rows.append({
                        "content_id": item.get("id"), "published_at": snippet.get("publishedAt"),
                        "title": snippet.get("title"),
                        "views": int(stats.get("viewCount") or 0),
                        "likes": int(stats.get("likeCount") or 0),
                        "comments": int(stats.get("commentCount") or 0),
                    })

        snippet = channel.get("snippet") or {}
        statistics = channel.get("statistics") or {}
        profile = {
            "title": snippet.get("title"), "custom_url": snippet.get("customUrl"),
            "published_at": snippet.get("publishedAt"),
            "subscribers": int(statistics.get("subscriberCount") or 0),
            "views": int(statistics.get("viewCount") or 0),
            "videos": int(statistics.get("videoCount") or 0),
            "subscribers_hidden": bool(statistics.get("hiddenSubscriberCount")),
        }
        summary = {
            "youtube_videos_published": len(video_rows),
            "youtube_video_views": sum(item["views"] for item in video_rows),
            "youtube_video_likes": sum(item["likes"] for item in video_rows),
            "youtube_video_comments": sum(item["comments"] for item in video_rows),
            "youtube_channel_subscribers": profile["subscribers"],
            "youtube_channel_views": profile["views"],
            "youtube_channel_videos": profile["videos"],
        }
        return {
            "schema_version": "aion.marketing.channel_metrics.v1", "workspace_id": workspace_id,
            "provider": "youtube", "range": {"since": since, "until": until},
            "collected_at": _now(), "collected_by": acting_person_id,
            "channels": [{"channel": "youtube", "account_id": channel_id,
                          "account_name": profile["title"], "profile": profile, "content": video_rows}],
            "summary": summary, "source_receipts": receipts, "partial_errors": errors,
            "read_only": True, "external_writes_enabled": False,
        }

    async def _sync_linkedin_metrics(
        self, *, workspace_id: str, token: dict[str, Any], organization_id: str,
        since: str, until: str, acting_person_id: str,
    ) -> dict[str, Any]:
        """Collect a bounded read-only Company Page, post and engagement snapshot."""
        headers = {
            "Authorization": f"Bearer {str(token.get('access_token') or '')}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": str(os.getenv("LINKEDIN_API_VERSION") or "202609"),
            "Content-Type": "application/json",
        }
        organization_urn = f"urn:li:organization:{organization_id}"
        start_ms = int(datetime.fromisoformat(f"{since}T00:00:00+00:00").timestamp() * 1000)
        end_ms = int((datetime.fromisoformat(f"{until}T00:00:00+00:00") + timedelta(days=1)).timestamp() * 1000)
        interval = f"(timeRange:(start:{start_ms},end:{end_ms}),timeGranularityType:DAY)"
        receipts: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            async def fetch(label: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
                try:
                    response = await client.get(f"https://api.linkedin.com/rest/{path}", params=params or {})
                    response.raise_for_status()
                    receipts.append({"source": label, "fetched_at": _now(),
                                     "api": "linkedin-rest", "api_version": headers["Linkedin-Version"]})
                    return response.json()
                except Exception as exc:
                    errors.append({"source": label, "error": type(exc).__name__})
                    return {}

            profile = await fetch("linkedin_organization", f"organizations/{organization_id}")
            posts = await fetch("linkedin_posts", "posts", {
                "q": "author", "author": organization_urn, "count": 100, "sortBy": "LAST_MODIFIED",
            })
            share_statistics = await fetch("linkedin_share_statistics", "organizationalEntityShareStatistics", {
                "q": "organizationalEntity", "organizationalEntity": organization_urn,
                "timeIntervals": interval,
            })
            page_statistics = await fetch("linkedin_page_statistics", "organizationPageStatistics", {
                "q": "organization", "organization": organization_urn, "timeIntervals": interval,
            })

        post_rows = [self._normalise_linkedin_post(item) for item in posts.get("elements", [])]
        aggregate = self._summarise_linkedin_statistics(share_statistics.get("elements", []))
        return {
            "schema_version": "aion.marketing.channel_metrics.v1", "workspace_id": workspace_id,
            "provider": "linkedin", "range": {"since": since, "until": until},
            "collected_at": _now(), "collected_by": acting_person_id,
            "channels": [{
                "channel": "linkedin", "account_id": organization_id,
                "account_name": profile.get("localizedName") or profile.get("vanityName") or organization_id,
                "profile": {
                    "vanity_name": profile.get("vanityName"),
                    "website": (profile.get("website") or {}).get("preferredLocale")
                        if isinstance(profile.get("website"), dict) else profile.get("website"),
                    "page_statistics": page_statistics.get("elements", []),
                },
                "content": post_rows,
                "period_metrics": aggregate,
            }],
            "summary": {"linkedin_posts": len(post_rows), **aggregate},
            "source_receipts": receipts, "partial_errors": errors,
            "read_only": True, "external_writes_enabled": False,
        }

    async def _sync_tiktok_metrics(
        self, *, workspace_id: str, token: dict[str, Any], creator_id: str,
        since: str, until: str, acting_person_id: str,
    ) -> dict[str, Any]:
        """Collect a bounded read-only TikTok creator and recent-video snapshot."""
        headers = {
            "Authorization": f"Bearer {str(token.get('access_token') or '')}",
            "Content-Type": "application/json",
        }
        receipts: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            profile: dict[str, Any] = {}
            try:
                response = await client.get(
                    "https://open.tiktokapis.com/v2/user/info/",
                    params={"fields": "open_id,union_id,avatar_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count"},
                )
                response.raise_for_status()
                profile = response.json().get("data", {}).get("user", {})
                receipts.append({"source": "tiktok_creator", "fetched_at": _now(), "api": "tiktok-v2"})
            except Exception as exc:
                errors.append({"source": "tiktok_creator", "error": type(exc).__name__})

            videos: list[dict[str, Any]] = []
            cursor: int | None = None
            fields = (
                "id,create_time,cover_image_url,share_url,video_description,duration,height,width,title,"
                "embed_html,embed_link,like_count,comment_count,share_count,view_count"
            )
            for _ in range(10):
                payload: dict[str, Any] = {"max_count": 20}
                if cursor is not None:
                    payload["cursor"] = cursor
                try:
                    response = await client.post(
                        "https://open.tiktokapis.com/v2/video/list/",
                        params={"fields": fields}, json=payload,
                    )
                    response.raise_for_status()
                    data = response.json().get("data", {})
                    page_videos = data.get("videos") or []
                    videos.extend(page_videos)
                    receipts.append({"source": "tiktok_videos", "fetched_at": _now(), "api": "tiktok-v2"})
                    if not data.get("has_more") or not page_videos:
                        break
                    cursor = int(data.get("cursor") or 0)
                    oldest = min((int(item.get("create_time") or 0) for item in page_videos), default=0)
                    if oldest and datetime.fromtimestamp(oldest, UTC).date().isoformat() < since:
                        break
                except Exception as exc:
                    errors.append({"source": "tiktok_videos", "error": type(exc).__name__})
                    break

        content: list[dict[str, Any]] = []
        for item in videos:
            created = int(item.get("create_time") or 0)
            published_at = datetime.fromtimestamp(created, UTC).isoformat() if created else ""
            if not published_at or not (since <= published_at[:10] <= until):
                continue
            content.append({
                "content_id": item.get("id"), "published_at": published_at,
                "title": item.get("title"), "description": item.get("video_description"),
                "share_url": item.get("share_url"), "cover_image_url": item.get("cover_image_url"),
                "duration_seconds": int(item.get("duration") or 0),
                "views": int(item.get("view_count") or 0), "likes": int(item.get("like_count") or 0),
                "comments": int(item.get("comment_count") or 0), "shares": int(item.get("share_count") or 0),
            })

        safe_profile = {
            "display_name": profile.get("display_name"), "bio_description": profile.get("bio_description"),
            "profile_deep_link": profile.get("profile_deep_link"), "avatar_url": profile.get("avatar_url"),
            "is_verified": bool(profile.get("is_verified")),
            "followers": int(profile.get("follower_count") or 0),
            "following": int(profile.get("following_count") or 0),
            "likes": int(profile.get("likes_count") or 0), "videos": int(profile.get("video_count") or 0),
        }
        summary = {
            "tiktok_videos_published": len(content),
            "tiktok_video_views": sum(item["views"] for item in content),
            "tiktok_video_likes": sum(item["likes"] for item in content),
            "tiktok_video_comments": sum(item["comments"] for item in content),
            "tiktok_video_shares": sum(item["shares"] for item in content),
            "tiktok_followers": safe_profile["followers"], "tiktok_following": safe_profile["following"],
            "tiktok_profile_likes": safe_profile["likes"], "tiktok_profile_videos": safe_profile["videos"],
        }
        return {
            "schema_version": "aion.marketing.channel_metrics.v1", "workspace_id": workspace_id,
            "provider": "tiktok", "range": {"since": since, "until": until},
            "collected_at": _now(), "collected_by": acting_person_id,
            "channels": [{"channel": "tiktok", "account_id": creator_id,
                          "account_name": safe_profile["display_name"] or creator_id,
                          "profile": safe_profile, "content": content}],
            "summary": summary, "source_receipts": receipts, "partial_errors": errors,
            "read_only": True, "external_writes_enabled": False,
        }

    @staticmethod
    def _normalise_linkedin_post(item: dict[str, Any]) -> dict[str, Any]:
        commentary = item.get("commentary")
        if isinstance(commentary, dict):
            commentary = commentary.get("text") or commentary.get("localized") or ""
        return {
            "content_id": item.get("id") or item.get("activity"),
            "published_at": item.get("publishedAt") or item.get("createdAt") or item.get("lastModifiedAt"),
            "text": str(commentary or "")[:1000],
            "lifecycle_state": item.get("lifecycleState"),
            "visibility": item.get("visibility"),
        }

    @staticmethod
    def _summarise_linkedin_statistics(elements: list[dict[str, Any]]) -> dict[str, int | float]:
        totals: dict[str, int | float] = {
            "linkedin_impressions": 0, "linkedin_unique_impressions": 0,
            "linkedin_clicks": 0, "linkedin_likes": 0,
            "linkedin_comments": 0, "linkedin_shares": 0,
        }
        mapping = {
            "impressionCount": "linkedin_impressions",
            "uniqueImpressionsCount": "linkedin_unique_impressions",
            "clickCount": "linkedin_clicks", "likeCount": "linkedin_likes",
            "commentCount": "linkedin_comments", "shareCount": "linkedin_shares",
        }
        for element in elements:
            statistics = element.get("totalShareStatistics") or element.get("shareStatistics") or {}
            for source, target in mapping.items():
                totals[target] += int(statistics.get(source) or 0)
        impressions = int(totals["linkedin_impressions"] or 0)
        interactions = sum(int(totals[key] or 0) for key in (
            "linkedin_clicks", "linkedin_likes", "linkedin_comments", "linkedin_shares",
        ))
        totals["linkedin_engagement_rate"] = interactions / impressions if impressions else 0.0
        return totals

    async def _sync_meta_metrics(
        self, *, workspace_id: str, token: dict[str, Any], page_id: str,
        instagram_id: str, ad_account_id: str, since: str, until: str,
        acting_person_id: str,
    ) -> dict[str, Any]:
        version = str(os.getenv("META_GRAPH_API_VERSION") or "v26.0")
        user_token = str(token.get("access_token") or "")
        page_token = str((token.get("page_tokens") or {}).get(page_id) or user_token)
        channels: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=30) as client:
            async def fetch(label: str, object_id: str, edge: str = "", *, params: dict[str, Any] | None = None,
                            access_token: str = user_token) -> dict[str, Any]:
                url = f"https://graph.facebook.com/{version}/{object_id}{('/' + edge) if edge else ''}"
                query = {**(params or {}), "access_token": access_token}
                try:
                    response = await client.get(url, params=query)
                    response.raise_for_status()
                    value = response.json()
                    receipts.append({"source": label, "object_id": object_id, "edge": edge or "object",
                                     "fetched_at": _now(), "api_version": version})
                    return value
                except Exception as exc:
                    errors.append({"source": label, "error": type(exc).__name__})
                    return {}

            if page_id:
                profile = await fetch("facebook_page_profile", page_id, params={
                    "fields": "id,name,fan_count,followers_count,link,verification_status",
                }, access_token=page_token)
                page_metrics: dict[str, Any] = {}
                for metric in ("page_impressions", "page_post_engagements", "page_daily_follows", "page_daily_unfollows_unique"):
                    result = await fetch(f"facebook_page_{metric}", page_id, "insights", params={
                        "metric": metric, "period": "day", "since": since, "until": until,
                    }, access_token=page_token)
                    if result.get("data"):
                        page_metrics[metric] = result["data"][0].get("values") or []
                posts = await fetch("facebook_page_posts", page_id, "posts", params={
                    "fields": "id,message,created_time,permalink_url,shares,comments.limit(0).summary(true),reactions.limit(0).summary(true)",
                    "since": since, "until": until, "limit": 50,
                }, access_token=page_token)
                channels.append({
                    "channel": "facebook", "account_id": page_id, "account_name": profile.get("name"),
                    "profile": {key: profile.get(key) for key in ("fan_count", "followers_count", "link", "verification_status")},
                    "daily_metrics": page_metrics,
                    "content": [self._normalise_meta_page_post(item) for item in posts.get("data", [])],
                })

            if instagram_id:
                profile = await fetch("instagram_profile", instagram_id, params={
                    "fields": "id,username,name,followers_count,follows_count,media_count,profile_picture_url",
                }, access_token=page_token)
                instagram_metrics: dict[str, Any] = {}
                for metric in ("views", "reach", "accounts_engaged", "total_interactions", "follows_and_unfollows", "profile_links_taps"):
                    result = await fetch(f"instagram_{metric}", instagram_id, "insights", params={
                        "metric": metric, "metric_type": "total_value", "period": "day", "since": since, "until": until,
                    }, access_token=page_token)
                    if result.get("data"):
                        instagram_metrics[metric] = result["data"][0].get("total_value") or result["data"][0].get("values") or {}
                media = await fetch("instagram_media", instagram_id, "media", params={
                    "fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
                    "since": since, "until": until, "limit": 50,
                }, access_token=page_token)
                channels.append({
                    "channel": "instagram", "account_id": instagram_id,
                    "account_name": profile.get("username") or profile.get("name"),
                    "profile": {key: profile.get(key) for key in ("followers_count", "follows_count", "media_count", "profile_picture_url")},
                    "period_metrics": instagram_metrics,
                    "content": [self._normalise_instagram_media(item) for item in media.get("data", [])],
                })

            if ad_account_id:
                object_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
                ad_insights = await fetch("meta_ad_insights", object_id, "insights", params={
                    "level": "campaign",
                    "fields": "account_id,account_name,campaign_id,campaign_name,objective,impressions,reach,clicks,spend,cpc,cpm,ctr,actions,action_values,purchase_roas",
                    "time_range": json.dumps({"since": since, "until": until}), "limit": 250,
                })
                channels.append({
                    "channel": "meta_ads", "account_id": ad_account_id,
                    "campaigns": [self._normalise_meta_ad_row(item) for item in ad_insights.get("data", [])],
                })

        return {
            "schema_version": "aion.marketing.channel_metrics.v1", "workspace_id": workspace_id,
            "provider": "meta", "range": {"since": since, "until": until}, "collected_at": _now(),
            "collected_by": acting_person_id, "channels": channels,
            "summary": self._summarise_meta_channels(channels), "source_receipts": receipts,
            "partial_errors": errors, "read_only": True, "external_writes_enabled": False,
        }

    @staticmethod
    def _normalise_meta_page_post(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "content_id": item.get("id"), "published_at": item.get("created_time"),
            "permalink": item.get("permalink_url"), "text": str(item.get("message") or "")[:1000],
            "reactions": int((item.get("reactions") or {}).get("summary", {}).get("total_count") or 0),
            "comments": int((item.get("comments") or {}).get("summary", {}).get("total_count") or 0),
            "shares": int((item.get("shares") or {}).get("count") or 0),
        }

    @staticmethod
    def _normalise_instagram_media(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "content_id": item.get("id"), "published_at": item.get("timestamp"),
            "permalink": item.get("permalink"), "text": str(item.get("caption") or "")[:1000],
            "media_type": item.get("media_type"), "media_product_type": item.get("media_product_type"),
            "likes": int(item.get("like_count") or 0), "comments": int(item.get("comments_count") or 0),
        }

    @staticmethod
    def _normalise_meta_ad_row(item: dict[str, Any]) -> dict[str, Any]:
        numeric = ("impressions", "reach", "clicks", "spend", "cpc", "cpm", "ctr")
        return {
            "campaign_id": item.get("campaign_id"), "campaign_name": item.get("campaign_name"),
            "objective": item.get("objective"),
            **{key: float(item.get(key) or 0) for key in numeric},
            "actions": item.get("actions") or [], "action_values": item.get("action_values") or [],
            "purchase_roas": item.get("purchase_roas") or [],
        }

    @staticmethod
    def _summarise_meta_channels(channels: list[dict[str, Any]]) -> dict[str, Any]:
        summary = {"facebook_posts": 0, "instagram_posts": 0, "meta_campaigns": 0,
                   "organic_interactions": 0, "ad_impressions": 0.0, "ad_clicks": 0.0, "ad_spend": 0.0}
        for channel in channels:
            if channel.get("channel") == "facebook":
                summary["facebook_posts"] = len(channel.get("content") or [])
                summary["organic_interactions"] += sum(
                    int(item.get("reactions") or 0) + int(item.get("comments") or 0) + int(item.get("shares") or 0)
                    for item in channel.get("content") or []
                )
            elif channel.get("channel") == "instagram":
                summary["instagram_posts"] = len(channel.get("content") or [])
                summary["organic_interactions"] += sum(
                    int(item.get("likes") or 0) + int(item.get("comments") or 0)
                    for item in channel.get("content") or []
                )
            elif channel.get("channel") == "meta_ads":
                campaigns = channel.get("campaigns") or []
                summary["meta_campaigns"] = len(campaigns)
                summary["ad_impressions"] += sum(float(item.get("impressions") or 0) for item in campaigns)
                summary["ad_clicks"] += sum(float(item.get("clicks") or 0) for item in campaigns)
                summary["ad_spend"] += sum(float(item.get("spend") or 0) for item in campaigns)
        return summary

    def select_accounts(self, workspace_id: str, provider: str, selection: dict[str, str], *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        record = self._load_record(workspace_id, provider, "connection")
        if record.get("status") != "connected": raise ValueError("provider_not_connected")
        accounts = record.get("accounts", []); valid = {str(x.get("id")) for x in accounts}
        if any(str(value) not in valid for value in selection.values() if value): raise ValueError("unknown_provider_account")
        for kind, value in selection.items():
            if value and kind != "primary" and not any(str(x.get("id")) == str(value) and str(x.get("kind")) == str(kind) for x in accounts):
                raise ValueError("provider_account_kind_mismatch")
        record.update({"selected_accounts": selection, "account_selection_updated_at": _now(), "account_selection_updated_by": acting_person_id})
        self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
        return self.status(workspace_id, provider)

    async def exam(self, workspace_id: str, provider: str, *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        record = self._load_record(workspace_id, provider, "connection"); token = MarketingTokenStore.load(workspace_id, provider)
        if not token.get("access_token"): raise ValueError("provider_not_connected")
        try:
            accounts = await self._discover(provider, token["access_token"])
            if provider == "meta":
                page_tokens = dict(token.get("page_tokens") or {})
                for account in accounts:
                    page_access_token = account.pop("_page_access_token", None)
                    if account.get("kind") == "page" and page_access_token:
                        page_tokens[str(account["id"])] = str(page_access_token)
                token["page_tokens"] = page_tokens
                MarketingTokenStore.save(workspace_id, provider, token)
            result = {"status": "passed", "read_only": True, "accounts_visible": len(accounts), "checked_at": _now(), "checked_by": acting_person_id}
            selected = dict(record.get("selected_accounts") or {})
            for kind in {str(account.get("kind") or "primary") for account in accounts}:
                candidates = [account for account in accounts if str(account.get("kind") or "primary") == kind]
                if len(candidates) == 1 and candidates[0].get("id"):
                    selected[kind] = str(candidates[0]["id"])
            record.update({"accounts": accounts, "selected_accounts": selected, "health": "healthy",
                           "last_exam": result, "reconnect_required": False})
        except Exception as exc:
            result = {"status": "failed", "read_only": True, "error": type(exc).__name__, "checked_at": _now(), "checked_by": acting_person_id}
            record.update({"health": "exam_failed", "last_exam": result, "reconnect_required": True})
        self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
        return result

    def disconnect(self, workspace_id: str, provider: str, *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        MarketingTokenStore.delete(workspace_id, provider)
        record = self._load_record(workspace_id, provider, "connection")
        record.update({"status": "disconnected", "accounts": [], "selected_accounts": {}, "secret_ref": None,
                       "disconnected_at": _now(), "disconnected_by": acting_person_id, "external_writes_enabled": False})
        self._write_record(workspace_id, provider, "connection", record, actor_id=acting_person_id)
        return self.status(workspace_id, provider)
