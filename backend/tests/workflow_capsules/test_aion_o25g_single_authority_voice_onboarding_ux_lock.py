from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25g_single_authority_block_exists():
    text = read_app()
    assert "AION O25G — Single Authority Voice Onboarding UX Lock" in text
    assert "openAionO25GBusinessFoundationVoiceConversation" in text
    assert "resetAionO25GVoiceOnboardingToStart" in text
    assert "__debugAionO25GSingleAuthorityVoiceOnboardingUX" in text


def test_o25g_removes_legacy_business_twin_setup_surfaces():
    text = read_app()
    start = text.index("AION O25G — Single Authority Voice Onboarding UX Lock")
    block = text[start:]
    assert "removeLegacyBusinessTwinSetupSurfaces" in block
    assert "AION does not guess your business" in block
    assert "Start Business Twin Setup" in block
    assert "Step 1" in block
    assert "Step 3" in block
    assert "MutationObserver" in block


def test_o25g_have_business_opens_voice_terminal_only():
    text = read_app()
    start = text.index("AION O25G — Single Authority Voice Onboarding UX Lock")
    block = text[start:]
    assert "isHaveBusinessTrigger" in block
    assert "I have a business" in block
    assert "openBusinessFoundationVoiceConversation(\"existing_business\")" in block
    assert "aion.o20c.conversationOpen" in block
    assert "beginAionO25FAutomaticConversation" in block


def test_o25g_aion_speaker_authority():
    text = read_app()
    start = text.index("AION O25G — Single Authority Voice Onboarding UX Lock")
    block = text[start:]
    assert "appendAionO25GTranscriptSpeakerAuthority" in block
    assert 'last.speaker = "AION"' in block
    assert 'last.role = "aion"' in block
    assert "local_stt_transcript" in block


def test_o25g_uses_absolute_local_stt_endpoint():
    text = read_app()
    start = text.index("AION O25G — Single Authority Voice Onboarding UX Lock")
    block = text[start:]
    assert 'http://127.0.0.1:8080/api/aion/voice/stt' in block
    assert 'fetch(LOCAL_STT_ENDPOINT' in block
    assert '"/api/aion/voice/stt"' not in block


def test_o25g_syntax_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
