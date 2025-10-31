# backend/routes/atom_save.py
import time, os, json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from backend.modules.patterns.pattern_registry import pattern_registry
from backend.modules.sqi.sqi_engine import evaluate_sqi
from backend.AION.trace_bus import trace_emit  # cognition bus / SCI bridge

router = APIRouter()

ATOMS_DIR = Path("workspace/Atoms")
ATOMS_DIR.mkdir(parents=True, exist_ok=True)

class AtomSaveRequest(BaseModel):
    name: str
    glyphs: list
    sqi: float | None = None
    patterns: list[str] | None = None

@router.post("/photon/save_atom")
async def save_atom(req: AtomSaveRequest):
    ts = int(time.time())
    day = time.strftime("%Y-%m-%d")
    day_dir = ATOMS_DIR / day
    day_dir.mkdir(exist_ok=True)

    slug = req.name.replace(" ", "_")
    base = f"{ts}_{slug}"

    # compute SQI if missing
    sqi = req.sqi or evaluate_sqi(req.glyphs)

    # write .photo (pure glyphs)
    photo_path = day_dir / f"{base}.photo"
    with open(photo_path, "w") as f:
        json.dump(req.glyphs, f, indent=2)

    # write metadata
    meta = {
        "name": req.name,
        "timestamp": ts,
        "sqi": sqi,
        "patterns": req.patterns or [],
        "glyph_count": len(req.glyphs),
    }

    meta_path = day_dir / f"{base}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # SCI event / cognition trace
    try:
        trace_emit("atom_save", {
            "name": req.name,
            "timestamp": ts,
            "sqi": sqi,
            "path": str(photo_path)
        })
    except Exception as e:
        print(f"[AtomSave] trace_emit failed: {e}")

    return {
        "status": "ok",
        "photo": str(photo_path),
        "meta": str(meta_path),
        "sqi": sqi
    }