# -*- coding: utf-8 -*-
# backend/routes/sqi_packs.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import List
from pathlib import Path
import json, math

router = APIRouter(prefix="/api/sqi/kg", tags=["SQI-KG Packs"])

KG_EXPORTS_DIR = Path("backend/modules/dimensions/containers/kg_exports")
EPS0 = 8.8541878128e-12  # vacuum permittivity

def _pack_path(name: str) -> Path:
    name = name.rstrip(".kg.json")
    return KG_EXPORTS_DIR / f"{name}.kg.json"

def _load_pack(name: str) -> dict:
    p = _pack_path(name)
    if not p.exists():
        raise HTTPException(404, f"KG pack not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/packs")
def list_packs() -> dict:
    KG_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    files: List[str] = sorted(
        p.stem for p in KG_EXPORTS_DIR.glob("*.kg.json")
    )
    return {"status": "ok", "packs": files}

@router.get("/packs/{name}")
def get_pack(name: str) -> dict:
    pack = _load_pack(name)
    return {"status": "ok", "pack": pack}

@router.get("/packs/{name}/has_gauss")
def has_gauss(name: str) -> dict:
    pack = _load_pack(name)
    present = any(
        ("div_E" in (link.get("relation") or "")) and ("ρ/ε0" in link["relation"])
        for link in pack.get("links", [])
    )
    return {"status": "ok", "gauss_law": bool(present)}

@router.get("/physics/point_field")
def point_field(q_coulomb: float, r_meters: float) -> dict:
    """Tiny physics compute: |E| = q / (4π ε0 r^2)"""
    if r_meters <= 0:
        raise HTTPException(400, "r_meters must be > 0")
    E = q_coulomb / (4 * math.pi * EPS0 * (r_meters ** 2))
    return {
        "status": "ok",
        "inputs": {"q_coulomb": q_coulomb, "r_meters": r_meters},
        "epsilon0": EPS0,
        "E_magnitude_V_per_m": E,
    }