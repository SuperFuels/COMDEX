from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON = APP_VOICE_ROOT / "python/bin/python"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24c"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "self_contained_runtime_audit_manifest.json"

EXPECTED_FINAL_PYTHON = "Tessaris.app/Contents/Resources/voice/python/bin/python"
EXTERNAL_PREFIXES = [
    "/opt/homebrew",
    "/usr/local",
    "/Library/Frameworks",
    "/System/Library",
    "/Applications/Xcode.app",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def run(cmd: list[str], env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def audit_path(path: Path) -> dict:
    exists = path.exists()
    resolved = path.resolve() if exists else None
    resolved_str = str(resolved) if resolved else None

    return {
        "path": rel(path),
        "exists": exists,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "realpath": resolved_str,
        "inside_voice_bundle": bool(resolved and is_inside(path, APP_VOICE_ROOT)),
        "external_prefix_match": next(
            (prefix for prefix in EXTERNAL_PREFIXES if resolved_str and resolved_str.startswith(prefix)),
            None,
        ),
    }


def find_external_symlinks(root: Path) -> list[dict]:
    findings: list[dict] = []

    if not root.exists():
        return findings

    for current, dirs, files in os.walk(root):
        current_path = Path(current)

        for name in dirs + files:
            path = current_path / name
            if not path.is_symlink():
                continue

            state = audit_path(path)
            if state["external_prefix_match"] or state["inside_voice_bundle"] is False:
                findings.append(state)

    return findings


def packaged_readiness_probe() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(APP_VOICE_ROOT),
            "AION_VOICE_NO_HIDDEN_DOWNLOADS": "true",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "AION_ELEVENLABS_ENABLED": "false",
            "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
            "PYTHONPATH": str(ROOT),
        }
    )

    result = run(
        [
            str(ROOT / ".venv/bin/python"),
            "-c",
            "import json; from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness; print(json.dumps(voice_startup_readiness(mode='packaged').to_dict()))",
        ],
        env=env,
    )

    try:
        payload = json.loads(result["stdout"].strip())
    except Exception:
        payload = {
            "parse_error": True,
            "stdout_tail": result["stdout_tail"],
            "stderr_tail": result["stderr_tail"],
        }

    payload["returncode"] = result["returncode"]
    return payload


def main() -> int:
    python_state = audit_path(APP_PYTHON)
    external_symlinks = find_external_symlinks(APP_VOICE_ROOT)
    readiness = packaged_readiness_probe()

    release_blockers = []

    if not APP_PYTHON.exists():
        release_blockers.append("missing_app_python")

    if python_state["is_symlink"]:
        release_blockers.append("app_python_is_symlink")

    if python_state["external_prefix_match"]:
        release_blockers.append("app_python_resolves_to_external_runtime")

    if external_symlinks:
        release_blockers.append("voice_bundle_contains_external_symlinks")

    if readiness.get("ok") is not True:
        release_blockers.append("packaged_readiness_not_passing")

    manifest = {
        "ok": True,
        "phase": "O24C",
        "purpose": "audit_if_tessaris_app_voice_runtime_is_self_contained",
        "status": "audit_complete_release_blockers_recorded",
        "expected_final_python": EXPECTED_FINAL_PYTHON,
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "python_state": python_state,
        "external_symlinks": external_symlinks,
        "packaged_readiness": {
            "ok": readiness.get("ok"),
            "returncode": readiness.get("returncode"),
            "bundle_root": readiness.get("bundle_root"),
            "python": readiness.get("python"),
        },
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "required_fix": {
            "must_replace_symlinked_python_with_relocatable_or_embedded_python": True,
            "must_not_resolve_to_homebrew_or_dev_machine_runtime": True,
            "must_keep_kokoro_spacy_whisper_assets_app_local": True,
            "must_keep_no_hidden_download_policy": True,
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

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))

    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
