# 📁 backend/routes/aion_synthesize_glyphs.py
# ==========================================================
# 💠 AION Glyph Synthesizer — Unified API
# ----------------------------------------------------------
# Handles synthesis of glyphs from text, structured content,
# and integrates with the Symatic Log + Thought Stream feed.
# ==========================================================

from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional, List, Any
from backend.modules.glyphos.glyph_synthesis_engine import synthesize_glyphs_from_text
from backend.modules.dna_chain.dc_handler import inject_glyphs_into_universal_container_system
from backend.modules.aion_resonance.thought_stream import broadcast_event
import traceback
import logging
import json
import os
from datetime import datetime

router = APIRouter()

SYMATIC_LOG_PATH = "data/symatic_log.json"


# ──────────────────────────────────────────────────────────
# 📦 Request / Response Models
# ──────────────────────────────────────────────────────────
class SynthesisRequest(BaseModel):
    input: Any  # accepts str or dict
    source: Optional[str] = "manual"
    inject_to_grid: Optional[bool] = False
    container: Optional[str] = None  # e.g. "glyph_synthesis_lab.dc.json"


class SynthesisResponse(BaseModel):
    success: bool
    glyphs: List[dict]
    injected: bool = False
    container: Optional[str] = None
    error: Optional[str] = None  # frontend / debug


# ──────────────────────────────────────────────────────────
# 🧠 Helper: Write glyph synthesis event into Symatic log
# ──────────────────────────────────────────────────────────
def append_to_symatic_log(entry: dict):
    try:
        if not os.path.exists(SYMATIC_LOG_PATH):
            base = {"log": []}
        else:
            with open(SYMATIC_LOG_PATH, "r") as f:
                base = json.load(f) or {"log": []}
        base["log"].append(entry)
        base["log"] = base["log"][-100:]  # keep recent 100
        with open(SYMATIC_LOG_PATH, "w") as f:
            json.dump(base, f, indent=2)
    except Exception as e:
        logging.warning(f"⚠️ Failed to append to Symatic log: {e}")


# ──────────────────────────────────────────────────────────
# 🔮 Main Endpoint
# ──────────────────────────────────────────────────────────
@router.post("/api/aion/synthesize-glyphs", response_model=SynthesisResponse)
async def synthesize_glyphs(request: SynthesisRequest = Body(...)):
    try:
        # Normalize input to text
        payload = request.input
        if isinstance(payload, (dict, list)):
            payload_text = json.dumps(payload, ensure_ascii=False)
        else:
            payload_text = str(payload)

        # Step 1: Run synthesis
        glyphs = synthesize_glyphs_from_text(payload_text, source=request.source)

        injected = False

        # Step 2: Optional injection into universal container
        if request.inject_to_grid and request.container:
            try:
                injected = inject_glyphs_into_universal_container_system(
                    container_filename=request.container,
                    glyphs=glyphs,
                    source=request.source
                )
            except Exception as inj_err:
                logging.warning(f"⚠️ Glyph injection failed: {inj_err}")

        # Step 3: Log synthesis event
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operator": "μ",
            "equation": f"Synthesize({request.source})",
            "glyph_count": len(glyphs),
            "payload": payload_text[:512],
        }
        append_to_symatic_log(log_entry)

        # Step 4: Broadcast to Thought Stream
        await broadcast_event({
            "type": "symatic",
            "message": f"μ synthesis → {len(glyphs)} glyphs generated",
            "tone": "active",
            "timestamp": log_entry["timestamp"]
        })

        return SynthesisResponse(
            success=True,
            glyphs=glyphs,
            injected=injected,
            container=request.container if injected else None,
        )

    except Exception as e:
        logging.error("❌ Glyph synthesis failed:")
        traceback.print_exc()

        fallback_glyph = {
            "symbol": "✦",
            "meaning": "Fallback Milestone",
            "source": "fallback",
            "confidence": 0.5,
        }

        # Log the failure to symatic log too
        append_to_symatic_log({
            "timestamp": datetime.utcnow().isoformat(),
            "operator": "∇",
            "equation": f"Error({str(e)})",
            "glyph_count": 0,
        })

        await broadcast_event({
            "type": "error",
            "message": f"∇ synthesis failure — {e}",
            "tone": "critical",
            "timestamp": datetime.utcnow().isoformat()
        })

        return SynthesisResponse(
            success=False,
            glyphs=[fallback_glyph],
            injected=False,
            error=str(e),
        )


# ✅ Export router
synthesize_glyphs_router = router