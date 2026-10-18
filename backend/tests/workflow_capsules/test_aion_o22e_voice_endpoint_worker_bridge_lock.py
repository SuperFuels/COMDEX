from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_o22e_api_has_gated_worker_bridge():
    text = read("backend/modules/aion_voice/api.py")
    assert "AION O22E WORKER BRIDGE" in text
    assert "AION_VOICE_WORKER_ENABLED" in text
    assert "_aion_voice_worker_enabled" in text
    assert "synthesize_with_worker" in text
    assert "transcribe_with_worker" in text
    assert "x-aion-voice-worker" in text
    assert "x-aion-voice-cloud" in text


def test_o22e_worker_bridge_is_not_default_forced():
    text = read("backend/modules/aion_voice/api.py")
    assert 'os.environ.get("AION_VOICE_WORKER_ENABLED"' in text
    assert '"true"' in text
    assert '"yes"' in text
    assert '"on"' in text
    assert "if _aion_voice_worker_enabled():" in text


def test_o22e_api_remains_business_agnostic():
    text = read("backend/modules/aion_voice/api.py")
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


def test_o22e_worker_bridge_returns_audio_and_json_paths():
    text = read("backend/modules/aion_voice/api.py")
    assert "Response(" in text
    assert "JSONResponse(" in text
    assert "audio_base64" in text
    assert "media_type" in text
    assert "audio/wav" in text


def test_o22e_routes_include_provider_tts_and_stt_paths():
    text = read("backend/modules/aion_voice/api.py")
    assert '@router.get("/providers")' in text
    assert '@router.post("/tts")' in text
    assert '@router.post("/stt")' in text
    assert '@router.post("/api/aion/voice/stt")' in text
