from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from tessaris_terminal.contract import iter_run_dirs, read_json


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("artifacts_roots", nargs="+", help="one or more artifacts roots to index")
    ap.add_argument("--out", default="Tessaris_OS/TERMINAL/registry/index.json")
    args = ap.parse_args()

    all_runs = []
    for artifacts_root in args.artifacts_roots:
        root = Path(artifacts_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for run_dir in iter_run_dirs(root):
        run = read_json(run_dir / "run.json")
        meta = read_json(run_dir / "meta.json")
        cfg = read_json(run_dir / "config.json")

        # best-effort pillar/test inference from path shape:
        # <pillar>/artifacts/<namespace>/<TEST_ID>/<run_hash>/
        parts = run_dir.parts
        test_id = run.get("test_id") or (parts[-2] if len(parts) >= 2 else "UNKNOWN")
        run_hash = run.get("run_hash") or run_dir.name

        rows.append({
            "run_dir": str(run_dir),
            "test_id": test_id,
            "run_hash": run_hash,
            "controller": run.get("controller"),
            "seed": run.get("seed"),
            "timestamp": meta.get("timestamp") or meta.get("created_at") or meta.get("time"),
            "namespace": parts[-3] if len(parts) >= 3 else None,
            "cfg": cfg,
            "metrics": {k: v for k, v in run.items() if k not in ("kappa_series","curl_rms_series","curvature_series","norm_series")},
        })

    rows.sort(key=lambda r: (str(r.get("test_id")), str(r.get("controller")), str(r.get("run_hash"))))
    out.write_text(json.dumps({"count": len(rows), "runs": rows}, indent=2, sort_keys=True), encoding="utf-8")
    print(f"OK: wrote {out} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
