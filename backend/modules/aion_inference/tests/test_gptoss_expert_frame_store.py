import hashlib
import json
import subprocess
import ctypes

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    ctypes_component_pointer_array,
    GptOssCompressedExpertFrameStore, GptOssExpertFrameStore,
    GptOssMappedPersistentL2ExpertFrameStore,
    GptOssPinnedVerifiedPersistentL2ExpertFrameStore,
    GptOssPersistentL2ExpertFrameStore,
    GptOssReusableArenaPersistentL2ExpertFrameStore,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _region(tmp_path, index, name, raw, expert=0):
    path = tmp_path / f"region-{index}.zstpack"
    subprocess.run(["zstd", "-q", "-c"], input=raw,
                   stdout=path.open("wb"), check=True)
    encoded = path.read_bytes()
    return {
        "region_name": name, "pack_relative_path": path.name,
        "frames": [{"expert": expert, "encoded_offset": 0,
                    "compressed_bytes": len(encoded), "compressed_sha256": _sha(encoded),
                    "raw_bytes": len(raw), "raw_sha256": _sha(raw)}],
    }


def test_reads_six_components_and_caches_complete_expert(tmp_path):
    regions = []
    expected = {}
    index = 0
    for projection in ("gate", "up", "down"):
        expected[projection] = {}
        for kind in ("weight", "bias"):
            raw = f"{projection}-{kind}".encode() * 100
            expected[projection][kind] = raw
            regions.append(_region(tmp_path, index,
                                   f"blk.0.ffn_{projection}_exps.{kind}", raw))
            index += 1
    manifest = {"schema": "aion.expert-frame-warehouse.v1",
                "status": "COMPLETE_VERIFIED", "regions": regions}
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps(manifest))
    total = sum(len(value) for projection in expected.values() for value in projection.values())
    store = GptOssExpertFrameStore(manifest_path, total)
    assert store.get(0, 0) == expected
    assert store.get(0, 0) == expected
    assert store.metrics()["faults"] == 1
    assert store.metrics()["hits"] == 1
    assert store.metrics()["resident_bytes"] == total


def test_rejects_duplicate_route(tmp_path):
    regions = [_region(tmp_path, 0, "blk.0.ffn_gate_exps.weight", b"x")]
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    store = GptOssExpertFrameStore(manifest_path, 0)
    try:
        store.get_layer_route(0, [0, 0])
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate route was accepted")


def test_parallel_route_faults_then_reuses_two_complete_experts(tmp_path):
    regions = []
    expected = []
    index = 0
    for expert in (0, 1):
        value = {}
        for projection in ("gate", "up", "down"):
            value[projection] = {}
            for kind in ("weight", "bias"):
                raw = f"{expert}-{projection}-{kind}".encode() * 100
                value[projection][kind] = raw
                regions.append(_region(tmp_path, index,
                    f"blk.0.ffn_{projection}_exps.{kind}", raw, expert=expert))
                index += 1
        expected.append(value)
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    total = sum(len(component) for value in expected for projection in value.values()
                for component in projection.values())
    store = GptOssExpertFrameStore(manifest_path, total)
    assert store.get_layer_route_parallel(0, [0, 1], workers=2) == expected
    assert store.get_layer_route_parallel(0, [0, 1], workers=2) == expected
    assert store.metrics()["faults"] == 2
    assert store.metrics()["hits"] == 2


def test_protected_raw_pool_makes_later_miss_transient(tmp_path):
    regions = []
    expected = []
    index = 0
    for expert in (0, 1):
        value = {}
        for projection in ("gate", "up", "down"):
            value[projection] = {}
            for kind in ("weight", "bias"):
                raw = f"{expert}-{projection}-{kind}".encode() * 100
                value[projection][kind] = raw
                regions.append(_region(tmp_path, index,
                    f"blk.0.ffn_{projection}_exps.{kind}", raw, expert=expert))
                index += 1
        expected.append(value)
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    one_expert = sum(len(component) for projection in expected[0].values()
                     for component in projection.values())
    store = GptOssExpertFrameStore(manifest_path, one_expert)
    assert store.get(0, 0) == expected[0]
    store.protect({"0": [0]})
    assert store.get(0, 1) == expected[1]
    assert store.get(0, 0) == expected[0]
    assert store.metrics()["protected_entries"] == 1
    assert store.metrics()["admission_bypasses"] == 1
    assert store.metrics()["evictions"] == 0


