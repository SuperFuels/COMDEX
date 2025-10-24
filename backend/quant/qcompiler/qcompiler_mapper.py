# ================================================================
# 🧩 QCompilerMapper — Resonant Symbolic → Photon Packet Translator
# ================================================================
"""
Bridges QuantPy symbolic equations and AION Photon-Language runtime.

Translates symbolic wave equations (⊕, ↔, ⟲, ∇, μ, π) or
serialized QuantPy state files (.sqs.qpy.json) into photon
instruction packets (.photo) for QQC / AION replay.

Each symbolic or tensor term becomes one or more photon ops:
    • Wave / Tensor   → PHOTON_SUPERPOSE
    • Entangled pair  → PHOTON_ENTANGLE
    • Resonant loop   → PHOTON_RESONATE
    • Collapse / Meas → PHOTON_COLLAPSE / PHOTON_MEASURE
    • Projection      → PHOTON_PROJECT

Outputs:
    data/quantum/qcompiler_output/<session_id>.photo
"""

import json, time, random, logging
from pathlib import Path

logger = logging.getLogger(__name__)
OUT_DIR = Path("data/quantum/qcompiler_output")

# --------------------------------------------------------------
# Operator → Photon Opcode map
# --------------------------------------------------------------
OPCODES = {
    "⊕": "PHOTON_SUPERPOSE",
    "↔": "PHOTON_ENTANGLE",
    "⟲": "PHOTON_RESONATE",
    "∇": "PHOTON_COLLAPSE",
    "μ": "PHOTON_MEASURE",
    "π": "PHOTON_PROJECT",
}


# --------------------------------------------------------------
# QCompilerMapper
# --------------------------------------------------------------
class QCompilerMapper:
    """Converts symbolic QuantPy states or expressions to photon instruction packets."""

    def map_equation(self, equation) -> dict:
        """Map a symbolic equation string or object into photon instructions."""
        text = equation.expr if hasattr(equation, "expr") else str(equation)
        ops = []
        for ch in text.split():
            if ch in OPCODES:
                ops.append(self._make_op(OPCODES[ch]))
        packet = {
            "timestamp": time.time(),
            "expr": text,
            "instructions": ops,
            "meta": {
                "schema": "QPhotoPacket.v1",
                "source": "Equation",
                "desc": "Symbolic expression → Photon instructions",
            },
        }
        logger.info(f"[QCompilerMapper] Compiled {len(ops)} ops from equation '{text}'")
        return packet

    def map_state_to_photo(self, state: dict) -> dict:
        """Map a QuantPy state (.sqs.qpy.json) into photon packet form."""
        ops = []
        terms = state.get("terms", [])
        if not terms and "expr" in state:
            terms = [{"op": "PHOTON_SUPERPOSE"}]  # fallback

        for i, term in enumerate(terms):
            op_type = term.get("op", "PHOTON_SUPERPOSE" if i % 2 == 0 else "PHOTON_ENTANGLE")
            ops.append(self._make_op(op_type))

        packet = {
            "timestamp": time.time(),
            "instructions": ops,
            "meta": {
                "schema": "QPhotoPacket.v1",
                "source_state": state.get("id", "unknown"),
                "desc": "Compiled from .sqs.qpy.json → .photo",
            },
        }
        logger.info(f"[QCompilerMapper] Mapped {len(ops)} ops from state {state.get('id', 'unnamed')}")
        return packet

    # ----------------------------------------------------------
    def _make_op(self, op_type: str):
        """Generate a randomized photon instruction with resonance attributes."""
        return {
            "op": op_type,
            "ρ": round(random.uniform(0.5, 1.0), 3),
            "I": round(random.uniform(0.7, 1.1), 3),
            "rho_grad": 1.0,
            "phase": round(random.uniform(-3.14, 3.14), 3),
            "timestamp": time.time(),
        }

    # ----------------------------------------------------------
    @staticmethod
    def export(packet, session_id="default"):
        """Save compiled photon packet to .photo file."""
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        outpath = OUT_DIR / f"{session_id}.photo"
        with open(outpath, "w") as f:
            json.dump(packet, f, indent=2)
        logger.info(f"[QCompilerMapper] Exported photon instructions → {outpath}")
        return outpath