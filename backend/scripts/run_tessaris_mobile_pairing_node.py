#!/usr/bin/env python3
"""Run the local Tessaris Node QR pairing screen.

This is deliberately LAN-only.  The QR code is a signed, short-lived invitation;
it contains no private key, confirmation code, device credential, or relay token.
The phone must still make a request and the owner must enter the code displayed
on this Node before pairing completes.
"""

from __future__ import annotations

import argparse
import io
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import qrcode
from qrcode.image.svg import SvgPathImage

from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.local_tls import LocalTLSAuthority
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.calendar_planning import GovernedCalendarPlanning
from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.runtime import AionFabricRuntime
from backend.modules.pilot_unified.personal import PersonalPilotProjection
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified.pairing_service import MobilePairingService
from backend.modules.pilot_unified.workspace_gateway import AionBoardroomWorkspaceProvider, ProviderIndependentWorkspaceGateway
from backend.modules.pilot_unified.contracts import Membership
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import FinancePilotConversationService
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def lan_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    finally:
        probe.close()


def qr_svg(payload: str) -> bytes:
    image = qrcode.make(payload, image_factory=SvgPathImage)
    output = io.BytesIO()
    image.save(output)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local Tessaris Node phone-pairing screen")
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--persona-id", required=True)
    parser.add_argument("--node-name", default="Tessaris Node")
    parser.add_argument("--pairing-port", type=int, default=8770)
    parser.add_argument("--screen-port", type=int, default=8772)
    parser.add_argument("--screen-only", action="store_true", help="Serve only the QR screen; use an already-running Node pairing service")
    parser.add_argument(
        "--profile", choices=("companion", "founder-boardroom"), default="companion",
        help="Pair a narrow companion phone or a founder phone with Boardroom workspace access.",
    )
    parser.add_argument("--founder-workspace-id", default="", help="One workspace enrolled for the Founder Boardroom profile")
    args = parser.parse_args()

    root = Path(args.runtime_dir).expanduser().resolve()
    trust_profile = root / "pilot_unified" / "Tessaris-Local-Node-Trust.mobileconfig"
    address = lan_address()
    identity = IdentityStore(root / "identity").load_or_create()
    identities = ProductionPrivateIdentity(root)
    calendar = GovernedCalendarPlanning(root, identities=identities)
    google_oauth = PersonaGoogleOAuth(root, identities=identities)
    profile = next((item for item in identities.snapshot().get("profiles", []) if item.get("persona_id") == args.persona_id and item.get("status") == "active"), None)
    if profile is None:
        raise SystemExit("The requested local founder identity is not active.")

    tls = LocalTLSAuthority(root).ensure(address=address, hostname=socket.gethostname())
    hostname = socket.gethostname().lower().replace(" ", "-").removesuffix(".local")
    authority = MobilePairingAuthority(
        root,
        mother_id=f"node_{hostname}.local",
        mother_identity=identity,
        endpoint=f"https://{address}:{args.pairing_port}",
        ca_sha256=tls.ca_sha256,
        ca_certificate_pem=tls.ca_certificate_path.read_bytes(),
        identity_registry=identities,
    )
    def issue_invitation() -> bytes:
        # The QR contains only this local URL. Generate its signed payload on
        # each fetch so a page left open overnight never hands a phone a stale
        # ten-minute invitation.
        requested_scopes = ("message.send", "task.create", "tv.control")
        if args.profile == "founder-boardroom":
            # These scopes provide a founder with mobile read/conversation and
            # explicit review authority.  They do not grant arbitrary external
            # writes; existing exact approval gates still apply.
            requested_scopes = (
                "inbox.read", "message.send", "task.create", "tv.control",
                "workspace.invitations.read", "workspace.invitations.respond",
                "workspace.read", "workspace.conversation", "workspace.cards.read",
                "workspace.cards.act", "workspace.approve", "workspace.signoff.prepare",
                "workspace.signoff.read", "workspace.signoff.director", "workspace.files.reference",
                "workspace.desktop.handoff", "workspace.custom_departments.manage",
                "workspace.support.read", "workspace.people.read", "workspace.finance.read",
            )
        invitation = authority.pairing_invitation(
            persona_id=args.persona_id,
            requested_scopes=requested_scopes,
            validity_minutes=10,
        )
        return json.dumps(invitation, separators=(",", ":"), sort_keys=True).encode("utf-8")
    state: dict[str, Any] = {"status": "Waiting for a phone to scan the code.", "code": ""}
    state_lock = threading.Lock()

    def show_confirmation(confirmation: dict[str, Any]) -> None:
        with state_lock:
            state["status"] = f"Confirm the code for {confirmation['device_label']} on this Node."
            state["code"] = str(confirmation["confirmation_code"])
            state["trust_words"] = " ".join(confirmation.get("trust_words") or [])

    workspace_gateway = None
    if args.founder_workspace_id:
        if args.profile != "founder-boardroom":
            raise SystemExit("Founder workspace enrollment requires --profile founder-boardroom.")
        workspace_gateway = ProviderIndependentWorkspaceGateway(
            issuer_id=identity.fingerprint, issuer_identity=identity, pairing_authority=authority,
        )
        def calendar_snapshot(persona_id: str) -> dict[str, Any]:
            account = google_oauth.snapshot(persona_id=persona_id)
            connected = any(
                item.get("status") == "connected" and "calendar" in set(item.get("services") or [])
                for item in account.get("bindings") or []
            )
            return {**calendar.snapshot(persona_id=persona_id), "connected": connected, "time_zone": "Europe/Madrid"}

        provider = AionBoardroomWorkspaceProvider(
            WorkspaceRepository(), BusinessContainerRepository(), DepartmentPilotRepository(),
            FinancePilotConversationService(), WorkflowFileCabinetRepository,
            calendar_snapshot_loader=calendar_snapshot,
        )
        workspace_gateway.register_provider(provider)
        workspace_gateway.discover(provider.provider_id)
        workspace_gateway.grant_membership(Membership(
            membership_id=f"membership/founder-{args.founder_workspace_id}-{args.persona_id[-12:]}",
            persona_id=args.persona_id, space_id=f"workspace/{args.founder_workspace_id}",
            role_id="founder_mobile_chat", scopes=("workspace.read", "workspace.conversation", "workspace.custom_departments.manage", "workspace.support.read", "workspace.people.read", "workspace.finance.read"),
            status="active", issued_at=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        ))

    # The phone service shares the Fabric runtime directory with the browser
    # dashboard. A phone can therefore establish a signed, time-limited
    # Personal session that the dashboard reads from the same identity store.
    def dashboard_action(persona_id: str, command: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route signed phone intent into the local Pilot runtime."""
        # Games is a direct, governed webOS launch.  It must not depend on the
        # browser dashboard being open or healthy: the phone should be able to
        # open the already-authorised Games surface by itself.
        if command == "games":
            runtime = AionFabricRuntime.bootstrap(root)
            return runtime.execute_companion_command("games", arguments)
        payload = json.dumps({"command": command, "arguments": arguments}).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:8765/api/dashboard/action", data=payload,
            headers={"Content-Type": "application/json", "X-AION-Fabric": "dashboard-v1"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:  # nosec B310: fixed localhost endpoint
                return dict(json.loads(response.read().decode("utf-8")))
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise RuntimeError("The local Pilot dashboard is not available") from error

    personal = PersonalPilotProjection(
        identities=identities,
        inbox=PilotInbox(root, identities=identities),
        pairing_authority=authority,
        calendar=calendar,
        google_oauth=google_oauth,
        dashboard_action_executor=dashboard_action,
    )

    pairing = None
    if not args.screen_only:
        pairing = MobilePairingService(
            authority,
            tls_context=tls.context(),
            confirmation_presenter=show_confirmation,
            address="0.0.0.0",
            port=args.pairing_port,
            default_persona_id=args.persona_id,
            personal=personal,
            workspace_gateway=workspace_gateway,
        )
        pairing.start()
    # The full invitation includes a public certificate and can exceed QR
    # capacity.  The phone fetches this LAN-only document then verifies its
    # signed contents before trusting the TLS endpoint.
    svg = qr_svg(f"http://{address}:{args.screen_port}/invitation")
    trust_svg = qr_svg(f"http://{address}:{args.screen_port}/Tessaris-Local-Node-Trust.mobileconfig") if trust_profile.exists() else b""

    class Screen(BaseHTTPRequestHandler):
        def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/qr.svg":
                return self.send_bytes(svg, "image/svg+xml")
            if self.path == "/trust.svg" and trust_svg:
                return self.send_bytes(trust_svg, "image/svg+xml")
            if self.path == "/Tessaris-Local-Node-Trust.mobileconfig" and trust_profile.exists():
                return self.send_bytes(trust_profile.read_bytes(), "application/x-apple-aspen-config")
            if self.path == "/status":
                with state_lock:
                    body = json.dumps(state).encode("utf-8")
                return self.send_bytes(body, "application/json")
            if self.path.split("?", 1)[0] == "/invitation":
                return self.send_bytes(issue_invitation(), "application/json")
            if self.path not in {"/", "/index.html"}:
                return self.send_bytes(b"Not found", "text/plain", 404)
            body = f"""<!doctype html><meta charset=utf-8><title>Pair Tessaris Node</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f6f4ef;color:#172032;margin:0;display:grid;place-items:center;min-height:100vh}}main{{width:min(720px,90vw);background:white;border:1px solid #dedbd2;padding:42px;border-radius:22px;text-align:center;box-shadow:0 16px 45px #1c26311a}}img{{width:min(360px,75vw);image-rendering:auto}}p{{color:#667085;line-height:1.5}}#code{{font-size:52px;letter-spacing:.15em;font-weight:750;margin:22px 0;color:#173a57}}small{{color:#8a6c24}}</style>
<main><small>TESSARIS NODE · PRIVATE PHONE PAIRING</small><h1>{args.node_name}</h1><p>Scan this code in Pilot. It expires in ten minutes and gives the phone no access by itself.</p><img src=/qr.svg alt='Tessaris Node QR code'><h2 id=status>Waiting for phone</h2><div id=code>—</div><p id=words></p><p>After scanning, enter the code shown here on the phone to complete pairing.</p>{"<hr><h2>Install Tessaris Local Node Trust</h2><p>Scan this with the iPhone Camera, not Pilot, then install the downloaded profile.</p><img src=/trust.svg alt='Tessaris local trust profile QR code'>" if trust_svg else ""}</main>
<script>async function update(){{let s=await (await fetch('/status')).json();status.textContent=s.status;code.textContent=s.code||'—';words.textContent=s.trust_words||''}}update();setInterval(update,1000)</script>""".encode("utf-8")
            self.send_bytes(body, "text/html; charset=utf-8")

        def log_message(self, *unused: object) -> None:
            return

    screen = ThreadingHTTPServer(("0.0.0.0", args.screen_port), Screen)
    print(f"PAIRING_SCREEN=http://{address}:{args.screen_port}", flush=True)
    try:
        screen.serve_forever(poll_interval=0.5)
    finally:
        if pairing:
            pairing.stop()
        screen.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
