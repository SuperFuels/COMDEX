from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.modules.aion_voice.voice_worker_bridge import (
    default_voice_python,
    resolve_voice_bundle_root,
    voice_python_for_bundle_root,
)


AION_O23G_VOICE_STARTUP_READINESS_VERSION = "aion.voice.o23g.startup_readiness.v1"

REQUIRED_IMPORTS = [
    "kokoro",
    "soundfile",
    "faster_whisper",
    "ctranslate2",
    "av",
    "torch",
    "spacy",
    "numpy",
]

REQUIRED_ASSETS = {
    "kokoro_model": "kokoro/kokoro-v1_0.pth",
    "kokoro_config": "kokoro/config.json",
    "kokoro_voice_af_heart": "kokoro/voices/af_heart.pt",
    "spacy_en_core_web_sm": "spacy/en_core_web_sm",
    "whisper_base": "whisper/base",
    "voice_manifest": "manifest.json",
}


@dataclass
class VoiceReadinessCheck:
    name: str
    ok: bool
    detail: str
    path: str | None = None


@dataclass
class VoiceReadinessReport:
    ok: bool
    version: str
    mode: str
    bundle_root: str
    python: str
    checks: list[VoiceReadinessCheck]
    download_policy: dict[str, bool]
    business_context_hardcoded: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [asdict(check) for check in self.checks]
        return data


def _short(path: Path) -> str:
    try:
        root = Path(__file__).resolve().parents[3]
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def _run_python(py: Path, code: str) -> dict[str, Any]:
    proc = subprocess.run(
        [str(py), "-c", code],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _python_probe(py: Path) -> dict[str, Any]:
    code = f"""
import importlib.util
import json
import sys

required = {REQUIRED_IMPORTS!r}
imports = {{}}

for name in required:
    spec = importlib.util.find_spec(name)
    imports[name] = {{
        "found": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
    }}

print(json.dumps({{
    "version_info": list(sys.version_info[:3]),
    "executable": sys.executable,
    "imports": imports,
}}))
"""
    result = _run_python(py, code)
    if result["returncode"] != 0:
        return {
            "ok": False,
            "error": "python_probe_failed",
            "stderr_tail": result["stderr"][-1200:],
        }

    try:
        payload = json.loads(result["stdout"].strip().splitlines()[-1])
    except Exception as exc:
        return {
            "ok": False,
            "error": f"python_probe_parse_failed: {exc}",
            "stdout_tail": result["stdout"][-1200:],
            "stderr_tail": result["stderr"][-1200:],
        }

    payload["ok"] = True
    return payload


def voice_startup_readiness(mode: str | None = None) -> VoiceReadinessReport:
    if mode is not None:
        original_mode = os.environ.get("AION_VOICE_RUNTIME_MODE")
        os.environ["AION_VOICE_RUNTIME_MODE"] = mode
    else:
        original_mode = None

    try:
        selected_mode = os.environ.get("AION_VOICE_RUNTIME_MODE", "auto") or "auto"
        bundle_root = resolve_voice_bundle_root()
        python = default_voice_python()
        checks: list[VoiceReadinessCheck] = []

        checks.append(
            VoiceReadinessCheck(
                name="bundle_root_exists",
                ok=bundle_root.exists(),
                detail="voice bundle root must exist",
                path=_short(bundle_root),
            )
        )

        expected_bundle_python = voice_python_for_bundle_root(bundle_root)
        checks.append(
            VoiceReadinessCheck(
                name="bundle_python_exists",
                ok=expected_bundle_python.exists(),
                detail="app-local voice python should exist in staging or packaged bundle",
                path=_short(expected_bundle_python),
            )
        )

        checks.append(
            VoiceReadinessCheck(
                name="selected_python_exists",
                ok=python.exists(),
                detail="resolved voice python must exist",
                path=_short(python),
            )
        )

        probe = _python_probe(python) if python.exists() else {"ok": False, "error": "missing_python"}
        py312_ok = bool(probe.get("ok") and probe.get("version_info", [0, 0])[0:2] == [3, 12])
        checks.append(
            VoiceReadinessCheck(
                name="python_is_3_12",
                ok=py312_ok,
                detail=json.dumps(probe.get("version_info", probe.get("error"))),
                path=_short(python),
            )
        )

        imports = probe.get("imports", {}) if probe.get("ok") else {}
        for module in REQUIRED_IMPORTS:
            found = bool(imports.get(module, {}).get("found"))
            checks.append(
                VoiceReadinessCheck(
                    name=f"import_{module}",
                    ok=found,
                    detail=imports.get(module, {}).get("origin") or "missing",
                )
            )

        for name, rel in REQUIRED_ASSETS.items():
            asset = bundle_root / rel
            checks.append(
                VoiceReadinessCheck(
                    name=f"asset_{name}",
                    ok=asset.exists(),
                    detail="required app-local voice asset",
                    path=_short(asset),
                )
            )

        checks.append(
            VoiceReadinessCheck(
                name="no_elevenlabs_fallback",
                ok=os.environ.get("AION_ELEVENLABS_ENABLED", "").lower() not in {"1", "true", "yes"},
                detail="ElevenLabs must not be enabled for local packaged voice readiness",
            )
        )

        checks.append(
            VoiceReadinessCheck(
                name="no_browser_speech_fallback",
                ok=os.environ.get("AION_BROWSER_SPEECH_FALLBACK_ENABLED", "").lower() not in {"1", "true", "yes"},
                detail="browser SpeechRecognition fallback must not be enabled",
            )
        )

        if selected_mode in {"packaged", "app", "bundle"}:
            packaged_python_ok = expected_bundle_python.exists() and python == expected_bundle_python
            checks.append(
                VoiceReadinessCheck(
                    name="packaged_mode_does_not_fallback_to_dev_venv",
                    ok=packaged_python_ok,
                    detail="packaged mode must use packaged bundle python when final app runtime exists",
                    path=_short(expected_bundle_python),
                )
            )

        report = VoiceReadinessReport(
            ok=all(check.ok for check in checks),
            version=AION_O23G_VOICE_STARTUP_READINESS_VERSION,
            mode=selected_mode,
            bundle_root=_short(bundle_root),
            python=_short(python),
            checks=checks,
            download_policy={
                "hidden_huggingface_downloads_allowed": False,
                "hidden_spacy_downloads_allowed": False,
                "hidden_elevenlabs_fallback_allowed": False,
                "hidden_browser_speech_fallback_allowed": False,
            },
            business_context_hardcoded=False,
        )
        return report
    finally:
        if mode is not None:
            if original_mode is None:
                os.environ.pop("AION_VOICE_RUNTIME_MODE", None)
            else:
                os.environ["AION_VOICE_RUNTIME_MODE"] = original_mode


def main() -> int:
    mode = os.environ.get("AION_VOICE_RUNTIME_MODE")
    report = voice_startup_readiness(mode=mode)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
