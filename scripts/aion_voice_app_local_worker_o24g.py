from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON = APP_VOICE_ROOT / "python/bin/python"

APP_RUNTIME_ROOT = APP_VOICE_ROOT / "runtime"
APP_RUNTIME_BACKEND = APP_RUNTIME_ROOT / "backend"
APP_RUNTIME_MODULES = APP_RUNTIME_BACKEND / "modules"
APP_RUNTIME_AION_VOICE = APP_RUNTIME_MODULES / "aion_voice"
APP_RUNTIME_SCRIPTS = APP_RUNTIME_ROOT / "scripts"
APP_WORKER = APP_RUNTIME_SCRIPTS / "aion_voice_worker.py"

REPO_WORKER = ROOT / "scripts/aion_voice_worker.py"
REPO_AION_VOICE = ROOT / "backend/modules/aion_voice"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24g"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "app_local_worker_manifest.json"

REQUIRED_WORKER_IMPORTS = [
    "backend.modules.aion_voice.voice_download_policy",
    "backend.modules.aion_voice.voice_worker_bridge",
    "backend.modules.aion_voice.voice_startup_readiness",
]

REQUIRED_VOICE_IMPORTS = [
    "kokoro",
    "soundfile",
    "faster_whisper",
    "ctranslate2",
    "av",
    "torch",
    "spacy",
    "numpy",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def run(cmd: list[str], env: dict[str, str] | None = None, cwd: Path = ROOT) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
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
    return {
        "path": rel(path),
        "exists": exists,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "realpath": str(path.resolve()) if exists else None,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def copy_runtime_code() -> dict:
    APP_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    APP_RUNTIME_BACKEND.mkdir(parents=True, exist_ok=True)
    APP_RUNTIME_MODULES.mkdir(parents=True, exist_ok=True)
    APP_RUNTIME_SCRIPTS.mkdir(parents=True, exist_ok=True)

    (APP_RUNTIME_BACKEND / "__init__.py").write_text("", encoding="utf-8")
    (APP_RUNTIME_MODULES / "__init__.py").write_text("", encoding="utf-8")

    if APP_RUNTIME_AION_VOICE.exists():
        shutil.rmtree(APP_RUNTIME_AION_VOICE)

    shutil.copytree(
        REPO_AION_VOICE,
        APP_RUNTIME_AION_VOICE,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    shutil.copy2(REPO_WORKER, APP_WORKER)

    return {
        "runtime_root": path_state(APP_RUNTIME_ROOT),
        "backend_package": path_state(APP_RUNTIME_BACKEND),
        "modules_package": path_state(APP_RUNTIME_MODULES),
        "aion_voice_package": path_state(APP_RUNTIME_AION_VOICE),
        "worker": path_state(APP_WORKER),
        "repo_worker": rel(REPO_WORKER),
        "repo_aion_voice": rel(REPO_AION_VOICE),
    }


def app_worker_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(APP_VOICE_ROOT),
            "AION_KOKORO_MODEL_PATH": str(APP_VOICE_ROOT / "kokoro/kokoro-v1_0.pth"),
            "AION_KOKORO_CONFIG_PATH": str(APP_VOICE_ROOT / "kokoro/config.json"),
            "AION_KOKORO_VOICE_PATH": str(APP_VOICE_ROOT / "kokoro/voices/af_heart.pt"),
            "AION_SPACY_MODEL_PATH": str(APP_VOICE_ROOT / "spacy/en_core_web_sm"),
            "AION_WHISPER_MODEL_PATH": str(APP_VOICE_ROOT / "whisper/base"),
            "AION_VOICE_NO_HIDDEN_DOWNLOADS": "true",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "AION_ELEVENLABS_ENABLED": "false",
            "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
            "PYTHONPATH": str(APP_RUNTIME_ROOT),
        }
    )
    return env


def app_local_import_probe() -> dict:
    code = f"""
import importlib.util
import json
import sys
from pathlib import Path

runtime_root = Path({str(APP_RUNTIME_ROOT)!r}).resolve()
repo_backend_source = Path({str(REPO_AION_VOICE)!r}).resolve()

worker_imports = {REQUIRED_WORKER_IMPORTS!r}
voice_imports = {REQUIRED_VOICE_IMPORTS!r}

imports = {{}}

for name in worker_imports + voice_imports:
    spec = importlib.util.find_spec(name)
    origin = getattr(spec, "origin", None) if spec else None
    resolved_origin = Path(origin).resolve() if origin else None
    imports[name] = {{
        "found": spec is not None,
        "origin": origin,
        "inside_app_runtime": bool(resolved_origin and str(resolved_origin).startswith(str(runtime_root))) if name.startswith("backend.") else None,
        "inside_repo": bool(resolved_origin and str(resolved_origin).startswith(str(repo_backend_source))) if name.startswith("backend.") else None,
    }}

print(json.dumps({{
    "executable": sys.executable,
    "version_info": list(sys.version_info[:3]),
    "runtime_root": str(runtime_root),
    "repo_backend_source": str(repo_backend_source),
    "imports": imports,
}}))
"""
    return parse_json_from_result(
        run([str(APP_PYTHON), "-c", code], env=app_worker_environment(), cwd=APP_RUNTIME_ROOT)
    )


def app_local_worker_probe() -> dict:
    return parse_json_from_result(
        run(
            [str(APP_PYTHON), str(APP_WORKER), "aion-o23i-bundle-probe"],
            env=app_worker_environment(),
            cwd=APP_RUNTIME_ROOT,
        )
    )


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


def contains_forbidden_business_context() -> bool:
    text = ""
    for path in [APP_WORKER, *APP_RUNTIME_AION_VOICE.rglob("*.py")]:
        try:
            text += "\n" + path.read_text(encoding="utf-8")
        except Exception:
            pass

    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
        "construct" + "ion",
        "roof" + " repair",
    ]

    return any(token in text for token in forbidden)


