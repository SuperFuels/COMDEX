from __future__ import annotations

import argparse
import json
import ssl
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .opaque_relay import OpaqueRelayRouteAuthority, OpaqueRelayStore


class SelfHostedOpaqueRelayService:
    """Deployable TLS boundary around the operator-unreadable reference relay."""

    MAX_BODY_BYTES = OpaqueRelayRouteAuthority.MAX_ENVELOPE_BYTES * 2

    def __init__(
        self, *, tls_context: ssl.SSLContext, address: str = "127.0.0.1",
        port: int = 0, store: OpaqueRelayStore | None = None,
    ) -> None:
        if tls_context.minimum_version < ssl.TLSVersion.TLSv1_2:
            raise ValueError("The self-hosted relay requires TLS 1.2 or newer")
        self.tls_context = tls_context
        self.address = str(address)
        self.port = int(port)
        self.store = store or OpaqueRelayStore()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._rate_lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    @property
    def port_in_use(self) -> int:
        return self._server.server_port if self._server else self.port

    def _allow(self, address: str) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            recent = self._requests[address]
            while recent and now - recent[0] > 60:
                recent.popleft()
            if len(recent) >= 120:
                return False
            recent.append(now)
            return True

    def start(self) -> None:
        service = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "PilotOpaqueRelay/1"

            def _reply(self, value: dict[str, Any], status: int = 200) -> None:
                body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Strict-Transport-Security", "max-age=31536000")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)

            def _body(self) -> dict[str, Any]:
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise ValueError("The relay accepts JSON only")
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > service.MAX_BODY_BYTES:
                    raise ValueError("The relay request is outside its size limit")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError("The relay expected one JSON object")
                return value

            def do_GET(self) -> None:  # noqa: N802
                if self.path != "/health":
                    self._reply({"error": "not_found"}, 404)
                    return
                self._reply({
                    "ok": True, "schema_version": "pilot.self-hosted-opaque-relay.v1",
                    "operator_can_read_content": False, "decryption_keys_held": 0,
                    "queue_persistence": "ephemeral_bounded_transport",
                })

            def do_POST(self) -> None:  # noqa: N802
                if not service._allow(self.client_address[0]):
                    self._reply({"error": "rate_limited"}, 429)
                    return
                try:
                    body = self._body()
                    if self.path == "/v1/routes/register":
                        descriptor = dict(body.get("descriptor") or {})
                        public_key = str(body.get("mother_public_key") or "")
                        if not OpaqueRelayRouteAuthority.verify_descriptor(descriptor, public_key):
                            raise PermissionError("The mother relay descriptor is invalid")
                        service.store.register(descriptor, poll_token=str(body.get("poll_token") or ""))
                        result = {"registered": True, "opaque_route_id": descriptor["opaque_route_id"]}
                    elif self.path == "/v1/requests/submit":
                        result = service.store.submit(
                            dict(body.get("envelope") or {}),
                            submission_token=str(body.get("submission_token") or ""),
                        )
                    elif self.path == "/v1/requests/pull":
                        result = {"envelope": service.store.pull(
                            str(body.get("opaque_route_id") or ""),
                            poll_token=str(body.get("poll_token") or ""),
                        )}
                    elif self.path == "/v1/responses/submit":
                        service.store.respond(
                            dict(body.get("response") or {}),
                            poll_token=str(body.get("poll_token") or ""),
                        )
                        result = {"accepted": True}
                    elif self.path == "/v1/responses/receive":
                        result = {"response": service.store.receive(
                            str(body.get("opaque_route_id") or ""),
                            str(body.get("request_id") or ""),
                            submission_token=str(body.get("submission_token") or ""),
                        )}
                    elif self.path == "/v1/operator/status":
                        result = service.store.operator_view(str(body.get("opaque_route_id") or ""))
                    else:
                        self._reply({"error": "not_found"}, 404)
                        return
                    self._reply(result)
                except PermissionError as error:
                    self._reply({"error": str(error)}, 403)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    self._reply({"error": str(error)}, 400)
                except RuntimeError as error:
                    self._reply({"error": str(error)}, 409)

            def log_message(self, _format: str, *_args: Any) -> None:
                return

        self._server = ThreadingHTTPServer((self.address, self.port), Handler)
        self._server.socket = self.tls_context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, name="pilot-self-hosted-relay", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a customer-owned Pilot opaque relay")
    parser.add_argument("--certificate", required=True, help="TLS certificate chain in PEM format")
    parser.add_argument("--private-key", required=True, help="TLS private key in PEM format")
    parser.add_argument("--address", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.certificate, args.private_key)
    service = SelfHostedOpaqueRelayService(
        tls_context=context, address=args.address, port=args.port,
    )
    service.start()
    try:
        service._thread.join()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
