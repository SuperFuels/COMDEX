# AION O21 — Local-First Voice Stack Lock

Lock ID: AION-O21-LOCAL-FIRST-VOICE-STACK

Status: LOCKED THROUGH O21A-O21G

## Executive Decision

ElevenLabs is no longer the default AION voice runtime.

AION voice is now local-first, provider-routed, transcript-first, non-blocking, approval-gated, and free from hidden paid voice usage.

## Locked Chain

- O21A — Local Voice Provider Router
- O21B — Kokoro Local TTS Provider
- O21C — Frontend Voice Provider Status
- O21D — faster-whisper STT Endpoint
- O21E — Live Mic Transcript Capture
- O21F — Business Twin Voice Answer Binding
- O21G — Voice Runtime Hardening + Smoke Helpers
- O21H — Final Local Voice Stack Lock

## Runtime Defaults

AION_TTS_PROVIDER=kokoro
AION_STT_PROVIDER=faster_whisper
AION_ALLOW_ELEVENLABS=false
AION_ALLOW_BROWSER_SPEECH=false
AION_LOCAL_VOICE_ENABLED=true
AION_KOKORO_VOICE=af_heart
AION_KOKORO_SAMPLE_RATE=24000
AION_WHISPER_MODEL=base
AION_WHISPER_DEVICE=auto
AION_WHISPER_COMPUTE_TYPE=int8

## Backend Routes

GET /api/aion/voice/providers
POST /api/aion/voice/tts
POST /api/aion/voice/stt

## Critical Rules

ElevenLabs must not be called by default.
Browser speech must not start silently.
Kokoro is the default local TTS provider.
faster-whisper is the default local STT provider.
Voice failure must not block transcript, typing, or Business Twin onboarding.
Voice answers require human approval.
Voice must not execute, book, pay, send, publish, or mutate external systems.
small_business_foundation remains the startup route authority.
business_context must not be hijacked.
No extra startup overlay should be created.

## Files Added

backend/modules/aion_voice/
backend/modules/aion_voice/api.py
backend/modules/aion_voice/voice_router.py
backend/modules/aion_voice/schemas.py
backend/modules/aion_voice/providers/kokoro_tts.py
backend/modules/aion_voice/providers/elevenlabs_tts.py
backend/modules/aion_voice/providers/browser_fallback.py
backend/modules/aion_voice/providers/faster_whisper_stt.py
backend/requirements-voice-local.txt
scripts/aion_voice_smoke_test.py

## Frontend Debug Helpers

__debugAionVoiceProviders()
__debugAionO21ELiveMicTranscript()
__debugAionO21FBusinessTwinVoiceAnswers()
mountAionO21ELiveMicTranscriptPanel()
startAionO21ELiveMicTranscriptCapture()
stopAionO21ELiveMicTranscriptCapture()
mountAionO21FBusinessTwinVoiceBinding()
bindAionO21FTranscriptToBusinessTwinAnswer(...)

## Browser Console Checks

__debugAionVoiceProviders()
mountAionO21ELiveMicTranscriptPanel()
__debugAionO21ELiveMicTranscript()
mountAionO21FBusinessTwinVoiceBinding()
bindAionO21FTranscriptToBusinessTwinAnswer(runtimeTranscriptText)
__debugAionO21FBusinessTwinVoiceAnswers()

## Optional Runtime Install

python -m pip install -r backend/requirements-voice-local.txt

## Optional Smoke Test

PYTHONPATH=. .venv/bin/python scripts/aion_voice_smoke_test.py --base-url http://127.0.0.1:8080

## Next Phase

O22A — install local voice dependencies
O22B — verify Kokoro audio generation
O22C — verify faster-whisper transcription
O22D — test app microphone permission and transcript append
O22E — test Business Twin voice answer review panel
O22F — package/install Tessaris.app with local voice stack

Lock Footer:
Lock ID: AION-O21-LOCAL-FIRST-VOICE-STACK
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson
