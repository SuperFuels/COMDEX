from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"
INDEX = ROOT / "desktop/mac/src/index.html"
CONTROLLER = ROOT / "desktop/mac/src/aion_business_foundation_voice_controller.js"


def read(path):
    return path.read_text(encoding="utf-8")


def test_o25c_controller_loads_before_app_js():
    text = read(INDEX)
    controller_tag = '<script src="./aion_business_foundation_voice_controller.js"></script>'
    app_tag = '<script src="./app.js"></script>'
    assert controller_tag in text
    assert app_tag in text
    assert text.index(controller_tag) < text.index(app_tag)


def test_o25c_app_bridges_voice_transcript_to_o25b_controller():
    text = read(APP)
    assert "AION O25C — Business Foundation Voice Discovery Bridge Lock" in text
    assert "window.applyAionO25BVoiceTurnToFoundationDraft" in text
    assert "window.__aionBusinessFoundationVoiceDiscoveryPacket" in text
    assert "window.__aionBusinessFoundationVoiceDraft" in text
    assert "__debugAionO25CBusinessFoundationVoiceDiscoveryBridge" in text


def test_o25c_old_loose_business_twin_binding_is_migrated():
    text = read(APP)
    bind_start = text.index("function bindAionO21FTranscriptToBusinessTwinAnswer")
    bind_end = text.index("function renderAionO21FBusinessTwinVoiceBindingPanel")
    block = text[bind_start:bind_end]
    assert "applyAionO25BVoiceTurnToFoundationDraft" in block
    assert "migrated_to_business_foundation_voice_controller" in block
    assert "o25b_foundation_voice_controller_not_loaded" in block
    assert "external_actions_allowed: false" in block
    assert "live_execution_allowed: false" in block


def test_o25c_removes_old_hard_coded_voice_field_guessing_from_active_functions():
    text = read(APP)

    classify_start = text.index("function classifyAionO21FVoiceAnswerField")
    classify_end = text.index("function normaliseAionO21FVoiceAnswerValue")
    classify_block = text[classify_start:classify_end]

    bind_start = text.index("function bindAionO21FTranscriptToBusinessTwinAnswer")
    bind_end = text.index("function renderAionO21FBusinessTwinVoiceBindingPanel")
    bind_block = text[bind_start:bind_end]

    forbidden = [
        "roof",
        "maintenance",
        "renovation",
        "homeowners",
        "landlords",
        "configured operating region",
        "my business is",
        "we offer",
        "we do",
    ]

    combined = (classify_block + bind_block).lower()
    for token in forbidden:
        assert token not in combined


def test_o25c_foundation_panel_is_business_foundation_not_old_twin_guessing():
    text = read(APP)
    start = text.index("function renderAionO21FBusinessTwinVoiceBindingPanel")
    end = text.index("function ensureAionO21FBusinessTwinVoiceBindingPanel")
    block = text[start:end]

    assert "Business Foundation voice discovery" in block
    assert "schema-driven" in block
    assert "data-aion-o25c-next-question" in block
    assert "Foundation readiness" in block
    assert "hard-code" not in block.lower()


def test_o25c_syntax_checks_clean():
    subprocess.run(["node", "--check", str(CONTROLLER)], cwd=ROOT, check=True)
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
