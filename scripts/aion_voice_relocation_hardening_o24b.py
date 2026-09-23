from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE_APP = ROOT / "desktop/mac/Tessaris.app"
SOURCE_VOICE_ROOT = SOURCE_APP / "Contents/Resources/voice"
SOURCE_APP_PYTHON = SOURCE_VOICE_ROOT / "python/bin/python"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24b"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RELOCATED_ROOT = OUT_DIR / "relocated_app"
RELOCATED_APP = RELOCATED_ROOT / "Tessaris.app"
RELOCATED_VOICE_ROOT = RELOCATED_APP / "Contents/Resources/voice"
RELOCATED_APP_PYTHON = RELOCATED_VOICE_ROOT / "python/bin/python"

MANIFEST = OUT_DIR / "relocation_hardening_manifest.json"

RELOCATION_TEST_OUTPUT_PATH = ".runtime/voice_runtime_tests/o24b/relocated_app"

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


def copy_relocated_app() -> dict:
    if not SOURCE_APP.exists():
        raise RuntimeError(f"Missing source app bundle: {SOURCE_APP}")

    if not SOURCE_APP_PYTHON.exists():
        raise RuntimeError(f"Missing source app voice python. Run O24A first: {SOURCE_APP_PYTHON}")

    if RELOCATED_APP.exists():
        shutil.rmtree(RELOCATED_APP)

    RELOCATED_ROOT.mkdir(parents=True, exist_ok=True)

    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".DS_Store",
    )

    shutil.copytree(SOURCE_APP, RELOCATED_APP, symlinks=True, ignore=ignore)

    return {
        "source_app": rel(SOURCE_APP),
        "source_voice_root": rel(SOURCE_VOICE_ROOT),
        "source_python": rel(SOURCE_APP_PYTHON),
        "relocated_app": rel(RELOCATED_APP),
        "relocated_voice_root": rel(RELOCATED_VOICE_ROOT),
        "relocated_python": rel(RELOCATED_APP_PYTHON),
        "relocated_python_exists": RELOCATED_APP_PYTHON.exists(),
    }


def file_state(path: Path) -> dict:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "realpath": str(path.resolve()) if path.exists() else None,
    }


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
    return parse_json_from_result(run([str(RELOCATED_APP_PYTHON), "-c", code]))


def packaged_readiness_probe() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(RELOCATED_VOICE_ROOT),
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


def worker_bundle_probe() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(RELOCATED_VOICE_ROOT),
            "AION_KOKORO_MODEL_PATH": str(RELOCATED_VOICE_ROOT / "kokoro/kokoro-v1_0.pth"),
            "AION_KOKORO_CONFIG_PATH": str(RELOCATED_VOICE_ROOT / "kokoro/config.json"),
            "AION_KOKORO_VOICE_PATH": str(RELOCATED_VOICE_ROOT / "kokoro/voices/af_heart.pt"),
            "AION_SPACY_MODEL_PATH": str(RELOCATED_VOICE_ROOT / "spacy/en_core_web_sm"),
            "AION_WHISPER_MODEL_PATH": str(RELOCATED_VOICE_ROOT / "whisper/base"),
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
                str(RELOCATED_APP_PYTHON),
                str(ROOT / "scripts/aion_voice_worker.py"),
                "aion-o23i-bundle-probe",
            ],
            env=env,
        )
    )


def asset_probe() -> dict:
    assets = {}

    for name, relative in REQUIRED_ASSETS.items():
        assets[name] = file_state(RELOCATED_VOICE_ROOT / relative)

    return assets


def contains_original_app_voice_root(payload: object) -> bool:
    original = str(SOURCE_VOICE_ROOT)
    original_rel = rel(SOURCE_VOICE_ROOT)
    blob = json.dumps(payload, sort_keys=True)
    return original in blob or original_rel in blob


def main() -> int:
    copy_state = copy_relocated_app()
    py_state = file_state(RELOCATED_APP_PYTHON)
    assets = asset_probe()
    py_probe = python_probe()
    readiness = packaged_readiness_probe()
    worker = worker_bundle_probe()

    relocated_path_used = (
        readiness.get("bundle_root") == rel(RELOCATED_VOICE_ROOT)
        and readiness.get("python") == rel(RELOCATED_APP_PYTHON)
        and worker.get("python") == str(RELOCATED_APP_PYTHON)
    )

    manifest = {
        "ok": True,
        "phase": "O24B",
        "purpose": "prove_tessaris_app_voice_runtime_survives_relocation",
        "status": "relocated_app_voice_runtime_candidate_tested",
        "source": copy_state,
        "relocated_python_state": py_state,
        "assets": assets,
        "python_probe": py_probe,
        "packaged_readiness": readiness,
        "worker_bundle_probe": worker,
        "relocated_path_used": relocated_path_used,
        "source_voice_root_leaked_into_runtime_probe": contains_original_app_voice_root(
            {
                "python_probe": py_probe,
                "packaged_readiness": readiness,
                "worker_bundle_probe": worker,
            }
        ),
        "release_notes": {
            "heavy_relocated_app_runtime_is_test_output": True,
            "heavy_relocated_app_runtime_should_not_be_committed": True,
            "repo_worker_script_still_used_for_probe": True,
            "next_step_should_embed_app_local_worker_entrypoint": True,
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
        RELOCATED_APP_PYTHON.exists(),
        py_probe.get("returncode") == 0,
        py_probe.get("version_info", [0, 0])[0:2] == [3, 12],
        all(item.get("found") is True for item in py_probe.get("imports", {}).values()),
        all(item.get("exists") is True for item in assets.values()),
        readiness.get("returncode") == 0,
        readiness.get("ok") is True,
        worker.get("returncode") == 0,
        worker.get("ok") is True,
        relocated_path_used is True,
        manifest["source_voice_root_leaked_into_runtime_probe"] is False,
    ]

    manifest["ok"] = all(checks)

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
