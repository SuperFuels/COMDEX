from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def test_gx1_dataset_sha256_matches_dataset_bytes(tmp_path: Path) -> None:
    dataset_path = "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl"
    out_root = tmp_path / "P21_GX1_TEST"

    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": dataset_path,
        "output_root": str(out_root),
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
    }

    r = run_genomics_benchmark(cfg)
    run_dir = Path(r["run_dir"])

    cfg_written = json.loads((run_dir / "CONFIG.json").read_text(encoding="utf-8"))
    replay = json.loads((run_dir / "REPLAY_BUNDLE.json").read_text(encoding="utf-8"))

    expect = _sha256_file(dataset_path)

    assert cfg_written["dataset_sha256"] == expect
    assert replay["dataset_sha256"] == expect
    assert cfg_written["dataset_id"] == Path(dataset_path).name
    assert replay["dataset_id"] == Path(dataset_path).name
