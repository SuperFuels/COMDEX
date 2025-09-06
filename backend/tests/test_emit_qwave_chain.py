# backend/tests/test_emit_qwave_chain.py

from backend.modules.glyphwave.emit_beam import emit_qwave_beam
from uuid import uuid4
import time

def simulate_full_beam_chain():
    container_id = f"test_container_{uuid4()}"
    glyph_id_src = f"glyph_src_{uuid4()}"
    glyph_id_mutated = f"glyph_mutated_{uuid4()}"
    glyph_id_predicted = f"glyph_predicted_{uuid4()}"

    print("🔧 Simulating symbolic mutation...")
    emit_qwave_beam(
        glyph_id=glyph_id_mutated,
        result={"id": glyph_id_mutated, "label": "mutated glyph"},
        source="codex_executor",
        context={"container_id": container_id},
        state="mutated",
        metadata={"innovation_score": 0.82, "sqi_score": 0.91}
    )

    time.sleep(0.5)

    print("🔮 Simulating prediction event...")
    emit_qwave_beam(
        glyph_id=glyph_id_predicted,
        result={"id": glyph_id_predicted, "label": "predicted glyph"},
        source="prediction_engine",
        context={"container_id": container_id},
        state="predicted",
        metadata={"confidence": 0.88, "sqi_score": 0.93}
    )

    time.sleep(0.5)

    print("📥 Simulating symbolic ingestion...")
    emit_qwave_beam(
        glyph_id=glyph_id_src,
        result={"id": glyph_id_src, "label": "raw ingest"},
        source="symbolic_ingestion_engine",
        context={"container_id": container_id},
        state="ingested",
        metadata={"tags": ["logic", "initial"], "sqi_score": 0.76}
    )

    print("✅ Full beam chain simulated.")


if __name__ == "__main__":
    simulate_full_beam_chain()