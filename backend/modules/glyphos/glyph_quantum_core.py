# File: backend/modules/glyphos/glyph_quantum_core.py
# Description: Symbolic Quantum Core — glyph-based QBit simulation and codex trace logging

from backend.modules.codex.codex_trace import log_codex_trace
import random
import uuid

class GlyphQuantumCore:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.entangled_pairs = {}  # {pair_id: (coord1, coord2)}

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

        log_codex_trace({
            "type": "qbit_generate",
            "qbit_id": qbit_id,
            "state": state,
            "coord": coord,
            "glyph": glyph,
            "container": self.container_id,
        })

        return result

    def collapse_qbit(self, qbit: dict) -> dict:
        collapsed = random.choice(["0", "1"])
        qbit["collapsed"] = collapsed
        qbit["state"] = "collapsed"

        log_codex_trace({
            "type": "qbit_collapse",
            "qbit_id": qbit["qbit_id"],
            "from_state": qbit.get("state"),
            "collapsed": collapsed,
            "coord": qbit.get("origin"),
            "glyph": qbit.get("glyph"),
            "container": self.container_id,
        })

        return qbit

    def entangle_qbits(self, coord1: str, coord2: str) -> str:
        pair_id = str(uuid.uuid4())[:8]
        self.entangled_pairs[pair_id] = (coord1, coord2)

        log_codex_trace({
            "type": "qbit_entangle",
            "pair_id": pair_id,
            "coords": [coord1, coord2],
            "container": self.container_id,
        })

        return pair_id