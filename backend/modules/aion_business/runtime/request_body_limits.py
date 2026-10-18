"""Pre-routing request-body limits for externally reachable trust boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class ScopedRequestBodyLimitMiddleware:
    """Reject oversized bodies before FastAPI or Pydantic parses them.

    Snapshot verify/import routes are intentionally excluded because their
    signed archives are streamed directly to a private temporary file by the
    GlyphChain administration dependency.
    """

    LEGAL_GENERAL_BYTES = 40 * 1024 * 1024
    LEGAL_SIGNER_BYTES = 64 * 1024
    RESEND_WEBHOOK_BYTES = 1_000_000
    GLYPHCHAIN_ADMIN_BYTES = 4 * 1024 * 1024
    P2P_BYTES = 4 * 1024 * 1024
    ACCOUNT_DESCRIPTOR_BYTES = 256 * 1024
    A2A_BYTES = 64 * 1024

    def __init__(self, app) -> None:
        self.app = app

    @classmethod
    def limit_for_path(cls, path: str) -> int | None:
        value = str(path or "")
        if value == "/api/aion/business/legal-signing/webhooks/resend":
            return cls.RESEND_WEBHOOK_BYTES
        if value.startswith("/api/aion/business/legal-signing/sign/"):
            return cls.LEGAL_SIGNER_BYTES
        if value.startswith("/api/aion/business/legal-signing/"):
            return cls.LEGAL_GENERAL_BYTES
        if value in {
            "/api/aion/business/glyphchain-admin/snapshot/verify",
            "/api/aion/business/glyphchain-admin/snapshot/import",
        }:
            return None
        if value.startswith("/api/aion/business/glyphchain-admin/"):
            return cls.GLYPHCHAIN_ADMIN_BYTES
        if value.startswith("/api/p2p/"):
            return cls.P2P_BYTES
        if value.startswith("/v1/accounts/") and value.endswith("/descriptor"):
            return cls.ACCOUNT_DESCRIPTOR_BYTES
        if value.startswith("/api/a2a/v1/") or value.startswith("/api/aion/business/a2a/"):
            return cls.A2A_BYTES
        return None

    async def __call__(self, scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        maximum = self.limit_for_path(str(scope.get("path") or ""))
        if maximum is None:
            await self.app(scope, receive, send)
            return

        declared = self._content_length(scope)
        if declared is not None and declared > maximum:
            await self._reject(send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            if message.get("type") != "http.request":
                continue
            chunk = bytes(message.get("body") or b"")
            if len(body) + len(chunk) > maximum:
                await self._reject(send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay() -> dict[str, Any]:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    def _content_length(scope) -> int | None:
        for name, value in scope.get("headers") or []:
            if bytes(name).lower() != b"content-length":
                continue
            try:
                parsed = int(bytes(value).decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                return None
            return parsed if parsed >= 0 else None
        return None

    @staticmethod
    async def _reject(send: Send) -> None:
        payload = b'{"detail":"request_body_too_large"}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        })
        await send({"type": "http.response.body", "body": payload, "more_body": False})
