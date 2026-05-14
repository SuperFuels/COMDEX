from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


DATA_P16_CANON = "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _run_once(tmp_root: Path) -> dict:
    out_root = tmp_root / "P21_GX1"
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": DATA_P16_CANON,
        "output_root": str(out_root),
        # pin run_id so we compare apples-to-apples
        "run_id": "P21_GX1_TEST_S1337",
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
        "thresholds": {
            "warmup_ticks": 128,
            "eval_ticks": 512,
            "rho_matched_min": 0.80,
            "rho_mismatch_abs_max": 0.20,
            "crosstalk_max": 0.20,
            "coherence_mean_min": 0.80,
            "drift_mean_max": 0.08,
        },
    }
    return run_genomics_benchmark(cfg)


def _load_metrics(run_dir: Path) -> dict:
    return _load_json(run_dir / "METRICS.json")


def test_gx1_determinism_same_config_same_bytes(tmp_path: Path) -> None:
    r1 = _run_once(tmp_path / "a")
    r2 = _run_once(tmp_path / "b")

    d1 = Path(r1["run_dir"])
    d2 = Path(r2["run_dir"])

    # Bytes MUST match for metrics + trace (core determinism surface)
    for fn in ["METRICS.json", "TRACE.jsonl"]:
        assert _sha256_file(d1 / fn) == _sha256_file(d2 / fn), f"mismatch: {fn}"

    m1 = _load_metrics(d1)
    m2 = _load_metrics(d2)
    assert m1 == m2

    # Replay bundle includes config.output_root (varies per tmp dir) — normalize then compare
    b1 = _load_json(d1 / "REPLAY_BUNDLE.json")
    b2 = _load_json(d2 / "REPLAY_BUNDLE.json")
    b1.get("config", {}).pop("output_root", None)
    b2.get("config", {}).pop("output_root", None)
    assert b1 == b2


def test_gx1_negative_control_mismatch_gate(tmp_path: Path) -> None:
    r = _run_once(tmp_path / "neg")
    m = _load_metrics(Path(r["run_dir"]))

    assert m["scenario_summaries"]["mismatched_key"]["mode"] == "mismatch"
    rho_mismatch = float(m["summary"]["rho_mismatch"])
    assert abs(rho_mismatch) <= 0.20


def test_gx1_multiplex_crosstalk_gate(tmp_path: Path) -> None:
    r = _run_once(tmp_path / "mux")
    m = _load_metrics(Path(r["run_dir"]))
    crosstalk_max = float(m["summary"]["crosstalk_max"])
    assert crosstalk_max <= 0.20


def test_gx1_mutation_degrades_target_channel(tmp_path: Path) -> None:
    r = _run_once(tmp_path / "mut")
    m = _load_metrics(Path(r["run_dir"]))

    matched = float(m["scenario_summaries"]["matched_key"]["rho_primary"])
    mutated = float(m["scenario_summaries"]["mutation_ch0_sev512"]["rho_primary"])

    assert matched >= 0.80
    assert mutated <= 0.80  # mutation should visibly degrade now
    assert mutated <= matched
