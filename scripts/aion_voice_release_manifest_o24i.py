#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON = APP_VOICE_ROOT / "python/bin/python"
APP_WORKER = APP_VOICE_ROOT / "runtime/scripts/aion_voice_worker.py"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24i"
OUT_MANIFEST = OUT_DIR / "voice_release_manifest.json"

SOURCE_MANIFESTS = {
    "o24f": ROOT / ".runtime/voice_runtime_tests/o24f/bundle_python_framework_manifest.json",
    "o24g": ROOT / ".runtime/voice_runtime_tests/o24g/app_local_worker_manifest.json",
    "o24h": ROOT / ".runtime/voice_runtime_tests/o24h/app_local_tts_stt_smoke_manifest.json",
}

FRAMEWORK_DYLIB_ID = "@rpath/Python.framework/Versions/3.12/Python"

EXPECTED_FILES = {
    "app_python": APP_PYTHON,
    "app_python3": APP_VOICE_ROOT / "python/bin/python3",
    "app_python312": APP_VOICE_ROOT / "python/bin/python3.12",
    "python_framework_dylib": APP_VOICE_ROOT / "python/Frameworks/Python.framework/Versions/3.12/Python",
    "app_worker": APP_WORKER,
    "kokoro_model": APP_VOICE_ROOT / "kokoro/kokoro-v1_0.pth",
    "kokoro_config": APP_VOICE_ROOT / "kokoro/config.json",
    "kokoro_voice": APP_VOICE_ROOT / "kokoro/voices/af_heart.pt",
    "spacy_model": APP_VOICE_ROOT / "spacy/en_core_web_sm",
    "whisper_model": APP_VOICE_ROOT / "whisper/base",
    "bundle_manifest": APP_VOICE_ROOT / "manifest.json",
}

DISALLOWED_EXTERNAL_PREFIXES = (
    "/opt/homebrew",
    "/usr/local",
    "/Library/Frameworks",
    "/Applications/Xcode.app",
)

GENERATED_PATH_PREFIXES = (
    "desktop/mac/Tessaris.app/Contents/Resources/voice/",
    ".runtime/voice_runtime_tests/",
)

