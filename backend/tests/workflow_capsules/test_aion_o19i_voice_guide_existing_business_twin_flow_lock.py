from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19i_installed_without_replacing_existing_flow():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK" in text
    assert "O19I voice guide on existing Business Twin flow installed" in text
    assert "function renderBusinessEntryModeSelector()" in text
    assert "function renderBusinessContextSurface()" in text
    assert "Business Twin Setup" in text
    assert "Step 1 · Business Classifier" in text
    assert "Step 2 · Confirm Archetype" in text
    assert "Step 3 · Evidence and Connector Map" in text

def test_o19i_uses_existing_selectors_only():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[1]
    block = block.split("END AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[0]
    assert "[data-aion-phase24a-business-entry-selector]" in block
    assert "[data-aion-business-twin-setup-root='true']" in block
    assert "[data-aion-business-entry-mode]" in block
    assert "[data-aion-business-twin-step]" in block
    assert "[data-aion-business-twin-field]" in block

def test_o19i_voice_script_has_premium_opener():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[1]
    block = block.split("END AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[0]
    assert "Welcome to Tessaris" in block
    assert "digital headquarters" in block
    assert "AI Boardroom" in block
    assert "Business Twin" in block
    assert "what should I call you" in block

def test_o19i_integrates_existing_o19a_session_contract():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[1]
    block = block.split("END AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK", 1)[0]
    assert "createAionVoiceDiscoverySessionO19A" in block
    assert "appendAionVoiceDiscoveryTranscriptO19A" in block
    assert "aion.voiceOnboarding.o19i.v1" in block
    assert "__debugAionO19IVoiceGuideExistingBusinessTwinFlow" in block

def test_o19f_o19g_route_markers_still_present():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19F RESTORE REAL BUSINESS ENTRY SELECTOR LOCK" in text
    assert "BEGIN AION O19G STARTUP ROUTE ALIAS BLOCKER LOCK" in text
    assert "O19F: small_business_foundation is restored as the real startup selector route" in text
    assert "O19F: old redirect disabled. small_business_foundation renders the real startup selector again." in text
