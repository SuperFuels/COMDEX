from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from backend.modules.aion_voice.voice_worker_bridge import (
    resolve_voice_bundle_root,
    voice_python_for_bundle_root,
    voice_worker_environment,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23i"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "staged_worker_paths_manifest.json"


def short(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)


def main() -> int:
    original_mode = os.environ.get("AION_VOICE_RUNTIME_MODE")
    os.environ["AION_VOICE_RUNTIME_MODE"] = "staging"

    try:
        bundle_root = resolve_voice_bundle_root()
        staged_python = voice_python_for_bundle_root(bundle_root)
        env = voice_worker_environment()
        env["PYTHONPATH"] = str(ROOT)

        proc = subprocess.run(
            [
                str(staged_python),
                str(ROOT / "scripts" / "aion_voice_worker.py"),
                "aion-o23i-bundle-probe",
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        try:
            worker_payload = json.loads(proc.stdout.strip())
        except Exception:
            try:
                start = proc.stdout.index("{")
                end = proc.stdout.rindex("}") + 1
                worker_payload = json.loads(proc.stdout[start:end])
            except Exception:
                worker_payload = {
                    "ok": False,
                    "parse_error": True,
                    "stdout_tail": proc.stdout[-2000:],
                    "stderr_tail": proc.stderr[-2000:],
                }

        manifest = {
            "ok": proc.returncode == 0 and worker_payload.get("ok") is True,
            "phase": "O23I",
            "purpose": "prove_worker_executes_via_staged_bundle_python_and_bundle_paths",
            "bundle_root": short(bundle_root),
            "staged_python": short(staged_python),
            "worker_returncode": proc.returncode,
            "worker_payload": worker_payload,
            "stderr_tail": proc.stderr[-2000:],
            "download_policy": {
                "hidden_huggingface_downloads_allowed": False,
                "hidden_transformers_downloads_allowed": False,
                "hidden_spacy_downloads_allowed": False,
                "hidden_elevenlabs_fallback_allowed": False,
                "hidden_browser_speech_fallback_allowed": False,
            },
            "business_context_hardcoded": False,
        }

        OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0 if manifest["ok"] else 2
    finally:
        if original_mode is None:
            os.environ.pop("AION_VOICE_RUNTIME_MODE", None)
        else:
            os.environ["AION_VOICE_RUNTIME_MODE"] = original_mode


if __name__ == "__main__":
    raise SystemExit(main())
