from __future__ import annotations

import html
import json
import secrets
import shutil
import subprocess
import ssl
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse

import qrcode
import qrcode.image.svg

from .tv_canvas import _lan_address


def _companion_html(token: str, csrf_token: str, snapshot: Dict[str, Any]) -> bytes:
    task = snapshot.get("active_task") or {}
    approval = task.get("approval") or {}
    controller = snapshot.get("controller") or {}
    perception = snapshot.get("perception") or {}
    inference = perception.get("inference") or {}
    personas = list((snapshot.get("household") or {}).get("personas") or [])
    active_persona = personas[0] if personas else {}
    service_proposal = snapshot.get("service_proposal") or {}
    request = html.escape(str(task.get("request") or "No task is waiting"))
    route = html.escape(str(task.get("route") or "idle"))
    state = html.escape(str(approval.get("state") or task.get("status") or "idle"))
    approval_id = html.escape(str(approval.get("approval_id") or ""), quote=True)
    safe_token = html.escape(token, quote=True)
    safe_csrf = html.escape(csrf_token, quote=True)
    tv_name = html.escape(str(controller.get("tv_name") or "Television"))
    volume = html.escape(str(controller.get("volume") if controller.get("volume") is not None else "--"))
    surface = html.escape(str(controller.get("surface") or "unknown"))
    observed = html.escape(str(inference.get("summary") or "No phone-camera observation yet"))
    gaming = snapshot.get("gaming") or {}
    latest_game = dict(gaming.get("latest_session") or {})
    gaming_state = html.escape(str(latest_game.get("state") or "No provider session prepared").replace("_", " "))
    gaming_title = html.escape(str(latest_game.get("title") or latest_game.get("query") or "No verified game title"))
    gaming_controller_count = len(list(gaming.get("controllers") or []))
    private_identity = snapshot.get("private_identity") or {}
    identity_profiles = list(private_identity.get("profiles") or [])
    active_identity = dict(private_identity.get("active_shared_identity") or {})
    selected_persona_id = str(active_identity.get("persona_id") or (identity_profiles[0].get("persona_id") if identity_profiles else ""))
    active_identity_name = html.escape(str(active_identity.get("display_name") or "No signed-in shared-screen person"))
    private_export = snapshot.get("private_identity_export") or {}
    private_memories = list(private_export.get("memories") or [])
    trusted_devices = [item for item in list(private_export.get("devices") or []) if item.get("status") == "trusted"]
    service_consents = [item for item in list(private_export.get("consents") or []) if item.get("status") == "granted"]
    secure_companion_url = html.escape(str(snapshot.get("secure_companion_url") or ""), quote=True)
    identity_name_counts: Dict[str, int] = {}
    for item in identity_profiles:
        key = str(item.get("display_name") or "Private identity").casefold()
        identity_name_counts[key] = identity_name_counts.get(key, 0) + 1
    identity_options = "".join(
        f'''<option value="{html.escape(str(item.get("persona_id") or ""), quote=True)}"{' selected' if str(item.get("persona_id") or "") == selected_persona_id else ''}>{html.escape(str(item.get("display_name") or "Private identity"))} · {html.escape(str(item.get("role") or "adult"))}{f" · {html.escape(str(item.get('persona_id') or '')[-4:])}" if identity_name_counts.get(str(item.get("display_name") or "Private identity").casefold(), 0) > 1 else ""}</option>'''
        for item in identity_profiles
    )
    trusted_device_options = "".join(
        f'''<option value="{html.escape(str(item.get("device_id") or ""), quote=True)}">{html.escape(str(item.get("device_label") or "Trusted phone"))}</option>'''
        for item in trusted_devices
    )
    memory_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("kind") or "memory"))} · {html.escape(str(item.get("scope") or "private").replace("_", " "))}</div><p>{html.escape(str(item.get("summary") or ""))}</p><div class="grid"><button data-memory-private="{html.escape(str(item.get("memory_id") or ""), quote=True)}">Make private</button><button data-memory-household="{html.escape(str(item.get("memory_id") or ""), quote=True)}">Share with household</button><button data-memory-delete="{html.escape(str(item.get("memory_id") or ""), quote=True)}" class="danger">Delete</button></div></div>'''
        for item in private_memories[-30:]
    ) or '<p class="privacy">No saved memory for this identity.</p>'
    session_release_control = '''
    <button id="identity-tv-logout" class="danger" style="width:100%;margin:10px 0">Log this person out of the TV</button>
    <p class="privacy">The TV locks automatically after five minutes without activity. Logging out does not delete this identity, its tasks, or its memory.</p>
    <script>window.addEventListener('DOMContentLoaded',()=>{const button=document.getElementById('identity-tv-logout');if(!button)return;const bytesToB64=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))),canonical=value=>JSON.stringify(value,Object.keys(value).sort()),dbOpen=()=>new Promise((resolve,reject)=>{const request=indexedDB.open('pilot-private-identity',1);request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)}),loadKey=async persona_id=>{const db=await dbOpen();return new Promise((resolve,reject)=>{const request=db.transaction('keys').objectStore('keys').get(persona_id);request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)})};button.onclick=async()=>{const persona_id=document.getElementById('inbox-persona').value;try{const record=await loadKey(persona_id);if(!record)throw new Error('This phone is not bound to the selected identity.');const nonce=crypto.randomUUID(),payload={purpose:'release_shared_screen',persona_id,device_id:record.device_id,nonce},signature=await crypto.subtle.sign({name:'Ed25519'},record.privateKey,new TextEncoder().encode(canonical(payload))),result=await command('identity_logout',{...payload,signature:bytesToB64(signature)});show(result.spoken_response);location.reload()}catch(e){show(e.message,true)}}});</script>
    '''
    memory_cards = session_release_control + memory_cards
    consent_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("service") or "service"))}</div><p>{html.escape(", ".join(str(value) for value in list(item.get("scopes") or [])))}</p><button data-consent-revoke="{html.escape(str(item.get("consent_id") or ""), quote=True)}" class="danger">Revoke consent</button></div>'''
        for item in service_consents[-20:]
    ) or '<p class="privacy">No connected-service consent has been granted.</p>'
    pilot_inbox = snapshot.get("pilot_inbox") or {}
    inbox_tasks = list(pilot_inbox.get("tasks") or [])
    inbox_messages = list(pilot_inbox.get("messages") or [])
    inbox_reminders = list(pilot_inbox.get("reminders") or [])
    inbox_contacts = list(pilot_inbox.get("contacts") or [])
    external_deliveries = list(pilot_inbox.get("external_deliveries") or [])
    contact_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("preferred_route") or "contact"))}</div><h3>{html.escape(str(item.get("display_name") or "Contact"))}</h3><p class="muted">{html.escape(str(item.get("email") or item.get("whatsapp") or "Pilot contact"))}</p></div>'''
        for item in inbox_contacts[-20:]
    ) or '<p class="privacy">No private contacts yet.</p>'
    external_delivery_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("channel") or "external"))} · {html.escape(str(item.get("status") or "prepared").replace("_", " "))}</div><h3>{html.escape(str(item.get("recipient_name") or "Contact"))}</h3><p>{html.escape(str(item.get("body") or ""))}</p>{f'<button data-external-approve="{html.escape(str(item.get("proposal_id") or ""), quote=True)}" class="approve">Approve this handoff</button>' if item.get("status") == "prepared_not_sent" else ''}</div>'''
        for item in external_deliveries[-20:]
    ) or '<p class="privacy">No external task handoffs waiting.</p>'
    task_options = "".join(
        f'''<option value="{html.escape(str(item.get("task_id") or ""), quote=True)}">{html.escape(str(item.get("title") or "Task"))}</option>'''
        for item in inbox_tasks if item.get("status") in {"open", "snoozed"}
    )
    inbox_task_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("status") or "open").replace("_", " "))}</div><h3>{html.escape(str(item.get("title") or "Task"))}</h3><p class="muted">{html.escape(str(item.get("notes") or ""))}</p><div class="grid">{f'<button data-inbox-accept="{html.escape(str(item.get("task_id") or ""), quote=True)}">Accept</button><button data-inbox-decline="{html.escape(str(item.get("task_id") or ""), quote=True)}">Decline</button>' if item.get("status") == "awaiting_recipient_acceptance" and item.get("assignee_persona_id") == selected_persona_id else f'<button data-inbox-complete="{html.escape(str(item.get("task_id") or ""), quote=True)}">Complete</button>' if item.get("status") == "open" else ''}</div></div>'''
        for item in inbox_tasks[-20:]
    ) or '<p class="privacy">No tasks in this Pilot stream yet.</p>'
    inbox_message_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("kind") or "message"))}</div><p>{html.escape(str(item.get("body") or ""))}</p></div>'''
        for item in inbox_messages[-10:]
    ) or '<p class="privacy">No agent messages yet.</p>'
    reminder_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("trigger") or "time").replace("_", " "))} · {html.escape(str(item.get("status") or "scheduled"))}</div><p>{html.escape(str(item.get("location_label") or item.get("at") or "Scheduled reminder"))}</p></div>'''
        for item in inbox_reminders[-20:]
    ) or '<p class="privacy">No reminders scheduled.</p>'
    contact_options = "".join(
        f'''<option value="{html.escape(str(item.get("contact_id") or ""), quote=True)}">{html.escape(str(item.get("display_name") or "Contact"))}</option>'''
        for item in inbox_contacts
    )
    communication = snapshot.get("communication") or {}
    communication_drafts = list(communication.get("drafts") or [])
    communication_received = list(communication.get("received") or [])
    communication_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("channel") or "message"))} · {html.escape(str(item.get("status") or "draft").replace("_", " "))}</div><h3>{html.escape(str(item.get("recipient_name") or "Recipient"))}</h3><p>{html.escape(str(item.get("subject") or ""))}</p><p>{html.escape(str(item.get("body") or ""))}</p>{f'<button class="approve" data-communication-approve="{html.escape(str(item.get("draft_id") or ""), quote=True)}" data-content-hash="{html.escape(str(item.get("content_hash") or ""), quote=True)}">Approve exact recipient and content</button>' if item.get("status") == "awaiting_private_approval" else ''}</div>'''
        for item in communication_drafts[-10:]
    ) or '<p class="privacy">No communication drafts yet.</p>'
    received_cards = "".join(
        f'''<div class="task"><div class="route">Received · {html.escape(str(item.get("source") or "provider"))}</div><h3>{html.escape(str(item.get("sender_name") or "Sender"))}</h3><p>{html.escape(str(item.get("summary") or ""))}</p><p class="privacy">Received {html.escape(str(item.get("received_at") or ""))}; freshness recorded at ingestion. Raw message body is not retained here.</p></div>'''
        for item in communication_received[-10:]
    ) or '<p class="privacy">No authorized received-message summaries.</p>'
    calendar_planning = snapshot.get("calendar_planning") or {}
    google_oauth = snapshot.get("google_oauth") or {}
    google_bindings = list(google_oauth.get("bindings") or [])
    calendar_proposals = list(calendar_planning.get("proposals") or [])
    calendar_cards = "".join(
        f'''<div class="task"><div class="route">{html.escape(str(item.get("action") or "change"))} · {html.escape(str(item.get("status") or "prepared").replace("_", " "))}</div><h3>{html.escape(str((item.get("scope") or {}).get("title") or "Calendar change"))}</h3><p>{html.escape(str((item.get("scope") or {}).get("start") or ""))} → {html.escape(str((item.get("scope") or {}).get("end") or ""))}</p><p class="privacy">Private conflicts: {int(item.get("conflict_count") or 0)}. Other event titles are not disclosed.</p>{f'<button class="approve" data-calendar-approve="{html.escape(str(item.get("proposal_id") or ""), quote=True)}" data-scope-hash="{html.escape(str(item.get("scope_hash") or ""), quote=True)}">Approve exact calendar change</button>' if item.get("status") in {"awaiting_private_approval", "awaiting_conflict_confirmation"} else ''}</div>'''
        for item in calendar_proposals[-10:]
    ) or '<p class="privacy">No calendar changes prepared.</p>'
    guardian = snapshot.get("guardian") or {}
    guardian_incidents = list(guardian.get("incidents") or [])
    guardian_permissions = list(guardian.get("permissions") or [])
    latest_guardian = dict(guardian_incidents[-1]) if guardian_incidents else {}
    guardian_state = html.escape(str(latest_guardian.get("status") or "ready").replace("_", " "))
    guardian_id = html.escape(str(latest_guardian.get("incident_id") or ""), quote=True)
    known_profile_names = [
        str(value)[:32] for value in list((snapshot.get("netflix_profiles") or {}).get("names") or [])[:5]
        if str(value).strip()
    ]
    profile_labels = [
        known_profile_names[index] if index < len(known_profile_names) else f"Profile {index + 1}"
        for index in range(5)
    ]
    profile_buttons = "".join(
        f'''<button data-command="profile_{index}">{html.escape(name)}</button>'''
        for index, name in enumerate(profile_labels, start=1)
    )
    profile_name_inputs = "".join(
        f'''<label class="detail-label">Position {index}<input data-netflix-profile-name type="text" maxlength="32" value="{html.escape(name, quote=True)}"></label>'''
        for index, name in enumerate(profile_labels, start=1)
    )
    persona_name = html.escape(str(active_persona.get("display_name") or "Unidentified household user"))
    bound_services = html.escape(", ".join(active_persona.get("bound_services") or []) or "no external services connected")
    tv_rooms = snapshot.get("tv_rooms") or {}
    registered_tvs = list(tv_rooms.get("televisions") or [])
    current_node_id = str(controller.get("node_id") or "")
    current_room = next((item for item in registered_tvs if item.get("node_id") == current_node_id), registered_tvs[0] if len(registered_tvs) == 1 else {})
    current_room_name = html.escape(str(current_room.get("room_name") or "Primary TV"))
    room_options = "".join(
        f'''<option value="{html.escape(str(item.get("room_name") or ""), quote=True)}">{html.escape(str(item.get("room_name") or "Unnamed room"))} · {html.escape(str(item.get("device_name") or "TV"))}</option>'''
        for item in registered_tvs if item.get("node_id") != current_node_id
    )
    latest_handoff = dict(tv_rooms.get("latest_handoff") or {})
    handoff_control = ""
    if latest_handoff.get("status") == "awaiting_private_confirmation":
        handoff_control = f'''<button class="approve" style="width:100%;margin-top:10px" onclick="this.disabled=true;command('tv_handoff_confirm',{{handoff_id:'{html.escape(str(latest_handoff.get("handoff_id") or ""), quote=True)}',confirmation_hash:'{html.escape(str(latest_handoff.get("confirmation_hash") or ""), quote=True)}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Confirm handoff to {html.escape(str(latest_handoff.get("destination_room") or "destination TV"))}</button>'''
    tv_reliability = snapshot.get("tv_reliability") or {}
    reliability_rate = int(round(float(tv_reliability.get("success_or_recovery_rate") or 0) * 100))
    reliability_cases = int(tv_reliability.get("field_cases") or 0)
    reliability_missing = list(tv_reliability.get("missing_areas") or [])
    reliability_coverage = "".join(
        f'''<li>{"✅" if value.get("covered") else "○"} {html.escape(str(area).replace("_", " ").title())} · {int(value.get("field_cases") or 0)} field cases</li>'''
        for area, value in dict(tv_reliability.get("coverage") or {}).items()
    )
    live_context = snapshot.get("live_context") or {}
    live_app = html.escape(str((live_context.get("app") or {}).get("title") or "No live context captured"))
    live_statement = html.escape(str(live_context.get("recent_statement") or "Ask Pilot immediately after a statement to explain or fact-check it."))
    research = snapshot.get("tv_research") or {}
    research_answer = html.escape(str(research.get("answer") or "No evidence result yet"))
    research_mode = html.escape(str(research.get("display_label") or research.get("mode") or "idle"))
    source_links = "".join(
        f'''<li><a href="{html.escape(str(item.get("url") or ""), quote=True)}" rel="noreferrer">{html.escape(str(item.get("title") or "Evidence source"))}</a></li>'''
        for item in list(research.get("items") or [])[:5]
        if str(item.get("url") or "").startswith("https://")
    )
    live_news = snapshot.get("live_news") or {}
    live_verdict = html.escape(str(live_news.get("verdict") or "No verdict yet"))
    live_confidence = int(round(float(live_news.get("confidence") or 0) * 100))
    live_claims = "".join(
        f'''<div class="task" style="margin-top:8px"><div class="route">{html.escape(str(item.get("verdict") or "Unverifiable"))} · {int(round(float(item.get("confidence") or 0) * 100))}%</div><strong>{html.escape(str(item.get("claim") or "Claim unavailable"))}</strong><p class="muted">{html.escape(str(item.get("explanation") or "No explanation established"))}</p></div>'''
        for item in list(live_news.get("claims") or [])[:4]
        if isinstance(item, dict)
    )
    live_sources = "".join(
        f'''<li><a href="{html.escape(str(item.get("url") or ""), quote=True)}" rel="noreferrer">{html.escape(str(item.get("title") or "Evidence source"))}</a> · {html.escape(str(item.get("source_class") or "source"))} · quality {int(round(float(item.get("quality_score") or 0) * 100))}%<br><span class="muted">{html.escape(str(item.get("quality_basis") or "Source quality not yet classified"))}</span></li>'''
        for item in list(live_news.get("sources") or [])[:5]
        if isinstance(item, dict) and str(item.get("url") or "").startswith("https://")
    )
    live_timeline = html.escape(" · ".join(
        f"{item.get('event')}: {item.get('detail')}" for item in list(live_news.get("correction_timeline") or [])[-5:]
        if isinstance(item, dict)
    ) or "No correction timeline yet")
    live_performance = dict(live_news.get("performance") or {})
    live_latency = int(live_performance.get("latency_ms") or 0)
    live_source_quality = int(round(float(live_performance.get("mean_source_quality") or 0) * 100))
    live_contradictions = int((live_news.get("contradiction_analysis") or {}).get("contradictions_detected") or 0)
    scene_explanation = snapshot.get("scene_explanation") or {}
    scene_answer = html.escape(str(scene_explanation.get("answer") or "Say ‘Pilot, what just happened?’ for a spoiler-safe explanation of the observed scene."))
    scene_uncertainty = html.escape(str(scene_explanation.get("uncertainty") or "Pilot has not explained a scene yet."))
    scene_confidence = int(round(float(scene_explanation.get("confidence") or 0) * 100))
    scene_facts = "".join(f"<li>{html.escape(str(value))}</li>" for value in list(scene_explanation.get("observed_facts") or [])[:5])
    scene_mode = html.escape(" · ".join(filter(None, [
        str(scene_explanation.get("request_kind") or "scene").replace("_", " "),
        str(scene_explanation.get("audience") or "general"),
        str(scene_explanation.get("detail_level") or "normal"),
    ])))
    scene_accessibility = html.escape(str(scene_explanation.get("accessibility_summary") or "No descriptive scene summary requested yet."))
    scene_learning = dict(scene_explanation.get("learning_activity") or {})
    scene_learning_text = html.escape(
        f"{scene_learning.get('subject')}: {scene_learning.get('prompt')} — {scene_learning.get('answer')}"
        if scene_learning.get("prompt") else "No scene-derived learning activity requested yet."
    )
    programme_companion = snapshot.get("programme_companion") or {}
    programme_cast_title = html.escape(str((programme_companion.get("programme") or {}).get("title") or "Ask ‘Pilot, who is in this?’ after the programme title is established."))
    programme_cast_answer = html.escape(str(programme_companion.get("answer") or "No verified cast lookup yet."))
    programme_cast_source = html.escape(str((programme_companion.get("source") or {}).get("attribution") or "Public cast evidence not acquired"))
    programme_cast_items = "".join(
        f"<li><strong>{html.escape(str(item.get('person') or 'Unknown'))}</strong> as {html.escape(str(item.get('character') or 'character not listed'))}</li>"
        for item in list(programme_companion.get("cast") or [])[:8]
        if isinstance(item, dict)
    ) or "<li>No verified cast entries available.</li>"
    programme_origins = snapshot.get("programme_origins") or {}
    programme_origin_title = html.escape(str((programme_origins.get("programme") or {}).get("title") or "No verified programme origin lookup yet."))
    programme_origin_answer = html.escape(str(programme_origins.get("answer") or "Ask where this was filmed, where it is set, or what it is based on."))
    programme_origin_source = html.escape(str((programme_origins.get("source") or {}).get("provider") or "Wikidata not queried"))
    programme_origin_evidence = dict(programme_origins.get("evidence") or {})
    programme_origin_facts = "".join(
        f"<li><strong>{html.escape(label.replace('_', ' ').title())}:</strong> {html.escape(', '.join(str(item.get('label') or '') for item in list(programme_origin_evidence.get(label) or [])[:6]))}</li>"
        for label in ("filming_locations", "narrative_locations", "based_on", "countries_of_origin", "original_languages", "original_broadcasters")
        if programme_origin_evidence.get(label)
    ) or "<li>No structured origin facts established.</li>"
    live_translation = snapshot.get("live_translation") or {}
    translation_text = html.escape(str(live_translation.get("translation") or "Say ‘Pilot, translate that’ immediately after dialogue, or capture a subtitle."))
    translation_source = html.escape(str(live_translation.get("source_text") or "No local line captured yet"))
    translation_route = html.escape(str(live_translation.get("provider") or "idle").replace("_", " "))
    translation_confidence = int(round(float(live_translation.get("confidence") or 0) * 100))
    translation_uncertainty = html.escape(str(live_translation.get("uncertainty") or "No translation requested yet."))
    live_sports = snapshot.get("live_sports") or {}
    sports_answer = html.escape(str(live_sports.get("answer") or "Say ‘Pilot, what’s the score?’ or ‘Pilot, explain that referee decision.’"))
    sports_rule = html.escape(str(live_sports.get("rule_explanation") or "No rule explanation requested yet."))
    sports_limit = html.escape(str(live_sports.get("limitation") or "Pilot has no current sports interpretation."))
    sports_scoreboard = dict(live_sports.get("scoreboard") or {})
    sports_score = html.escape(str(sports_scoreboard.get("score_text") or sports_scoreboard.get("clock") or "No captured scoreboard"))
    sports_confidence = int(round(float(live_sports.get("confidence") or 0) * 100))
    live_event_status = snapshot.get("live_events") or {}
    live_event = dict(live_event_status.get("latest") or {})
    live_event_provider = dict(live_event.get("provider") or {})
    live_event_answer = html.escape(str(live_event.get("answer") or "Ask ‘Pilot, who scored?’, ‘show the statistics’, or ‘show the fixtures’."))
    live_event_kind = html.escape(str(live_event.get("question_kind") or "idle").replace("_", " "))
    live_event_reconciliation = html.escape(str(live_event.get("reconciliation") or "no evidence yet").replace("_", " "))
    live_event_provider_name = html.escape(str(live_event_provider.get("provider") or "No provider queried"))
    live_event_provider_state = "authenticated" if live_event_provider.get("authenticated") else "not connected"
    live_event_confidence = int(round(float(live_event.get("confidence") or 0) * 100))
    football_connection = "connected" if (live_event_status.get("football_data") or {}).get("connected") else "not configured"
    ticketmaster_connection = "connected" if (live_event_status.get("ticketmaster") or {}).get("connected") else "not configured"
    live_event_fact = live_event.get("authenticated_provider_fact")
    live_event_fact_text = html.escape(json.dumps(live_event_fact, ensure_ascii=False, indent=2)[:2800] if live_event_fact else "No authenticated provider fact is available.")
    live_engagement = snapshot.get("live_engagement") or {}
    pending_watch = dict(live_engagement.get("pending") or {})
    pending_watch_id = html.escape(str(pending_watch.get("watch_id") or ""), quote=True)
    pending_watch_controls = ""
    if pending_watch_id:
        threshold = html.escape(str((pending_watch.get("threshold") or {}).get("value") or 0))
        pending_watch_controls = f'''<div class="task" style="margin-top:12px"><div class="route">Private event alert · awaiting claim</div><h3>Notify me when the score margin is {threshold} or less</h3><button class="approve" style="width:100%" onclick="this.disabled=true;command('live_watch_claim',{{watch_id:'{pending_watch_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Activate for my Pilot identity</button></div>'''
    engagement_notifications = "".join(
        f'''<div class="task" style="margin-top:10px"><div class="route">Private live alert</div><p>{html.escape(str(item.get("message") or ""))}</p></div>'''
        for item in reversed(list(live_engagement.get("notifications") or [])[-5:]) if isinstance(item, dict)
    )
    contextual_companion = snapshot.get("contextual_companion") or {}
    companion_profile = dict(contextual_companion.get("profile") or {})
    companion_pending = next((dict(item) for item in reversed(list(contextual_companion.get("pending") or [])) if isinstance(item, dict) and item.get("status") == "awaiting_private_claim"), {})
    companion_support_id = html.escape(str(companion_pending.get("support_id") or ""), quote=True)
    companion_support = ""
    if companion_support_id:
        companion_support = f'''<div class="task" style="margin-top:12px"><div class="route">{html.escape(str(companion_pending.get("category") or "support").replace("_", " "))} · shared room</div><p>{html.escape(str(companion_pending.get("response") or ""))}</p><button class="approve" style="width:100%" onclick="this.disabled=true;command('companion_support_claim',{{support_id:'{companion_support_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Continue this privately</button></div>'''
    companion_enabled = " checked" if companion_profile.get("enabled") else ""
    companion_large = " checked" if companion_profile.get("large_controls") else ""
    companion_body_class = "large-controls" if companion_profile.get("large_controls") else ""
    companion_frequency = str(companion_profile.get("frequency") or "balanced")
    companion_reading = str(companion_profile.get("reading_level") or "standard")
    companion_frequency_options = "".join(f'''<option value="{value}"{" selected" if value == companion_frequency else ""}>{value.replace("_", " ").title()}</option>''' for value in ("off", "low", "balanced", "active"))
    companion_reading_options = "".join(f'''<option value="{value}"{" selected" if value == companion_reading else ""}>{value.replace("_", " ").title()}</option>''' for value in ("child", "simple", "standard", "detailed"))
    private_saves = snapshot.get("private_saves") or {}
    pending_save = dict(private_saves.get("pending") or {})
    pending_save_id = html.escape(str(pending_save.get("save_id") or ""), quote=True)
    pending_save_title = html.escape(str(pending_save.get("title") or "Nothing is waiting to be saved"))
    pending_save_detail = html.escape(str(pending_save.get("detail") or "Say ‘Pilot, save this product, recipe, destination, song or idea.’"))
    pending_save_category = html.escape(str(pending_save.get("category") or "idle"))
    pending_save_state = html.escape(str(pending_save.get("status") or "idle").replace("_", " "))
    pending_save_confidence = int(round(float(pending_save.get("confidence") or 0) * 100))
    pending_save_evidence = "".join(
        f'''<li><strong>{html.escape(str(item.get("kind") or "evidence").replace("_", " ").title())}:</strong> {html.escape(str(item.get("detail") or ""))}</li>'''
        for item in list(pending_save.get("evidence") or [])[:6]
        if isinstance(item, dict)
    )
    pending_save_controls = ""
    if pending_save_id and pending_save.get("status") == "awaiting_private_claim":
        pending_save_controls = f'''<button class="approve" style="width:100%;margin-top:10px" onclick="this.disabled=true;command('private_save_claim',{{save_id:'{pending_save_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save to my Pilot</button>'''
    saved_private_cards = ""
    followthrough_actions = {"product": "shopping", "destination": "trip", "music": "playlist", "recipe": "task", "learning": "learning", "idea": "task"}
    for item in reversed(list(private_saves.get("saved") or [])[-10:]):
        if not isinstance(item, dict):
            continue
        save_id = html.escape(str(item.get("save_id") or ""), quote=True)
        category = str(item.get("category") or "idea")
        action = followthrough_actions.get(category, "task")
        action_label = {"shopping": "Prepare shopping", "trip": "Prepare trip", "playlist": "Prepare playlist", "task": "Create local task", "learning": "Create learning plan"}[action]
        saved_private_cards += f'''<div class="task" style="margin-top:10px"><div class="route">{html.escape(category)}</div><h3>{html.escape(str(item.get("title") or "Saved item"))}</h3><p>{html.escape(str(item.get("detail") or ""))}</p><div class="grid"><button onclick="this.disabled=true;command('saved_research',{{save_id:'{save_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Research</button><button onclick="this.disabled=true;command('saved_action',{{save_id:'{save_id}',action:'{action}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">{action_label}</button><button onclick="this.disabled=true;command('saved_action',{{save_id:'{save_id}',action:'shortlist'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Make shortlist</button><button class="danger" onclick="command('private_save_delete',{{save_id:'{save_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>show(e.message,true))">Delete</button></div></div>'''
    saved_private_cards = saved_private_cards or '<p class="privacy">No programme items saved to this private identity yet.</p>'
    saved_followthrough = snapshot.get("saved_followthrough") or {}
    latest_followthrough = dict(saved_followthrough.get("latest") or {})
    followthrough_title = html.escape(str(latest_followthrough.get("title") or "No saved-item continuation yet"))
    followthrough_state = html.escape(str(latest_followthrough.get("status") or "idle").replace("_", " "))
    followthrough_answer = html.escape(str(latest_followthrough.get("answer") or "Research or prepare an action from one of your saved items above."))
    followthrough_scope = html.escape(json.dumps(latest_followthrough.get("exact_scope") or {}, ensure_ascii=False, indent=2)[:2600])
    followthrough_sources = "".join(
        f'''<li><a href="{html.escape(str(item.get("url") or ""), quote=True)}" rel="noreferrer">{html.escape(str(item.get("title") or "Evidence source"))}</a><br><span class="muted">{html.escape(str(item.get("reason") or ""))}</span></li>'''
        for item in list(latest_followthrough.get("items") or [])[:5]
        if isinstance(item, dict) and str(item.get("url") or "").startswith("https://")
    )
    followthrough_proposal = dict(latest_followthrough.get("service_proposal") or {})
    followthrough_proposal_id = html.escape(str(followthrough_proposal.get("proposal_id") or ""), quote=True)
    followthrough_controls = ""
    if followthrough_proposal.get("status") == "needs_details":
        missing = list(followthrough_proposal.get("missing_fields") or [])
        if missing == ["date"]:
            followthrough_controls = f'''<div class="detail-grid"><label class="detail-label">Travel date<input id="saved-action-date" type="datetime-local"></label><button class="approve" onclick="this.disabled=true;command('saved_action_details',{{proposal_id:'{followthrough_proposal_id}',details:{{date:document.getElementById('saved-action-date').value}}}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save private date</button></div>'''
        else:
            followthrough_controls = f'''<p class="privacy">More private details are required: {html.escape(", ".join(str(value) for value in missing))}.</p>'''
    elif followthrough_proposal.get("status") == "awaiting_private_approval":
        followthrough_controls = f'''<div class="approval-actions"><button class="approve" onclick="this.disabled=true;command('saved_action_decide',{{proposal_id:'{followthrough_proposal_id}',approved:true}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Approve exact proposal</button><button class="danger" onclick="command('saved_action_decide',{{proposal_id:'{followthrough_proposal_id}',approved:false}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>show(e.message,true))">Reject</button></div>'''
    elif followthrough_proposal.get("status") == "approved_pending_adapter":
        followthrough_controls = '<p class="privacy">Approved, but no authorized service adapter has executed it. Nothing was purchased, booked, messaged, or added to an external account.</p>'
    entertainment = snapshot.get("entertainment") or {}
    entertainment_discovery = dict(entertainment.get("latest") or {})
    entertainment_result_cards = ""
    for index, item in enumerate(list(entertainment_discovery.get("items") or [])[:5]):
        if not isinstance(item, dict):
            continue
        entertainment_result_cards += f'''<div class="task" style="margin-top:10px"><div class="route">{html.escape(str(item.get("provider") or "Provider evidence"))} · {html.escape(str(item.get("availability") or "unverified").replace("_", " "))}</div><h3>{html.escape(str(item.get("title") or "Entertainment result"))}</h3><p class="muted">{html.escape(str(item.get("reason") or item.get("detail") or ""))}</p><button style="width:100%" onclick="this.disabled=true;command('entertainment_prepare',{{item_index:{index}}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Prepare official route</button></div>'''
    entertainment_result_cards = entertainment_result_cards or '<p class="privacy">Ask Pilot where to watch a title first. Only an exact official title or video route can be prepared for execution.</p>'
    entertainment_execution = snapshot.get("entertainment_execution") or {}
    latest_entertainment_execution = dict(entertainment_execution.get("latest") or {})
    entertainment_execution_id = html.escape(str(latest_entertainment_execution.get("execution_id") or ""), quote=True)
    entertainment_execution_title = html.escape(str(latest_entertainment_execution.get("title") or "No provider route prepared"))
    entertainment_execution_provider = html.escape(str(latest_entertainment_execution.get("provider") or "idle"))
    entertainment_execution_state = html.escape(str(latest_entertainment_execution.get("status") or "idle").replace("_", " "))
    entertainment_execution_controls = ""
    if latest_entertainment_execution.get("status") == "awaiting_private_confirmation":
        entertainment_execution_controls = f'''<button class="approve" style="width:100%;margin-top:10px" onclick="this.disabled=true;command('entertainment_execute',{{execution_id:'{entertainment_execution_id}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Confirm and open this exact route</button>'''
    entertainment_personalization = snapshot.get("entertainment_personalization") or {}
    pending_entertainment_memory = next((dict(item) for item in reversed(list(entertainment_personalization.get("pending_history") or [])) if isinstance(item, dict)), {})
    pending_entertainment_id = html.escape(str(pending_entertainment_memory.get("pending_id") or ""), quote=True)
    entertainment_memory_control = ""
    if pending_entertainment_id:
        entertainment_memory_control = f'''<div class="task" style="margin-top:12px"><div class="route">Viewing preference · awaiting private claim</div><h3>{html.escape(str(pending_entertainment_memory.get("title") or "Title"))}</h3><p>{html.escape(str(pending_entertainment_memory.get("outcome") or "preference"))}</p><button class="approve" style="width:100%" onclick="this.disabled=true;command('entertainment_memory_claim',{{pending_id:'{pending_entertainment_id}',share_with_household:false}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save privately as me</button></div>'''
    watchlist_items = "".join(f'''<li>{html.escape(str(item.get("title") or "Title"))} <span class="muted">· {html.escape(str(item.get("visibility") or "private").replace("_", " "))}</span></li>''' for item in list(entertainment_personalization.get("watchlists") or [])[-10:] if isinstance(item, dict)) or "<li>No private or explicitly shared watchlist items yet.</li>"
    last_entertainment_route = dict(entertainment_execution.get("last_verified") or {})
    continue_control = '<button style="width:100%;margin-top:10px" onclick="this.disabled=true;command(\'entertainment_continue\').then(r=>{show(r.spoken_response);location.reload()}).catch(e=>{show(e.message,true);this.disabled=false})">Prepare continue watching</button>' if last_entertainment_route else ""
    verified_navigation = snapshot.get("verified_navigation") or {}
    navigation_transaction = dict(verified_navigation.get("active") or verified_navigation.get("last_transaction") or {})
    navigation_state = html.escape(str(navigation_transaction.get("status") or "idle").replace("_", " "))
    navigation_goal = html.escape(str(navigation_transaction.get("goal") or "No action waiting for verification"))
    navigation_expected = html.escape(json.dumps(navigation_transaction.get("expected") or {}, ensure_ascii=False))
    navigation_attempts = len(navigation_transaction.get("attempts") or [])
    navigation_route_count = int(verified_navigation.get("route_memory_count") or 0)
    navigation_controls = ""
    if navigation_transaction.get("status") == "recovery_ready":
        navigation_controls = '''<button class="approve" style="width:100%;margin-top:10px" onclick="this.disabled=true;command('navigation_retry').then(r=>{show(r.spoken_response);location.reload()}).catch(e=>{show(e.message,true);this.disabled=false})">Try verified recovery route</button>'''
    elif navigation_transaction.get("status") == "awaiting_after_observation":
        navigation_controls = '<p class="privacy">The command was delivered, but success is not established. Use Observer Mode or Take a picture below to provide the after-observation.</p>'
    moment = (snapshot.get("pilot_moments") or {}).get("latest") or {}
    moment_title = html.escape(str((moment.get("playback") or {}).get("title") or (moment.get("app") or {}).get("title") or "No Moment prepared"))
    moment_state = html.escape(str(moment.get("delivery_state") or "idle"))
    moment_detail = html.escape(str(moment.get("recent_statement") or "Say ‘Pilot, share that moment’ to prepare one."))
    moment_id = html.escape(str(moment.get("moment_id") or ""), quote=True)
    moment_preview_hash = html.escape(str(moment.get("preview_hash") or ""), quote=True)
    moment_fact = dict(moment.get("fact_check") or {})
    moment_recipient = dict(moment.get("recipient") or {})
    moment_fact_block = ""
    if moment_fact:
        fact_sources = "".join(
            f'''<li><a href="{html.escape(str(item.get("url") or ""), quote=True)}" rel="noreferrer">{html.escape(str(item.get("title") or "Evidence source"))}</a></li>'''
            for item in list(moment_fact.get("sources") or [])[:5]
        )
        moment_fact_block = f'''<div class="task" style="margin-top:10px"><div class="route">{html.escape(str(moment_fact.get("verdict") or "Unverifiable"))} · {int(round(float(moment_fact.get("confidence") or 0) * 100))}%</div><h3>{html.escape(str(moment_fact.get("statement") or ""))}</h3><p class="muted">{html.escape(str(moment_fact.get("summary") or ""))}</p><ul>{fact_sources}</ul></div>'''
    moment_controls = ""
    if moment_id and moment.get("delivery_state") not in {"delivered", "revoked", "deleted", "expired", "reported_and_blocked"}:
        if not moment_recipient:
            moment_controls = f'''<div class="detail-grid"><label class="detail-label">Delivery method<select id="moment-route"><option value="private_phone">This private phone</option><option value="email">Email</option><option value="messaging">Messaging</option><option value="pilot_contact">Pilot contact</option></select></label><label class="detail-label">Recipient<input id="moment-recipient" type="text" maxlength="240" autocomplete="off" placeholder="Only needed for email, messaging or a contact"></label><button class="approve" onclick="this.disabled=true;command('moment_recipient',{{moment_id:'{moment_id}',route:document.getElementById('moment-route').value,recipient:document.getElementById('moment-recipient').value}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save recipient and preview</button></div>'''
        elif moment.get("delivery_state") == "awaiting_send_confirmation":
            moment_controls = f'''<div class="task" style="margin-top:10px"><strong>Private recipient</strong><p>{html.escape(str(moment_recipient.get("address") or ""))} · {html.escape(str(moment_recipient.get("route") or ""))}</p></div><button class="approve" style="width:100%;margin-top:10px" onclick="this.disabled=true;command('moment_send',{{moment_id:'{moment_id}',preview_hash:'{moment_preview_hash}'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Send this exact Moment</button>'''
        elif moment.get("delivery_state") == "approved_pending_adapter":
            moment_controls = '''<p class="privacy">Send was approved, but no authorized delivery account is connected. Nothing left this mother brain.</p>'''
        moment_controls += f'''<div class="approval-actions"><button class="danger" onclick="command('moment_revoke',{{moment_id:'{moment_id}'}}).then(()=>location.reload()).catch(e=>show(e.message,true))">Revoke</button><button class="danger" onclick="command('moment_delete',{{moment_id:'{moment_id}'}}).then(()=>location.reload()).catch(e=>show(e.message,true))">Delete private data</button><button class="danger" onclick="command('moment_report',{{moment_id:'{moment_id}',reason:'unwanted'}}).then(()=>location.reload()).catch(e=>show(e.message,true))">Report abuse</button></div>'''
    screen = snapshot.get("screen_understanding") or {}
    screen_observation_id = html.escape(str(screen.get("observation_id") or ""), quote=True)
    screen_summary = html.escape(str(screen.get("summary") or "Take a picture of the TV to build a private, confidence-labelled screen observation."))
    screen_confidence = int(round(float(screen.get("confidence") or 0) * 100))
    screen_findings = []
    for label, key in (("Subtitles", "subtitles"), ("Scoreboard", "scoreboard"), ("Products", "products"), ("Locations", "locations"), ("Game HUD", "game"), ("Cooking", "cooking"), ("Objects", "objects")):
        finding = dict(screen.get(key) or {})
        if finding.get("detected"):
            screen_findings.append(f"{label} {int(round(float(finding.get('confidence') or 0) * 100))}%")
    screen_finding_text = html.escape(" · ".join(screen_findings) or "No supported element established yet")
    subtitle_text = html.escape(" / ".join((screen.get("subtitles") or {}).get("lines") or []) or "No subtitle line established")
    scoreboard_text = html.escape(str((screen.get("scoreboard") or {}).get("score_text") or (screen.get("scoreboard") or {}).get("clock") or "No score established"))
    product_text = html.escape(" / ".join((screen.get("products") or {}).get("prices") or []) or str((screen.get("products") or {}).get("candidate_text") or "No product established"))
    cooking = dict(screen.get("cooking") or {})
    cooking_text = html.escape(
        "Ingredients: " + (", ".join(str(value) for value in list(cooking.get("ingredients") or [])) or "none established")
        + " · Techniques: " + (", ".join(str(value) for value in list(cooking.get("techniques") or [])) or "none established")
    )
    objects_text = html.escape(", ".join(str(value) for value in list((screen.get("objects") or {}).get("labels") or [])) or "No objects established")
    provider = snapshot.get("provider_metadata") or {}
    provider_name = html.escape(str(provider.get("provider") or "unknown").title())
    provider_title = html.escape(str(provider.get("title") or provider.get("content_id") or "No provider content identifier established"))
    provider_status = html.escape(str(provider.get("metadata_status") or "reference_missing").replace("_", " "))
    provider_attribution = html.escape(str(provider.get("attribution") or "No external catalogue attribution required"))
    provider_catalogue_verified = "yes" if provider.get("catalogue_identity_verified") else "no"
    provider_playback_verified = "yes" if provider.get("current_playback_verified") else "no"
    observer = snapshot.get("observer") or {}
    observer_state = "paused" if observer.get("paused") else "active" if observer.get("active") else "stopped"
    observer_frames = int(observer.get("frames_accepted") or 0)
    observer_profile = html.escape(str(observer.get("capture_profile") or "balanced"))
    observer_interval = int(observer.get("effective_interval_seconds") or 5)
    observer_resource = observer.get("resource_state") or {}
    observer_resource_text = html.escape(
        f"battery {observer_resource.get('battery_band', 'unknown')} · thermal {observer_resource.get('thermal_state', 'nominal')} · every {observer_interval}s"
    )
    perception_timeline = dict((snapshot.get("perception_timeline") or {}).get("current") or {})
    timeline_surface = html.escape(str(perception_timeline.get("surface") or "uncertain"))
    timeline_frame_count = int(perception_timeline.get("frame_count") or 0)
    timeline_confidence = int(round(float(perception_timeline.get("confidence") or 0) * 100))
    timeline_programme = dict(perception_timeline.get("programme") or {})
    timeline_programme_title = html.escape(str(timeline_programme.get("title") or "No stable programme title"))
    timeline_identity_source = html.escape(str(timeline_programme.get("identity_source") or "none").replace("_", " "))
    timeline_subtitles = html.escape(" / ".join(str(value) for value in list(perception_timeline.get("subtitle_timeline") or [])[-4:]) or "No multi-frame subtitle timeline")
    timeline_position = dict(perception_timeline.get("playback_position") or {})
    timeline_position_text = html.escape(
        (
            f"{timeline_position.get('position_seconds')}s / {timeline_position.get('duration_seconds')}s · signed provider"
            if timeline_position.get("verified_by_provider")
            else f"{timeline_position.get('position')} / {timeline_position.get('duration')}"
        )
        if timeline_position else "No playback position observed"
    )
    telemetry_snapshot = snapshot.get("provider_telemetry") or {}
    provider_telemetry = dict(telemetry_snapshot.get("latest") or {})
    telemetry_content = dict(provider_telemetry.get("content") or {})
    telemetry_playback = dict(provider_telemetry.get("playback") or {})
    telemetry_entitlement = dict(provider_telemetry.get("entitlement") or {})
    telemetry_title = html.escape(str(telemetry_content.get("title") or "No signed provider session connected"))
    telemetry_route = html.escape(str(provider_telemetry.get("provider") or "idle").title())
    telemetry_state = html.escape(str(telemetry_playback.get("state") or "unknown"))
    telemetry_position = html.escape(
        f"{int(telemetry_playback.get('position_seconds') or 0)}s / {int(telemetry_playback.get('duration_seconds') or 0)}s"
        if provider_telemetry else "No signed position"
    )
    telemetry_entitlement_status = html.escape(str(telemetry_entitlement.get("status") or "unknown"))
    telemetry_sources = int(telemetry_snapshot.get("trusted_sources") or 0)
    infrared = snapshot.get("infrared_climate") or {}
    infrared_device = dict(infrared.get("device") or {})
    infrared_state = "gateway selected" if infrared.get("connected") else "gateway not found"
    infrared_host = html.escape(str(infrared_device.get("host") or "No local IR bridge connected"))
    infrared_pending = dict(infrared.get("pending_learning") or {})
    infrared_pending_text = html.escape(str(infrared_pending.get("preset") or "No preset waiting for capture").replace("_", " "))
    infrared_buttons = "".join(
        f'''<button data-ir-preset="{html.escape(str(item.get("preset") or ""), quote=True)}">{html.escape(str(item.get("preset") or "").replace("_", " ").title())}</button>'''
        for item in list(infrared.get("learned_presets") or [])
        if isinstance(item, dict) and item.get("preset")
    ) or '<p class="privacy">No commands learned yet.</p>'
    service_scope = html.escape(json.dumps(service_proposal.get("parameters") or {}, ensure_ascii=False, indent=2)[:3000])
    missing_fields = [str(field) for field in service_proposal.get("missing_fields") or []]
    input_types = {"start": "datetime-local", "end": "datetime-local", "to": "email", "quantity": "number"}
    detail_inputs = "".join(
        f'''<label class="detail-label">{html.escape(field.replace("_", " ").title())}<input data-service-field="{html.escape(field, quote=True)}" type="{input_types.get(field, "text")}" autocomplete="off"></label>'''
        for field in missing_fields
    )
    if detail_inputs:
        detail_inputs += f'''<button id="save-service-details" data-proposal="{html.escape(str(service_proposal.get("proposal_id") or ""), quote=True)}" class="approve">Save private details</button>'''
    approval_controls = ""
    if approval_id and approval.get("state") == "pending":
        if route in {"calendar", "communication", "shopping", "booking"} and not service_proposal:
            approval_controls = '''<div class="approval-actions"><button data-command="claim_task" class="approve">Prepare privately as this identity</button></div>'''
        elif service_proposal.get("status") == "needs_details":
            missing = html.escape(", ".join(missing_fields))
            approval_controls = f'''<p class="privacy">Approval is locked until these private details are supplied: {missing}.</p><div class="detail-grid">{detail_inputs}</div>'''
        else:
            approval_controls = f'''<div class="approval-actions"><button data-decision="approve" data-approval="{approval_id}" class="approve">Approve this exact action</button><button data-decision="reject" data-approval="{approval_id}" class="danger">Reject</button></div>'''
    scope_block = f'''<p class="privacy">Exact proposed scope:</p><pre style="white-space:pre-wrap;color:var(--m);font-size:12px">{service_scope}</pre>''' if service_proposal else ""
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
    <meta name="theme-color" content="#06111f"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="/companion/{safe_token}/manifest.webmanifest"><link rel="apple-touch-icon" href="/companion/{safe_token}/icon.svg">
    <title>Pilot Controller</title><style>:root{{--bg:#06111f;--p:#10243a;--p2:#091a2b;--t:#eef7ff;--m:#9db3c8;--c:#5bddff;--g:#62ecae;--r:#e9899d}}
    *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}body{{margin:0;background:linear-gradient(145deg,#06111f,#0c2940);color:var(--t);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh;padding:env(safe-area-inset-top) 14px env(safe-area-inset-bottom)}}main{{max-width:640px;margin:auto;padding:18px 0 40px}}.brand{{color:var(--c);font-weight:850;letter-spacing:.15em;font-size:12px}}h1{{font-size:30px;margin:7px 0 14px}}h2{{font-size:18px;margin:0 0 12px}}.status,.panel{{background:rgba(16,36,58,.95);border:1px solid #294963;border-radius:20px;padding:18px;margin:12px 0}}.status{{display:grid;grid-template-columns:1fr auto;gap:7px 16px}}.online{{color:var(--g);font-weight:800}}.muted{{color:var(--m)}}.volume{{font-size:36px;color:var(--c);font-weight:800;grid-row:1/3;grid-column:2}}button,input,select{{font:inherit}}button{{border:1px solid #31526d;background:#153953;color:var(--t);border-radius:14px;min-height:50px;padding:10px;font-weight:800}}button:active{{transform:scale(.97);background:#1c5378}}button:disabled{{opacity:.5}}.dpad{{display:grid;grid-template-columns:repeat(3,64px);grid-template-rows:repeat(3,58px);gap:8px;justify-content:center}}.up{{grid-column:2}}.left{{grid-column:1;grid-row:2}}.ok{{grid-column:2;grid-row:2;border-radius:50%;background:#146b50}}.right{{grid-column:3;grid-row:2}}.down{{grid-column:2;grid-row:3}}.touchpad{{height:210px;border:1px solid #41627d;border-radius:18px;background:radial-gradient(circle at center,#153953,#071827);display:grid;place-items:center;color:var(--m);font-weight:800;touch-action:pan-y;user-select:none}}.touchpad.armed{{touch-action:none;outline:2px solid var(--c)}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:15px}}.ask{{display:grid;grid-template-columns:1fr auto;gap:8px}}input[type=text],input[type=email],input[type=password],input[type=number],input[type=datetime-local],select{{width:100%;min-width:0;background:#071827;border:1px solid #41627d;color:white;border-radius:13px;padding:14px}}.detail-grid{{display:grid;gap:10px;margin-top:12px}}.detail-label{{display:grid;gap:5px;color:var(--m);font-size:13px}}.task{{padding:15px;border-radius:14px;background:var(--p2)}}.route{{color:var(--g);text-transform:uppercase;font-weight:800;font-size:12px}}.approval-actions{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}}.approve{{background:#146b50}}.danger{{background:#592d3b}}.camera-label{{display:block;border:1px dashed #4d7895;border-radius:14px;padding:14px;text-align:center;color:var(--c);font-weight:800}}input[type=file]{{position:absolute;left:-10000px}}#message{{position:sticky;bottom:12px;background:#081522e8;border:1px solid #31526d;padding:12px;border-radius:13px;color:var(--g);display:none}}.privacy{{font-size:13px;color:var(--m);line-height:1.4}}.mode-hidden{{display:none!important}}.mode-picker{{position:sticky;top:calc(env(safe-area-inset-top) + 8px);z-index:20;background:#10243af2;box-shadow:0 8px 26px #020b14b8}}.mode-picker h2{{margin-bottom:6px}}.quick-modes{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}}.secure-note{{border:1px solid #396785;background:#071827;border-radius:14px;padding:13px;color:var(--m)}}.secure-note strong{{color:var(--c)}}body.large-controls{{font-size:19px}}body.large-controls button{{min-height:64px;font-size:19px}}body.large-controls .privacy,body.large-controls .detail-label{{font-size:16px}}body.large-controls .grid{{grid-template-columns:repeat(2,1fr)}}@media(max-width:390px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}</style></head>
    <body class="{companion_body_class}"><main><div class="brand">TESSARIS · PILOT</div><h1>Private TV controller</h1><p class="privacy">This phone holds no TV pairing key or COMDEX credential. Every action returns to the governed mother.</p>
    <section class="status"><div id="connection-status" class="online">● Mother connected</div><div class="volume">{volume}</div><div>{tv_name} · {current_room_name} · <span id="surface">{surface}</span></div></section>
    <section class="panel mode-picker"><h2>What do you want to use?</h2><select id="controller-mode" aria-label="Choose controller area"><option value="controller">TV Remote &amp; Apps</option><option value="identity">My Pilot — identity, tasks &amp; messages</option><option value="camera">Take a TV photo</option><option value="assistant">Ask Pilot</option><option value="entertainment">Live TV intelligence</option><option value="games">Games</option><option value="learning">Learning</option><option value="advanced">Advanced diagnostics</option></select><div class="quick-modes"><button data-mode-shortcut="controller">TV Remote</button><button data-mode-shortcut="controller" data-activate="touchpad-enable">Mouse / trackpad</button><button data-mode-shortcut="camera">Take TV photo</button></div><p class="privacy">Only the selected area is shown. Your last choice is remembered on this phone.</p><a href="/pilot-household-ca.crt" style="display:block;color:var(--c);font-weight:800;margin-top:8px">Install iPhone trust certificate for signed identity</a></section>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const picker=document.getElementById('controller-mode'),panels=[...document.querySelectorAll('section.panel:not(.mode-picker)')],camera=new Set(['Observer Mode','Multi-frame perception','Visual observer','Screen understanding','Programme evidence','Signed playback telemetry']),entertainment=new Set(['Live Companion','Verified entertainment','Live fact-check','Context and accessibility','Programme cast','Locations and original sources','Live translation','Live sports','Live Event Intelligence','Contextual companion and wellbeing','Save from TV','Continue a saved item','Pilot Moment']),controller=new Set(['Television rooms','Remote','TV touchpad','Netflix','Open','Air conditioning']),advanced=new Set(['Verified navigation','TV reliability qualification','God View controller']);for(const panel of panels){{const title=(panel.querySelector('h2')||{{textContent:''}}).textContent.trim();let group='advanced';if(controller.has(title))group='controller';else if(title==='Private identity'&&panel.querySelector('#identity-name'))group='identity';else if(title==='Pilot stream'||title==='Private approval')group='identity';else if(camera.has(title))group='camera';else if(title==='Ask Pilot')group='assistant';else if(entertainment.has(title))group='entertainment';else if(title==='Games')group='games';else if(title==='Pilot Learning Centre')group='learning';else if(advanced.has(title))group='advanced';panel.dataset.controllerGroup=group}}const apply=mode=>{{if(![...picker.options].some(option=>option.value===mode))mode='controller';picker.value=mode;sessionStorage.setItem('pilot-controller-mode',mode);for(const panel of panels)panel.classList.toggle('mode-hidden',panel.dataset.controllerGroup!==mode);window.scrollTo({{top:0,behavior:'smooth'}})}};picker.onchange=()=>apply(picker.value);document.querySelectorAll('[data-mode-shortcut]').forEach(button=>button.onclick=()=>{{apply(button.dataset.modeShortcut);if(button.dataset.activate)setTimeout(()=>{{const target=document.getElementById(button.dataset.activate);if(target){{target.click();target.closest('section.panel').scrollIntoView({{behavior:'smooth',block:'start'}})}}}},100)}});apply(sessionStorage.getItem('pilot-controller-mode')||'controller')}});</script>
    <section class="panel"><h2>Television rooms</h2><div class="task"><div class="route">{len(registered_tvs)} registered TV surfaces</div><h3>This TV: {current_room_name}</h3><p class="muted">Room names stay on the mother brain and route commands without sharing credentials between televisions.</p></div><div class="detail-grid"><label class="detail-label">Name this room<input id="tv-room-name" type="text" maxlength="60" value="{current_room_name}"></label><button onclick="this.disabled=true;command('tv_room_name',{{room_name:document.getElementById('tv-room-name').value}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save room name</button><label class="detail-label">Prepare playback handoff<select id="tv-room-destination"><option value="">Choose another television</option>{room_options}</select></label><button {'disabled' if not room_options else ''} onclick="this.disabled=true;command('tv_handoff_prepare',{{destination_room:document.getElementById('tv-room-destination').value}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Prepare handoff</button></div>{handoff_control}<p class="privacy">A handoff requires signed, persona-bound playback evidence and separate private confirmation. Pilot never claims the destination is playing until its own adapter verifies it.</p></section>
    <section class="panel"><h2>Remote</h2><div class="dpad"><button class="up" data-command="up">▲</button><button class="left" data-command="left">◀</button><button class="ok" data-command="enter">OK</button><button class="right" data-command="right">▶</button><button class="down" data-command="down">▼</button></div><div class="grid"><button data-command="back">Back</button><button data-command="home">Home</button><button data-command="volume_down">Volume −</button><button data-command="volume_up">Volume +</button><button data-command="play">Play</button><button data-command="pause">Pause</button><button data-command="mute">Mute</button><button data-command="unmute">Unmute</button><button data-command="observe">Refresh state</button></div></section>
    <section class="panel"><h2>Verified navigation</h2><div class="task"><div class="route">{navigation_state} · {navigation_attempts}/3 attempts</div><h3>{navigation_goal}</h3><p class="muted">Expected: {navigation_expected}</p><p class="muted">Remembered verified/failed routes: {navigation_route_count}</p></div>{navigation_controls}<p class="privacy">Button delivery is never treated as screen success. Pilot verifies through permitted device state or a structured after-observation, then remembers the result for this television and surface.</p></section>
    <section class="panel"><h2>TV reliability qualification</h2><div class="task"><div class="route">{reliability_rate}% verified or recovered · {reliability_cases}/20 field cases</div><h3>{"Section 3 closed for this LG" if tv_reliability.get("section_3_closed") else "Qualification still in progress"}</h3><p class="muted">Missing areas: {html.escape(", ".join(str(value).replace("_", " ") for value in reliability_missing) or "none")}</p></div><button style="width:100%;margin-top:10px" onclick="this.disabled=true;command('reliability_baseline').then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Run safe LG baseline</button><ul>{reliability_coverage}</ul><p class="privacy">The baseline reads state, changes volume by one step, restores it and proves duplicate suppression. Simulated adapter checks and button-delivery-only receipts are excluded. Closure requires at least twenty real field cases, 95% verified-or-recovered success, and evidence in every required operation area.</p></section>
    <section class="panel"><h2>TV touchpad</h2><div id="touchpad" class="touchpad" data-armed="false">Touchpad locked for scrolling</div><button id="touchpad-enable" style="width:100%;margin-top:10px">Enable touchpad for 30 seconds</button><p class="privacy">Use this when a website requires a mouse. You—not AION—choose and click legal consent, payment, or account buttons.</p></section>
    <section class="panel"><h2>Netflix</h2><p class="privacy">Search inside Netflix or switch directly to a household profile. Pilot learns visible labels from an owner-submitted chooser observation; credentials are never read or retained.</p><div class="detail-grid"><label class="detail-label">Title<input id="netflix-verify-title" type="text" maxlength="120" value="The Crown"></label><button id="netflix-search-verify">Search Netflix</button></div><button data-command="profile_menu" style="width:100%;margin-top:10px">Switch profile</button><div class="grid">{profile_buttons}</div><details style="margin-top:14px"><summary>Edit the five profile names</summary><div class="detail-grid">{profile_name_inputs}<button id="save-profile-names" class="approve">Save profile names</button></div></details></section>
    <section class="panel"><h2>Open</h2><div class="grid"><button data-command="netflix">Netflix</button><button data-command="youtube">YouTube</button><button data-command="games">Games</button><button data-command="aion">Pilot</button><button data-command="god_view">God View</button></div></section>
    <section class="panel"><h2>Air conditioning</h2><div class="task"><div class="route">{infrared_state}</div><h3>Toshiba RAS-24J2KVG-E</h3><p class="muted">{infrared_host} · WH-UC01NE remote</p></div><button id="ir-discover" style="width:100%;margin-top:10px">Discover local IR gateway</button><h3>Learn a complete remote preset</h3><div class="detail-grid"><label class="detail-label">Preset<select id="ir-learn-preset"><option value="off">Off</option><option value="cool_18">Cool 18°C</option><option value="cool_20">Cool 20°C</option><option value="cool_22" selected>Cool 22°C</option><option value="cool_24">Cool 24°C</option><option value="cool_26">Cool 26°C</option><option value="heat_20">Heat 20°C</option><option value="heat_22">Heat 22°C</option><option value="fan_auto">Fan auto</option></select></label><button id="ir-learn-begin">Start learning</button><button id="ir-learn-capture" class="approve">Capture remote command</button></div><p class="privacy">Waiting: {infrared_pending_text}. Point the Toshiba remote at the IR gateway and press the exact command once, then Capture.</p><h3>Learned controls</h3><div class="grid">{infrared_buttons}</div><p class="privacy">Pilot sends locally over Wi-Fi to a line-of-sight infrared transmitter. Infrared is one-way: delivery is audited, but the air conditioner’s actual state is not claimed as verified.</p></section>
    <section class="panel"><h2>God View controller</h2><p class="privacy">These controls travel through the governed mother brain, so they work even when the LG browser does not expose its gamepad.</p><div class="dpad"><button class="up" data-command="god_up">▲</button><button class="left" data-command="god_left">◀</button><button class="ok" data-command="god_select">OK</button><button class="right" data-command="god_right">▶</button><button class="down" data-command="god_down">▼</button></div><div class="grid"><button data-command="god_lapland">Fly to Lapland</button><button data-command="god_home_region">Fly home</button><button data-command="god_pilot">✈ Pilot Mode</button><button data-command="god_earth">Whole Earth</button><button data-command="god_nasa">NASA Earth</button><button data-command="god_iss">Live View from Space</button><button data-command="god_track_iss">Track ISS</button><button data-command="god_back">Pilot Home</button></div></section>
    <section class="panel"><h2>Games</h2><div class="task"><div class="route">{gaming_state}</div><h3>{gaming_title}</h3><p class="muted">{gaming_controller_count} locally observed controller profiles · Provider open is not gameplay · Search is not launch</p></div><button id="detect-gamepad" style="width:100%;margin-top:10px">Detect and test this phone/browser gamepad</button><p id="gamepad-status" class="privacy">No controller input test has run on this page.</p><p class="privacy">Open GeForce NOW first. Prefer NVIDIA’s QR/device sign-in when offered. Otherwise focus the matching field on the TV, then send it from here. Pilot delivers the text once and does not retain or audit its value.</p><div class="detail-grid"><label class="detail-label">NVIDIA email or username<input id="game-user" type="text" maxlength="320" autocomplete="username"></label><button data-private-field="game-user" data-purpose="username">Send username to focused TV field</button><label class="detail-label">NVIDIA password<input id="game-password" type="password" maxlength="320" autocomplete="current-password"></label><button data-private-field="game-password" data-purpose="password">Send password to focused TV field</button><label class="detail-label">Game title<input id="game-search" type="text" maxlength="160" autocomplete="off" placeholder="For example: Fortnite"></label><button data-private-field="game-search" data-purpose="game_search">Send title to focused game search</button></div><p class="privacy"><strong>Provider boundary:</strong> QR/device sign-in, CAPTCHA, two-factor approval, terms and the final sign-in action remain yours. On local HTTP, do not type a real password; use provider QR/device sign-in or the trusted HTTPS controller. Pilot only reports a game as playing after title, stream-readiness and signed playing evidence are all present.</p></section>
    <section class="panel"><h2>Pilot Learning Centre</h2><p class="privacy">Anonymous local learner profiles keep progress separate without child accounts. Choose a bounded age, difficulty and subject; Pilot adapts weak skills without advertising or paid AI.</p><div class="detail-grid"><label class="detail-label">Age band<select id="education-age"><option>6-7</option><option>8-9</option><option>10-12</option></select></label><label class="detail-label">Difficulty<select id="education-difficulty"><option value="foundation">Foundation</option><option value="developing">Developing</option><option value="challenge">Challenge</option></select></label><label class="detail-label">Subject<select id="education-subject"><option value="spanish">Spanish</option><option value="mathematics">Mathematics</option><option value="science">Science</option></select></label></div><div class="grid"><button data-education-start="explorer_a">Start Explorer A</button><button data-education-start="explorer_b">Start Explorer B</button><button id="education-repeat">Hear it again</button></div><div id="education-status" class="task" style="margin-top:12px">Choose a learner to begin.</div><div id="education-choices" class="detail-grid"></div><button id="education-next" class="approve" style="width:100%;margin-top:10px;display:none">Next challenge</button><div class="detail-grid"><input id="education-pronunciation" maxlength="160" placeholder="Local speech transcript for pronunciation"><button id="education-check-pronunciation">Check pronunciation locally</button><select id="education-parent-profile"><option value="explorer_a">Explorer A parent report</option><option value="explorer_b">Explorer B parent report</option></select><button id="education-parent-report">Show private parent progress</button><input id="education-parent-note" maxlength="240" placeholder="Private parent correction or practice note"><button id="education-parent-correction">Save parent correction</button></div><pre id="education-parent-output" style="white-space:pre-wrap"></pre><p class="privacy">Original code-generated illustrations replace emoji-only teaching. No ads, open-web links, purchases, child logins, raw voice, or raw pronunciation transcripts are retained. Parent controls stay on the private phone.</p></section>
    <section class="panel"><h2>Private identity</h2><div class="task"><div class="route">Active on shared screens</div><h3>{active_identity_name}</h3><p class="muted">Private details remain on this phone. A signed phone-possession activation is required before a shared screen can select a person.</p></div><div id="identity-security" class="secure-note" data-secure-url="{secure_companion_url}"><strong>Signed phone security</strong><div id="identity-security-message">Checking this connection…</div></div><div class="detail-grid"><input id="identity-name" maxlength="80" placeholder="Display name"><select id="identity-role"><option value="adult">Independent adult</option><option value="child">Guardian-controlled child</option></select><select id="identity-guardian"><option value="">Choose guardian for a child</option>{identity_options}</select><button id="identity-onboard" class="approve">Create private identity</button></div><pre id="identity-result" style="white-space:pre-wrap"></pre><h3>My Pilot memory</h3><div class="detail-grid"><input id="identity-memory" maxlength="500" placeholder="Something Pilot should remember"><select id="identity-memory-scope"><option value="private">Only me</option><option value="household_shared">Share with household</option></select><button id="identity-memory-add">Save memory with this scope</button><button id="identity-export">Export my identity data</button></div>{memory_cards}<pre id="identity-export-result" style="white-space:pre-wrap;max-height:300px;overflow:auto"></pre><h3>Connected-service consent</h3><div class="detail-grid"><input id="identity-service" maxlength="80" placeholder="Service, for example google_tasks"><input id="identity-scopes" maxlength="500" placeholder="Exact scopes, separated by commas"><select id="identity-device"><option value="">Choose the trusted phone approving this</option>{trusted_device_options}</select><button id="identity-consent-grant" class="approve">Grant these exact scopes</button></div>{consent_cards}<p class="privacy">The recovery code is shown once. Signed-phone possession, lost-device revocation, scoped service consent and memory inspection/export/delete are enforced by the mother brain. Native biometric attestation remains required before Pilot calls an approval biometric.</p></section>
    <script>window.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{{const security=document.getElementById('identity-security'),container=document.getElementById('identity-result').parentElement,buttons=[...container.querySelectorAll('button')],bind=buttons.find(button=>button.textContent.startsWith('Bind this browser phone')),activate=buttons.find(button=>button.textContent.startsWith('Activate selected person'));if(!bind||!activate)return;if(window.isSecureContext){{security.querySelector('#identity-security-message').textContent='Secure connection ready. Bind this phone once, then activate the selected identity.';bind.textContent='Bind this phone with a signed key';return}}security.querySelector('#identity-security-message').textContent='Your identity is saved. This standard controller cannot create a phone key; open the trusted controller below.';bind.textContent='Open secure identity setup';bind.onclick=()=>{{const url=security.dataset.secureUrl;if(url)location.href=url;else show('The trusted controller is not available.',true)}};activate.disabled=true;activate.textContent='Bind securely before activation'}},0));</script>
    <section class="panel"><h2>Pilot stream</h2><p class="privacy">This is agent-to-agent coordination: messages arrive in a person's Pilot inbox; delegated tasks remain requests until that recipient accepts.</p><div class="detail-grid"><select id="inbox-persona">{identity_options}</select><input id="inbox-list-name" maxlength="100" placeholder="New personal or household list"><select id="inbox-list-scope"><option value="private">Private list</option><option value="household_shared">Household shared list</option></select><button id="inbox-create-list">Create list</button><input id="inbox-task-title" maxlength="240" placeholder="Add a task"><select id="inbox-assignee"><option value="">Assign to myself</option>{identity_options}</select><button id="inbox-create-task" class="approve">Add or send task request</button><textarea id="inbox-message" maxlength="2000" style="width:100%;min-height:90px;background:#071827;border:1px solid #41627d;color:white;border-radius:13px;padding:14px" placeholder="Message another person's Pilot"></textarea><select id="inbox-recipient"><option value="">Choose a Pilot recipient</option>{identity_options}</select><button id="inbox-send-message">Send to Pilot inbox</button></div><h3>Private contacts</h3><div class="detail-grid"><input id="contact-name" maxlength="100" placeholder="Name, for example Becca"><input id="contact-email" type="email" maxlength="180" placeholder="Email (optional)"><input id="contact-whatsapp" type="tel" maxlength="40" placeholder="WhatsApp number with country code (optional)"><select id="contact-pilot"><option value="">Not linked to a Pilot identity</option>{identity_options}</select><select id="contact-route"><option value="whatsapp">Prefer WhatsApp</option><option value="email">Prefer email</option><option value="pilot">Prefer Pilot-to-Pilot</option></select><button id="contact-import">Choose from phone contacts</button><button id="contact-save" class="approve">Save private contact</button></div><p class="privacy">Phone contact selection is available only on supported trusted HTTPS browsers and always requires your tap. Web pages cannot enumerate WhatsApp contacts. Manual entry always works.</p>{contact_cards}<h3>Prepared external handoffs</h3>{external_delivery_cards}<h3>Tasks</h3>{inbox_task_cards}<h3>Reminders</h3><div class="detail-grid"><select id="reminder-task"><option value="">Choose a task</option>{task_options}</select><select id="reminder-trigger"><option value="time">At a time</option><option value="arrival">On arrival</option><option value="departure">On departure</option><option value="journey">During a journey</option><option value="closing_time">Before closing time</option></select><input id="reminder-at" type="datetime-local"><input id="reminder-location" maxlength="160" placeholder="Location label"><input id="reminder-location-permission" maxlength="160" placeholder="Location permission receipt (required for location triggers)"><input id="reminder-repeat" maxlength="80" placeholder="Repeat: none, daily, weekly…"><button id="reminder-add">Schedule reminder</button></div>{reminder_cards}<h3>Agent messages</h3>{inbox_message_cards}<p class="privacy">The recipient address and your sending account are separate. Email or WhatsApp remains prepared until you approve it and connect an authorized sender account. Location reminders require explicit location permission.</p></section>
    <section class="panel"><h2>Communication</h2><p class="privacy">Pilot drafts locally first. The exact private recipient and content must be approved here; delivery is never claimed without a provider receipt.</p><div class="detail-grid"><label class="detail-label">Contact<select id="communication-contact"><option value="">Choose a private contact</option>{contact_options}</select></label><label class="detail-label">Route<select id="communication-channel"><option value="email">Email</option><option value="whatsapp">WhatsApp handoff</option><option value="pilot">Pilot</option></select></label><input id="communication-subject" maxlength="240" placeholder="Subject"><textarea id="communication-body" maxlength="20000" style="width:100%;min-height:110px;background:#071827;border:1px solid #41627d;color:white;border-radius:13px;padding:14px" placeholder="Message or reply"></textarea><button id="communication-draft" class="approve">Draft with AION Native</button></div>{communication_cards}<h3>Received summaries</h3>{received_cards}<p class="privacy">Child external communication requires a separate guardian decision. Calls are prepared only; placement requires an explicit tap on an authorized phone surface.</p></section>
    <section class="panel"><h2>Calendar and planning</h2><div class="task"><div class="route">Google account · {'connected' if google_bindings else 'not connected'}</div><p>{'Authorized services: ' + html.escape(', '.join(str(service) for binding in google_bindings for service in list(binding.get('services') or []))) if google_bindings else 'A registered Pilot Google OAuth client and your private authorization are still required.'}</p></div><p class="privacy">Create, reschedule and cancel are separate exact approvals. Availability exposes free slots—not private event titles.</p><div class="detail-grid"><label class="detail-label">Action<select id="calendar-action"><option value="create">Create event</option><option value="reschedule">Reschedule exact event</option><option value="cancel">Cancel exact event</option></select></label><input id="calendar-title" maxlength="240" placeholder="Event title"><label class="detail-label">Start<input id="calendar-start" type="datetime-local"></label><label class="detail-label">End<input id="calendar-end" type="datetime-local"></label><input id="calendar-event-id" maxlength="240" placeholder="Provider event ID for reschedule or cancel"><input id="calendar-location" maxlength="300" placeholder="Location"><label class="detail-label">Travel minutes<input id="calendar-travel" type="number" min="0" max="1440" value="0"></label><label class="detail-label">Reminder minutes<input id="calendar-reminder" type="number" min="0" max="10080" value="30"></label><button id="calendar-prepare" class="approve">Check conflicts and prepare</button></div>{calendar_cards}<p class="privacy">Execution remains unavailable until this person completes Google OAuth and grants the exact Calendar scopes.</p></section>
    <section class="panel" style="border:2px solid #e45b5b"><h2 style="font-size:28px">Pilot Guardian</h2><div class="task"><div class="route">{guardian_state}</div><h3>{'Urgent help flow active' if latest_guardian else 'Trusted-contact urgent help'}</h3><p>Guardian alerts authorized trusted contacts. It does not diagnose a fall and never claims ambulance dispatch without a tested official route.</p></div><div class="detail-grid"><label class="detail-label">Emergency contact<select id="guardian-contact"><option value="">Choose trusted contact</option>{contact_options}</select></label><label class="detail-label">Alert route<select id="guardian-channel"><option value="pilot">Pilot</option><option value="whatsapp">WhatsApp</option><option value="email">Email</option></select></label><label class="detail-label"><input id="guardian-location" type="checkbox"> Share location during Guardian alert</label><input id="guardian-location-receipt" maxlength="160" placeholder="Explicit location permission receipt"><button id="guardian-permission">Save separate emergency permission</button><button id="guardian-help" class="danger" style="min-height:78px;font-size:22px">I need help</button>{f'<button id="guardian-confirm" class="danger" data-incident="{guardian_id}" style="min-height:78px;font-size:22px">CONFIRM TRUSTED-CONTACT ALERT</button><button id="guardian-cancel" data-incident="{guardian_id}">False alarm — cancel</button>' if latest_guardian.get("status") == "awaiting_large_confirmation" else ''}</div><p class="privacy">Configured emergency contacts: {len(guardian_permissions)}. Connectivity failure produces a visible fallback; it is never silently reported as delivered.</p></section>
    <section class="panel"><h2>Ask Pilot</h2><div class="ask"><input id="ask" type="text" maxlength="300" placeholder="Plan, search, control, or refine…"><button id="send">Send</button></div><button id="push-to-talk" style="width:100%;margin-top:10px">Hold to speak privately</button><p id="push-to-talk-state" class="privacy">Phone audio exists only while held, is transcribed locally, and is deleted immediately. Trusted HTTPS is required on iPhone.</p><p class="privacy">Your request goes to the mother brain. Purchases, bookings, messages and calendar changes still stop at a private approval gate.</p></section>
    <section class="panel"><h2>Live Companion</h2><div class="task"><div class="route">{research_mode}</div><h3>{live_app}</h3><p>{live_statement}</p><p class="muted">{research_answer}</p><ul>{source_links}</ul></div><p class="privacy">Context is captured only after an explicit Pilot request. Raw audio and protected TV pixels are not retained.</p></section>
    <section class="panel"><h2>Verified entertainment</h2>{entertainment_result_cards}<div class="task" style="margin-top:12px"><div class="route">{entertainment_execution_provider} · {entertainment_execution_state}</div><h3>{entertainment_execution_title}</h3><p class="muted">Entitlement: {html.escape(str(latest_entertainment_execution.get("entitlement") or "unknown"))}</p><p>Provider open verified: {"yes" if latest_entertainment_execution.get("provider_open_verified") else "no"} · Playback verified: {"yes" if latest_entertainment_execution.get("playback_verified") else "no"}</p></div>{entertainment_execution_controls}{continue_control}{entertainment_memory_control}<button style="width:100%;margin-top:10px" onclick="this.disabled=true;command('entertainment_watchlist_add',{{visibility:'private'}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Add exact signed-in title to my watchlist</button><ul>{watchlist_items}</ul><p class="privacy">A search result is not a subscription entitlement, opening a provider is not playback, and shared-TV speech never selects a person’s private history. Pilot reports playback only when both the title and playing state are explicitly observed.</p></section>
    <section class="panel"><h2>Live fact-check</h2><div class="task"><div class="route">{live_verdict} · confidence {live_confidence}%</div><h3>{html.escape(str(live_news.get("statement") or "Say ‘Pilot, fact check that’ immediately after a claim."))}</h3><p class="muted">{html.escape(str(live_news.get("summary") or "No evidence result yet"))}</p><p class="privacy">{len(list(live_news.get("sources") or []))} retained sources · mean source quality {live_source_quality}% · {live_contradictions} contradictions · {live_latency} ms</p></div>{live_claims}<ul>{live_sources}</ul><p class="privacy"><strong>Correction timeline:</strong> {live_timeline}</p><p class="privacy">Pilot speaks the short verdict without replacing what is playing. Ask “Pilot, show me the evidence”, “who disagrees?”, or “explain the difference.” Follow-ups are derived from the frozen evidence record and cannot invent a source.</p></section>
    <section class="panel"><h2>Context and accessibility</h2><div class="task"><div class="route">{scene_mode} · confidence {scene_confidence}%</div><h3>{scene_answer}</h3><p class="muted">{scene_uncertainty}</p><ul>{scene_facts}</ul><p><strong>Descriptive summary:</strong> {scene_accessibility}</p><p><strong>Learning activity:</strong> {scene_learning_text}</p></div><p class="privacy">Pilot uses only recent local dialogue, owner-captured subtitles and the current structured screen observation. Joke/reference answers distinguish interpretation from evidence. Child mode avoids mature additions. Descriptions do not identify people. No future plot evidence is used and playback remains on screen.</p></section>
    <section class="panel"><h2>Programme cast</h2><div class="task"><div class="route">Evidence-backed cast · {programme_cast_source}</div><h3>{programme_cast_title}</h3><p>{programme_cast_answer}</p><ul>{programme_cast_items}</ul></div><p class="privacy">Pilot can list the verified main cast or answer an exact character question. It does not use face recognition, does not identify the person currently visible, and does not claim that every listed cast member appears in the current scene.</p></section>
    <section class="panel"><h2>Locations and original sources</h2><div class="task"><div class="route">Structured public evidence · {programme_origin_source}</div><h3>{programme_origin_title}</h3><p>{programme_origin_answer}</p><ul>{programme_origin_facts}</ul></div><p class="privacy">Filming location, story setting and source work are different facts. Pilot reports only properties present in one exact structured programme record, does not infer the current scene location and does not search faces or copy programme media.</p></section>
    <section class="panel"><h2>Live translation</h2><div class="task"><div class="route">{translation_route} · confidence {translation_confidence}%</div><p class="muted">{translation_source}</p><h3>{translation_text}</h3><p class="muted">{translation_uncertainty}</p></div><p class="privacy">Translation runs on the mother brain from bounded local dialogue or an owner-captured subtitle. It uses no web search or paid AI, retains no raw audio or pixels, and keeps the programme playing.</p></section>
    <section class="panel"><h2>Live sports</h2><div class="task"><div class="route">Observed + rule interpretation · confidence {sports_confidence}%</div><p class="muted">Captured scoreboard: {sports_score}</p><h3>{sports_answer}</h3><p>{sports_rule}</p><p class="muted">{sports_limit}</p></div><p class="privacy">Pilot distinguishes the captured score or commentary from its rule explanation. It does not identify unseen players or claim the referee was correct. Capture the screen again for a current score. Playback remains on screen.</p></section>
    <section class="panel"><h2>Live Event Intelligence</h2><div class="task"><div class="route">{live_event_kind} · {live_event_reconciliation} · confidence {live_event_confidence}%</div><h3>{live_event_answer}</h3><p class="muted">Feed: {live_event_provider_name} · {live_event_provider_state}</p></div><pre style="white-space:pre-wrap;color:var(--m);font-size:12px">{live_event_fact_text}</pre>{pending_watch_controls}{engagement_notifications}<p class="privacy"><strong>Connectors:</strong> football-data.org {football_connection}; Ticketmaster {ticketmaster_connection}. Provider facts, owner-captured screen evidence, and Pilot interpretation remain separate. API keys stay on the mother brain; raw provider responses are not retained. Alerts are identity-bound on this private phone and do not enable betting. Playback remains on screen.</p></section>
    <section class="panel"><h2>Contextual companion and wellbeing</h2><div class="detail-grid"><label class="detail-label"><input id="companion-enabled" type="checkbox"{companion_enabled}> Opt in to companion offers</label><label class="detail-label">Frequency<select id="companion-frequency">{companion_frequency_options}</select></label><label class="detail-label">Reading level<select id="companion-reading">{companion_reading_options}</select></label><label class="detail-label">Quiet from<input id="companion-quiet-start" type="time" value="{html.escape(str(companion_profile.get('quiet_start') or '21:00'), quote=True)}"></label><label class="detail-label">Quiet until<input id="companion-quiet-end" type="time" value="{html.escape(str(companion_profile.get('quiet_end') or '08:00'), quote=True)}"></label><label class="detail-label"><input id="companion-large" type="checkbox"{companion_large}> Larger, simpler controls</label><button class="approve" onclick="this.disabled=true;command('companion_configure',{{enabled:document.getElementById('companion-enabled').checked,frequency:document.getElementById('companion-frequency').value,reading_level:document.getElementById('companion-reading').value,quiet_start:document.getElementById('companion-quiet-start').value,quiet_end:document.getElementById('companion-quiet-end').value,large_controls:document.getElementById('companion-large').checked}}).then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Save private companion settings</button></div>{companion_support}<button style="width:100%;margin-top:12px" onclick="this.disabled=true;command('companion_handoff_phone').then(r=>{{show(r.spoken_response);location.reload()}}).catch(e=>{{show(e.message,true);this.disabled=false}})">Continue the TV conversation privately here</button><p class="privacy">Pilot identifies itself as an AI system. Companion mode is opt-in, frequency-limited and quiet-time aware. It cannot claim consciousness, demand exclusivity, optimize for dependency, diagnose illness or claim emergency dispatch. Urgent support and trusted-contact actions require a separate explicit confirmation.</p></section>
    <section class="panel"><h2>Save from TV</h2><div class="task"><div class="route">{pending_save_category} · {pending_save_state} · confidence {pending_save_confidence}%</div><h3>{pending_save_title}</h3><p>{pending_save_detail}</p><ul>{pending_save_evidence}</ul></div>{pending_save_controls}<p class="privacy">The shared television only prepared this evidence card. It has not chosen a person, purchased anything, sent a message, or added it to anyone’s memory. Press Save to my Pilot on this private phone to claim it.</p><h3 style="margin-top:18px">Saved to this identity</h3>{saved_private_cards}</section>
    <section class="panel"><h2>Continue a saved item</h2><div class="task"><div class="route">{followthrough_state}</div><h3>{followthrough_title}</h3><p>{followthrough_answer}</p><ul>{followthrough_sources}</ul><pre style="white-space:pre-wrap;color:var(--m);font-size:12px">{followthrough_scope}</pre></div>{followthrough_controls}<p class="privacy">A saved item is evidence and memory, not standing authority. Research changes nothing externally. Shopping, booking and music proposals require a new exact private approval, and approval still does not claim execution without an authorized adapter and verified receipt.</p></section>
    <section class="panel"><h2>Pilot Moment</h2><div class="task"><div class="route">{moment_state}</div><h3>{moment_title}</h3><p>{moment_detail}</p></div>{moment_fact_block}{moment_controls}<p class="privacy">Recipient selection and Send happen only on this private phone. The shared TV cannot choose a person or transmit the card. Protected programme audio or video is never copied.</p></section>
    <section class="panel"><h2>Screen understanding</h2><div class="task"><div class="route">Confidence {screen_confidence}%</div><h3>{screen_summary}</h3><p class="muted">{screen_finding_text}</p><p><strong>Subtitle:</strong> {subtitle_text}</p><p><strong>Score:</strong> {scoreboard_text}</p><p><strong>Product evidence:</strong> {product_text}</p><p><strong>Cooking evidence:</strong> {cooking_text}</p><p><strong>Object labels:</strong> {objects_text}</p></div><div class="detail-grid"><label class="detail-label">Correct Pilot’s observation<select id="screen-correction-field"><option value="scene">Scene</option><option value="subtitle">Subtitle</option><option value="scoreboard">Scoreboard</option><option value="product">Product</option><option value="location">Location</option></select></label><input id="screen-correction-value" type="text" maxlength="240" placeholder="Tell Pilot what is actually on screen"><button id="save-screen-correction" data-observation="{screen_observation_id}" class="approve">Save correction</button></div><p class="privacy">Ingredients, techniques and objects are reported only from recognized OCR terms or bounded local labels. People remain unknown; Pilot never guesses face identity. Product claims require evidence checking, and purchases still require private confirmation.</p></section>
    <section class="panel"><h2>Programme evidence</h2><div class="task"><div class="route">{provider_name} · {provider_status}</div><h3>{provider_title}</h3><p class="muted">Catalogue identity verified: {provider_catalogue_verified} · Current playback verified: {provider_playback_verified}</p><p class="muted">{provider_attribution}</p></div><p class="privacy">A repeated screen title may be checked against a bounded public catalogue. That establishes only the programme record—not what is playing, regional availability, subscription entitlement, or household access. Those facts require separate signed provider evidence.</p></section>
    <section class="panel"><h2>Signed playback telemetry</h2><div class="task"><div class="route">{telemetry_route} · {telemetry_state}</div><h3>{telemetry_title}</h3><p><strong>Position:</strong> {telemetry_position}</p><p><strong>Entitlement:</strong> {telemetry_entitlement_status}</p><p class="muted">Trusted persona-bound sources: {telemetry_sources}</p></div><p class="privacy">Only a locally approved adapter with a valid Ed25519 signature can establish these facts. Packets expire, nonces cannot replay, provider responses and account identifiers are not retained, and an entitlement claim requires its own granted scope.</p></section>
    <section class="panel"><h2>Observer Mode</h2><div class="task"><div id="observer-state" class="route">● {observer_state} · {observer_frames} frames</div><p id="observer-countdown" class="muted">Camera indicator remains visible while capture is active.</p><p id="observer-message" class="muted">{observer_profile} · {observer_resource_text}. Every frame is deleted after local analysis.</p></div><video id="observer-preview" playsinline muted style="display:none;width:100%;margin-top:12px;border-radius:14px"></video><canvas id="observer-canvas" style="display:none"></canvas><div class="detail-grid"><label class="detail-label">Capture profile<select id="observer-profile"><option value="detail"{' selected' if observer_profile == 'detail' else ''}>Detail · every 3 seconds</option><option value="balanced"{' selected' if observer_profile == 'balanced' else ''}>Balanced · every 5 seconds</option><option value="battery_saver"{' selected' if observer_profile == 'battery_saver' else ''}>Battery saver · every 15 seconds</option></select></label><label class="detail-label">Visible session length<select id="observer-duration"><option value="120">2 minutes</option><option value="300">5 minutes</option><option value="600" selected>10 minutes</option></select></label></div><div class="grid"><button id="observer-start" class="approve">Start visible Observer</button><button id="observer-configure">Apply profile</button><button id="observer-pause">Pause camera</button><button id="observer-resume">Resume visibly</button><button id="observer-stop" class="danger">Stop and close</button></div><p class="privacy">Pilot pauses when this page is hidden, when a reported device thermal state is critical, or when an unplugged battery is critically low. It slows down before those limits. The camera never restarts invisibly after phone sleep. A signed native app is still required for production background execution.</p></section>
    <section class="panel"><h2>Multi-frame perception</h2><div class="task"><div class="route">{timeline_surface} · {timeline_frame_count} frames · confidence {timeline_confidence}%</div><h3>{timeline_programme_title}</h3><p class="muted">Programme stable: {"yes" if timeline_programme.get("stable") else "no"} · Identity source: {timeline_identity_source} · Catalogue verified: {"yes" if timeline_programme.get("catalogue_verified") else "no"} · Current playback verified: {"yes" if timeline_programme.get("current_playback_verified") else "no"}</p><p><strong>Recent subtitles:</strong> {timeline_subtitles}</p><p><strong>Playback position:</strong> {timeline_position_text}</p></div><p class="privacy">A single frame cannot establish a stable surface or programme. Pilot requires repeated agreement, ignores duplicate frames, retains at most twelve structured records, and permanently deletes source pixels.</p></section>
    <section class="panel"><h2>Visual observer</h2><label class="camera-label" for="capture">Take a picture of the TV screen</label><input id="capture" type="file" accept="image/jpeg,image/png,image/heic" capture="environment"><p id="observed" class="privacy">{observed}</p><div id="context-actions" class="grid"></div><p class="privacy">The image is analysed locally with Apple Vision and immediately deleted. Only OCR geometry, classifications, evidence hashes and structured screen meaning are retained. The current programme or game remains on screen.</p></section>
    <section class="panel"><h2>Private identity</h2><div class="task"><div class="route">{persona_name}</div><div class="muted">Personal routes: {bound_services}. Shared TV content never selects a card, calendar or account by itself.</div></div></section>
    <section class="panel"><h2>Private approval</h2><div class="task"><div class="route">{route}</div><h3>{request}</h3><div class="muted">State: {state}</div>{scope_block}{approval_controls}</div></section><div id="message"></div>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const person=()=>document.getElementById('inbox-persona').value,run=async(button,name,args)=>{{button.disabled=true;try{{const result=await command(name,{{persona_id:person(),...args}});show(result.spoken_response);location.reload()}}catch(error){{show(error.message,true);button.disabled=false}}}},iso=id=>{{const value=document.getElementById(id).value;return value?new Date(value).toISOString():''}};const draft=document.getElementById('communication-draft');draft.onclick=()=>run(draft,'communication_draft',{{contact_id:document.getElementById('communication-contact').value,channel:document.getElementById('communication-channel').value,subject:document.getElementById('communication-subject').value,body:document.getElementById('communication-body').value}});document.querySelectorAll('[data-communication-approve]').forEach(button=>button.onclick=()=>run(button,'communication_approve',{{draft_id:button.dataset.communicationApprove,content_hash:button.dataset.contentHash,approved:true}}));const calendar=document.getElementById('calendar-prepare');calendar.onclick=()=>run(calendar,'calendar_prepare',{{action:document.getElementById('calendar-action').value,title:document.getElementById('calendar-title').value,start:iso('calendar-start'),end:iso('calendar-end'),provider_event_id:document.getElementById('calendar-event-id').value,location:document.getElementById('calendar-location').value,travel_minutes:Number(document.getElementById('calendar-travel').value||0),reminder_minutes:Number(document.getElementById('calendar-reminder').value||0)}});document.querySelectorAll('[data-calendar-approve]').forEach(button=>button.onclick=()=>run(button,'calendar_decide',{{proposal_id:button.dataset.calendarApprove,scope_hash:button.dataset.scopeHash,approved:true,accept_conflicts:confirm('Approve even if Pilot detected a private calendar conflict?')}}));const permission=document.getElementById('guardian-permission');permission.onclick=()=>run(permission,'guardian_permission',{{contact_id:document.getElementById('guardian-contact').value,channel:document.getElementById('guardian-channel').value,share_location:document.getElementById('guardian-location').checked,location_permission_receipt:document.getElementById('guardian-location-receipt').value,allow_interruption:true}});const help=document.getElementById('guardian-help');help.onclick=()=>run(help,'guardian_request',{{trigger:'Explicit private-phone help request'}});const confirmAlert=document.getElementById('guardian-confirm');if(confirmAlert)confirmAlert.onclick=()=>run(confirmAlert,'guardian_confirm',{{incident_id:confirmAlert.dataset.incident}});const cancelAlert=document.getElementById('guardian-cancel');if(cancelAlert)cancelAlert.onclick=()=>run(cancelAlert,'guardian_cancel',{{incident_id:cancelAlert.dataset.incident}})}});</script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const persona=()=>document.getElementById('inbox-persona').value,save=document.getElementById('contact-save'),importButton=document.getElementById('contact-import');save.onclick=async()=>{{save.disabled=true;try{{const r=await command('inbox_contact_save',{{persona_id:persona(),display_name:document.getElementById('contact-name').value,email:document.getElementById('contact-email').value,whatsapp:document.getElementById('contact-whatsapp').value,pilot_persona_id:document.getElementById('contact-pilot').value,preferred_route:document.getElementById('contact-route').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true);save.disabled=false}}}};importButton.onclick=async()=>{{if(!navigator.contacts||!navigator.contacts.select)return show('This browser does not offer private contact selection. Enter the contact manually.',true);try{{const selected=await navigator.contacts.select(['name','email','tel'],{{multiple:false}}),contact=selected&&selected[0];if(!contact)return;document.getElementById('contact-name').value=(contact.name||[])[0]||'';document.getElementById('contact-email').value=(contact.email||[])[0]||'';document.getElementById('contact-whatsapp').value=(contact.tel||[])[0]||'';show('Contact copied into the private form. Review it before saving.')}}catch(e){{show('Contact selection was cancelled or unavailable.',true)}}}};document.querySelectorAll('[data-external-approve]').forEach(button=>button.onclick=async()=>{{button.disabled=true;try{{const r=await command('inbox_external_delivery_approve',{{persona_id:persona(),proposal_id:button.dataset.externalApprove}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true);button.disabled=false}}}})}});</script>
    <script>
    const aionNativeFetch=window.fetch.bind(window);
    window.fetch=async(...args)=>{{
      let error;
      for(let attempt=0;attempt<3;attempt++){{
        try{{return await aionNativeFetch(...args)}}catch(e){{error=e;await new Promise(resolve=>setTimeout(resolve,350*(attempt+1)))}}
      }}
      throw error;
    }};
    window.addEventListener('DOMContentLoaded',()=>{{
      const connected=document.getElementById('connection-status');
      const reconnect=async()=>{{
        connected.textContent='● Reconnecting…';
        try{{const response=await aionNativeFetch(base+'/state',{{cache:'no-store'}});if(!response.ok)throw new Error('offline');await refresh();connected.textContent='● Mother connected';connected.style.color='var(--g)'}}
        catch(e){{connected.textContent='● Tap to reconnect';connected.style.color='var(--r)'}}
      }};
      connected.onclick=reconnect;
      window.addEventListener('online',reconnect);
      window.addEventListener('pageshow',reconnect);
      document.addEventListener('visibilitychange',()=>{{if(!document.hidden)reconnect()}});
      const originalEducationRender=renderEducation;
      renderEducation=(education)=>{{
        originalEducationRender(education);
        const lesson=(education||{{}}).session||null;
        if(!lesson)return;
        const score='✅ '+Number(lesson.correct_in_session||0)+'/'+Number(lesson.lesson_total||50);
        const status=document.getElementById('education-status');
        status.textContent=score+' · Question '+Math.min(Number(lesson.round_number||1),Number(lesson.lesson_total||50))+'/'+Number(lesson.lesson_total||50)+' · '+(lesson.feedback||lesson.instruction);
        if(lesson.phase==='feedback'){{
          document.getElementById('education-next').style.display='none';
          [...document.getElementById('education-choices').querySelectorAll('button')].forEach((button,index)=>{{
            if(index===lesson.selected_index&&!lesson.was_correct)button.textContent='❌ '+button.textContent;
            if((lesson.choices||[])[index]&&lesson.choices[index].text===lesson.correct_text)button.textContent='✅ '+button.textContent;
          }});
        }}
      }};
    }});
    </script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const output=document.getElementById('identity-result'),container=output.parentElement,bind=document.createElement('button'),activate=document.createElement('button');bind.textContent='Bind this browser phone with a signed key';activate.textContent='Activate selected person on shared screens';container.insertBefore(bind,output);container.insertBefore(activate,output);const bytesToB64=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes)));const canonical=value=>JSON.stringify(value,Object.keys(value).sort());const dbOpen=()=>new Promise((resolve,reject)=>{{const request=indexedDB.open('pilot-private-identity',1);request.onupgradeneeded=()=>request.result.createObjectStore('keys',{{keyPath:'persona_id'}});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)}});const storeKey=async record=>{{const db=await dbOpen();await new Promise((resolve,reject)=>{{const tx=db.transaction('keys','readwrite');tx.objectStore('keys').put(record);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)}})}};const loadKey=async persona_id=>{{const db=await dbOpen();return new Promise((resolve,reject)=>{{const request=db.transaction('keys').objectStore('keys').get(persona_id);request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)}})}};bind.onclick=async()=>{{const persona_id=document.getElementById('inbox-persona').value;if(!persona_id)return show('Create and select an identity first.',true);try{{if(!crypto.subtle)throw new Error('Trusted HTTPS is required for signed phone possession.');const pair=await crypto.subtle.generateKey({{name:'Ed25519'}},true,['sign','verify']),publicRaw=await crypto.subtle.exportKey('raw',pair.publicKey),begin=await command('identity_phone_begin',{{persona_id,device_label:navigator.platform||'Private phone',public_key:bytesToB64(publicRaw),biometric_capable:!!globalThis.PublicKeyCredential}}),challenge=begin.result,signed={{challenge_id:challenge.challenge_id,persona_id:challenge.persona_id,device_id:challenge.device_id,device_label:challenge.device_label,biometric_capable:challenge.biometric_capable,nonce:challenge.nonce,expires_at:challenge.expires_at}},signature=await crypto.subtle.sign({{name:'Ed25519'}},pair.privateKey,new TextEncoder().encode(canonical(signed))),complete=await command('identity_phone_complete',{{challenge_id:challenge.challenge_id,signature:bytesToB64(signature)}});await storeKey({{persona_id,device_id:complete.result.device_id,privateKey:pair.privateKey}});show(complete.spoken_response)}}catch(e){{show(e.message,true)}}}};activate.onclick=async()=>{{const persona_id=document.getElementById('inbox-persona').value;try{{const record=await loadKey(persona_id);if(!record)throw new Error('Bind this phone to the selected identity first.');const nonce=crypto.randomUUID(),payload={{purpose:'activate_shared_screen',persona_id,device_id:record.device_id,nonce}},signature=await crypto.subtle.sign({{name:'Ed25519'}},record.privateKey,new TextEncoder().encode(canonical(payload))),result=await command('identity_activate',{{...payload,signature:bytesToB64(signature)}});show(result.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}}}});</script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const persona=()=>document.getElementById('inbox-persona').value;document.getElementById('identity-onboard').onclick=async()=>{{try{{const r=await command('identity_onboard',{{display_name:document.getElementById('identity-name').value,role:document.getElementById('identity-role').value,guardian_persona_id:document.getElementById('identity-guardian').value,age_band:'6-12'}});document.getElementById('identity-result').textContent='Recovery code (shown once): '+r.result.recovery_code;show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};document.getElementById('inbox-create-list').onclick=async()=>{{try{{const r=await command('inbox_list_create',{{persona_id:persona(),name:document.getElementById('inbox-list-name').value,scope:document.getElementById('inbox-list-scope').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.getElementById('inbox-create-task').onclick=async()=>{{try{{const r=await command('inbox_task_create',{{persona_id:persona(),title:document.getElementById('inbox-task-title').value,assignee_persona_id:document.getElementById('inbox-assignee').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.getElementById('inbox-send-message').onclick=async()=>{{try{{const r=await command('inbox_message_send',{{persona_id:persona(),recipient_persona_id:document.getElementById('inbox-recipient').value,body:document.getElementById('inbox-message').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.querySelectorAll('[data-inbox-accept]').forEach(b=>b.onclick=()=>command('inbox_delegation_respond',{{persona_id:persona(),task_id:b.dataset.inboxAccept,accept:true}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.querySelectorAll('[data-inbox-decline]').forEach(b=>b.onclick=()=>command('inbox_delegation_respond',{{persona_id:persona(),task_id:b.dataset.inboxDecline,accept:false}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.querySelectorAll('[data-inbox-complete]').forEach(b=>b.onclick=()=>command('inbox_task_complete',{{persona_id:persona(),task_id:b.dataset.inboxComplete}}).then(()=>location.reload()).catch(e=>show(e.message,true)))}});</script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{const persona=()=>document.getElementById('inbox-persona').value;document.getElementById('identity-memory-add').onclick=async()=>{{try{{const r=await command('identity_memory_add',{{persona_id:persona(),kind:'user_note',summary:document.getElementById('identity-memory').value,scope:document.getElementById('identity-memory-scope').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.getElementById('identity-export').onclick=async()=>{{try{{const r=await command('identity_export',{{persona_id:persona()}});document.getElementById('identity-export-result').textContent=JSON.stringify(r.result,null,2);show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};document.querySelectorAll('[data-memory-private]').forEach(b=>b.onclick=()=>command('identity_memory_update',{{persona_id:persona(),memory_id:b.dataset.memoryPrivate,scope:'private'}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.querySelectorAll('[data-memory-household]').forEach(b=>b.onclick=()=>command('identity_memory_update',{{persona_id:persona(),memory_id:b.dataset.memoryHousehold,scope:'household_shared'}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.querySelectorAll('[data-memory-delete]').forEach(b=>b.onclick=()=>command('identity_memory_delete',{{persona_id:persona(),memory_id:b.dataset.memoryDelete}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.getElementById('identity-consent-grant').onclick=async()=>{{try{{const scopes=document.getElementById('identity-scopes').value.split(',').map(x=>x.trim()).filter(Boolean),r=await command('identity_consent_grant',{{persona_id:persona(),service:document.getElementById('identity-service').value,scopes,device_id:document.getElementById('identity-device').value}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.querySelectorAll('[data-consent-revoke]').forEach(b=>b.onclick=()=>command('identity_consent_revoke',{{persona_id:persona(),consent_id:b.dataset.consentRevoke}}).then(()=>location.reload()).catch(e=>show(e.message,true)));document.getElementById('reminder-add').onclick=async()=>{{try{{const r=await command('inbox_reminder_add',{{persona_id:persona(),task_id:document.getElementById('reminder-task').value,trigger:document.getElementById('reminder-trigger').value,at:document.getElementById('reminder-at').value,location_label:document.getElementById('reminder-location').value,location_permission_id:document.getElementById('reminder-location-permission').value,repetition:document.getElementById('reminder-repeat').value||'none'}});show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}}}});</script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{document.getElementById('ir-discover').onclick=async()=>{{try{{const r=await command('ir_discover');show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.getElementById('ir-learn-begin').onclick=async()=>{{try{{const r=await command('ir_learn_begin',{{preset:document.getElementById('ir-learn-preset').value}});show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};document.getElementById('ir-learn-capture').onclick=async()=>{{try{{const r=await command('ir_learn_capture');show(r.spoken_response);location.reload()}}catch(e){{show(e.message,true)}}}};document.querySelectorAll('[data-ir-preset]').forEach(b=>b.onclick=async()=>{{b.disabled=true;try{{const r=await command('ir_send',{{preset:b.dataset.irPreset}});show(r.spoken_response)}}catch(e){{show(e.message,true)}}finally{{b.disabled=false}}}})}});</script>
    <script>window.addEventListener('DOMContentLoaded',()=>{{let recorder=null,stream=null,chunks=[];const button=document.getElementById('push-to-talk'),state=document.getElementById('push-to-talk-state');async function start(event){{event.preventDefault();if(recorder)return;try{{if(!window.isSecureContext||!navigator.mediaDevices)throw new Error('Open the trusted HTTPS controller to use private push-to-talk.');stream=await navigator.mediaDevices.getUserMedia({{audio:true,video:false}});const kind=MediaRecorder.isTypeSupported('audio/mp4')?'audio/mp4':'audio/webm';chunks=[];recorder=new MediaRecorder(stream,{{mimeType:kind}});recorder.ondataavailable=e=>{{if(e.data.size)chunks.push(e.data)}};recorder.start();button.textContent='Release to send';state.textContent='Listening only while held…'}}catch(e){{show(e.message,true)}}}}async function stop(event){{event.preventDefault();const active=recorder;if(!active)return;recorder=null;await new Promise(resolve=>{{active.onstop=resolve;active.stop()}});if(stream)stream.getTracks().forEach(track=>track.stop());stream=null;button.textContent='Hold to speak privately';try{{state.textContent='Transcribing locally…';const blob=new Blob(chunks,{{type:active.mimeType}});const result=await post('/voice',blob,{{'Content-Type':active.mimeType}});state.textContent='Heard: '+result.transcript;show(result.spoken_response||'Done');await refresh()}}catch(e){{state.textContent='Push-to-talk is ready.';show(e.message,true)}}finally{{chunks=[]}}}}button.addEventListener('pointerdown',start);button.addEventListener('pointerup',stop);button.addEventListener('pointercancel',stop)}});</script>
    <script>const base='/companion/{safe_token}',csrf='{safe_csrf}',message=document.getElementById('message');function show(t,bad=false){{message.textContent=t;message.style.color=bad?'var(--r)':'var(--g)';message.style.display='block';setTimeout(()=>message.style.display='none',4500)}}async function post(path,body,headers={{}}){{const r=await fetch(base+path,{{method:'POST',headers:{{'X-AION-CSRF':csrf,...headers}},body}});const j=await r.json().catch(()=>({{error:'Invalid response'}}));if(!r.ok)throw new Error(j.error||'Request failed');return j}}async function command(name,args={{}}){{const requestId=(globalThis.crypto&&crypto.randomUUID)?crypto.randomUUID():"phone-"+Date.now()+"-"+Math.random().toString(16).slice(2);return post('/command',new URLSearchParams({{command:name,arguments:JSON.stringify({{...args,_request_id:requestId}})}}),{{'Content-Type':'application/x-www-form-urlencoded'}})}}async function runButton(b){{b.disabled=true;try{{const r=await command(b.dataset.command);show(r.spoken_response||'Done');await refresh()}}catch(e){{show(e.message,true)}}finally{{b.disabled=false}}}}document.querySelectorAll('[data-command]').forEach(b=>b.onclick=()=>runButton(b));const netflixSearchVerify=document.getElementById('netflix-search-verify');if(netflixSearchVerify)netflixSearchVerify.onclick=async()=>{{const query=document.getElementById('netflix-verify-title').value.trim();if(!query)return show('Enter a Netflix title first.',true);netflixSearchVerify.disabled=true;try{{const r=await command('netflix_search',{{query}});show(r.spoken_response||'Netflix search sent')}}catch(e){{show(e.message,true)}}finally{{netflixSearchVerify.disabled=false}}}};const saveProfileNames=document.getElementById('save-profile-names');if(saveProfileNames)saveProfileNames.onclick=async()=>{{const names=[...document.querySelectorAll('[data-netflix-profile-name]')].map(input=>input.value.trim());if(names.length!==5||names.some(name=>!name))return show('Enter all five profile names in screen order.',true);saveProfileNames.disabled=true;try{{const r=await command('profile_names_save',{{names}});show(r.spoken_response||'Profile names saved');location.reload()}}catch(e){{show(e.message,true);saveProfileNames.disabled=false}}}};
const pad=document.getElementById('touchpad'),padEnable=document.getElementById('touchpad-enable');let padTimer=null;padEnable.onclick=()=>{{pad.dataset.armed='true';pad.classList.add('armed');pad.textContent='Drag to move · tap to click';padEnable.textContent='Touchpad enabled';clearTimeout(padTimer);padTimer=setTimeout(()=>{{pad.dataset.armed='false';pad.classList.remove('armed');pad.textContent='Touchpad locked for scrolling';padEnable.textContent='Enable touchpad for 30 seconds'}},30000)}};let touching=false,lastX=0,lastY=0,total=0,pendingX=0,pendingY=0,lastSent=0;async function flushPointer(force=false){{const now=Date.now();if(!force&&now-lastSent<350)return;if(!pendingX&&!pendingY)return;const dx=Math.max(-240,Math.min(240,Math.round(pendingX*1.8))),dy=Math.max(-240,Math.min(240,Math.round(pendingY*1.8)));pendingX=pendingY=0;lastSent=now;try{{await command('pointer_move',{{dx,dy}})}}catch(e){{show(e.message,true)}}}}pad.onpointerdown=e=>{{if(pad.dataset.armed!=='true')return;touching=true;lastX=e.clientX;lastY=e.clientY;total=0;pendingX=pendingY=0;pad.setPointerCapture(e.pointerId)}};pad.onpointermove=e=>{{if(!touching)return;const dx=e.clientX-lastX,dy=e.clientY-lastY;lastX=e.clientX;lastY=e.clientY;total+=Math.abs(dx)+Math.abs(dy);pendingX+=dx;pendingY+=dy;flushPointer()}};pad.onpointerup=async()=>{{touching=false;await flushPointer(true);if(total<8)try{{await command('pointer_click');show('TV pointer clicked')}}catch(e){{show(e.message,true)}}}};pad.onpointercancel=()=>{{touching=false;pendingX=pendingY=0}};document.querySelectorAll('[data-private-field]').forEach(b=>b.onclick=async()=>{{const input=document.getElementById(b.dataset.privateField),value=input.value;if(!value)return show('Enter the private text first.',true);b.disabled=true;try{{const r=await post('/private-text',new URLSearchParams({{purpose:b.dataset.purpose,value}}),{{'Content-Type':value?'application/x-www-form-urlencoded':'text/plain'}});show(r.spoken_response||'Private text delivered')}}catch(e){{show(e.message,true)}}finally{{input.value='';b.disabled=false}}}});document.getElementById('detect-gamepad').onclick=async()=>{{const status=document.getElementById('gamepad-status'),pads=[...(navigator.getGamepads?navigator.getGamepads():[])].filter(Boolean);if(!pads.length){{status.textContent='No browser Gamepad API device is visible. Press a controller button and try again.';return}}const gamepad=pads[0],events=[];if([...gamepad.buttons].some(button=>button.pressed))events.push('button_pressed');if([...gamepad.axes].some(axis=>Math.abs(axis)>.15))events.push('axis_moved');try{{const r=await command('gaming_controller_observe',{{controller_id:gamepad.id||'browser-gamepad',name:gamepad.id||'Browser gamepad',capabilities:[gamepad.buttons.length?'buttons':'',gamepad.axes.length?'axes':''].filter(Boolean),input_events_seen:events}});status.textContent=r.spoken_response+' '+r.gaming_controller.input_mode+' · '+r.gaming_controller.compatibility}}catch(e){{status.textContent=e.message}}}};function renderEducation(education){{const lesson=(education||{{}}).session||null,status=document.getElementById('education-status'),choices=document.getElementById('education-choices'),next=document.getElementById('education-next');choices.replaceChildren();if(!lesson){{status.textContent='Choose a learner to begin.';next.style.display='none';return}}const profile=((education.profiles||{{}})[lesson.profile_id]||{{}});status.textContent=lesson.display_name+' · '+(profile.subject||'spanish')+' · Round '+lesson.round_number+' · '+(lesson.feedback||lesson.instruction)+' · '+(profile.stars||0)+' stars';for(const choice of lesson.choices||[]){{const b=document.createElement('button');b.textContent=String.fromCharCode(65+choice.index)+'. '+choice.text;b.disabled=lesson.phase!=='question';b.onclick=async()=>{{try{{const r=await command('education_answer',{{choice_index:choice.index}});show(r.spoken_response);renderEducation(r.education)}}catch(e){{show(e.message,true)}}}};choices.appendChild(b)}}next.style.display=lesson.phase==='feedback'?'block':'none'}}document.querySelectorAll('[data-education-start]').forEach(b=>b.onclick=async()=>{{b.disabled=true;try{{const r=await command('education_start',{{profile_id:b.dataset.educationStart,age_band:document.getElementById('education-age').value,difficulty:document.getElementById('education-difficulty').value,subject:document.getElementById('education-subject').value}});show(r.spoken_response);renderEducation(r.education)}}catch(e){{show(e.message,true)}}finally{{b.disabled=false}}}});document.getElementById('education-repeat').onclick=async()=>{{try{{const r=await command('education_repeat');show(r.spoken_response);renderEducation(r.education)}}catch(e){{show(e.message,true)}}}};document.getElementById('education-next').onclick=async()=>{{try{{const r=await command('education_next');show(r.spoken_response);renderEducation(r.education)}}catch(e){{show(e.message,true)}}}};document.getElementById('education-check-pronunciation').onclick=async()=>{{const recognised_text=document.getElementById('education-pronunciation').value.trim();if(!recognised_text)return show('Use local speech-to-text or type what was heard.',true);try{{const r=await command('education_pronunciation',{{recognised_text}});document.getElementById('education-pronunciation').value='';show(r.spoken_response);renderEducation(r.education)}}catch(e){{show(e.message,true)}}}};document.getElementById('education-parent-report').onclick=async()=>{{try{{const r=await command('education_parent_report',{{profile_id:document.getElementById('education-parent-profile').value}});document.getElementById('education-parent-output').textContent=JSON.stringify(r.parent_report,null,2);show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};document.getElementById('education-parent-correction').onclick=async()=>{{const note=document.getElementById('education-parent-note').value.trim();if(!note)return show('Enter a private practice note.',true);try{{const r=await command('education_parent_correction',{{profile_id:document.getElementById('education-parent-profile').value,card_id:'current',note}});document.getElementById('education-parent-note').value='';show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};const saveDetails=document.getElementById('save-service-details');if(saveDetails)saveDetails.onclick=async()=>{{const details={{}};document.querySelectorAll('[data-service-field]').forEach(i=>details[i.dataset.serviceField]=i.value.trim());if(Object.values(details).some(v=>!v)){{show('Complete every required field before saving.',true);return}}saveDetails.disabled=true;try{{const r=await command('service_details',{{proposal_id:saveDetails.dataset.proposal,details}});show(r.spoken_response||'Details saved');location.reload()}}catch(e){{show(e.message,true);saveDetails.disabled=false}}}};const saveCorrection=document.getElementById('save-screen-correction');if(saveCorrection)saveCorrection.onclick=async()=>{{const value=document.getElementById('screen-correction-value').value.trim();if(!saveCorrection.dataset.observation)return show('Capture the screen first.',true);if(!value)return show('Enter the correction first.',true);saveCorrection.disabled=true;try{{const r=await command('screen_correction',{{observation_id:saveCorrection.dataset.observation,field:document.getElementById('screen-correction-field').value,value}});show(r.spoken_response||'Correction saved');location.reload()}}catch(e){{show(e.message,true);saveCorrection.disabled=false}}}};
let observerStream=null,observerTimer=null,observerCountdownTimer=null,observerToken=sessionStorage.getItem('pilot_observer_token')||'',observerBusy=false,observerPolicy={{effective_interval_seconds:5,max_frame_dimension:1280,jpeg_quality:.72}};
function closeObserverCamera(){{if(observerTimer)clearInterval(observerTimer);observerTimer=null;if(observerStream)observerStream.getTracks().forEach(track=>track.stop());observerStream=null;document.getElementById('observer-preview').style.display='none'}}
function renderObserverPolicy(value){{observerPolicy={{...observerPolicy,...(value||{{}})}};const resources=observerPolicy.resource_state||{{}};document.getElementById('observer-state').textContent='● '+(observerPolicy.paused?'paused':observerPolicy.active?'active':'stopped')+' · '+(observerPolicy.frames_accepted||0)+' frames';document.getElementById('observer-message').textContent=(observerPolicy.capture_profile||'balanced').replace('_',' ')+' · battery '+(resources.battery_band||'unknown')+' · thermal '+(resources.thermal_state||'nominal')+' · every '+(observerPolicy.effective_interval_seconds||5)+'s';if(observerCountdownTimer)clearInterval(observerCountdownTimer);observerCountdownTimer=setInterval(()=>{{const remaining=Math.max(0,Math.ceil((Date.parse(observerPolicy.expires_at||0)-Date.now())/1000));document.getElementById('observer-countdown').textContent=observerPolicy.active?'Visible capture · '+remaining+' seconds remaining':'Camera closed'}},1000)}}
async function observerResourceState(visibility=document.visibilityState){{let batteryLevel=null,charging=null;try{{if(navigator.getBattery){{const battery=await navigator.getBattery();batteryLevel=battery.level;charging=battery.charging}}}}catch(e){{}}try{{const r=await command('observer_resource_state',{{battery_level:batteryLevel,charging,thermal_state:'nominal',visibility:visibility==='visible'?'visible':'hidden'}});renderObserverPolicy(r.observer);if((r.observer||{{}}).paused)closeObserverCamera();return r.observer}}catch(e){{return null}}}}
async function stopObserver(notify=true){{closeObserverCamera();if(observerCountdownTimer)clearInterval(observerCountdownTimer);observerCountdownTimer=null;if(notify)try{{const r=await command('observer_stop');renderObserverPolicy(r.observer)}}catch(e){{}}observerToken='';sessionStorage.removeItem('pilot_observer_token')}}
async function observerFrame(){{if(observerBusy||!observerStream||!observerToken||observerPolicy.paused)return;observerBusy=true;const video=document.getElementById('observer-preview'),canvas=document.getElementById('observer-canvas'),maximum=Number(observerPolicy.max_frame_dimension||1280),scale=Math.min(1,maximum/video.videoWidth);canvas.width=Math.max(1,Math.round(video.videoWidth*scale));canvas.height=Math.max(1,Math.round(video.videoHeight*scale));canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);canvas.toBlob(async blob=>{{try{{const r=await post('/perception',blob,{{'Content-Type':'image/jpeg','X-Pilot-Observer':observerToken}});renderObserverPolicy(r.observer||observerPolicy);document.getElementById('observer-message').textContent=((r.multi_frame_perception||{{}}).surface_stable?'Stable: ':'Learning: ')+((r.multi_frame_perception||{{}}).surface||'screen')}}catch(e){{show(e.message,true);closeObserverCamera()}}finally{{observerBusy=false}}}},'image/jpeg',Number(observerPolicy.jpeg_quality||.72))}}
async function attachObserverCamera(){{if(!observerToken)throw new Error('Start Observer Mode first.');if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)throw new Error('Continuous camera requires trusted HTTPS or the native Pilot app.');closeObserverCamera();const policy=await observerResourceState('visible');if(policy&&policy.paused)throw new Error('Observer is paused by its battery, thermal, or visibility policy.');observerStream=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:{{ideal:'environment'}}}},audio:false}});const video=document.getElementById('observer-preview');video.srcObject=observerStream;video.style.display='block';await video.play();document.getElementById('observer-state').textContent='● active · visible camera';await observerFrame();observerTimer=setInterval(observerFrame,Number(observerPolicy.effective_interval_seconds||5)*1000)}}
document.getElementById('observer-start').onclick=async()=>{{try{{const profile=document.getElementById('observer-profile').value,duration=Number(document.getElementById('observer-duration').value),interval={{detail:3,balanced:5,battery_saver:15}}[profile];const r=await command('observer_start',{{duration_seconds:duration,interval_seconds:interval,capture_profile:profile}});observerPolicy=r.observer||observerPolicy;observerToken=observerPolicy.frame_token||'';sessionStorage.setItem('pilot_observer_token',observerToken);renderObserverPolicy(observerPolicy);await attachObserverCamera()}}catch(e){{show(e.message,true);closeObserverCamera()}}}};
document.getElementById('observer-configure').onclick=async()=>{{try{{const profile=document.getElementById('observer-profile').value,interval={{detail:3,balanced:5,battery_saver:15}}[profile],r=await command('observer_configure',{{capture_profile:profile,interval_seconds:interval}});renderObserverPolicy(r.observer);if(observerStream)await attachObserverCamera();show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};
document.getElementById('observer-pause').onclick=async()=>{{closeObserverCamera();try{{const r=await command('observer_pause');renderObserverPolicy(r.observer);show(r.spoken_response)}}catch(e){{show(e.message,true)}}}};
document.getElementById('observer-resume').onclick=async()=>{{try{{observerToken=sessionStorage.getItem('pilot_observer_token')||observerToken;await observerResourceState('visible');const r=await command('observer_resume');renderObserverPolicy(r.observer);await attachObserverCamera();show('Visible Observer Mode resumed')}}catch(e){{show(e.message,true)}}}};
document.getElementById('observer-stop').onclick=()=>stopObserver(true);document.addEventListener('visibilitychange',async()=>{{if(document.visibilityState!=='visible')closeObserverCamera();await observerResourceState(document.visibilityState)}});window.addEventListener('pagehide',()=>{{closeObserverCamera()}});document.getElementById('send').onclick=async()=>{{const input=document.getElementById('ask'),text=input.value.trim();if(!text)return;try{{show('Pilot is working…');const r=await command('ask',{{text}});input.value='';show(r.spoken_response||'Plan ready');await refresh()}}catch(e){{show(e.message,true)}}}};document.getElementById('ask').addEventListener('keydown',e=>{{if(e.key==='Enter')document.getElementById('send').click()}});document.querySelectorAll('[data-decision]').forEach(b=>b.onclick=async()=>{{try{{await post('/decision',new URLSearchParams({{approval_id:b.dataset.approval,decision:b.dataset.decision}}),{{'Content-Type':'application/x-www-form-urlencoded'}});show('Decision recorded');location.reload()}}catch(e){{show(e.message,true)}}}});function actions(p){{const box=document.getElementById('context-actions');box.replaceChildren();let items=[];if(p.view==='profile_chooser')items=[1,2,3,4,5].map(n=>['profile_'+n,'Profile '+n]);else if(p.view==='google_consent')items=[['accept_google','Accept focused choice']];for(const [cmd,label] of items){{const b=document.createElement('button');b.dataset.command=cmd;b.textContent=label;b.onclick=()=>runButton(b);box.appendChild(b)}}}}document.getElementById('capture').onchange=async e=>{{const file=e.target.files[0];if(!file)return;try{{show('Analysing the screen locally…');const r=await post('/perception',file,{{'Content-Type':file.type||'application/octet-stream'}});document.getElementById('observed').textContent=r.inference.summary||'Observation complete';actions(r.inference||{{}});const v=r.navigation_verification;show(v?(v.success?'Navigation verified':'That result was not verified'):'Screen understanding updated',v&&!v.success);setTimeout(()=>location.reload(),650)}}catch(err){{show(err.message,true)}}finally{{e.target.value=''}}}};async function refresh(){{try{{const s=await(await fetch(base+'/state',{{cache:'no-store'}})).json(),c=s.controller||{{}},p=(s.perception||{{}}).inference||{{}},n=s.navigation||{{}};document.querySelector('.volume').textContent=c.volume??'--';document.getElementById('surface').textContent=c.surface||'unknown';if(p.summary)document.getElementById('observed').textContent=p.summary+(n.pending?' · Capture again to verify '+n.pending.action:'');actions(p);renderEducation(s.education||{{}});renderObserverPolicy(s.observer||{{}})}}catch(e){{}}}}setInterval(refresh,2500);refresh();if('serviceWorker'in navigator)navigator.serviceWorker.register(base+'/sw.js',{{scope:base+'/'}}).catch(()=>{{}});</script></main></body></html>'''.encode("utf-8")


def _entry_html(pair_code: str = "000000", *, secure_url: str | None = None, ca_available: bool = False, ca_fingerprint: str = "") -> bytes:
    safe_code = html.escape(pair_code)
    trust = ""
    if secure_url and ca_available:
        trust = f'''<section><h2>Enable secure camera mode</h2><p>1. Download the public Pilot household certificate. 2. Review and install it in Settings. 3. Explicitly enable full trust under Certificate Trust Settings. 4. Return here and open the secure controller.</p><a class="button" href="/pilot-household-ca.crt">Download public trust certificate</a><a class="button" href="{html.escape(secure_url, quote=True)}">Open secure controller</a><p class="fingerprint">CA SHA-256: {html.escape(ca_fingerprint)}</p><p>No private key is downloaded. Remove the Pilot profile from device management to revoke phone trust.</p></section>'''
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pilot Connect</title><style>body{{margin:0;background:#06111f;color:#eef7ff;font-family:-apple-system,sans-serif;padding:28px}}main{{max-width:520px;margin:5vh auto;background:#10243a;border:1px solid #294963;border-radius:24px;padding:28px;text-align:center}}h1{{font-size:32px}}h2{{font-size:20px;margin-top:30px}}p{{color:#9db3c8}}img{{width:min(72vw,300px);background:white;border-radius:18px;padding:14px}}.code{{font-size:34px;letter-spacing:.18em;color:#62ecae;font-weight:850}}input,button,.button{{width:100%;box-sizing:border-box;padding:16px;border-radius:12px;font-size:18px;margin-top:12px;display:block;text-decoration:none;touch-action:manipulation}}input{{background:#071827;border:1px solid #41627d;color:white}}button,.button{{border:0;background:#146b50;color:white;font-weight:800;cursor:pointer}}section{{border-top:1px solid #294963;margin-top:26px}}.fingerprint{{font:11px ui-monospace,monospace;overflow-wrap:anywhere}}</style></head><body><main><h1>Connect to Pilot</h1><img src="/pair.svg" alt="Scan to connect this phone to Pilot"><p>Scan this beacon from another phone, or enter the rotating six-digit code below.</p><div class="code">{safe_code}</div><form method="post" action="/connect"><label for="pilot-code">Six-digit code</label><input id="pilot-code" name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" autocomplete="one-time-code" required autofocus><button type="submit">Open private controller</button></form><p>The standard controller opens immediately. Secure camera mode below is optional and requires explicitly trusting the household certificate.</p>{trust}</main></body></html>'''.encode("utf-8")


def _qr_svg(value: str) -> bytes:
    image = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=3)
    return image.to_string(encoding="unicode").encode("utf-8")


def _manifest(token: str) -> bytes:
    return json.dumps({"name": "Pilot Private Controller", "short_name": "Pilot", "id": f"/companion/{token}", "start_url": f"/companion/{token}", "scope": f"/companion/{token}/", "display": "standalone", "background_color": "#06111f", "theme_color": "#06111f", "icons": [{"src": f"/companion/{token}/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}, separators=(",", ":")).encode("utf-8")


def _icon_svg() -> bytes:
    return b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="42" fill="#06111f"/><path d="M96 26c38 0 69 31 69 69s-31 69-69 69S27 133 27 95 58 26 96 26Z" fill="none" stroke="#5bddff" stroke-width="12"/><path d="M61 119 96 52l35 67M76 93h40" fill="none" stroke="#62ecae" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></svg>'''


class CompanionService:
    """Token-protected phone controller, private handoff and visual observer."""

    def __init__(self, snapshot_provider: Callable[[], Dict[str, Any]], decision_handler: Callable[[str, bool], Dict[str, Any]], *, command_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]] | None = None, perception_handler: Callable[[bytes, str, str | None], Dict[str, Any]] | None = None, private_text_handler: Callable[[str, str], Dict[str, Any]] | None = None, voice_handler: Callable[[bytes, str], Dict[str, Any]] | None = None, provider_telemetry_handler: Callable[[Dict[str, Any], str], Dict[str, Any]] | None = None, preferred_peer: str | None = None, port: int = 8767, token: str | None = None, csrf_token: str | None = None, pair_code: str | None = None, tls_context: ssl.SSLContext | None = None, ca_certificate: bytes | None = None, ca_fingerprint: str = "", secure_controller_url: str | None = None, redirect_public_url: str | None = None) -> None:
        self.snapshot_provider = snapshot_provider
        self.decision_handler = decision_handler
        self.command_handler = command_handler
        self.perception_handler = perception_handler
        self.private_text_handler = private_text_handler
        self.voice_handler = voice_handler
        self.provider_telemetry_handler = provider_telemetry_handler
        self.address = _lan_address(preferred_peer)
        self.port = port
        self.token = token or secrets.token_urlsafe(24)
        self.csrf_token = csrf_token or secrets.token_urlsafe(24)
        self.pair_code = pair_code or f"{secrets.randbelow(1_000_000):06d}"
        self.tls_context = tls_context
        self.ca_certificate = ca_certificate
        self.ca_fingerprint = ca_fingerprint
        self.secure_controller_url = secure_controller_url
        self.redirect_public_url = redirect_public_url
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._bonjour_process: subprocess.Popen[bytes] | None = None
        self._rate_lock = threading.Lock()
        self._requests: Dict[str, deque[float]] = defaultdict(deque)

    @property
    def public_url(self) -> str:
        port = self._server.server_port if self._server else self.port
        scheme = "https" if self.tls_context else "http"
        return f"{scheme}://{self.address}:{port}/companion/{self.token}"

    @property
    def entry_url(self) -> str:
        port = self._server.server_port if self._server else self.port
        scheme = "https" if self.tls_context else "http"
        return f"{scheme}://{self.address}:{port}"

    def _allow_request(self, address: str) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            recent = self._requests[address]
            while recent and now - recent[0] > 10:
                recent.popleft()
            if len(recent) >= 40:
                return False
            recent.append(now)
            return True

    def start(self) -> None:
        service = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Permissions-Policy", "camera=(self), microphone=(self)")
                if service.tls_context:
                    self.send_header("Strict-Transport-Security", "max-age=31536000")
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data: blob:; form-action 'self'")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _json(self, value: Dict[str, Any], status: int = 200) -> None:
                self._send(json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

            def _csrf(self) -> None:
                if not secrets.compare_digest(self.headers.get("X-AION-CSRF", ""), service.csrf_token):
                    raise PermissionError("Invalid private-controller request token")

            def do_GET(self) -> None:  # noqa: N802
                base = f"/companion/{service.token}"
                request_path = urlparse(self.path).path
                if request_path.rstrip("/") == "":
                    self._send(_entry_html(service.pair_code, secure_url=service.secure_controller_url, ca_available=service.ca_certificate is not None, ca_fingerprint=service.ca_fingerprint), "text/html; charset=utf-8")
                elif request_path == "/pair.svg":
                    self._send(_qr_svg(service.entry_url), "image/svg+xml")
                elif request_path == "/pilot-household-ca.crt" and service.ca_certificate is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-x509-ca-cert")
                    self.send_header("Content-Disposition", 'attachment; filename="pilot-household-ca.crt"')
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Content-Length", str(len(service.ca_certificate)))
                    self.end_headers()
                    self.wfile.write(service.ca_certificate)
                elif request_path.rstrip("/") == base:
                    self._send(_companion_html(service.token, service.csrf_token, service.snapshot_provider()), "text/html; charset=utf-8")
                elif request_path == f"{base}/state":
                    self._json(service.snapshot_provider())
                elif request_path == f"{base}/manifest.webmanifest":
                    self._send(_manifest(service.token), "application/manifest+json")
                elif request_path == f"{base}/icon.svg":
                    self._send(_icon_svg(), "image/svg+xml")
                elif request_path == f"{base}/sw.js":
                    self._send(b"self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(clients.claim()));self.addEventListener('fetch',()=>{});", "application/javascript; charset=utf-8")
                else:
                    self._send(b"Not found", "text/plain; charset=utf-8", 404)

            def do_POST(self) -> None:  # noqa: N802
                if not service._allow_request(self.client_address[0]):
                    self._json({"error": "Private controller rate limit exceeded"}, 429)
                    return
                if self.path == "/connect":
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if length <= 0 or length > 1024:
                            raise ValueError("Invalid connection request")
                        form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
                        if not secrets.compare_digest(str(form.get("code", [""])[0]), service.pair_code):
                            raise ValueError("That AION code is not valid")
                        self.send_response(303)
                        self.send_header("Location", service.redirect_public_url or service.public_url)
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                    except ValueError as exc:
                        self._json({"error": str(exc)}, 400)
                    return
                base = f"/companion/{service.token}"
                try:
                    self._csrf()
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0:
                        raise ValueError("Empty private-controller request")
                    if self.path == f"{base}/perception":
                        if service.perception_handler is None or length > 5 * 1024 * 1024:
                            raise ValueError("Phone visual perception is unavailable or the image is too large")
                        result = service.perception_handler(
                            self.rfile.read(length),
                            self.headers.get("Content-Type", "application/octet-stream"),
                            self.headers.get("X-Pilot-Observer"),
                        )
                    elif self.path == f"{base}/voice":
                        if not service.tls_context or service.voice_handler is None or length > 3 * 1024 * 1024:
                            raise PermissionError("Private push-to-talk requires the trusted HTTPS controller")
                        result = service.voice_handler(
                            self.rfile.read(length),
                            self.headers.get("Content-Type", "application/octet-stream"),
                        )
                    elif self.path == f"{base}/provider-telemetry":
                        if not service.tls_context or service.provider_telemetry_handler is None:
                            raise PermissionError("Signed provider telemetry requires the trusted HTTPS controller")
                        if length > 64 * 1024 or self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                            raise ValueError("Provider telemetry must be bounded JSON")
                        try:
                            envelope = json.loads(self.rfile.read(length))
                        except json.JSONDecodeError as exc:
                            raise ValueError("Invalid provider telemetry JSON") from exc
                        if not isinstance(envelope, dict):
                            raise ValueError("Provider telemetry must be a JSON object")
                        result = service.provider_telemetry_handler(
                            envelope,
                            self.headers.get("X-Pilot-Telemetry-Signature", ""),
                        )
                    else:
                        if length > 8192:
                            raise ValueError("Private-controller request is too large")
                        form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
                        if self.path == f"{base}/private-text":
                            if service.private_text_handler is None:
                                raise ValueError("Private TV keyboard is unavailable")
                            purpose = str(form.get("purpose", [""])[0])
                            value = str(form.get("value", [""])[0])
                            if purpose not in {"username", "password", "game_search"}:
                                raise ValueError("Invalid private keyboard purpose")
                            if not value or len(value) > 320:
                                raise ValueError("Private keyboard text must contain 1 to 320 characters")
                            result = service.private_text_handler(value, purpose)
                            value = ""
                        elif self.path == f"{base}/decision":
                            approval_id = str(form.get("approval_id", [""])[0])
                            decision = str(form.get("decision", [""])[0])
                            if decision not in {"approve", "reject"}:
                                raise ValueError("Invalid approval decision")
                            result = service.decision_handler(approval_id, decision == "approve")
                        elif self.path == f"{base}/command":
                            if service.command_handler is None:
                                raise ValueError("TV controller is unavailable")
                            command = str(form.get("command", [""])[0])
                            try:
                                arguments = json.loads(str(form.get("arguments", ["{}"])[0]))
                            except json.JSONDecodeError as exc:
                                raise ValueError("Invalid controller arguments") from exc
                            if not isinstance(arguments, dict):
                                raise ValueError("Controller arguments must be an object")
                            result = service.command_handler(command, arguments)
                        else:
                            self._send(b"Not found", "text/plain; charset=utf-8", 404)
                            return
                    self._json(result)
                except PermissionError as exc:
                    self._json({"error": str(exc)}, 403)
                except (ValueError, KeyError) as exc:
                    self._json({"error": str(exc)}, 400)
                except Exception as exc:
                    self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        if self.tls_context:
            self._server.socket = self.tls_context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, name="aion-companion", daemon=True)
        self._thread.start()
        dns_sd = shutil.which("dns-sd")
        if dns_sd:
            self._bonjour_process = subprocess.Popen(
                [dns_sd, "-R", "AION Mother", "_aion-fabric._tcp", "local", str(self._server.server_port), "path=/", f"protocol={'aion-companion-tls-v1' if self.tls_context else 'aion-companion-v1'}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def stop(self) -> None:
        if self._bonjour_process:
            self._bonjour_process.terminate()
            self._bonjour_process = None
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=3)
