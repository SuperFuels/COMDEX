# ============================================================
# 📙 backend/modules/wiki_capsules/validation_maintenance/maintenance_jobs.py
# ============================================================
"""
Maintenance Jobs — Automated Nightly Validation & Pruning
----------------------------------------------------------
Combines linter and reference validator; can be triggered via CLI or CI task.
"""

from pathlib import Path
from datetime import datetime
import json
from backend.modules.wiki_capsules.validation_maintenance.wiki_linter import lint_directory
from backend.modules.wiki_capsules.validation_maintenance.reference_validator import validate_cross_references

LOG_PATH = Path("logs/wiki_maintenance")
LOG_PATH.mkdir(parents=True, exist_ok=True)


def run_full_check(root_dir: str = "data/knowledge") -> dict:
    """Run linter + reference validation; return combined report."""
    ts = datetime.utcnow().isoformat()
    results = {
        "timestamp": ts,
        "lint_results": lint_directory(Path(root_dir)),
        "cross_ref": validate_cross_references(),
    }

    out_path = LOG_PATH / f"maintenance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"[Maintenance] Validation report saved → {out_path}")
    return results


# ──────────────────────────────────────────────
# Optional CLI entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    run_full_check()