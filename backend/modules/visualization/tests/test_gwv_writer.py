import os
import json
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer, GWVWriter


def test_snapshot_ringbuffer_stability_and_export(tmp_path):
    buf = SnapshotRingBuffer(maxlen=5)
    for i in range(5):
        buf.add_snapshot({"frame_id": i}, collapse_rate=0.1 * i, decoherence_rate=0.05 * i)
    stability = buf.compute_stability_metric()
    assert 0.0 <= stability <= 1.0

    path = buf.export_to_gwv("test_container", output_dir=tmp_path)
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert "frames" in data and len(data["frames"]) == 5
    assert "stability" in data


def test_gwv_writer_multi_container_recording(tmp_path):
    writer = GWVWriter(output_dir=tmp_path)
    for cid in ["a.dc", "b.dc"]:
        for i in range(3):
            frame = {"tick": i, "visual": f"frame_{i}"}
            writer.record_frame(cid, frame, collapse_rate=0.05, decoherence_rate=0.03)
        path = writer.flush_to_disk(cid)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["snapshot_count"] == 3
        assert "stability" in data