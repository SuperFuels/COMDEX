from __future__ import annotations

import os
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


NODE_CAPABILITY_SCHEMA = "tessaris.node-capability.v1"
NODE_HEALTH_SCHEMA = "tessaris.node-health.v1"
SUPPORTED_SYSTEMS = frozenset({"darwin", "windows", "linux"})
SUPPORTED_ARCHITECTURES = frozenset({"x86_64", "amd64", "arm64", "aarch64"})


def _normalise_architecture(value: str) -> str:
    architecture = value.strip().lower()
    return {"x64": "x86_64", "amd64": "x86_64", "aarch64": "arm64"}.get(
        architecture, architecture
    )


def _memory_bytes() -> int | None:
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        return page_size * pages if page_size > 0 and pages > 0 else None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class NodeCapability:
    schema_version: str
    system: str
    architecture: str
    os_release: str
    cpu_logical_count: int
    memory_bytes: int | None
    available_storage_bytes: int
    profile: str
    qualified: bool
    limitations: tuple[str, ...]

    def content_free_payload(self) -> dict[str, Any]:
        return {**asdict(self), "limitations": list(self.limitations)}


def classify_node(
    *,
    system: str,
    architecture: str,
    os_release: str,
    cpu_logical_count: int,
    memory_bytes: int | None,
    available_storage_bytes: int,
) -> NodeCapability:
    system_name = system.strip().lower()
    normal_architecture = _normalise_architecture(architecture)
    limitations: list[str] = []
    if system_name not in SUPPORTED_SYSTEMS:
        limitations.append("operating_system_unqualified")
    if normal_architecture not in {"x86_64", "arm64"}:
        limitations.append("architecture_unqualified")
    if cpu_logical_count < 2:
        limitations.append("cpu_below_minimum")
    if memory_bytes is None:
        limitations.append("memory_unknown")
    elif memory_bytes < 4 * 1024**3:
        limitations.append("memory_below_minimum")
    if available_storage_bytes < 10 * 1024**3:
        limitations.append("storage_below_minimum")

    qualified = not any(item.endswith(("_unqualified", "_below_minimum")) for item in limitations)
    memory_gib = (memory_bytes or 0) / 1024**3
    storage_gib = available_storage_bytes / 1024**3
    if qualified and cpu_logical_count >= 12 and memory_gib >= 32 and storage_gib >= 100:
        profile = "compute-worker-capable"
    elif qualified and cpu_logical_count >= 4 and memory_gib >= 8 and storage_gib >= 20:
        profile = "node-capable"
    else:
        profile = "desktop-only"

    return NodeCapability(
        schema_version=NODE_CAPABILITY_SCHEMA,
        system=system_name,
        architecture=normal_architecture,
        os_release=os_release.strip(),
        cpu_logical_count=max(0, int(cpu_logical_count)),
        memory_bytes=memory_bytes,
        available_storage_bytes=max(0, int(available_storage_bytes)),
        profile=profile,
        qualified=qualified,
        limitations=tuple(sorted(set(limitations))),
    )


def probe_node(storage_root: str | Path) -> NodeCapability:
    storage = Path(storage_root).expanduser()
    existing = storage
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    available = shutil.disk_usage(existing).free
    return classify_node(
        system=platform.system(),
        architecture=platform.machine(),
        os_release=platform.release(),
        cpu_logical_count=os.cpu_count() or 0,
        memory_bytes=_memory_bytes(),
        available_storage_bytes=available,
    )


def node_health_snapshot(
    capability: NodeCapability,
    *,
    component_versions: Mapping[str, str],
    checks: Mapping[str, Callable[[], bool]],
    update_channel: str,
) -> dict[str, Any]:
    """Return a content-free local health view suitable for allowlisted telemetry."""

    permitted_channels = {"stable", "preview", "offline"}
    if update_channel not in permitted_channels:
        raise ValueError("update_channel_invalid")
    check_results: dict[str, str] = {}
    for name, check in sorted(checks.items()):
        try:
            check_results[name] = "healthy" if bool(check()) else "degraded"
        except Exception:
            check_results[name] = "unavailable"
    overall = "healthy" if capability.qualified and all(
        value == "healthy" for value in check_results.values()
    ) else "degraded"
    return {
        "schema_version": NODE_HEALTH_SCHEMA,
        "content_free": True,
        "overall": overall,
        "platform": {
            "system": capability.system,
            "architecture": capability.architecture,
            "profile": capability.profile,
            "qualified": capability.qualified,
        },
        "component_versions": {
            str(name): str(version) for name, version in sorted(component_versions.items())
        },
        "checks": check_results,
        "update_channel": update_channel,
    }
