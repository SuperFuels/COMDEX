import hashlib
import json
import subprocess
import sys

import pytest


def _canonical(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def test_derives_stricter_selected_layer_plan(tmp_path):
    source = tmp_path / "source.json"
    output = tmp_path / "derived.json"
    source.write_text(json.dumps({
        "schema": "aion.gptoss-120b-top1-threshold-plan.v1",
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "minimum_top_gate_gap_by_layer": {"0": 0.2, "1": 0.3, "33": 0.4},
        "selection": {"development_families": ["arithmetic", "extraction"]},
        "sources": [],
        "canonical_sha256": "source-canonical",
    }))
    subprocess.run([
        sys.executable,
        "backend/scripts/derive_aion_gptoss_top1_threshold_plan.py",
        "--input", str(source),
        "--output", str(output),
        "--absolute-margin", "0.1",
        "--layers", "0,33",
    ], check=True)
    result = json.loads(output.read_text())
    claimed = result.pop("canonical_sha256")
    assert result["schema"] == "aion.gptoss-120b-top1-threshold-plan.v1"
    assert result["selected_layers"] == [0, 33]
    assert result["minimum_top_gate_gap_by_layer"] == pytest.approx({"0": 0.3, "33": 0.5})
    assert claimed == _canonical(result)
