from __future__ import annotations

import base64
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.modules.aion_business.contracts.sovereign_brain import (
    CANONICAL_STORE_KINDS,
    build_brain_export_manifest,
)
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary
from backend.modules.aion_business.runtime.sovereign_boardroom_bridge import SovereignBoardroomBridge
from backend.modules.aion_business.runtime.sovereign_runtime_supervisor import SovereignRuntimeSupervisor
from backend.modules.aion_fabric.canonical import canonical_bytes, utc_now_iso
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.pilot_unified.ownership import DEPLOYMENT_PROFILES, MotherOwnershipAuthority


SETUP_VERSION = "aion.sovereign_setup.v1"
VAULT_VERSION = "aion.sovereign_vault.v1"
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}")


def _atomic_private_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(dict(value)))
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, path)


class HardwareProfiler:
    """Collects coarse capacity only; no serial number or stable host identifier."""

    @staticmethod
    def _memory_bytes() -> int:
        try:
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            size = int(os.sysconf("SC_PAGE_SIZE"))
            if pages > 0 and size > 0:
                return pages * size
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["/usr/sbin/sysctl", "-n", "hw.memsize"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                return int(result.stdout.strip())
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
        return 0

    @classmethod
    def profile(cls, storage_root: str | Path) -> Dict[str, Any]:
        root = Path(storage_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        machine = platform.machine().lower()
        system = platform.system()
        memory = cls._memory_bytes()
        disk = shutil.disk_usage(root)
        accelerator = "apple_silicon" if system == "Darwin" and machine in {"arm64", "aarch64"} else "unknown"
        return {
            "schema_version": "aion.hardware_profile.v1",
            "os_family": system.lower() or "unknown",
            "architecture": machine or "unknown",
            "cpu_count": int(os.cpu_count() or 1),
            "memory_bytes": memory,
            "storage_free_bytes": int(disk.free),
            "accelerator_class": accelerator,
            "contains_stable_device_identifier": False,
            "profiled_at": utc_now_iso(),
        }

    @staticmethod
    def model_plan(profile: Mapping[str, Any]) -> Dict[str, Any]:
        gib = int(profile.get("memory_bytes") or 0) / (1024**3)
        free_gib = int(profile.get("storage_free_bytes") or 0) / (1024**3)
        if gib >= 64 and free_gib >= 40:
            tier, parameters, context = "workstation", "12B-20B quantized", 32768
        elif gib >= 24 and free_gib >= 20:
            tier, parameters, context = "capable", "7B-9B quantized", 16384
        elif gib >= 12 and free_gib >= 10:
            tier, parameters, context = "standard", "3B-4B quantized", 8192
        else:
            tier, parameters, context = "lite", "1B-2B quantized", 4096
        return {
            "schema_version": "aion.model_plan.v1",
            "tier": tier,
            "recommended_parameter_class": parameters,
            "recommended_context_tokens": context,
            "local_core_supported": True,
            "larger_workloads": "optional_customer_compute",
            "automatic_model_download": False,
            "reason": f"Recommendation uses coarse memory ({gib:.1f} GiB) and free storage ({free_gib:.1f} GiB).",
        }


class BusinessRequirementsProfiler:
    """Recommend capabilities from operating needs without assigning a size label."""

    @staticmethod
    def profile(requirements: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        source = dict(requirements or {})
        counts = {
            "legal_entities": max(1, int(source.get("legal_entities") or 1)),
            "locations": max(1, int(source.get("locations") or 1)),
            "countries": max(1, int(source.get("countries") or 1)),
            "currencies": max(1, int(source.get("currencies") or 1)),
            "users": max(1, int(source.get("users") or 1)),
            "approval_levels": max(0, int(source.get("approval_levels") or 0)),
        }
        needs = {key: bool(source.get(key)) for key in (
            "project_budgeting", "external_collaborators", "separation_of_duties",
            "enterprise_identity", "regulated_data", "private_compute",
        )}
        modules = ["core_business_brain", "boardroom_core"]
        reasons = []
        if needs["project_budgeting"]:
            modules.append("project_operations")
            reasons.append("Projects need teams, budgets, milestones and risks.")
        if counts["locations"] > 1 or counts["countries"] > 1:
            modules.append("multi_location")
            reasons.append("Operations span more than one location or country.")
        if counts["legal_entities"] > 1 or counts["currencies"] > 1:
            modules.append("multi_entity_group")
            reasons.append("Legal entities or currencies must remain distinct.")
        if counts["approval_levels"] > 0 or needs["separation_of_duties"]:
            modules.append("delegated_authority")
            reasons.append("Work requires approval levels or separation of duties.")
        if needs["external_collaborators"]:
            modules.append("bounded_external_workspaces")
            reasons.append("External people need deliberately restricted workspaces.")
        if needs["enterprise_identity"]:
            modules.append("enterprise_identity")
            reasons.append("The customer wants its existing identity provider.")
        if needs["regulated_data"]:
            modules.append("regulated_data_controls")
            reasons.append("Residency, retention and stronger audit controls are required.")
        if needs["private_compute"]:
            modules.append("private_compute")
            reasons.append("Model compute must run in customer-controlled infrastructure.")
        return {
            "schema_version": "aion.business_requirements_profile.v1",
            "counts": counts, "needs": needs, "recommended_modules": modules,
            "recommendation_reasons": reasons,
            "business_size_label_used": False,
            "commercial_entitlement_decided_separately": True,
            "profiled_at": utc_now_iso(),
        }


class SovereignVault:
    """Small AES-GCM vault. Raw values are never exposed through status or export manifests."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.key_path = self.root / "device-vault.key"
        self.data_path = self.root / "vault.enc"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        if not self.key_path.exists():
            self.key_path.write_bytes(secrets.token_bytes(32))
            try:
                os.chmod(self.key_path, 0o600)
            except OSError:
                pass
        if len(self.key_path.read_bytes()) != 32:
            raise RuntimeError("Sovereign vault device key is invalid")
        if not self.data_path.exists():
            self._write({"schema_version": VAULT_VERSION, "revision": 0, "secrets": {}})
        self._read()

    def set_secret(self, binding: str, value: str) -> Dict[str, Any]:
        if not _SAFE_NAME.fullmatch(str(binding or "")):
            raise ValueError("Vault binding name is invalid")
        secret = str(value or "")
        if not secret or len(secret.encode("utf-8")) > 65536:
            raise ValueError("Vault secret is empty or too large")
        state = self._read()
        state["revision"] = int(state.get("revision") or 0) + 1
        state.setdefault("secrets", {})[binding] = secret
        self._write(state)
        return {"binding": binding, "stored": True, "revision": state["revision"], "secret_exposed": False}

    def get_secret(self, binding: str) -> str:
        return str(self._read().get("secrets", {}).get(binding) or "")

    def delete_secret(self, binding: str) -> bool:
        state = self._read()
        existed = binding in state.get("secrets", {})
        if existed:
            del state["secrets"][binding]
            state["revision"] = int(state.get("revision") or 0) + 1
            self._write(state)
        return existed

    def status(self) -> Dict[str, Any]:
        state = self._read()
        return {
            "ok": True,
            "schema_version": state["schema_version"],
            "revision": int(state.get("revision") or 0),
            "bindings": sorted(state.get("secrets", {})),
            "secret_count": len(state.get("secrets", {})),
            "encrypted_at_rest": True,
            "secrets_exposed": False,
            "key_protection": "owner-only device file; OS secure-store wrapping required before production",
        }

    def _read(self) -> Dict[str, Any]:
        if not self.key_path.exists() or not self.data_path.exists():
            raise RuntimeError("Sovereign vault has not been initialized")
        envelope = json.loads(self.data_path.read_text(encoding="utf-8"))
        if envelope.get("schema_version") != VAULT_VERSION:
            raise RuntimeError("Sovereign vault format is unsupported")
        key = self.key_path.read_bytes()
        try:
            raw = AESGCM(key).decrypt(
                base64.b64decode(envelope["nonce"], validate=True),
                base64.b64decode(envelope["ciphertext"], validate=True),
                VAULT_VERSION.encode("utf-8"),
            )
        except Exception:
            raise PermissionError("Sovereign vault could not be decrypted or authenticated") from None
        state = json.loads(raw)
        if state.get("schema_version") != VAULT_VERSION:
            raise RuntimeError("Sovereign vault payload is unsupported")
        return state

    def _write(self, state: Mapping[str, Any]) -> None:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.key_path.read_bytes()).encrypt(
            nonce, canonical_bytes(dict(state)), VAULT_VERSION.encode("utf-8")
        )
        envelope = {
            "schema_version": VAULT_VERSION,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        _atomic_private_json(self.data_path, envelope)


class SovereignBrainSetup:
    """Idempotent first-run and continuity authority for a clean customer brain."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.setup_path = self.root / "setup.json"
        self.owner_path = self.root / "owner" / "owner.json"
        self.hardware_path = self.root / "system" / "hardware.json"
        self.model_plan_path = self.root / "system" / "model-plan.json"
        self.requirements_path = self.root / "system" / "business-requirements.json"
        self.vault = SovereignVault(self.root / "vault")
        self.supervisor = SovereignRuntimeSupervisor(self.root / "system" / "supervisor.json")

    def initialize(
        self,
        *,
        owner_display_name: str,
        deployment_profile: str = "personal_computer",
        customer_compute: str = "local",
        business_requirements: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        name = " ".join(str(owner_display_name or "").split())
        if not 1 <= len(name) <= 100:
            raise ValueError("Owner display name is required")
        if deployment_profile not in DEPLOYMENT_PROFILES:
            raise ValueError("Choose a supported deployment profile")
        if customer_compute not in {"local", "customer_server", "customer_cloud", "external_api_optional"}:
            raise ValueError("Choose a supported intelligence location")

        self.root.mkdir(parents=True, exist_ok=True)
        identity = IdentityStore(self.root / "identity").load_or_create()
        existing_owner = json.loads(self.owner_path.read_text()) if self.owner_path.exists() else None
        owner = existing_owner or {
            "schema_version": "aion.owner.v1",
            "owner_id": f"owner_{uuid4().hex}",
            "display_name": name,
            "created_at": utc_now_iso(),
            "roles": ["brain_owner", "mother_administrator"],
        }
        if existing_owner and existing_owner.get("display_name") != name:
            raise PermissionError("This brain is already owned; use the identity settings to rename its owner")
        _atomic_private_json(self.owner_path, owner)

        brain_id = f"brain_{identity.fingerprint}"
        boundary = SovereignBrainBoundary.bootstrap(
            self.root / "brain",
            brain_id=brain_id,
            owner_id=owner["owner_id"],
            public_key_fingerprint=identity.fingerprint,
        )
        SovereignBoardroomBridge(self.root).initialize()
        self.vault.initialize()
        self.supervisor.initialize()
        hardware = HardwareProfiler.profile(self.root)
        model_plan = HardwareProfiler.model_plan(hardware)
        _atomic_private_json(self.hardware_path, hardware)
        _atomic_private_json(self.model_plan_path, model_plan)
        requirements_profile = (
            json.loads(self.requirements_path.read_text(encoding="utf-8"))
            if business_requirements is None and self.requirements_path.exists()
            else BusinessRequirementsProfiler.profile(business_requirements)
        )
        _atomic_private_json(self.requirements_path, requirements_profile)

        setup = {
            "schema_version": SETUP_VERSION,
            "brain_id": brain_id,
            "owner_id": owner["owner_id"],
            "mother_fingerprint": identity.fingerprint,
            "deployment_profile": deployment_profile,
            "customer_compute": customer_compute,
            "data_controller": "customer",
            "tessaris_data_copy_required": False,
            "provider_keys_required": False,
            "demo_data_installed": False,
            "created_at": (json.loads(self.setup_path.read_text()).get("created_at") if self.setup_path.exists() else utc_now_iso()),
            "updated_at": utc_now_iso(),
        }
        _atomic_private_json(self.setup_path, setup)
        self._write_export_manifest(identity=identity, boundary=boundary)
        return self.status()

    def status(self) -> Dict[str, Any]:
        if not self.setup_path.exists():
            return {"ok": False, "state": "setup_required", "provider_keys_required": False}
        setup = json.loads(self.setup_path.read_text(encoding="utf-8"))
        identity_store = IdentityStore(self.root / "identity")
        if not identity_store.private_path.exists():
            return {
                "ok": False,
                "state": "restore_required",
                "reason": "mother_identity_missing",
                "provider_keys_required": False,
            }
        identity = identity_store.load_or_create()
        boundary = SovereignBrainBoundary(self.root / "brain").status()
        vault = self.vault.status()
        hardware = json.loads(self.hardware_path.read_text(encoding="utf-8"))
        model_plan = json.loads(self.model_plan_path.read_text(encoding="utf-8"))
        requirements_profile = json.loads(self.requirements_path.read_text(encoding="utf-8")) if self.requirements_path.exists() else BusinessRequirementsProfiler.profile()
        boardroom_business_map = SovereignBoardroomBridge(self.root).status()
        healthy = (
            setup.get("schema_version") == SETUP_VERSION
            and setup.get("mother_fingerprint") == identity.fingerprint
            and boundary.get("ok") is True
            and vault.get("ok") is True
        )
        return {
            "ok": healthy,
            "state": "ready" if healthy else "repair_required",
            "brain_id": setup.get("brain_id"),
            "owner_id": setup.get("owner_id"),
            "mother_fingerprint": identity.fingerprint,
            "deployment_profile": setup.get("deployment_profile"),
            "customer_compute": setup.get("customer_compute"),
            "provider_keys_required": False,
            "demo_data_installed": False,
            "canonical_stores": boundary.get("canonical_stores", []),
            "vault": vault,
            "hardware": {key: hardware.get(key) for key in ("os_family", "architecture", "cpu_count", "memory_bytes", "storage_free_bytes", "accelerator_class")},
            "model_plan": model_plan,
            "business_requirements": requirements_profile,
            "boardroom_business_map": boardroom_business_map,
            "runtime_supervisor": self.supervisor.status(),
        }

    def repair(self) -> Dict[str, Any]:
        """Repair regenerable metadata only; identity and vault-key loss fail closed."""
        if not self.setup_path.exists() or not self.owner_path.exists():
            raise RuntimeError("First-run setup must be completed before repair")
        identity_store = IdentityStore(self.root / "identity")
        if not identity_store.private_path.exists():
            raise RuntimeError("Mother identity is missing; restore an encrypted backup")
        if not self.vault.key_path.exists():
            raise RuntimeError("Vault key is missing; restore an encrypted backup")
        setup = json.loads(self.setup_path.read_text(encoding="utf-8"))
        owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
        identity = identity_store.load_or_create()
        SovereignBrainBoundary.bootstrap(
            self.root / "brain",
            brain_id=str(setup["brain_id"]),
            owner_id=str(owner["owner_id"]),
            public_key_fingerprint=identity.fingerprint,
        )
        self.vault.initialize()
        self.supervisor.initialize()
        if not self.hardware_path.exists():
            hardware = HardwareProfiler.profile(self.root)
            _atomic_private_json(self.hardware_path, hardware)
        if not self.model_plan_path.exists():
            hardware = json.loads(self.hardware_path.read_text(encoding="utf-8"))
            _atomic_private_json(self.model_plan_path, HardwareProfiler.model_plan(hardware))
        if not self.requirements_path.exists():
            _atomic_private_json(self.requirements_path, BusinessRequirementsProfiler.profile())
        self._write_export_manifest(identity=identity, boundary=SovereignBrainBoundary(self.root / "brain"))
        return self.status()

    def ownership(self) -> MotherOwnershipAuthority:
        setup = json.loads(self.setup_path.read_text(encoding="utf-8"))
        identity = IdentityStore(self.root / "identity").load_or_create()
        return MotherOwnershipAuthority(self.root, identity=identity, mother_id=str(setup["brain_id"]))

    def create_complete_export(self, *, destination: str | Path, passphrase: str) -> Dict[str, Any]:
        identity = IdentityStore(self.root / "identity").load_or_create()
        self._write_export_manifest(identity=identity, boundary=SovereignBrainBoundary(self.root / "brain"))
        return self.ownership().create_migration_export(
            source=self.root, destination=destination, passphrase=passphrase
        )

    @staticmethod
    def restore_complete_export(
        *, package: str | Path, destination: str | Path, passphrase: str, source_public_key: str
    ) -> Dict[str, Any]:
        target = Path(destination).resolve()
        if target.exists() and any(target.iterdir()):
            raise ValueError("Restore destination must be empty")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="aion-restore-", dir=target.parent) as temporary:
            temporary_root = Path(temporary)
            temporary_identity = IdentityStore(temporary_root / "identity").load_or_create()
            authority = MotherOwnershipAuthority(
                temporary_root / "authority", identity=temporary_identity, mother_id="restore_target"
            )
            result = authority.restore_migration_export(
                package=package,
                destination=target,
                passphrase=passphrase,
                source_public_key=source_public_key,
            )
        status = SovereignBrainSetup(target).status()
        if not status.get("ok"):
            raise RuntimeError("Restored sovereign brain failed its health check")
        return {**result, "brain_status": status, "logical_brain_preserved": True}

    def _write_export_manifest(self, *, identity: Any, boundary: SovereignBrainBoundary) -> None:
        stores: Dict[str, Dict[str, Any]] = {}
        for kind in CANONICAL_STORE_KINDS:
            stores[kind] = json.loads((boundary.stores_dir / f"{kind}.json").read_text(encoding="utf-8"))
        brain_identity = json.loads(boundary.identity_path.read_text(encoding="utf-8"))
        manifest = build_brain_export_manifest(brain_identity=brain_identity, stores=stores)
        payload = {**manifest, "mother_fingerprint": identity.fingerprint}
        payload["manifest_signature"] = identity.sign(canonical_bytes(payload))
        _atomic_private_json(self.root / "brain-export-manifest.json", payload)


def public_setup_choices() -> Dict[str, Any]:
    return {
        "schema_version": SETUP_VERSION,
        "deployment_profiles": [
            {"id": key, **value} for key, value in DEPLOYMENT_PROFILES.items()
        ],
        "intelligence_locations": [
            {"id": "local", "label": "This computer", "sends_data_externally": False},
            {"id": "customer_server", "label": "My private server", "sends_data_externally": False},
            {"id": "customer_cloud", "label": "My cloud account", "sends_data_externally": True},
            {"id": "external_api_optional", "label": "Optional AI provider", "sends_data_externally": True},
        ],
        "default_deployment": "personal_computer",
        "default_intelligence_location": "local",
        "provider_keys_required": False,
    }