FORBIDDEN_BUSINESS_TOKENS = (
    "Home" + " Fixed",
    "Costa" + "Connect",
    "Costa" + "Conexion",
    "Al" + "mería",
    "Mur" + "cia",
    "Mo" + "jácar",
    "Al" + "box",
    "per" + "gola",
    "car" + "port",
    "vil" + "la",
    "trades" + "men",
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def path_state(path: Path) -> dict[str, Any]:
    exists = path.exists()
    is_symlink = path.is_symlink()
    realpath = str(path.resolve()) if exists else None
    external_prefix = None
    if realpath:
        for prefix in DISALLOWED_EXTERNAL_PREFIXES:
            if realpath.startswith(prefix):
                external_prefix = prefix
                break
    return {
        "path": rel(path),
        "exists": exists,
        "is_file": path.is_file() if exists else False,
        "is_dir": path.is_dir() if exists else False,
        "is_symlink": is_symlink,
        "realpath": realpath,
        "external_prefix_match": external_prefix,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def otool_deps(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": rel(path), "returncode": None, "dependencies": [], "external_dependencies": []}

    proc = subprocess.run(
        ["otool", "-L", str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    deps: list[str] = []
    if proc.returncode == 0:
        for line in proc.stdout.splitlines()[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            deps.append(stripped.split(" (", 1)[0])

    external = [
        dep
        for dep in deps
        if any(dep.startswith(prefix) for prefix in DISALLOWED_EXTERNAL_PREFIXES)
    ]

    return {
        "path": rel(path),
        "returncode": proc.returncode,
        "dependencies": deps,
        "external_dependencies": external,
        "stderr_tail": proc.stderr[-1000:],
    }



def harden_framework_dylib_id() -> dict[str, Any]:
    framework_dylib = APP_VOICE_ROOT / "python/Frameworks/Python.framework/Versions/3.12/Python"
    before = otool_deps(framework_dylib)

    changed = False
    install_name_result: dict[str, Any] | None = None
    codesign_result: dict[str, Any] | None = None
    verify_result: dict[str, Any] | None = None

    if before.get("dependencies"):
        current_id = before["dependencies"][0]
        if any(current_id.startswith(prefix) for prefix in DISALLOWED_EXTERNAL_PREFIXES):
            install = subprocess.run(
                ["install_name_tool", "-id", FRAMEWORK_DYLIB_ID, str(framework_dylib)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            install_name_result = {
                "returncode": install.returncode,
                "stdout_tail": install.stdout[-1000:],
                "stderr_tail": install.stderr[-1000:],
            }

            sign = subprocess.run(
                ["codesign", "--force", "--sign", "-", str(framework_dylib)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            codesign_result = {
                "returncode": sign.returncode,
                "stdout_tail": sign.stdout[-1000:],
                "stderr_tail": sign.stderr[-1000:],
            }

            verify = subprocess.run(
                ["codesign", "--verify", "--verbose=2", str(framework_dylib)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            verify_result = {
                "returncode": verify.returncode,
                "stdout_tail": verify.stdout[-1000:],
                "stderr_tail": verify.stderr[-1000:],
            }

            changed = install.returncode == 0

    after = otool_deps(framework_dylib)

    return {
        "target": rel(framework_dylib),
        "desired_id": FRAMEWORK_DYLIB_ID,
        "changed": changed,
        "before": before,
        "install_name_tool": install_name_result,
        "codesign": codesign_result,
        "codesign_verify": verify_result,
        "after": after,
    }


def tree_digest(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {
            "root": rel(root),
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "tree_sha256": None,
        }

    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    h = hashlib.sha256()
    total = 0

    for file_path in files:
        relative = file_path.relative_to(root).as_posix()
        size = file_path.stat().st_size
        file_hash = sha256_file(file_path)
        total += size
        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("ascii"))
        h.update(b"\0")
        h.update(file_hash.encode("ascii"))
        h.update(b"\n")

    return {
        "root": rel(root),
        "exists": True,
        "file_count": len(files),
        "total_bytes": total,
        "tree_sha256": h.hexdigest(),
    }


def selected_file_inventory() -> dict[str, Any]:
    inventory: dict[str, Any] = {}
    for name, path in EXPECTED_FILES.items():
        state = path_state(path)
        if path.exists() and path.is_file() and not path.is_symlink():
            state["sha256"] = sha256_file(path)
        inventory[name] = state
    return inventory


def git_generated_staging_guard() -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    staged = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    generated = [
        item
        for item in staged
        if item.startswith(GENERATED_PATH_PREFIXES)
    ]
    return {
        "returncode": proc.returncode,
        "staged_files": staged,
        "generated_staged_files": generated,
        "generated_runtime_staged": bool(generated),
        "stderr_tail": proc.stderr[-1000:],
    }


def scan_business_context() -> bool:
    scan_paths = [
        ROOT / "scripts/aion_voice_release_manifest_o24i.py",
        ROOT / "backend/tests/workflow_capsules/test_aion_o24i_voice_release_manifest_lock.py",
    ]
    blob = "\n".join(path.read_text(encoding="utf-8") for path in scan_paths if path.exists())
    return any(token in blob for token in FORBIDDEN_BUSINESS_TOKENS)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_manifests: dict[str, Any] = {}
    for name, path in SOURCE_MANIFESTS.items():
        source_manifests[name] = {
            "path": rel(path),
            "exists": path.exists(),
            "data": read_json(path) if path.exists() else None,
        }

    framework_id_hardening = harden_framework_dylib_id()
    file_inventory = selected_file_inventory()
    app_python_otool = otool_deps(APP_PYTHON)
    app_python3_otool = otool_deps(APP_VOICE_ROOT / "python/bin/python3")
    app_python312_otool = otool_deps(APP_VOICE_ROOT / "python/bin/python3.12")
    framework_otool = otool_deps(APP_VOICE_ROOT / "python/Frameworks/Python.framework/Versions/3.12/Python")

    digest = tree_digest(APP_VOICE_ROOT)
    staging_guard = git_generated_staging_guard()

    prereq_ready = {
        "o24f_release_ready": bool((source_manifests["o24f"]["data"] or {}).get("release_ready")),
        "o24g_release_ready": bool((source_manifests["o24g"]["data"] or {}).get("release_ready")),
        "o24h_release_ready": bool((source_manifests["o24h"]["data"] or {}).get("release_ready")),
        "o24h_tts_ok": bool((source_manifests["o24h"]["data"] or {}).get("tts_ok")),
        "o24h_stt_ok": bool((source_manifests["o24h"]["data"] or {}).get("stt_ok")),
    }

    release_blockers: list[str] = []

    if not APP_VOICE_ROOT.exists():
        release_blockers.append("app_voice_root_missing")
    if not APP_PYTHON.exists():
        release_blockers.append("app_python_missing")
    if APP_PYTHON.is_symlink():
        release_blockers.append("app_python_is_symlink")
    if not APP_WORKER.exists():
        release_blockers.append("app_local_worker_missing")

    missing_expected = [
        name
        for name, state in file_inventory.items()
        if not state["exists"]
    ]
    if missing_expected:
        release_blockers.append("expected_bundle_files_missing")

    external_deps = (
        app_python_otool["external_dependencies"]
        + app_python3_otool["external_dependencies"]
        + app_python312_otool["external_dependencies"]
        + framework_otool["external_dependencies"]
    )
    if external_deps:
        release_blockers.append("external_native_dependencies_present")

    if not all(prereq_ready.values()):
        release_blockers.append("prerequisite_voice_locks_not_release_ready")

    if staging_guard["generated_runtime_staged"]:
        release_blockers.append("generated_runtime_staged")

    business_context_hardcoded = scan_business_context()
    if business_context_hardcoded:
        release_blockers.append("business_context_hardcoded")

    manifest = {
        "ok": not release_blockers,
        "phase": "O24I",
        "purpose": "create_release_manifest_and_packaging_digest_for_app_local_voice_runtime",
        "status": "voice_release_manifest_and_digest_created",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "app_worker": rel(APP_WORKER),
        "source_manifests": {
            name: {
                "path": value["path"],
                "exists": value["exists"],
                "ok": (value["data"] or {}).get("ok"),
                "release_ready": (value["data"] or {}).get("release_ready"),
                "release_blockers": (value["data"] or {}).get("release_blockers"),
            }
            for name, value in source_manifests.items()
        },
        "prerequisite_ready": prereq_ready,
        "file_inventory": file_inventory,
        "framework_id_hardening": framework_id_hardening,
        "native_dependency_checks": {
            "app_python": app_python_otool,
            "app_python3": app_python3_otool,
            "app_python312": app_python312_otool,
            "python_framework_dylib": framework_otool,
        },
        "packaging_digest": digest,
        "git_generated_staging_guard": staging_guard,
        "release_ready": not release_blockers,
        "release_blockers": release_blockers,
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_transformers_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "business_context_hardcoded": business_context_hardcoded,
        "next_step": {
            "wire_app_startup_to_app_local_worker": True,
            "then_create_final_voice_runtime_release_gate": True,
        },
    }

    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
