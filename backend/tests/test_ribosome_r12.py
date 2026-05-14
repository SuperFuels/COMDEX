#!/usr/bin/env python3
# ================================================================
# 🧪 RibosomeEngine Phase R12 - Functional Test
# ================================================================
# Generates a symbolic RNA scroll with Symatics operators and runs
# the full synthesis -> protein (.prot) + photon trace (.photo)
# ================================================================

from backend.modules.symbolic_biology.ribosome_engine import RibosomeEngine
import json, time
from pathlib import Path

# ------------------------------------------------------------
# Create a sample symbolic RNA scroll (.rna)
# ------------------------------------------------------------
rna_scroll = {
    "type": "RNA_SCROLL",
    "source": "data/containers/test_symatics.dc",
    "timestamp": time.time(),
    "content": {
        "glyphs": [
            {"id": "g1", "logic": "⊕ ↔ ⟲ -> μ π", "entropy": 0.62, "coherence": 0.81, "tags": ["test", "resonance"]}
        ]
    },
    "mutation_proposal": {
        "timestamp": time.time(),
        "position": 2,
        "original": "⊕",
        "mutated": "⟲",
        "mutation_type": "symbolic_shift",
        "confidence": 0.842,
        "context": {"container": "data/containers/test_symatics.dc"}
    }
}

Path("data/tmp").mkdir(parents=True, exist_ok=True)
with open("data/tmp/test_scroll.rna", "w") as f:
    json.dump(rna_scroll, f, indent=2)

print("✅ Created RNA scroll -> data/tmp/test_scroll.rna")

# ------------------------------------------------------------
# Run synthesis via RibosomeEngine
# ------------------------------------------------------------
rib = RibosomeEngine()
result = rib.synthesize("data/tmp/test_scroll.rna")

print("\n🧬 Synthesis Output Preview:\n")
print(result)
print("\n✅ Check data/tmp/ribosome_output.prot and data/tmp/ribosome_photon_trace.photo for full output.\n")