def test_admission_allowlist_builds_pool_during_exact_reads(tmp_path):
    regions = []
    expected = []
    index = 0
    for expert in (0, 1):
        value = {}
        for projection in ("gate", "up", "down"):
            value[projection] = {}
            for kind in ("weight", "bias"):
                raw = f"{expert}-{projection}-{kind}".encode() * 100
                value[projection][kind] = raw
                regions.append(_region(tmp_path, index,
                    f"blk.0.ffn_{projection}_exps.{kind}", raw, expert=expert))
                index += 1
        expected.append(value)
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    capacity = sum(len(component) for value in expected for projection in value.values()
                   for component in projection.values())
    store = GptOssExpertFrameStore(manifest_path, capacity)
    store.set_admission_allowlist({"0": [0]})
    assert store.get(0, 1) == expected[1]
    assert store.get(0, 0) == expected[0]
    assert store.get(0, 0) == expected[0]
    metrics = store.metrics()
    assert metrics["admission_allowlist_entries"] == 1
    assert metrics["admission_bypasses"] == 1
    assert metrics["resident_bytes"] < capacity
    assert metrics["hits"] == 1


def test_protected_core_retains_an_unprotected_lru_halo(tmp_path):
    regions = []
    expected = []
    index = 0
    for expert in (0, 1, 2):
        value = {}
        for projection in ("gate", "up", "down"):
            value[projection] = {}
            for kind in ("weight", "bias"):
                raw = f"{expert}-{projection}-{kind}".encode() * 100
                value[projection][kind] = raw
                regions.append(_region(
                    tmp_path, index, f"blk.0.ffn_{projection}_exps.{kind}",
                    raw, expert=expert,
                ))
                index += 1
        expected.append(value)
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({
        "schema": "aion.expert-frame-warehouse.v1",
        "status": "COMPLETE_VERIFIED",
        "regions": regions,
    }))
    one_expert = sum(len(component) for projection in expected[0].values()
                     for component in projection.values())
    store = GptOssExpertFrameStore(manifest_path, 2 * one_expert)
    assert store.get(0, 0) == expected[0]
    store.protect({"0": [0]})
    assert store.get(0, 1) == expected[1]
    assert store.get(0, 1) == expected[1]
    assert store.get(0, 2) == expected[2]
    assert store.get(0, 0) == expected[0]
    metrics = store.metrics()
    assert metrics["protected_entries"] == 1
    assert metrics["evictions"] == 1
    assert metrics["hits"] == 2
    assert metrics["admission_bypasses"] == 0


