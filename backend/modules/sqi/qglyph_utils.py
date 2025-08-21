import uuid
from typing import Dict, List, Optional, TYPE_CHECKING

from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.websocket_manager import broadcast_event
from backend.modules.symbolic.mutation_engine import suggest_mutations_for_glyph

if TYPE_CHECKING:
    from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph


def generate_qglyph_from_string(
    raw_string: str,
    metadata: Optional[Dict] = None,
    entangled: bool = False,
    predictive: bool = False,
    superposition: Optional[List[str]] = None,
    trace_origin: Optional[str] = None,
    inject: bool = True,
    broadcast: bool = True,
    suggest_mutations: bool = False,
    entangle_pair_id: Optional[str] = None,
) -> "LogicGlyph":
    """
    Converts a raw symbolic string into a Q-Glyph compatible LogicGlyph.

    Args:
        raw_string (str): Base symbolic glyph content.
        metadata (dict): Additional metadata to inject.
        entangled (bool): Mark glyph as entangled.
        predictive (bool): Mark glyph as predictive.
        superposition (List[str]): Optional list of symbolic states.
        trace_origin (str): Optional origin trace.
        inject (bool): If True, write to KnowledgeGraph.
        broadcast (bool): If True, send over WebSocket.
        suggest_mutations (bool): Suggest mutations per Q-state.
        entangle_pair_id (str): Link this glyph to another via ↔ ID.

    Returns:
        LogicGlyph: Fully registered QGlyph.
    """
    from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph  # Delayed import

    try:
        glyph: LogicGlyph = CodexLangRewriter.parse_string_to_glyph(raw_string)
    except Exception as e:
        raise ValueError(f"Failed to parse Q-Glyph from string: {raw_string}") from e

    # Unique ID for Q-Glyph
    glyph_id = str(uuid.uuid4())

    # Core metadata injection
    glyph.metadata.update({
        "id": glyph_id,
        "qglyph": True,
        "source": "QGlyphGen",
        "entangled": entangled,
        "predictive": predictive,
        "superposition": superposition or [],
        "trace_origin": trace_origin,
    })

    if entangle_pair_id:
        glyph.metadata["entangled_with"] = entangle_pair_id
        glyph.metadata["↔"] = [glyph_id, entangle_pair_id]

    if metadata:
        glyph.metadata.update(metadata)

    if inject:
        KnowledgeGraphWriter.inject_glyph(glyph)

    CodexMetrics.score_glyph_tree(glyph)

    if suggest_mutations and superposition:
        suggestions = []
        for state in superposition:
            mutated = suggest_mutations_for_glyph(glyph, context=f"Q-State:{state}")
            suggestions.extend(mutated)
        glyph.metadata["suggested_mutations"] = [m.to_dict() for m in suggestions]

    if broadcast:
        try:
            broadcast_symbolic_glyph(glyph)
        except Exception as e:
            print(f"[QGlyph Broadcast Error] {e}")

    return glyph


def generate_qglyph_batch(
    raw_strings: List[str],
    shared_metadata: Optional[Dict] = None,
    entangled: bool = True,
    predictive: bool = False,
    inject: bool = True,
    broadcast: bool = True,
    suggest_mutations: bool = False,
) -> List["LogicGlyph"]:
    """
    Batch generate Q-Glyphs with entangled IDs and optional mutation hints.
    """
    entangle_id = str(uuid.uuid4()) if entangled else None

    return [
        generate_qglyph_from_string(
            raw,
            metadata=shared_metadata,
            entangled=entangled,
            predictive=predictive,
            inject=inject,
            broadcast=broadcast,
            suggest_mutations=suggest_mutations,
            entangle_pair_id=entangle_id,
        )
        for raw in raw_strings
    ]