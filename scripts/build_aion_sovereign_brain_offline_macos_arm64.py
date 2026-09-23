#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from scripts.build_aion_sovereign_brain_bootstrap import PACKAGING, build


REPO = Path(__file__).resolve().parents[1]
DIST = REPO / "dist"
OLLAMA = Path("/opt/homebrew/Cellar/ollama/0.20.2/bin/ollama")
MODEL_ROOT = Path.home() / ".ollama" / "models"
MODEL_MANIFEST = MODEL_ROOT / "manifests/registry.ollama.ai/library/gemma3/1b"
PYTHON_VERSION = "3.13.15"
PYTHON_BUILD = "20260901"
PYTHON_ARCHIVE = f"cpython-{PYTHON_VERSION}+{PYTHON_BUILD}-aarch64-apple-darwin-install_only.tar.gz"
PYTHON_URL = (
    f"https://github.com/astral-sh/python-build-standalone/releases/download/{PYTHON_BUILD}/"
    f"cpython-{PYTHON_VERSION}%2B{PYTHON_BUILD}-aarch64-apple-darwin-install_only.tar.gz"
)
PYTHON_SHA256 = "b9054a9d3d54f4cb5573d44907fddb29874b08909bde73f29f2868cf872223ee"
CACHE = DIST / "offline-build-cache"


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verified_download(url: str, target: Path, digest: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and sha(target) == digest:
        return target
    temporary = target.with_suffix(target.suffix + ".partial")
    temporary.unlink(missing_ok=True)
    urllib.request.urlretrieve(url, temporary)
    actual = sha(temporary)
    if actual != digest:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded runtime digest mismatch: expected {digest}, received {actual}")
    temporary.replace(target)
    return target


def build_offline() -> Path:
    if not OLLAMA.is_file() or not MODEL_MANIFEST.is_file():
        raise RuntimeError("The qualified Ollama arm64 runtime and Gemma 3 1B cache are required")
    portable_python = verified_download(PYTHON_URL, CACHE / PYTHON_ARCHIVE, PYTHON_SHA256)
    base = build()
    release = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    version = str(release["version"])
    output = DIST / f"aion-sovereign-brain-offline-macos-arm64-{version}.zip"
    with tempfile.TemporaryDirectory(prefix="aion-offline-") as temporary:
        root = Path(temporary) / f"AION Sovereign Brain Offline macOS arm64 {version}"
        with zipfile.ZipFile(base) as archive:
            archive.extractall(root / "bootstrap")
        inner = next((root / "bootstrap").iterdir())
        wheelhouse = inner / "wheelhouse"
        wheelhouse.mkdir()
        offline_requirements = PACKAGING / "requirements-offline-macos-arm64-py313.txt"
        shutil.copy2(offline_requirements, inner / offline_requirements.name)
        subprocess.run([
            str(REPO / ".venv/bin/python"), "-m", "pip", "download", "--quiet",
            "--only-binary=:all:", "--platform", "macosx_11_0_arm64", "--python-version", "313",
            "--implementation", "cp", "--dest", str(wheelhouse),
            "-r", str(offline_requirements),
        ], check=True)
        with tarfile.open(portable_python, "r:gz") as archive:
            members = archive.getmembers()
            if not members or any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
                raise RuntimeError("Portable Python archive contains an unsafe path")
            archive.extractall(inner / "offline-python", filter="data")
        python_root = inner / "offline-python/python"
        if not (python_root / "bin/python3").is_file():
            raise RuntimeError("Portable Python archive did not contain python/bin/python3")
        for cache in list(python_root.rglob("__pycache__")):
            shutil.rmtree(cache)
        for bytecode in python_root.rglob("*.pyc"):
            bytecode.unlink()
        runtime = inner / "offline-runtime"
        runtime.mkdir()
        shutil.copy2(OLLAMA, runtime / "ollama")
        shutil.copy2(OLLAMA.parents[1] / "LICENSE", runtime / "OLLAMA-LICENSE.txt")
        (runtime / "ollama").chmod(0o755)
        shutil.copy2(PACKAGING / "offline-local-proof.py", inner / "offline-local-proof.py")
        shutil.copy2(PACKAGING / "offline-verify.py", inner / "offline-verify.py")
        model_target = inner / "offline-models/manifests/registry.ollama.ai/library/gemma3"
        model_target.mkdir(parents=True)
        shutil.copy2(MODEL_MANIFEST, model_target / "1b")
        manifest = json.loads(MODEL_MANIFEST.read_text())
        blobs = inner / "offline-models/blobs"
        blobs.mkdir(parents=True)
        for descriptor in [manifest["config"], *manifest["layers"]]:
            digest = descriptor["digest"].replace(":", "-")
            shutil.copy2(MODEL_ROOT / f"blobs/{digest}", blobs / digest)
        launcher = inner / "Run Offline Proof.command"
        launcher.write_text(
            '#!/bin/zsh\nset -e\nROOT="${0:A:h}"\nunset OPENAI_API_KEY GEMINI_API_KEY ANTHROPIC_API_KEY\n'
            'export PYTHONDONTWRITEBYTECODE=1\n'
            'export OLLAMA_HOST=127.0.0.1:11455 OLLAMA_MODELS="$ROOT/offline-models" OLLAMA_NO_CLOUD=true\n'
            'export OLLAMA_LLM_LIBRARY=cpu OLLAMA_CONTEXT_LENGTH=512 OLLAMA_LOAD_TIMEOUT=10m\n'
            '"$ROOT/offline-runtime/ollama" serve >"$ROOT/offline-ollama.log" 2>&1 &\nPID=$!\ntrap "kill $PID 2>/dev/null || true" EXIT\n'
            'for i in {1..60}; do curl -fsS http://127.0.0.1:11455/api/tags >/dev/null && break; sleep 1; done\n'
            '"$ROOT/offline-python/python/bin/python3" "$ROOT/offline-local-proof.py"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
        setup_launcher = inner / "Set Up Pilot Offline.command"
        setup_launcher.write_text(
            '#!/bin/zsh\nset -e\nROOT="${0:A:h}"\ncd "$ROOT"\nexport PYTHONDONTWRITEBYTECODE=1\n'
            '"$ROOT/offline-python/python/bin/python3" "$ROOT/offline-verify.py"\n'
            'if [ ! -x .pilot-offline-venv/bin/python ]; then "$ROOT/offline-python/python/bin/python3" -m venv .pilot-offline-venv; '
            '.pilot-offline-venv/bin/python -m pip install --no-index --find-links "$ROOT/wheelhouse" '
            '-r "$ROOT/requirements-offline-macos-arm64-py313.txt"; fi\n'
            'exec .pilot-offline-venv/bin/python -m backend.modules.aion_business.runtime.sovereign_setup_service\n',
            encoding="utf-8",
        )
        setup_launcher.chmod(0o755)
        files = []
        for path in sorted(inner.rglob("*")):
            if path.is_file():
                files.append({"path": path.relative_to(inner).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
        evidence = {
            "schema_version": "aion.sovereign_offline_bundle.v1", "platform": "macos-arm64",
            "python": f"portable CPython {PYTHON_VERSION} ({PYTHON_BUILD})",
            "python_source": PYTHON_URL, "python_archive_sha256": PYTHON_SHA256,
            "local_runtime": "Ollama 0.20.2 arm64", "model": "gemma3:1b",
            "licences": {
                "python": "offline-python/python/lib/python3.13/LICENSE.txt",
                "ollama": "offline-runtime/OLLAMA-LICENSE.txt",
                "model": "embedded in the Ollama model manifest as application/vnd.ollama.image.license",
            },
            "provider_keys_required": False, "network_required_after_download": False,
            "files": files,
        }
        (inner / "offline-integrity-manifest.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for path in sorted(inner.rglob("*")):
                if path.is_file():
                    archive.write(path, Path(root.name) / path.relative_to(inner))
    return output


if __name__ == "__main__":
    print(build_offline())
