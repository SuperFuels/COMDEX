"""Read-only model-storage inventory for the Tessaris Vault."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .local_model_package import LocalModelPackage, LocalModelReleaseCatalogue
from .local_model_runtime_profiles import profile_for


_PACKAGE_ROOT = Path(__file__).parent / "model_packages"


def _memory_bytes() -> int:
    try:
        return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _scan_roots() -> list[Path]:
    configured = [Path(value).expanduser() for value in os.environ.get("TESSARIS_LOCAL_MODEL_ROOTS", "").split(":") if value]
    volumes = sorted(Path("/Volumes").glob("*")) if Path("/Volumes").is_dir() else []
    roots = [*configured, Path.home() / "TessarisModels", *volumes]
    return list(dict.fromkeys(root.resolve() for root in roots if root.is_dir()))


class LocalModelVault:
    def __init__(self, *, catalogue_path: Path = _PACKAGE_ROOT / "catalogue.v1.json") -> None:
        self.catalogue = LocalModelReleaseCatalogue(catalogue_path)

    def snapshot(self) -> dict[str, Any]:
        internal_free = shutil.disk_usage(Path.home()).free
        memory = _memory_bytes()
        roots = _scan_roots()
        entries = []
        for entry in self.catalogue.entries():
            package_path = self.catalogue.catalogue_path.parent / str(
                next((item.get("package") for item in self.catalogue.catalogue["models"] if item.get("model_id") == entry["model_id"]), "")
            )
            installations = []
            if package_path.is_file():
                package = LocalModelPackage(package_path)
                for root in roots:
                    result = package.preflight(root, internal_free_bytes=internal_free, memory_bytes=memory)
                    if result["warehouse"]["reason"] != "warehouse_manifest_missing":
                        installations.append({"storage_root": str(root), **result})
            legacy = self._legacy_installation(entry["model_id"], roots)
            if legacy:
                entries.append({
                    **entry,
                    "runtime_profile": profile_for(entry["model_id"]),
                    "release_status": "package_validation_pending",
                    "selection_status": "visible_not_selectable",
                    "reason": legacy["reason"],
                    "installations": [legacy],
                })
            else:
                entries.append({
                    **entry,
                    "runtime_profile": profile_for(entry["model_id"]),
                    "installations": installations,
                })
        return {
            "schema_version": "aion.local-model-vault.v1",
            "ok": True,
            "models": entries,
            "scan_roots": [str(root) for root in roots],
            "hardware": {"architecture": "arm64", "memory_bytes": memory, "internal_free_bytes": internal_free},
        }

    @staticmethod
    def _legacy_installation(model_id: str, roots: list[Path]) -> dict[str, Any] | None:
        """Recognise preserved pre-package AION layouts without selecting them."""
        for root in roots:
            inference = root / "AION-Inference"
            if model_id == "ibm-granite-3.1-3b-a800m-aion-sd":
                checkpoint = inference / "hf-models" / "granite-3.1-3b-a800m-instruct"
                required = ("config.json", "tokenizer.json", "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors")
                if all((checkpoint / name).is_file() for name in required):
                    return {
                        "storage_root": str(root), "selectable": False,
                        "legacy_layout": True,
                        "reason": "complete_legacy_checkpoint_found",
                        "detail": "Complete Granite checkpoint, tokenizer and verified expert derivatives found. A signed package card and release acceptance are still required.",
                    }
            if model_id == "qwen3-30b-a3b-aion-resident-q2":
                candidate = inference / "hf-models" / "qwen3-30b-a3b-gguf-q2-experts" / "Qwen3-30B-A3B-Q2_EXPERTS.gguf"
                control = inference / "hf-models" / "qwen3-30b-a3b-gguf-q4-k-m" / "Qwen3-30B-A3B-Q4_K_M.gguf"
                if candidate.is_file() and control.is_file():
                    return {
                        "storage_root": str(root), "selectable": False,
                        "legacy_layout": True,
                        "reason": "complete_legacy_candidate_found",
                        "detail": "The Q2 resident candidate and preserved Q4 control are found. A signed package card and broader quality acceptance are still required.",
                    }
        return None
