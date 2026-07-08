from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON_ROOT = APP_VOICE_ROOT / "python"
APP_PYTHON_BIN = APP_PYTHON_ROOT / "bin"
APP_FRAMEWORKS = APP_PYTHON_ROOT / "Frameworks"

APP_PYTHON = APP_PYTHON_BIN / "python"
APP_PYTHON3 = APP_PYTHON_BIN / "python3"
APP_PYTHON312 = APP_PYTHON_BIN / "python3.12"

PYTHON_BINARIES = [APP_PYTHON, APP_PYTHON3, APP_PYTHON312]

SOURCE_FRAMEWORK = Path(
    "/opt/homebrew/Cellar/python@3.12/3.12.13_4/Frameworks/Python.framework"
)
BUNDLED_FRAMEWORK = APP_FRAMEWORKS / "Python.framework"
BUNDLED_FRAMEWORK_DYLIB = BUNDLED_FRAMEWORK / "Versions/3.12/Python"

OLD_DYLIB = (
    "/opt/homebrew/Cellar/python@3.12/3.12.13_4/"
    "Frameworks/Python.framework/Versions/3.12/Python"
)
NEW_DYLIB = "@executable_path/../Frameworks/Python.framework/Versions/3.12/Python"

BACKUP_SYMLINK_DIR = APP_PYTHON_BIN / ".o24e_symlink_backups"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24f"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "bundle_python_framework_manifest.json"

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
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "realpath": realpath,
        "external_prefix_match": external_prefix,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def otool_l(path: Path) -> dict:
    result = run(["otool", "-L", str(path)])

    deps: list[str] = []
    external: list[str] = []
    relative: list[str] = []

    if result["returncode"] == 0:
        for line in result["stdout"].splitlines()[1:]:
            dep = line.strip().split(" ", 1)[0].strip()
            if not dep:
                continue

            deps.append(dep)

            if dep.startswith("@"):
                relative.append(dep)

            if any(dep.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
                external.append(dep)

    return {
        "path": rel(path),
        "returncode": result["returncode"],
        "dependencies": deps,
        "relative_dependencies": relative,
        "external_dependencies": external,
        "stderr_tail": result["stderr_tail"],
    }


def copy_framework() -> dict:
    if not SOURCE_FRAMEWORK.exists():
        raise RuntimeError(f"Missing source Python.framework: {SOURCE_FRAMEWORK}")

    APP_FRAMEWORKS.mkdir(parents=True, exist_ok=True)

    if BUNDLED_FRAMEWORK.exists():
        shutil.rmtree(BUNDLED_FRAMEWORK)

    shutil.copytree(
        SOURCE_FRAMEWORK,
        BUNDLED_FRAMEWORK,
        symlinks=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    return {
        "source_framework": str(SOURCE_FRAMEWORK),
        "bundled_framework": rel(BUNDLED_FRAMEWORK),
        "bundled_framework_exists": BUNDLED_FRAMEWORK.exists(),
        "bundled_framework_dylib": rel(BUNDLED_FRAMEWORK_DYLIB),
        "bundled_framework_dylib_exists": BUNDLED_FRAMEWORK_DYLIB.exists(),
    }


def relink_python_binaries() -> dict:
    results = {}

    for binary in PYTHON_BINARIES:
        before = otool_l(binary)

        change_result = run(
            [
                "install_name_tool",
                "-change",
                OLD_DYLIB,
                NEW_DYLIB,
                str(binary),
            ]
        )

        after = otool_l(binary)

        results[binary.name] = {
            "binary": rel(binary),
            "state": path_state(binary),
            "before": before,
            "install_name_tool": {
                "returncode": change_result["returncode"],
                "stderr_tail": change_result["stderr_tail"],
                "stdout_tail": change_result["stdout_tail"],
            },
            "after": after,
        }

    return results


def remove_backup_symlinks() -> dict:
    before = path_state(BACKUP_SYMLINK_DIR)

    removed = False

    if BACKUP_SYMLINK_DIR.exists():
        shutil.rmtree(BACKUP_SYMLINK_DIR)
        removed = True

    after = path_state(BACKUP_SYMLINK_DIR)

    return {
        "backup_dir": rel(BACKUP_SYMLINK_DIR),
        "before": before,
        "removed": removed,
        "after": after,
    }



def codesign_runtime() -> dict:
    # O24F.2: install_name_tool mutates Mach-O binaries on macOS.
    # Without ad-hoc re-signing, macOS can terminate the relocated Python with SIGKILL (-9).
    targets = [
        BUNDLED_FRAMEWORK_DYLIB,
        APP_PYTHON,
        APP_PYTHON3,
        APP_PYTHON312,
    ]

    results = {}

    # Sign the framework directory first, then the direct executables.
    framework_result = run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            str(BUNDLED_FRAMEWORK),
        ]
    )

    results["framework"] = {
        "target": rel(BUNDLED_FRAMEWORK),
        "returncode": framework_result["returncode"],
        "stdout_tail": framework_result["stdout_tail"],
        "stderr_tail": framework_result["stderr_tail"],
    }

    for target in targets:
        result = run(["codesign", "--force", "--sign", "-", str(target)])
        verify = run(["codesign", "--verify", "--verbose=2", str(target)])

        results[target.name] = {
            "target": rel(target),
            "returncode": result["returncode"],
            "stdout_tail": result["stdout_tail"],
            "stderr_tail": result["stderr_tail"],
            "verify_returncode": verify["returncode"],
            "verify_stdout_tail": verify["stdout_tail"],
            "verify_stderr_tail": verify["stderr_tail"],
        }

    return results


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


