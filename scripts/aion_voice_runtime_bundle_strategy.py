from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE_VENV = ROOT / ".venv_voice"
VOICE_PYTHON = VOICE_VENV / "bin/python"

VOICE_ROOT = ROOT / "desktop/mac/voice_bundle_staging/voice"
PYTHON_ROOT = VOICE_ROOT / "python"
PYTHON_BIN = PYTHON_ROOT / "bin/python"

STRATEGY_MANIFEST = VOICE_ROOT / "python_runtime_manifest.o23e.json"
VOICE_MANIFEST = VOICE_ROOT / "manifest.json"

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


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_python(py: Path, code: str) -> dict:
    proc = subprocess.run(
        [str(py), "-c", code],
        cwd=str(ROOT),
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


def probe_python(py: Path) -> dict:
    code = f"""
import importlib.util
import json
import platform
import site
import sys

required = {REQUIRED_IMPORTS!r}
imports = {{}}

for name in required:
    spec = importlib.util.find_spec(name)
    imports[name] = {{
        "found": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
        "locations": [str(p) for p in (spec.submodule_search_locations or [])] if spec and spec.submodule_search_locations else [],
    }}

print(json.dumps({{
    "executable": sys.executable,
    "version": sys.version,
    "version_info": list(sys.version_info[:3]),
    "platform": platform.platform(),
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "site_packages": site.getsitepackages(),
    "imports": imports,
}}))
"""
    result = run_python(py, code)
    payload = json.loads(result["stdout"].strip().splitlines()[-1])
    payload["probe_returncode"] = result["returncode"]
    return payload


def directory_summary(path: Path) -> dict:
    if not path.exists():
        return {
            "path": str(path.relative_to(ROOT)),
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "tree_sha256": None,
        }

    h = hashlib.sha256()
    file_count = 0
    total_bytes = 0

    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = str(file.relative_to(path))
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        h.update(rel.encode("utf-8"))
        h.update((sha256_file(file) or "").encode("utf-8"))
        file_count += 1
        total_bytes += file.stat().st_size

    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "tree_sha256": h.hexdigest(),
    }


def write_staging_launcher() -> dict:
    (PYTHON_ROOT / "bin").mkdir(parents=True, exist_ok=True)

    launcher = """#!/usr/bin/env bash
# AION O23E staging launcher.
# Development/staging only: delegates to the proven local Python 3.12 voice runtime.
# Release packaging must replace this with an embedded or relocatable Python 3.12 runtime.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../../.." && pwd)"
exec "$ROOT/.venv_voice/bin/python" "$@"
"""
    PYTHON_BIN.write_text(launcher, encoding="utf-8")
    PYTHON_BIN.chmod(0o755)

    readme = """# AION Voice Python Runtime Staging

This folder is the target location for the future packaged voice runtime.

Current O23E status:
- The directory contract exists.
- The staging launcher delegates to the proven local .venv_voice/bin/python.
- The real release build must replace this launcher with an embedded or relocatable Python 3.12 runtime.
- .venv_voice/ must not be committed directly.

Expected final packaged path:
Tessaris.app/Contents/Resources/voice/python/bin/python
"""
    (PYTHON_ROOT / "README.md").write_text(readme, encoding="utf-8")

    return {
        "launcher": str(PYTHON_BIN.relative_to(ROOT)),
        "launcher_exists": PYTHON_BIN.exists(),
        "launcher_sha256": sha256_file(PYTHON_BIN),
        "readme": str((PYTHON_ROOT / "README.md").relative_to(ROOT)),
    }


def validate_launcher() -> dict:
    result = run_python(
        PYTHON_BIN,
        "import sys,json; print(json.dumps({'executable': sys.executable, 'version_info': list(sys.version_info[:3])}))",
    )
    payload = json.loads(result["stdout"].strip().splitlines()[-1])
    return {
        "ok": result["returncode"] == 0 and payload["version_info"][0:2] == [3, 12],
        "returncode": result["returncode"],
        "payload": payload,
        "stderr_tail": result["stderr"][-1000:],
    }


