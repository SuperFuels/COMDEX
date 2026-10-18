from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.node_capabilities import (
    NODE_HEALTH_SCHEMA,
    classify_node,
    node_health_snapshot,
)


def test_platform_and_architecture_are_normalised():
    capability = classify_node(
        system="Windows",
        architecture="AMD64",
        os_release="11",
        cpu_logical_count=8,
        memory_bytes=16 * 1024**3,
        available_storage_bytes=80 * 1024**3,
    )
    assert capability.system == "windows"
    assert capability.architecture == "x86_64"
    assert capability.profile == "node-capable"
    assert capability.qualified is True


def test_large_supported_machine_is_compute_worker_capable():
    capability = classify_node(
        system="Linux",
        architecture="aarch64",
        os_release="6",
        cpu_logical_count=16,
        memory_bytes=64 * 1024**3,
        available_storage_bytes=200 * 1024**3,
    )
    assert capability.architecture == "arm64"
    assert capability.profile == "compute-worker-capable"


def test_unsupported_or_too_small_machine_is_not_overpromised():
    capability = classify_node(
        system="Plan9",
        architecture="mips",
        os_release="1",
        cpu_logical_count=1,
        memory_bytes=2 * 1024**3,
        available_storage_bytes=2 * 1024**3,
    )
    assert capability.profile == "desktop-only"
    assert capability.qualified is False
    assert "operating_system_unqualified" in capability.limitations
    assert "storage_below_minimum" in capability.limitations


def test_health_snapshot_is_content_free_and_bounded():
    capability = classify_node(
        system="Darwin",
        architecture="arm64",
        os_release="25",
        cpu_logical_count=10,
        memory_bytes=16 * 1024**3,
        available_storage_bytes=100 * 1024**3,
    )
    result = node_health_snapshot(
        capability,
        component_versions={"guardian": "1.0.0", "node": "1.1.0"},
        checks={"guardian": lambda: True, "backup": lambda: False},
        update_channel="stable",
    )
    assert result["schema_version"] == NODE_HEALTH_SCHEMA
    assert result["content_free"] is True
    assert result["overall"] == "degraded"
    assert set(result) == {
        "schema_version",
        "content_free",
        "overall",
        "platform",
        "component_versions",
        "checks",
        "update_channel",
    }


def test_unknown_update_channel_is_rejected():
    capability = classify_node(
        system="Linux",
        architecture="x86_64",
        os_release="6",
        cpu_logical_count=8,
        memory_bytes=16 * 1024**3,
        available_storage_bytes=100 * 1024**3,
    )
    with pytest.raises(ValueError, match="update_channel_invalid"):
        node_health_snapshot(
            capability,
            component_versions={},
            checks={},
            update_channel="untrusted",
        )
