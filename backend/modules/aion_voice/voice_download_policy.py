from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any


AION_O23H_NO_HIDDEN_DOWNLOADS_VERSION = "aion.voice.o23h.no_hidden_downloads.v1"

OFFLINE_ENV_DEFAULTS = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "AION_VOICE_NO_HIDDEN_DOWNLOADS": "true",
    "AION_ELEVENLABS_ENABLED": "false",
    "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
}


@dataclass
class VoiceDownloadPolicyReport:
    ok: bool
    version: str
    mode: str
    environment: dict[str, str]
    hidden_huggingface_downloads_allowed: bool
    hidden_transformers_downloads_allowed: bool
    hidden_spacy_downloads_allowed: bool
    hidden_elevenlabs_fallback_allowed: bool
    hidden_browser_speech_fallback_allowed: bool
    business_context_hardcoded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def voice_runtime_mode() -> str:
    return os.environ.get("AION_VOICE_RUNTIME_MODE", "auto").strip().lower() or "auto"


def no_hidden_downloads_required(mode: str | None = None) -> bool:
    selected = (mode or voice_runtime_mode()).strip().lower()
    explicit = os.environ.get("AION_VOICE_NO_HIDDEN_DOWNLOADS", "").strip().lower()

    if explicit in {"1", "true", "yes", "on"}:
        return True

    return selected in {"staging", "bundle_staging", "staged", "packaged", "app", "bundle"}


def build_voice_download_policy_env(base: dict[str, str] | None = None, mode: str | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    selected = (mode or env.get("AION_VOICE_RUNTIME_MODE", "auto")).strip().lower() or "auto"

    if no_hidden_downloads_required(selected):
        for key, value in OFFLINE_ENV_DEFAULTS.items():
            env[key] = value

    return env


def apply_voice_download_policy(mode: str | None = None) -> dict[str, str]:
    env = build_voice_download_policy_env(os.environ, mode=mode)
    for key in OFFLINE_ENV_DEFAULTS:
        if key in env:
            os.environ[key] = env[key]
    return env


def voice_download_policy_report(mode: str | None = None) -> VoiceDownloadPolicyReport:
    selected = (mode or voice_runtime_mode()).strip().lower() or "auto"
    env = build_voice_download_policy_env(os.environ, mode=selected)

    relevant = {
        key: env.get(key, "")
        for key in sorted(OFFLINE_ENV_DEFAULTS)
    }

    return VoiceDownloadPolicyReport(
        ok=(
            relevant["HF_HUB_OFFLINE"] == "1"
            and relevant["TRANSFORMERS_OFFLINE"] == "1"
            and relevant["HF_DATASETS_OFFLINE"] == "1"
            and relevant["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
            and relevant["AION_ELEVENLABS_ENABLED"] == "false"
            and relevant["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"
        ),
        version=AION_O23H_NO_HIDDEN_DOWNLOADS_VERSION,
        mode=selected,
        environment=relevant,
        hidden_huggingface_downloads_allowed=False,
        hidden_transformers_downloads_allowed=False,
        hidden_spacy_downloads_allowed=False,
        hidden_elevenlabs_fallback_allowed=False,
        hidden_browser_speech_fallback_allowed=False,
        business_context_hardcoded=False,
    )


def assert_no_hidden_downloads_policy(mode: str | None = None) -> VoiceDownloadPolicyReport:
    report = voice_download_policy_report(mode=mode)
    if not report.ok:
        raise RuntimeError(f"AION voice no-hidden-downloads policy failed: {report.to_dict()}")
    return report
