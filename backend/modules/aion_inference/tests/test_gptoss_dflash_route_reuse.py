from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "scripts" / "analyze_aion_gptoss_dflash_route_reuse.py"


def test_counts_real_route_groups_without_double_counting_replicates(tmp_path: Path) -> None:
    layers = [{"route": [1, 2, 3, 4]} for _ in range(36)]
    other = [{"route": [1, 5, 6, 7]} for _ in range(36)]
    source = tmp_path / "trace.json"
    output = tmp_path / "result.json"
    source.write_text(json.dumps({
        "routes_repeatable": True,
        "input_token_ids": [10],
        "canonical_sha256": "source",
        "run_a": {"tokens": [
            {"layers": layers}, {"layers": layers}, {"layers": other},
        ]},
    }))
    subprocess.run([
        sys.executable, str(SCRIPT), "--trace", str(source),
        "--block-size", "2", "--output", str(output),
    ], check=True)
    report = json.loads(output.read_text())
    block = report["blocks"][0]
    assert block["expert_occurrences"] == 288
    assert block["distinct_expert_groups"] == 252
    assert block["group_size_histogram"] == {"1": 216, "2": 36}
    assert report["status"] == "STOP_UNCHANGED_EXPERT_GROUPING_AS_DFLASH_BREAKTHROUGH"
