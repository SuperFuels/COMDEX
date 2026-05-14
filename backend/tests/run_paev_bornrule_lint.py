#!/usr/bin/env python3
"""
Deterministic evidence runner for PAEV Born Rule (v0.3).

Inputs (source-of-record):
  - docs/Artifacts/paev_bornrule_v0_3/artifacts/PAEV_TestA3_BornRule_analytic.txt

Writes (Truth Chain surface):
  - docs/Artifacts/paev_bornrule_v0_3/PAEV_LINT_PROOF.log
  - docs/Artifacts/paev_bornrule_v0_3/PAEV_METRICS.json

This runner is intentionally "audit-style":
- verifies required artifacts exist
- parses analytic report
- enforces acceptance thresholds
- emits sha256 digests + metrics snapshot
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


ROOT = Path("/workspaces/COMDEX")

ART_ROOT = ROOT / "docs/Artifacts/paev_bornrule_v0_3"
IN_A3 = ART_ROOT / "artifacts/PAEV_TestA3_BornRule_analytic.txt"

OUT_LOG = ART_ROOT / "PAEV_LINT_PROOF.log"
OUT_METRICS = ART_ROOT / "PAEV_METRICS.json"

LOCK_ID = "PAEV-BORN-RULE-v0.3"

# Acceptance thresholds (match the Q&A doc reproducibility section)
THRESH_L1 = 1e-5
THRESH_LINF = 5e-6


@dataclass(frozen=True)
class ParsedA3:
    n: int
    k: int
    l1: float
    linf: float
    pqm: Dict[int, float]
    fpa: Dict[int, float]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_a3_report(txt: str) -> ParsedA3:
    # N=5, K=100000
    m = re.search(r"\bN\s*=\s*(\d+)\s*,\s*K\s*=\s*(\d+)\b", txt)
    if not m:
        raise ValueError("Could not parse 'N=..., K=...' header.")
    n = int(m.group(1))
    k = int(m.group(2))

    # L1 error  = ...
    m1 = re.search(r"\bL1\s*error\s*=\s*([0-9.eE+-]+)\b", txt)
    m2 = re.search(r"\bLinf\s*error\s*=\s*([0-9.eE+-]+)\b", txt)
    if not m1 or not m2:
        raise ValueError("Could not parse L1/Linf errors.")
    l1 = float(m1.group(1))
    linf = float(m2.group(1))

    # p_qm(i) lines
    pqm: Dict[int, float] = {}
    for mi, mv in re.findall(r"p_qm\((\d+)\)\s*=\s*([0-9.]+)", txt):
        pqm[int(mi)] = float(mv)

    # f_pa(i) lines
    fpa: Dict[int, float] = {}
    for mi, mv in re.findall(r"f_pa\((\d+)\)\s*=\s*([0-9.]+)", txt):
        fpa[int(mi)] = float(mv)

    if len(pqm) != n or len(fpa) != n:
        # Not fatal, but indicates mismatch between header N and lines present.
        # Treat as error because we want reviewer-proof hygiene.
        raise ValueError(f"Probability tables incomplete: expected {n}, got p_qm={len(pqm)}, f_pa={len(fpa)}.")

    return ParsedA3(n=n, k=k, l1=l1, linf=linf, pqm=pqm, fpa=fpa)


def main() -> int:
    ART_ROOT.mkdir(parents=True, exist_ok=True)

    if not IN_A3.exists():
        err = {
            "error": f"missing required input: {str(IN_A3)}",
            "lock_id": LOCK_ID,
            "status": "FAILED",
        }
        OUT_LOG.write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(err, indent=2))
        return 2

    txt = IN_A3.read_text(encoding="utf-8", errors="replace")
    digest = sha256_file(IN_A3)

    parsed = parse_a3_report(txt)

    passed = (parsed.l1 < THRESH_L1) and (parsed.linf < THRESH_LINF)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    metrics = {
        "lock_id": LOCK_ID,
        "timestamp_utc": now,
        "inputs": {
            "A3_analytic_report": str(IN_A3),
            "A3_analytic_report_sha256": digest,
        },
        "params": {
            "N": parsed.n,
            "K": parsed.k,
            "threshold_L1": THRESH_L1,
            "threshold_Linf": THRESH_LINF,
        },
        "results": {
            "L1_error": parsed.l1,
            "Linf_error": parsed.linf,
            "p_qm": parsed.pqm,
            "f_pa": parsed.fpa,
        },
        "status": "PASS" if passed else "FAIL",
    }

    OUT_METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = []
    lines.append(f"[{'PASS' if passed else 'FAIL'}] lock_id={LOCK_ID}")
    lines.append(f"timestamp_utc={now}")
    lines.append(f"input={IN_A3}")
    lines.append(f"sha256={digest}")
    lines.append(f"N={parsed.n} K={parsed.k}")
    lines.append(f"L1={parsed.l1:.12e} (threshold {THRESH_L1:.2e})")
    lines.append(f"Linf={parsed.linf:.12e} (threshold {THRESH_LINF:.2e})")
    OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[{'PASS' if passed else 'FAIL'}] wrote: {OUT_LOG}")
    print(f"       wrote: {OUT_METRICS}")
    print(f"       N={parsed.n} K={parsed.k} L1={parsed.l1} Linf={parsed.linf}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
