import json

from backend.modules.aion_inference.qwen_expert_glyph_store import QwenExpertGlyphStore


def _fixture(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(bytes(range(120)))
    experts = []
    for expert in range(4):
        ranges = {}
        for projection_index, projection in enumerate(("gate", "up", "down")):
            ranges[projection] = {
                "absolute_offset": expert * 30 + projection_index * 10,
                "byte_length": 10,
            }
        experts.append({"expert": expert, "byte_length": 30, "ranges": ranges})
    manifest = tmp_path / "index.json"
    manifest.write_text(json.dumps({
        "schema": "aion.qwen3moe.gguf-expert-addresses.v1",
        "source_path": str(model),
        "source_bytes": 120,
        "layers": [{"layer": 0, "experts": experts}],
    }))
    return manifest


def test_budgeted_lru_reads_exact_ranges(tmp_path):
    manifest = _fixture(tmp_path)
    with QwenExpertGlyphStore(manifest, capacity_bytes=60) as store:
        first = store.get(0, 0)
        assert b"".join(first) == bytes(range(30))
        store.get(0, 1)
        store.get(0, 0)
        store.get(0, 2)
        assert store.metrics() == {
            "capacity_bytes": 60,
            "resident_bytes": 60,
            "peak_resident_bytes": 60,
            "hits": 1,
            "faults": 3,
            "hit_rate": 0.25,
            "physical_bytes": 90,
            "evictions": 1,
        }


def test_zero_capacity_never_retains(tmp_path):
    manifest = _fixture(tmp_path)
    with QwenExpertGlyphStore(manifest, capacity_bytes=0) as store:
        store.get(0, 3)
        store.get(0, 3)
        assert store.metrics()["faults"] == 2
        assert store.metrics()["resident_bytes"] == 0
