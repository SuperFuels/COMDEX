from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/voice/aion_voice_packaging_lock_o23_latex_section.tex"


def test_o23k_latex_section_exists_and_documents_o23_voice_packaging():
    assert DOC.exists()

    text = DOC.read_text(encoding="utf-8")

    assert "\\section{O23 Voice Packaging Runtime Lock}" in text
    assert "O23A" in text
    assert "O23J" in text
    assert "110 passed" in text
    assert "e93420e6 lock(voice): finalize packaging contract" in text
    assert "Tessaris.app/Contents/Resources/voice" in text
    assert "Tessaris.app/Contents/Resources/voice/python/bin/python" in text
    assert "desktop/mac/voice_bundle_staging/voice" in text
    assert ".venv_voice/bin/python" in text


def test_o23k_latex_section_documents_runtime_assets_and_imports():
    text = DOC.read_text(encoding="utf-8")

    for token in [
        "kokoro",
        "soundfile",
        "faster_whisper",
        "ctranslate2",
        "av",
        "torch",
        "spacy",
        "numpy",
        "voice/kokoro/kokoro-v1_0.pth",
        "voice/kokoro/config.json",
        "voice/kokoro/voices/af_heart.pt",
        "voice/spacy/en_core_web_sm",
        "voice/whisper/base",
    ]:
        assert token in text


def test_o23k_latex_section_documents_no_hidden_downloads_policy():
    text = DOC.read_text(encoding="utf-8")

    for token in [
        "HF_HUB_OFFLINE=1",
        "TRANSFORMERS_OFFLINE=1",
        "HF_DATASETS_OFFLINE=1",
        "HF_HUB_DISABLE_TELEMETRY=1",
        "AION_VOICE_NO_HIDDEN_DOWNLOADS=true",
        "AION_ELEVENLABS_ENABLED=false",
        "AION_BROWSER_SPEECH_FALLBACK_ENABLED=false",
    ]:
        assert token in text


def test_o23k_latex_section_is_business_agnostic():
    text = DOC.read_text(encoding="utf-8")

    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
        "construct" + "ion",
        "roof" + " repair",
    ]

    for token in forbidden:
        assert token not in text
