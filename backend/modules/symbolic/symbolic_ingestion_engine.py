from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.codex.symbolic_registry import symbolic_registry
from backend.modules.symbolic.symbolic_parser import parse_raw_input_to_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.sqi.sqi_container_registry import SQIContainerRegistry

# NEW: logic parser for ∀x. P(x) → Q(x)
from backend.modules.codex.codexlang_parser import parse_codexlang_to_ast

# NEW: SymbolNet enrichment engine
from backend.modules.symbolnet.symbolnet_ingestor import SymbolNetIngestor


def is_logic_expression(expr: str) -> bool:
    """Rough check for logic symbols like ∀, ∃, →, ∧, ¬, etc."""
    return any(sym in expr for sym in ["\u2200", "\u2203", "\u2192", "\u2227", "\u2228", "\u00ac"])


class SymbolicIngestionEngine:
    def __init__(self):
        self.graph_writer = get_kg_writer()
        self.registry = SQIContainerRegistry()
        self.rewriter = CodexLangRewriter()
        self.symbolnet = SymbolNetIngestor()

    def dispatch_ingest(
        self,
        op: str,
        args: Optional[Any] = None,
        codexlang: Optional[str] = None,
        domain: str = "general",
        source: str = "external"
    ) -> Dict[str, Any]:
        """
        Public entry point for ingestion API. Dispatches to appropriate ingestion path.
        """
        metadata = {
            "domains": [domain],
            "source_type": "api",
            "origin": source,
        }

        if op == "ingest_codexlang" and codexlang:
            return self.ingest_data(
                source=source,
                raw_content=codexlang,
                metadata=metadata,
            )
        else:
            raise ValueError(f"Unsupported ingestion op: {op}")

    def ingest_data(
        self,
        source: str,
        raw_content: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None,
        plugin_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest raw input (math, physics, text, etc.) into symbolic form and store in the Knowledge Graph.
        """

        # 1. Parse raw input into symbolic AST (logic-aware)
        if is_logic_expression(raw_content):
            symbolic_ast = parse_codexlang_to_ast(raw_content)
        else:
            symbolic_ast = parse_raw_input_to_ast(raw_content)

        # 2. Encode AST to simplified CodexLang
        codex_lang_raw = self.rewriter.ast_to_codexlang(symbolic_ast)
        codex_lang = self.rewriter.simplify(codex_lang_raw)

        # 3. Encode CodexLang into glyphs
        glyphs = encode_codex_ast_to_glyphs(codex_lang)

        # 4. Enrich glyphs via SymbolNet (external semantics)
        enriched = self.symbolnet.enrich_glyphs(glyphs)

        # 5. Generate content hash to prevent duplication
        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()

        # 6. Determine container type (Fact, Project, Note, etc.)
        container_type = self._infer_container_type(metadata)

        # 7. Construct symbolic knowledge packet
        packet = {
            "content_hash": content_hash,
            "source": source,
            "plugin_id": plugin_id,
            "user_id": user_id,
            "raw_content": raw_content,
            "symbolic_ast": symbolic_ast,
            "codex_lang": codex_lang,
            "glyphs": enriched,  # use enriched glyphs
            "domains": metadata.get("domains", []),
            "tags": metadata.get("tags", []),
            "origin": metadata.get("origin", source),
            "container_type": container_type,
            "timestamp": datetime.utcnow().isoformat(),
            "proof_link": metadata.get("proof_link"),
            "source_type": metadata.get("source_type", "plugin" if plugin_id else "user"),
        }

        # 8. Register symbolic entry
        symbolic_registry.register(name=content_hash, glyph_tree=symbolic_ast)

        # 9. Inject into Knowledge Graph
        container_id = self.graph_writer.store_symbolic_fact(packet)

        # 10. Register in SQIContainerRegistry
        self.registry.register_entry(container_id, packet)

        return {
            "container_id": container_id,
            "status": "ingested",
            "hash": content_hash,
            "container_type": container_type,
            "glyph_count": len(enriched),
        }

    def _infer_container_type(self, metadata: Dict[str, Any]) -> str:
        """Determine whether input is Fact, Note, Project, etc."""
        if metadata.get("validated") or metadata.get("proof_link"):
            return "Fact"
        if metadata.get("goal") or metadata.get("linked_projects"):
            return "Project"
        if metadata.get("ephemeral") or not metadata.get("verified"):
            return "Note"
        return "Note"