from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23j"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "final_packaging_lock_manifest.json"

VOICE_STAGING_ROOT = ROOT / "desktop/mac/voice_bundle_staging/voice"
VOICE_STAGING_MANIFEST = VOICE_STAGING_ROOT / "manifest.json"
O23E_PYTHON_STRATEGY = VOICE_STAGING_ROOT / "python_runtime_manifest.o23e.json"
O23F_RESOLVER_MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23f/packaged_resolver_manifest.json"
O23G_READINESS_MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23g/startup_readiness_manifest.json"
O23H_DOWNLOADS_MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23h/no_hidden_downloads_manifest.json"
O23I_WORKER_PATHS_MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23i/staged_worker_paths_manifest.json"

DOC_PATH = ROOT / "docs/voice/aion_voice_packaging_lock_o23j.md"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "path": str(path.relative_to(ROOT))}
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def required_file(path: Path) -> dict:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def write_docs(manifest: dict) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

    text = f"""# AION Voice Packaging Lock O23J

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

    {manifest["proof_chain"]["o23e_python_strategy"]["path"]}

O23F app-local packaged resolver manifest:

    {manifest["proof_chain"]["o23f_resolver"]["path"]}

O23G startup readiness manifest:

    {manifest["proof_chain"]["o23g_startup_readiness"]["path"]}

O23H no-hidden-downloads manifest:

    {manifest["proof_chain"]["o23h_no_hidden_downloads"]["path"]}

O23I staged worker paths manifest:

    {manifest["proof_chain"]["o23i_staged_worker_paths"]["path"]}

## Current lock result

Staging readiness: {manifest["staging_readiness_ok"]}
Packaged readiness: {manifest["packaged_readiness_ok"]}
Packaged missing runtime clearly reported: {manifest["packaged_missing_runtime_is_clear"]}
Final app runtime already present: {manifest["final_app_runtime_present"]}

This is the expected O23J state before building the actual release app bundle.
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    staging_readiness = voice_startup_readiness(mode="staging").to_dict()
    packaged_readiness = voice_startup_readiness(mode="packaged").to_dict()

    o23e = read_json(O23E_PYTHON_STRATEGY)
    o23f = read_json(O23F_RESOLVER_MANIFEST)
    o23g = read_json(O23G_READINESS_MANIFEST)
    o23h = read_json(O23H_DOWNLOADS_MANIFEST)
    o23i = read_json(O23I_WORKER_PATHS_MANIFEST)

    final_app_python = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"

    packaged_missing_runtime_is_clear = any(
        check["name"] == "packaged_mode_does_not_fallback_to_dev_venv" and check["ok"] is False
        for check in packaged_readiness.get("checks", [])
    )

    required_staging_assets = {
        "staging_voice_root": required_file(VOICE_STAGING_ROOT),
        "staging_voice_manifest": required_file(VOICE_STAGING_MANIFEST),
        "staging_python_launcher": required_file(VOICE_STAGING_ROOT / "python/bin/python"),
        "kokoro_model": required_file(VOICE_STAGING_ROOT / "kokoro/kokoro-v1_0.pth"),
        "kokoro_config": required_file(VOICE_STAGING_ROOT / "kokoro/config.json"),
        "kokoro_voice_af_heart": required_file(VOICE_STAGING_ROOT / "kokoro/voices/af_heart.pt"),
        "spacy_en_core_web_sm": required_file(VOICE_STAGING_ROOT / "spacy/en_core_web_sm"),
        "whisper_base": required_file(VOICE_STAGING_ROOT / "whisper/base"),
    }

    proof_chain = {
        "o23e_python_strategy": {
            "path": rel(O23E_PYTHON_STRATEGY),
            "exists": O23E_PYTHON_STRATEGY.exists(),
            "ok": bool(o23e.get("ok")),
        },
        "o23f_resolver": {
            "path": rel(O23F_RESOLVER_MANIFEST),
            "exists": O23F_RESOLVER_MANIFEST.exists(),
            "ok": bool(o23f.get("ok")),
        },
        "o23g_startup_readiness": {
            "path": rel(O23G_READINESS_MANIFEST),
            "exists": O23G_READINESS_MANIFEST.exists(),
            "ok": bool(o23g.get("ok")),
        },
        "o23h_no_hidden_downloads": {
            "path": rel(O23H_DOWNLOADS_MANIFEST),
            "exists": O23H_DOWNLOADS_MANIFEST.exists(),
            "ok": bool(o23h.get("ok")),
        },
        "o23i_staged_worker_paths": {
            "path": rel(O23I_WORKER_PATHS_MANIFEST),
            "exists": O23I_WORKER_PATHS_MANIFEST.exists(),
            "ok": bool(o23i.get("ok")),
        },
    }

    manifest = {
        "ok": True,
        "phase": "O23J",
        "purpose": "final_voice_packaging_contract_lock_and_docs",
        "status": "staging_locked_release_contract_locked_final_app_runtime_not_yet_embedded",
        "final_packaged_voice_root": "Tessaris.app/Contents/Resources/voice",
        "final_packaged_python": "Tessaris.app/Contents/Resources/voice/python/bin/python",
        "final_app_runtime_present": final_app_python.exists(),
        "staging_readiness_ok": staging_readiness.get("ok") is True,
        "packaged_readiness_ok": packaged_readiness.get("ok") is True,
        "packaged_missing_runtime_is_clear": packaged_missing_runtime_is_clear,
        "required_staging_assets": required_staging_assets,
        "proof_chain": proof_chain,
        "release_gates": {
            "must_embed_python_3_12": True,
            "must_include_kokoro_runtime": True,
            "must_include_kokoro_model_config_and_voice": True,
            "must_include_spacy_model": True,
            "must_include_whisper_model": True,
            "must_pass_startup_readiness": True,
            "must_pass_no_hidden_downloads_policy": True,
            "must_not_fallback_to_dev_venv_in_customer_release": True,
            "must_not_use_elevenlabs_fallback": True,
            "must_not_use_browser_speechrecognition_fallback": True,
        },
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_transformers_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "docs": {
            "path": rel(DOC_PATH),
        },
        "business_context_hardcoded": False,
    }

    checks = [
        manifest["staging_readiness_ok"] is True,
        manifest["packaged_missing_runtime_is_clear"] is True,
        all(item["exists"] for item in required_staging_assets.values()),
        all(item["exists"] for item in proof_chain.values()),
        proof_chain["o23e_python_strategy"]["ok"] is True,
        proof_chain["o23f_resolver"]["ok"] is True,
        proof_chain["o23g_startup_readiness"]["ok"] is True,
        proof_chain["o23h_no_hidden_downloads"]["ok"] is True,
        proof_chain["o23i_staged_worker_paths"]["ok"] is True,
    ]

    manifest["ok"] = all(checks)

    write_docs(manifest)

    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
