from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import json

REQUIRED_FILES = ("run.json", "meta.json", "config.json", "metrics.csv")
REQUIRED_RUN_KEYS = ("test_id", "run_hash", "controller", "seed")

# Optional (Phase0+): enable replay / streaming
OPTIONAL_FILES = ("field.npz", "telemetry.jsonl")  # or frames/*.png in future


@dataclass(frozen=True)
class ContractViolation:
    run_dir: str
    reason: str


def read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def validate_run_dir(run_dir: Path) -> List[ContractViolation]:
    v: List[ContractViolation] = []
    for fn in REQUIRED_FILES:
        if not (run_dir / fn).exists():
            v.append(ContractViolation(str(run_dir), f"missing required file '{fn}'"))
            # if core file missing, bail early to avoid noisy errors
            return v

    run = read_json(run_dir / "run.json")
    for k in REQUIRED_RUN_KEYS:
        if k not in run:
            v.append(ContractViolation(str(run_dir), f"run.json missing key '{k}'"))

    return v


def iter_run_dirs(artifacts_root: Path) -> Iterable[Path]:
    # artifacts_root can be <PILLAR>/artifacts or any subfolder under it.
    # We detect run dirs by presence of run.json.
    for p in artifacts_root.rglob("run.json"):
        yield p.parent


def summarize_violations(violations: List[ContractViolation]) -> Tuple[int, str]:
    if not violations:
        return 0, "PASSED"
    lines = [f"FAIL {v.run_dir} :: {v.reason}" for v in violations]
    return len(violations), "\n".join(lines)
