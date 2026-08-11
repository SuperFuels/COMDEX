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
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


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
        "scopes": {"analytics": ["pages_show_list", "pages_read_engagement", "read_insights", "instagram_basic"],
                   "organic": ["pages_manage_posts", "instagram_content_publish"],
                   "advertising": ["ads_read", "ads_management", "business_management"]},
    },
    "google_ads": {
        "label": "Google Ads", "client_id": "GOOGLE_MARKETING_CLIENT_ID", "client_secret": "GOOGLE_MARKETING_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
        "scopes": {"analytics": ["https://www.googleapis.com/auth/adwords"], "organic": [], "advertising": []},
    },
    "youtube": {
        "label": "YouTube", "client_id": "GOOGLE_MARKETING_CLIENT_ID", "client_secret": "GOOGLE_MARKETING_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
        "scopes": {"analytics": ["https://www.googleapis.com/auth/youtube.readonly"],
                   "organic": ["https://www.googleapis.com/auth/youtube.upload"], "advertising": []},
    },
    "linkedin": {
        "label": "LinkedIn", "client_id": "LINKEDIN_CLIENT_ID", "client_secret": "LINKEDIN_CLIENT_SECRET",
        "authorize": "https://www.linkedin.com/oauth/v2/authorization", "token": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": {"analytics": ["openid", "profile"], "organic": ["w_member_social"], "advertising": []},
    },
    "tiktok": {
        "label": "TikTok", "client_id": "TIKTOK_CLIENT_KEY", "client_secret": "TIKTOK_CLIENT_SECRET",
        "authorize": "https://www.tiktok.com/v2/auth/authorize/", "token": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": {"analytics": ["user.info.basic", "video.list"], "organic": ["video.publish"], "advertising": []},
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


class MarketingConnectionService:
    def __init__(self, *, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("AION_PUBLIC_BACKEND_URL") or "http://127.0.0.1:8080").rstrip("/")

    def _dir(self, workspace_id: str, provider: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(canonical_business_id(workspace_id)) / "integrations" / "marketing" / provider
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str, provider: str) -> Path:
        return self._dir(workspace_id, provider) / "connection.json"

    def _pending(self, workspace_id: str, provider: str) -> Path:
        return self._dir(workspace_id, provider) / "pending.json"

    @staticmethod
    def _credentials(provider: str) -> tuple[str, str]:
        spec = PROVIDERS[provider]
        client_id = str(os.getenv(spec["client_id"]) or "").strip()
        client_secret = str(os.getenv(spec["client_secret"]) or "").strip()
        if provider in {"google_ads", "youtube"}:
            client_id = client_id or str(os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or "").strip()
            client_secret = client_secret or str(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
        return client_id, client_secret

    @staticmethod
    def _scopes(provider: str, tier: str) -> list[str]:
        levels = ["analytics"] + (["organic"] if tier in {"organic", "advertising"} else []) + (["advertising"] if tier == "advertising" else [])
        return list(dict.fromkeys(scope for level in levels for scope in PROVIDERS[provider]["scopes"][level]))

    def catalog(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.status(workspace_id, provider) for provider in PROVIDERS]

    def status(self, workspace_id: str, provider: str) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError("unsupported_marketing_provider")
        value = _read(self._path(workspace_id, provider), {})
        client_id, client_secret = self._credentials(provider)
        configured = bool(client_id and client_secret)
        platform_requirements: list[str] = []
        if provider == "google_ads" and not str(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") or "").strip():
            configured = False; platform_requirements.append("GOOGLE_ADS_DEVELOPER_TOKEN")
        return {
            "provider": provider, "label": PROVIDERS[provider]["label"],
            "configured": configured, "platform_requirements": platform_requirements,
            "status": value.get("status", "not_connected"),
            "connected": value.get("status") == "connected", "permission_tier": value.get("permission_tier", "analytics"),
            "granted_scopes": value.get("granted_scopes", []), "accounts": value.get("accounts", []),
            "selected_accounts": value.get("selected_accounts", {}), "connected_at": value.get("connected_at"),
            "connected_by": value.get("connected_by"), "last_exam": value.get("last_exam"),
            "health": value.get("health", "not_examined"), "reconnect_required": bool(value.get("reconnect_required")),
            "secret_storage": value.get("secret_ref", "") .split("://", 1)[0] if value.get("secret_ref") else None,
            "external_writes_enabled": False,
            "boundary": "Connection and read-only validation only; publishing and spend require separate exact approval.",
        }

    def begin(self, workspace_id: str, provider: str, *, tier: str, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS or tier not in {"analytics", "organic", "advertising"}:
            raise ValueError("invalid_marketing_connection_request")
        client_id, client_secret = self._credentials(provider)
        if not client_id or not client_secret:
            return {"status": "platform_configuration_required", "provider": provider,
                    "missing": [name for name, value in ((PROVIDERS[provider]["client_id"], client_id), (PROVIDERS[provider]["client_secret"], client_secret)) if not value]}
        if provider == "google_ads" and not str(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") or "").strip():
            return {"status": "platform_configuration_required", "provider": provider,
                    "missing": ["GOOGLE_ADS_DEVELOPER_TOKEN"]}
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
        redirect_uri = f"{self.base_url}/api/aion/marketing/connections/{provider}/callback"
        pending = {"workspace_id": canonical_business_id(workspace_id), "provider": provider, "state": state,
                   "verifier": verifier, "tier": tier, "acting_person_id": acting_person_id,
                   "redirect_uri": redirect_uri, "expires_at": (datetime.now(UTC) + timedelta(minutes=15)).isoformat()}
        _write(self._pending(workspace_id, provider), pending)
        spec = PROVIDERS[provider]
        version = str(os.getenv("META_GRAPH_API_VERSION") or "v23.0")
        params: dict[str, Any] = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state,
                                  "scope": " ".join(self._scopes(provider, tier)), "code_challenge": challenge, "code_challenge_method": "S256"}
        if provider in {"google_ads", "youtube"}:
            params.update({"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"})
        if provider == "tiktok":
            params["client_key"] = params.pop("client_id"); params["scope"] = ",".join(self._scopes(provider, tier))
        return {"status": "authorization_required", "provider": provider,
                "authorization_url": spec["authorize"].format(version=version) + "?" + urlencode(params),
                "expires_in_seconds": 900, "permission_tier": tier}

    def _locate_pending(self, provider: str, state: str) -> dict[str, Any]:
        root = AIONBusinessPaths.BUSINESS_CONTAINERS
        for path in root.glob(f"*/integrations/marketing/{provider}/pending.json"):
            value = _read(path, {})
            if secrets.compare_digest(str(value.get("state") or ""), state):
                value["_path"] = str(path)
                return value
        raise ValueError("oauth_state_invalid_or_expired")

    async def complete(self, provider: str, *, state: str, code: str) -> dict[str, Any]:
        pending = self._locate_pending(provider, state)
        if datetime.fromisoformat(pending["expires_at"]) < datetime.now(UTC):
            raise ValueError("oauth_state_expired")
        client_id, client_secret = self._credentials(provider)
        spec = PROVIDERS[provider]; version = str(os.getenv("META_GRAPH_API_VERSION") or "v23.0")
        body = {"client_id": client_id, "client_secret": client_secret, "code": code,
                "redirect_uri": pending["redirect_uri"], "grant_type": "authorization_code", "code_verifier": pending["verifier"]}
        if provider == "tiktok":
            body["client_key"] = body.pop("client_id"); body["client_secret"] = body.pop("client_secret")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(spec["token"].format(version=version), data=body)
            response.raise_for_status(); token = response.json()
        if "access_token" not in token:
            raise ValueError("provider_did_not_return_access_token")
        if token.get("expires_in"):
            token["expires_at"] = (datetime.now(UTC) + timedelta(seconds=int(token["expires_in"]))).isoformat()
        workspace_id = pending["workspace_id"]
        secret_ref = MarketingTokenStore.save(workspace_id, provider, token)
        accounts = await self._discover(provider, token["access_token"])
        record = {"status": "connected", "provider": provider, "permission_tier": pending["tier"],
                  "granted_scopes": str(token.get("scope") or " ".join(self._scopes(provider, pending["tier"]))).replace(",", " ").split(),
                  "accounts": accounts, "selected_accounts": {}, "connected_at": _now(),
                  "connected_by": pending["acting_person_id"], "secret_ref": secret_ref, "health": "connected_not_examined"}
        _write(self._path(workspace_id, provider), record)
        Path(pending["_path"]).unlink(missing_ok=True)
        return self.status(workspace_id, provider)

    async def _discover(self, provider: str, access_token: str) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}; version = str(os.getenv("META_GRAPH_API_VERSION") or "v23.0")
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            if provider == "meta":
                page_response = await client.get(f"https://graph.facebook.com/{version}/me/accounts", params={"fields": "id,name,tasks"})
                page_response.raise_for_status(); pages = page_response.json().get("data", [])
                accounts = [{"id": x.get("id"), "name": x.get("name"), "kind": "page"} for x in pages]
                for page in pages:
                    ig_response = await client.get(f"https://graph.facebook.com/{version}/{page.get('id')}", params={"fields": "instagram_business_account{id,username,name}"})
                    if ig_response.is_success:
                        ig = ig_response.json().get("instagram_business_account") or {}
                        if ig.get("id"):
                            accounts.append({"id": ig["id"], "name": ig.get("username") or ig.get("name") or ig["id"], "kind": "instagram", "page_id": page.get("id")})
                ads_response = await client.get(f"https://graph.facebook.com/{version}/me/adaccounts", params={"fields": "id,name,account_status,currency,timezone_name"})
                if ads_response.is_success:
                    accounts.extend({"id": x.get("id"), "name": x.get("name") or x.get("id"), "kind": "ad_account",
                                     "currency": x.get("currency"), "account_status": x.get("account_status")} for x in ads_response.json().get("data", []))
                return accounts
            if provider == "google_ads":
                api_version = str(os.getenv("GOOGLE_ADS_API_VERSION") or "v24")
                response = await client.get(f"https://googleads.googleapis.com/{api_version}/customers:listAccessibleCustomers",
                                            headers={**headers, "developer-token": str(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") or "")})
                return [{"id": str(x).split("/")[-1], "name": str(x), "kind": "customer"} for x in response.json().get("resourceNames", [])]
            if provider == "youtube":
                data = (await client.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "id,snippet", "mine": "true"})).json()
                return [{"id": x.get("id"), "name": (x.get("snippet") or {}).get("title"), "kind": "channel"} for x in data.get("items", [])]
            if provider == "linkedin":
                data = (await client.get("https://api.linkedin.com/v2/userinfo")).json()
                return [{"id": data.get("sub"), "name": data.get("name"), "kind": "member"}]
            data = (await client.get("https://open.tiktokapis.com/v2/user/info/", params={"fields": "open_id,display_name"})).json().get("data", {}).get("user", {})
            return [{"id": data.get("open_id"), "name": data.get("display_name"), "kind": "creator"}]

    def select_accounts(self, workspace_id: str, provider: str, selection: dict[str, str], *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        record = _read(self._path(workspace_id, provider), {})
        if record.get("status") != "connected": raise ValueError("provider_not_connected")
        accounts = record.get("accounts", []); valid = {str(x.get("id")) for x in accounts}
        if any(str(value) not in valid for value in selection.values() if value): raise ValueError("unknown_provider_account")
        for kind, value in selection.items():
            if value and kind != "primary" and not any(str(x.get("id")) == str(value) and str(x.get("kind")) == str(kind) for x in accounts):
                raise ValueError("provider_account_kind_mismatch")
        record.update({"selected_accounts": selection, "account_selection_updated_at": _now(), "account_selection_updated_by": acting_person_id})
        _write(self._path(workspace_id, provider), record)
        return self.status(workspace_id, provider)

    async def exam(self, workspace_id: str, provider: str, *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        record = _read(self._path(workspace_id, provider), {}); token = MarketingTokenStore.load(workspace_id, provider)
        if not token.get("access_token"): raise ValueError("provider_not_connected")
        try:
            accounts = await self._discover(provider, token["access_token"])
            result = {"status": "passed", "read_only": True, "accounts_visible": len(accounts), "checked_at": _now(), "checked_by": acting_person_id}
            record.update({"accounts": accounts, "health": "healthy", "last_exam": result, "reconnect_required": False})
        except Exception as exc:
            result = {"status": "failed", "read_only": True, "error": type(exc).__name__, "checked_at": _now(), "checked_by": acting_person_id}
            record.update({"health": "exam_failed", "last_exam": result, "reconnect_required": True})
        _write(self._path(workspace_id, provider), record)
        return result

    def disconnect(self, workspace_id: str, provider: str, *, acting_person_id: str) -> dict[str, Any]:
        if provider not in PROVIDERS: raise ValueError("unsupported_marketing_provider")
        MarketingTokenStore.delete(workspace_id, provider)
        record = _read(self._path(workspace_id, provider), {})
        record.update({"status": "disconnected", "accounts": [], "selected_accounts": {}, "secret_ref": None,
                       "disconnected_at": _now(), "disconnected_by": acting_person_id, "external_writes_enabled": False})
        _write(self._path(workspace_id, provider), record)
        return self.status(workspace_id, provider)
