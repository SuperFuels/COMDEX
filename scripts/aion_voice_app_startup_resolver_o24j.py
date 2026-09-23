from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "desktop/mac/src/aion_voice_worker_runtime.js"
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24j"
MANIFEST = OUT_DIR / "app_startup_voice_worker_resolver_manifest.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
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


def parse_json(result: dict) -> dict:
    try:
        data = json.loads(result["stdout"])
    except Exception:
        data = {
            "parse_error": True,
            "stdout_tail": result.get("stdout_tail"),
            "stderr_tail": result.get("stderr_tail"),
        }
    data["returncode"] = result["returncode"]
    return data


def contains_forbidden_business_context() -> bool:
    text = HELPER.read_text(encoding="utf-8") + "\n" + Path(__file__).read_text(encoding="utf-8")
    forbidden = [
        "Home" + " Fixed",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jácar",
        "per" + "gola",
        "car" + "port",
        "vil" + "la",
        "trades" + "men",
    ]
    return any(token in text for token in forbidden)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    node_check = run(["node", "--check", str(HELPER)])
    probe_result = parse_json(run(["node", str(HELPER)]))

    release_blockers = []

    if node_check["returncode"] != 0:
        release_blockers.append("node_helper_syntax_failed")

    if probe_result.get("ok") is not True:
        release_blockers.append("startup_voice_worker_probe_failed")

    if probe_result.get("launchMode") != "app_local_packaged_worker":
        release_blockers.append("startup_not_using_app_local_packaged_worker")

    if not str(probe_result.get("python", "")).endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"):
        release_blockers.append("startup_python_not_app_local")

    if not str(probe_result.get("worker", "")).endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/runtime/scripts/aion_voice_worker.py"):
        release_blockers.append("startup_worker_not_app_local")

    if probe_result.get("pythonExists") is not True:
        release_blockers.append("startup_python_missing")

    if probe_result.get("workerExists") is not True:
        release_blockers.append("startup_worker_missing")

    env = probe_result.get("env") or {}
    if not (
        env.get("AION_VOICE_RUNTIME_MODE") == "packaged"
        and env.get("AION_VOICE_NO_HIDDEN_DOWNLOADS") == "true"
        and env.get("HF_HUB_OFFLINE") == "1"
        and env.get("TRANSFORMERS_OFFLINE") == "1"
        and env.get("HF_DATASETS_OFFLINE") == "1"
        and env.get("AION_ELEVENLABS_ENABLED") == "false"
        and env.get("AION_BROWSER_SPEECH_FALLBACK_ENABLED") == "false"
    ):
        release_blockers.append("startup_hidden_download_policy_not_locked")

    if contains_forbidden_business_context():
        release_blockers.append("business_context_hardcoded")

    manifest = {
        "ok": not release_blockers,
        "phase": "O24J",
        "purpose": "prove_electron_startup_resolves_app_local_voice_worker",
        "status": "electron_startup_voice_worker_resolver_locked",
        "helper": rel(HELPER),
        "node_check": {
            "returncode": node_check["returncode"],
            "stderr_tail": node_check["stderr_tail"],
        },
        "probe": probe_result,
        "release_ready": not release_blockers,
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
            "wire_main_app_to_resolver_when_startup_lifecycle_is_ready": True,
            "then_create_final_voice_runtime_release_gate": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
