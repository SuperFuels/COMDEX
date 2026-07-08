from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_PATH = ROOT / "desktop/mac/voice/manifest.o23a.json"

STAGING_ROOT = ROOT / "desktop/mac/voice_bundle_staging"
VOICE_ROOT = STAGING_ROOT / "voice"
KOKORO_ROOT = VOICE_ROOT / "kokoro"
KOKORO_VOICES = KOKORO_ROOT / "voices"
WHISPER_ROOT = VOICE_ROOT / "whisper/base"
SPACY_ROOT = VOICE_ROOT / "spacy/en_core_web_sm"
RUNTIME_ROOT = VOICE_ROOT / "runtime"
PYTHON_ROOT = VOICE_ROOT / "python"
MANIFEST_PATH = VOICE_ROOT / "manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def copy_file(src: Path, dst: Path) -> dict[str, Any]:
    if not src.exists() or not src.is_file():
        raise RuntimeError(f"Missing source file: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "source": str(src),
        "target": str(dst.relative_to(ROOT)),
        "size_bytes": dst.stat().st_size,
        "sha256": sha256_file(dst),
    }


def copy_tree(src: Path, dst: Path) -> dict[str, Any]:
    if not src.exists() or not src.is_dir():
        raise RuntimeError(f"Missing source directory: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    shutil.copytree(src, dst, ignore=ignore)

    file_count = 0
    total_bytes = 0
    digest = hashlib.sha256()

    for file in sorted(p for p in dst.rglob("*") if p.is_file()):
        rel = str(file.relative_to(dst))
        digest.update(rel.encode("utf-8"))
        digest.update(sha256_file(file).encode("utf-8"))
        file_count += 1
        total_bytes += file.stat().st_size

    return {
        "source": str(src),
        "target": str(dst.relative_to(ROOT)),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "tree_sha256": digest.hexdigest(),
    }


def first_file(items: list[dict[str, Any]], suffix: str | None = None) -> Path:
    for item in items:
        p = Path(item["path"])
        if item.get("is_file") and p.exists():
            if suffix is None or str(p).endswith(suffix):
                return p
    raise RuntimeError(f"No matching file found for suffix={suffix!r}")


def first_dir(items: list[dict[str, Any]], required_name: str | None = None) -> Path:
    for item in items:
        p = Path(item["path"])
        if item.get("is_dir") and p.exists():
            if required_name is None or p.name == required_name:
                return p
    raise RuntimeError(f"No matching directory found for required_name={required_name!r}")


def find_faster_whisper_base_snapshot(discovery: dict[str, Any]) -> Path:
    candidates = discovery["assets"].get("whisper_base", [])
    for item in candidates:
        p = Path(item["path"])
        if p.exists() and p.is_dir() and p.name.startswith("models--Systran--faster-whisper-base"):
            snapshots = p / "snapshots"
            if snapshots.exists():
                dirs = [d for d in snapshots.iterdir() if d.is_dir()]
                if dirs:
                    return sorted(dirs)[-1]
    raise RuntimeError("Could not find Systran faster-whisper-base snapshot directory.")


def main() -> int:
    if not DISCOVERY_PATH.exists():
        raise RuntimeError("Missing O23A discovery manifest. Run scripts/aion_voice_asset_discovery.py first.")

    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))

    for d in [
        VOICE_ROOT,
        KOKORO_ROOT,
        KOKORO_VOICES,
        WHISPER_ROOT,
        SPACY_ROOT.parent,
        RUNTIME_ROOT,
        PYTHON_ROOT,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    kokoro_model_src = first_file(discovery["assets"]["kokoro_model"], "kokoro-v1_0.pth")
    kokoro_voice_src = first_file(discovery["assets"]["kokoro_voice_af_heart"], "af_heart.pt")

    kokoro_config_src = None
    for item in discovery["assets"]["kokoro_config"]:
        p = Path(item["path"])
        if p.exists() and p.is_file() and "models--hexgrad--Kokoro-82M" in str(p):
            kokoro_config_src = p
            break
    if kokoro_config_src is None:
        raise RuntimeError("Could not find Kokoro config.json from hexgrad/Kokoro-82M.")

    spacy_src = first_dir(discovery["assets"]["spacy_en_core_web_sm"], "en_core_web_sm")
    whisper_src = find_faster_whisper_base_snapshot(discovery)

    copied = {
        "kokoro_model": copy_file(kokoro_model_src, KOKORO_ROOT / "kokoro-v1_0.pth"),
        "kokoro_voice_af_heart": copy_file(kokoro_voice_src, KOKORO_VOICES / "af_heart.pt"),
        "kokoro_config": copy_file(kokoro_config_src, KOKORO_ROOT / "config.json"),
        "spacy_en_core_web_sm": copy_tree(spacy_src, SPACY_ROOT),
        "faster_whisper_base": copy_tree(whisper_src, WHISPER_ROOT),
    }

    manifest = {
        "ok": True,
        "phase": "O23B_O23C_O23D",
        "purpose": "stage_app_local_voice_assets_for_future_tessaris_app_bundle",
        "bundle_root": str(VOICE_ROOT.relative_to(ROOT)),
        "source_discovery_manifest": str(DISCOVERY_PATH.relative_to(ROOT)),
        "copied": copied,
        "expected_packaged_paths": {
            "app_voice_root": "Tessaris.app/Contents/Resources/voice",
            "kokoro_model": "Tessaris.app/Contents/Resources/voice/kokoro/kokoro-v1_0.pth",
            "kokoro_config": "Tessaris.app/Contents/Resources/voice/kokoro/config.json",
            "kokoro_voice_af_heart": "Tessaris.app/Contents/Resources/voice/kokoro/voices/af_heart.pt",
            "spacy_model": "Tessaris.app/Contents/Resources/voice/spacy/en_core_web_sm",
            "whisper_base": "Tessaris.app/Contents/Resources/voice/whisper/base",
            "python_runtime": "Tessaris.app/Contents/Resources/voice/python/bin/python",
            "manifest": "Tessaris.app/Contents/Resources/voice/manifest.json",
        },
        "download_policy": {
            "packaged_mode_hidden_huggingface_downloads_allowed": False,
            "packaged_mode_hidden_spacy_downloads_allowed": False,
            "packaged_mode_hidden_elevenlabs_fallback_allowed": False,
            "staging_contains_required_model_assets": True,
        },
        "python_runtime_bundled_in_this_step": False,
        "python_runtime_next_step": "O23E",
        "business_context_hardcoded": False,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "phase": manifest["phase"],
        "bundle_root": manifest["bundle_root"],
        "kokoro_model": file_record(KOKORO_ROOT / "kokoro-v1_0.pth"),
        "kokoro_voice_af_heart": file_record(KOKORO_VOICES / "af_heart.pt"),
        "kokoro_config": file_record(KOKORO_ROOT / "config.json"),
        "spacy_en_core_web_sm": {
            "path": str(SPACY_ROOT.relative_to(ROOT)),
            "exists": SPACY_ROOT.exists(),
            "is_dir": SPACY_ROOT.is_dir(),
        },
        "faster_whisper_base": {
            "path": str(WHISPER_ROOT.relative_to(ROOT)),
            "exists": WHISPER_ROOT.exists(),
            "is_dir": WHISPER_ROOT.is_dir(),
        },
        "python_runtime_bundled_in_this_step": False,
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
