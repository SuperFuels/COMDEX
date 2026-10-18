from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23g"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "startup_readiness_manifest.json"


def main() -> int:
    staging = voice_startup_readiness(mode="staging")
    packaged = voice_startup_readiness(mode="packaged")

    staging_data = staging.to_dict()
    packaged_data = packaged.to_dict()

    packaged_missing_runtime_is_clear = any(
        check["name"] == "packaged_mode_does_not_fallback_to_dev_venv" and check["ok"] is False
        for check in packaged_data["checks"]
    )

    manifest = {
        "ok": staging.ok and packaged_missing_runtime_is_clear,
        "phase": "O23G",
        "purpose": "prove_startup_readiness_checker_for_voice_bundle",
        "staging_readiness": staging_data,
        "packaged_readiness": packaged_data,
        "packaged_missing_runtime_is_clear": packaged_missing_runtime_is_clear,
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "business_context_hardcoded": False,
    }

    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
