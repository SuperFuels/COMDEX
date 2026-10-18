from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_business.runtime.business_vault import validate_vault_separation
from backend.modules.aion_business.runtime.node_release_contract import ReleasePreflight


UPDATE_SCHEMA = "aion.sovereign_update.v1"
STATE_SCHEMA = "aion.sovereign_update_state.v1"
STAGE_AUTHORIZATION_SCHEMA = "aion.sovereign_update_stage_authorization.v1"
STAGE_AUTHORIZATION_FILE = ".tessaris-stage-authorization.json"
STAGED_MANIFEST_FILE = ".tessaris-update-manifest.json"
SAFE_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,39}$")
MAX_FILES = 20_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_PACKAGE_BYTES = 1024 * 1024 * 1024


class SovereignUpdateService:
    """Stages trusted releases, atomically selects one and rolls back on failed health."""

    def __init__(
        self,
        root: str | Path,
        *,
        mother_identity: DeviceIdentity,
        trusted_signers: Iterable[str],
        application_root: str | Path | None = None,
        vault_roots: Iterable[str | Path] = (),
        require_release_preflight: bool = False,
    ) -> None:
        self.root = Path(root).resolve()
        self.releases = self.root / "releases"
        self.staging = self.root / "staging"
        self.state_path = self.root / "update-state.json"
        self.identity = mother_identity
        self.trusted_signers = frozenset(str(value) for value in trusted_signers if value)
        self.vault_roots = tuple(Path(value).expanduser().resolve() for value in vault_roots)
        self.require_release_preflight = bool(require_release_preflight or self.vault_roots)
        if self.vault_roots and application_root is None:
            raise ValueError("update_application_root_required_for_vault_boundary")
        for vault_root in self.vault_roots:
            validate_vault_separation(
                vault_root,
                application_root=Path(application_root).expanduser().resolve(),
                update_root=self.root,
            )
        self.releases.mkdir(parents=True, exist_ok=True)
        self.staging.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass

    def stage(
        self,
        package: str | Path,
        *,
        release_preflight: ReleasePreflight | None = None,
    ) -> dict[str, Any]:
        source = Path(package).resolve()
        if not source.is_file() or source.stat().st_size > MAX_PACKAGE_BYTES:
            raise ValueError("update_package_missing_or_too_large")
        with zipfile.ZipFile(source) as archive:
            try:
                manifest = json.loads(archive.read("update-manifest.json"))
            except (KeyError, json.JSONDecodeError) as exc:
                raise ValueError("update_manifest_missing_or_invalid") from exc
            self._verify_manifest(manifest)
            version = str(manifest["version"])
            self._verify_release_preflight(version, release_preflight)
            target = self.staging / version
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)
            records = {str(item["path"]): item for item in manifest["files"]}
            if len(records) != len(manifest["files"]):
                raise ValueError("update_file_identity_duplicate")
            for info in archive.infolist():
                if info.filename == "update-manifest.json":
                    continue
                relative = self._safe_member(info)
                record = records.pop(relative.as_posix(), None)
                if record is None:
                    raise ValueError("update_contains_undeclared_file")
                raw = archive.read(info)
                if len(raw) != int(record["bytes"]) or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise ValueError("update_file_integrity_failed")
                destination = target.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                os.chmod(destination, 0o700 if bool(record.get("executable")) else 0o600)
            if records:
                raise ValueError("update_declared_file_missing")
        staged_manifest_path = target / STAGED_MANIFEST_FILE
        staged_manifest_path.write_bytes(canonical_bytes(manifest))
        os.chmod(staged_manifest_path, 0o600)
        manifest_hash = canonical_hash(self._unsigned(manifest))
        self._write_stage_authorization(
            target,
            version=version,
            manifest_hash=manifest_hash,
            release_preflight=release_preflight,
        )
        receipt = self._append_history(
            "staged",
            version,
            {
                "manifest_hash": manifest_hash,
                "release_preflight_required": self.require_release_preflight,
                "release_preflight_verified": release_preflight is not None,
                "vault_boundary_enforced": bool(self.vault_roots),
            },
        )
        return {"version": version, "status": "staged", "path": str(target), "receipt": receipt}

    def activate(
        self,
        version: str,
        *,
        start_release: Callable[[Path], bool],
        health_check: Callable[[Path], bool],
        stop_release: Callable[[Path], bool] | None = None,
    ) -> dict[str, Any]:
        if not SAFE_VERSION.fullmatch(str(version or "")):
            raise ValueError("update_version_invalid")
        candidate = self.staging / version
        if not candidate.is_dir():
            raise KeyError("staged_update_not_found")
        stage_authorization = self._verify_stage_authorization(candidate, version=version)
        self._verify_staged_release(
            candidate,
            version=version,
            stage_authorization=stage_authorization,
        )
        state = self._state()
        previous_version = state.get("current_version")
        previous = self.releases / str(previous_version) if previous_version else None
        installed = self.releases / version
        if installed.exists():
            shutil.rmtree(installed)
        os.replace(candidate, installed)
        self._write_pointer({**state, "current_version": version, "previous_version": previous_version})
        started = self._safe(start_release, installed)
        healthy = started and self._safe(health_check, installed)
        if healthy:
            receipt = self._append_history(
                "activated",
                version,
                {
                    "previous_version": previous_version,
                    "stage_authorization_hash": canonical_hash(stage_authorization),
                },
            )
            return {"version": version, "status": "activated", "healthy": True, "rolled_back_to": None, "receipt": receipt}

        if stop_release:
            self._safe(stop_release, installed)
        rollback_started = False
        if previous and previous.is_dir():
            self._write_pointer({**self._state(), "current_version": previous_version, "previous_version": version})
            rollback_started = self._safe(start_release, previous) and self._safe(health_check, previous)
        else:
            self._write_pointer({**self._state(), "current_version": None, "previous_version": version})
        receipt = self._append_history(
            "rolled_back", version,
            {
                "rolled_back_to": previous_version,
                "previous_runtime_healthy": rollback_started,
                "stage_authorization_hash": canonical_hash(stage_authorization),
            },
        )
        return {
            "version": version,
            "status": "rolled_back",
            "healthy": False,
            "rolled_back_to": previous_version,
            "previous_runtime_healthy": rollback_started,
            "manual_recovery_required": not rollback_started,
            "receipt": receipt,
        }

    def status(self) -> dict[str, Any]:
        state = self._state()
        return {
            "schema_version": STATE_SCHEMA,
            "current_version": state.get("current_version"),
            "previous_version": state.get("previous_version"),
            "history": list(state.get("history") or []),
            "trusted_signer_count": len(self.trusted_signers),
            "release_preflight_required": self.require_release_preflight,
            "vault_boundary_enforced": bool(self.vault_roots),
            "vault_count": len(self.vault_roots),
        }

    def _verify_manifest(self, manifest: Mapping[str, Any]) -> None:
        if manifest.get("schema_version") != UPDATE_SCHEMA:
            raise ValueError("update_schema_not_supported")
        if manifest.get("customer_data_included") is not False:
            raise ValueError("update_customer_data_boundary_invalid")
        if manifest.get("customer_credentials_included") is not False:
            raise ValueError("update_credentials_boundary_invalid")
        version = str(manifest.get("version") or "")
        if not SAFE_VERSION.fullmatch(version):
            raise ValueError("update_version_invalid")
        signer = str(manifest.get("signer_public_key") or "")
        if signer not in self.trusted_signers:
            raise PermissionError("update_signer_not_trusted")
        signature = str(manifest.get("signature") or "")
        if not DeviceIdentity.verify(signer, canonical_bytes(self._unsigned(manifest)), signature):
            raise PermissionError("update_signature_invalid")
        files = manifest.get("files")
        if not isinstance(files, list) or not files or len(files) > MAX_FILES:
            raise ValueError("update_file_manifest_invalid")
        total = 0
        for record in files:
            if not isinstance(record, Mapping):
                raise ValueError("update_file_record_invalid")
            self._safe_relative(str(record.get("path") or ""))
            size = int(record.get("bytes") or -1)
            digest = str(record.get("sha256") or "")
            if size < 0 or size > MAX_FILE_BYTES or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("update_file_record_invalid")
            total += size
        if total > MAX_PACKAGE_BYTES:
            raise ValueError("update_unpacked_size_exceeded")

    def _verify_release_preflight(
        self,
        package_version: str,
        release_preflight: ReleasePreflight | None,
    ) -> None:
        if release_preflight is None:
            if self.require_release_preflight:
                raise PermissionError("update_release_preflight_required")
            return
        if release_preflight.release_version != package_version:
            raise ValueError("update_release_preflight_version_mismatch")
        if not release_preflight.eligible:
            reasons = ",".join(release_preflight.reasons) or "unspecified"
            raise PermissionError(f"update_release_preflight_rejected:{reasons}")

    def _write_stage_authorization(
        self,
        target: Path,
        *,
        version: str,
        manifest_hash: str,
        release_preflight: ReleasePreflight | None,
    ) -> None:
        unsigned = {
            "schema_version": STAGE_AUTHORIZATION_SCHEMA,
            "version": version,
            "update_manifest_hash": manifest_hash,
            "release_preflight_required": self.require_release_preflight,
            "release_preflight_verified": release_preflight is not None,
            "release_preflight_hash": (
                canonical_hash(release_preflight.payload())
                if release_preflight is not None
                else None
            ),
        }
        authorization = {
            **unsigned,
            "mother_signature": self.identity.sign(canonical_bytes(unsigned)),
        }
        path = target / STAGE_AUTHORIZATION_FILE
        path.write_bytes(canonical_bytes(authorization))
        os.chmod(path, 0o600)

    def _verify_stage_authorization(
        self, candidate: Path, *, version: str
    ) -> dict[str, Any]:
        path = candidate / STAGE_AUTHORIZATION_FILE
        try:
            authorization = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PermissionError("update_stage_authorization_missing_or_invalid") from exc
        expected_keys = {
            "schema_version",
            "version",
            "update_manifest_hash",
            "release_preflight_required",
            "release_preflight_verified",
            "release_preflight_hash",
            "mother_signature",
        }
        if not isinstance(authorization, dict) or set(authorization) != expected_keys:
            raise PermissionError("update_stage_authorization_invalid")
        if (
            authorization.get("schema_version") != STAGE_AUTHORIZATION_SCHEMA
            or authorization.get("version") != version
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(authorization.get("update_manifest_hash") or "")
            )
            or bool(authorization.get("release_preflight_required"))
            != self.require_release_preflight
            or (
                self.require_release_preflight
                and authorization.get("release_preflight_verified") is not True
            )
        ):
            raise PermissionError("update_stage_authorization_invalid")
        preflight_hash = authorization.get("release_preflight_hash")
        if authorization.get("release_preflight_verified") is True:
            if not re.fullmatch(r"[0-9a-f]{64}", str(preflight_hash or "")):
                raise PermissionError("update_stage_authorization_invalid")
        elif preflight_hash is not None:
            raise PermissionError("update_stage_authorization_invalid")
        signature = str(authorization.get("mother_signature") or "")
        unsigned = {
            key: value
            for key, value in authorization.items()
            if key != "mother_signature"
        }
        if not DeviceIdentity.verify(
            self.identity.public_key_b64, canonical_bytes(unsigned), signature
        ):
            raise PermissionError("update_stage_authorization_signature_invalid")
        return authorization

    def _verify_staged_release(
        self,
        candidate: Path,
        *,
        version: str,
        stage_authorization: Mapping[str, Any],
    ) -> None:
        manifest_path = candidate / STAGED_MANIFEST_FILE
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PermissionError("update_staged_manifest_missing_or_invalid") from exc
        self._verify_manifest(manifest)
        if (
            str(manifest.get("version") or "") != version
            or canonical_hash(self._unsigned(manifest))
            != stage_authorization.get("update_manifest_hash")
        ):
            raise PermissionError("update_staged_manifest_authorization_mismatch")
        declared = {str(item["path"]): item for item in manifest["files"]}
        observed: set[str] = set()
        for path in candidate.rglob("*"):
            if path.is_symlink():
                raise PermissionError("update_staged_file_integrity_failed")
            if not path.is_file():
                continue
            relative = path.relative_to(candidate).as_posix()
            if relative in {STAGE_AUTHORIZATION_FILE, STAGED_MANIFEST_FILE}:
                continue
            record = declared.get(relative)
            if record is None:
                raise PermissionError("update_staged_file_undeclared")
            raw = path.read_bytes()
            if (
                len(raw) != int(record["bytes"])
                or hashlib.sha256(raw).hexdigest() != record["sha256"]
            ):
                raise PermissionError("update_staged_file_integrity_failed")
            observed.add(relative)
        if observed != set(declared):
            raise PermissionError("update_staged_file_missing")

    @staticmethod
    def _unsigned(manifest: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in manifest.items() if key != "signature"}

    @staticmethod
    def _safe_relative(value: str) -> PurePosixPath:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or any(not part for part in path.parts):
            raise ValueError("update_path_unsafe")
        return path

    @classmethod
    def _safe_member(cls, info: zipfile.ZipInfo) -> PurePosixPath:
        path = cls._safe_relative(info.filename)
        mode = info.external_attr >> 16
        if info.is_dir() or stat.S_ISLNK(mode):
            raise ValueError("update_archive_member_unsupported")
        return path

    @staticmethod
    def _safe(callback: Callable[[Path], bool], path: Path) -> bool:
        try:
            return bool(callback(path))
        except Exception:
            return False

    def _state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": STATE_SCHEMA, "current_version": None, "previous_version": None, "history": []}
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        if value.get("schema_version") != STATE_SCHEMA or not isinstance(value.get("history"), list):
            raise RuntimeError("update_state_invalid")
        self._verify_history(value["history"])
        return value

    def _verify_history(self, history: list[Any]) -> None:
        previous_hash = "genesis"
        for item in history:
            if not isinstance(item, dict):
                raise RuntimeError("update_history_invalid")
            receipt_hash = str(item.get("receipt_hash") or "")
            signature = str(item.get("mother_signature") or "")
            unsigned_receipt = {
                key: value
                for key, value in item.items()
                if key not in {"receipt_hash", "mother_signature"}
            }
            signed_receipt = {
                key: value
                for key, value in item.items()
                if key != "mother_signature"
            }
            if (
                item.get("schema_version") != "aion.sovereign_update_receipt.v1"
                or item.get("previous_hash") != previous_hash
                or canonical_hash(unsigned_receipt) != receipt_hash
                or not DeviceIdentity.verify(
                    self.identity.public_key_b64,
                    canonical_bytes(signed_receipt),
                    signature,
                )
            ):
                raise RuntimeError("update_history_integrity_failed")
            previous_hash = receipt_hash

    def _write_pointer(self, state: Mapping[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(dict(state)))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)

    def _append_history(self, event: str, version: str, detail: Mapping[str, Any]) -> dict[str, Any]:
        state = self._state()
        previous_hash = str(state["history"][-1]["receipt_hash"]) if state["history"] else "genesis"
        receipt = {
            "schema_version": "aion.sovereign_update_receipt.v1",
            "event": event,
            "version": version,
            "detail": dict(detail),
            "previous_hash": previous_hash,
            "recorded_at": utc_now_iso(),
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        receipt["mother_signature"] = self.identity.sign(canonical_bytes(receipt))
        state["history"].append(receipt)
        self._write_pointer(state)
        return receipt


def build_signed_update_package(
    source: str | Path,
    destination: str | Path,
    *,
    version: str,
    publisher: DeviceIdentity,
) -> Path:
    """Release-side helper used by controlled build tooling and tests."""
    if not SAFE_VERSION.fullmatch(str(version or "")):
        raise ValueError("update_version_invalid")
    root = Path(source).resolve()
    output = Path(destination).resolve()
    files = []
    selected = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        files.append({
            "path": relative,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "executable": bool(path.stat().st_mode & stat.S_IXUSR),
        })
        selected.append((relative, raw))
    unsigned = {
        "schema_version": UPDATE_SCHEMA,
        "version": version,
        "created_at": utc_now_iso(),
        "signer_public_key": publisher.public_key_b64,
        "files": files,
        "customer_data_included": False,
        "customer_credentials_included": False,
    }
    manifest = {**unsigned, "signature": publisher.sign(canonical_bytes(unsigned))}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("update-manifest.json", canonical_bytes(manifest))
        for relative, raw in selected:
            archive.writestr(relative, raw)
    return output
