import logging
from typing import List, Dict, Any, Optional
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.symbolnet.conceptnet_adapter import ConceptNetAdapter
from backend.modules.symbolnet.wikidata_adapter import query_wikidata
from backend.modules.symbolnet.wordnet_adapter import query_wordnet
from backend.modules.symbolnet.conceptnet_adapter import query_conceptnet
from backend.modules.symbolnet.symbol_vector_store import get_semantic_vector  # ✅ Real vector source

logger = logging.getLogger(__name__)

class SymbolNetBridge:
    def __init__(self):
        self.adapters = [
            ConceptNetAdapter(),
            # WordNetAdapter(),         # TODO
            # PluginAdapterRegistry()   # TODO
        ]
        self.func_sources = [
            query_conceptnet,
            query_wordnet,
            query_wikidata,
            # query_plugin_sources      # TODO
        ]

    def expand_glyph(self, glyph: LogicGlyph, mode: str = "default") -> List[Dict[str, Any]]:
        results = []
        SKIP_LOGIC_SYMBOLS = {"∀", "→", "∧", "∨", "¬", "∅", "=", "≠", "<", ">", "≥", "≤"}

        try:
            label = getattr(glyph, "label", None) or getattr(glyph, "symbol", None) or glyph.metadata.get("label")
            if not label:
                logger.warning(f"⚠️ Glyph has no label/symbol: {glyph}")
                return results

            label = str(label).strip()
            if label in SKIP_LOGIC_SYMBOLS:
                logger.info(f"⏭️ Skipping logical symbol: '{label}' (id: {glyph.id})")
                glyph.metadata.setdefault("description", f"Logical symbol: {label}")
                glyph.metadata.setdefault("source", "builtin_logic")
                return results

            logger.info(f"🌐 Expanding glyph: '{label}' (id: {glyph.id})")

            for adapter in self.adapters:
                try:
                    source_results = adapter.query(label, context=glyph.context, mode=mode)
                    results.extend(source_results)
                except Exception as e:
                    logger.warning(f"⚠️ Adapter failed: {adapter.__class__.__name__} | {e}")

            for func in self.func_sources:
                try:
                    source_results = func(label, context=glyph.context, mode=mode)
                    results.extend(source_results)
                except Exception as e:
                    logger.warning(f"⚠️ Function source failed: {func.__name__} | {e}")

        except Exception as e:
            logger.error(f"❌ SymbolNet expansion failed for glyph {getattr(glyph, 'id', '∅')}: {e}")

        return results

    def suggest_goal_paths(self, glyph: LogicGlyph, goal: Optional[str] = None) -> List[Dict[str, Any]]:
        related = self.expand_glyph(glyph)
        suggestions = []

        for item in related:
            item["score"] = self.goal_match_score(glyph, goal) if goal else 0.5
            item["match_type"] = "goal_alignment" if item["score"] > 0.8 else "semantic"
            suggestions.append(item)

        return sorted(suggestions, key=lambda x: -x["score"])

    def format_for_kg_injection(self, glyph: LogicGlyph, expansions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        for entry in expansions:
            formatted.append({
                "id": entry.get("id", f"ext:{entry['label']}"),
                "label": entry["label"],
                "type": entry.get("type", "symbolnet"),
                "metadata": {
                    "source": entry.get("source"),
                    "description": entry.get("description"),
                    "score": entry.get("score", 0.5),
                    "match_type": entry.get("match_type", "semantic")
                },
                "linked_from": glyph.id
            })
        return formatted

    def inject_to_container(self, container: Dict[str, Any], glyph: LogicGlyph, expansions: List[Dict[str, Any]]) -> None:
        if "symbolnet" not in container:
            container["symbolnet"] = []
        entries = self.format_for_kg_injection(glyph, expansions)
        container["symbolnet"].extend(entries)
        logger.info(f"🧠 Injected {len(entries)} SymbolNet nodes into container")

    def merge_data(self, enrichment_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        sources = []
        skip_keys = {"symbolnet_enriched", "symbolnet_sources"}

        for source, data in enrichment_results.items():
            if not isinstance(data, dict):
                continue
            sources.append(source)
            for key, value in data.items():
                if key in skip_keys:
                    continue
                if key not in merged:
                    merged[key] = value
                else:
                    if isinstance(value, list) and isinstance(merged[key], list):
                        merged[key] = list(set(merged[key] + value))
                    elif isinstance(value, dict) and isinstance(merged[key], dict):
                        merged[key].update(value)
                    else:
                        merged[f"{source}_{key}"] = value

        merged["symbolnet_enriched"] = True
        merged["symbolnet_sources"] = sorted(sources)
        return merged

    def goal_match_score(self, glyph: LogicGlyph, goal_label: Optional[str]) -> float:
        """
        Computes how well the glyph aligns with a given goal label using semantic vector distance.
        """
        if not goal_label:
            return 0.0
        try:
            glyph_vec = get_semantic_vector(glyph.label or glyph.metadata.get("label", ""))
            goal_vec = get_semantic_vector(goal_label)
            distance = self.semantic_distance(glyph_vec, goal_vec)
            return max(0.0, 1.0 - distance)
        except Exception as e:
            logger.warning(f"⚠️ goal_match_score failed: {e}")
            return 0.0

def semantic_distance(self, vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine distance between two semantic vectors.
    """
    try:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 1.0
        return 1.0 - (dot / (norm1 * norm2))
    except Exception as e:
        logger.warning(f"⚠️ semantic_distance failed: {e}")
        return 1.0