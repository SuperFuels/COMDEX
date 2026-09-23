from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o19o_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19O RESET AND OPENING TRIGGER AUTHORITY LOCK" in text
    assert "O19O reset and opening trigger authority installed" in text
    assert "__debugAionO19OResetAndOpeningTriggerAuthority" in text


def test_o19o_clears_all_old_voice_state():
    text = APP.read_text(encoding="utf-8")
    assert "resetAionO19OFullVoiceOnboarding" in text
    assert "clearAllVoiceOnboardingState" in text
    assert "voiceOnboarding" in text
    assert "voiceDiscovery" in text
    assert 'user_name: ""' in text
    assert 'transcript: []' in text
    assert 'stage: "startup_intro"' in text


def test_o19o_aion_click_routes_to_o19n_opening_sequence():
    text = APP.read_text(encoding="utf-8")
    assert 'event.target?.closest?.("[data-aion-o19m-start]")' in text
    assert "stopImmediatePropagation" in text
    assert "startAionO19NOpeningSequence" in text
    assert "playAionO19NCurrentPrompt" in text
    assert 'authority: "o19o_to_o19n"' in text


def test_o19o_replaces_old_reset_and_start_aliases():
    text = APP.read_text(encoding="utf-8")
    assert "window.resetAionO19MOnboarding = clearAllVoiceOnboardingState" in text
    assert "window.startAionO19MOnboarding = startAuthoritativeOpening" in text
    assert "window.startAionO19LLiveMicOnboarding = startAuthoritativeOpening" in text
