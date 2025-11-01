# ================================================================
# 🧩 QuantPy Schema Exporter - v0.5 Resonant State Export
# ================================================================
"""
Converts .sqs.qpy.json symbolic state files into .photo packets
for use by the AION replay engine.
"""

import json, logging, random, time
from pathlib import Path

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Minimal internal mapper (fallback if QCompilerMapper not present)
# ----------------------------------------------------------------
class QCompilerMapper:
    """Stub mapping: converts a QState JSON into a .photo packet."""
    def map_state_to_photo(self, state: dict):
        ops = []
        for i, term in enumerate(state.get("terms", [])):
            ops.append({
                "op": term.get("op", "PHOTON_SUPERPOSE" if i % 2 == 0 else "PHOTON_ENTANGLE"),
                "ρ": round(random.uniform(0.5, 1.0), 3),
                "I": round(random.uniform(0.7, 1.1), 3),
                "rho_grad": 1.0,
                "phase": round(random.uniform(-3.14, 3.14), 3),
                "timestamp": time.time(),
            })
        packet = {
            "timestamp": time.time(),
            "instructions": ops,
            "meta": {
                "schema": "QPhotoPacket.v1",
                "source_state": state.get("id", "unknown"),
                "desc": "Auto-converted from .sqs.qpy.json",
            },
        }
        return packet


# ----------------------------------------------------------------
# Exporter
# ----------------------------------------------------------------
class QPySchemaExporter:
    def export(self, source: Path, out_dir: Path = Path("data/quantum/qcompiler_output")):
        mapper = QCompilerMapper()
        with open(source) as f:
            state = json.load(f)
        packet = mapper.map_state_to_photo(state)
        out_path = out_dir / (source.stem + ".photo")
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(packet, f, indent=2)
        logger.info(f"[QPySchemaExporter] Exported {source.name} -> {out_path}")
        return out_path


if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python -m backend.quant.qpy.qpy_schema_exporter <source.sqs.qpy.json>")
        sys.exit(1)
    exporter = QPySchemaExporter()
    exporter.export(Path(sys.argv[1]))
    print("✅ Resonant schema export complete.")