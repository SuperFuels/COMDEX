from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


OWNERSHIP_VERSION = "pilot.mother-ownership.v1"
DEPLOYMENT_PROFILES = {
    "personal_computer": {"audience": "individual", "remote_access": "optional", "ha": False},
    "home_server": {"audience": "household", "remote_access": "recommended", "ha": False},
    "private_vps": {"audience": "individual_or_team", "remote_access": "required", "ha": False},
    "business": {"audience": "organization", "remote_access": "required", "ha": True},
}
_REDACT = re.compile(r"(?i)(password|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)")
_PACKAGE_EXCLUDED_PARTS = frozenset({".git", ".runtime", "node_modules", "__pycache__", ".next", "dist"})


class MotherOwnershipAuthority:
    """Customer-controlled deployment, continuity and recovery authority."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path, *, identity: DeviceIdentity, mother_id: str) -> None:
        self.runtime_dir = Path(runtime_dir).resolve()
        self.root = self.runtime_dir / "pilot_ownership"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.identity = identity
        self.mother_id = mother_id
        self.state_path = self.root / "state.json"
        self.primary_path = self.root / "primary.json"

    def _read(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": OWNERSHIP_VERSION, "revision": 0, "backups": [], "updates": []}
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != OWNERSHIP_VERSION:
            raise RuntimeError("Pilot ownership state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        state["revision"] = int(state.get("revision") or 0) + 1
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)

    def deployment_plan(
        self,
        *,
        profile: str,
        public_remote_access: bool = False,
        customer_cloud: str | None = None,
    ) -> dict[str, Any]:
        if profile not in DEPLOYMENT_PROFILES:
            raise ValueError("Choose a supported customer-owned deployment")
        if customer_cloud and not re.fullmatch(r"[A-Za-z0-9 ._-]{2,80}", customer_cloud):
            raise ValueError("Cloud provider label is invalid")
        plan = {
            "schema_version": OWNERSHIP_VERSION,
            "profile": profile,
            **DEPLOYMENT_PROFILES[profile],
            "data_controller": "customer",
            "mother_location": "customer_controlled",
            "customer_cloud": customer_cloud,
            "public_remote_access": bool(public_remote_access),
            "required_controls": ["tls", "signed_phone_possession", "encrypted_backup", "single_writable_primary"],
            "tessaris_data_copy_required": False,
        }
        return {**plan, "plan_hash": canonical_hash(plan)}

    @staticmethod
    def _safe_package_files(source: Path) -> list[Path]:
        files: list[Path] = []
        total = 0
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(source)
            if any(part in _PACKAGE_EXCLUDED_PARTS for part in relative.parts):
                continue
            if any(part.startswith(".env") or _REDACT.search(part) for part in relative.parts):
                continue
            size = path.stat().st_size
            if size > 50 * 1024 * 1024:
                raise ValueError(f"Deployment file is too large: {relative.as_posix()}")
            total += size
            if total > 512 * 1024 * 1024:
                raise ValueError("Deployment source exceeds the clean-package size limit")
            files.append(path)
        if not files:
            raise ValueError("Deployment source contains no safe application files")
        return files

    def build_deployment_package(
        self, *, profile: str, application_source: str | Path,
        destination: str | Path, version: str,
    ) -> dict[str, Any]:
        """Build a signed, secret-free customer-owned Pilot distribution."""
        if profile not in DEPLOYMENT_PROFILES:
            raise ValueError("Choose a supported customer-owned deployment")
        if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,39}", version):
            raise ValueError("Deployment version is invalid")
        source = Path(application_source).resolve()
        target = Path(destination).resolve()
        if not source.is_dir():
            raise ValueError("Deployment source must be a directory")
        try:
            target.relative_to(source)
        except ValueError:
            pass
        else:
            raise ValueError("Deployment output must be outside its application source")
        selected = self._safe_package_files(source)
        application_files = []
        for path in selected:
            raw = path.read_bytes()
            application_files.append({
                "path": f"pilot/{path.relative_to(source).as_posix()}",
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            })
        plan = self.deployment_plan(profile=profile)
        config = {
            "schema_version": "pilot.customer-deployment-config.v1",
            "profile": profile, "version": version,
            "bind": "127.0.0.1" if profile == "personal_computer" else "0.0.0.0",
            "remote_access": DEPLOYMENT_PROFILES[profile]["remote_access"],
            "data_directory": "./customer-data",
            "secrets_directory": "./customer-secrets",
            "customer_owns_data": True,
            "tessaris_data_copy": False,
        }
        launcher = "#!/bin/sh\nset -eu\nexec python3 -m backend.modules.aion_fabric.cli --runtime-dir ./customer-data serve\n"
        readme = (
            "Pilot customer-owned deployment\n\n"
            f"Profile: {profile}\nVersion: {version}\n\n"
            "This archive contains no customer credentials or runtime data. Put secrets in "
            "customer-secrets, keep that directory private, and follow the guided setup before "
            "opening remote access. Pilot writes memory and receipts only to customer-data.\n"
        )
        manifest_payload = {
            "schema_version": "pilot.customer-deployment-package.v1",
            "package_id": f"deployment_{uuid4().hex}",
            "profile": profile, "version": version, "created_at": utc_now_iso(),
            "mother_fingerprint": self.identity.fingerprint,
            "application_files": application_files,
            "configuration_hash": canonical_hash(config),
            "plan_hash": plan["plan_hash"],
            "customer_data_included": False, "customer_secrets_included": False,
        }
        manifest = {**manifest_payload, "signature": self.identity.sign(canonical_bytes(manifest_payload))}
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, record in zip(selected, application_files, strict=True):
                archive.writestr(record["path"], path.read_bytes())
            archive.writestr("pilot-deployment.json", canonical_bytes(config))
            archive.writestr("pilot-deployment-manifest.json", canonical_bytes(manifest))
            archive.writestr("README.txt", readme.encode("utf-8"))
            launcher_info = zipfile.ZipInfo("start-pilot.sh")
            launcher_info.external_attr = 0o755 << 16
            archive.writestr(launcher_info, launcher.encode("utf-8"))
        verification = self.verify_deployment_package(package=target, signer_public_key=self.identity.public_key_b64)
        return {**verification, "path": str(target), "profile": profile, "version": version}

    @staticmethod
    def verify_deployment_package(*, package: str | Path, signer_public_key: str) -> dict[str, Any]:
        with zipfile.ZipFile(Path(package).resolve()) as archive:
            names = archive.namelist()
            for name in names:
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("Deployment package contains an unsafe path")
            manifest = json.loads(archive.read("pilot-deployment-manifest.json"))
            signature = str(manifest.pop("signature", ""))
            if not DeviceIdentity.verify(signer_public_key, canonical_bytes(manifest), signature):
                raise PermissionError("Deployment package signature is invalid")
            config = json.loads(archive.read("pilot-deployment.json"))
            if canonical_hash(config) != manifest["configuration_hash"]:
                raise RuntimeError("Deployment configuration verification failed")
            for record in manifest["application_files"]:
                raw = archive.read(record["path"])
                if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise RuntimeError("Deployment application verification failed")
            if manifest.get("customer_data_included") or manifest.get("customer_secrets_included"):
                raise RuntimeError("Deployment package claims to contain customer-private material")
            return {
                "package_id": manifest["package_id"], "verified": True,
                "file_count": len(manifest["application_files"]),
                "customer_data_included": False, "customer_secrets_included": False,
            }

    def connection_descriptor(self, *, endpoints: list[str], expires_minutes: int = 15) -> dict[str, Any]:
        if not 1 <= expires_minutes <= 60:
            raise ValueError("Connection descriptor lifetime is outside the supported bound")
        clean = []
        for endpoint in endpoints:
            value = str(endpoint)
            if not re.fullmatch(r"https://[^\s]{3,240}", value):
                raise ValueError("Pilot connection endpoints must use trusted HTTPS")
            clean.append(value)
        issued = datetime.now(timezone.utc)
        payload = {
            "schema_version": "pilot.connect-descriptor.v1",
            "mother_id": self.mother_id,
            "mother_fingerprint": self.identity.fingerprint,
            "endpoints": sorted(set(clean)),
            "issued_at": issued.isoformat(),
            "expires_at": (issued + timedelta(minutes=expires_minutes)).isoformat(),
            "nonce": secrets.token_urlsafe(18),
            "contains_mother_secret": False,
        }
        return {**payload, "signature": self.identity.sign(canonical_bytes(payload))}

    @staticmethod
    def verify_connection_descriptor(descriptor: dict[str, Any], public_key_b64: str) -> bool:
        signature = str(descriptor.get("signature") or "")
        payload = {key: value for key, value in descriptor.items() if key != "signature"}
        try:
            expires = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            return False
        return expires > datetime.now(timezone.utc) and DeviceIdentity.verify(public_key_b64, canonical_bytes(payload), signature)

    def sealed_rendezvous_record(self, *, descriptor: dict[str, Any], phone_transport_public_key: str) -> dict[str, Any]:
        phone_key = X25519PublicKey.from_public_bytes(base64.b64decode(phone_transport_public_key, validate=True))
        ephemeral = X25519PrivateKey.generate()
        shared = ephemeral.exchange(phone_key)
        key = hashlib.sha256(b"pilot-rendezvous-v1" + shared).digest()
        nonce = secrets.token_bytes(12)
        opaque_id = "mother_" + canonical_hash({"mother_id": self.mother_id, "salt": secrets.token_hex(16)})[:32]
        aad = canonical_bytes({"schema_version": "pilot.rendezvous.v1", "opaque_mother_id": opaque_id})
        ciphertext = AESGCM(key).encrypt(nonce, canonical_bytes(descriptor), aad)
        return {
            "schema_version": "pilot.rendezvous.v1",
            "opaque_mother_id": opaque_id,
            "ephemeral_public_key": base64.b64encode(ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "sealed_descriptor": base64.b64encode(ciphertext).decode("ascii"),
            "expires_at": descriptor["expires_at"],
            "readable_endpoint_exposed": False,
            "identity_exposed": False,
        }

    @staticmethod
    def open_rendezvous_record(record: dict[str, Any], phone_private_key: X25519PrivateKey) -> dict[str, Any]:
        ephemeral = X25519PublicKey.from_public_bytes(base64.b64decode(record["ephemeral_public_key"], validate=True))
        key = hashlib.sha256(b"pilot-rendezvous-v1" + phone_private_key.exchange(ephemeral)).digest()
        aad = canonical_bytes({"schema_version": record["schema_version"], "opaque_mother_id": record["opaque_mother_id"]})
        raw = AESGCM(key).decrypt(base64.b64decode(record["nonce"]), base64.b64decode(record["sealed_descriptor"]), aad)
        return json.loads(raw)

    @staticmethod
    def _derive_backup_key(passphrase: str, salt: bytes) -> bytes:
        if len(passphrase) < 12:
            raise ValueError("Backup passphrase must contain at least 12 characters")
        return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase.encode("utf-8"))

    @staticmethod
    def _archive(source: Path) -> tuple[bytes, list[dict[str, Any]]]:
        buffer = BytesIO()
        manifest = []
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(source).as_posix()
                raw = path.read_bytes()
                manifest.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
                archive.writestr(relative, raw)
        return buffer.getvalue(), manifest

    def create_backup(self, *, source: str | Path, destination: str | Path, passphrase: str) -> dict[str, Any]:
        source_path = Path(source).resolve()
        destination_path = Path(destination).resolve()
        if not source_path.is_dir():
            raise ValueError("Backup source must be a directory")
        raw, files = self._archive(source_path)
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        key = self._derive_backup_key(passphrase, salt)
        header = {
            "schema_version": "pilot.encrypted-backup.v1",
            "backup_id": f"backup_{uuid4().hex}",
            "mother_fingerprint": self.identity.fingerprint,
            "created_at": utc_now_iso(),
            "file_count": len(files),
            "content_hash": hashlib.sha256(raw).hexdigest(),
            "manifest_hash": canonical_hash(files),
            "kdf": "scrypt-n16384-r8-p1",
            "cipher": "aes-256-gcm",
        }
        ciphertext = AESGCM(key).encrypt(nonce, raw, canonical_bytes(header))
        envelope = {
            **header,
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(canonical_bytes(envelope))
        os.chmod(destination_path, 0o600)
        verified = self.inspect_backup(destination=destination_path, passphrase=passphrase)
        with self._lock:
            state = self._read()
            state["backups"].append({key_: verified[key_] for key_ in ("backup_id", "created_at", "file_count", "content_hash", "verified")})
            state["last_successful_backup_at"] = verified["created_at"]
            self._write(state)
        return verified

    def inspect_backup(self, *, destination: str | Path, passphrase: str) -> dict[str, Any]:
        envelope = json.loads(Path(destination).read_text(encoding="utf-8"))
        header_keys = ("schema_version", "backup_id", "mother_fingerprint", "created_at", "file_count", "content_hash", "manifest_hash", "kdf", "cipher")
        header = {key: envelope[key] for key in header_keys}
        key = self._derive_backup_key(passphrase, base64.b64decode(envelope["salt"]))
        try:
            raw = AESGCM(key).decrypt(base64.b64decode(envelope["nonce"]), base64.b64decode(envelope["ciphertext"]), canonical_bytes(header))
        except Exception:
            raise PermissionError("Pilot could not decrypt or verify that backup") from None
        if hashlib.sha256(raw).hexdigest() != header["content_hash"]:
            raise RuntimeError("Backup content verification failed")
        return {**header, "verified": True, "archive_bytes": len(raw)}

    def restore_backup(self, *, backup: str | Path, destination: str | Path, passphrase: str) -> dict[str, Any]:
        envelope = json.loads(Path(backup).read_text(encoding="utf-8"))
        inspected = self.inspect_backup(destination=backup, passphrase=passphrase)
        header = {key: envelope[key] for key in ("schema_version", "backup_id", "mother_fingerprint", "created_at", "file_count", "content_hash", "manifest_hash", "kdf", "cipher")}
        key = self._derive_backup_key(passphrase, base64.b64decode(envelope["salt"]))
        raw = AESGCM(key).decrypt(base64.b64decode(envelope["nonce"]), base64.b64decode(envelope["ciphertext"]), canonical_bytes(header))
        target = Path(destination).resolve()
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            for member in archive.infolist():
                relative = PurePosixPath(member.filename)
                if relative.is_absolute() or ".." in relative.parts or member.is_dir():
                    if member.is_dir():
                        continue
                    raise RuntimeError("Backup contains an unsafe path")
                output = target.joinpath(*relative.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(archive.read(member))
        restored, files = self._archive(target)
        if canonical_hash(files) != inspected["manifest_hash"]:
            raise RuntimeError("Restored files do not match the backup manifest")
        return {"restored": True, "verified": True, "backup_id": inspected["backup_id"], "file_count": len(files), "restored_archive_hash": hashlib.sha256(restored).hexdigest()}

    def create_migration_export(
        self, *, source: str | Path, destination: str | Path, passphrase: str,
    ) -> dict[str, Any]:
        """Export the complete mother as an encrypted, signed migration capsule."""
        target = Path(destination).resolve()
        temporary_backup = self.root / f"migration-{uuid4().hex}.pilotbackup"
        try:
            backup = self.create_backup(source=source, destination=temporary_backup, passphrase=passphrase)
            backup_raw = temporary_backup.read_bytes()
            payload = {
                "schema_version": "pilot.mother-migration.v1",
                "migration_id": f"migration_{uuid4().hex}",
                "mother_id": self.mother_id,
                "mother_fingerprint": self.identity.fingerprint,
                "created_at": utc_now_iso(),
                "encrypted_backup_file": "mother.pilotbackup",
                "encrypted_backup_sha256": hashlib.sha256(backup_raw).hexdigest(),
                "file_count": backup["file_count"],
                "preserves_identity_permissions_messages_proofs": True,
                "source_primary_release_required": True,
            }
            manifest = {**payload, "signature": self.identity.sign(canonical_bytes(payload))}
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("migration-manifest.json", canonical_bytes(manifest))
                archive.writestr("mother.pilotbackup", backup_raw)
        finally:
            temporary_backup.unlink(missing_ok=True)
        inspected = self.inspect_migration_export(package=target, signer_public_key=self.identity.public_key_b64)
        return {**inspected, "path": str(target)}

    @staticmethod
    def inspect_migration_export(*, package: str | Path, signer_public_key: str) -> dict[str, Any]:
        with zipfile.ZipFile(Path(package).resolve()) as archive:
            if set(archive.namelist()) != {"migration-manifest.json", "mother.pilotbackup"}:
                raise RuntimeError("Migration capsule contains unexpected files")
            manifest = json.loads(archive.read("migration-manifest.json"))
            signature = str(manifest.pop("signature", ""))
            if not DeviceIdentity.verify(signer_public_key, canonical_bytes(manifest), signature):
                raise PermissionError("Migration capsule signature is invalid")
            backup_raw = archive.read("mother.pilotbackup")
            if hashlib.sha256(backup_raw).hexdigest() != manifest["encrypted_backup_sha256"]:
                raise RuntimeError("Migration capsule content verification failed")
            return {
                "schema_version": manifest["schema_version"],
                "migration_id": manifest["migration_id"],
                "mother_id": manifest["mother_id"],
                "mother_fingerprint": manifest["mother_fingerprint"],
                "file_count": manifest["file_count"], "verified": True,
                "encrypted": True, "source_primary_release_required": True,
            }

    def restore_migration_export(
        self, *, package: str | Path, destination: str | Path, passphrase: str,
        source_public_key: str,
    ) -> dict[str, Any]:
        inspected = self.inspect_migration_export(package=package, signer_public_key=source_public_key)
        temporary_backup = self.root / f"restore-{uuid4().hex}.pilotbackup"
        try:
            with zipfile.ZipFile(Path(package).resolve()) as archive:
                temporary_backup.write_bytes(archive.read("mother.pilotbackup"))
            restored = self.restore_backup(backup=temporary_backup, destination=destination, passphrase=passphrase)
        finally:
            temporary_backup.unlink(missing_ok=True)
        return {
            **restored, "migration_id": inspected["migration_id"],
            "source_mother_fingerprint": inspected["mother_fingerprint"],
            "destination_primary_activation_required": True,
            "identity_permissions_messages_proofs_preserved": True,
        }

    def acquire_primary(self, *, instance_id: str, ttl_seconds: int = 30) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,120}", instance_id) or not 10 <= ttl_seconds <= 300:
            raise ValueError("Primary lease request is invalid")
        now = datetime.now(timezone.utc)
        with self._lock:
            current = json.loads(self.primary_path.read_text()) if self.primary_path.exists() else None
            if current:
                expires = datetime.fromisoformat(current["expires_at"])
                if expires > now and current["instance_id"] != instance_id:
                    raise PermissionError("Another Pilot instance holds the writable-primary lease")
            payload = {
                "schema_version": "pilot.primary-lease.v1", "instance_id": instance_id,
                "mother_fingerprint": self.identity.fingerprint, "issued_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            }
            lease = {**payload, "signature": self.identity.sign(canonical_bytes(payload))}
            temporary = self.primary_path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(lease))
            os.replace(temporary, self.primary_path)
            return lease

    def release_primary(self, *, instance_id: str) -> None:
        with self._lock:
            if not self.primary_path.exists():
                return
            current = json.loads(self.primary_path.read_text())
            if current.get("instance_id") != instance_id:
                raise PermissionError("Only the active primary may release its lease")
            self.primary_path.unlink()

    def stage_update(self, *, artifact: str | Path, signature: str, signer_public_key: str, version: str) -> dict[str, Any]:
        raw = Path(artifact).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        signed = canonical_bytes({"version": version, "sha256": digest})
        if not DeviceIdentity.verify(signer_public_key, signed, signature):
            raise PermissionError("Pilot update signature is invalid")
        staged = self.root / "updates" / version
        staged.mkdir(parents=True, exist_ok=True)
        target = staged / "artifact.bin"
        shutil.copyfile(artifact, target)
        record = {"version": version, "sha256": digest, "status": "staged", "staged_at": utc_now_iso(), "path": str(target)}
        state = self._read()
        state["updates"].append(record)
        self._write(state)
        return record

    def verify_or_rollback_update(self, *, version: str, health_check: Callable[[], bool]) -> dict[str, Any]:
        state = self._read()
        record = next((item for item in reversed(state["updates"]) if item["version"] == version), None)
        if not record:
            raise KeyError("That staged update is not available")
        healthy = bool(health_check())
        record["status"] = "activated" if healthy else "rolled_back"
        record["verified_at"] = utc_now_iso()
        if not healthy:
            Path(record["path"]).unlink(missing_ok=True)
        self._write(state)
        return {"version": version, "healthy": healthy, "status": record["status"]}

    def diagnostic_bundle(self, values: dict[str, Any]) -> dict[str, Any]:
        def redact(value: Any, key: str = "") -> Any:
            if _REDACT.search(key):
                return "[REDACTED]"
            if isinstance(value, dict):
                return {str(k): redact(v, str(k)) for k, v in value.items()}
            if isinstance(value, list):
                return [redact(item, key) for item in value[:200]]
            if isinstance(value, str):
                value = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [REDACTED]", value)
                return value[:500]
            return value
        report = {
            "schema_version": "pilot.redacted-diagnostics.v1",
            "created_at": utc_now_iso(),
            "mother_fingerprint": self.identity.fingerprint,
            "diagnostics": redact(values),
            "secrets_included": False,
        }
        return {**report, "report_hash": canonical_hash(report)}
