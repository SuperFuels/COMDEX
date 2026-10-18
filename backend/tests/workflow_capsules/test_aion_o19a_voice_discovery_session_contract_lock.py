from pathlib import Path

APP = Path("desktop/mac/src/app.js")
DOC = Path("docs/aion_build_tasks/aion_voice_discovery_onboarding_build_task.md")

def test_o19a_contract_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19A VOICE DISCOVERY SESSION CONTRACT LOCK" in text
    assert "AION_VOICE_DISCOVERY_SESSION_SCHEMA_VERSION" in text
    assert "createAionVoiceDiscoverySessionO19A" in text
    assert "appendAionVoiceDiscoveryTranscriptO19A" in text
    assert "confirmAionVoiceDiscoverySessionO19A" in text
    assert "__debugAionO19AVoiceDiscoverySessionContract" in text

def test_o19a_provider_abstraction_no_elevenlabs_dependency():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19A VOICE DISCOVERY SESSION CONTRACT LOCK", 1)[1]
    block = block.split("END AION O19A VOICE DISCOVERY SESSION CONTRACT LOCK", 1)[0]
    assert "provider_abstract" in block
    assert "text_only_dev_adapter" in block
    assert "requires_customer_key: false" in block
    assert "hard_coded_provider: false" in block
    assert "hard_coded_elevenlabs: false" in block.lower()
    assert "ElevenLabs or another TTS provider can be added later" in block

def test_o19a_session_contract_fields():
    text = APP.read_text(encoding="utf-8")
    for field in [
        "session_id",
        "business_id",
        "workspace_id",
        "current_stage",
        "transcript_chunks",
        "speaker_turns",
        "extracted_facts",
        "department_questions",
        "answered_questions",
        "unanswered_questions",
        "confidence_by_field",
        "business_twin_draft",
        "department_ledger_patch",
        "boardroom_readiness_patch",
        "discovery_backlog_patch",
        "confirmation_summary",
        "user_confirmed",
        "cost_controls",
        "consent",
    ]:
        assert field in text

def test_o19a_safety_and_no_raw_audio_default():
    text = APP.read_text(encoding="utf-8")
    assert "store_raw_audio: false" in text
    assert "allow_cloud_stt: false" in text
    assert "allow_cloud_tts: false" in text
    assert "no_live_external_actions: true" in text
    assert "no_bookings: true" in text
    assert "no_payments: true" in text
    assert "no_invoices: true" in text

def test_voice_build_doc_exists():
    assert DOC.exists()
    text = DOC.read_text(encoding="utf-8")
    assert "Voice Discovery Onboarding" in text
    assert "Do not hard-code ElevenLabs" in text
    assert "Provider Principle" in text
