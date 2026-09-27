from __future__ import annotations

import json
import ipaddress
import secrets
import ssl
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, TYPE_CHECKING

from .pairing import MobilePairingAuthority

if TYPE_CHECKING:
    from .handoff import TrustedHandoffAuthority
    from .inbox import UnifiedInbox
    from .personal import PersonalPilotProjection
    from .workspace_gateway import ProviderIndependentWorkspaceGateway


class MobilePairingService:
    """Small HTTPS API for local pairing; never returns the mother-side code."""

    def __init__(
        self,
        authority: MobilePairingAuthority,
        *,
        tls_context: ssl.SSLContext,
        confirmation_presenter: Callable[[dict[str, Any]], None],
        address: str = "0.0.0.0",
        port: int = 8770,
        allowed_origins: tuple[str, ...] = (),
        inbox: UnifiedInbox | None = None,
        default_persona_id: str | None = None,
        live_inbox_url: str | None = None,
        personal: PersonalPilotProjection | None = None,
        workspace_gateway: ProviderIndependentWorkspaceGateway | None = None,
        trusted_handoffs: TrustedHandoffAuthority | None = None,
    ) -> None:
        if tls_context.minimum_version < ssl.TLSVersion.TLSv1_2:
            raise ValueError("Pilot pairing requires TLS 1.2 or newer")
        self.authority = authority
        self.tls_context = tls_context
        self.confirmation_presenter = confirmation_presenter
        self.address = address
        self.port = int(port)
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins)
        self.inbox = inbox
        self.default_persona_id = str(default_persona_id or "")
        self.live_inbox_url = str(live_inbox_url or "")
        self.personal = personal
        self.workspace_gateway = workspace_gateway
        self.trusted_handoffs = trusted_handoffs
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._rate_lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

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

    @staticmethod
    def _is_trusted_local_address(address: str) -> bool:
        try:
            value = ipaddress.ip_address(str(address).split("%", 1)[0])
            local_networks = (
                ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("172.16.0.0/12"),
                ipaddress.ip_network("192.168.0.0/16"), ipaddress.ip_network("127.0.0.0/8"),
                ipaddress.ip_network("169.254.0.0/16"), ipaddress.ip_network("fc00::/7"),
                ipaddress.ip_network("fe80::/10"), ipaddress.ip_network("::1/128"),
            )
            return any(value.version == network.version and value in network for network in local_networks)
        except ValueError:
            return False

    @property
    def port_in_use(self) -> int:
        return self._server.server_port if self._server else self.port

    def start(self) -> None:
        service = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "PilotPairing/1"

            def _origin(self) -> str | None:
                origin = str(self.headers.get("Origin") or "").rstrip("/")
                if not origin:
                    return None
                if origin not in service.allowed_origins:
                    raise PermissionError("This app is not allowed to connect to this Pilot")
                return origin

            def _headers(self, status: int, length: int, *, origin: str | None = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Strict-Transport-Security", "max-age=31536000")
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                if origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.end_headers()

            def _json(self, value: dict[str, Any], status: int = 200, *, origin: str | None = None) -> None:
                body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self._headers(status, len(body), origin=origin)
                self.wfile.write(body)

            def _body(self) -> dict[str, Any]:
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                length = int(self.headers.get("Content-Length", "0"))
                maximum = 2_100_000 if self.path in {
                    "/v1/inbox/attachments/send", "/v1/inbox/voice-notes/send", "/v1/network/handoffs/send",
                } else 32 * 1024
                if content_type != "application/json" or length <= 0 or length > maximum:
                    raise ValueError("Pilot expected a small secure connection request")
                try:
                    value = json.loads(self.rfile.read(length))
                except json.JSONDecodeError:
                    raise ValueError("Pilot could not read that connection request") from None
                if not isinstance(value, dict):
                    raise ValueError("Pilot expected one connection request")
                return value

            def do_OPTIONS(self) -> None:  # noqa: N802
                try:
                    origin = self._origin()
                    if not origin:
                        raise PermissionError("Cross-origin connection is not enabled")
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.send_header("Access-Control-Max-Age", "600")
                    self.send_header("Vary", "Origin")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                except PermissionError as exc:
                    self._json({"error": str(exc)}, 403)

            def do_GET(self) -> None:  # noqa: N802
                try:
                    origin = self._origin()
                    if self.path == "/.well-known/pilot-mother":
                        self._json({
                            "descriptor": service.authority.mother_descriptor(),
                            "trust_words": service.authority.trust_words(),
                            "pairing_path": "/v1/pairing/challenges",
                            "inbox_websocket_url": service.live_inbox_url or None,
                        }, origin=origin)
                    elif self.path == "/health":
                        self._json({"ok": True, "service": "pilot-mobile-pairing", "private_keys_exposed": False}, origin=origin)
                    elif self.path.startswith("/v1/public/invitations/"):
                        if service.personal is None or service.personal.communication is None:
                            raise RuntimeError("Pilot invitations are not active on this mother")
                        token = self.path.removeprefix("/v1/public/invitations/").split("?", 1)[0]
                        self._json(service.personal.communication.inspect_invitation(token), origin=origin)
                    else:
                        self._json({"error": "Not found"}, 404, origin=origin)
                except PermissionError as exc:
                    self._json({"error": str(exc)}, 403)

            def do_POST(self) -> None:  # noqa: N802
                origin: str | None = None
                try:
                    if not service._allow(self.client_address[0]):
                        raise RuntimeError("Too many connection attempts; wait a moment")
                    origin = self._origin()
                    body = self._body()
                    if self.path == "/v1/pairing/challenges":
                        result = service.authority.begin_pairing(
                            persona_id=str(body.get("persona_id") or service.default_persona_id),
                            device_label=str(body.get("device_label") or ""),
                            phone_public_key=str(body.get("phone_public_key") or ""),
                            requested_scopes=list(body.get("requested_scopes") or []),
                        )
                        service.confirmation_presenter(dict(result["local_confirmation"]))
                        self._json(dict(result["phone_challenge"]), 201, origin=origin)
                    elif self.path == "/v1/pairing/complete":
                        result = service.authority.complete_pairing(
                            challenge_id=str(body.get("challenge_id") or ""),
                            confirmation_code=str(body.get("confirmation_code") or ""),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/leases/renew":
                        request = dict(body.get("request") or {})
                        result = service.authority.renew_lease(
                            request,
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/stream":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.stream(
                            persona_id=str(body.get("persona_id") or ""),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/network/handoffs/snapshot":
                        if service.trusted_handoffs is None:
                            raise RuntimeError("The trusted Pilot network is not active on this mother")
                        result = service.trusted_handoffs.snapshot(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/network/handoffs/send":
                        if service.trusted_handoffs is None:
                            raise RuntimeError("The trusted Pilot network is not active on this mother")
                        result = service.trusted_handoffs.send(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/network/handoffs/tasks/approve":
                        if service.trusted_handoffs is None:
                            raise RuntimeError("The trusted Pilot network is not active on this mother")
                        result = service.trusted_handoffs.approve_task(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/personal/snapshot":
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        result = service.personal.snapshot(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/personal/reminders/create":
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        result = service.personal.create_reminder(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/personal/reminders/transition":
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        result = service.personal.transition_reminder(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/calendar/snapshot",
                        "/v1/personal/calendar/availability",
                        "/v1/personal/calendar/prepare",
                        "/v1/personal/calendar/decide",
                        "/v1/personal/calendar/execute",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/calendar/snapshot": service.personal.calendar_snapshot,
                            "/v1/personal/calendar/availability": service.personal.calendar_availability,
                            "/v1/personal/calendar/prepare": service.personal.prepare_calendar,
                            "/v1/personal/calendar/decide": service.personal.decide_calendar,
                            "/v1/personal/calendar/execute": service.personal.execute_calendar,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/workspaces/spaces/snapshot",
                        "/v1/workspaces/surfaces/open",
                        "/v1/workspaces/invitations/snapshot",
                        "/v1/workspaces/invitations/respond",
                        "/v1/workspaces/surfaces/read",
                        "/v1/workspaces/conversations/turn",
                        "/v1/workspaces/conversations/history",
                        "/v1/workspaces/executive-channels/status",
                        "/v1/workspaces/executive-channels/history",
                        "/v1/workspaces/executive-channels/turn",
                        "/v1/workspaces/custom-departments/create",
                        "/v1/workspaces/custom-departments/delete",
                        "/v1/workspaces/cards/snapshot",
                        "/v1/workspaces/cards/action",
                        "/v1/workspaces/signoffs/prepare",
                        "/v1/workspaces/signoffs/snapshot",
                        "/v1/workspaces/signoffs/decide",
                        "/v1/workspaces/files/reference",
                        "/v1/workspaces/files/references",
                        "/v1/workspaces/handoffs/desktop",
                        "/v1/workspaces/commercial/snapshot",
                        "/v1/workspaces/commercial/action",
                        "/v1/workspaces/work-schedule/snapshot",
                        "/v1/workspaces/work-schedule/action",
                    }:
                        if service.workspace_gateway is None:
                            raise RuntimeError("The Workspace Gateway is not active on this mother")
                        operation = {
                            "/v1/workspaces/spaces/snapshot": service.workspace_gateway.mobile_spaces_snapshot,
                            "/v1/workspaces/surfaces/open": service.workspace_gateway.mobile_open_surface,
                            "/v1/workspaces/invitations/snapshot": service.workspace_gateway.invitation_snapshot,
                            "/v1/workspaces/invitations/respond": service.workspace_gateway.respond_to_invitation,
                            "/v1/workspaces/surfaces/read": service.workspace_gateway.mobile_read_surface,
                            "/v1/workspaces/conversations/turn": service.workspace_gateway.mobile_conversation_turn,
                            "/v1/workspaces/conversations/history": service.workspace_gateway.mobile_conversation_history,
                            "/v1/workspaces/executive-channels/status": service.workspace_gateway.mobile_executive_channels_status,
                            "/v1/workspaces/executive-channels/history": service.workspace_gateway.mobile_executive_channel_history,
                            "/v1/workspaces/executive-channels/turn": service.workspace_gateway.mobile_executive_channel_turn,
                            "/v1/workspaces/custom-departments/create": service.workspace_gateway.mobile_custom_department_create,
                            "/v1/workspaces/custom-departments/delete": service.workspace_gateway.mobile_custom_department_delete,
                            "/v1/workspaces/cards/snapshot": service.workspace_gateway.mobile_review_cards,
                            "/v1/workspaces/cards/action": service.workspace_gateway.mobile_review_card_action,
                            "/v1/workspaces/signoffs/prepare": service.workspace_gateway.mobile_prepare_signoff,
                            "/v1/workspaces/signoffs/snapshot": service.workspace_gateway.mobile_signoff_snapshot,
                            "/v1/workspaces/signoffs/decide": service.workspace_gateway.mobile_decide_signoff,
                            "/v1/workspaces/files/reference": service.workspace_gateway.mobile_create_file_reference,
                            "/v1/workspaces/files/references": service.workspace_gateway.mobile_file_references,
                            "/v1/workspaces/handoffs/desktop": service.workspace_gateway.mobile_prepare_desktop_handoff,
                            "/v1/workspaces/commercial/snapshot": service.workspace_gateway.mobile_commercial_snapshot,
                            "/v1/workspaces/commercial/action": service.workspace_gateway.mobile_commercial_action,
                            "/v1/workspaces/work-schedule/snapshot": service.workspace_gateway.mobile_work_schedule_snapshot,
                            "/v1/workspaces/work-schedule/action": service.workspace_gateway.mobile_work_schedule_action,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}), certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}), phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/contacts/snapshot",
                        "/v1/personal/contacts/save",
                        "/v1/personal/contacts/remove",
                        "/v1/personal/contacts/resolve",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/contacts/snapshot": service.personal.contacts_snapshot,
                            "/v1/personal/contacts/save": service.personal.save_contact,
                            "/v1/personal/contacts/remove": service.personal.remove_contact,
                            "/v1/personal/contacts/resolve": service.personal.resolve_contact,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/communication/snapshot",
                        "/v1/personal/communication/prepare",
                        "/v1/personal/communication/decide",
                        "/v1/personal/communication/execute",
                        "/v1/personal/communication/convert",
                        "/v1/personal/communication/follow-up",
                        "/v1/personal/communication/call",
                        "/v1/personal/communication/invite",
                        "/v1/personal/communication/invite/claim",
                        "/v1/personal/communication/protect",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/communication/snapshot": service.personal.communication_snapshot,
                            "/v1/personal/communication/prepare": service.personal.prepare_communication,
                            "/v1/personal/communication/decide": service.personal.decide_communication,
                            "/v1/personal/communication/execute": service.personal.execute_communication,
                            "/v1/personal/communication/convert": service.personal.convert_received_communication,
                            "/v1/personal/communication/follow-up": service.personal.schedule_communication_follow_up,
                            "/v1/personal/communication/call": service.personal.prepare_communication_call,
                            "/v1/personal/communication/invite": service.personal.create_communication_invitation,
                            "/v1/personal/communication/invite/claim": service.personal.claim_communication_invitation,
                            "/v1/personal/communication/protect": service.personal.protect_communication_contact,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/services/snapshot",
                        "/v1/personal/services/prepare",
                        "/v1/personal/services/update",
                        "/v1/personal/services/decide",
                        "/v1/personal/services/execute",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/services/snapshot": service.personal.service_snapshot,
                            "/v1/personal/services/prepare": service.personal.prepare_service_action,
                            "/v1/personal/services/update": service.personal.update_service_details,
                            "/v1/personal/services/decide": service.personal.decide_service_action,
                            "/v1/personal/services/execute": service.personal.execute_service_action,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/library/snapshot",
                        "/v1/personal/library/claim",
                        "/v1/personal/library/delete",
                        "/v1/personal/library/continue",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/library/snapshot": service.personal.library_snapshot,
                            "/v1/personal/library/claim": service.personal.claim_library_item,
                            "/v1/personal/library/delete": service.personal.delete_library_item,
                            "/v1/personal/library/continue": service.personal.continue_library_item,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/devices/snapshot",
                        "/v1/personal/devices/discover",
                        "/v1/personal/devices/iot-control",
                        "/v1/personal/tv/control",
                        "/v1/personal/tv/session",
                        "/v1/personal/tv/presence",
                        "/v1/personal/tv/presentation",
                        "/v1/personal/dashboard/action",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/devices/snapshot": service.personal.device_mesh_snapshot,
                            "/v1/personal/devices/discover": service.personal.discover_device_mesh,
                            "/v1/personal/devices/iot-control": service.personal.control_iot_device,
                            "/v1/personal/tv/control": service.personal.control_shared_tv,
                            "/v1/personal/tv/session": service.personal.change_shared_tv_session,
                            "/v1/personal/tv/presence": service.personal.confirm_shared_tv_presence,
                            "/v1/personal/tv/presentation": service.personal.control_shared_tv_presentation,
                            "/v1/personal/dashboard/action": service.personal.control_dashboard_action,
                        }[self.path]
                        call_args = {
                            "certificate": dict(body.get("certificate") or {}),
                            "lease": dict(body.get("lease") or {}),
                            "phone_signature": str(body.get("phone_signature") or ""),
                        }
                        if self.path == "/v1/personal/tv/presence":
                            call_args["trusted_local_address"] = service._is_trusted_local_address(self.client_address[0])
                        result = operation(dict(body.get("request") or {}), **call_args)
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/experiences/snapshot",
                        "/v1/personal/experiences/control",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/experiences/snapshot": service.personal.experience_snapshot,
                            "/v1/personal/experiences/control": service.personal.control_experience,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/memory/snapshot",
                        "/v1/personal/memory/create",
                        "/v1/personal/memory/update",
                        "/v1/personal/memory/delete",
                        "/v1/personal/memory/export",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/memory/snapshot": service.personal.memory_snapshot,
                            "/v1/personal/memory/create": service.personal.create_memory,
                            "/v1/personal/memory/update": service.personal.update_memory,
                            "/v1/personal/memory/delete": service.personal.delete_memory,
                            "/v1/personal/memory/export": service.personal.export_memory,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/guardian/snapshot",
                        "/v1/personal/guardian/configure",
                        "/v1/personal/guardian/action",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/guardian/snapshot": service.personal.guardian_snapshot,
                            "/v1/personal/guardian/configure": service.personal.configure_guardian_contact,
                            "/v1/personal/guardian/action": service.personal.control_guardian_incident,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path in {
                        "/v1/personal/intelligence/snapshot",
                        "/v1/personal/intelligence/ask",
                        "/v1/personal/intelligence/configure",
                    }:
                        if service.personal is None:
                            raise RuntimeError("Personal Pilot is not active on this mother")
                        operation = {
                            "/v1/personal/intelligence/snapshot": service.personal.intelligence_snapshot,
                            "/v1/personal/intelligence/ask": service.personal.use_intelligence,
                            "/v1/personal/intelligence/configure": service.personal.configure_intelligence,
                        }[self.path]
                        result = operation(
                            dict(body.get("request") or {}), certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}), phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/tasks/respond":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.respond_to_task(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/tasks/transition":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.transition_task(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/attachments/send":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.send_attachment(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/attachments/read":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.read_attachment(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/voice-notes/send":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.send_voice_note(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/cards/send":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.send_structured_card(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/ptt/floor":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.control_ptt_floor(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/search":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        result = service.inbox.search(
                            dict(body.get("request") or {}),
                            certificate=dict(body.get("certificate") or {}),
                            lease=dict(body.get("lease") or {}),
                            phone_signature=str(body.get("phone_signature") or ""),
                        )
                        self._json(result, origin=origin)
                    elif self.path == "/v1/inbox/packets/receive":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        self._json(service.inbox.receive_packet(dict(body.get("packet") or {})), origin=origin)
                    elif self.path == "/v1/inbox/receipts/reconcile":
                        if service.inbox is None:
                            raise RuntimeError("The private Inbox is not active on this Pilot")
                        self._json(service.inbox.reconcile_receipt(dict(body.get("receipt") or {})), origin=origin)
                    else:
                        self._json({"error": "Not found"}, 404, origin=origin)
                except PermissionError as exc:
                    self._json({"error": str(exc)}, 403, origin=origin)
                except (KeyError, TypeError, ValueError) as exc:
                    self._json({"error": str(exc)}, 400, origin=origin)
                except RuntimeError as exc:
                    self._json({"error": str(exc)}, 429, origin=origin)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer((self.address, self.port), Handler)
        server.socket = self.tls_context.wrap_socket(server.socket, server_side=True)
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="pilot-mobile-pairing", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None
