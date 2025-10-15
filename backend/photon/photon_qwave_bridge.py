"""
Photon ↔ QWave Bridge (v0.5)
-----------------------------
Extends the Photon→QWave bridge to route compiled programs
directly through the Symatics Lightwave Engine.
"""

import time, json, logging
from typing import Dict, Any
from pathlib import Path

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam
from backend.modules.symatics_lightwave import SymaticsDispatcher

logger = logging.getLogger(__name__)
EXPORT_PATH = Path("sle_waveprogram_log.json")

#───────────────────────────────────────────────
def _flatten_photon_ast(ast: Dict[str, Any]) -> str:
    if not ast:
        return "∅"
    if ast.get("op") == "lit":
        return ast.get("value", "∅")
    op = ast.get("op", "?")
    args = ast.get("args", [])
    return f"{op}({','.join(_flatten_photon_ast(a) for a in args)})"

#───────────────────────────────────────────────
def to_qglyph(photon_ast: Dict[str, Any]) -> Dict[str, Any]:
    if not photon_ast:
        return {"type": "qglyph", "symbol": "∅", "operands": []}
    if photon_ast.get("op") == "lit":
        return {"type": "qglyph", "symbol": photon_ast.get("value"), "operands": []}
    return {
        "type": "qglyph",
        "symbol": photon_ast.get("op"),
        "operands": [to_qglyph(arg) for arg in photon_ast.get("args", [])],
    }

#───────────────────────────────────────────────
def to_wave_program(photon_ast: Dict[str, Any], container_id: str = "unknown", source: str = "photon") -> WaveState:
    qglyph = to_qglyph(photon_ast)
    wave = WaveState()
    wave.metadata.update({
        "qglyph": qglyph,
        "flattened": _flatten_photon_ast(photon_ast),
        "container_id": container_id,
        "source": source,
        "timestamp": time.time(),
    })
    import asyncio

    try:
        asyncio.run(emit_qwave_beam(
            wave=wave,
            container_id=container_id,
            source=source,
            metadata=wave.metadata
        ))
    except RuntimeError:
        # If we're already in an event loop (e.g. notebook or async context)
        loop = asyncio.get_event_loop()
        loop.create_task(emit_qwave_beam(
            wave=wave,
            container_id=container_id,
            source=source,
            metadata=wave.metadata
        ))
    return wave

#───────────────────────────────────────────────
def compile_photon_ast(photon_ast: Dict[str, Any], run_dispatch=True) -> Dict[str, Any]:
    """
    Compile a Photon AST into a WaveProgram, optionally execute via SymaticsDispatcher.
    """
    try:
        wave = to_wave_program(photon_ast)
        instruction = {"opcode": photon_ast.get("op", "∅")}
        result = {}

        if run_dispatch:
            dispatcher = SymaticsDispatcher()
            result = dispatcher.dispatch(instruction)

        # Compose telemetry record
        record = {
            "symbol": photon_ast.get("op"),
            "flattened": wave.metadata.get("flattened"),
            "coherence": result.get("coherence"),
            "collapse_time_ms": result.get("collapse_time_ms"),
            "timestamp": time.time(),
        }

        # Export to JSON
        try:
            data = []
            if EXPORT_PATH.exists():
                data = json.loads(EXPORT_PATH.read_text())
            data.append(record)
            EXPORT_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"[Photon→QWave] Could not export telemetry: {e}")

        return {"status": "compiled", **record}

    except Exception as e:
        logger.error(f"[Photon→QWave] Failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}