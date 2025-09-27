"""
📄 photon_executor.py
Photon Executor — runs Photon ASTs by compiling them into QWave programs
"""

import logging
from backend.modules.photon.photon_qwave_bridge import to_wave_program
from backend.modules.codex.codex_executor import emit_qwave_beam_ff

logger = logging.getLogger(__name__)

def execute_photon_ast(photon_ast: list, container_id: str = "global", source: str = "photon"):
    """
    Run a Photon AST by compiling to WaveProgram + emitting beams.
    """
    try:
        # 1) Compile AST → wave program
        program = to_wave_program(photon_ast, container_id=container_id)

        # 2) Emit each wave
        for wave in program:
            emit_qwave_beam_ff(
                source=source,
                payload={
                    "wave_id": wave.wave_id,
                    "container_id": container_id,
                    "glow": getattr(wave, "glow_intensity", 0.0),
                    "pulse": getattr(wave, "pulse_frequency", 0.0),
                    "event": "photon_exec",
                    "mutation_type": "photon",
                }
            )

        return {"status": "ok", "emitted": len(program)}

    except Exception as e:
        logger.error(f"[PhotonExecutor] Failed to execute Photon AST: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}