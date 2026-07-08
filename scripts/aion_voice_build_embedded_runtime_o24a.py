# AION O24A LOCK: embedded app runtime candidate builder.
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE_VENV = ROOT / ".venv_voice"
SOURCE_PYTHON = SOURCE_VENV / "bin" / "python"

STAGING_VOICE_ROOT = ROOT / "desktop/mac/voice_bundle_staging/voice"
APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON_ROOT = APP_VOICE_ROOT / "python"
APP_PYTHON = APP_PYTHON_ROOT / "bin" / "python"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24a"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "embedded_runtime_build_manifest.json"

FINAL_PACKAGED_PYTHON_PATH = "Tessaris.app/Contents/Resources/voice/python/bin/python"
FINAL_PACKAGED_PYTHON_RELATIVE = "python/bin/python"

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


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        "pip-selfcheck.json",
    )
    shutil.copytree(src, dst, symlinks=True, ignore=ignore)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_asset_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
    else:
        copy_file(src, dst)


def ensure_app_voice_assets() -> dict:
    copied = {}

    APP_VOICE_ROOT.mkdir(parents=True, exist_ok=True)

    for name, rel_path in REQUIRED_ASSETS.items():
        src = STAGING_VOICE_ROOT / rel_path
        dst = APP_VOICE_ROOT / rel_path
        copy_asset_tree(src, dst)
        copied[name] = {
            "source": rel(src),
            "target": rel(dst),
            "target_exists": dst.exists(),
            "is_file": dst.is_file(),
            "is_dir": dst.is_dir(),
        }

    readme = APP_VOICE_ROOT / "README.O24A.md"
    readme.write_text(
        "# AION O24A Embedded Voice Runtime Candidate\n\n"
        "This folder is generated locally by scripts/aion_voice_build_embedded_runtime_o24a.py.\n\n"
        "It is an app-bundle runtime candidate for Tessaris.app. The heavy runtime/assets are build outputs and should not be committed directly.\n\n"
        "The packaged runtime must pass startup readiness and no-hidden-download checks before release.\n",
        encoding="utf-8",
    )
    copied["readme"] = {
        "source": "generated",
        "target": rel(readme),
        "target_exists": readme.exists(),
        "is_file": readme.is_file(),
        "is_dir": readme.is_dir(),
    }

    return copied


def build_python_runtime() -> dict:
    if not SOURCE_PYTHON.exists():
        raise RuntimeError(f"Missing source voice Python: {SOURCE_PYTHON}")

    APP_PYTHON_ROOT.parent.mkdir(parents=True, exist_ok=True)
    copytree_clean(SOURCE_VENV, APP_PYTHON_ROOT)

    return {
        "source": rel(SOURCE_VENV),
        "target": rel(APP_PYTHON_ROOT),
        "python": rel(APP_PYTHON),
        "python_exists": APP_PYTHON.exists(),
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


def python_probe() -> dict:
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
    "executable": sys.executable,
    "version_info": list(sys.version_info[:3]),
    "imports": imports,
}}))
"""
    result = run([str(APP_PYTHON), "-c", code])
    try:
        payload = json.loads(result["stdout"].strip())
    except Exception:
        try:
            stdout = result["stdout"]
            start = stdout.index("{")
            end = stdout.rindex("}") + 1
            payload = json.loads(stdout[start:end])
        except Exception:
            payload = {
                "parse_error": True,
                "stdout_tail": result["stdout_tail"],
                "stderr_tail": result["stderr_tail"],
            }

    payload["returncode"] = result["returncode"]
    return payload


def readiness_probe() -> dict:
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
            str(ROOT / ".venv" / "bin" / "python"),
            "-c",
            "import json; from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness; print(json.dumps(voice_startup_readiness(mode='packaged').to_dict()))",
        ],
        env=env,
    )

    return parse_json_from_result(result)

def worker_bundle_probe() -> dict:
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
            "AION_ELEVENLABS_ENABLED": "false",
            "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
            "PYTHONPATH": str(ROOT),
        }
    )

    result = run(
        [
            str(APP_PYTHON),
            str(ROOT / "scripts/aion_voice_worker.py"),
            "aion-o23i-bundle-probe",
        ],
        env=env,
    )

    return parse_json_from_result(result)

def main() -> int:
    assets = ensure_app_voice_assets()
    runtime = build_python_runtime()
    py_probe = python_probe()
    readiness = readiness_probe()
    worker_probe = worker_bundle_probe()

    manifest = {
        "ok": True,
        "phase": "O24A",
        "purpose": "build_actual_tessaris_app_embedded_voice_runtime_candidate",
        "status": "local_app_bundle_runtime_candidate_built",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "source_venv": rel(SOURCE_VENV),
        "runtime": runtime,
        "assets": assets,
        "python_probe": py_probe,
        "packaged_readiness": readiness,
        "worker_bundle_probe": worker_probe,
        "release_notes": {
            "heavy_app_runtime_assets_should_not_be_committed_directly": True,
            "source_dev_venv_should_not_be_committed_directly": True,
            "candidate_uses_existing_proven_local_voice_runtime": True,
            "next_step_should_harden_relocation_and_release_packaging": True,
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
        APP_PYTHON.exists(),
        py_probe.get("returncode") == 0,
        py_probe.get("version_info", [0, 0])[0:2] == [3, 12],
        all(item.get("found") is True for item in py_probe.get("imports", {}).values()),
        readiness.get("returncode") == 0,
        readiness.get("ok") is True,
        worker_probe.get("returncode") == 0,
        worker_probe.get("ok") is True,
        all(item.get("target_exists") is True for item in assets.values()),
    ]

    manifest["ok"] = all(checks)

    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
