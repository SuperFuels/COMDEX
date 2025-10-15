import json
import tempfile
import os
from backend.modules.glyphwave.schema.validate_gwv import validate_gwv_file, safe_validate_gwv

def test_validate_gwv_pass(tmp_path):
    data = {
        "schema_version": "1.1",
        "container_id": "demo.qfc",
        "snapshot_count": 1,
        "stability": 0.95,
        "frames": [{
            "timestamp": "2025-10-15T00:00:00Z",
            "collapse_rate": 0.1,
            "decoherence_rate": 0.2,
            "frame": {"nodes": [], "edges": []}
        }]
    }
    fpath = tmp_path / "valid.gwv"
    with open(fpath, "w") as f:
        json.dump(data, f)
    assert validate_gwv_file(fpath)

def test_validate_gwv_fail(tmp_path):
    bad = {"schema_version": "1.1", "frames": []}
    fpath = tmp_path / "invalid.gwv"
    with open(fpath, "w") as f:
        json.dump(bad, f)
    assert safe_validate_gwv(fpath) is False