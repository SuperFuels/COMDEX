# ============================================================
# 🧩 test_maintenance_jobs.py
# ============================================================
import json
from backend.modules.wiki_capsules.validation_maintenance.maintenance_jobs import run_full_check, LOG_PATH

def test_run_full_check(tmp_path, monkeypatch):
    data_dir = tmp_path / "data" / "knowledge"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "Test.wiki.phn").write_text(
        "meta:\n  version: 1.0\n  signed_by: Tessaris-Core\n  checksum: abc\nlemma: Test\ndefinitions: [x]\nexamples: [y]\n",
        encoding="utf-8"
    )
    result = run_full_check(str(data_dir))
    assert "lint_results" in result
    assert "cross_ref" in result
    log_files = list(LOG_PATH.glob("maintenance_*.json"))
    assert log_files
    report = json.load(open(log_files[-1], "r", encoding="utf-8"))
    assert "timestamp" in report