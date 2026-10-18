from __future__ import annotations

from types import SimpleNamespace

from fastapi import Request, Response

from backend.routes.auth import _set_session_cookie
from backend.utils.auth import AUTH_COOKIE_NAME, create_access_token, get_current_user


def _request(*, host: str = "testserver", cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie:
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https" if host != "testserver" else "http",
            "path": "/auth/profile",
            "raw_path": b"/auth/profile",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": (host, 443 if host != "testserver" else 80),
        }
    )


class _Database:
    def __init__(self, user):
        self.user = user

    def get(self, model, user_id):
        return self.user if user_id == self.user.id else None


def test_browser_session_cookie_is_httponly_samesite_and_secure_in_production(monkeypatch):
    monkeypatch.delenv("TESSARIS_AUTH_COOKIE_SECURE", raising=False)
    response = Response()

    _set_session_cookie(response, _request(host="api.tessaris.ai"), "secret-token")

    header = response.headers["set-cookie"]
    assert f"{AUTH_COOKIE_NAME}=secret-token" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header
    assert "Secure" in header
    assert "Path=/" in header


def test_local_node_cookie_can_run_on_loopback_without_weakening_production(monkeypatch):
    monkeypatch.delenv("TESSARIS_AUTH_COOKIE_SECURE", raising=False)
    response = Response()

    _set_session_cookie(response, _request(), "local-token")

    header = response.headers["set-cookie"]
    assert "HttpOnly" in header
    assert "Secure" not in header


def test_current_user_accepts_httponly_cookie_without_browser_bearer_storage():
    user = SimpleNamespace(id=42, role="buyer")
    token = create_access_token(subject=user.id, role=user.role)
    request = _request(cookie=f"{AUTH_COOKIE_NAME}={token}")

    resolved = get_current_user(request=request, token=None, db=_Database(user))

    assert resolved is user