def test_compressed_cache_redecodes_without_second_physical_read(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index, f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    capacity = sum(frame["frames"][0]["compressed_bytes"] for frame in regions)
    store = GptOssCompressedExpertFrameStore(manifest_path, capacity)
    assert store.get(0, 0) == expected
    physical = store.metrics()["compressed_bytes_read"]
    assert store.get(0, 0) == expected
    assert store.metrics()["compressed_bytes_read"] == physical
    assert store.metrics()["hits"] == 1
    assert store.metrics()["cache_representation"] == "verified_compressed_frames"


def test_persistent_l2_reuses_exact_expert_across_store_instances(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    first = GptOssPersistentL2ExpertFrameStore(manifest_path, 0, l2_root, 1024 * 1024)
    assert first.get(0, 0) == expected
    assert first.metrics()["sd_fallbacks"] == 1
    second = GptOssPersistentL2ExpertFrameStore(manifest_path, 0, l2_root, 1024 * 1024)
    assert second.get(0, 0) == expected
    metrics = second.metrics()
    assert metrics["l2_hits"] == 1
    assert metrics["sd_fallbacks"] == 0
    assert metrics["l2_entries"] == 1


def test_persistent_l2_rejects_corruption_and_repairs_from_source(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    first = GptOssPersistentL2ExpertFrameStore(manifest_path, 0, l2_root, 1024 * 1024)
    assert first.get(0, 0) == expected
    frame = next(l2_root.rglob("*.aionraw"))
    payload = bytearray(frame.read_bytes())
    payload[-1] ^= 0xFF
    frame.write_bytes(payload)
    repaired = GptOssPersistentL2ExpertFrameStore(manifest_path, 0, l2_root, 1024 * 1024)
    assert repaired.get(0, 0) == expected
    metrics = repaired.metrics()
    assert metrics["l2_integrity_failures"] == 1
    assert metrics["sd_fallbacks"] == 1


def test_persistent_l2_bypass_avoids_duplicate_disk_frame(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    store = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 1024 * 1024, tmp_path / "l2", 1024 * 1024)
    store.set_l2_bypass({"0": [0]})
    assert store.get(0, 0) == expected
    metrics = store.metrics()
    assert metrics["l2_bypass_entries"] == 1
    assert metrics["l2_entries"] == 0
    assert metrics["l2_bytes_written"] == 0


def test_persistent_l2_cartridge_protection_never_evicts_protected_expert(tmp_path):
    regions = []
    expected = []
    index = 0
    for expert in (0, 1):
        value = {}
        for projection in ("gate", "up", "down"):
            value[projection] = {}
            for kind in ("weight", "bias"):
                raw = f"{expert}-{projection}-{kind}".encode() * 100
                value[projection][kind] = raw
                regions.append(_region(
                    tmp_path, index, f"blk.0.ffn_{projection}_exps.{kind}",
                    raw, expert=expert))
                index += 1
        expected.append(value)
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({
        "schema": "aion.expert-frame-warehouse.v1",
        "status": "COMPLETE_VERIFIED", "regions": regions,
    }))
    first_size = 56 + sum(len(component) for component in expected[0].values()
                          for component in component.values())
    store = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, tmp_path / "l2", first_size)
    store.set_l2_protected({"0": [0]})
    assert store.get(0, 0) == expected[0]
    assert store.get(0, 1) == expected[1]
    assert store.get(0, 0) == expected[0]
    metrics = store.metrics()
    assert metrics["l2_entries"] == 1
    assert metrics["l2_protected_entries"] == 1
    assert metrics["l2_protected_resident_entries"] == 1
    assert metrics["l2_hits"] == 1
    assert metrics["sd_fallbacks"] == 2


def test_mapped_l2_verifies_once_then_reuses_views_without_materializing(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert populate.get(0, 0) == expected
    mapped = GptOssMappedPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    first = mapped.get(0, 0)
    second = mapped.get(0, 0)
    assert first == expected
    assert second == expected
    assert isinstance(first["gate"]["weight"], memoryview)
    metrics = mapped.metrics()
    assert metrics["l2_verification_passes"] == 1
    assert metrics["l2_verification_reuses"] == 1
    assert metrics["raw_bytes_materialized"] == 0
    assert metrics["mapped_l2_hits"] == 2


def test_new_mapped_store_revalidates_changed_file_and_repairs_from_sd(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert populate.get(0, 0) == expected
    mapped = GptOssMappedPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    value = mapped.get(0, 0)
    assert value == expected
    del value
    frame = next(l2_root.rglob("*.aionraw"))
    payload = bytearray(frame.read_bytes())
    payload[-1] ^= 0xFF
    frame.write_bytes(payload)
    del mapped
    reopened = GptOssMappedPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert reopened.get(0, 0) == expected
    metrics = reopened.metrics()
    assert metrics["l2_integrity_failures"] == 1
    assert metrics["sd_fallbacks"] == 1


def test_pinned_verified_l2_hashes_once_but_keeps_bulk_copies(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert populate.get(0, 0) == expected
    pinned = GptOssPinnedVerifiedPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert pinned.get(0, 0) == expected
    assert pinned.get(0, 0) == expected
    metrics = pinned.metrics()
    assert metrics["l2_verification_passes"] == 1
    assert metrics["l2_verification_reuses"] == 1
    assert metrics["l2_hits"] == 2
    assert metrics["raw_bytes_materialized"] > 0


def test_new_pinned_verified_store_revalidates_and_repairs_corruption(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert populate.get(0, 0) == expected
    frame = next(l2_root.rglob("*.aionraw"))
    payload = bytearray(frame.read_bytes())
    payload[-1] ^= 0xFF
    frame.write_bytes(payload)
    reopened = GptOssPinnedVerifiedPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    assert reopened.get(0, 0) == expected
    metrics = reopened.metrics()
    assert metrics["l2_integrity_failures"] == 1
    assert metrics["sd_fallbacks"] == 1


def test_reusable_route_arena_returns_exact_writable_views(tmp_path):
    regions = []
    expected = {}
    for expert in range(4):
        expected[expert] = {}
        for index, (projection, kind) in enumerate(
                (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
            raw = f"{expert}-{projection}-{kind}".encode() * 100
            expected[expert].setdefault(projection, {})[kind] = raw
            regions.append(_region(tmp_path, expert * 6 + index,
                                   f"blk.0.ffn_{projection}_exps.{kind}", raw,
                                   expert=expert))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1",
                                         "status": "COMPLETE_VERIFIED", "regions": regions}))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    for expert in range(4):
        assert populate.get(0, expert) == expected[expert]
    arena = GptOssReusableArenaPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    values = arena.get_layer_route_parallel(0, [0, 1, 2, 3], workers=4)
    assert values == [expected[index] for index in range(4)]
    assert all(isinstance(value["gate"]["weight"], memoryview) for value in values)
    first = arena.read_verified_l2_component_group_into_slot(
        0, 0, 0, (0, 1, 2, 3))
    second = arena.read_verified_l2_component_group_into_slot(
        0, 0, 0, (4, 5))
    assert first == {"gate": expected[0]["gate"], "up": expected[0]["up"]}
    assert second == {"down": expected[0]["down"]}
    metrics = arena.metrics()
    assert metrics["route_arena_reads"] == 4
    assert metrics["l2_verification_passes"] == 4
    assert metrics["sd_fallbacks"] == 0
    assert metrics["partial_l2_read_calls"] == 2


def test_reusable_route_arena_admits_only_declared_l1_hotset(tmp_path):
    regions = []
    expected = {}
    for expert in range(2):
        expected[expert] = {}
        for index, (projection, kind) in enumerate(
                (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
            raw = f"{expert}-{projection}-{kind}".encode() * 100
            expected[expert].setdefault(projection, {})[kind] = raw
            regions.append(_region(
                tmp_path, expert * 6 + index,
                f"blk.0.ffn_{projection}_exps.{kind}", raw, expert=expert))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({
        "schema": "aion.expert-frame-warehouse.v1",
        "status": "COMPLETE_VERIFIED", "regions": regions,
    }))
    l2_root = tmp_path / "l2"
    populate = GptOssPersistentL2ExpertFrameStore(
        manifest_path, 0, l2_root, 1024 * 1024)
    for expert in range(2):
        assert populate.get(0, expert) == expected[expert]
    hot_size = sum(len(component) for components in expected[0].values()
                   for component in components.values())
    arena = GptOssReusableArenaPersistentL2ExpertFrameStore(
        manifest_path, hot_size, l2_root, 1024 * 1024)
    arena.set_route_arena_l1_allowlist({"0": [0]})
    assert arena.get_layer_route_parallel(0, [0, 1], workers=2) == [
        expected[0], expected[1]]
    assert arena.get_layer_route_parallel(0, [0, 1], workers=2) == [
        expected[0], expected[1]]
    metrics = arena.metrics()
    assert metrics["route_arena_reads"] == 3
    assert metrics["route_arena_l1_allowlist_entries"] == 1
    assert metrics["route_arena_l1_admissions"] == 1
    assert metrics["route_arena_l1_admission_bytes"] == hot_size
    assert metrics["hits"] == 1


def test_reusable_route_arena_direct_hotset_admission_is_idempotent(tmp_path):
    regions = []
    expected = {}
    for index, (projection, kind) in enumerate(
            (p, k) for p in ("gate", "up", "down") for k in ("weight", "bias")):
        raw = f"0-{projection}-{kind}".encode() * 100
        expected.setdefault(projection, {})[kind] = raw
        regions.append(_region(tmp_path, index,
                               f"blk.0.ffn_{projection}_exps.{kind}", raw))
    manifest_path = tmp_path / "manifest.v1.json"
    manifest_path.write_text(json.dumps({
        "schema": "aion.expert-frame-warehouse.v1",
        "status": "COMPLETE_VERIFIED", "regions": regions,
    }))
    hot_size = sum(len(component) for components in expected.values()
                   for component in components.values())
    arena = GptOssReusableArenaPersistentL2ExpertFrameStore(
        manifest_path, hot_size, tmp_path / "l2", 1024 * 1024)
    arena.set_route_arena_l1_allowlist({"0": [0]})
    first = arena.maybe_admit_route_arena_l1(0, 0, expected)
    second = arena.maybe_admit_route_arena_l1(0, 0, expected)
    assert first == expected
    assert second == expected
    assert arena.metrics()["route_arena_l1_admissions"] == 1


def test_component_pointer_array_uses_buffer_without_copy():
    raw = bytearray(b"mapped-packed-weight")
    view = memoryview(raw)
    references, pointers = ctypes_component_pointer_array([view, b"bias"])
    assert ctypes.string_at(pointers[0], len(raw)) == raw
    assert ctypes.string_at(pointers[1], 4) == b"bias"
    raw[0] = ord("M")
    assert ctypes.string_at(pointers[0], len(raw)) == raw
    assert len(references) == 2
