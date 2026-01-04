from __future__ import annotations

import json
from pathlib import Path

from backend.genome_engine.gx1_builder import build_gx1_payload
from backend.genome_engine.replay_runner import verify_replay_bundle
from backend.genome_engine.stable_json import stable_stringify
    
def test_gx1_replay_roundtrip(tmp_path: Path) -> None:
    # Minimal deterministic dataset
    ds = tmp_path / "ds.jsonl"
    ds.write_text(
        json.dumps({"id": "r0", "seq": "ACGTACGTACGT"}) + "\n"
        + json.dumps({"id": "r1", "seq": "TGCATGCA"}) + "\n",
        encoding="utf-8",
    )

    cfg = {
        "dataset_path": str(ds),
        "output_root": str(tmp_path / "P21_GX1"),
        "seed": 1337,
        "mode": "sim",
        # keep trace small and deterministic for test speed
        "trace_mode": "sampled",
        "trace_stride": 4,
        "trace_max_events": 512,
        "steps": 256,
    }

    payload = build_gx1_payload(cfg)
    replay = payload["replay_bundle"]

    rp = tmp_path / "REPLAY_BUNDLE.json"
    rp.write_text(stable_stringify(replay) + "\n", encoding="utf-8")

    r = verify_replay_bundle(str(rp))
    assert r["ok"] is True, r
