from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict
import re


def _matter_root() -> Path:
    # .../MATTER/src/programmable_matter/artifacts.py -> parents[2] == .../MATTER
    return Path(__file__).resolve().parents[2]


def _to_jsonable_cfg(cfg: Any) -> Dict[str, Any]:
    if is_dataclass(cfg):
        return asdict(cfg)
    if isinstance(cfg, dict):
        return dict(cfg)
    # best-effort: object with __dict__
    return dict(getattr(cfg, "__dict__", {}))


def write_run_artifacts(*, cfg: Any, run: Dict[str, Any]) -> Path:
    """
    Writes:
      - config.json
      - meta.json
      - run.json
      - metrics.csv  (tolerant to variable series keys across MTxx tests)

    Folder:
      MATTER/artifacts/programmable_matter/<TEST_ID>/<RUN_HASH>/
    # Phase-0 artifacts contract hardening: ensure run.json includes test_id
    if not run.get("test_id"):
        cn = cfg.__class__.__name__
        m = re.match(r"(MT\d+)", cn)
        run["test_id"] = m.group(1) if m else "MT"
    """
    test_id = str(run.get("test_id", "UNKNOWN"))
    run_hash = str(run.get("run_hash", "nohash"))
    # Phase-0 artifacts contract hardening: ensure run.json includes run_hash
    if not run.get('run_hash'):
        run['run_hash'] = str(run_hash)

    out_dir = _matter_root() / "artifacts" / "programmable_matter" / test_id / run_hash
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg_dict = _to_jsonable_cfg(cfg)

    # --- config.json ---
    (out_dir / "config.json").write_text(json.dumps(cfg_dict, indent=2, sort_keys=True) + "\n")

    # --- meta.json ---
    meta = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": run.get("controller"),
        "seed": run.get("seed"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")

    # --- run.json ---
    (out_dir / "run.json").write_text(json.dumps(run, indent=2, sort_keys=True) + "\n")

    # --- metrics.csv (series-flexible) ---
    # Supported / common series keys (union across MT01/MT02/etc)
    series_keys = [
        "peak_series",
        "width_series",
        "gain_series",
        "chi_series",
        "norm_series",
        "symmetry_error_series",
    ]
    present = [k for k in series_keys if isinstance(run.get(k), list)]
    max_len = 0
    for k in present:
        max_len = max(max_len, len(run[k]))

    if max_len > 0:
        with (out_dir / "metrics.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", *present])
            for i in range(max_len):
                row = [i]
                for k in present:
                    arr = run.get(k, [])
                    row.append(arr[i] if i < len(arr) else "")
                w.writerow(row)

    return out_dir