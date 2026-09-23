from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"
INDEX = ROOT / "desktop/mac/src/index.html"


def text(path):
    return path.read_text(encoding="utf-8")


def test_o25d_index_loads_foundation_controller_before_app():
    html = text(INDEX)
    assert "./aion_business_foundation_voice_controller.js" in html
    assert html.index("./aion_business_foundation_voice_controller.js") < html.index("./app.js")


def test_o25d_conversation_copy_is_foundation_not_elevenlabs_placeholder():
    app = text(APP)
    assert "Business Foundation Conversation" in app
    assert "Business Twin Conversation" not in app
    assert "AION is speaking through ElevenLabs. Your answers are captured into the transcript" not in app
    assert "Business Foundation canvas, Business Map, and Boardroom readiness profile" in app


def test_o25d_terminal_has_real_mount_targets_for_existing_voice_panels():
    app = text(APP)
    assert 'data-aion-o20c-conversation-terminal="true"' in app
    assert 'data-aion-startup-conversation-terminal="true"' in app
    assert 'data-aion-business-foundation-terminal="true"' in app
    assert 'data-aion-o25d-foundation-terminal="true"' in app
    assert "renderAionO21ELiveMicTranscriptPanel" in app
    assert "renderAionO21FBusinessTwinVoiceBindingPanel" in app
    assert "renderAionVoiceProviderStatusPanelO21C" in app


def test_o25d_panel_has_starter_questions_next_question_and_readiness():
    app = text(APP)
    start = app.index("AION O25D — Startup Conversation Foundation UX Lock")
    block = app[start:]
    assert "I have a business" in block
    assert "I have an idea" in block
    assert "Generate an idea" in block
    assert "data-aion-o25d-next-question" in block
    assert "Foundation readiness" in block
    assert "schema-driven Business Foundation discovery" in block
    assert "Marketing, Sales, Finance" in block
    assert "department pilots" in block


def test_o25d_typed_ux_test_routes_into_transcript_and_o25b_controller():
    app = text(APP)
    start = app.index("AION O25D — Startup Conversation Foundation UX Lock")
    block = app[start:]
    assert "data-aion-o25d-typed-answer" in block
    assert "data-aion-o25d-submit-typed-answer" in block
    assert "appendAionO21ETranscript" in block
    assert "applyAionO25BVoiceTurnToFoundationDraft" in block
    assert "typed_ux_test" in block


def test_o25d_keeps_preview_safe_and_no_hard_coded_answers():
    app = text(APP)
    start = app.index("AION O25D — Startup Conversation Foundation UX Lock")
    block = app[start:]
    assert "external_actions_allowed: false" in block
    assert "live_execution_allowed: false" in block
    assert "preview_only: true" in block
    assert "no_hard_coded_business_answers" in block
    forbidden = [
        "Home Fixed",
        "home_fixed",
        "costa-conexion",
        "CostaConexion",
        "roof",
        "plumber",
        "electrician",
    ]
    for token in forbidden:
        assert token not in block


def test_o25d_syntax_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
