#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = REPO_ROOT / "backend" / "modules" / "aion_fabric"
PACKAGING = REPO_ROOT / "packaging" / "aion_fabric_preview"
DIST = REPO_ROOT / "dist"
EXTRA_SOURCE_FILES = (
    REPO_ROOT / "backend/modules/aion_business/runtime/business_connector_onboarding_service.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/sovereign_intelligence_router.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/signed_model_catalogue.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/compute_plugins.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_model_bindings.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_harness_context.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_evidence_engine.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_deliberation.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_governance.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/aion_flow_execution.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/capability_packages.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/medium_business_operating_service.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/governed_improvement_service.py",
    REPO_ROOT / "backend/modules/aion_business/runtime/commercial_assurance_service.py",
)


def _resolve_module(module: str) -> Path | None:
    candidate = REPO_ROOT.joinpath(*module.split("."))
    module_file = candidate.with_suffix(".py")
    if module_file.is_file():
        return module_file
    package_file = candidate / "__init__.py"
    return package_file if package_file.is_file() else None


def _internal_dependency_closure() -> list[Path]:
    """Resolve imported COMDEX modules without copying unrelated intelligence or runtime data."""
    pending = list(SOURCE_PACKAGE.glob("*.py")) + list(EXTRA_SOURCE_FILES)
    selected: set[Path] = set()
    while pending:
        source = pending.pop().resolve()
        if source in selected:
            continue
        selected.add(source)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        relative = source.relative_to(REPO_ROOT).with_suffix("")
        package_parts = list(relative.parts[:-1])
        for node in ast.walk(tree):
            modules: list[str] = []
            names: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names if alias.name != "*"]
                if node.level:
                    base = package_parts[: len(package_parts) - (node.level - 1)]
                    if node.module:
                        base.extend(node.module.split("."))
                    modules = [".".join(base)]
                elif node.module:
                    modules = [node.module]
            for module in modules:
                if not module.startswith("backend.modules."):
                    continue
                resolved = _resolve_module(module)
                if resolved and resolved not in selected:
                    pending.append(resolved)
                package_dir = REPO_ROOT.joinpath(*module.split("."))
                if package_dir.is_dir():
                    for name in names:
                        child = _resolve_module(f"{module}.{name}")
                        if child and child not in selected:
                            pending.append(child)
    return sorted(selected)


def _cached_speech_model() -> Path | None:
    model_root = Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-base"
    reference = model_root / "refs" / "main"
    if not reference.exists():
        return None
    revision = reference.read_text(encoding="utf-8").strip()
    snapshot = model_root / "snapshots" / revision
    return snapshot if snapshot.is_dir() else None


def build() -> Path:
    manifest = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    DIST.mkdir(parents=True, exist_ok=True)
    output = DIST / f"aion-fabric-preview-{version}.zip"

    with tempfile.TemporaryDirectory(prefix="aion-fabric-build-") as temp:
        root = Path(temp) / f"AION Fabric Preview {version}"
        dependencies = _internal_dependency_closure()
        package_target = root / "backend" / "modules" / "aion_fabric"
        package_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            SOURCE_PACKAGE,
            package_target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for source in dependencies:
            relative = source.relative_to(REPO_ROOT)
            if relative.parts[:3] == ("backend", "modules", "aion_fabric"):
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        package_dirs = {root / "backend", root / "backend" / "modules"}
        for source in dependencies:
            relative_parent = source.relative_to(REPO_ROOT).parent
            while relative_parent.parts and relative_parent.parts[0] == "backend":
                package_dirs.add(root / relative_parent)
                relative_parent = relative_parent.parent
        package_dirs.add(root / "backend" / "modules" / "aion_fabric")
        for package_dir in package_dirs:
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
        for name in ("README.md", "requirements.txt", "release_manifest.json", "Start AION Fabric.command", "Install Pilot.command", "Uninstall Pilot.command"):
            shutil.copy2(PACKAGING / name, root / name)
        speech_model = _cached_speech_model()
        if speech_model is None:
            raise FileNotFoundError("The pinned local faster-whisper base model is required for the offline release")
        shutil.copytree(speech_model, root / "models" / "faster-whisper-base", symlinks=False)
        for launcher_name in ("Start AION Fabric.command", "Install Pilot.command", "Uninstall Pilot.command"):
            launcher = root / launcher_name
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root.parent))
    return output


if __name__ == "__main__":
    print(build())
