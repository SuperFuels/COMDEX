#!/usr/bin/env python3
"""Pin BG01 audit artifacts + write BRIDGE registry + evidence block.

Place this file at:
  BRIDGE/tools/bg01_pin_audit.py

Run (from repo root):
  python BRIDGE/tools/bg01_pin_audit.py

This script:
  - Finds latest BG01 artifact runs per controller
  - Writes:
      BRIDGE/AUDIT_REGISTRY.md
      BRIDGE/docs/BG01_EVIDENCE_BLOCK.md
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
ART_DIR = REPO_ROOT / "BRIDGE" / "artifacts" / "programmable_bridge" / "BG01"

REG_PATH = REPO_ROOT / "BRIDGE" / "AUDIT_REGISTRY.md"
EVID_PATH = REPO_ROOT / "BRIDGE" / "docs" / "BG01_EVIDENCE_BLOCK.md"

# canonical controller names (as written into run.json["controller"])
PIN_CONTROLLERS = [
    "tessaris_bg01_curl_drive",
    "open_loop",
    "random_jitter_kappa",
]


def _git(cmd: List[str]) -> str:
    try:
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def _now_utc_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _find_runs() -> List[Tuple[str, str, Path]]:
    """Return list of (controller, run_hash, run_json_path)."""
    runs: List[Tuple[str, str, Path]] = []
    if not ART_DIR.exists():
        return runs

    for run_json in ART_DIR.glob("*/run.json"):
        run_hash = run_json.parent.name
        try:
            run = _read_json(run_json)
            ctrl = str(run.get("controller", "")) or ""
            if not ctrl:
                meta = run_json.parent / "meta.json"
                if meta.exists():
                    ctrl = str(_read_json(meta).get("controller", "")) or ""
            runs.append((ctrl, run_hash, run_json))
        except Exception:
            continue
    return runs


def _pick_latest_per_controller(runs: List[Tuple[str, str, Path]]) -> Dict[str, Dict[str, Any]]:
    """Pick latest (by mtime) run.json for each pinned controller."""
    by_ctrl: Dict[str, List[Tuple[str, str, Path]]] = {}
    for ctrl, run_hash, p in runs:
        by_ctrl.setdefault(ctrl, []).append((ctrl, run_hash, p))

    picked: Dict[str, Dict[str, Any]] = {}
    for want in PIN_CONTROLLERS:
        cand = by_ctrl.get(want, [])
        if not cand:
            continue
        cand.sort(key=lambda x: x[2].stat().st_mtime, reverse=True)
        ctrl, run_hash, p = cand[0]
        picked[want] = {"controller": ctrl, "run_hash": run_hash, "path": p.parent, "run": _read_json(p)}
    return picked


def _fmt(x: Any, nd: int = 6) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def main() -> int:
    runs = _find_runs()
    picked = _pick_latest_per_controller(runs)

    missing = [c for c in PIN_CONTROLLERS if c not in picked]
    if missing:
        print("ERROR: Missing BG01 artifact runs for:")
        for c in missing:
            print(" -", c)
        print(f"Searched: {ART_DIR}")
        print("Generate artifacts by running:")
        print("  env PYTHONPATH=$PWD/BRIDGE/src python -m pytest BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv")
        return 2

    # Ensure docs dir exists
    EVID_PATH.parent.mkdir(parents=True, exist_ok=True)

    git_head = _git(["git", "rev-parse", "--short", "HEAD"])
    git_status = _git(["git", "status", "--porcelain"])
    commit_line = (git_head + (" (dirty)" if git_status else "")) if git_head else "<unknown>"

    repro = (
        "cd /workspaces/COMDEX || exit 1\n"
        "env PYTHONPATH=$PWD/BRIDGE/src python -m pytest \\\n"
        "  BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv"
    )

    def row(ctrl: str):
        r = picked[ctrl]["run"]
        return (
            picked[ctrl]["run_hash"],
            _fmt(r.get("coupling_coeff")),
            _fmt(r.get("coupling_score")),
            _fmt(r.get("max_norm"), nd=3),
        )

    tess, opn, jit = PIN_CONTROLLERS
    t_h, t_cc, t_cs, t_mn = row(tess)
    o_h, o_cc, o_cs, o_mn = row(opn)
    j_h, j_cc, j_cs, j_mn = row(jit)

    # AUDIT_REGISTRY.md
    REG_PATH.write_text(
        f"""# BRIDGE — AUDIT REGISTRY

