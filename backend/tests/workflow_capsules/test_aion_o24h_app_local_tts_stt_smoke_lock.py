from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_app_local_tts_stt_smoke_o24h.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24h/app_local_tts_stt_smoke_manifest.json"


def test_o24h_script_exists_and_documents_full_app_local_voice_smoke():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24H" in text
    assert "prove_full_app_local_tts_stt_smoke" in text
    assert "APP_WORKER" in text
    assert "aion-o23i-bundle-probe" in text
    assert "KPipeline" in text
    assert "WhisperModel" in text
    assert "HF_HUB_OFFLINE" in text
    assert "AION_ELEVENLABS_ENABLED" in text
    assert "AION_BROWSER_SPEECH_FALLBACK_ENABLED" in text


def test_o24h_manifest_proves_tts_and_stt_from_app_local_runtime():
    assert MANIFEST.exists(), "Run scripts/aion_voice_app_local_tts_stt_smoke_o24h.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24H"
    assert data["ok"] is True
    assert data["release_ready"] is True
    assert data["release_blockers"] == []

    assert data["worker_probe_ok"] is True
    assert data["packaged_readiness"]["ok"] is True

    assert data["tts_ok"] is True
    assert data["tts_wav"]["exists"] is True
    assert data["tts_wav"]["is_file"] is True
    assert data["tts_wav"]["size_bytes"] > 1000

    assert data["stt_ok"] is True
    assert isinstance(data["stt_transcript"], str)
    assert data["stt_transcript"].strip()

    transcript = data["stt_transcript"].lower()
    assert "aion" in transcript or "runtime" in transcript or "smoke" in transcript


def test_o24h_uses_app_local_assets_and_offline_policy():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    runtime_probe = data["runtime_probe"]

    assert runtime_probe["tts"]["ok"] is True
    assert runtime_probe["tts"]["samplerate"] == 24000
    assert runtime_probe["tts"]["frames"] > 0

    assert runtime_probe["stt"]["ok"] is True

    assert runtime_probe["kokoro_model"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/kokoro/kokoro-v1_0.pth")
    assert runtime_probe["kokoro_config"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/kokoro/config.json")
    assert runtime_probe["kokoro_voice"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/kokoro/voices/af_heart.pt")
    assert runtime_probe["whisper_model"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/whisper/base")

    offline_env = runtime_probe["offline_env"]
    assert offline_env["HF_HUB_OFFLINE"] == "1"
    assert offline_env["TRANSFORMERS_OFFLINE"] == "1"
    assert offline_env["HF_DATASETS_OFFLINE"] == "1"
    assert offline_env["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
    assert offline_env["AION_ELEVENLABS_ENABLED"] == "false"
    assert offline_env["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"


def test_o24h_is_business_agnostic():
    text = SCRIPT.read_text(encoding="utf-8")

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
