from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON = APP_VOICE_ROOT / "python/bin/python"
SITE_PACKAGES = APP_VOICE_ROOT / "python/lib/python3.12/site-packages"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24d"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "native_dependency_audit_manifest.json"

EXTERNAL_PREFIXES = [
    "/opt/homebrew",
    "/usr/local",
    "/Library/Frameworks",
    "/Applications/Xcode.app",
]

SYSTEM_PREFIXES_ALLOWED_FOR_MACOS = [
    "/usr/lib",
    "/System/Library",
]

NATIVE_SUFFIXES = [
    ".so",
    ".dylib",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
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


def otool_l(path: Path) -> dict:
    result = run(["otool", "-L", str(path)])

    deps: list[str] = []
    external: list[str] = []
    system: list[str] = []
    relative: list[str] = []

    if result["returncode"] == 0:
        for line in result["stdout"].splitlines()[1:]:
            dep = line.strip().split(" ", 1)[0].strip()
            if not dep:
                continue

            deps.append(dep)

            if dep.startswith("@rpath") or dep.startswith("@loader_path") or dep.startswith("@executable_path"):
                relative.append(dep)
            elif any(dep.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
                external.append(dep)
            elif any(dep.startswith(prefix) for prefix in SYSTEM_PREFIXES_ALLOWED_FOR_MACOS):
                system.append(dep)

    return {
        "path": rel(path),
        "exists": path.exists(),
        "is_symlink": path.is_symlink(),
        "realpath": str(path.resolve()) if path.exists() else None,
        "otool_returncode": result["returncode"],
        "dependencies": deps,
        "external_dependencies": external,
        "system_dependencies": system,
        "relative_dependencies": relative,
        "stderr_tail": result["stderr_tail"],
    }


def collect_native_files() -> list[Path]:
    files: list[Path] = []

    if APP_PYTHON.exists():
        files.append(APP_PYTHON)

    if SITE_PACKAGES.exists():
        for current, _dirs, names in os.walk(SITE_PACKAGES):
            for name in names:
                path = Path(current) / name
                if any(name.endswith(suffix) for suffix in NATIVE_SUFFIXES):
                    files.append(path)

    unique = []
    seen = set()

    for path in files:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)

    return unique


def main() -> int:
    native_files = collect_native_files()

    audited = []
    external_dependency_records = []

    for path in native_files:
        state = otool_l(path)
        audited.append(state)

        if state["is_symlink"]:
            resolved = state.get("realpath") or ""
            if any(resolved.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
                external_dependency_records.append(
                    {
                        "path": state["path"],
                        "kind": "symlink_to_external_runtime",
                        "target": resolved,
                    }
                )

        for dep in state["external_dependencies"]:
            external_dependency_records.append(
                {
                    "path": state["path"],
                    "kind": "native_external_dependency",
                    "target": dep,
                }
            )

    release_blockers = []

    if not APP_PYTHON.exists():
        release_blockers.append("missing_app_python")

    if external_dependency_records:
        release_blockers.append("external_native_dependencies_present")

    if APP_PYTHON.is_symlink():
        release_blockers.append("app_python_symlink_present")

    manifest = {
        "ok": True,
        "phase": "O24D",
        "purpose": "audit_native_binary_dependencies_for_packaged_voice_runtime",
        "status": "native_dependency_audit_complete_release_blockers_recorded",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "site_packages": rel(SITE_PACKAGES),
        "native_file_count": len(native_files),
        "audited_count": len(audited),
        "external_dependency_count": len(external_dependency_records),
        "external_dependency_records": external_dependency_records[:200],
        "audited_native_files_sample": audited[:50],
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "required_fix": {
            "must_embed_real_python_runtime_not_homebrew_symlink": True,
            "must_rewrite_or_bundle_external_dylibs": True,
            "must_use_app_local_paths_for_packaged_voice_runtime": True,
            "must_re_run_packaged_readiness_after_rewrite": True,
            "must_re_run_relocation_hardening_after_rewrite": True,
        },
        "allowed_system_dependencies": SYSTEM_PREFIXES_ALLOWED_FOR_MACOS,
        "disallowed_external_prefixes": EXTERNAL_PREFIXES,
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
