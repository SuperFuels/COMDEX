from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON_BIN = APP_VOICE_ROOT / "python/bin"
APP_PYTHON = APP_PYTHON_BIN / "python"
APP_PYTHON3 = APP_PYTHON_BIN / "python3"
APP_PYTHON312 = APP_PYTHON_BIN / "python3.12"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24e"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "materialize_python_manifest.json"

PYTHON_NAMES = [
    "python",
    "python3",
    "python3.12",
]

EXTERNAL_PREFIXES = [
    "/opt/homebrew",
    "/usr/local",
    "/Library/Frameworks",
    "/Applications/Xcode.app",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


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


def parse_json_from_result(result: dict) -> dict:
    stdout = result.get("stdout", "") or result.get("stdout_tail", "")
    stderr = result.get("stderr", "") or result.get("stderr_tail", "")

    try:
        payload = json.loads(stdout.strip())
    except Exception:
        try:
            start = stdout.index("{")
            end = stdout.rindex("}") + 1
            payload = json.loads(stdout[start:end])
        except Exception:
            payload = {
                "parse_error": True,
                "stdout_tail": stdout[-4000:],
                "stderr_tail": stderr[-4000:],
            }

    payload["returncode"] = result.get("returncode")
    return payload


def path_state(path: Path) -> dict:
    exists = path.exists()
    realpath = str(path.resolve()) if exists else None
    external_prefix = None

    if realpath:
        external_prefix = next(
            (prefix for prefix in EXTERNAL_PREFIXES if realpath.startswith(prefix)),
            None,
        )

    return {
        "path": rel(path),
        "exists": exists,
        "is_file": path.is_file(),
        "is_symlink": path.is_symlink(),
        "realpath": realpath,
        "external_prefix_match": external_prefix,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def materialize_python_executables() -> dict:
    if not APP_PYTHON.exists():
        raise RuntimeError(f"Missing app bundle Python. Run O24A first: {APP_PYTHON}")

    APP_PYTHON_BIN.mkdir(parents=True, exist_ok=True)

    before = {name: path_state(APP_PYTHON_BIN / name) for name in PYTHON_NAMES}

    source_realpath = APP_PYTHON.resolve()
    if not source_realpath.exists():
        raise RuntimeError(f"Cannot resolve Python source realpath: {APP_PYTHON}")

    backup_dir = APP_PYTHON_BIN / ".o24e_symlink_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    materialized = {}

    for name in PYTHON_NAMES:
        target = APP_PYTHON_BIN / name

        if target.exists() or target.is_symlink():
            backup = backup_dir / name
            if backup.exists() or backup.is_symlink():
                backup.unlink()
            if target.is_symlink():
                backup.symlink_to(os.readlink(target))
            else:
                shutil.copy2(target, backup)
            target.unlink()

        shutil.copy2(source_realpath, target)
        mode = target.stat().st_mode
        target.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        materialized[name] = {
            "target": rel(target),
            "source_realpath": str(source_realpath),
            "after": path_state(target),
        }

    after = {name: path_state(APP_PYTHON_BIN / name) for name in PYTHON_NAMES}

    return {
        "source_realpath": str(source_realpath),
        "before": before,
        "after": after,
        "materialized": materialized,
        "backup_dir": rel(backup_dir),
    }


def otool_l(path: Path) -> dict:
    result = run(["otool", "-L", str(path)])

    deps = []
    external = []

    if result["returncode"] == 0:
        for line in result["stdout"].splitlines()[1:]:
            dep = line.strip().split(" ", 1)[0].strip()
            if not dep:
                continue
            deps.append(dep)
            if any(dep.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
                external.append(dep)

    return {
        "path": rel(path),
        "returncode": result["returncode"],
        "dependencies": deps,
        "external_dependencies": external,
        "stderr_tail": result["stderr_tail"],
    }


def python_probe() -> dict:
    code = """
import importlib.util
import json
import sys

required = ["kokoro", "soundfile", "faster_whisper", "ctranslate2", "av", "torch", "spacy", "numpy"]
imports = {}

for name in required:
    spec = importlib.util.find_spec(name)
    imports[name] = {
        "found": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
    }

print(json.dumps({
    "executable": sys.executable,
    "version_info": list(sys.version_info[:3]),
    "imports": imports,
}))
"""
    return parse_json_from_result(run([str(APP_PYTHON), "-c", code]))


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

    return parse_json_from_result(
        run(
            [
                str(ROOT / ".venv/bin/python"),
                "-c",
                "import json; from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness; print(json.dumps(voice_startup_readiness(mode='packaged').to_dict()))",
            ],
            env=env,
        )
    )


def self_contained_probe() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "PYTHONPATH": str(ROOT),
        }
    )

    return parse_json_from_result(
        run(
            [
                str(ROOT / ".venv/bin/python"),
                str(ROOT / "scripts/aion_voice_self_contained_runtime_audit_o24c.py"),
            ],
            env=env,
        )
    )


def main() -> int:
    materialized = materialize_python_executables()
    py_probe = python_probe()
    readiness = packaged_readiness_probe()
    python_otool = otool_l(APP_PYTHON)
    self_audit = self_contained_probe()

    app_python_after = path_state(APP_PYTHON)

    release_blockers = []

    if app_python_after["is_symlink"]:
        release_blockers.append("app_python_still_symlink")

    if app_python_after["external_prefix_match"]:
        release_blockers.append("app_python_still_resolves_to_external_runtime")

    if python_otool["external_dependencies"]:
        release_blockers.append("python_binary_has_external_native_dependencies")

    if readiness.get("ok") is not True:
        release_blockers.append("packaged_readiness_failed_after_materialization")

    if py_probe.get("returncode") != 0:
        release_blockers.append("materialized_python_probe_failed")

    manifest = {
        "ok": True,
        "phase": "O24E",
        "purpose": "materialize_app_bundle_python_executables_from_symlinks",
        "status": "python_executables_materialized_release_blockers_reduced_or_recorded",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "materialized": materialized,
        "app_python_after": app_python_after,
        "python_probe": py_probe,
        "packaged_readiness": {
            "ok": readiness.get("ok"),
            "returncode": readiness.get("returncode"),
            "bundle_root": readiness.get("bundle_root"),
            "python": readiness.get("python"),
        },
        "python_otool": python_otool,
        "self_contained_audit_after_materialization": {
            "release_ready": self_audit.get("release_ready"),
            "release_blockers": self_audit.get("release_blockers"),
            "python_is_symlink": self_audit.get("python_state", {}).get("is_symlink"),
            "external_symlink_count": len(self_audit.get("external_symlinks", [])) if isinstance(self_audit.get("external_symlinks"), list) else None,
        },
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "required_next_fix": {
            "if_python_binary_has_external_native_dependencies_bundle_or_rewrite_them": True,
            "if_framework_dependency_exists_bundle_python_framework_or_use_relocatable_distribution": True,
            "re_run_o24c_and_o24d_after_materialization": True,
            "re_run_relocation_hardening_after_materialization": True,
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
        app_python_after["exists"] is True,
        app_python_after["is_symlink"] is False,
        py_probe.get("returncode") == 0,
        py_probe.get("version_info", [0, 0])[0:2] == [3, 12],
        all(item.get("found") is True for item in py_probe.get("imports", {}).values()),
        readiness.get("ok") is True,
        readiness.get("returncode") == 0,
    ]

    manifest["ok"] = all(checks)

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
