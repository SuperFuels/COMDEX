from __future__ import annotations

import argparse
import html
import json
import os
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .demo import run_local_demo
from .runtime import AionFabricRuntime
from .supervisor import AutonomousDiscoverySupervisor
from .tv_canvas import TVCanvasService
from .voice import VoiceControlService
from .companion import CompanionService
from .universal_service import UniversalNodeService
from .service_state import ConnectionHealthMonitor, PrivateServiceState
from .local_tls import LocalTLSAuthority, LocalTLSMaterial
from .webos import WebOsGateway
from .canonical import canonical_hash
from backend.modules.pilot_unified.inbox import UnifiedInbox
from backend.modules.pilot_unified.inbox_live_service import UnifiedInboxLiveService
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified.pairing_service import MobilePairingService
from backend.modules.pilot_unified.workspace_gateway import AionBoardroomWorkspaceProvider, ProviderIndependentWorkspaceGateway
from backend.modules.pilot_unified.contracts import Membership
from backend.modules.pilot_unified.shared_surface import SharedSurfaceManifestAuthority
from backend.modules.pilot_unified.adoption import TrustedNetworkAuthority
from backend.modules.pilot_unified.handoff import TrustedHandoffAuthority
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import FinancePilotConversationService
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.commercial_adoption_service import CommercialAdoptionService


DEFAULT_RUNTIME = Path(".runtime/aion_fabric")


