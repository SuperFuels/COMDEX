from __future__ import annotations

import json
import shutil
from pathlib import Path

from backend.modules.hexcore.cross_domain_method_transfer_campaign import run_campaign


def test_three_method_cards_reduce_attempts_on_disjoint_targets(tmp_path: Path) -> None:
    repo = tmp_path / "repo"; (repo / "results").mkdir(parents=True)
    source_root = Path(__file__).resolve().parents[2]
    (repo / "tools/photon-js").mkdir(parents=True)
    shutil.copy(source_root / "tools/photon-js/package.json", repo / "tools/photon-js/package.json")
    shutil.copy(source_root / "package.json", repo / "package.json")
    row = {"cycle": 1, "commitment_sha256": "c", "outcomes": {"source": {"reachable": True}}}
    body = dict(row)
    import hashlib
    row["outcome_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (repo / "results/hexcore_prospective_cross_domain_outcomes.jsonl").write_text(json.dumps(row) + "\n")
    result = run_campaign(repo, repo / "results/result.json", repo / "state/learning.json")
    assert result["passed"] is True
    assert result["gate"]["verified_transfers"] == 3
    assert result["gate"]["mean_attempt_reduction"] >= 2 / 3
    assert all(row["warm"]["attempts"] == 1 and row["cold"]["attempts"] == 3 for row in result["transfers"])

