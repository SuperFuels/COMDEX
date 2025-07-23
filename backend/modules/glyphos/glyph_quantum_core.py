# File: backend/modules/glyphos/glyph_quantum_core.py
# Description: Symbolic Quantum Core — glyph-based QBit simulation and codex trace logging

import random
import uuid
import hashlib

from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.aion.dream_core import DreamCore
from backend.modules.glyphos.codexlang_translator import run_codexlang_string

codex_trace = CodexTrace()

class GlyphQuantumCore:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.entangled_pairs = {}  # {pair_id: (coord1, coord2)}
        self.dream_core = DreamCore()

    def generate_qbit(self, glyph: str, coord: str) -> dict:
        qbit_id = str(uuid.uuid4())[:8]
        state = random.choice(["0", "1", "superposed"])

        result = {
            "qbit_id": qbit_id,
            "state": state,
            "origin": coord,
            "glyph": glyph,
            "container": self.container_id,
        }

        codex_trace.record(
            glyph=glyph,
            context={
                "type": "qbit_generate",
                "qbit_id": qbit_id,
                "state": state,
                "coord": coord,
                "glyph": glyph,
                "container": self.container_id,
            },
            result="generated"
        )

        return result

    def collapse_qbit(self, qbit: dict) -> dict:
        collapsed = random.choice(["0", "1"])
        previous_state = qbit.get("state")
        qbit["collapsed"] = collapsed
        qbit["state"] = "collapsed"

        codex_trace.record(
            glyph=qbit.get("glyph"),
            context={
                "type": "qbit_collapse",
                "qbit_id": qbit["qbit_id"],
                "from_state": previous_state,
                "collapsed": collapsed,
                "coord": qbit.get("origin"),
                "glyph": qbit.get("glyph"),
                "container": self.container_id,
            },
            result=f"collapsed_to_{collapsed}"
        )

        # Reflect QGlyph collapse into DreamCore
        collapse_result = {
            "selected": {
                "path": qbit.get("glyph"),
                "collapsed": collapsed,
                "qbit_id": qbit["qbit_id"],
                "coord": qbit.get("origin"),
                "container": self.container_id,
            },
            "ranked": [
                {"path": qbit.get("glyph"), "collapse": "0"},
                {"path": qbit.get("glyph"), "collapse": "1"},
            ],
            "observer_bias": {
                "left": round(random.uniform(0.3, 0.7), 2),
                "right": round(random.uniform(0.3, 0.7), 2),
                "decision": collapsed
            }
        }

        self.dream_core.reflect_qglyph_collapse(collapse_result)

        return qbit

    def entangle_qbits(self, coord1: str, coord2: str) -> str:
        pair_id = str(uuid.uuid4())[:8]
        self.entangled_pairs[pair_id] = (coord1, coord2)

        codex_trace.record(
            glyph="↔",
            context={
                "type": "qbit_entangle",
                "pair_id": pair_id,
                "coords": [coord1, coord2],
                "container": self.container_id,
            },
            result="entangled"
        )

        return pair_id


# 🔁 Standalone QGlyph Generator for Benchmarking
def generate_qglyph_from_string(codex_string: str) -> dict:
    """
    Converts a CodexLang string into a symbolic QGlyph format.
    This simulates compression and hashing for traceable quantum-symbolic execution.
    """
    qglyph_id = hashlib.sha256(codex_string.encode()).hexdigest()[:12]
    parsed_tree = run_codexlang_string(codex_string)
    entropy = len(set(codex_string))

    codex_trace.record(
        glyph="[qglyph]",
        context={
            "type": "qglyph_generate",
            "qglyph_id": qglyph_id,
            "source": "generate_qglyph_from_string",
            "entropy": entropy,
            "length": len(codex_string),
        },
        result="generated"
    )

    return {
        "id": qglyph_id,
        "entropy": entropy,
        "compressed_length": len(codex_string) // 3,
        "parsed_tree": parsed_tree
    }