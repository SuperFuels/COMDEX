from __future__ import annotations

import json
import os
from pathlib import Path

from backend.modules.aion_voice.voice_worker_bridge import (
    default_voice_python,
    resolve_voice_bundle_root,
    voice_bundle_packaged_root,
    voice_bundle_staging_root,
    voice_python_for_bundle_root,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23f"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "packaged_resolver_manifest.json"


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_with_env(**env: str) -> dict:
    original = {
        "AION_VOICE_PYTHON": os.environ.get("AION_VOICE_PYTHON"),
        "AION_VOICE_BUNDLE_ROOT": os.environ.get("AION_VOICE_BUNDLE_ROOT"),
        "AION_VOICE_RUNTIME_MODE": os.environ.get("AION_VOICE_RUNTIME_MODE"),
    }

    for key in original:
        os.environ.pop(key, None)

    for key, value in env.items():
        os.environ[key] = value

    try:
        bundle = resolve_voice_bundle_root()
        python = default_voice_python()
        return {
            "bundle_root": short_path(bundle),
            "python": short_path(python),
            "python_exists": python.exists(),
        }
    finally:
        for key, value in original.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value


def main() -> int:
    staging_root = voice_bundle_staging_root()
    packaged_root = voice_bundle_packaged_root()
    staging_python = voice_python_for_bundle_root(staging_root)
    packaged_python = voice_python_for_bundle_root(packaged_root)

    manifest = {
        "ok": True,
        "phase": "O23F",
        "purpose": "prove_app_local_packaged_mode_voice_resolver",
        "staging": {
            "bundle_root": short_path(staging_root),
            "python": short_path(staging_python),
            "python_exists": staging_python.exists(),
        },
        "packaged": {
            "bundle_root": short_path(packaged_root),
            "python": short_path(packaged_python),
            "python_exists": packaged_python.exists(),
            "expected_final_packaged_path": "Tessaris.app/Contents/Resources/voice/python/bin/python",
        },
        "resolution_cases": {
            "default": resolve_with_env(),
            "staging_mode": resolve_with_env(AION_VOICE_RUNTIME_MODE="staging"),
            "packaged_mode": resolve_with_env(AION_VOICE_RUNTIME_MODE="packaged"),
            "bundle_root_override": resolve_with_env(AION_VOICE_BUNDLE_ROOT=str(staging_root)),
            "explicit_python_override": resolve_with_env(AION_VOICE_PYTHON=str(staging_python)),
        },
        "environment_contract": {
            "AION_VOICE_PYTHON": "highest priority explicit python executable override",
            "AION_VOICE_BUNDLE_ROOT": "explicit app-local voice bundle root",
            "AION_VOICE_RUNTIME_MODE": "development, staging, or packaged resolver mode",
        },
        "download_policy": {
            "packaged_mode_hidden_huggingface_downloads_allowed": False,
            "packaged_mode_hidden_spacy_downloads_allowed": False,
            "packaged_mode_hidden_elevenlabs_fallback_allowed": False,
        },
        "business_context_hardcoded": False,
    }

    checks = [
        manifest["staging"]["python_exists"] is True,
        manifest["resolution_cases"]["staging_mode"]["python"] == manifest["staging"]["python"],
        manifest["resolution_cases"]["bundle_root_override"]["python"] == manifest["staging"]["python"],
        manifest["resolution_cases"]["explicit_python_override"]["python"] == manifest["staging"]["python"],
        "Tessaris.app/Contents/Resources/voice" in manifest["packaged"]["bundle_root"],
    ]

    manifest["ok"] = all(checks)
    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
