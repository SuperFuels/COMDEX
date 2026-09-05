#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGING = REPO_ROOT / "packaging" / "aion_sovereign_brain_bootstrap"
DIST = REPO_ROOT / "dist"
SOURCE_FILES = (
    "backend/modules/aion_business/contracts/sovereign_brain.py",
    "backend/modules/aion_business/contracts/intelligence.py",
    "backend/modules/aion_business/contracts/business_containers.py",
    "backend/modules/aion_business/runtime/paths.py",
    "backend/modules/aion_business/runtime/canonical_business_identity.py",
    "backend/modules/aion_business/runtime/business_container_repository.py",
    "backend/modules/aion_business/runtime/business_map_governance_service.py",
    "backend/modules/aion_business/runtime/business_knowledge_service.py",
    "backend/modules/aion_business/runtime/business_connector_onboarding_service.py",
    "backend/modules/aion_business/runtime/foundation_onboarding_session_service.py",
    "backend/modules/aion_business/runtime/workflow_file_cabinet_repository.py",
    "backend/modules/aion_business/runtime/sovereign_brain_boundary.py",
    "backend/modules/aion_business/runtime/sovereign_intelligence_router.py",
    "backend/modules/aion_business/runtime/signed_model_catalogue.py",
    "backend/modules/aion_business/runtime/compute_plugins.py",
    "backend/modules/aion_business/runtime/aion_flow_model_bindings.py",
    "backend/modules/aion_business/runtime/aion_flow_harness_context.py",
    "backend/modules/aion_business/runtime/aion_flow_evidence_engine.py",
    "backend/modules/aion_business/runtime/aion_flow_deliberation.py",
    "backend/modules/aion_business/runtime/aion_flow_governance.py",
    "backend/modules/aion_business/runtime/capability_packages.py",
    "backend/modules/aion_business/runtime/medium_business_operating_service.py",
    "backend/modules/aion_business/runtime/governed_improvement_service.py",
    "backend/modules/aion_business/runtime/commercial_assurance_service.py",
    "backend/modules/aion_business/runtime/commercial_adoption_service.py",
    "backend/modules/aion_business/runtime/payment_boundary_service.py",
    "backend/modules/aion_business/runtime/sovereign_capacity_planner.py",
    "backend/modules/aion_business/runtime/sovereign_migration_orchestrator.py",
    "backend/modules/aion_business/runtime/sovereign_boardroom_bridge.py",
    "backend/modules/aion_business/runtime/sovereign_brain_setup.py",
    "backend/modules/aion_business/runtime/sovereign_setup_service.py",
    "backend/modules/aion_business/runtime/sovereign_runtime_supervisor.py",
    "backend/modules/aion_business/runtime/sovereign_installed_service.py",
    "backend/modules/aion_business/runtime/sovereign_windows_service.py",
    "backend/modules/aion_business/runtime/sovereign_update_service.py",
    "backend/modules/aion_fabric/canonical.py",
    "backend/modules/aion_fabric/identity.py",
    "backend/modules/pilot_unified/ownership.py",
)
PACKAGE_FILES = (
    "requirements.txt",
    "release_manifest.json",
    "Set Up Pilot.command",
    "set-up-pilot.sh",
    "Set-Up-Pilot.ps1",
    "README.md",
)


def build() -> Path:
    release = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    version = str(release["version"])
    DIST.mkdir(parents=True, exist_ok=True)
    output = DIST / f"aion-sovereign-brain-bootstrap-{version}.zip"
    with tempfile.TemporaryDirectory(prefix="aion-brain-bootstrap-") as temporary:
        root = Path(temporary) / f"AION Sovereign Brain Bootstrap {version}"
        records = []
        for relative_name in SOURCE_FILES:
            source = REPO_ROOT / relative_name
            target = root / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            raw = target.read_bytes()
            records.append({"path": relative_name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        for package_name in PACKAGE_FILES:
            source = PACKAGING / package_name
            target = root / package_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            raw = target.read_bytes()
            records.append({"path": package_name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        for package_dir in (
            "backend",
            "backend/modules",
            "backend/modules/aion_business",
            "backend/modules/aion_business/contracts",
            "backend/modules/aion_business/runtime",
            "backend/modules/aion_fabric",
            "backend/modules/pilot_unified",
        ):
            init_path = root / package_dir / "__init__.py"
            init_path.write_text("", encoding="utf-8")
            raw = init_path.read_bytes()
            records.append({
                "path": init_path.relative_to(root).as_posix(),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        integrity = {
            "schema_version": "aion.bootstrap-integrity.v1",
            "release": release,
            "files": sorted(records, key=lambda item: item["path"]),
            "contains_customer_data": False,
            "contains_provider_credentials": False,
            "cryptographic_distribution_signature": False,
        }
        (root / "integrity-manifest.json").write_text(
            json.dumps(integrity, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
        for launcher in (root / "Set Up Pilot.command", root / "set-up-pilot.sh"):
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root.parent))
    return output


if __name__ == "__main__":
    print(build())
