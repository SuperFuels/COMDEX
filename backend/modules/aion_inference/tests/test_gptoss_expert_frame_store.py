import hashlib
import json
import subprocess

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssCompressedExpertFrameStore, GptOssExpertFrameStore,
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
