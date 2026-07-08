from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import site
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o23a"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = OUT_DIR / "voice_asset_discovery_manifest.json"
PACKAGING_MANIFEST_PATH = ROOT / "desktop/mac/voice/manifest.o23a.json"

VOICE_PYTHON = ROOT / ".venv_voice/bin/python"


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path),
    }


def run_voice_python(code: str) -> dict[str, Any]:
    proc = subprocess.run(
        [str(VOICE_PYTHON), "-c", code],
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


def package_location(module_name: str) -> dict[str, Any]:
    code = f"""
import importlib.util, json
spec = importlib.util.find_spec({module_name!r})
payload = {{
    "module": {module_name!r},
    "found": spec is not None,
    "origin": getattr(spec, "origin", None) if spec else None,
    "submodule_search_locations": [str(p) for p in (spec.submodule_search_locations or [])] if spec and spec.submodule_search_locations else [],
}}
print(json.dumps(payload))
"""
    result = run_voice_python(code)
    try:
        payload = json.loads(result["stdout"].strip().splitlines()[-1])
    except Exception:
        payload = {
            "module": module_name,
            "found": False,
            "origin": None,
            "submodule_search_locations": [],
            "error": result,
        }
    return payload


def python_runtime_info() -> dict[str, Any]:
    code = """
import json, sys, site, platform
payload = {
    "executable": sys.executable,
    "version": sys.version,
    "version_info": list(sys.version_info[:3]),
    "platform": platform.platform(),
    "site_packages": site.getsitepackages(),
    "usersite": site.getusersitepackages(),
}
print(json.dumps(payload))
"""
    result = run_voice_python(code)
    return json.loads(result["stdout"].strip().splitlines()[-1])


def collect_hf_cache_candidates() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []

    roots = [
        Path(os.environ.get("HF_HOME", "")) if os.environ.get("HF_HOME") else None,
        home / ".cache/huggingface/hub",
        home / ".cache/huggingface",
    ]

    for root in roots:
        if root and root.exists():
            candidates.append(root)

    return candidates


def find_named_assets() -> dict[str, list[dict[str, Any]]]:
    search_roots: list[Path] = []

    for root in collect_hf_cache_candidates():
        search_roots.append(root)

    search_roots.extend([
        ROOT / ".runtime",
        ROOT / ".venv_voice",
        ROOT / "desktop/mac",
    ])

    names = {
        "kokoro_model": ["kokoro-v1_0.pth"],
        "kokoro_voice_af_heart": ["af_heart.pt"],
        "kokoro_config": ["config.json"],
        "spacy_en_core_web_sm": ["en_core_web_sm"],
        "whisper_base": ["base"],
        "whisper_small": ["small"],
    }

    found: dict[str, list[dict[str, Any]]] = {key: [] for key in names}

    for root in search_roots:
        if not root.exists():
            continue

        for key, targets in names.items():
            for target in targets:
                try:
                    if target in ["en_core_web_sm", "base", "small"]:
                        matches = [p for p in root.rglob(f"*{target}*") if p.exists()]
                    else:
                        matches = [p for p in root.rglob(target) if p.exists()]
                except Exception:
                    matches = []

                for match in matches[:20]:
                    info = file_info(match)
                    info["search_root"] = str(root)
                    found[key].append(info)

    # Deduplicate by path.
    for key, items in found.items():
        seen = set()
        deduped = []
        for item in items:
            p = item["path"]
            if p in seen:
                continue
            seen.add(p)
            deduped.append(item)
        found[key] = deduped

    return found


def main() -> int:
    if not VOICE_PYTHON.exists():
        raise RuntimeError(f"Missing voice python runtime: {VOICE_PYTHON}")

    runtime = python_runtime_info()

    modules = {
        name: package_location(name)
        for name in [
            "kokoro",
            "soundfile",
            "faster_whisper",
            "ctranslate2",
            "av",
            "torch",
            "spacy",
            "numpy",
        ]
    }

    assets = find_named_assets()

    required_summary = {
        "python_3_12_runtime": runtime["version_info"][0] == 3 and runtime["version_info"][1] == 12,
        "kokoro_package": modules["kokoro"]["found"],
        "soundfile_package": modules["soundfile"]["found"],
        "faster_whisper_package": modules["faster_whisper"]["found"],
        "ctranslate2_package": modules["ctranslate2"]["found"],
        "av_package": modules["av"]["found"],
        "torch_package": modules["torch"]["found"],
        "spacy_package": modules["spacy"]["found"],
        "kokoro_model_found": bool(assets["kokoro_model"]),
        "kokoro_voice_af_heart_found": bool(assets["kokoro_voice_af_heart"]),
        "kokoro_config_found": bool(assets["kokoro_config"]),
        "spacy_en_core_web_sm_found": bool(assets["spacy_en_core_web_sm"]),
        "whisper_base_or_small_found": bool(assets["whisper_base"] or assets["whisper_small"]),
    }

    packaging_targets = {
        "bundle_root": "Tessaris.app/Contents/Resources/voice",
        "python_runtime": "Tessaris.app/Contents/Resources/voice/python/bin/python",
        "kokoro_root": "Tessaris.app/Contents/Resources/voice/kokoro",
        "kokoro_model": "Tessaris.app/Contents/Resources/voice/kokoro/kokoro-v1_0.pth",
        "kokoro_voice_af_heart": "Tessaris.app/Contents/Resources/voice/kokoro/voices/af_heart.pt",
        "kokoro_config": "Tessaris.app/Contents/Resources/voice/kokoro/config.json",
        "spacy_model": "Tessaris.app/Contents/Resources/voice/spacy/en_core_web_sm",
        "whisper_model_root": "Tessaris.app/Contents/Resources/voice/whisper/base",
        "manifest": "Tessaris.app/Contents/Resources/voice/manifest.json",
    }

    manifest = {
        "ok": all(required_summary.values()),
        "phase": "O23A",
        "purpose": "discover_local_voice_assets_for_future_app_bundle",
        "runtime": runtime,
        "modules": modules,
        "assets": assets,
        "required_summary": required_summary,
        "packaging_targets": packaging_targets,
        "download_policy": {
            "packaged_mode_hidden_huggingface_downloads_allowed": False,
            "packaged_mode_hidden_spacy_downloads_allowed": False,
            "packaged_mode_hidden_elevenlabs_fallback_allowed": False,
            "development_cache_discovery_only": True,
        },
        "business_context_hardcoded": False,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    PACKAGING_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACKAGING_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
