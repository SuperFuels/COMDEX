import hashlib
import json
import subprocess

import pytest

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _warehouse(tmp_path, status="COMPLETE_VERIFIED"):
    raw_frames = [b"GGUFabc", b"defghij", b"klmnop"]
    regions = []
    offset = 0
    for index, raw in enumerate(raw_frames):
        pack = tmp_path / f"region-{index}.zstpack"
        subprocess.run(["zstd", "-q", "-c"], input=raw,
                       stdout=pack.open("wb"), check=True)
        encoded = pack.read_bytes()
        regions.append({
            "source_shard": "tiny.gguf", "source_offset": offset,
            "raw_bytes": len(raw), "pack_relative_path": pack.name,
            "frames": [{"relative_offset": 0, "encoded_offset": 0,
                        "compressed_bytes": len(encoded),
                        "compressed_sha256": _sha(encoded),
                        "raw_bytes": len(raw), "raw_sha256": _sha(raw)}],
        })
        offset += len(raw)
    complete = b"".join(raw_frames)
    manifest = {
        "schema": "aion.expert-frame-warehouse.v1", "status": status,
        "verified_sources": [{"name": "tiny.gguf", "size": len(complete),
                              "expected_sha256": _sha(complete),
                              "verified_sha256": _sha(complete)}],
        "regions": regions,
    }
    path = tmp_path / "manifest.v1.json"
    path.write_text(json.dumps(manifest))
    return path, complete


def test_cross_frame_random_access_is_exact_and_bounded(tmp_path):
    manifest, complete = _warehouse(tmp_path)
    reader = ExpertFrameGGUFReader(manifest, "tiny.gguf", cache_bytes=14)
    assert reader.read(4) == b"GGUF"
    assert reader.read_at(5, 11) == complete[5:16]
    assert reader.seek(-4, 2) == len(complete) - 4
    assert reader.read() == complete[-4:]
    metrics = reader.metrics()
    assert metrics["cache_resident_bytes"] <= 14
    assert metrics["peak_resident_bytes"] <= 14


def test_rejects_unverified_or_incomplete_warehouse(tmp_path):
    manifest, _ = _warehouse(tmp_path, status="IN_PROGRESS")
    with pytest.raises(ValueError, match="not complete and verified"):
        ExpertFrameGGUFReader(manifest, "tiny.gguf")


def test_rejects_source_hash_disagreement(tmp_path):
    manifest, _ = _warehouse(tmp_path)
    value = json.loads(manifest.read_text())
    value["verified_sources"][0]["verified_sha256"] = "0" * 64
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="source shard hash is not verified"):
        ExpertFrameGGUFReader(manifest, "tiny.gguf")
