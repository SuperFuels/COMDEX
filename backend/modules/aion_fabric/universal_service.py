from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from .household import UniversalNodeAuthority
from .tv_canvas import _lan_address


class UniversalNodeService:
    """Bounded LAN API for mutual mother/node handshake and capability leases."""

    def __init__(self, authority: UniversalNodeAuthority, *, port: int = 8768, preferred_peer: str | None = None) -> None:
        self.authority = authority
        self.address = _lan_address(preferred_peer)
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._rate_lock = threading.Lock()
        self._requests: Dict[str, deque[float]] = defaultdict(deque)

    @property
    def public_url(self) -> str:
        port = self._server.server_port if self._server else self.port
        return f"http://{self.address}:{port}"

    def _allow(self, address: str) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            recent = self._requests[address]
            while recent and now - recent[0] > 60:
                recent.popleft()
            if len(recent) >= 30:
                return False
            recent.append(now)
            return True

    def start(self) -> bool:
        service = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, value: Dict[str, Any], status: int = 200) -> None:
                body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/identity":
                    self._json({
                        "schema_version": "aion.universal-node.identity.v1",
                        "node_id": service.authority.node_id,
                        "public_key": service.authority.identity.public_key_b64,
                        "handshake": "/handshake/begin",
                        "leases": "/lease",
                        "policy": {"new_mother_requires_local_confirmation": True, "maximum_lease_hours": 24},
                    })
                elif self.path == "/status":
                    self._json(service.authority.snapshot())
                else:
                    self._json({"error": "Not found"}, 404)

            def do_POST(self) -> None:  # noqa: N802
                if not service._allow(self.client_address[0]):
                    self._json({"error": "Universal-node handshake rate limit exceeded"}, 429)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 16_384 or "application/json" not in self.headers.get("Content-Type", ""):
                        raise ValueError("Invalid universal-node request")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("Universal-node request must be an object")
                    if self.path == "/handshake/begin":
                        result = service.authority.begin_handshake(mother_id=str(payload.get("mother_id") or ""), public_key=str(payload.get("public_key") or ""))
                    elif self.path == "/handshake/complete":
                        result = service.authority.complete_handshake(
                            handshake_id=str(payload.get("handshake_id") or ""),
                            confirmation_code=str(payload.get("confirmation_code") or ""),
                            mother_signature=str(payload.get("mother_signature") or ""),
                            approved_by="local_confirmation_code",
                        )
                    elif self.path == "/lease":
                        request = payload.get("request")
                        if not isinstance(request, dict):
                            raise ValueError("A signed lease request is required")
                        result = service.authority.accept_lease_request(request, str(payload.get("signature") or ""))
                    else:
                        self._json({"error": "Not found"}, 404)
                        return
                    self._json(result)
                except PermissionError as exc:
                    self._json({"error": str(exc)}, 403)
                except KeyError as exc:
                    self._json({"error": str(exc)}, 404)
                except (ValueError, json.JSONDecodeError) as exc:
                    self._json({"error": str(exc)}, 400)
                except Exception as exc:
                    self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

            def log_message(self, format: str, *args: object) -> None:
                return

        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        except OSError as exc:
            # The universal handshake endpoint is supplementary.  A previous
            # local Pilot process can still own this shared LAN port while the
            # dashboard is being restarted; that must never prevent Pilot,
            # its microphone, or TV recovery from starting.
            if getattr(exc, "errno", None) == 48:
                self._server = None
                return False
            raise
        self._thread = threading.Thread(target=self._server.serve_forever, name="aion-universal-node", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=3)
