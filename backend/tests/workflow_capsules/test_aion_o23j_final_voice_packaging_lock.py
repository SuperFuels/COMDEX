from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_final_packaging_lock.py"
DOC = ROOT / "docs/voice/aion_voice_packaging_lock_o23j.md"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23j/final_packaging_lock_manifest.json"


def test_o23j_final_packaging_script_locks_release_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O23J" in text
    assert "final_voice_packaging_contract_lock_and_docs" in text
    assert "Tessaris.app/Contents/Resources/voice" in text
    assert "Tessaris.app/Contents/Resources/voice/python/bin/python" in text
    assert "must_embed_python_3_12" in text
    assert "must_not_fallback_to_dev_venv_in_customer_release" in text
    assert "must_not_use_elevenlabs_fallback" in text
    assert "must_not_use_browser_speechrecognition_fallback" in text


def test_o23j_manifest_exists_and_links_o23e_to_o23i_chain():
    assert MANIFEST.exists(), "Run scripts/aion_voice_final_packaging_lock.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O23J"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["staging_readiness_ok"] is True
    assert data["packaged_missing_runtime_is_clear"] is True
    assert data["final_packaged_python"] == "Tessaris.app/Contents/Resources/voice/python/bin/python"

    chain = data["proof_chain"]
    assert chain["o23e_python_strategy"]["ok"] is True
    assert chain["o23f_resolver"]["ok"] is True
    assert chain["o23g_startup_readiness"]["ok"] is True
    assert chain["o23h_no_hidden_downloads"]["ok"] is True
    assert chain["o23i_staged_worker_paths"]["ok"] is True

    gates = data["release_gates"]
    assert gates["must_embed_python_3_12"] is True
    assert gates["must_include_kokoro_runtime"] is True
    assert gates["must_include_whisper_model"] is True
    assert gates["must_not_fallback_to_dev_venv_in_customer_release"] is True


def test_o23j_manifest_locks_required_staging_assets_and_download_policy():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for item in data["required_staging_assets"].values():
        assert item["exists"] is True

    policy = data["download_policy"]
    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o23j_docs_exist_and_explain_release_gate():
    assert DOC.exists()

    text = DOC.read_text(encoding="utf-8")

    assert "AION Voice Packaging Lock O23J" in text
    assert "Tessaris.app/Contents/Resources/voice" in text
    assert "Tessaris.app/Contents/Resources/voice/python/bin/python" in text
    assert "HF_HUB_OFFLINE=1" in text
    assert "TRANSFORMERS_OFFLINE=1" in text
    assert "AION_VOICE_NO_HIDDEN_DOWNLOADS=true" in text
    assert ".venv_voice/bin/python" in text
    assert "must not silently fall back" in text


def test_o23j_is_business_agnostic():
    text = SCRIPT.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")

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