This registry lists **shipped** BRIDGE anchors and the **pinned** artifact run hashes.

## Shipped Anchors

### BG01 — Frame Dragging Analogue (Magneto–Gravity Dual)

**Claim (audit-safe, model-only):** programming **curl** in a shared information-flux field induces a predictable, signed shift in a **curvature proxy** (a cross-operator coupling).  
**We do not claim unification in nature**—only operator coupling in this controlled model.

**Pinned runs (BG01):**
- **{tess}:** `{t_h}`
- **{opn}:** `{o_h}`
- **{jit}:** `{j_h}`

**Pinned artifact paths:**
- `BRIDGE/artifacts/programmable_bridge/BG01/{t_h}/`
- `BRIDGE/artifacts/programmable_bridge/BG01/{o_h}/`
- `BRIDGE/artifacts/programmable_bridge/BG01/{j_h}/`

**Repro command:**
```bash
{repro}
```

**Pinned commit:** `{commit_line}`
""",
        encoding="utf-8",
    )

    # BG01_EVIDENCE_BLOCK.md
    EVID_PATH.write_text(
        f"""# BG01 — Frame Dragging Analogue (Evidence Block)

**Pillar:** BRIDGE  
**Anchor:** BG01 — Frame Dragging Analogue (Gemini “Coupling Dual”)  
**Generated:** `{_now_utc_iso()}`  
**Pinned commit:** `{commit_line}`

## Scope / Guardrails

This evidence block is **simulation-first** and **model-only**.

We claim **operator coupling** inside a shared information-flux (J-field) model:
- We *program curl* (magnetism-side operator proxy) via bounded phase swirl injection.
- We measure the induced shift in a **curvature proxy** (gravity-side proxy derived from lattice amplitude structure).
- We report a signed, reproducible coupling coefficient under deterministic configuration + seed.

**Non-claims:** no claims about real-world gravity, frame dragging in spacetime, or unification laws of nature.

## What the anchor asserts (pytest)

- `coupling_coeff > 0` (signed coupling, by convention)
- `tessaris` beats `open_loop` and `random_jitter` on `coupling_score`
- boundedness guardrail: `max_norm` remains under configured safety threshold

## Pinned Runs

| Controller | Run hash | coupling_coeff | coupling_score | max_norm |
|---|---:|---:|---:|---:|
| `{tess}` | `{t_h}` | `{t_cc}` | `{t_cs}` | `{t_mn}` |
| `{opn}` | `{o_h}` | `{o_cc}` | `{o_cs}` | `{o_mn}` |
| `{jit}` | `{j_h}` | `{j_cc}` | `{j_cs}` | `{j_mn}` |

## Pinned Artifact Paths

- `BRIDGE/artifacts/programmable_bridge/BG01/{t_h}/`
- `BRIDGE/artifacts/programmable_bridge/BG01/{o_h}/`
- `BRIDGE/artifacts/programmable_bridge/BG01/{j_h}/`

Expected files per run folder:
- `run.json`
- `metrics.csv`
- `meta.json`
- `config.json`

## Repro Command

```bash
{repro}
```

## Reviewer checklist

1. Run the repro command (should PASS deterministically).
2. Open each pinned run folder and inspect:
   - `run.json` for summary metrics
   - `metrics.csv` for time series (curl RMS, curvature proxy, kappa schedule)
3. Confirm the pinned run hashes match this evidence block and `BRIDGE/AUDIT_REGISTRY.md`.
""",
        encoding="utf-8",
    )

    print("OK: wrote")
    print(" -", REG_PATH.relative_to(REPO_ROOT))
    print(" -", EVID_PATH.relative_to(REPO_ROOT))
    print("Pinned BG01 runs:")
    for c in PIN_CONTROLLERS:
        print(f" - {c}: {picked[c]['run_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