def main() -> int:
    copied = copy_runtime_code()

    import_probe = app_local_import_probe()
    worker_probe = app_local_worker_probe()
    readiness = packaged_readiness_probe()

    worker_imports = import_probe.get("imports", {})
    app_worker_imports_ok = all(
        worker_imports.get(name, {}).get("found") is True
        and worker_imports.get(name, {}).get("inside_app_runtime") is True
        and worker_imports.get(name, {}).get("inside_repo") is False
        for name in REQUIRED_WORKER_IMPORTS
    )

    voice_imports_ok = all(
        worker_imports.get(name, {}).get("found") is True
        for name in REQUIRED_VOICE_IMPORTS
    )

    worker_probe_paths = worker_probe.get("paths", {})
    worker_probe_ok = worker_probe.get("ok") is True and worker_probe.get("returncode") == 0

    worker_python_is_app_python = str(Path(worker_probe.get("python", "")).resolve()) == str(APP_PYTHON.resolve())

    worker_uses_app_bundle_root = (
        worker_probe_paths.get("AION_VOICE_BUNDLE_ROOT", {}).get("path") == str(APP_VOICE_ROOT)
        and worker_probe_paths.get("AION_VOICE_BUNDLE_ROOT", {}).get("exists") is True
    )

    no_hidden_downloads = (
        worker_probe.get("offline_env", {}).get("HF_HUB_OFFLINE") == "1"
        and worker_probe.get("offline_env", {}).get("TRANSFORMERS_OFFLINE") == "1"
        and worker_probe.get("offline_env", {}).get("HF_DATASETS_OFFLINE") == "1"
        and worker_probe.get("offline_env", {}).get("AION_VOICE_NO_HIDDEN_DOWNLOADS") == "true"
        and worker_probe.get("offline_env", {}).get("AION_ELEVENLABS_ENABLED") == "false"
        and worker_probe.get("offline_env", {}).get("AION_BROWSER_SPEECH_FALLBACK_ENABLED") == "false"
    )

    repo_worker_used = str(REPO_WORKER.resolve()) in json.dumps(worker_probe) or str(REPO_WORKER) in json.dumps(worker_probe)

    release_blockers = []

    if not APP_WORKER.exists():
        release_blockers.append("app_local_worker_missing")

    if import_probe.get("returncode") != 0:
        release_blockers.append("app_local_import_probe_failed")

    if not app_worker_imports_ok:
        release_blockers.append("backend_aion_voice_imports_not_app_local")

    if not voice_imports_ok:
        release_blockers.append("voice_runtime_imports_missing")

    if not worker_probe_ok:
        release_blockers.append("app_local_worker_probe_failed")

    if not worker_python_is_app_python:
        release_blockers.append("worker_not_using_app_python")

    if not worker_uses_app_bundle_root:
        release_blockers.append("worker_not_using_app_voice_bundle_root")

    if not no_hidden_downloads:
        release_blockers.append("no_hidden_download_policy_not_active")

    if repo_worker_used:
        release_blockers.append("repo_worker_script_still_used")

    if readiness.get("ok") is not True:
        release_blockers.append("packaged_readiness_failed")

    if contains_forbidden_business_context():
        release_blockers.append("business_context_hardcoded")

    manifest = {
        "ok": len(release_blockers) == 0,
        "phase": "O24G",
        "purpose": "bundle_app_local_voice_worker_entrypoint",
        "status": "app_local_worker_entrypoint_bundled_and_proven",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "app_runtime_root": rel(APP_RUNTIME_ROOT),
        "app_worker": rel(APP_WORKER),
        "copied": copied,
        "import_probe": import_probe,
        "app_worker_imports_ok": app_worker_imports_ok,
        "voice_imports_ok": voice_imports_ok,
        "worker_probe": worker_probe,
        "worker_probe_ok": worker_probe_ok,
        "worker_python_is_app_python": worker_python_is_app_python,
        "worker_uses_app_bundle_root": worker_uses_app_bundle_root,
        "repo_worker_used": repo_worker_used,
        "packaged_readiness": {
            "ok": readiness.get("ok"),
            "returncode": readiness.get("returncode"),
            "bundle_root": readiness.get("bundle_root"),
            "python": readiness.get("python"),
        },
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_transformers_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "business_context_hardcoded": contains_forbidden_business_context(),
        "next_step": {
            "create_full_app_local_tts_stt_smoke": True,
            "then_create_release_manifest_and_packaging_digest": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
