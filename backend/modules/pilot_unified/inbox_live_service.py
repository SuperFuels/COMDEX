from __future__ import annotations

import asyncio
import json
import ssl
import threading
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity

from .inbox import UnifiedInbox


class UnifiedInboxLiveService:
    """TLS WebSocket stream authenticated by the phone possession key and lease."""

    def __init__(
        self,
        inbox: UnifiedInbox,
        *,
        tls_context: ssl.SSLContext,
        address: str = "0.0.0.0",
        port: int = 8771,
        allowed_origins: tuple[str, ...] = (),
    ) -> None:
        if tls_context.minimum_version < ssl.TLSVersion.TLSv1_2:
            raise ValueError("Pilot live Inbox requires TLS 1.2 or newer")
        self.inbox = inbox
        self.tls_context = tls_context
        self.address = address
        self.port = int(port)
        self.allowed_origins = tuple(origin.rstrip("/") for origin in allowed_origins)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Any = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._start_error: BaseException | None = None

    @property
    def port_in_use(self) -> int:
        if self._server and self._server.sockets:
            return int(self._server.sockets[0].getsockname()[1])
        return self.port

    @property
    def public_url(self) -> str:
        return f"wss://{self.address}:{self.port_in_use}/v1/inbox/live"

    @staticmethod
    def _authenticate(inbox: UnifiedInbox, payload: dict[str, Any]) -> tuple[str, int]:
        request = dict(payload.get("request") or {})
        required = {"purpose", "persona_id", "device_id", "lease_id", "nonce", "after_revision"}
        if set(request) != required or request.get("purpose") != "open_inbox_stream":
            raise ValueError("The live Inbox request is malformed")
        if not isinstance(request.get("after_revision"), int) or int(request["after_revision"]) < 0:
            raise ValueError("The live Inbox cursor is invalid")
        nonce = str(request.get("nonce") or "")
        if len(nonce) < 16 or len(nonce) > 200:
            raise ValueError("The live Inbox nonce is invalid")
        certificate = dict(payload.get("certificate") or {})
        lease = dict(payload.get("lease") or {})
        verified = inbox.pairing.validate(certificate=certificate, lease=lease, required_scope="inbox.read")
        if (
            request.get("persona_id") != verified["persona_id"]
            or request.get("device_id") != verified["device_id"]
            or request.get("lease_id") != lease.get("lease_id")
        ):
            raise PermissionError("The live Inbox connection does not match this phone")
        if not DeviceIdentity.verify(
            str(certificate.get("phone_public_key") or ""),
            canonical_bytes(request),
            str(payload.get("phone_signature") or ""),
        ):
            raise PermissionError("This phone did not sign the live Inbox connection")
        return str(verified["persona_id"]), int(request["after_revision"])

    async def _handler(self, websocket: Any) -> None:
        if websocket.request.path != "/v1/inbox/live":
            await websocket.close(code=1008, reason="Unknown Pilot live route")
            return
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=6)
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > 64 * 1024:
                raise ValueError("Pilot expected one small signed live request")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Pilot expected one signed live request")
            persona_id, cursor = self._authenticate(self.inbox, payload)
        except (asyncio.TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError, PermissionError) as exc:
            await websocket.close(code=1008, reason=str(exc)[:120])
            return

        await websocket.send(json.dumps({
            "type": "inbox.ready",
            "persona_id": persona_id,
            "resumed_from_revision": cursor,
            "duplicates_replayed": 0,
        }, separators=(",", ":")))
        last_revision = cursor
        try:
            while True:
                stream = self.inbox.stream(
                    persona_id=persona_id,
                    certificate=dict(payload["certificate"]),
                    lease=dict(payload["lease"]),
                )
                revision = int(stream.get("revision") or 0)
                if revision > last_revision or last_revision == 0:
                    await websocket.send(json.dumps({"type": "inbox.snapshot", "stream": stream}, separators=(",", ":")))
                    last_revision = revision
                try:
                    incoming = await asyncio.wait_for(websocket.recv(), timeout=0.75)
                    if incoming == "ping":
                        await websocket.send(json.dumps({"type": "inbox.heartbeat", "revision": last_revision}, separators=(",", ":")))
                except asyncio.TimeoutError:
                    pass
        except ConnectionClosed:
            return
        except PermissionError as exc:
            await websocket.close(code=1008, reason=str(exc)[:120])

    async def _serve(self) -> None:
        try:
            self._server = await websockets.serve(
                self._handler,
                self.address,
                self.port,
                ssl=self.tls_context,
                origins=self.allowed_origins,
                compression=None,
                max_size=64 * 1024,
                max_queue=8,
                ping_interval=20,
                ping_timeout=20,
            )
        except BaseException as exc:
            self._start_error = exc
        finally:
            self._ready.set()
        if self._server:
            await self._server.wait_closed()

    def start(self) -> None:
        if self._thread:
            return
        self._ready.clear()
        self._start_error = None

        def run() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._serve())
            finally:
                loop.close()

        self._thread = threading.Thread(target=run, name="pilot-unified-inbox-live", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Pilot live Inbox did not start")
        if self._start_error:
            raise RuntimeError(f"Pilot live Inbox could not start: {type(self._start_error).__name__}") from self._start_error

    def stop(self) -> None:
        if self._loop and self._server:
            self._loop.call_soon_threadsafe(self._server.close)
        if self._thread:
            self._thread.join(timeout=4)
        self._server = None
        self._thread = None
        self._loop = None