def update_voice_manifest() -> None:
    if VOICE_MANIFEST.exists():
        data = json.loads(VOICE_MANIFEST.read_text(encoding="utf-8"))
    else:
        data = {"ok": True, "phase": "O23B_O23C_O23D"}

    data["python_runtime_bundled_in_this_step"] = False
    data["python_runtime_strategy"] = {
        "phase": "O23E",
        "strategy_manifest": str(STRATEGY_MANIFEST.relative_to(ROOT)),
        "staging_python_launcher": str(PYTHON_BIN.relative_to(ROOT)),
        "release_requirement": "replace staging launcher with embedded or relocatable Python 3.12 runtime",
        "do_not_commit_dev_venv": True,
    }
    data["python_runtime_next_step"] = "O23F"
    data["business_context_hardcoded"] = False

    VOICE_MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    if not VOICE_PYTHON.exists():
        raise RuntimeError(f"Missing proven voice runtime: {VOICE_PYTHON}")

    source_probe = probe_python(VOICE_PYTHON)
    launcher = write_staging_launcher()
    launcher_validation = validate_launcher()

    source_is_py312 = source_probe["version_info"][0:2] == [3, 12]
    required_imports_ok = all(
        source_probe["imports"][name]["found"] is True
        for name in REQUIRED_IMPORTS
    )

    strategy = {
        "ok": bool(source_is_py312 and required_imports_ok and launcher_validation["ok"]),
        "phase": "O23E",
        "purpose": "define_and_stage_python_3_12_voice_runtime_bundle_strategy",
        "source_voice_runtime": {
            "path": str(VOICE_VENV.relative_to(ROOT)),
            "python": str(VOICE_PYTHON.relative_to(ROOT)),
            "probe": source_probe,
            "summary": directory_summary(VOICE_VENV),
            "commit_dev_venv_directly": False,
        },
        "staging_runtime": {
            "root": str(PYTHON_ROOT.relative_to(ROOT)),
            "python_launcher": launcher,
            "launcher_validation": launcher_validation,
            "is_final_release_runtime": False,
        },
        "release_runtime_requirement": {
            "final_path": "Tessaris.app/Contents/Resources/voice/python/bin/python",
            "must_be_python_3_12": True,
            "must_include_voice_dependencies": REQUIRED_IMPORTS,
            "must_be_relocatable_or_embedded": True,
            "must_not_require_terminal_pip_install": True,
            "must_not_require_hidden_downloads": True,
        },
        "allowed_runtime_build_methods": [
            "build clean Python 3.12 venv during release packaging",
            "copy a relocatable Python 3.12 runtime generated by build pipeline",
            "ship official Tessaris voice runtime artifact",
        ],
        "forbidden_runtime_build_methods": [
            "commit .venv_voice directly to normal git",
            "silently pip install dependencies on customer machine",
            "silently download model assets at first voice use",
            "silently fall back to ElevenLabs",
            "silently fall back to browser SpeechRecognition",
        ],
        "download_policy": {
            "packaged_mode_hidden_huggingface_downloads_allowed": False,
            "packaged_mode_hidden_spacy_downloads_allowed": False,
            "packaged_mode_hidden_elevenlabs_fallback_allowed": False,
        },
        "business_context_hardcoded": False,
    }

    STRATEGY_MANIFEST.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
    update_voice_manifest()

    print(json.dumps({
        "ok": strategy["ok"],
        "phase": "O23E",
        "source_python": str(VOICE_PYTHON.relative_to(ROOT)),
        "staging_python": str(PYTHON_BIN.relative_to(ROOT)),
        "source_is_python_3_12": source_is_py312,
        "required_imports_ok": required_imports_ok,
        "launcher_validation": launcher_validation,
        "strategy_manifest": str(STRATEGY_MANIFEST.relative_to(ROOT)),
        "updated_voice_manifest": str(VOICE_MANIFEST.relative_to(ROOT)),
        "commit_dev_venv_directly": False,
    }, indent=2))

    return 0 if strategy["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
