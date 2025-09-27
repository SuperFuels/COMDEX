"""
Photon ↔ QWave Bridge
======================

Converts symbolic Photon ASTs into QWave glyph programs.

Exports:
- to_qglyph(photon_ast)       → normalized qglyph (dict)
- to_wave_program(photon_ast) → full WaveState program for execution
"""

import time
import logging
from typing import Dict, Any

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam

logger = logging.getLogger(__name__)

# ✅ Utility: flatten photon AST into symbolic op + args
def _flatten_photon_ast(ast: Dict[str, Any]) -> str:
    if not ast:
        return "∅"
    if ast.get("op") == "lit":
        return ast.get("value", "∅")
    op = ast.get("op", "?")
    args = ast.get("args", [])
    return f"{op}({','.join(_flatten_photon_ast(a) for a in args)})"


def to_qglyph(photon_ast: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Photon AST into normalized qglyph representation.
    Example:
    {"op": "⊕", "args": [{"op":"lit","value":"x"},{"op":"lit","value":"y"}]}
        → {"type":"qglyph","symbol":"⊕","operands":["x","y"]}
    """
    if not photon_ast:
        return {"type": "qglyph", "symbol": "∅", "operands": []}

    if photon_ast.get("op") == "lit":
        return {"type": "qglyph", "symbol": photon_ast.get("value"), "operands": []}

    return {
        "type": "qglyph",
        "symbol": photon_ast.get("op"),
        "operands": [to_qglyph(arg) for arg in photon_ast.get("args", [])],
    }


def to_wave_program(photon_ast: Dict[str, Any], container_id: str = "unknown", source: str = "photon") -> WaveState:
    """
    Wrap a Photon AST into a WaveState program for execution in QWave.
    """
    try:
        qglyph = to_qglyph(photon_ast)

        wave = WaveState(
            wave_id=f"photon_{int(time.time()*1000)}",
            glow_intensity=1.0,  # default symbolic intensity
            pulse_frequency=1.0,
            mutation_type="photon",
            mutation_cause=source,
            timestamp=time.time(),
        )

        metadata = {
            "qglyph": qglyph,
            "flattened": _flatten_photon_ast(photon_ast),
        }

        # Fire-and-forget beam emit
        coro = emit_qwave_beam(
            wave=wave,
            container_id=container_id,
            source=source,
            metadata=metadata,
        )
        # If you have _spawn_async wrapper from codex_executor, import and use it
        return wave

    except Exception as e:
        logger.error(f"[Photon→QWave] Failed to convert AST: {e}", exc_info=True)
        raise