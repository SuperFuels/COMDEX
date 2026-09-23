from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / "frontend" / "pages" / "pilot" / "mobile.tsx"
STYLES = ROOT / "frontend" / "styles" / "PilotMobile.module.css"
MANIFEST = ROOT / "frontend" / "public" / "pilot-mobile.webmanifest"
WORKER = ROOT / "frontend" / "public" / "pilot-mobile-sw.js"
FIXTURE = ROOT / "docs" / "aion" / "fixtures" / "pilot_unified_mobile_v1.json"
PAIRING = ROOT / "frontend" / "lib" / "pilot" / "pairing.ts"


def test_reference_surface_reads_the_canonical_fixture() -> None:
    source = PAGE.read_text(encoding="utf-8")
    assert "pilot_unified_mobile_v1.json" in source
    assert "surface_manifests" in source
    assert "Demo Owner" not in source


def test_all_three_product_modes_are_fixture_defined() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    modes = {item["mode"] for item in fixture["surface_manifests"]}
    assert modes == {"personal", "workspace", "boardroom"}


def test_mobile_routes_do_not_expose_deferred_economic_features() -> None:
    combined = "\n".join(
        [PAGE.read_text(encoding="utf-8"), json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8")))]
    ).lower()
    for prohibited in ("photonpay", "staking", "mint token", "buy pho", "wallet balance"):
        assert prohibited not in combined


def test_installable_shell_assets_are_scoped_to_pilot() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    worker = WORKER.read_text(encoding="utf-8")
    assert manifest["start_url"] == "/pilot/mobile"
    assert manifest["display"] == "standalone"
    assert manifest["icons"][0]["src"] == "/pilot-mobile-icon.svg"
    assert '"/pilot/mobile"' in worker
    assert "pilot-mobile-shell-v1" in worker


def test_mobile_surface_includes_accessibility_and_responsive_guards() -> None:
    page = PAGE.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")
    assert 'aria-label="Pilot unified mobile app"' in page
    assert 'aria-label="Primary navigation"' in page
    assert "prefers-reduced-motion" in styles
    assert "env(safe-area-inset-bottom)" in styles
    assert ".iconButton, .avatar" in styles and "width: 44px; height: 44px" in styles
    assert ".composer input" in styles and "height: 44px" in styles
    assert ".composer button" in styles and "width: 44px; height: 44px" in styles
    assert ".modeSwitcher button" in styles and "min-height: 44px" in styles
    assert ".sectionTitle button" in styles and "min-height: 44px" in styles


def test_mobile_surface_uses_one_grouped_context_at_a_time() -> None:
    page = PAGE.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")
    assert 'aria-label={`${modeCopy[mode].label} grouped tools`}' in page
    assert '<optgroup key={group} label={group}>' in page
    assert 'activeNav === "Pilot" && mode === "personal" && selectedShortcut === "TV"' in page
    assert 'activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Memory"' in page
    assert 'activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Guardian"' in page
    assert 'if (label !== "Pilot") setSelectedShortcut(null)' in page
    assert '((activeNav === "Pilot" && !selectedShortcut) || activeNav === "Actions")' in page
    assert ".contextPicker" in styles


def test_mobile_grouped_tools_keep_daily_tv_and_device_controls_close() -> None:
    page = PAGE.read_text(encoding="utf-8")
    assert '["TV", "Tasks", "Calendar", "Devices"].includes(shortcut)' in page
    assert 'onClick={() => openShortcut(shortcut)}' in page
    assert 'onClick={() => openShortcut(null)}>Close tool' in page


def test_boardroom_commercial_controls_use_signed_workspace_authority() -> None:
    page = PAGE.read_text(encoding="utf-8")
    pairing = PAIRING.read_text(encoding="utf-8")
    assert 'aria-label="Departments, usage and value"' in page
    assert "Start 30-day trial" in page
    assert "Set monthly capacity" in page
    assert "Allow overage" in page
    assert "No automatic renewal" in page
    assert "readWorkspaceCommercialDashboard" in page
    assert "controlWorkspaceCommercialService" in page
    assert "/v1/workspaces/commercial/snapshot" in pairing
    assert "/v1/workspaces/commercial/action" in pairing
    assert '"workspace.commercial.read", "workspace.commercial.control"' in pairing


def test_mobile_requests_prefer_lan_then_verify_a_signed_direct_remote_route() -> None:
    source = PAIRING.read_text(encoding="utf-8")
    assert "pilot.direct-remote-route.v1" in source
    assert "verifiedDirectRemoteEndpoints" in source
    assert "verifyRemoteMother" in source
    assert "postConnectedJson" in source
    assert 'const result = await postJson(connection.endpoint, path, body, signal)' in source
    assert 'descriptor.mother_id !== connection.certificate.mother_id' in source
    assert 'route.relay_used !== false || route.contains_mother_secret !== false' in source
    assert source.count("postJson(connection.endpoint") == 2
    assert 'postJson(connection.endpoint, "/v1/personal/tv/presence"' in source
    assert "Presence deliberately uses only the mother's paired LAN endpoint" in source
    assert "public route can carry commands, but it cannot prove that the phone is home" in source


def test_mobile_uses_operator_unreadable_relay_only_after_direct_network_failure() -> None:
    source = PAIRING.read_text(encoding="utf-8")
    assert "pilot.opaque-relay-route.v1" in source
    assert "verifiedOpaqueRelayRoute" in source
    assert "postViaOpaqueRelay" in source
    assert 'operator_can_read_content !== false' in source
    assert 'x25519_hkdf_sha256_aes_256_gcm' in source
    assert 'crypto.subtle.generateKey("X25519"' in source
    assert 'direction: "request" | "response"' in source
    assert 'const result = await postViaOpaqueRelay(connection, path, body, signal)' in source
    assert source.index("for (const endpoint of candidates)") < source.index("postViaOpaqueRelay(connection, path, body, signal)")


def test_mobile_roaming_is_cursor_safe_bounded_and_network_aware() -> None:
    source = PAIRING.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    assert "pilot-inbox-cursor:" in source
    assert "revision < afterRevision || (revision === afterRevision && streamDelivered)" in source
    assert "Math.max(afterRevision, Number(saved.revision || 0))" in source
    assert 'window.addEventListener("online", networkChanged)' in source
    assert 'window.addEventListener("offline", networkChanged)' in source
    assert 'document.addEventListener("visibilitychange", becameVisible)' in source
    assert "pollInFlight" in source
    assert "const controller = new AbortController()" in source
    assert "activePoll?.abort()" in source
    assert "Math.min(pollRetry * 2, 30_000)" in source
    assert "Math.min(socketRetry * 2, 30_000)" in source
    assert "socketGeneration" in source
    assert 'socket.send("ping")' in source
    assert 'onRoute?: (route: "lan" | "direct" | "relay") => void' in source
    assert "initialRevision: initialInboxRevision" in page
    assert "`${liveRoute} · live`" in page
    assert '"offline" | "closed"' in page


def test_mobile_surface_explains_private_mother_connection_without_false_claims() -> None:
    page = PAGE.read_text(encoding="utf-8")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert 'aria-label="Phone and Pilot connection"' in page
    assert "six digits" in page
    assert "Check the words match" in page
    assert "beginPilotPairing" in page
    assert "completePilotPairing" in page
    assert "readPilotInbox" in page
    assert "watchPilotInbox" in page
    assert "actOnPilotTask" in page
    assert "searchPilotInbox" in page
    assert "downloadPilotAttachment" in page
    assert "controlPilotPttFloor" in page
    assert "sendPilotVoiceNote" in page
    assert "sendPilotStructuredCard" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalPilot" in page
    assert "createPersonalReminder" in page
    assert "updatePersonalReminder" in page
    assert "Schedule reminder" in page
    assert "readPersonalCalendar" in page
    assert "preparePersonalCalendarChange" in page
    assert "decidePersonalCalendarChange" in page
    assert "executePersonalCalendarChange" in page
    assert "Check privately" in page
    assert "Approve exact change" in page
    assert "/v1/personal/calendar/execute" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalContacts" in page
    assert "savePersonalContact" in page
    assert "removePersonalContact" in page
    assert "resolvePersonalContact" in page
    assert "Choose from phone when supported" in page
    assert "/v1/personal/contacts/resolve" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalCommunication" in page
    assert "preparePersonalCommunication" in page
    assert "decidePersonalCommunication" in page
    assert "executePersonalCommunication" in page
    assert "Prepare exact draft" in page
    assert "Approve exact message" in page
    assert "Send approved message" in page
    assert "Verified delivery receipts" in page
    assert "/v1/personal/communication/execute" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalServices" in page
    assert "preparePersonalServiceAction" in page
    assert "decidePersonalServiceAction" in page
    assert "executePersonalServiceAction" in page
    assert "Prepare exact proposal" in page
    assert "Approve exact proposal" in page
    assert "Verified service receipts" in page
    assert "/v1/personal/services/execute" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalLibrary" in page
    assert "claimPersonalLibraryItem" in page
    assert "continuePersonalLibraryItem" in page
    assert "deletePersonalLibraryItem" in page
    assert "Files &amp; saved items" in page
    assert "Research never inherits permission" in page
    assert "Open verified file" in page
    assert "/v1/personal/library/continue" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalDeviceMesh" in page
    assert "discoverPersonalDevices" in page
    assert "changePersonalTVSession" in page
    assert "controlPersonalTV" in page
    assert "controlPersonalIotPreset" in page
    assert "Devices &amp; IoT" in page
    assert "Discovery observes advertisements only" in page
    assert "Take control" in page
    assert "Refresh TV state" in page
    assert "Infrared proves transport delivery only" in page
    assert "/v1/personal/devices/discover" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/tv/session" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/tv/control" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/tv/presence" in PAIRING.read_text(encoding="utf-8")
    assert "confirmPersonalTVPresence" in page
    assert "nearby trusted-phone signal" in page
    assert "/v1/personal/devices/iot-control" in PAIRING.read_text(encoding="utf-8")
    assert "readPersonalExperiences" in page
    assert "controlPersonalExperience" in page
    assert "Start a 50-question session" in page
    assert "Open GeForce NOW on TV" in page
    assert "Prepare continue watching" in page
    assert "Provider open: " in page
    assert "/v1/personal/experiences/snapshot" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/experiences/control" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/memory/snapshot" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/personal/memory/export" in PAIRING.read_text(encoding="utf-8")
    assert "Permanently delete this memory" in PAGE.read_text(encoding="utf-8")
    assert "/v1/personal/guardian/action" in PAIRING.read_text(encoding="utf-8")
    assert "CONFIRM AND ALERT TRUSTED CONTACTS" in PAGE.read_text(encoding="utf-8")
    assert "Emergency-service dispatch" in PAGE.read_text(encoding="utf-8")
    assert "/v1/personal/intelligence/ask" in PAIRING.read_text(encoding="utf-8")
    assert "local capability first" in PAGE.read_text(encoding="utf-8")
    assert "askPersonalIntelligence" in PAGE.read_text(encoding="utf-8")
    assert "/v1/personal/snapshot" in PAIRING.read_text(encoding="utf-8")
    assert "Your Personal Pilot" in page
    assert "structuredCard" in page
    assert "Hold to reply" in page
    assert "Search messages, tasks and files" in page
    assert "/v1/inbox/stream" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/inbox/live" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/inbox/search" in PAIRING.read_text(encoding="utf-8")
    assert "/v1/inbox/attachments/read" in PAIRING.read_text(encoding="utf-8")
    assert fixture["connection"]["route"] == "direct_at_home"


def test_browser_phone_key_is_non_extractable_after_creation() -> None:
    source = PAIRING.read_text(encoding="utf-8")
    assert "indexedDB.open" in source
    assert 'generateKey({ name: "Ed25519" }' in source
    assert 'importKey("pkcs8", exportedPrivate, { name: "Ed25519" }, false, ["sign"])' in source
    assert "exportedPrivate.fill(0)" in source
    assert "verifyMotherDescriptor" in source
    assert 'endpoint.protocol !== "https:"' in source
