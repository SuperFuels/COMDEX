from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import json


def load_run(run_dir: Path) -> Dict[str, Any]:
    run_path = run_dir / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"missing {run_path}")
    return json.loads(run_path.read_text())


def load_config(run_dir: Path) -> Dict[str, Any]:
    cfg_path = run_dir / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"missing {cfg_path}")
    return json.loads(cfg_path.read_text())


def load_meta(run_dir: Path) -> Optional[Dict[str, Any]]:
    p = run_dir / "meta.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def telemetry_path(run_dir: Path) -> Path:
    return run_dir / "telemetry.jsonl"


def field_npz_path(run_dir: Path) -> Path:
    return run_dir / "field.npz"
