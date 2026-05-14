from __future__ import annotations

import subprocess
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


PHASE_ROOT = Path("/workspaces/COMDEX/docs/Artifacts/v0.4/P21_GX1")
EXAMPLE_CFG = "/workspaces/COMDEX/backend/genome_engine/examples/gx1_config_p16pilot.json"


def _ensure_latest_run() -> str:
    latest = PHASE_ROOT / "runs" / "LATEST_RUN_ID.txt"
    if not latest.exists():
        run_genomics_benchmark(EXAMPLE_CFG)
    return (PHASE_ROOT / "runs" / "LATEST_RUN_ID.txt").read_text(encoding="utf-8").strip()


def test_gx1_phase_docs_present() -> None:
    run_id = _ensure_latest_run()

    ev = PHASE_ROOT / "docs" / "P21_GX1_EVIDENCE_BLOCK.md"
    assert ev.exists(), f"missing evidence block: {ev}"

    idx = (PHASE_ROOT / "ARTIFACTS_INDEX.md").read_text(encoding="utf-8")
    assert "- docs/P21_GX1_EVIDENCE_BLOCK.md" in idx, "ARTIFACTS_INDEX.md missing evidence entry"
    assert "- AUDIT_REGISTRY.md" in idx, "ARTIFACTS_INDEX.md missing AUDIT_REGISTRY entry"

    # checksum verify must pass for the latest run
    subprocess.check_call(
        ["sha256sum", "-c", f"checksums/{run_id}.sha256"],
        cwd=str(PHASE_ROOT),
    )
