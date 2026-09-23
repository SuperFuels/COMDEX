from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19j_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19J VOICE STARTUP CONVERSATION STATE MACHINE LOCK" in text
    assert "__debugAionO19JVoiceStartupConversationStateMachine" in text
    assert "[AION] O19J voice startup conversation state machine installed" in text

def test_o19j_has_name_then_choice_flow():
    text = APP.read_text(encoding="utf-8")
    assert "startup_choice:" in text
    assert "Great to have you here" in text
    assert "Are we setting up a brand-new idea" in text
    assert "existing business you want Tessaris to help organise, grow, or automate" in text
    assert 'const effectiveStage = stage === "startup_intro" && state.user_name ? "startup_choice" : stage;' in text

def test_o19j_captures_name_and_responds_with_choice_prompt():
    text = APP.read_text(encoding="utf-8")
    assert 'const capturedName = replyStage === "startup_intro" ? maybeCaptureNameO19I(value) : "";' in text
    assert 'writeStateO19I({ user_name: capturedName, stage: "startup_choice" });' in text
    assert 'getScriptO19I("startup_choice", capturedName)' in text
    assert 'speakO19I(`${nextScript.title}. ${nextScript.body}`);' in text

def test_o19j_existing_business_advances_to_business_twin_intro():
    text = APP.read_text(encoding="utf-8")
    assert 'const entryStage = state.user_name ? "startup_choice" : "startup_intro";' in text
    assert 'if (mode === "small_business_growth") {' in text
    assert 'writeStateO19I({ stage: "business_twin_intro" });' in text
    assert 'getScriptO19I("business_twin_intro", state.user_name)' in text

def test_o19j_does_not_replace_existing_pages():
    text = APP.read_text(encoding="utf-8")
    assert "function renderBusinessEntryModeSelector()" in text
    assert "function renderBusinessContextSurface()" in text
    assert "Business Twin Setup" in text
    assert "Step 1 · Business Classifier" in text
    assert "Step 2 · Confirm Archetype" in text
    assert "Step 3 · Evidence and Connector Map" in text
