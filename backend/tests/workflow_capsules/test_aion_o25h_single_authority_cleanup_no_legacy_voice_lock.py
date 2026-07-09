from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"
MAIN = ROOT / "backend/main.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block_after(text: str, marker: str) -> str:
    start = text.find(marker)
    assert start != -1, f"missing marker: {marker}"
    end = text.find("})();", start)
    assert end != -1, f"missing closure after marker: {marker}"
    return text[start : end + len("})();")]


def test_o25h_disables_legacy_elevenlabs_canonical_tts_route():
    text = read(MAIN)

    assert '@app.post("/api/aion/voice/tts/legacy-elevenlabs-disabled")' in text
    assert 'async def aion_o19k_elevenlabs_voice_tts' in text

    legacy_def_start = text.find("async def aion_o19k_elevenlabs_voice_tts")
    assert legacy_def_start != -1
    legacy_window = text[max(0, legacy_def_start - 250): legacy_def_start + 250]
    assert '@app.post("/api/aion/voice/tts")' not in legacy_window


def test_o25h_single_authority_cleanup_block_exists():
    text = read(APP)
    block = block_after(text, "AION O25H Single Authority Cleanup Lock")

    assert "single_authority_cleanup" in block
    assert "removeLegacyVoiceOnboardingNodes" in block
    assert "forceCanonicalTerminal" in block
    assert "clearStaleConversationOnColdStart" in block
    assert "patchTranscriptRowsForSpeakerAuthority" in block


def test_o25h_removes_legacy_visible_onboarding_terms_from_voice_route():
    text = read(APP)
    block = block_after(text, "AION O25H Single Authority Cleanup Lock")

    for token in [
        "AION does not guess your business",
        "Business Twin Setup",
        "Business Classifier",
        "Evidence and Connector Map",
        "Start Business Twin Setup",
        "Continue in Limited Context Mode",
        "Pending review",
        "Business Twin mutation",
    ]:
        assert token in block

    assert "data-aion-o25h-legacy-removed" in block
    assert "aion-o25h-foundation-voice-active" in block


def test_o25h_cloud_voice_warning_is_hidden_from_business_foundation_voice_route():
    text = read(APP)
    block = block_after(text, "AION O25H Single Authority Cleanup Lock")

    assert "visible_cloud_voice_warning" in block
    assert "ELEVENLABS VOICE UNAVAILABLE" in block
    assert "ElevenLabs voice unavailable" in block
    assert "canonical_terminal_present" in block


def test_o25h_aion_turns_render_as_aion_not_you():
    text = read(APP)
    block = block_after(text, "AION O25H Single Authority Cleanup Lock")

    assert "normaliseSpeakerForO25H" in block
    assert 'return "AION"' in block
    assert "appendAionO25HTranscriptWithSpeakerAuthority" in block
    assert 'nextMeta.speaker = "AION"' in block
    assert 'nextMeta.role = "assistant"' in block


def test_o25h_syntax_checks_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
    subprocess.run(["python", "-m", "py_compile", str(MAIN)], cwd=ROOT, check=True)