def _print(value: Dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def _sovereign_brain_html() -> bytes:
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>How the Pilot brain works</title>
<style>
:root{--ink:#17213a;--muted:#66748c;--line:#dde5f0;--blue:#1769e8;--navy:#092a55;--green:#118b61;--paper:#fff}
*{box-sizing:border-box}body{margin:0;color:var(--ink);font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(circle at 50% -12%,#e5f0ff 0,#f7f9fc 38%,#fff 72%);line-height:1.55}
main{max-width:1160px;margin:auto;padding:28px 28px 80px}nav{display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{font-size:23px;font-weight:850;letter-spacing:-.03em}.back{color:#155fcd;text-decoration:none;font-weight:750;padding:10px 14px;border:1px solid #d4e1f4;border-radius:14px;background:#fff}
.hero{text-align:center;max-width:870px;margin:86px auto 62px}.eyebrow{color:#52708f;text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:.17em}.mark{display:grid;place-items:center;width:72px;height:72px;margin:18px auto;border-radius:24px;color:#fff;font-size:31px;background:linear-gradient(145deg,#071a35,#1557d6 55%,#29a9ff);box-shadow:0 16px 38px #2565bb30}.hero h1{font-size:52px;letter-spacing:-.055em;line-height:1.02;margin:20px 0 17px}.hero p{font-size:21px;color:var(--muted);max-width:760px;margin:auto}
.principle{margin:0 auto 70px;padding:29px 34px;border:1px solid #cfe0f7;border-radius:26px;background:#fff;box-shadow:0 18px 50px #233b6012;text-align:center}.principle strong{display:block;font-size:28px;margin-bottom:7px}.principle span{color:var(--muted)}
h2{font-size:32px;letter-spacing:-.035em;margin:0 0 10px}.intro{color:var(--muted);max-width:760px;margin:0 0 26px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:17px;margin:24px 0 70px}.card{background:#fff;border:1px solid var(--line);border-radius:23px;padding:25px;box-shadow:0 8px 28px #263c5d0d}.card b{display:block;font-size:19px;margin:12px 0 7px}.card p{color:var(--muted);margin:0}.icon{display:grid;place-items:center;width:45px;height:45px;border-radius:15px;background:#edf4ff;color:#155fcd;font-weight:850}.card:nth-child(2) .icon{background:#ebfaf3;color:#0b875b}.card:nth-child(3) .icon{background:#fff4e5;color:#b46a00}
.flow{padding:29px;border-radius:28px;background:#0a1d38;color:#fff;margin:24px 0 70px;overflow:auto}.flow h3{font-size:21px;margin:0 0 22px}.rail{display:flex;align-items:stretch;gap:9px;min-width:950px}.node{display:flex;flex:1;flex-direction:column;justify-content:center;min-height:105px;padding:15px;border:1px solid #365170;border-radius:17px;background:#112b4d}.node strong{font-size:14px}.node small{color:#a7b9cf;margin-top:4px}.arrow{align-self:center;color:#55b9ff}.node.aion{border-color:#318af0;background:#123e76}.node.action{border-color:#36a578;background:#103b34}.caption{color:#9fb2ca;font-size:13px;margin:18px 3px 0}
.rules{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:24px 0 70px}.rule{padding:22px 24px;border-left:4px solid #2175e7;background:#fff;border-radius:6px 19px 19px 6px;box-shadow:0 7px 24px #2036540c}.rule strong{display:block;margin-bottom:5px}.rule span{color:var(--muted)}
table{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--line);border-radius:20px;overflow:hidden;margin:24px 0 70px}th,td{text-align:left;padding:16px;border-bottom:1px solid var(--line)}th{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:#617089;background:#f7f9fc}tr:last-child td{border-bottom:0}td:first-child{font-weight:750}
.promise{padding:35px;border-radius:28px;background:linear-gradient(135deg,#eef5ff,#effbf6);border:1px solid #d7e7f5}.promise h2{margin-bottom:12px}.promise p{color:#53647d;max-width:850px}.badge{display:inline-block;margin:8px 7px 0 0;padding:7px 11px;border-radius:999px;background:#fff;color:#1769e8;border:1px solid #d6e3f5;font-size:12px;font-weight:750}
@media(max-width:800px){.hero{margin-top:55px}.hero h1{font-size:40px}.grid,.rules{grid-template-columns:1fr}main{padding:22px 18px 60px}}
</style></head><body><main>
<nav><div class="brand">Pilot</div><a class="back" href="/">← Pilot Home</a></nav>
<section class="hero"><div class="eyebrow">Tessaris · Sovereign intelligence</div><div class="mark">✈</div><h1>Your AI is not the model.</h1><p>Pilot is the face. AION is your customer-owned second brain. Models are replaceable specialists it can use without surrendering your identity, memory, policies or business knowledge.</p></section>
<section class="principle"><strong>You keep the brain. You choose the compute.</strong><span>Run locally, in your own cloud, or through an optional provider—and change the model later without starting again.</span></section>
<section><h2>One brain, three layers</h2><p class="intro">The separation is deliberate: intelligence accumulated about you or your organisation must outlive any model, cloud or interface.</p><div class="grid">
<article class="card"><div class="icon">A</div><b>AION brain</b><p>Owns identity, memory, the business map, policy, capability authority, outcome learning and audit receipts.</p></article>
<article class="card"><div class="icon">M</div><b>Replaceable specialists</b><p>Local models, retrieval engines, harnesses and customer-cloud compute perform bounded cognitive work.</p></article>
<article class="card"><div class="icon">P</div><b>Pilot surfaces</b><p>Phone, television, desktop, Workspace and Boardroom provide conversation, review, approval and control.</p></article>
</div></section>
<section><h2>AION Flow</h2><p class="intro">A visual, plug-and-play intelligence fabric for choosing models, harnesses, evidence, hosting and actions. AION surrounds the graph; it is not merely another node in the queue.</p><div class="flow"><h3>A governed intelligence route</h3><div class="rail">
<div class="node aion"><strong>AION admits</strong><small>identity · intent · minimum context</small></div><span class="arrow">→</span>
<div class="node"><strong>Evidence</strong><small>files · systems · public sources</small></div><span class="arrow">→</span>
<div class="node"><strong>Specialists</strong><small>model · harness · chosen compute</small></div><span class="arrow">→</span>
<div class="node"><strong>Compare</strong><small>bounded debate · validators</small></div><span class="arrow">→</span>
<div class="node aion"><strong>AION governs</strong><small>policy · evidence · approval</small></div><span class="arrow">→</span>
<div class="node action"><strong>Act &amp; verify</strong><small>capability · outcome · receipt</small></div>
</div><p class="caption">A model output is a proposal, never authority. Only a governed capability may change an external system.</p></div></section>
<section><h2>What makes multi-model workflows useful</h2><div class="rules">
<div class="rule"><strong>Different specialists, not repetition</strong><span>Route research, vision, coding, finance or drafting to independently qualified tools rather than asking one model the same question repeatedly.</span></div>
<div class="rule"><strong>Evidence before consensus</strong><span>Agreement between models is not proof. Deterministic checks, source evidence and contradiction detection remain separate.</span></div>
<div class="rule"><strong>Bounded refinement</strong><span>Every loop declares an iteration, time and cost limit plus a clear exit condition. No runaway agent conversations.</span></div>
<div class="rule"><strong>Visible disclosure</strong><span>Every edge states what data leaves the brain, where it goes, its residency and whether encryption is required.</span></div>
</div></section>
<section><h2>Choose where intelligence runs</h2><table><thead><tr><th>Mode</th><th>Where models run</th><th>Best for</th></tr></thead><tbody>
<tr><td>AION Local</td><td>Your computer or private server</td><td>Privacy, offline work and predictable cost</td></tr>
<tr><td>Customer cloud</td><td>Your AWS, Google Cloud, Azure, NVIDIA, Prem or compatible environment</td><td>Private scalable compute under your account</td></tr>
<tr><td>Optional provider</td><td>A provider API you explicitly connect</td><td>Convenience or specialist capability, with disclosure</td></tr>
</tbody></table></section>
<section class="promise"><h2>The ownership promise</h2><p>Remove a provider and your brain still boots. Swap a model and your learned business map remains. Disconnect the internet and core local intelligence still works. AION preserves the durable understanding; replaceable tools provide temporary computation.</p><span class="badge">Provider-independent memory</span><span class="badge">Inspectible permissions</span><span class="badge">Verified actions</span><span class="badge">Portable brain export</span></section>
</main></body></html>"""
    return document.encode("utf-8")


def _dashboard_html(
    runtime: AionFabricRuntime,
    demo: Dict[str, Any] | None = None,
    voice_service: VoiceControlService | None = None,
    canvas_service: TVCanvasService | None = None,
    companion_service: CompanionService | None = None,
    workspace_gateway: ProviderIndependentWorkspaceGateway | None = None,
) -> bytes:
    status = runtime.status()
    transport = (demo or {}).get("transport", {})
    nodes = [
        node for node in status.get("nodes", [])
        if not node.get("profile", {}).get("metadata", {}).get("hidden_from_topology")
    ]
    cards = []
    for node in nodes:
        profile = node["profile"]
        transports = ", ".join(profile.get("transports", [])) or "local"
        control_names = profile.get("controls", [])
        controls = ", ".join(control_names[:5]) if control_names else "none"
        if len(control_names) > 5:
            controls += f" +{len(control_names) - 5} more"
        enrollment = node.get("enrollment", "discovered")
        enrollment_class = "online" if enrollment == "enrolled" else "discovered"
        metadata = profile.get("metadata", {})
        documents = int(metadata.get("documentation_artifacts", 0))
        inferred_controls = int(metadata.get("inferred_controls", len(control_names)))
        enrollment_button = (
            f'<button class="enroll" data-node="{html.escape(profile["node_id"])}">Enroll read-only gateway</button>'
            if enrollment == "discovered" and any(
                str(name).lower().startswith(("get", "query", "list", "read", "browse", "search"))
                for name in control_names
            )
            else ""
        )
        probe_button = (
            f'<button class="probe" data-node="{html.escape(profile["node_id"])}">Run permitted read-only probe</button>'
            if enrollment == "enrolled" and metadata.get("read_only_action_ids")
            else ""
        )
        is_lg_webos = "lg" in profile.get("platform", "").lower() and "webos" in profile.get("name", "").lower()
        paired = metadata.get("webos_pairing") == "paired"
        webos_button = (
            f'<button class="webos-pair" data-node="{html.escape(profile["node_id"])}">'
            f'{"Read paired TV volume" if paired else "Pair LG webOS securely"}</button>'
            if enrollment == "enrolled" and is_lg_webos
            else ""
        )
        canvas_button = (
            f'<button class="tv-canvas" data-node="{html.escape(profile["node_id"])}">Put AION on this TV</button>'
            if paired and metadata.get("webos_integration") == "connected" and canvas_service is not None
            else ""
        )
        pairing_status = (
            f'<p class="pairing-state">Paired webOS proof: {html.escape(json.dumps(metadata.get("webos_read_only_proof", {}), separators=(",", ":")))}</p>'
            if paired
            else ""
        )
        integration_surfaces = metadata.get("webos_connected_surfaces", [])
        round_trip = metadata.get("webos_volume_round_trip", {})
        integration_status = ""
        if metadata.get("webos_integration") == "connected":
            trip_text = (
                f'{round_trip.get("original")}→{round_trip.get("target")}→{round_trip.get("observed_restored")} restored'
                if round_trip.get("restored")
                else "not run"
            )
            denied = len(metadata.get("webos_read_errors", {}))
            integration_status = (
                f'<p class="integration-state">Integrated: {len(integration_surfaces)} live surfaces · '
                f'Volume test {html.escape(trip_text)} · {denied} TV-denied surfaces</p>'
            )
        cards.append(
            f"""
            <article class="node">
              <div class="node-top"><span class="role {html.escape(node['role'])}">{html.escape(node['role'])}</span><span class="{enrollment_class}">● {html.escape(enrollment)}</span></div>
              <h3>{html.escape(profile['name'])}</h3>
              <p>{html.escape(profile['device_class'])} · {html.escape(profile['platform'])}</p>
              <dl><dt>Node</dt><dd>{html.escape(profile['node_id'])}</dd><dt>Transport</dt><dd>{html.escape(transports)}</dd><dt>Docs</dt><dd>{documents} acquired</dd><dt>Schema</dt><dd>{inferred_controls} controls inferred</dd><dt>Controls</dt><dd>{html.escape(controls)}</dd></dl>
              {enrollment_button}
              {probe_button}
              {webos_button}
              {canvas_button}
              {pairing_status}
              {integration_status}
            </article>
            """
        )
    ledger = status["ledger"]
    saving = transport.get("saving_vs_repeated_raw_snapshots_percent")
    voice = voice_service.status() if voice_service else {"running": False, "ready": False}
    voice_label = (
        "Microphone asleep"
        if voice.get("sleeping")
        else "Voice ready — say ‘Pilot’"
        if voice.get("ready")
        else f"Voice starting: {voice.get('error', '')}"
        if voice_service
        else "Voice disabled"
    )
    voice_details = (
        f"State {voice.get('activity_state', 'off')} · Mic level {voice.get('audio_rms', 0)} · Heard {voice.get('heard_utterances', 0)} utterances · "
        f"Wake matches {voice.get('wake_matches', 0)} · Last heard: {voice.get('last_heard_transcript') or 'nothing yet'} · "
        f"Result: {voice.get('last_result') or 'waiting'}"
    )
    voice_options = "".join(
        f'<option value="{name}"{" selected" if voice.get("voice_name") == name else ""}>{name}</option>'
        for name in ("Daniel", "Samantha", "Karen", "Mónica", "Thomas", "Anna", "Alice", "Joana")
    )
    quiet_start = html.escape(str(voice.get("quiet_start") or ""), quote=True)
    quiet_end = html.escape(str(voice.get("quiet_end") or ""), quote=True)
    saving_card = (
        f"<strong>{saving:.2f}%</strong><span>test-stream reduction</span>"
        if isinstance(saving, (int, float))
        else "<strong>Ready</strong><span>waiting for device streams</span>"
    )
    active_identity = dict(runtime.private_identity.snapshot().get("active_shared_identity") or {})
    active_person_name = str(active_identity.get("display_name") or "").strip()
    workspace_state_class = "unlocked" if active_identity.get("persona_id") else "locked"
    workspace_state_text = (
        f"Active as {html.escape(active_person_name)}. Private tiles follow this signed television session."
        if active_person_name
        else "Private workspace locked. Acquire the television from a trusted phone to open personal content."
    )
    surface_authority = SharedSurfaceManifestAuthority(
        runtime.base_dir, issuer=runtime.identity, identities=runtime.private_identity,
        workspace_gateway=workspace_gateway,
    )
    surface_manifest = surface_authority.issue_home_manifest(surface_id="surface.tv.dashboard")
    tile_configuration = {
        "games": ("games", "🎮", "Open cloud gaming on the television."),
        "aion": ("tv", "📺", "Put Pilot on the big screen and control the room."),
        "education_start": ("learning", "🎓", "Start the interactive Spanish Learning Centre."),
        "shopping": ("shopping", "🛒", "Find, compare, and prepare a purchase."),
        "devices": ("workspace", "⌁", "Connect, inspect, and manage household devices."),
        "tasks": ("workspace", "✓", "Your private lists, reminders, and requests."),
        "calendar": ("workspace", "▣", "Your schedule and approved events."),
        "boardroom": ("workspace", "◆", "Open the separately authenticated Boardroom."),
        "files": ("workspace", "▤", "Your approved documents and saved assets."),
        "work": ("workspace", "✦", "Research, writing, study, and personal projects."),
        "personal": ("workspace", "●", "Unlock your private Pilot."),
        "household": ("workspace", "⌂", "Unlock household tools."),
        "workspace": ("workspace", "◇", "No Workspace membership is exposed while locked."),
    }
    experience_tiles, private_tiles = [], []
    for tile in surface_manifest["tiles"]:
        tile_id = str(tile["tile_id"])
        base_tile_id = tile_id.split(".", 1)[0]
        css_class, icon, description = tile_configuration.get(
            tile_id,
            tile_configuration.get(base_tile_id, ("workspace", "•", "Open this authorized Pilot surface.")),
        )
        locked = tile.get("privacy") == "locked"
        local_view = ' data-local-view="nodes-view"' if tile_id == "devices" and not locked else ""
        launch = (
            "" if locked or local_view else
            f' data-mode="shopping"' if tile_id == "shopping" else
            f' data-launch="{html.escape(tile_id)}"'
        )
        locked_class = " locked" if locked else ""
        disabled = " disabled" if locked else ""
        markup = f'<button class="launch {css_class}{locked_class}"{local_view}{launch}{disabled}><span class="icon">{icon}</span><span><strong>{html.escape(str(tile["label"]))}</strong><span>{html.escape(description)}</span></span></button>'
        (experience_tiles if tile.get("privacy") == "public" and tile_id != "devices" else private_tiles).append(markup)
    experience_launcher = "".join(experience_tiles)
    workspace_launcher = "".join(private_tiles)
    phone_beacon = ""
    if companion_service:
        secure_note = f'''<p><strong>Secure camera controller:</strong> <a href="{html.escape(companion_service.secure_controller_url)}">{html.escape(companion_service.secure_controller_url)}</a> after explicitly installing and trusting the public household certificate.</p><p>Verify the certificate on your phone shows CA SHA-256 <code>{html.escape(companion_service.ca_fingerprint)}</code>. Compare it here on this trusted laptop before enabling trust.</p>''' if companion_service.secure_controller_url else ""
        phone_beacon = f'''<div class="phone-beacon"><img src="{html.escape(companion_service.entry_url)}/pair.svg" alt="Scan to connect an iPhone to Pilot"><div><strong>Connect a phone</strong><p>Scan this rotating local beacon with the iPhone camera. Confirm code <code>{html.escape(companion_service.pair_code)}</code>. No IP address typing is required.</p><a href="{html.escape(companion_service.entry_url)}">Open pairing and certificate page</a>{secure_note}</div></div>'''
    intelligence = runtime.tv_research.policy.status()
    intelligence_mode = str(intelligence.get("mode") or "native")
    gemini_state = "connected" if intelligence.get("gemini_connected") else "add a Gemini key in the private vault"
    openai_state = "connected" if intelligence.get("openai_connected") else "optional"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot</title>
<style>
:root{{--bg:#07111f;--panel:#101d2d;--line:#24364d;--text:#edf5ff;--muted:#91a4bb;--cyan:#52d6ff;--green:#60e6a8;--amber:#ffc66d}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0,#15304b 0,#07111f 36%);color:var(--text);font:15px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:auto;padding:44px 24px 70px}} header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:28px}}
h1{{font-size:38px;margin:6px 0}} h2{{font-size:20px;margin:0 0 16px}} h3{{margin:16px 0 6px;font-size:19px}} p{{color:var(--muted)}}
.eyebrow{{color:var(--cyan);font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:12px}} .live{{padding:10px 14px;border:1px solid #286247;border-radius:999px;color:var(--green);background:#102a23}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}} .metric,.node,.notice{{background:linear-gradient(145deg,#132337,#0d1928);border:1px solid var(--line);border-radius:16px;padding:20px}}
.metric strong{{display:block;font-size:28px;color:var(--cyan)}} .metric span{{color:var(--muted)}} .nodes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}
.node-top{{display:flex;justify-content:space-between}} .role{{padding:5px 9px;border-radius:8px;background:#173451;color:var(--cyan);font-size:12px;text-transform:uppercase;font-weight:800}} .role.mother{{background:#382d15;color:var(--amber)}} .role.edge{{background:#14382d;color:var(--green)}}
.online{{color:var(--green);font-size:12px}} .discovered{{color:var(--amber);font-size:12px}} dl{{display:grid;grid-template-columns:80px 1fr;gap:8px;margin:16px 0 0}} dt{{color:var(--muted)}} dd{{margin:0;overflow-wrap:anywhere}} .notice{{margin-top:22px;border-color:#315373}} code{{color:var(--cyan)}}
.toolbar{{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:30px 0 16px}} .toolbar h2{{margin:0}} button{{appearance:none;border:1px solid #2e8caf;background:#113954;color:var(--text);border-radius:11px;padding:11px 16px;font-weight:750;cursor:pointer}} button:hover{{background:#174b6d}} button:disabled{{opacity:.55;cursor:wait}} #scan-status{{color:var(--muted);margin-left:10px}} .enroll,.probe,.webos-pair,.tv-canvas{{width:100%;margin-top:18px}} .enroll{{border-color:#8a6a2c;background:#3b2d13}} .probe{{border-color:#287a59;background:#123d2f}} .webos-pair{{border-color:#536bd1;background:#202d63}} .tv-canvas{{border-color:#4edeb9;background:linear-gradient(135deg,#15563f,#123f5d);font-size:15px}} .pairing-state,.integration-state{{color:var(--green);font-size:13px;overflow-wrap:anywhere}} .integration-state{{color:var(--cyan)}}
.phone-beacon{{display:flex;align-items:center;gap:20px;background:#081522;border:1px solid #315373;border-radius:16px;padding:18px;margin:18px 0}}.phone-beacon img{{width:170px;background:white;border-radius:12px;padding:8px}}.phone-beacon strong{{font-size:20px;color:var(--green)}}
.intelligence-picker{{margin-top:28px;padding:22px;border:1px solid var(--line);border-radius:22px;background:var(--panel);box-shadow:0 8px 28px #2b3a5210}}.intelligence-picker h2{{margin-bottom:5px}}.intelligence-picker>p{{margin:0 0 16px}}.intelligence-options{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.intelligence-option{{text-align:left;background:#fff;color:var(--text);border:1px solid #dfe5ee}}.intelligence-option.active{{border-color:#1769d2;background:#eef4ff;box-shadow:0 0 0 2px #1769d21f}}.intelligence-option strong,.intelligence-option span{{display:block}}.intelligence-option span{{margin-top:5px;color:var(--muted);font-weight:500;font-size:12px}}#intelligence-result{{min-height:18px;margin:12px 0 0;font-size:13px}}
.view[hidden]{{display:none}}.welcome{{margin:4px 0 24px}}.welcome h2{{font-size:31px;margin-bottom:7px}}.welcome p{{font-size:17px;margin:0}}.launcher{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}.launch{{min-height:190px;padding:22px;text-align:left;display:flex;flex-direction:column;justify-content:space-between;border:1px solid var(--line);border-radius:22px;background:linear-gradient(145deg,#152b42,#0d1928);transition:transform .18s,border-color .18s,box-shadow .18s}}.launch:hover{{transform:translateY(-3px);border-color:#3faacc;box-shadow:0 18px 45px #0005}}.launch .icon{{font-size:42px}}.launch strong{{display:block;font-size:22px;margin-bottom:6px;color:var(--text)}}.launch span{{display:block;color:var(--muted);line-height:1.4;font-weight:500}}.launch.games{{background:linear-gradient(145deg,#31235d,#111a35)}}.launch.tv{{background:linear-gradient(145deg,#123b50,#0d1c2d)}}.launch.learning{{background:linear-gradient(145deg,#173c35,#0d2024)}}.launch.shopping{{background:linear-gradient(145deg,#49321d,#211b1a)}}.ask-box{{margin:22px 0;background:linear-gradient(145deg,#132337,#0c1725);border:1px solid #315373;border-radius:20px;padding:20px}}.ask-box label{{display:block;font-weight:800;font-size:17px;margin-bottom:11px}}.ask-row{{display:grid;grid-template-columns:1fr auto auto;gap:10px}}#home-query{{width:100%;border:1px solid #36516d;background:#07111f;color:white;border-radius:13px;padding:15px 17px;font:inherit;font-size:16px;outline:none}}#home-query:focus{{border-color:var(--cyan);box-shadow:0 0 0 3px #52d6ff22}}#home-result{{min-height:20px;margin:11px 2px 0;color:var(--muted)}}.home-phone{{margin-top:22px}}.section-intro{{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:16px}}.section-intro p{{margin:0}}a{{color:var(--cyan)}}
@media(max-width:900px){{.launcher{{grid-template-columns:1fr 1fr}}}}@media(max-width:760px){{.summary{{grid-template-columns:1fr 1fr}}header{{display:block}}.live{{display:inline-block;margin-top:12px}}.phone-beacon{{display:block;text-align:center}}.phone-beacon img{{width:min(70vw,240px)}}.launcher{{grid-template-columns:1fr 1fr}}}}@media(max-width:520px){{.launcher{{grid-template-columns:1fr}}.ask-row{{grid-template-columns:1fr}}.tabs{{width:100%}}.tab{{flex:1}}}}
/* Pilot light experience: search-first, calm, and consumer-facing. */
:root{{--bg:#f7f9fc;--panel:#fff;--line:#e3e8f0;--text:#182238;--muted:#657086;--cyan:#1677ff;--green:#19a974;--amber:#ed8b00}}
body{{background:radial-gradient(circle at 50% -15%,#e9f2ff 0,#f7f9fc 38%,#fff 100%);color:var(--text);min-height:100vh}}
main{{max-width:1240px;padding:30px 30px 76px}}
header{{margin-bottom:18px;align-items:center}}
header h1{{font-size:27px;letter-spacing:-.03em;margin:2px 0 3px}}
header p{{margin:0;color:#718096}}
.eyebrow{{font-size:10px;color:#59718e;letter-spacing:.16em}}.brain-link{{display:inline-block;margin-top:8px;color:#155fc8;text-decoration:none;font-size:13px;font-weight:750}}.brain-link:hover{{text-decoration:underline}}
.live{{border-color:#bee9d4;background:#ecfbf4;color:#13885f;box-shadow:0 3px 12px #2034500d}}
.welcome{{text-align:center;margin:64px auto 20px}}
.welcome:before{{content:'P';display:grid;place-items:center;width:76px;height:76px;margin:0 auto 20px;border-radius:24px;color:#fff;font-size:39px;font-weight:800;background:conic-gradient(from 210deg,#4285f4,#7c4dff,#ea4335,#fbbc05,#34a853,#4285f4);box-shadow:0 14px 35px #4279cc35}}
.welcome h2{{font-size:40px;letter-spacing:-.045em;color:#17213a;margin-bottom:8px}}
.welcome p{{font-size:17px;color:#738097}}
.ask-box{{max-width:850px;margin:0 auto 42px;background:#fff;border-color:#dfe5ee;border-radius:26px;padding:9px;box-shadow:0 14px 45px #34496b17}}
.ask-box label{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}}
.ask-row{{grid-template-columns:1fr auto auto;align-items:center}}
#home-query{{border:0;background:transparent;color:#1d2940;border-radius:20px;padding:17px 19px;font-size:17px;box-shadow:none}}
#home-query:focus{{border:0;box-shadow:none}}
.ask-row button{{border:0;border-radius:18px;padding:14px 22px;color:#fff;background:linear-gradient(135deg,#246bfd,#7657e8);box-shadow:0 6px 18px #3f65d733}}
.ask-row button:hover{{background:linear-gradient(135deg,#155eea,#6845df)}}
.ask-row .god-view{{background:linear-gradient(135deg,#071a35,#147ed4);display:flex;align-items:center;gap:8px;white-space:nowrap}}
#home-result{{margin:8px 13px 4px;text-align:center;color:#7a8598;font-size:13px}}
.home-microphone{{display:flex;justify-content:center;align-items:center;gap:10px;margin:-24px auto 30px;color:#647187;font-size:13px}}.home-microphone button{{border:1px solid #cedbfa;border-radius:999px;padding:9px 15px;background:#eef3ff;color:#1d57c6;font-weight:750;cursor:pointer}}.home-microphone button.listening{{background:#e8f8ef;border-color:#bfe8d0;color:#147a56}}
.launcher{{grid-template-columns:repeat(4,1fr);gap:18px}}
.launch,.launch.games,.launch.tv,.launch.learning,.launch.shopping{{min-height:182px;padding:22px;border-radius:24px;background:#fff;border:1px solid #e5eaf1;box-shadow:0 8px 26px #2c3b5510;color:var(--text)}}
.launch:hover{{transform:translateY(-5px);border-color:#cdd9ed;box-shadow:0 18px 40px #2a3b5b20}}
.launch .icon{{display:grid;place-items:center;width:52px;height:52px;font-size:29px;border-radius:17px;background:#f0f3ff}}
.launch.tv .icon{{background:#eaf7ff}}.launch.learning .icon{{background:#eafaf2}}.launch.shopping .icon{{background:#fff4e7}}
.launch strong{{font-size:21px;color:#19243b}}
.launch span span{{color:#707c91}}
.workspace-launcher{{grid-template-columns:repeat(3,1fr);margin-top:18px}}
.workspace-heading{{display:flex;align-items:end;justify-content:space-between;gap:18px;margin:40px 0 14px}}
.workspace-heading h2{{margin:0;color:#1d2940;font-size:23px}}.workspace-heading p{{margin:4px 0 0}}
.workspace-state{{padding:8px 12px;border-radius:999px;background:#ecfbf4;color:#13885f;font-size:12px;font-weight:750;white-space:nowrap}}
.workspace-state.locked{{background:#f3f5f9;color:#707c91}}
.launch.workspace{{min-height:142px}}
.launch.workspace .icon{{background:#eef4ff}}
.launch.workspace.locked{{background:#fafbfc}}
.launch.workspace.locked strong:after{{content:' · Locked';color:#8993a5;font-size:11px;font-weight:700}}
.home-phone{{margin-top:42px;padding-top:32px;border-top:1px solid #e3e8f0}}.connection-health{{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:0 0 24px;padding:18px 20px;background:#fff;border:1px solid #dfe6ef;border-radius:20px;box-shadow:0 8px 28px #2b3a5210}}.connection-health strong{{display:block;color:#18243a;font-size:18px}}.connection-health span{{display:block;color:#6e7a8f;margin-top:4px}}.connection-health[data-status="connected"] .health-dot{{color:#169567}}.connection-health[data-status="recovering"] .health-dot{{color:#ed8b00}}#connection-retry{{background:#eef4ff;color:#155bc5;border-color:#d5e3fb;white-space:nowrap}}
.section-intro h2{{color:#1d2940}}.section-intro p{{color:#758096}}
.phone-beacon{{background:#fff;border-color:#e1e7ef;box-shadow:0 8px 28px #2b3a5210}}
.phone-beacon strong{{color:#168a66}}.phone-beacon p{{color:#6f7b90}}a,code{{color:#1769d2}}
#nodes-view{{margin-top:34px}}.devices-nav{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}}.devices-nav button{{background:#eef4ff;color:#155bc5;border-color:#d5e3fb}}.devices-nav h1{{margin:0;font-size:31px}}.devices-nav p{{margin:5px 0 0}}
.summary{{margin-top:20px}}.metric,.node,.notice{{background:#fff;border-color:#e1e7ef;box-shadow:0 5px 18px #33415b0d}}.metric strong{{color:#1769d2}}.metric span,dt,.node p,.notice p{{color:#6e7a8f}}
.role{{background:#e9f3ff;color:#1263b4}}.role.mother{{background:#fff3da;color:#a16300}}.role.edge{{background:#e8f8f0;color:#147a56}}
.toolbar button,.enroll,.probe,.webos-pair,.tv-canvas{{color:#fff}}
/* Pilot mark: a simple forward-moving jet silhouette, shared with the TV surface. */
.welcome{{position:relative}}.welcome:before{{content:'';color:transparent;font-size:0;background:#4285f4;background-image:conic-gradient(from 210deg,#4285f4,#7c4dff,#ea4335,#fbbc05,#34a853,#4285f4)}}.welcome:after{{content:'';position:absolute;top:17px;left:50%;width:42px;height:42px;transform:translateX(-50%);background:#fff;-webkit-clip-path:polygon(50% 2%,58% 28%,94% 49%,94% 60%,58% 49%,58% 77%,72% 90%,72% 98%,50% 89%,28% 98%,28% 90%,42% 77%,42% 49%,6% 60%,6% 49%,42% 28%);clip-path:polygon(50% 2%,58% 28%,94% 49%,94% 60%,58% 49%,58% 77%,72% 90%,72% 98%,50% 89%,28% 98%,28% 90%,42% 77%,42% 49%,6% 60%,6% 49%,42% 28%);filter:drop-shadow(0 2px 2px #17315b35)}}
.welcome:before{{background:#0b2a55;background-image:linear-gradient(145deg,#071a35 0%,#1557d6 52%,#29a9ff 100%)}}.welcome:after{{top:19px;width:50px;height:38px;transform:translateX(-50%) rotate(-5deg);-webkit-clip-path:polygon(2% 56%,27% 43%,38% 41%,48% 46%,68% 45%,81% 33%,88% 7%,98% 7%,94% 44%,99% 48%,99% 63%,75% 69%,68% 84%,57% 84%,53% 69%,35% 68%,32% 77%,24% 75%,23% 66%,5% 64%,0% 59%);clip-path:polygon(2% 56%,27% 43%,38% 41%,48% 46%,68% 45%,81% 33%,88% 7%,98% 7%,94% 44%,99% 48%,99% 63%,75% 69%,68% 84%,57% 84%,53% 69%,35% 68%,32% 77%,24% 75%,23% 66%,5% 64%,0% 59%)}}
@media(max-width:760px){{main{{padding:22px 18px 60px}}.welcome{{margin-top:26px}}.welcome h2{{font-size:32px}}.launcher{{grid-template-columns:1fr 1fr}}.workspace-heading{{display:block}}.workspace-state{{display:inline-block;margin-top:10px;white-space:normal}}}}
@media(max-width:520px){{.launcher{{grid-template-columns:1fr}}.ask-row{{grid-template-columns:1fr auto}}.devices-nav{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><main>
<header><div><div class="eyebrow">Tessaris · Your local intelligence</div><h1>Pilot</h1><p>Your intelligent home, ready when you are.</p><a class="brain-link" href="/brain">How the second brain works →</a></div><div><div class="live">● Pilot online</div><p>{html.escape(voice_label)}</p></div></header>
<section id="home-view" class="view">
 <div class="welcome"><h2>What would you like to do?</h2><p>Choose an experience or ask Pilot naturally.</p></div>
 <form id="home-search" class="ask-box"><label for="home-query">Ask Pilot anything</label><div class="ask-row"><input id="home-query" maxlength="300" autocomplete="off" placeholder="Ask Pilot anything…"><button type="submit">Ask Pilot</button><button type="button" class="god-view" data-launch="god_view"><span>🌍</span> God View</button></div><p id="home-result">Search, plan, learn, compare, control your connected home, or explore the living planet.</p></form>
 <div class="home-microphone"><span id="home-voice-state">Pilot microphone is checking…</span><button id="home-voice-toggle" type="button">Turn on microphone</button></div>
 <section class="launcher" aria-label="Pilot experiences">
  {experience_launcher}
 </section>
 <div class="workspace-heading"><div><h2>Your workspace</h2><p>Personal surfaces follow the signed identity currently controlling the television.</p></div><span class="workspace-state {workspace_state_class}">{workspace_state_text}</span></div>
 <section class="launcher workspace-launcher" aria-label="Pilot private workspace">
  {workspace_launcher}
 </section>
 <div id="connection-health" class="connection-health" data-status="starting"><div><strong><span class="health-dot">●</span> Checking your TV</strong><span id="connection-message">Pilot is confirming the television connection…</span></div><button id="connection-retry" type="button">Reconnect now</button></div>
 <section class="home-phone"><div class="section-intro"><div><h2>Use your phone as the private controller</h2><p>Connect once. The same private link will keep working after Pilot restarts.</p></div></div>{phone_beacon}</section>
 <section class="intelligence-picker"><h2>Pilot intelligence</h2><p>Choose the maximum route Pilot may use. Local capability is always tried first.</p><div class="intelligence-options">
  <button class="intelligence-option {'active' if intelligence_mode == 'native' else ''}" data-intelligence-mode="native"><strong>AION Native</strong><span>Local intelligence and public evidence. No paid AI required.</span></button>
  <button class="intelligence-option {'active' if intelligence_mode == 'gemini' else ''}" data-intelligence-mode="gemini"><strong>AION + Gemini</strong><span>Gemini is {html.escape(gemini_state)}. Premium providers remain off.</span></button>
  <button class="intelligence-option {'active' if intelligence_mode == 'boost' else ''}" data-intelligence-mode="boost"><strong>Pilot Boost</strong><span>Premium reasoning is allowed. OpenAI is {html.escape(openai_state)}.</span></button>
 </div><p id="intelligence-result">Current mode: {html.escape(str(intelligence.get('label') or 'AION Native'))}. Provider keys remain on the mother brain.</p></section>
</section>
<section id="nodes-view" class="view" hidden><div class="devices-nav"><div><h1>IoT &amp; Devices</h1><p>Connected equipment, discovery, permissions, capabilities, and diagnostics.</p></div><button type="button" data-local-view="home-view">← Pilot Home</button></div>
<section class="summary">
 <div class="metric"><strong>{len(nodes)}</strong><span>fabric nodes</span></div>
 <div class="metric"><strong>{ledger.get('capability_capsules',0)}</strong><span>capability capsules</span></div>
 <div class="metric"><strong>{ledger.get('delta_ledger',0)+ledger.get('stream_ledger',0)}</strong><span>accepted updates</span></div>
 <div class="metric">{saving_card}</div>
</section>
<div class="toolbar"><h2>Fabric topology</h2><div><button id="scan">Discover nearby devices</button><span id="scan-status"></span></div></div><section class="nodes">{''.join(cards)}</section>
<section class="notice"><h2>AION TV Intelligence</h2><p>Say <strong>“Pilot, take over the TV”</strong>, “Pilot, show the device mesh”, “Pilot, show the Boardroom”, “Pilot, give me a briefing”, “Pilot, movie mode”, or “Pilot, open games”. The TV Canvas is a temporary read-only display; control keys and private COMDEX data remain on this Mac.</p><p><strong>Microphone privacy:</strong> say “Pilot, sleep” to close the microphone completely. It cannot hear a wake command while asleep; use the local button below to resume.</p><p><button id="voice-sleep">Turn microphone off</button> <button id="voice-resume">Resume microphone</button> <button class="voice-setting" data-quiet="true">Quiet mode</button> <button class="voice-setting" data-quiet="false">Spoken replies</button></p><p><label>Local voice <select id="voice-name">{voice_options}</select></label> <label>Quiet from <input id="quiet-start" type="time" value="{quiet_start}"></label> <label>until <input id="quiet-end" type="time" value="{quiet_end}"></label> <button id="save-voice-preferences">Save voice settings</button></p><p>Speak open-ended outcomes such as “Pilot, compare family hotels in Granada and prepare a booking” or “Pilot, find the best ladder and prepare the purchase”. AION now observes the foreground app, builds a persistent plan, researches options, and stops before a booking, purchase, message, or calendar change. Consequential actions continue on the <a href="{html.escape(companion_service.public_url if companion_service else '#')}">private phone companion</a>.</p><p>For research, say “Pilot, find me extendable ladders”, “Pilot, open the first result”, or “Pilot, show my results again”. On Netflix, ask for a title naturally or say “Pilot, go back”.</p><p>Standard controls include volume, mute, playback, HDMI switching, Netflix, YouTube and the allowlisted GeForce NOW Games surface. Raw microphone audio remains local and is not retained. Voice volume is capped at 50; power remains blocked. Purchases, bookings, messages and calendar changes require private approval and an authorized service adapter.</p><p id="voice-diagnostics">{html.escape(voice_details)}</p><p><strong>Discovery safety:</strong> AION listens for standard advertisements, sends one bounded SSDP discovery request, reads the existing neighbor cache, and inspects known Bluetooth records. It may download advertised local descriptors with strict limits.</p><p>Machine status: <code>/status</code> · Voice status: <code>/api/voice</code> · Discovery evidence: <code>/api/discovery</code></p></section>
</section>
<script>
// A locked shared dashboard observes only the lock state. Once a trusted
// Personal phone acquires it, reload once to render that phone's private tiles.
const sharedDashboardLocked = {str(not bool(active_identity.get("persona_id"))).lower()};
if (sharedDashboardLocked) setInterval(() => location.reload(), 10000);
document.querySelectorAll('[data-local-view]').forEach(control=>control.addEventListener('click',()=>{{document.querySelectorAll('.view').forEach(view=>view.hidden=view.id!==control.dataset.localView);window.scrollTo({{top:0,behavior:'smooth'}})}}));
async function dashboardAction(command,arguments={{}}){{const response=await fetch('/api/dashboard/action',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1','Content-Type':'application/json'}},body:JSON.stringify({{command,arguments}})}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Pilot could not complete that request');return result}}
const homeQuery=document.getElementById('home-query'),homeResult=document.getElementById('home-result');
const homeVoiceToggle=document.getElementById('home-voice-toggle'),homeVoiceState=document.getElementById('home-voice-state');
async function refreshVoiceControl(){{if(!homeVoiceToggle||!homeVoiceState)return;try{{const voice=await (await fetch('/api/voice',{{cache:'no-store'}})).json();const listening=['listening','hearing','awake','active'].includes(String(voice.activity_state||'').toLowerCase());homeVoiceToggle.textContent=listening?'Turn microphone off':'Turn on microphone';homeVoiceToggle.classList.toggle('listening',listening);homeVoiceState.textContent=listening?'Pilot is listening locally.':'Pilot microphone is off.'}}catch(error){{homeVoiceState.textContent='Pilot microphone is unavailable.'}}}}
async function setVoiceCapture(enabled,control){{if(control)control.disabled=true;try{{const response=await fetch(enabled?'/api/voice/resume':'/api/voice/sleep',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Voice control failed');await refreshVoiceControl()}}catch(error){{if(homeVoiceState)homeVoiceState.textContent=error.message}}finally{{if(control)control.disabled=false}}}}
if(homeVoiceToggle)homeVoiceToggle.addEventListener('click',()=>setVoiceCapture(homeVoiceToggle.textContent==='Turn on microphone',homeVoiceToggle));refreshVoiceControl();
document.querySelectorAll('[data-launch]').forEach(tile=>tile.addEventListener('click',async()=>{{tile.disabled=true;const title=tile.querySelector('strong');homeResult.textContent='Pilot is opening '+(title?title.textContent:tile.textContent.trim())+'…';try{{const result=await dashboardAction(tile.dataset.launch,tile.dataset.launch==='education_start'?{{profile_id:'explorer_a'}}:{{}});homeResult.textContent=result.spoken_response||'Ready on the television.'}}catch(error){{homeResult.textContent=error.message}}finally{{tile.disabled=false}}}}));
document.querySelector('[data-mode="shopping"]').addEventListener('click',()=>{{homeQuery.value='Find and compare ';homeQuery.focus();homeQuery.setSelectionRange(homeQuery.value.length,homeQuery.value.length);homeResult.textContent='Tell Pilot what you are looking for. It will research and prepare, but not purchase without private approval.'}});
document.getElementById('home-search').addEventListener('submit',async event=>{{event.preventDefault();const text=homeQuery.value.trim();if(!text)return;const submit=event.currentTarget.querySelector('button');submit.disabled=true;homeResult.textContent='Pilot is thinking…';try{{const result=await dashboardAction('ask',{{text}});homeResult.textContent=result.spoken_response||'Pilot has prepared the result.';homeQuery.value=''}}catch(error){{homeResult.textContent=error.message}}finally{{submit.disabled=false}}}});
document.querySelectorAll('[data-intelligence-mode]').forEach(control=>control.addEventListener('click',async()=>{{const label=document.getElementById('intelligence-result');control.disabled=true;label.textContent='Updating the mother-brain route…';try{{const response=await fetch('/api/intelligence/mode',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1','Content-Type':'application/json'}},body:JSON.stringify({{mode:control.dataset.intelligenceMode}})}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Intelligence mode could not be changed');document.querySelectorAll('[data-intelligence-mode]').forEach(item=>item.classList.toggle('active',item===control));label.textContent='Current mode: '+result.label+'. Local capability remains first.'}}catch(error){{label.textContent=error.message}}finally{{control.disabled=false}}}}));
const button=document.getElementById('scan'); const label=document.getElementById('scan-status');
button.addEventListener('click',async()=>{{button.disabled=true;label.textContent='Listening for advertised devices…';try{{const response=await fetch('/api/discovery/scan',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Scan failed');label.textContent=`Found ${{result.run.observations.length}} observations. Reloading…`;setTimeout(()=>location.reload(),500)}}catch(error){{label.textContent=error.message;button.disabled=false}}}});
document.querySelectorAll('.enroll').forEach(item=>item.addEventListener('click',async()=>{{if(!confirm('Enroll this discovered device through a local gateway for evidenced read-only tests? No mutating controls will be granted.'))return;item.disabled=true;item.textContent='Enrolling…';try{{const response=await fetch(`/api/nodes/${{item.dataset.node}}/enroll-readonly`,{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Enrollment failed');item.textContent=`Enrolled ${{result.read_only_capabilities}} read capabilities`;setTimeout(()=>location.reload(),700)}}catch(error){{item.textContent=error.message;item.disabled=false}}}}));
document.querySelectorAll('.probe').forEach(item=>item.addEventListener('click',async()=>{{if(!confirm('Send one schema-verified read-only status query to this enrolled device?'))return;item.disabled=true;item.textContent='Reading device state…';try{{const response=await fetch(`/api/nodes/${{item.dataset.node}}/probe-readonly`,{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Probe failed');item.textContent=`${{result.action_name}}: ${{JSON.stringify(result.values)}}`}}catch(error){{item.textContent=error.message;item.disabled=false}}}}));
document.querySelectorAll('.webos-pair').forEach(item=>item.addEventListener('click',async()=>{{if(!confirm('The LG television may show an AION connection request. Approve it with the TV remote. This step reads volume state only and executes no control action.'))return;item.disabled=true;item.textContent='Approve AION on the television…';try{{const response=await fetch(`/api/nodes/${{item.dataset.node}}/pair-webos-readonly`,{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Pairing failed');item.textContent=`Paired: ${{JSON.stringify(result.proof_values)}}`;setTimeout(()=>location.reload(),1200)}}catch(error){{item.textContent=error.message;item.disabled=false}}}}));
document.querySelectorAll('.tv-canvas').forEach(item=>item.addEventListener('click',async()=>{{item.disabled=true;item.textContent='Opening Pilot on the television…';try{{const response=await fetch('/api/tv/canvas/open',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Pilot TV failed');item.textContent='Pilot opened on TV';setTimeout(()=>{{item.disabled=false;item.textContent='Put Pilot on this TV'}},2500)}}catch(error){{item.textContent=error.message;item.disabled=false}}}}));
const voiceDiagnostics=document.getElementById('voice-diagnostics');
if(voiceDiagnostics) setInterval(async()=>{{try{{const voice=await (await fetch('/api/voice')).json();voiceDiagnostics.textContent=`State ${{voice.activity_state||'off'}} · Mic level ${{voice.audio_rms||0}} · Heard ${{voice.heard_utterances||0}} utterances · Wake matches ${{voice.wake_matches||0}} · Last heard: ${{voice.last_heard_transcript||'nothing yet'}} · Result: ${{voice.last_result||'waiting'}}`}}catch(error){{}}}},1000);
document.querySelectorAll('.voice-setting').forEach(control=>control.addEventListener('click',async()=>{{control.disabled=true;try{{const response=await fetch('/api/voice/settings',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1','Content-Type':'application/json'}},body:JSON.stringify({{quiet_mode:control.dataset.quiet==='true'}})}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Voice preference failed');if(voiceDiagnostics)voiceDiagnostics.textContent=result.quiet_mode?'Quiet mode enabled':'Spoken replies enabled'}}catch(error){{alert(error.message)}}finally{{control.disabled=false}}}}));
const saveVoicePreferences=document.getElementById('save-voice-preferences');if(saveVoicePreferences)saveVoicePreferences.addEventListener('click',async()=>{{saveVoicePreferences.disabled=true;try{{const response=await fetch('/api/voice/settings',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1','Content-Type':'application/json'}},body:JSON.stringify({{voice_name:document.getElementById('voice-name').value,quiet_start:document.getElementById('quiet-start').value,quiet_end:document.getElementById('quiet-end').value}})}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Voice preference failed');voiceDiagnostics.textContent='Voice settings saved locally.'}}catch(error){{alert(error.message)}}finally{{saveVoicePreferences.disabled=false}}}});
const healthCard=document.getElementById('connection-health'),healthMessage=document.getElementById('connection-message'),healthRetry=document.getElementById('connection-retry');
async function refreshConnectionHealth(){{if(!healthCard)return;try{{const state=await(await fetch('/api/connection-health',{{cache:'no-store'}})).json();healthCard.dataset.status=state.status||'recovering';healthCard.querySelector('strong').lastChild.textContent=state.status==='connected'?' TV connected':' Reconnecting to TV';healthMessage.textContent=state.message||'Pilot is checking the television.'}}catch(error){{healthCard.dataset.status='recovering';healthMessage.textContent='Pilot is restarting the local connection.'}}}}
if(healthRetry)healthRetry.addEventListener('click',async()=>{{healthRetry.disabled=true;const original=healthRetry.textContent;healthRetry.textContent='Reconnecting…';healthMessage.textContent='Checking the TV connection now…';try{{const response=await fetch('/api/connection-health/retry',{{method:'POST',headers:{{'X-AION-Fabric':'dashboard-v1'}}}});const state=await response.json();if(!response.ok)throw new Error(state.error||'TV reconnection failed');healthCard.dataset.status=state.status||'recovering';healthMessage.textContent=state.message||'Pilot is checking the television.'}}catch(error){{healthCard.dataset.status='recovering';healthMessage.textContent=error.message}}finally{{healthRetry.textContent=original;healthRetry.disabled=false}}}});refreshConnectionHealth();setInterval(refreshConnectionHealth,5000);
for(const [id,enabled] of [['voice-sleep',false],['voice-resume',true]]){{const control=document.getElementById(id);if(control)control.addEventListener('click',()=>setVoiceCapture(enabled,control))}}
</script></main></body></html>"""
    return document.encode("utf-8")


def _serve(
    runtime: AionFabricRuntime,
    host: str,
    port: int,
    *,
    demo: Dict[str, Any] | None = None,
    open_browser: bool = False,
    autonomous_discovery: bool = False,
    scan_interval: float = 300.0,
    voice_control: bool = False,
    founder_persona_id: str = "",
    founder_workspace_id: str = "",
) -> None:
    private_state = PrivateServiceState(runtime.base_dir).load()
    supervisor = (
        AutonomousDiscoverySupervisor(runtime, interval_seconds=scan_interval)
        if autonomous_discovery
        else None
    )
    integrated = next(
        (
            node
            for node in runtime.store.list_nodes()
            if node.profile.metadata.get("webos_integration") == "connected"
        ),
        None,
    )
    if integrated is not None:
        existing_rooms = runtime.tv_rooms.snapshot().get("televisions") or []
        existing_room = next((item for item in existing_rooms if item.get("node_id") == integrated.profile.node_id), None)
        runtime.tv_rooms.register(
            node_id=integrated.profile.node_id,
            device_name=integrated.profile.name,
            room_name=str((existing_room or {}).get("room_name") or "Primary TV"),
            endpoint=str(integrated.profile.metadata.get("webos_host") or ""),
            make_default=bool((existing_room or {}).get("default", not existing_rooms)),
        )
    universal_service = UniversalNodeService(
        runtime.universal_node,
        preferred_peer=str(integrated.profile.metadata.get("webos_host") or "") if integrated else None,
    )
    universal_service.start()
    canvas_service: TVCanvasService | None = None
    workspace_gateway: ProviderIndependentWorkspaceGateway | None = None
    surface_authority: SharedSurfaceManifestAuthority | None = None
    if integrated is not None:
        def execute_tv_education(command: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            if command == "start":
                education = runtime.education.start(str(arguments.get("profile_id") or "explorer_a"))
            elif command == "answer":
                education = runtime.education.answer(int(arguments.get("choice_index", -1)))
            elif command == "next":
                current = runtime.education.snapshot()
                session = dict(current.get("session") or {})
                expected_round = int(arguments.get("expected_round", -1))
                if expected_round >= 0 and (
                    int(session.get("round_number", -2)) != expected_round
                    or session.get("phase") != "feedback"
                ):
                    education = current
                else:
                    education = runtime.education.next_round()
            else:
                education = runtime.education.repeat()
            session = dict(education.get("session") or {})
            runtime.store.append_audit(
                "education_tv_remote_interaction",
                {
                    "command": command,
                    "profile_id": str(session.get("profile_id") or ""),
                    "round_number": int(session.get("round_number") or 0),
                },
            )
            return {"accepted": True, "education": education}

        def private_tv_workspace(persona_id: str) -> Dict[str, Any]:
            stream = runtime.pilot_inbox.stream(persona_id=persona_id)
            tasks = [
                {
                    "title": str(item.get("title") or "")[:240],
                    "status": str(item.get("status") or "open"),
                    "assigned_to_me": str(item.get("assignee_persona_id") or "") == persona_id,
                    "created_at": str(item.get("created_at") or ""),
                }
                for item in list(stream.get("tasks") or [])[-20:]
                if str(item.get("title") or "").strip()
            ]
            reminders = [
                {
                    "title": str(item.get("title") or item.get("text") or "Reminder")[:240],
                    "status": str(item.get("status") or "pending"),
                    "trigger": str(item.get("trigger") or ""),
                }
                for item in list(stream.get("reminders") or [])[-10:]
            ]
            return {"tasks": tasks, "reminders": reminders}

        surface_authority = SharedSurfaceManifestAuthority(
            runtime.base_dir, issuer=runtime.identity, identities=runtime.private_identity,
        )
        canvas_service = TVCanvasService(
            runtime.status,
            education_handler=execute_tv_education,
            private_workspace_provider=private_tv_workspace,
            surface_manifest_provider=lambda: surface_authority.issue_home_manifest(surface_id="surface.tv.canvas"),
            presentation_provider=lambda: surface_authority.active_presentation(surface_id="surface.tv.canvas"),
            preferred_peer=str(integrated.profile.metadata.get("webos_host") or "") or None,
            token=private_state["canvas_token"],
            education_action_token=private_state["education_token"],
        )
        canvas_service.start()
    companion_service: CompanionService | None = None
    secure_companion_service: CompanionService | None = None
    unified_mobile_service: MobilePairingService | None = None
    unified_inbox_live_service: UnifiedInboxLiveService | None = None
    companion_tls_material: LocalTLSMaterial | None = None
    if integrated is not None:
        def companion_snapshot() -> Dict[str, Any]:
            snapshot = runtime.tv_agent.snapshot()
            canvas = canvas_service.snapshot() if canvas_service else {}
            belief = runtime.tv_autopilot.snapshot().get("belief", {})
            snapshot["controller"] = {
                "node_id": integrated.profile.node_id,
                "tv_name": canvas.get("tv_name") or integrated.profile.name,
                "volume": canvas.get("tv_volume"),
                "surface": belief.get("surface", "unknown"),
                "view": belief.get("view"),
                "confidence": belief.get("confidence", 0),
                "audit_chain_valid": runtime._cached_audit_chain_valid(),
            }
            snapshot["perception"] = runtime.phone_perception.latest()
            snapshot["netflix_profiles"] = runtime.phone_perception.known_profiles()
            snapshot["navigation"] = runtime.phone_navigation.snapshot()
            snapshot["conversation"] = runtime.conversation_memory.snapshot(channel="private_phone")
            snapshot["household"] = runtime.household.snapshot()
            snapshot["service_execution"] = runtime.service_hub.snapshot()
            snapshot["education"] = runtime.education.snapshot()
            snapshot["gaming"] = runtime.gaming.snapshot(persona_id=str(runtime.local_persona["persona_id"]))
            private_identity = runtime.private_identity.snapshot()
            snapshot["private_identity"] = private_identity
            active_private = dict(private_identity.get("active_shared_identity") or {})
            profiles = list(private_identity.get("profiles") or [])
            viewer_persona_id = str(active_private.get("persona_id") or "")
            snapshot["private_identity_export"] = (
                runtime.private_identity.export(
                    persona_id=viewer_persona_id,
                    requester_persona_id=viewer_persona_id,
                )
                if viewer_persona_id else None
            )
            snapshot["pilot_inbox"] = runtime.pilot_inbox.snapshot(persona_id=viewer_persona_id) if viewer_persona_id else runtime.pilot_inbox.snapshot()
            snapshot["communication"] = runtime.communication.snapshot(persona_id=viewer_persona_id) if viewer_persona_id else {}
            snapshot["calendar_planning"] = runtime.calendar_planning.snapshot(persona_id=viewer_persona_id) if viewer_persona_id else {}
            snapshot["guardian"] = runtime.guardian.snapshot(persona_id=viewer_persona_id) if viewer_persona_id else {}
            snapshot["google_oauth"] = runtime.google_oauth.snapshot(persona_id=viewer_persona_id) if viewer_persona_id else {}
            snapshot["entertainment"] = runtime.entertainment.snapshot()
            snapshot["live_context"] = runtime.live_context.latest()
            snapshot["pilot_moments"] = runtime.pilot_moments.snapshot()
            snapshot["tv_research"] = runtime.tv_research.latest()
            snapshot["screen_understanding"] = runtime.screen_understanding.latest()
            snapshot["provider_metadata"] = runtime.provider_metadata.latest()
            snapshot["observer"] = runtime.observer_sessions.snapshot()
            snapshot["live_news"] = runtime.live_news.latest()
            snapshot["scene_explanation"] = runtime.scene_explanation.latest()
            snapshot["programme_companion"] = runtime.programme_companion.latest()
            snapshot["programme_origins"] = runtime.programme_origins.latest()
            snapshot["live_translation"] = runtime.live_translation.latest()
            snapshot["live_sports"] = runtime.live_sports.latest()
            snapshot["live_events"] = runtime.live_events.status()
            snapshot["live_engagement"] = runtime.live_engagement.snapshot(persona_id=str(runtime.local_persona["persona_id"]))
            snapshot["contextual_companion"] = runtime.contextual_companion.snapshot(persona_id=str(runtime.local_persona["persona_id"]))
            snapshot["private_saves"] = runtime.private_saves.snapshot(
                persona_id=str(runtime.local_persona["persona_id"])
            )
            snapshot["saved_followthrough"] = runtime.saved_followthrough.snapshot(
                persona_id=str(runtime.local_persona["persona_id"])
            )
            snapshot["entertainment_execution"] = runtime.entertainment_execution.snapshot(
                persona_id=str(runtime.local_persona["persona_id"])
            )
            snapshot["entertainment_personalization"] = runtime.entertainment_personalization.snapshot(
                persona_id=str(runtime.local_persona["persona_id"])
            )
            snapshot["verified_navigation"] = runtime.verified_navigation.snapshot()
            snapshot["perception_timeline"] = runtime.perception_timeline.snapshot()
            snapshot["provider_telemetry"] = runtime.provider_telemetry.snapshot(
                persona_id=str(runtime.local_persona["persona_id"])
            )
            snapshot["infrared_climate"] = runtime.infrared_climate.snapshot()
            snapshot["tv_rooms"] = runtime.tv_rooms.snapshot()
            snapshot["tv_reliability"] = runtime.tv_reliability.report(
                device_id=integrated.profile.node_id,
                adapter="lg_webos_gateway",
            )
            snapshot["companion_tls"] = companion_tls_material.public_status() if companion_tls_material else {
                "enabled": False,
                "trust_installation": "unavailable",
            }
            snapshot["secure_companion_url"] = secure_companion_service.public_url if secure_companion_service else None
            approval_id = str(((snapshot.get("active_task") or {}).get("approval") or {}).get("approval_id") or "")
            snapshot["service_proposal"] = runtime.service_hub.for_agent_approval(approval_id) if approval_id else None
            return snapshot

        def decide_agent_task(approval_id: str, approved: bool) -> Dict[str, Any]:
            task = runtime.tv_agent.decide(approval_id, approved=approved)
            service_proposal = runtime.service_hub.for_agent_approval(approval_id)
            persona_id = str(runtime.local_persona["persona_id"])
            if approved and task.get("route") in {"calendar", "communication", "shopping", "booking"}:
                service_name = "email" if task["route"] == "communication" else str(task["route"])
                if service_proposal is None:
                    prepared = dict(task.get("prepared_result") or {})
                    service_proposal = runtime.service_hub.prepare(
                        persona_id=persona_id,
                        service=service_name,
                        action=f"prepare_{service_name}",
                        parameters={
                            "request": str(task.get("request") or "")[:500],
                            "summary": str(prepared.get("summary") or "")[:700],
                            "items": list(prepared.get("items") or [])[:5],
                        },
                        agent_approval_id=approval_id,
                    )
                service_proposal = runtime.service_hub.decide(
                    str(service_proposal["proposal_id"]),
                    persona_id=persona_id,
                    approved=True,
                )
            runtime.store.append_audit(
                "agent_private_approval_decided",
                {
                    "task_id": task["task_id"],
                    "approval_id": approval_id,
                    "decision": "approved" if approved else "rejected",
                    "external_action_executed": False,
                },
            )
            return {**task, "service_proposal": service_proposal}

        def execute_phone_command(command: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            if command == "navigation_retry":
                route = runtime.verified_navigation.current_route()
                result = runtime.execute_companion_command(
                    str(route["command"]),
                    dict(route.get("arguments") or {}),
                    canvas_url=canvas_service.display_url if canvas_service else None,
                    canvas_view_callback=canvas_service.set_view if canvas_service else None,
                    companion_url=(secure_companion_service.public_url if secure_companion_service else companion_service.public_url) if companion_service else None,
                    continue_verified_navigation=True,
                )
                transaction = dict(result.get("verified_navigation") or {})
                result["spoken_response"] = (
                    "Recovery route delivered. Capture the television again so Pilot can verify the outcome."
                    if transaction.get("status") == "awaiting_after_observation"
                    else str(result.get("spoken_response") or "Recovery route checked.")
                )
                return result
            if command in {"entertainment_prepare", "entertainment_continue", "entertainment_execute"}:
                persona_id = str(runtime.local_persona["persona_id"])
                if command == "entertainment_prepare":
                    discovery = runtime.entertainment.latest() or {}
                    items = [item for item in list(discovery.get("items") or []) if isinstance(item, dict)]
                    index = int(arguments.get("item_index") or 0)
                    if index < 0 or index >= len(items):
                        raise ValueError("Choose an available entertainment result")
                    execution = runtime.entertainment_execution.prepare(item=items[index], persona_id=persona_id)
                    spoken = "That exact official provider route is ready for private confirmation. Subscription access is still unknown."
                    event_type = "private_entertainment_route_prepared"
                elif command == "entertainment_continue":
                    execution = runtime.entertainment_execution.prepare_continue(persona_id=persona_id)
                    spoken = "Your last verified provider route is ready to continue. Confirm it privately before Pilot opens it."
                    event_type = "private_entertainment_continue_prepared"
                else:
                    execution_id = str(arguments.get("execution_id") or "")
                    runtime.entertainment_execution.confirm(execution_id, persona_id=persona_id)
                    result = runtime.execute_private_entertainment(execution_id, persona_id=persona_id)
                    execution = result["entertainment_execution"]
                    spoken = (
                        "The official provider route is open on the television. Pilot has not claimed playback because the provider did not expose title and playing evidence."
                        if execution.get("provider_open_verified") and not execution.get("playback_verified")
                        else "The device attempt could not be verified."
                    )
                    event_type = "private_entertainment_route_confirmed_and_attempted"
                runtime.store.append_audit(
                    event_type,
                    {
                        "execution_id": execution.get("execution_id"),
                        "persona_id": persona_id,
                        "provider": execution.get("provider"),
                        "route_hash": execution.get("route_hash"),
                        "status": execution.get("status"),
                        "playback_verified": bool(execution.get("playback_verified")),
                        "raw_url_recorded_in_audit": False,
                    },
                )
                return {"accepted": True, "spoken_response": spoken, "entertainment_execution": execution}
            if command in {"entertainment_memory_claim", "entertainment_watchlist_add"}:
                persona_id = str(runtime.local_persona["persona_id"])
                if command == "entertainment_memory_claim":
                    record = runtime.entertainment_personalization.claim_history(
                        str(arguments.get("pending_id") or ""), persona_id=persona_id,
                        share_with_household=bool(arguments.get("share_with_household")),
                    )
                    spoken = "That viewing preference now belongs to this private identity."
                    event_type = "entertainment_preference_claimed"
                else:
                    telemetry = dict(runtime.provider_telemetry.latest(persona_id=persona_id) or {})
                    content = dict(telemetry.get("content") or {})
                    if not content.get("title"):
                        raise ValueError("An exact signed provider title is required before adding a watchlist item")
                    record = runtime.entertainment_personalization.add_watchlist(
                        persona_id=persona_id, title=str(content["title"]), provider=str(telemetry.get("provider") or ""),
                        visibility=str(arguments.get("visibility") or "private"),
                    )
                    spoken = "That exact provider title is saved to your private watchlist."
                    event_type = "entertainment_watchlist_item_added"
                runtime.store.append_audit(event_type, {"persona_id": persona_id, "record_hash": record["record_hash"], "raw_private_history_recorded": False})
                return {"accepted": True, "spoken_response": spoken, "entertainment_personalization": record}
            if command in {"saved_research", "saved_action", "saved_action_details", "saved_action_decide"}:
                persona_id = str(runtime.local_persona["persona_id"])
                followthrough = runtime.saved_followthrough
                if command in {"saved_research", "saved_action"}:
                    save_id = str(arguments.get("save_id") or "")
                    saved_item = runtime.private_saves.get_saved(save_id, persona_id=persona_id)
                    if command == "saved_research":
                        result_followthrough = followthrough.research(
                            item=saved_item,
                            persona_id=persona_id,
                            researcher=runtime.tv_research,
                        )
                        event_type = "saved_item_researched_privately"
                        spoken = "Research is ready on this private phone. Nothing external was changed."
                    else:
                        result_followthrough = followthrough.prepare_action(
                            item=saved_item,
                            persona_id=persona_id,
                            action=str(arguments.get("action") or ""),
                            service_hub=runtime.service_hub,
                        )
                        event_type = "saved_item_followthrough_prepared"
                        spoken = (
                            "A separate private service proposal is ready. Review its exact scope before approval."
                            if result_followthrough.get("private_approval_created")
                            else "A private local draft is ready. No external action was taken."
                        )
                else:
                    proposal_id = str(arguments.get("proposal_id") or "")
                    if command == "saved_action_details":
                        proposal = runtime.service_hub.update_details(
                            proposal_id,
                            persona_id=persona_id,
                            details=dict(arguments.get("details") or {}),
                        )
                        event_type = "saved_item_service_details_updated"
                        spoken = "The exact private scope is complete and ready for approval." if proposal["status"] == "awaiting_private_approval" else "More private details are required."
                    else:
                        proposal = runtime.service_hub.decide(
                            proposal_id,
                            persona_id=persona_id,
                            approved=bool(arguments.get("approved")),
                        )
                        event_type = "saved_item_service_proposal_decided"
                        spoken = "The proposal was approved, but no external action has executed." if proposal["status"] == "approved_pending_adapter" else "The proposal was rejected."
                    result_followthrough = followthrough.refresh_proposal(proposal, persona_id=persona_id)
                runtime.store.append_audit(
                    event_type,
                    {
                        "followthrough_id": result_followthrough.get("followthrough_id"),
                        "save_id": result_followthrough.get("save_id"),
                        "persona_id": persona_id,
                        "kind": result_followthrough.get("kind"),
                        "action": result_followthrough.get("action"),
                        "record_hash": result_followthrough.get("record_hash"),
                        "external_action_executed": False,
                        "raw_private_content_recorded_in_audit": False,
                    },
                )
                return {"accepted": True, "spoken_response": spoken, "saved_followthrough": result_followthrough}
            if command in {"private_save_claim", "private_save_delete"}:
                save_id = str(arguments.get("save_id") or "")
                persona_id = str(runtime.local_persona["persona_id"])
                if command == "private_save_claim":
                    private_save = runtime.private_saves.claim(save_id, persona_id=persona_id)
                    event_type = "programme_private_save_claimed"
                    spoken = f"Saved {private_save['title']} to your private Pilot memory."
                else:
                    private_save = runtime.private_saves.delete(save_id, persona_id=persona_id)
                    event_type = "programme_private_save_deleted"
                    spoken = "That item was deleted from your private Pilot memory."
                runtime.store.append_audit(
                    event_type,
                    {
                        "save_id": save_id,
                        "persona_id": persona_id,
                        "category": private_save.get("category"),
                        "evidence_hash": private_save.get("evidence_hash"),
                        "raw_content_recorded_in_audit": False,
                        "external_action_executed": False,
                    },
                )
                return {"accepted": True, "spoken_response": spoken, "private_save": private_save}
            if command == "live_watch_claim":
                persona_id = str(runtime.local_persona["persona_id"])
                watch = runtime.live_engagement.claim_watch(str(arguments.get("watch_id") or ""), persona_id=persona_id)
                runtime.store.append_audit(
                    "live_event_watch_claimed",
                    {
                        "watch_id": watch["watch_id"],
                        "persona_id": persona_id,
                        "threshold": watch["threshold"],
                        "external_push_enabled": False,
                    },
                )
                return {"accepted": True, "spoken_response": "The close-match alert is active for this private Pilot identity.", "live_engagement": watch}
            if command in {"companion_configure", "companion_support_claim", "companion_handoff_phone"}:
                persona_id = str(runtime.local_persona["persona_id"])
                if command == "companion_configure":
                    result_companion = runtime.contextual_companion.configure(
                        persona_id=persona_id,
                        enabled=bool(arguments.get("enabled")),
                        frequency=str(arguments.get("frequency") or "balanced"),
                        quiet_start=str(arguments.get("quiet_start") or "21:00"),
                        quiet_end=str(arguments.get("quiet_end") or "08:00"),
                        reading_level=str(arguments.get("reading_level") or "standard"),
                        large_controls=bool(arguments.get("large_controls")),
                    )
                    event_type = "contextual_companion_preferences_updated"
                    spoken = "Your private companion, quiet-time and accessibility preferences are saved."
                elif command == "companion_support_claim":
                    result_companion = runtime.contextual_companion.claim_support(str(arguments.get("support_id") or ""), persona_id=persona_id)
                    event_type = "contextual_companion_support_claimed"
                    spoken = "This support conversation is now private to this phone identity."
                else:
                    conversation = runtime.conversation_memory.snapshot(channel="shared_tv")
                    result_companion = runtime.contextual_companion.prepare_handoff(
                        persona_id=persona_id,
                        source="shared_tv",
                        destination="private_phone",
                        objective=str((conversation.get("active_task") or {}).get("objective") or "Continue this conversation"),
                        summary="Continue the current shared-room conversation privately.",
                    )
                    event_type = "contextual_companion_handoff_prepared"
                    spoken = "The current conversation is ready to continue privately on this phone."
                runtime.store.append_audit(event_type, {"persona_id": persona_id, "record_hash": result_companion.get("record_hash") or result_companion.get("handoff_hash"), "raw_transcript_recorded": False})
                return {"accepted": True, "spoken_response": spoken, "contextual_companion": result_companion}
            if command in {"moment_recipient", "moment_send", "moment_revoke", "moment_delete", "moment_report"}:
                moment_id = str(arguments.get("moment_id") or "")
                persona_id = str(runtime.local_persona["persona_id"])
                moments = runtime.pilot_moments
                if command == "moment_recipient":
                    result_moment = moments.set_recipient(
                        moment_id,
                        persona_id=persona_id,
                        route=str(arguments.get("route") or ""),
                        recipient=str(arguments.get("recipient") or ""),
                    )
                    event_type = "pilot_moment_recipient_bound"
                    spoken = "Recipient saved privately. Review the exact card, recipient, and sources before pressing Send."
                elif command == "moment_send":
                    result_moment = moments.send(
                        moment_id,
                        persona_id=persona_id,
                        preview_hash=str(arguments.get("preview_hash") or ""),
                    )
                    event_type = "pilot_moment_send_confirmed"
                    spoken = (
                        "Moment delivered and verified."
                        if result_moment.get("delivery_state") == "delivered"
                        else "Your Send approval is recorded, but no authorized delivery account is connected. Nothing was sent."
                    )
                elif command == "moment_revoke":
                    result_moment = moments.revoke(moment_id, persona_id=persona_id)
                    event_type = "pilot_moment_revoked"
                    spoken = "The Moment is revoked."
                elif command == "moment_delete":
                    result_moment = moments.delete(moment_id, persona_id=persona_id)
                    event_type = "pilot_moment_deleted"
                    spoken = "The private Moment data was deleted."
                else:
                    result_moment = moments.report_abuse(
                        moment_id, persona_id=persona_id, reason=str(arguments.get("reason") or "unwanted")
                    )
                    event_type = "pilot_moment_abuse_reported"
                    spoken = "The Moment was reported and blocked."
                runtime.store.append_audit(
                    event_type,
                    {
                        "moment_id": moment_id,
                        "delivery_state": result_moment.get("delivery_state"),
                        "recipient_hash": result_moment.get("recipient_hash"),
                        "raw_recipient_recorded_in_audit": False,
                    },
                )
                return {"accepted": True, "spoken_response": spoken, "moment": result_moment}
            if canvas_service and canvas_service.snapshot().get("view") == "god_view" and command in {
                "up", "down", "left", "right", "enter", "back",
            }:
                control = canvas_service.send_god_control("select" if command == "enter" else command)
                runtime.store.append_audit(
                    "god_view_private_controller_command",
                    {"command": command, "sequence": control["sequence"], "source": "private_phone"},
                )
                return {
                    "accepted": True,
                    "spoken_response": "God View control sent.",
                    "god_view_control": control,
                }
            if canvas_service and command.startswith("god_") and command != "god_view":
                god_command = command.removeprefix("god_")
                control = canvas_service.send_god_control(god_command, arguments)
                runtime.store.append_audit(
                    "god_view_private_controller_command",
                    {"command": god_command, "sequence": control["sequence"], "source": "private_phone"},
                )
                return {
                    "accepted": True,
                    "spoken_response": "God View control sent.",
                    "god_view_control": control,
                }
            result = runtime.execute_companion_command(
                command,
                arguments,
                canvas_url=canvas_service.public_url if canvas_service else None,
                canvas_view_callback=canvas_service.set_view if canvas_service else None,
                companion_url=(secure_companion_service.entry_url if secure_companion_service else companion_service.entry_url) if companion_service else None,
            )
            if canvas_service:
                canvas_service.record_voice_result(f"Phone: {command}", result)
            return result

        def accept_phone_perception(payload: bytes, media_type: str, observer_token: str | None = None) -> Dict[str, Any]:
            return runtime.accept_phone_perception(payload, media_type, observer_token)

        def deliver_private_tv_text(value: str, purpose: str) -> Dict[str, Any]:
            return runtime.send_private_tv_text(value, purpose=purpose)

        voice_holder: Dict[str, VoiceControlService | None] = {"service": None}

        def accept_private_phone_voice(payload: bytes, media_type: str) -> Dict[str, Any]:
            service = voice_holder["service"]
            if service is None:
                raise RuntimeError("Local Pilot speech is not ready")
            transcript = service.transcribe_push_to_talk(payload, media_type)
            lowered = transcript.lower().strip()
            effective = transcript if lowered.startswith(("pilot", "hey pilot", "hi pilot", "hello pilot", "ok pilot", "okay pilot")) else f"Pilot {transcript}"
            result = runtime.execute_voice_command(
                effective,
                canvas_url=canvas_service.public_url if canvas_service else None,
                canvas_view_callback=canvas_service.set_view if canvas_service else None,
                companion_url=(secure_companion_service.entry_url if secure_companion_service else companion_service.entry_url) if companion_service else None,
                conversation_channel="private_phone",
                persona_id=str(runtime.local_persona["persona_id"]),
                recent_context=service.recent_context(exclude_latest=False),
            )
            runtime.store.append_audit(
                "private_phone_push_to_talk",
                {
                    "transcript_hash": canonical_hash(transcript),
                    "audio_retained": False,
                    "channel": "private_phone",
                    "accepted": bool(result.get("accepted")),
                },
            )
            if canvas_service:
                canvas_service.record_voice_result("Private phone voice", result)
            return {**result, "transcript": transcript, "audio_retained": False}

        companion_service = CompanionService(
            companion_snapshot,
            decide_agent_task,
            command_handler=execute_phone_command,
            perception_handler=accept_phone_perception,
            private_text_handler=deliver_private_tv_text,
            voice_handler=accept_private_phone_voice,
            preferred_peer=str(integrated.profile.metadata.get("webos_host") or "") or None,
            token=private_state["companion_token"],
            csrf_token=private_state["companion_csrf"],
            pair_code=private_state["companion_pair_code"],
        )
        try:
            companion_tls_material = LocalTLSAuthority(runtime.base_dir).ensure(
                address=companion_service.address,
                hostname=socket.gethostname(),
            )
            secure_companion_service = CompanionService(
                companion_snapshot,
                decide_agent_task,
                command_handler=execute_phone_command,
                perception_handler=accept_phone_perception,
                private_text_handler=deliver_private_tv_text,
                voice_handler=accept_private_phone_voice,
                provider_telemetry_handler=runtime.accept_provider_telemetry,
                preferred_peer=str(integrated.profile.metadata.get("webos_host") or "") or None,
                port=8769,
                token=private_state["companion_token"],
                csrf_token=private_state["companion_csrf"],
                pair_code=private_state["companion_pair_code"],
                tls_context=companion_tls_material.context(),
                ca_certificate=companion_tls_material.ca_certificate_path.read_bytes(),
                ca_fingerprint=companion_tls_material.ca_sha256,
            )
            secure_companion_service.secure_controller_url = secure_companion_service.public_url
            companion_service.ca_certificate = companion_tls_material.ca_certificate_path.read_bytes()
            companion_service.ca_fingerprint = companion_tls_material.ca_sha256
            companion_service.secure_controller_url = secure_companion_service.public_url
            # Keep ordinary pairing usable on phones that have not explicitly
            # installed the household CA. Secure camera mode remains an opt-in
            # link; accepting the six-digit code must not silently cross an
            # untrusted-certificate boundary.
            companion_service.redirect_public_url = None
            identity_snapshot = runtime.private_identity.snapshot()
            active_private = dict(identity_snapshot.get("active_shared_identity") or {})
            available_profiles = [item for item in list(identity_snapshot.get("profiles") or []) if item.get("status") == "active"]
            default_mobile_persona = str(active_private.get("persona_id") or (available_profiles[0].get("persona_id") if available_profiles else ""))
            if default_mobile_persona:
                try:
                    mobile_pairing = MobilePairingAuthority(
                        runtime.base_dir,
                        mother_id=runtime.profile.node_id,
                        mother_identity=runtime.identity,
                        endpoint=f"https://{companion_service.address}:8770",
                        ca_sha256=companion_tls_material.ca_sha256,
                        ca_certificate_pem=companion_tls_material.ca_certificate_path.read_bytes(),
                        identity_registry=runtime.private_identity,
                        remote_endpoints=tuple(
                            value.strip()
                            for value in os.environ.get("PILOT_REMOTE_ENDPOINTS", "").split(",")
                            if value.strip()
                        ),
                        relay_endpoint=os.environ.get("PILOT_RELAY_ENDPOINT") or None,
                    )
                    unified_inbox = UnifiedInbox(
                        runtime.base_dir,
                        mother_id=runtime.profile.node_id,
                        mother_identity=runtime.identity,
                        pairing_authority=mobile_pairing,
                        pilot_inbox=runtime.pilot_inbox,
                    )
                    trusted_network = TrustedNetworkAuthority(
                        runtime.base_dir,
                        mother_identity=runtime.identity,
                    )
                    trusted_handoffs = TrustedHandoffAuthority(
                        network=trusted_network,
                        inbox=unified_inbox,
                    )
                    from backend.modules.pilot_unified.personal import PersonalPilotProjection

                    def mobile_device_snapshot() -> Dict[str, Any]:
                        current_nodes = []
                        primary_tv_id = integrated.profile.node_id if integrated else ""
                        for node in runtime.store.list_nodes():
                            capsule = runtime.store.latest_capsule_for_node(node.profile.node_id)
                            current_nodes.append({
                                **node.to_dict(),
                                "capabilities": list(capsule.capabilities) if capsule else [],
                                "is_primary_tv": node.profile.node_id == primary_tv_id,
                            })
                        tv_connection: Dict[str, Any] = {
                            "status": "not_connected" if integrated is None else "checking",
                            "message": "No television is paired." if integrated is None else "Refresh the television to verify its live state.",
                            "last_checked_at": None,
                        }
                        if integrated is not None:
                            try:
                                host_value = runtime._refresh_webos_host(integrated)
                                proof = WebOsGateway.probe_endpoint(host_value, timeout=0.8)
                                tv_connection = {
                                    "status": "connected" if proof.get("connected") else "recovering",
                                    "message": "TV connected and ready." if proof.get("connected") else "Pilot is looking for the television.",
                                    "last_checked_at": time.time(),
                                }
                            except Exception:
                                tv_connection = {
                                    "status": "recovering",
                                    "message": "Pilot is looking for the TV. Keep it on and on the same Wi-Fi.",
                                    "last_checked_at": time.time(),
                                }
                        return {
                            "nodes": current_nodes,
                            "rooms": list(runtime.tv_rooms.snapshot().get("televisions") or []),
                            "tv_connection": tv_connection,
                            "active_shared_identity": runtime.private_identity.snapshot().get("active_shared_identity"),
                            "climate": runtime.infrared_climate.snapshot(),
                        }

                    def execute_mobile_device_command(command: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
                        return runtime.execute_companion_command(
                            command,
                            arguments,
                            canvas_url=canvas_service.public_url if canvas_service else None,
                            canvas_view_callback=canvas_service.set_view if canvas_service else None,
                            companion_url=companion_service.public_url if companion_service else None,
                        )

                    def mobile_experience_snapshot(persona_id: str) -> Dict[str, Any]:
                        return {
                            "learning": runtime.education.snapshot(),
                            "games": runtime.gaming.snapshot(persona_id=persona_id),
                            "entertainment": {
                                "personalization": runtime.entertainment_personalization.snapshot(persona_id=persona_id),
                                "execution": runtime.entertainment_execution.snapshot(persona_id=persona_id),
                            },
                        }

                    def execute_mobile_experience(
                        persona_id: str, operation: str, arguments: Dict[str, Any],
                    ) -> Dict[str, Any]:
                        if operation == "learning_start":
                            learning = runtime.education.start(
                                str(arguments.get("profile_id") or "explorer_a"),
                                age_band=str(arguments.get("age_band") or "6-7"),
                                difficulty=str(arguments.get("difficulty") or "foundation"),
                                subject=str(arguments.get("subject") or "spanish"),
                            )
                            return {"learning": learning, "state": "learning_active", "spoken_response": "The learning session is ready on this phone."}
                        if operation == "learning_answer":
                            learning = runtime.education.answer(int(arguments.get("choice_index", -1)))
                            return {"learning": learning, "state": "answer_checked", "spoken_response": str((learning.get("session") or {}).get("feedback") or "Answer checked.")}
                        if operation == "learning_next":
                            return {"learning": runtime.education.next_round(), "state": "learning_active", "spoken_response": "Next challenge ready."}
                        if operation == "learning_repeat":
                            return {"learning": runtime.education.repeat(), "state": "learning_active", "spoken_response": "Question repeated."}
                        if operation in {"games_open", "games_continue"}:
                            device_attempt = runtime.execute_voice_command(
                                "Pilot continue last game" if operation == "games_continue" else "Pilot open games",
                                canvas_url=canvas_service.public_url if canvas_service else None,
                                canvas_view_callback=canvas_service.set_view if canvas_service else None,
                                companion_url=companion_service.public_url if companion_service else None,
                                conversation_channel="private_phone",
                                persona_id=persona_id,
                            )
                            return {
                                "games": runtime.gaming.snapshot(persona_id=persona_id),
                                "device_attempt": device_attempt,
                                "state": "provider_surface_attempted",
                                "spoken_response": "GeForce NOW was requested on the television. Playing is not verified yet.",
                                "external_effect_verified": bool(dict(device_attempt.get("receipt") or {}).get("verified")),
                                "playing_verified": False,
                            }
                        if operation == "entertainment_continue_prepare":
                            execution = runtime.entertainment_execution.prepare_continue(persona_id=persona_id)
                            return {"entertainment": {"execution": execution}, "state": execution["status"], "spoken_response": "Your last verified title is prepared. Review it before opening the provider."}
                        if operation == "entertainment_continue_confirm":
                            execution = runtime.entertainment_execution.confirm(
                                str(arguments.get("execution_id") or ""), persona_id=persona_id,
                            )
                            return {"entertainment": {"execution": execution}, "state": execution["status"], "spoken_response": "The exact provider route is approved. It has not opened yet."}
                        if operation == "entertainment_continue_execute":
                            result = runtime.execute_private_entertainment(
                                str(arguments.get("execution_id") or ""), persona_id=persona_id,
                            )
                            execution = dict(result.get("entertainment_execution") or {})
                            return {
                                "entertainment": {"execution": execution},
                                "device_attempt": result.get("receipt"),
                                "state": str(execution.get("status") or "device_attempt_unverified"),
                                "spoken_response": "The provider route was attempted. Pilot only says playing when playback evidence confirms it.",
                                "external_effect_verified": bool(execution.get("provider_open_verified")),
                                "playing_verified": bool(execution.get("playback_verified")),
                            }
                        if operation == "entertainment_remember":
                            record = runtime.entertainment_personalization.remember(
                                persona_id=persona_id,
                                title=str(arguments.get("title") or ""),
                                outcome=str(arguments.get("outcome") or "watched"),
                                share_with_household=bool(arguments.get("share_with_household")),
                            )
                            return {"entertainment": {"memory": record}, "state": "remembered_privately", "spoken_response": "Entertainment preference saved privately."}
                        if operation == "entertainment_watchlist_add":
                            record = runtime.entertainment_personalization.add_watchlist(
                                persona_id=persona_id,
                                title=str(arguments.get("title") or ""),
                                provider=str(arguments.get("provider") or ""),
                                visibility=str(arguments.get("visibility") or "private"),
                            )
                            return {"entertainment": {"watchlist": record}, "state": "saved_privately", "spoken_response": "Title added to your private watchlist."}
                        raise PermissionError("That experience action is unavailable")

                    def execute_mobile_intelligence(
                        persona_id: str, operation: str, arguments: Dict[str, Any],
                    ) -> Dict[str, Any]:
                        if operation == "configure":
                            result = runtime.tv_research.policy.set_mode(
                                str(arguments.get("mode") or "native"),
                                gemini_grounding_enabled=bool(arguments.get("gemini_grounding_enabled")),
                            )
                            runtime.store.append_audit("intelligence_policy_changed_from_private_phone", {
                                "persona_id": persona_id, "mode": result["mode"],
                                "gemini_grounding_enabled": result["gemini_grounding_enabled"],
                            })
                            return result
                        return runtime.execute_voice_command(
                            str(arguments.get("query") or ""),
                            canvas_url=canvas_service.public_url if canvas_service else None,
                            canvas_view_callback=canvas_service.set_view if canvas_service else None,
                            companion_url=companion_service.public_url if companion_service else None,
                            conversation_channel="private_phone", persona_id=persona_id,
                        )

                    def execute_tv_presentation(persona_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
                        if surface_authority is None or canvas_service is None:
                            raise RuntimeError("The governed television presentation surface is unavailable")
                        operation = str(request.get("operation") or "")
                        if operation == "dismiss":
                            result = surface_authority.dismiss_presentation(
                                surface_id="surface.tv.canvas", persona_id=persona_id,
                            )
                            runtime.store.append_audit("private_tv_presentation_dismissed", {
                                "persona_id": persona_id, "surface_id": "surface.tv.canvas",
                                "dismissed": bool(result.get("dismissed")),
                            })
                            return result
                        manifest = surface_authority.issue_home_manifest(surface_id="surface.tv.canvas")
                        kind = str(request.get("content_kind") or "")
                        authority_domain = str(request.get("authority_domain") or "personal")
                        content_id = str(request.get("content_id") or "")
                        title = str(request.get("title") or "")
                        if authority_domain == "personal":
                            if kind != "briefing" or content_id != "personal/today":
                                raise PermissionError("Only the repository-backed personal briefing can be presented here")
                            content = private_tv_workspace(persona_id)
                            title = title or "My Pilot briefing"
                        elif authority_domain in {"workspace", "boardroom"}:
                            if workspace_gateway is None:
                                raise RuntimeError("The Workspace gateway is unavailable")
                            membership_id = str(request.get("membership_id") or "")
                            surface = {"briefing": "briefings", "dashboard": "dashboards", "document": "files"}.get(kind)
                            if surface is None:
                                raise ValueError("Choose a briefing, dashboard or document")
                            projection = workspace_gateway.read(
                                persona_id=persona_id, membership_id=membership_id, surface=surface,
                            )
                            actual_domain = "boardroom" if str(dict(projection.get("space") or {}).get("kind") or "") == "boardroom" else "workspace"
                            if actual_domain != authority_domain:
                                raise PermissionError("The requested presentation domain does not match the membership")
                            content = projection.get("data") or {}
                            if kind == "document":
                                files = list(dict(content).get("files") or []) if isinstance(content, dict) else []
                                selected = next((item for item in files if str(item.get("id") or "") == content_id), None)
                                if selected is None:
                                    raise LookupError("That authorized document is no longer available")
                                content = selected
                            title = title or str(dict(projection.get("space") or {}).get("display_name") or "Workspace")
                            content_id = content_id or f"{projection.get('space', {}).get('space_id')}/{surface}"
                        else:
                            raise PermissionError("That authority domain cannot present private television content")
                        receipt = surface_authority.present(
                            manifest=manifest, content_kind=kind, content_id=content_id,
                            title=title, content=content, authority_domain=authority_domain,
                        )
                        runtime.store.append_audit("private_tv_presentation_started", {
                            "persona_id": persona_id, "surface_id": "surface.tv.canvas",
                            "content_kind": kind, "content_id_hash": canonical_hash(content_id),
                            "content_hash": receipt.get("content_hash"), "authority_domain": authority_domain,
                        })
                        return receipt

                    personal_mobile = PersonalPilotProjection(
                        identities=runtime.private_identity,
                        inbox=runtime.pilot_inbox,
                        pairing_authority=mobile_pairing,
                        calendar=runtime.calendar_planning,
                        google_oauth=runtime.google_oauth,
                        communication=runtime.communication,
                        service_hub=runtime.service_hub,
                        private_saves=runtime.private_saves,
                        saved_followthrough=runtime.saved_followthrough,
                        researcher=runtime.tv_research,
                        device_snapshot_provider=mobile_device_snapshot,
                        device_discovery=lambda: runtime.scan_devices(timeout_seconds=2.5),
                        device_command_executor=execute_mobile_device_command,
                        experience_snapshot_provider=mobile_experience_snapshot,
                        experience_command_executor=execute_mobile_experience,
                        guardian=runtime.guardian,
                        intelligence_status_provider=runtime.tv_research.policy.status,
                        intelligence_command_executor=execute_mobile_intelligence,
                        tv_presentation_executor=execute_tv_presentation,
                        dashboard_action_executor=lambda _persona_id, command, arguments: execute_mobile_device_command(command, arguments),
                    )
                    workspace_gateway = ProviderIndependentWorkspaceGateway(
                        issuer_id=runtime.identity.fingerprint,
                        issuer_identity=runtime.identity,
                        pairing_authority=mobile_pairing,
                        commercial_service=CommercialAdoptionService(
                            Path(os.environ.get("TESSARIS_DATA_ROOT") or Path.cwd() / "data")
                            / "aion_business" / "commercial_adoption"
                        ),
                    )
                    boardroom_provider = AionBoardroomWorkspaceProvider(
                        WorkspaceRepository(), BusinessContainerRepository(), DepartmentPilotRepository(),
                        FinancePilotConversationService(), WorkflowFileCabinetRepository,
                    )
                    workspace_gateway.register_provider(boardroom_provider)
                    workspace_gateway.discover(boardroom_provider.provider_id)
                    # A founder chat enrollment is intentionally narrow.  It
                    # grants only read and governed conversation authority for
                    # one declared local workspace; it cannot administer users,
                    # issue invitations, approve commercial actions or sign off.
                    if founder_persona_id or founder_workspace_id:
                        if not founder_persona_id or not founder_workspace_id:
                            raise ValueError("Founder mobile enrollment requires both a persona and a workspace id")
                        workspace_gateway.grant_membership(Membership(
                            membership_id=f"membership/founder-{founder_workspace_id}-{founder_persona_id[-12:]}",
                            persona_id=founder_persona_id,
                            space_id=f"workspace/{founder_workspace_id}",
                            role_id="founder_mobile_chat",
                            scopes=("workspace.read", "workspace.conversation"),
                            status="active", issued_at=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                        ))
                    if surface_authority is not None:
                        surface_authority.workspace_gateway = workspace_gateway
                    mobile_origins = (
                        "http://127.0.0.1:3000",
                        "http://localhost:3000",
                        f"https://{companion_service.address}:8769",
                    )
                    unified_inbox_live_service = UnifiedInboxLiveService(
                        unified_inbox,
                        tls_context=companion_tls_material.context(),
                        address=companion_service.address,
                        port=8771,
                        allowed_origins=mobile_origins,
                    )
                    unified_inbox_live_service.start()
                    pairing_confirmation_page = runtime.base_dir / "pilot_unified" / "mobile_pairing_confirmation.html"

                    def present_mobile_confirmation(confirmation: dict[str, Any]) -> None:
                        """Show the one-time code locally on the owner's Mac.

                        The code never travels through the LAN QR screen: it is
                        rendered into a local file and opened by the local Node.
                        """
                        pairing_confirmation_page.parent.mkdir(parents=True, exist_ok=True)
                        code = html.escape(str(confirmation["confirmation_code"]))
                        label = html.escape(str(confirmation["device_label"]))
                        words = html.escape(" ".join(confirmation.get("trust_words") or []))
                        pairing_confirmation_page.write_text(
                            "<!doctype html><meta charset=utf-8><title>Confirm Pilot pairing</title>"
                            "<style>body{font-family:-apple-system,sans-serif;background:#f5f4ef;"
                            "display:grid;place-items:center;min-height:100vh;margin:0}main{background:white;"
                            "padding:48px;border-radius:24px;text-align:center;box-shadow:0 12px 44px #0002}"
                            "b{font-size:58px;letter-spacing:.16em;color:#173a57}</style>"
                            f"<main><p>TESSARIS NODE · CONFIRM PAIRING</p><h1>{label}</h1>"
                            f"<p>Enter this code on the phone:</p><b>{code}</b><p>{words}</p></main>",
                            encoding="utf-8",
                        )
                        pairing_confirmation_page.chmod(0o600)
                        webbrowser.open(pairing_confirmation_page.as_uri())
                        print(f"Pilot mobile connection code {confirmation['confirmation_code']} for {confirmation['device_label']}")

                    unified_mobile_service = MobilePairingService(
                        mobile_pairing,
                        tls_context=companion_tls_material.context(),
                        confirmation_presenter=present_mobile_confirmation,
                        address=companion_service.address,
                        port=8770,
                        allowed_origins=mobile_origins,
                        inbox=unified_inbox,
                        default_persona_id=default_mobile_persona,
                        live_inbox_url=unified_inbox_live_service.public_url,
                        personal=personal_mobile,
                        workspace_gateway=workspace_gateway,
                        trusted_handoffs=trusted_handoffs,
                    )
                    unified_mobile_service.start()
                except (OSError, RuntimeError, ValueError) as exc:
                    if unified_inbox_live_service:
                        unified_inbox_live_service.stop()
                    unified_inbox_live_service = None
                    unified_mobile_service = None
                    runtime.store.append_audit(
                        "unified_mobile_service_unavailable",
                        {"error_type": type(exc).__name__, "private_keys_exposed": False},
                    )
            secure_companion_service.start()
            runtime.store.append_audit(
                "private_companion_tls_ready",
                {
                    "address": companion_tls_material.address,
                    "ca_sha256": companion_tls_material.ca_sha256,
                    "server_sha256": companion_tls_material.server_sha256,
                    "private_keys_exposed": False,
                    "trust_installation": "explicit_user_action_required",
                },
            )
        except (OSError, RuntimeError, ValueError) as exc:
            runtime.store.append_audit(
                "private_companion_tls_unavailable",
                {"error_type": type(exc).__name__, "private_keys_exposed": False},
            )
            secure_companion_service = None
            companion_tls_material = None
        companion_service.start()
        if canvas_service:
            canvas_service.set_companion(companion_service.entry_url, companion_service.pair_code)
    health_monitor: ConnectionHealthMonitor | None = None
    if integrated is not None:
        last_recovery_scan = 0.0
        def check_tv_connection() -> Dict[str, Any]:
            nonlocal integrated, last_recovery_scan
            gateway = WebOsGateway(runtime.base_dir / "pairing" / "webos")
            host_value = runtime._refresh_webos_host(integrated)
            try:
                result = gateway.probe_endpoint(host_value, timeout=1.0)
                return {**result, "detail": "webOS SSAP session verified"}
            except Exception as first_error:
                now = time.monotonic()
                if now - last_recovery_scan >= 30:
                    last_recovery_scan = now
                    runtime.scan_devices(timeout_seconds=2.5)
                    integrated = runtime.store.get_node(integrated.profile.node_id) or integrated
                    host_value = runtime._refresh_webos_host(integrated)
                    try:
                        result = gateway.probe_endpoint(host_value, timeout=1.0)
                        return {**result, "detail": "webOS SSAP session recovered after rediscovery"}
                    except Exception as retry_error:
                        first_error = retry_error
                return {
                    "connected": False,
                    "host": host_value,
                    "detail": f"{type(first_error).__name__}: {first_error}"[:220],
                }

        health_monitor = ConnectionHealthMonitor(check_tv_connection)
        health_monitor.start()

    voice_service: VoiceControlService | None = None
    if voice_control:
        if integrated is not None:
            runtime.enable_voice_tv_policy(
                node_id=integrated.profile.node_id,
                approved_by="user_authorized_voice_control_2026-08-28",
            )

        def handle_voice(transcript: str) -> Dict[str, Any]:
            result = runtime.execute_voice_command(
                transcript,
                canvas_url=canvas_service.public_url if canvas_service else None,
                canvas_view_callback=canvas_service.set_view if canvas_service else None,
                companion_url=(secure_companion_service.entry_url if secure_companion_service else companion_service.entry_url) if companion_service else None,
                recent_context=voice_service.recent_context(exclude_latest=True) if voice_service else [],
            )
            if canvas_service:
                canvas_service.record_voice_result(transcript, result)
            return result

        voice_service = VoiceControlService(handle_voice, settings_path=runtime.base_dir / "voice" / "preferences.json")
        if integrated is not None:
            voice_holder["service"] = voice_service
        voice_service.start()
    class Handler(BaseHTTPRequestHandler):
        def _send_headers(self, content_type: str, length: int, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(length))
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            if self.path in {"/", "/dashboard"}:
                payload = _dashboard_html(
                    runtime, demo, voice_service, canvas_service, companion_service,
                    workspace_gateway=workspace_gateway,
                )
                content_type = "text/html; charset=utf-8"
            elif self.path in {"/brain", "/how-pilot-works"}:
                payload = _sovereign_brain_html()
                content_type = "text/html; charset=utf-8"
            elif self.path in {"/health", "/status"}:
                payload = json.dumps(runtime.status(), ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif self.path == "/api/demo" and demo is not None:
                payload = json.dumps(demo, ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif self.path == "/api/discovery":
                payload = json.dumps(runtime.discovery_status(), ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif self.path == "/api/voice" and voice_service is not None:
                payload = json.dumps(voice_service.status(), ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif self.path == "/api/intelligence":
                payload = json.dumps(runtime.tv_research.policy.status(), ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif self.path == "/api/connection-health":
                payload = json.dumps(health_monitor.snapshot() if health_monitor else {"status": "no_tv", "message": "No TV has been paired yet."}, ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
            self._send_headers(content_type, len(payload))
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
            is_discovery_scan = self.path == "/api/discovery/scan"
            is_readonly_enrollment = self.path.startswith("/api/nodes/") and self.path.endswith("/enroll-readonly")
            is_readonly_probe = self.path.startswith("/api/nodes/") and self.path.endswith("/probe-readonly")
            is_webos_pairing = self.path.startswith("/api/nodes/") and self.path.endswith("/pair-webos-readonly")
            is_canvas_open = self.path == "/api/tv/canvas/open"
            is_canvas_phone = self.path == "/api/tv/canvas/phone"
            is_dashboard_action = self.path == "/api/dashboard/action"
            is_voice_sleep = self.path == "/api/voice/sleep"
            is_voice_resume = self.path == "/api/voice/resume"
            is_voice_settings = self.path == "/api/voice/settings"
            is_intelligence_mode = self.path == "/api/intelligence/mode"
            is_connection_retry = self.path == "/api/connection-health/retry"
            is_reliability_baseline = self.path == "/api/tv/reliability/baseline"
            if not (is_discovery_scan or is_readonly_enrollment or is_readonly_probe or is_webos_pairing or is_canvas_open or is_canvas_phone or is_dashboard_action or is_voice_sleep or is_voice_resume or is_voice_settings or is_intelligence_mode or is_connection_retry or is_reliability_baseline):
                self.send_error(404)
                return
            if self.headers.get("X-AION-Fabric") != "dashboard-v1":
                payload = json.dumps({"error": "Missing local dashboard request marker"}).encode()
                self._send_headers("application/json; charset=utf-8", len(payload), 403)
                self.wfile.write(payload)
                return
            try:
                if is_connection_retry:
                    result = health_monitor.retry_now() if health_monitor else {"status": "no_tv"}
                elif is_reliability_baseline:
                    result = runtime.run_safe_tv_reliability_baseline()
                elif is_intelligence_mode:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 512:
                        raise ValueError("Invalid Pilot intelligence request")
                    request_value = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(request_value, dict):
                        raise ValueError("Invalid Pilot intelligence request")
                    result = runtime.tv_research.policy.set_mode(
                        str(request_value.get("mode") or ""),
                        gemini_grounding_enabled=(
                            bool(request_value["gemini_grounding_enabled"])
                            if "gemini_grounding_enabled" in request_value else None
                        ),
                    )
                    runtime.store.append_audit(
                        "intelligence_policy_changed",
                        {"mode": result["mode"], "gemini_grounding_enabled": result["gemini_grounding_enabled"]},
                    )
                elif is_dashboard_action:
                    if integrated is None or canvas_service is None or companion_service is None:
                        raise RuntimeError("AION needs an integrated television before this experience can open")
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 2048:
                        raise ValueError("Invalid AION Home request")
                    request_value = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(request_value, dict):
                        raise ValueError("Invalid AION Home request")
                    command = str(request_value.get("command") or "")
                    arguments = request_value.get("arguments") or {}
                    workspace_commands = {
                        "tasks": "Pilot open my tasks",
                        "calendar": "Pilot open my calendar",
                        "boardroom": "Pilot open my Boardroom",
                        "files": "Pilot open my files",
                        "iot": "Pilot open my IoT devices",
                        "work": "Pilot open my personal work",
                    }
                    if command not in {"games", "aion", "education_start", "god_view", "ask", *workspace_commands} or not isinstance(arguments, dict):
                        raise ValueError("That AION Home experience is unavailable")
                    if command == "ask":
                        text = " ".join(str(arguments.get("text") or "").split())[:300]
                        if len(text) < 2:
                            raise ValueError("Enter something for AION to help with")
                        arguments = {"text": text}
                    if command in workspace_commands:
                        result = runtime.execute_voice_command(
                            workspace_commands[command],
                            canvas_url=canvas_service.public_url,
                            canvas_view_callback=canvas_service.set_view,
                        )
                    else:
                        result = runtime.execute_companion_command(
                            command,
                            arguments,
                            canvas_url=canvas_service.public_url,
                            canvas_view_callback=canvas_service.set_view,
                            companion_url=secure_companion_service.entry_url if secure_companion_service else companion_service.entry_url,
                        )
                    canvas_service.record_voice_result(f"Dashboard Home: {command}", result)
                elif is_voice_settings:
                    if voice_service is None:
                        raise RuntimeError("Local voice service is unavailable")
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 512:
                        raise ValueError("Invalid voice preference request")
                    request_value = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(request_value, dict):
                        raise ValueError("Invalid voice preference request")
                    result = voice_service.set_preferences(
                        voice_name=request_value.get("voice_name"),
                        speech_rate=request_value.get("speech_rate"),
                        quiet_mode=request_value.get("quiet_mode"),
                        quiet_start=request_value.get("quiet_start"),
                        quiet_end=request_value.get("quiet_end"),
                    )
                    runtime.store.append_audit("voice_preferences_changed", {
                        "voice_name": result.get("voice_name"),
                        "speech_rate": result.get("speech_rate"),
                        "quiet_mode": result.get("quiet_mode"),
                        "quiet_start": result.get("quiet_start"),
                        "quiet_end": result.get("quiet_end"),
                    })
                elif is_voice_sleep or is_voice_resume:
                    if voice_service is None:
                        raise RuntimeError("Local voice service is unavailable")
                    if is_voice_sleep:
                        voice_service.sleep()
                    else:
                        voice_service.start()
                    result = voice_service.status()
                elif is_canvas_open or is_canvas_phone:
                    if canvas_service is None:
                        raise RuntimeError("No integrated television is available for Pilot")
                    result = runtime.execute_voice_command(
                        "Pilot show the phone controller" if is_canvas_phone else "Pilot take over the TV",
                        canvas_url=canvas_service.public_url,
                        canvas_view_callback=canvas_service.set_view,
                    )
                    canvas_service.record_voice_result("Dashboard: show phone pairing" if is_canvas_phone else "Dashboard: put Pilot on the TV", result)
                elif is_discovery_scan:
                    result = runtime.scan_devices(timeout_seconds=2.5)
                elif is_readonly_enrollment:
                    node_id = self.path[len("/api/nodes/") : -len("/enroll-readonly")].strip("/")
                    if not node_id.startswith("node_discovered_"):
                        raise ValueError("Only a discovered Fabric node can be enrolled here")
                    result = runtime.enroll_gateway_for_read_only_testing(
                        node_id=node_id,
                        approved_by="local_dashboard_owner",
                    )
                elif is_webos_pairing:
                    node_id = self.path[len("/api/nodes/") : -len("/pair-webos-readonly")].strip("/")
                    if not node_id.startswith("node_discovered_"):
                        raise ValueError("Only an enrolled discovered node can be paired here")
                    result = runtime.pair_webos_and_prove_read_only(
                        node_id=node_id,
                        approved_by="local_dashboard_owner",
                    ).to_dict()
                else:
                    node_id = self.path[len("/api/nodes/") : -len("/probe-readonly")].strip("/")
                    if not node_id.startswith("node_discovered_"):
                        raise ValueError("Only an enrolled discovered node can be probed here")
                    result = runtime.run_read_only_probe(node_id=node_id).to_dict()
                payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self._send_headers("application/json; charset=utf-8", len(payload))
            except Exception as exc:
                payload = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                self._send_headers("application/json; charset=utf-8", len(payload), 500)
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"AION Fabric mother is ready at {url}")
    print("Discovery is observe-only; devices require explicit enrollment and capability approval.")
    if supervisor:
        supervisor.start()
        print(f"Autonomous safe discovery is active every {max(30.0, scan_interval):.0f} seconds.")
    if voice_service:
        print("Local AION voice control is starting. Say 'Pilot' followed by a TV command.")
    if canvas_service:
        print(f"Secure read-only TV Canvas is ready at {canvas_service.public_url}")
    if companion_service:
        print(
            f"Private cross-device companion is ready at {companion_service.entry_url} "
            f"with TV code {companion_service.pair_code}"
        )
    if secure_companion_service:
        print(
            f"Trusted private companion is ready at {secure_companion_service.entry_url}; "
            "install and explicitly trust the public household certificate first"
        )
    if unified_mobile_service:
        print(f"Unified Pilot mobile pairing and Inbox are ready at https://{companion_service.address}:8770")
    if unified_inbox_live_service:
        print(f"Unified Pilot live Inbox is ready at {unified_inbox_live_service.public_url}")
    print(f"Universal node handshake is ready at {universal_service.public_url}")
    print("Keep this window open. Press Control-C to stop AION Fabric.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if supervisor:
            supervisor.stop()
        if voice_service:
            voice_service.stop()
        if canvas_service:
            canvas_service.stop()
        if companion_service:
            companion_service.stop()
        if secure_companion_service:
            secure_companion_service.stop()
        if unified_mobile_service:
            unified_mobile_service.stop()
        if unified_inbox_live_service:
            unified_inbox_live_service.stop()
        if health_monitor:
            health_monitor.stop()
        universal_service.stop()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aion-fabric", description="AION Device Fabric developer preview")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Start the local fabric and print status")
    serve = subparsers.add_parser("serve", help="Run the local mother status service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--demo", action="store_true", help="Load the fridge/TV demonstration fabric")
    serve.add_argument("--open-browser", action="store_true", help="Open the dashboard in the default browser")
    serve.add_argument("--autonomous-discovery", action="store_true", help="Continuously refresh safe discovery evidence")
    serve.add_argument("--scan-interval", type=float, default=300.0)
    serve.add_argument("--voice-control", action="store_true", help="Run local wake-phrase TV voice control")
    serve.add_argument("--founder-persona-id", default="", help="Founder persona for narrow mobile Boardroom chat enrollment")
    serve.add_argument("--founder-workspace-id", default="", help="One local workspace for that founder mobile chat enrollment")
    subparsers.add_parser("status", help="Read current fabric status")
    subparsers.add_parser("demo", help="Run an isolated mother/fridge/TV proof")

    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)
    if args.command == "demo":
        _print(run_local_demo(runtime_dir / "demo"))
        return 0

    demo = None
    if args.command == "serve" and args.demo:
        demo = run_local_demo(runtime_dir / "demo")
        runtime = AionFabricRuntime.bootstrap(runtime_dir / "demo" / "mother")
    else:
        runtime = AionFabricRuntime.bootstrap(runtime_dir)
    if args.command in {"start", "status"}:
        _print(runtime.status())
        return 0
    if args.command == "serve":
        _serve(
            runtime,
            args.host,
            args.port,
            demo=demo,
            open_browser=args.open_browser,
            autonomous_discovery=args.autonomous_discovery,
            scan_interval=args.scan_interval,
            voice_control=args.voice_control,
            founder_persona_id=args.founder_persona_id,
            founder_workspace_id=args.founder_workspace_id,
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
