from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_hash_from_dict(d: Mapping[str, Any]) -> str:
    payload = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:7]


def write_run_artifacts(
    *,
    base_dir: str,
    test_id: str,
    config: Mapping[str, Any],
    controller: str,
    run_hash: str,
    run: Mapping[str, Any],
    git_commit: str | None = None,
) -> Path:
    out = Path(base_dir) / test_id / run_hash
    out.mkdir(parents=True, exist_ok=True)

    (out / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True))
    meta = {
        "test_id": test_id,
        "controller": controller,
        "run_hash": run_hash,
        "git_commit": git_commit,
        "created_utc": _utc_now_iso(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    (out / "run.json").write_text(json.dumps(run, indent=2, sort_keys=True))

    rows = ["t,v0,T,coherence"]
    ts = run.get("t_series", [])
    v0s = run.get("v0_series", [])
    Ts = run.get("T_series", [])
    Cs = run.get("coh_series", [])

    n = min(len(ts), len(v0s), len(Ts), len(Cs))
    for i in range(n):
        rows.append(f"{ts[i]},{v0s[i]},{Ts[i]},{Cs[i]}")
    (out / "metrics.csv").write_text("\n".join(rows) + "\n")

    return out
