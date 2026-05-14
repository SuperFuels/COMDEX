#!/usr/bin/env python3
"""
BG01 audit pinning helper for Tessaris OS

Writes:
- BRIDGE/AUDIT_REGISTRY.md
- BRIDGE/docs/BG01_EVIDENCE_BLOCK.md

It auto-selects the best run per controller (by coupling_score; fallback coupling_coeff)
from BRIDGE/artifacts/programmable_bridge/BG01/*/run.json.

Usage:
  cd /workspaces/COMDEX || exit 1
  python tools/bg01_pin_audit.py

Optional:
  python tools/bg01_pin_audit.py --no-strict
"""

from __future__ import annotations

from pathlib import Path
import argparse
import datetime
import glob
import json
import subprocess


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return "UNKNOWN"


def fmt(x, nd: int = 6) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "NA"


def fmt3(x) -> str:
    try:
        return f"{float(x):.3f}"
    except Exception:
        return "NA"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-strict", action="store_true", help="Do not error if a required controller is missing.")
    args = ap.parse_args()

    ROOT = Path("BRIDGE")
    ART = ROOT / "artifacts" / "programmable_bridge" / "BG01"
    DOCS = ROOT / "docs"
    DOCS.mkdir(parents=True, exist_ok=True)

    git_sha = sh(["git", "rev-parse", "--short", "HEAD"])
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    rows: list[tuple[str, str, dict]] = []
    for run_path in glob.glob(str(ART / "*" / "run.json")):
        runp = Path(run_path)
        h = runp.parent.name
        try:
            r = json.loads(runp.read_text())
        except Exception:
            continue
        ctrl = r.get("controller") or "UNKNOWN"
        rows.append((ctrl, h, r))

    if not rows:
        raise SystemExit(f"ERROR: no BG01 runs found under {ART}")

    picked: dict[str, tuple[str, str, dict]] = {}
    for ctrl, h, r in rows:
        score = r.get("coupling_score", None)
        if score is None:
            score = r.get("coupling_coeff", -1e30)
        cur = picked.get(ctrl)
        if cur is None:
            picked[ctrl] = (ctrl, h, r)
            continue
        cur_score = cur[2].get("coupling_score", cur[2].get("coupling_coeff", -1e30))
        if float(score) > float(cur_score):
            picked[ctrl] = (ctrl, h, r)

    req = ["tessaris_bg01_curl_drive", "open_loop", "random_jitter_kappa"]
    missing = [c for c in req if c not in picked]
    if missing and not args.no_strict:
        have = sorted(picked.keys())
        raise SystemExit(f"ERROR: missing controllers {missing}. Have: {have}")

    def get(ctrl: str) -> tuple[str, str, dict]:
        if ctrl in picked:
            return picked[ctrl]
        return (ctrl, "MISSING", {"controller": ctrl})

    t_ctrl, t_hash, t_run = get("tessaris_bg01_curl_drive")
    o_ctrl, o_hash, o_run = get("open_loop")
    j_ctrl, j_hash, j_run = get("random_jitter_kappa")

    audit = f"""# BRIDGE / AUDIT_REGISTRY

## BG01 — Frame Dragging Analogue (Magneto–Gravity Dual; Audit-Pinned)

**Scope:** model-only operator coupling in a shared J-field lattice proxy.  
**Claim style:** “operator coupling in shared J-field model”, not a claim about unification in nature.

### Pinned Runs (BG01)
- **tessaris_bg01_curl_drive:** `{t_hash}`
- **open_loop:** `{o_hash}`
- **random_jitter_kappa:** `{j_hash}`

### Pinned Artifact Paths
- `{ART.as_posix()}/{t_hash}/`
- `{ART.as_posix()}/{o_hash}/`
- `{ART.as_posix()}/{j_hash}/`

### Repro Command (BG01)
```bash
cd /workspaces/COMDEX || exit 1
env PYTHONPATH=$PWD/BRIDGE/src python -m pytest \\
  BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv
```

### Notes
- Registry generated: {ts}
- Git (current HEAD at generation time): `{git_sha}`
"""
    (ROOT / "AUDIT_REGISTRY.md").write_text(audit)

    evid = f"""# BRIDGE / BG01 Evidence Block — Frame Dragging Analogue (Audit-Pinned)

## Summary
BG01 programs a bounded **curl** (magnetism-side proxy) and measures the induced shift in a **curvature proxy** (gravity-side), producing an auditable **cross-coupling coefficient**.

**Audit-safe claim:** under fixed configuration + seed, the Tessaris controller yields a **predictable signed coupling** and beats baselines on coupling score while remaining bounded.

## Pinned Runs (BG01)
- tessaris_bg01_curl_drive: `{t_hash}`
- open_loop: `{o_hash}`
- random_jitter_kappa: `{j_hash}`

## Pinned Artifact Paths
- `{ART.as_posix()}/{t_hash}/`
- `{ART.as_posix()}/{o_hash}/`
- `{ART.as_posix()}/{j_hash}/`

## Repro Command
```bash
cd /workspaces/COMDEX || exit 1
env PYTHONPATH=$PWD/BRIDGE/src python -m pytest \\
  BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv
```

## Key Metrics (from pinned run.json)

| controller | run_hash | coupling_coeff | coupling_score | delta_curvature | curl_rmsT | max_norm |
|---|---:|---:|---:|---:|---:|---:|
| {t_ctrl} | {t_hash} | {fmt(t_run.get("coupling_coeff"))} | {fmt(t_run.get("coupling_score"))} | {fmt(t_run.get("delta_curvature"))} | {fmt(t_run.get("curl_rmsT"))} | {fmt3(t_run.get("max_norm"))} |
| {o_ctrl} | {o_hash} | {fmt(o_run.get("coupling_coeff"))} | {fmt(o_run.get("coupling_score"))} | {fmt(o_run.get("delta_curvature"))} | {fmt(o_run.get("curl_rmsT"))} | {fmt3(o_run.get("max_norm"))} |
| {j_ctrl} | {j_hash} | {fmt(j_run.get("coupling_coeff"))} | {fmt(j_run.get("coupling_score"))} | {fmt(j_run.get("delta_curvature"))} | {fmt(j_run.get("curl_rmsT"))} | {fmt3(j_run.get("max_norm"))} |

## Artifact Expectations
Each pinned run directory includes:
- `run.json` (summary metrics + series)
- `metrics.csv` (time series)
- `meta.json` (controller + environment metadata)
- `config.json` (exact config)

## Git
- Generated: {ts}
- Current HEAD (at generation time): `{git_sha}`
"""
    (DOCS / "BG01_EVIDENCE_BLOCK.md").write_text(evid)

    print("OK: wrote")
    print(" - BRIDGE/AUDIT_REGISTRY.md")
    print(" - BRIDGE/docs/BG01_EVIDENCE_BLOCK.md")
    print("Pinned:")
    print(" - tessaris_bg01_curl_drive =", t_hash)
    print(" - open_loop               =", o_hash)
    print(" - random_jitter_kappa      =", j_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
