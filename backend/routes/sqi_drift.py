# -*- coding: utf-8 -*-
# backend/routes/sqi_drift.py
from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.sqi_harmonics import suggest_harmonics

router = APIRouter(prefix="/api/sqi", tags=["SQI Drift"])


# --------------------------
# Helpers
# --------------------------
def _load_container_by_path(path: str) -> Dict[str, Any]:
    """Load a UCS/DC container from disk by path."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------
# Routes
# --------------------------
@router.get("/drift")
def get_drift(
    container_path: str = Query(..., description="Path to .dc.json container"),
    suggest: bool = Query(False, description="Include lemma suggestions"),
) -> Dict[str, Any]:
    """
    Compute SQI drift for a container. Optionally attach harmonic lemma suggestions.
    """
    try:
        container = _load_container_by_path(container_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Container not found: {container_path}")

    rep = compute_drift(container)

    payload: Dict[str, Any] = {
        "container_id": rep.container_id,
        "total_weight": rep.total_weight,
        "status": rep.status,
        "gaps": [g.__dict__ for g in rep.gaps],
        "meta": rep.meta,
    }

    if suggest and payload["gaps"]:
        for gap in payload["gaps"]:
            if gap.get("reason") == "missing_dependencies":
                suggestions = []
                for missing in gap.get("missing", []):
                    candidates = suggest_harmonics(container, missing, top_k=3)
                    suggestions.append(
                        {
                            "missing": missing,
                            "candidates": [{"name": name, "score": score} for name, score in candidates],
                        }
                    )
                gap["suggestions"] = suggestions

    return payload