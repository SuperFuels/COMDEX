from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "scripts" / "analyze_aion_gptoss_dflash_eligibility.py"


def _block(path: Path, positions: int, speedup: float) -> None:
    path.write_text(json.dumps({
        "positions": positions,
        "status": "STOP_FULL_BLOCK",
        "all_positions_all_runs_bitwise_exact": True,
        "wall_speedup_p50": speedup,
        "compressed_traffic_reduction_p50": 1.5,
        "canonical_sha256": f"source-{positions}",
    }))


def test_defers_without_drafter_and_batched_verifier(tmp_path: Path) -> None:
    two = tmp_path / "two.json"
    eight = tmp_path / "eight.json"
    output = tmp_path / "report.json"
    _block(two, 2, 1.02)
    _block(eight, 8, 1.04)
    subprocess.run([
        sys.executable, str(SCRIPT), "--block-result", str(two),
        "--block-result", str(eight), "--output", str(output),
    ], check=True)
    report = json.loads(output.read_text())
    assert report["status"] == "DEFER_DFLASH_UNTIL_BATCHED_VERIFIER"
    assert report["best_measured_block_positions"] == 8
    assert report["best_measured_block_verifier_speedup"] == 1.04
    assert not report["acceptance"]["compatible_gptoss_120b_drafter_installed"]


def test_advances_only_when_both_physical_prerequisites_pass(tmp_path: Path) -> None:
    block = tmp_path / "block.json"
    drafter = tmp_path / "drafter"
    output = tmp_path / "report.json"
    drafter.mkdir()
    _block(block, 8, 1.6)
    subprocess.run([
        sys.executable, str(SCRIPT), "--block-result", str(block),
        "--compatible-drafter-path", str(drafter), "--output", str(output),
    ], check=True)
    report = json.loads(output.read_text())
    assert report["status"] == "ADVANCE_DFLASH_INTEGRATION"
