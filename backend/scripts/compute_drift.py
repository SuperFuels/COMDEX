# -*- coding: utf-8 -*-
# File: backend/scripts/compute_drift.py

import json
import sys
import argparse
from dataclasses import asdict, is_dataclass

from backend.modules.sqi.sqi_math_adapter import compute_drift

# suggestions are optional; script still works if the module isn't present yet
try:
    from backend.modules.sqi.sqi_harmonics import suggest_harmonics  # C3
except Exception:
    suggest_harmonics = None


def _gap_to_dict(g):
    if is_dataclass(g):
        return asdict(g)
    # fallback for simple objects
    d = {}
    for k in ("name", "reason", "missing", "weight", "hints", "meta"):
        if hasattr(g, k):
            d[k] = getattr(g, k)
    return d


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compute_drift",
        description="Compute drift (proof gaps) for a .dc container"
    )
    p.add_argument("container", help="Path to container JSON")
    p.add_argument(
        "--suggest",
        action="store_true",
        help="Include harmonic lemma suggestions for missing deps"
    )
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load container
    with open(args.container, "r", encoding="utf-8") as f:
        container = json.load(f)

    # Compute drift report
    rep = compute_drift(container)

    # Serialize gaps
    gaps_out = []
    for g in rep.gaps:
        gdict = _gap_to_dict(g)

        # Attach suggestions when asked and applicable
        if args.suggest and gdict.get("reason") == "missing_dependencies":
            if suggest_harmonics is None:
                gdict["suggestions"] = [{"error": "sqi_harmonics not available"}]
            else:
                bundles = []
                for miss in gdict.get("missing", []) or []:
                    cands = suggest_harmonics(container, miss, top_k=3)
                    bundles.append({
                        "missing": miss,
                        "candidates": [
                            {"name": n, "score": round(s, 3)} for (n, s) in cands
                        ],
                    })
                gdict["suggestions"] = bundles

        gaps_out.append(gdict)

    out = {
        "container_id": getattr(rep, "container_id", None),
        "total_weight": getattr(rep, "total_weight", 0.0),
        "status": getattr(rep, "status", "UNKNOWN"),
        "gaps": gaps_out,
        "meta": getattr(rep, "meta", {}),
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())