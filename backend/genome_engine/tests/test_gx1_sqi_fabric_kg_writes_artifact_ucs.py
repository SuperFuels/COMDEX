from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # .../backend/genome_engine/tests/<this_file>
    return Path(__file__).resolve().parents[3]


def _load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise TypeError(f"Expected dict JSON in {p}")
    return obj


def _write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def test_gx1_sqi_fabric_kg_writes_artifact_ucs(tmp_path: Path) -> None:
    repo = _repo_root()

    base_cfg_path = repo / "backend/genome_engine/examples/gx1_config_p16pilot__sqi_fabric_kgw__executor_ucs.json"
    cfg = _load_json(base_cfg_path)

    # Override output_root so tests don't write into docs/Artifacts
    out_root = tmp_path / "P21_GX1_TEST_ARTIFACTS"
    cfg["output_root"] = str(out_root)

    # Ensure fabric is enabled and UCS executor is selected (explicit, even if base config already has it)
    cfg.setdefault("sqi", {})
    if not isinstance(cfg["sqi"], dict):
        cfg["sqi"] = {}

    cfg["sqi"]["enabled"] = True
    cfg["sqi"]["level"] = "fabric"
    cfg["sqi"]["executor"] = "ucs"
    cfg["sqi"]["kg_write"] = True

    # Back-compat flag (builder normalizes this too, but keep explicit here)
    cfg["export_sqi_bundle"] = True

    cfg_path = tmp_path / "gx1_config__ucs_test.json"
    _write_json(cfg_path, cfg)

    env = dict(os.environ)
    env["TESSARIS_TEST_QUIET"] = "1"
    env["TESSARIS_DETERMINISTIC_TIME"] = "1"
    env["PYTHONPATH"] = str(repo)

    # Run the CLI (black-box) so we validate the real artifact ladder end-to-end
    subprocess.run(
        [sys.executable, "-m", "backend.genome_engine.run_genomics_benchmark", "--config", str(cfg_path)],
        cwd=str(repo),
        env=env,
        check=True,
    )

    # Locate run
    latest = out_root / "runs" / "LATEST_RUN_ID.txt"
    assert latest.exists(), f"missing {latest}"
    run_id = latest.read_text(encoding="utf-8").strip()
    assert run_id, "LATEST_RUN_ID.txt empty"

    run_dir = out_root / "runs" / run_id
    metrics_path = run_dir / "METRICS.json"
    assert metrics_path.exists(), f"missing {metrics_path}"

    metrics = _load_json(metrics_path)
    summary = metrics.get("summary") if isinstance(metrics.get("summary"), dict) else {}
    assert summary.get("sqi_executor") == "ucs", f"expected sqi_executor=ucs, got {summary.get('sqi_executor')!r}"

    # Artifact presence
    kgw_path = run_dir / "SQI_KG_WRITES.jsonl"
    assert kgw_path.exists(), f"missing {kgw_path}"
    assert kgw_path.stat().st_size > 0, "SQI_KG_WRITES.jsonl empty"

    # Indexed + checksummed
    idx_path = out_root / "ARTIFACTS_INDEX.md"
    assert idx_path.exists(), f"missing {idx_path}"
    idx_txt = idx_path.read_text(encoding="utf-8")
    rel = f"runs/{run_id}/SQI_KG_WRITES.jsonl"
    assert rel in idx_txt, "SQI_KG_WRITES.jsonl not referenced in ARTIFACTS_INDEX.md"

    sha_path = out_root / "checksums" / f"{run_id}.sha256"
    assert sha_path.exists(), f"missing {sha_path}"
    sha_txt = sha_path.read_text(encoding="utf-8")
    assert rel in sha_txt, "SQI_KG_WRITES.jsonl not referenced in per-run sha256"

    # Verify checksum ladders (run + index)
    subprocess.run(["sha256sum", "-c", f"checksums/{run_id}.sha256"], cwd=str(out_root), env=env, check=True)
    subprocess.run(["sha256sum", "-c", "ARTIFACTS_INDEX.sha256"], cwd=str(out_root), env=env, check=True)
