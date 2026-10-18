# AION Voice Packaging Lock O23J

Status: locked for staging and release packaging contract
Phase: O23J
Maintainer: Tessaris AI
Business context: generic / business-agnostic

## Purpose

This document locks the final local-first AION voice packaging contract for the Mac desktop app.

The current repo proves the staging voice bundle path, local worker launch path, startup readiness checks, and no-hidden-download policy. It does not claim that the final embedded Tessaris.app Python runtime has already been built.

## Final packaged app contract

The final app must include the voice runtime at:

    Tessaris.app/Contents/Resources/voice/

The final packaged Python executable must exist at:

    Tessaris.app/Contents/Resources/voice/python/bin/python

The final packaged Python runtime must be Python 3.12 and must include the local voice dependencies required by the worker:

    kokoro
    soundfile
    faster_whisper
    ctranslate2
    av
    torch
    spacy
    numpy

The final packaged voice bundle must include:

    voice/kokoro/kokoro-v1_0.pth
    voice/kokoro/config.json
    voice/kokoro/voices/af_heart.pt
    voice/spacy/en_core_web_sm
    voice/whisper/base
    voice/manifest.json

## Staging proof

The staging bundle root is:

    desktop/mac/voice_bundle_staging/voice

The staging Python launcher is:

    desktop/mac/voice_bundle_staging/voice/python/bin/python

O23I proves the worker can be launched through the staged Python path and receives the staged Kokoro, spaCy and Whisper paths through environment variables.

## No hidden download policy

Packaged and staging voice modes must not perform hidden model/runtime downloads.

The runtime must set or preserve:

    HF_HUB_OFFLINE=1
    TRANSFORMERS_OFFLINE=1
    HF_DATASETS_OFFLINE=1
    HF_HUB_DISABLE_TELEMETRY=1
    AION_VOICE_NO_HIDDEN_DOWNLOADS=true
    AION_ELEVENLABS_ENABLED=false
    AION_BROWSER_SPEECH_FALLBACK_ENABLED=false

## Release gate

A release build must fail readiness until the real packaged runtime exists at:

    Tessaris.app/Contents/Resources/voice/python/bin/python

The system must not silently fall back to:

    .venv_voice/bin/python

for a customer packaged release.

## Current proof chain

O23E Python runtime strategy manifest:

    desktop/mac/voice_bundle_staging/voice/python_runtime_manifest.o23e.json

O23F app-local packaged resolver manifest:

    .runtime/voice_runtime_tests/o23f/packaged_resolver_manifest.json

O23G startup readiness manifest:

    .runtime/voice_runtime_tests/o23g/startup_readiness_manifest.json

O23H no-hidden-downloads manifest:

    .runtime/voice_runtime_tests/o23h/no_hidden_downloads_manifest.json

O23I staged worker paths manifest:

    .runtime/voice_runtime_tests/o23i/staged_worker_paths_manifest.json

## Current lock result

Staging readiness: True
Packaged readiness: False
Packaged missing runtime clearly reported: True
Final app runtime already present: False

This is the expected O23J state before building the actual release app bundle.
