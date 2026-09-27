"""Portable local-model package discovery and fail-closed SD-card preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


PACKAGE_SCHEMA = "aion.local-model-package.v1"
WAREHOUSE_SCHEMA = "aion.expert-frame-warehouse.v1"
RELEASE_CATALOGUE_SCHEMA = "aion.local-model-release-catalogue.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalModelPackage:
    """Read a portable model card and verify its mounted model warehouse.

    The result is deliberately suitable for the product selector: a card is never
    shown as selectable merely because a volume happens to contain similarly named
    files.  The runtime still owns engine startup; this class establishes the
    trusted model location and the immutable profile it may start.
    """

    def __init__(self, package_path: str | Path) -> None:
        self.package_path = Path(package_path).resolve()
        self.package = json.loads(self.package_path.read_text(encoding="utf-8"))
        self._validate_package()

    @property
    def model_ref(self) -> str:
        return f"{self.package['model_id']}@{self.package['version']}"

    @classmethod
    def discover(cls, roots: Iterable[str | Path]) -> list["LocalModelPackage"]:
        found: list[LocalModelPackage] = []
        for root in roots:
            root_path = Path(root)
            if not root_path.is_dir():
                continue
            for card in sorted(root_path.glob("AION-Models/*/model-package.v1.json")):
                try:
                    found.append(cls(card))
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
        return found

    def preflight(self, volume_root: str | Path, *, internal_free_bytes: int,
                  memory_bytes: int, architecture: str = "arm64") -> dict[str, Any]:
        volume = Path(volume_root).resolve()
        storage = dict(self.package["storage"])
        runtime = dict(self.package["runtime_profile"])
        failures: list[str] = []
        warehouse_path = volume / storage["warehouse_manifest_relative_path"]
        if architecture not in self.package["compatibility"]["architectures"]:
            failures.append("architecture_not_supported")
        if memory_bytes < int(self.package["compatibility"]["minimum_memory_bytes"]):
            failures.append("insufficient_memory")
        if internal_free_bytes < int(runtime["minimum_internal_free_bytes"]):
            failures.append("insufficient_internal_free_space")
        integrity = self._verify_warehouse(warehouse_path)
        if not integrity["verified"]:
            failures.append(integrity["reason"])
        model_path = self._resolve_model_path(volume, warehouse_path, integrity)
        if integrity["verified"] and model_path is None:
            failures.append("model_source_missing")
        return {
            "schema_version": "aion.local-model-preflight.v1",
            "model_ref": self.model_ref,
            "display_name": self.package["display_name"],
            "selectable": not failures,
            "failures": failures,
            "warehouse": integrity,
            "runtime_profile": runtime,
            "speed_claim": dict(self.package["speed_claim"]),
            "model_sha256": str((storage.get("source_shards") or [{}])[0].get("sha256") or ""),
            "model_path": str(model_path) if model_path is not None else None,
        }

    def _resolve_model_path(
        self, volume: Path, warehouse_path: Path, integrity: dict[str, Any]
    ) -> Path | None:
        """Resolve the exact packaged weight without accepting an arbitrary path."""
        if not integrity.get("verified"):
            return None
        try:
            warehouse = json.loads(warehouse_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        expected = dict((self.package["storage"].get("source_shards") or [{}])[0])
        source = next(
            (item for item in warehouse.get("verified_sources") or []
             if item.get("name") == expected.get("name")),
            {},
        )
        relative = str(source.get("path") or source.get("relative_path") or expected.get("name") or "")
        candidate = (warehouse_path.parent / relative).resolve()
        try:
            candidate.relative_to(volume)
        except ValueError:
            return None
        if not candidate.is_file() or candidate.stat().st_size != int(expected.get("bytes") or -1):
            return None
        return candidate

    def _verify_warehouse(self, path: Path) -> dict[str, Any]:
        expected = dict(self.package["storage"])
        if not path.is_file():
            return {"verified": False, "reason": "warehouse_manifest_missing", "path": str(path)}
        try:
            warehouse = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"verified": False, "reason": "warehouse_manifest_invalid", "path": str(path)}
        accepted_statuses = {"COMPLETE_VERIFIED", "COMPLETE_VERIFIED_BOUNDED"}
        if warehouse.get("schema") != WAREHOUSE_SCHEMA or warehouse.get("status") not in accepted_statuses:
            return {"verified": False, "reason": "warehouse_not_complete_verified", "path": str(path)}
        if _sha256(path) != expected["warehouse_manifest_sha256"]:
            return {"verified": False, "reason": "warehouse_manifest_hash_mismatch", "path": str(path)}
        sources = {entry.get("name"): entry for entry in warehouse.get("verified_sources") or []}
        for source in expected["source_shards"]:
            observed = sources.get(source["name"], {})
            observed_hash = observed.get("verified_sha256") or observed.get("sha256")
            observed_bytes = observed.get("size") if "size" in observed else observed.get("bytes")
            if observed_hash != source["sha256"] or int(observed_bytes or -1) != int(source["bytes"]):
                return {"verified": False, "reason": "warehouse_source_identity_mismatch", "path": str(path)}
        bounded = warehouse.get("status") == "COMPLETE_VERIFIED_BOUNDED"
        return {
            "verified": True, "reason": "verified_bounded" if bounded else "verified",
            "path": str(path), "sha256": _sha256(path),
            "approval_scope": warehouse.get("approval_scope") if bounded else None,
            "known_failed_capabilities": list(warehouse.get("known_failed_capabilities") or []) if bounded else [],
            "required_tool_routes": list(warehouse.get("required_tool_routes") or []) if bounded else [],
        }

    def _validate_package(self) -> None:
        required = ("schema_version", "model_id", "version", "display_name", "storage",
                    "runtime_profile", "compatibility", "speed_claim")
        missing = [key for key in required if not self.package.get(key)]
        if missing:
            raise ValueError(f"local_model_package_fields_missing:{','.join(missing)}")
        if self.package["schema_version"] != PACKAGE_SCHEMA:
            raise ValueError("local_model_package_schema_invalid")
        storage = dict(self.package["storage"])
        if not storage.get("warehouse_manifest_relative_path") or len(str(storage.get("warehouse_manifest_sha256") or "")) != 64:
            raise ValueError("local_model_package_storage_identity_invalid")
        if not isinstance(storage.get("source_shards"), list) or not storage["source_shards"]:
            raise ValueError("local_model_package_source_shards_required")
        runtime = dict(self.package["runtime_profile"])
        if runtime.get("mode") != "full_exact" or int(runtime.get("minimum_internal_free_bytes") or 0) <= 0:
            raise ValueError("local_model_package_runtime_profile_invalid")


class LocalModelReleaseCatalogue:
    """The single source for Model Vault availability before model startup."""

    def __init__(self, catalogue_path: str | Path) -> None:
        self.catalogue_path = Path(catalogue_path).resolve()
        self.catalogue = json.loads(self.catalogue_path.read_text(encoding="utf-8"))
        if self.catalogue.get("schema_version") != RELEASE_CATALOGUE_SCHEMA:
            raise ValueError("local_model_release_catalogue_schema_invalid")
        if not isinstance(self.catalogue.get("models"), list):
            raise ValueError("local_model_release_catalogue_models_invalid")

    def entries(self) -> list[dict[str, Any]]:
        """Return only customer-safe fields for the selector list."""
        allowed = ("model_id", "version", "release_status", "selection_status", "reason", "device_test", "category", "role", "harness")
        return [{key: entry.get(key) for key in allowed} for entry in self.catalogue["models"]]

    def package_for(self, model_id: str) -> Path | None:
        entry = next((item for item in self.catalogue["models"] if item.get("model_id") == model_id), None)
        if not entry or entry.get("selection_status") != "selectable" or not entry.get("package"):
            return None
        return self.catalogue_path.parent / str(entry["package"])
