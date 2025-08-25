import uuid
from datetime import datetime

from backend.modules.knowledge_graph.kg_writer_singleton import write_glyph_event
from backend.modules.codex.codex_metrics import record_mutation_event
from backend.modules.sqi.sqi_event_bus import emit_sqi_mutation_score_if_applicable
from backend.modules.symbolic.symbolic_broadcast import broadcast_glyph_event


def add_dna_mutation(original_glyph: dict, mutated_glyph: dict, metadata: dict = None) -> dict:
    """
    Record a DNA mutation from one glyph to another and dispatch it into:
    - Knowledge Graph
    - Codex Metrics
    - .dc container (if linked)
    - GlyphNet WebSocket
    - SQI scoring hooks

    Args:
        original_glyph: The original glyph dictionary.
        mutated_glyph: The mutated glyph dictionary.
        metadata: Optional metadata like reason, entropy delta, etc.

    Returns:
        A dictionary representing the mutation record.
    """
    mutation_record = {
        "mutation_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "original": original_glyph,
        "mutated": mutated_glyph,
        "metadata": metadata or {}
    }

    container_id = metadata.get("container_id") if metadata else None

    # 🧠 Write into KG trace
    write_glyph_event("dna_mutation", mutation_record, container_id=container_id)

    # 📊 Record into CodexMetrics
    record_mutation_event(mutation_record)

    # 🌐 Emit to GlyphNet
    broadcast_glyphnet_event(
        event_type="mutation",
        container_id=container_id,
        data=mutation_record
    )

    # 🔬 Score mutation via SQI if enabled
    emit_sqi_mutation_score_if_applicable(mutation_record)

    return mutation_record