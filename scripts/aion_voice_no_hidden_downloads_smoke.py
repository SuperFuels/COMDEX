from __future__ import annotations

import json
import os
from pathlib import Path

from backend.modules.aion_voice.voice_download_policy import (
    build_voice_download_policy_env,
    voice_download_policy_report,
)
from backend.modules.aion_voice.voice_worker_bridge import voice_worker_environment


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23h"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "no_hidden_downloads_manifest.json"


def main() -> int:
    staging_report = voice_download_policy_report(mode="staging")
    packaged_report = voice_download_policy_report(mode="packaged")
    worker_env = voice_worker_environment()

    manifest = {
        "ok": True,
        "phase": "O23H",
        "purpose": "lock_no_hidden_downloads_for_packaged_voice_runtime",
        "staging_report": staging_report.to_dict(),
        "packaged_report": packaged_report.to_dict(),
        "worker_environment": {
            key: worker_env.get(key, "")
            for key in [
                "HF_HUB_OFFLINE",
                "TRANSFORMERS_OFFLINE",
                "HF_DATASETS_OFFLINE",
                "HF_HUB_DISABLE_TELEMETRY",
                "TOKENIZERS_PARALLELISM",
                "AION_VOICE_NO_HIDDEN_DOWNLOADS",
                "AION_ELEVENLABS_ENABLED",
                "AION_BROWSER_SPEECH_FALLBACK_ENABLED",
            ]
        },
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_transformers_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "business_context_hardcoded": False,
    }

    checks = [
        staging_report.ok,
        packaged_report.ok,
        manifest["worker_environment"]["HF_HUB_OFFLINE"] == "1",
        manifest["worker_environment"]["TRANSFORMERS_OFFLINE"] == "1",
        manifest["worker_environment"]["HF_DATASETS_OFFLINE"] == "1",
        manifest["worker_environment"]["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true",
        manifest["worker_environment"]["AION_ELEVENLABS_ENABLED"] == "false",
        manifest["worker_environment"]["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false",
    ]

    manifest["ok"] = all(checks)
    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