def audit_script(script_name: str) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "PYTHONPATH": str(ROOT),
        }
    )

    return parse_json_from_result(
        run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / script_name)], env=env)
    )


def main() -> int:
    framework = copy_framework()
    backup_cleanup = remove_backup_symlinks()
    relink = relink_python_binaries()
    codesign = codesign_runtime()

    py_probe = python_probe()
    readiness = packaged_readiness_probe()
    o24c_after = audit_script("aion_voice_self_contained_runtime_audit_o24c.py")
    o24d_after = audit_script("aion_voice_native_dependency_audit_o24d.py")
    o24b_after = audit_script("aion_voice_relocation_hardening_o24b.py")

    app_python_otool = otool_l(APP_PYTHON)

    release_blockers = []

    if not BUNDLED_FRAMEWORK_DYLIB.exists():
        release_blockers.append("bundled_python_framework_missing")

    if app_python_otool["external_dependencies"]:
        release_blockers.append("app_python_still_has_external_native_dependencies")

    if OLD_DYLIB in json.dumps(app_python_otool):
        release_blockers.append("old_homebrew_python_framework_reference_still_present")

    if NEW_DYLIB not in json.dumps(app_python_otool):
        release_blockers.append("app_python_missing_app_local_framework_reference")

    if readiness.get("ok") is not True:
        release_blockers.append("packaged_readiness_failed_after_framework_relink")

    if py_probe.get("returncode") != 0:
        release_blockers.append("python_probe_failed_after_framework_relink")

    if o24c_after.get("release_ready") is not True:
        release_blockers.append("o24c_self_contained_audit_not_release_ready")

    if o24d_after.get("release_ready") is not True:
        release_blockers.append("o24d_native_dependency_audit_not_release_ready")

    if o24b_after.get("ok") is not True:
        release_blockers.append("o24b_relocation_hardening_failed_after_framework_relink")

    manifest = {
        "ok": True,
        "phase": "O24F",
        "purpose": "bundle_python_framework_and_relink_app_python",
        "status": "python_framework_bundled_and_app_python_relinked",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "old_dylib": OLD_DYLIB,
        "new_dylib": NEW_DYLIB,
        "framework": framework,
        "backup_cleanup": backup_cleanup,
        "relink": relink,
        "codesign": codesign,
        "framework_directory_codesign_note": "Python.framework directory signing may be unsuitable for this copied framework layout; the actual framework dylib and Python executables are the required signed Mach-O targets.",
        "app_python_otool_after": app_python_otool,
        "python_probe": py_probe,
        "packaged_readiness": {
            "ok": readiness.get("ok"),
            "returncode": readiness.get("returncode"),
            "bundle_root": readiness.get("bundle_root"),
            "python": readiness.get("python"),
        },
        "post_relink_audits": {
            "o24c_release_ready": o24c_after.get("release_ready"),
            "o24c_release_blockers": o24c_after.get("release_blockers"),
            "o24d_release_ready": o24d_after.get("release_ready"),
            "o24d_release_blockers": o24d_after.get("release_blockers"),
            "o24d_external_dependency_count": o24d_after.get("external_dependency_count"),
            "o24b_ok": o24b_after.get("ok"),
            "o24b_relocated_path_used": o24b_after.get("relocated_path_used"),
        },
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "required_next_step": {
            "if_release_ready_create_app_local_worker_entrypoint": True,
            "if_not_release_ready_fix_recorded_blockers_then_rerun_o24b_o24c_o24d": True,
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
        BUNDLED_FRAMEWORK_DYLIB.exists(),
        all(item.get("returncode") == 0 and item.get("verify_returncode", 0) == 0 for key, item in codesign.items() if key != "framework"),
        app_python_otool["external_dependencies"] == [],
        NEW_DYLIB in json.dumps(app_python_otool),
        OLD_DYLIB not in json.dumps(app_python_otool),
        py_probe.get("returncode") == 0,
        py_probe.get("version_info", [0, 0])[0:2] == [3, 12],
        all(item.get("found") is True for item in py_probe.get("imports", {}).values()),
        readiness.get("ok") is True,
        readiness.get("returncode") == 0,
        o24c_after.get("release_ready") is True,
        o24d_after.get("release_ready") is True,
        o24b_after.get("ok") is True,
    ]

    manifest["ok"] = all(checks)

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
