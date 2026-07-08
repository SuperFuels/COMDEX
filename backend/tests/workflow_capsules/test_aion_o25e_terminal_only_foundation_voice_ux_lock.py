from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app():
    return APP.read_text(encoding="utf-8")


def o25e_block():
    text = read_app()
    start = text.index("AION O25E — Terminal-only Foundation Voice UX Lock")
    end = text.index("console.log(\"[AION] O25E terminal-only Foundation voice UX installed\")", start)
    return text[start:end]


def test_o25e_terminal_only_voice_ux_installed():
    block = o25e_block()
    assert "renderAionO25ETerminalOnlyVoiceConversation" in block
    assert "syncAionO25ETerminalOnlyVoiceConversation" in block
    assert "data-aion-o25e-voice-terminal-only" in block
    assert "data-aion-o25e-transcript-log" in block


def test_o25e_has_simple_voice_controls_not_debug_surface():
    block = o25e_block()
    assert "Reply to AION" in block
    assert "Stop talking" in block
    assert "data-aion-o25e-voice-bar" in block
    assert "data-aion-o25e-speaking-orb" in block
    assert "data-aion-o25e-typed-form" in block
    assert "Foundation readiness" not in block
    assert "Pending review" not in block
    assert "schema-driven" not in block


def test_o25e_transcript_bridges_to_existing_stt_and_foundation_controller():
    block = o25e_block()
    assert "appendAionO21ETranscript" in block
    assert "toggleAionO21ELiveMicTranscriptCapture" in block
    assert "stopAionO21ELiveMicTranscriptCapture" in block
    assert "__debugAionO25CBusinessFoundationVoiceDiscoveryBridge" in block


def test_o25e_hides_old_debug_panels_inside_terminal():
    block = o25e_block()
    assert "[data-aion-o21c-voice-provider-status]" in block
    assert "[data-aion-o21e-live-mic-panel]" in block
    assert "[data-aion-o21f-business-twin-voice-binding]" in block
    assert "display: none !important" in block


def test_o25e_removes_visible_elevenlabs_language_from_new_terminal():
    block = o25e_block()
    assert "ElevenLabs" not in block
    assert "Local voice runtime" in block
    assert "preview only" in block


def test_o25e_debug_probe_available_for_manual_ux_testing():
    block = o25e_block()
    assert "__debugAionO25ETerminalOnlyFoundationVoiceUX" in block
    assert "visible_text_contains_paid_cloud_voice_branding" in block
    assert "terminal_present" in block
    assert "talk_control_present" in block


def test_o25e_syntax_check_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
