import hashlib
import json
import subprocess

from backend.modules.aion_inference.chunked_gguf_reader import ChunkedGGUFReader


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_cross_chunk_random_access_is_exact_and_bounded(tmp_path):
    raw_chunks = [b"GGUFabc", b"defghij", b"klm"]
    receipts = []
    for index, raw in enumerate(raw_chunks):
        encoded_path = tmp_path / f"chunk-{index}.zst"
        subprocess.run(["zstd", "-q", "-c"], input=raw,
                       stdout=encoded_path.open("wb"), check=True)
        encoded = encoded_path.read_bytes()
        receipts.append({
            "source_shard": "tiny.gguf", "chunk_index": index,
            "raw_bytes": len(raw), "raw_sha256": _sha(raw),
            "compressed_bytes": len(encoded), "compressed_sha256": _sha(encoded),
            "relative_path": encoded_path.name,
        })
    manifest = {
        "schema": "aion.chunked-gguf-warehouse.v1",
        "status": "COMPLETE_VERIFIED",
        "chunk_size_bytes": 7,
        "source_shards": [{"name": "tiny.gguf", "size": 17,
                            "sha256": _sha(b"".join(raw_chunks)),
                            "verified_sha256": _sha(b"".join(raw_chunks))}],
        "chunks": receipts,
    }
    path = tmp_path / "manifest.v1.json"
    path.write_text(json.dumps(manifest))
    reader = ChunkedGGUFReader(path, "tiny.gguf", cache_bytes=14)
    assert reader.read(4) == b"GGUF"
    assert reader.read_at(5, 9) == b"bcdefghij"
    assert reader.seek(-3, 2) == 14
    assert reader.read() == b"klm"
    assert reader.metrics()["cache_resident_bytes"] <= 14


def test_rejects_unverified_manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": "aion.chunked-gguf-warehouse.v1",
                                "status": "IN_PROGRESS"}))
    try:
        ChunkedGGUFReader(path, "tiny.gguf")
    except ValueError as exc:
        assert "not complete and verified" in str(exc)
    else:
        raise AssertionError("reader accepted an unverified warehouse")
