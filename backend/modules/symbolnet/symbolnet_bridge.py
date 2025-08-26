import logging
from typing import List, Dict, Any, Optional

from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.symbolnet.conceptnet_adapter import ConceptNetAdapter
from backend.modules.symbolnet.wikidata_adapter import query_wikidata
from backend.modules.symbolnet.wordnet_adapter import query_wordnet
from backend.modules.symbolnet.conceptnet_adapter import query_conceptnet
# TODO: from backend.modules.symbolnet.plugin_adapter_registry import query_plugin_sources
# TODO: Implement WordNetAdapter as class
# TODO: Implement PluginAdapterRegistry class

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
        """
        Expand a LogicGlyph by querying all connected semantic sources.

        Returns a list of related semantic nodes with metadata and type labels.
        """
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
        """
        Suggest possible expansion paths toward a goal (if defined).
        """
        related = self.expand_glyph(glyph)
        suggestions = []
        for item in related:
            if goal and goal.lower() in item.get("description", "").lower():
                item["score"] = 1.0
                item["match_type"] = "goal_alignment"
            else:
                item["score"] = 0.5
            suggestions.append(item)
        return sorted(suggestions, key=lambda x: -x["score"])

    def format_for_kg_injection(self, glyph: LogicGlyph, expansions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert external results into LogicGlyph-like dicts for KG injection or QFC display.
        """
        formatted = []
        for entry in expansions:
            formatted.append({
                "id": entry.get("id", f"ext:{entry['label']}"),
                "label": entry["label"],
                "type": entry.get("type", "symbolnet"),
                "metadata": {
                    "source": entry.get("source"),
                    "description": entry.get("description"),
                    "score": entry.get("score", 0.5)
                },
                "linked_from": glyph.id
            })
        return formatted

    def inject_to_container(self, container: Dict[str, Any], glyph: LogicGlyph, expansions: List[Dict[str, Any]]) -> None:
        """
        Inject semantic expansions directly into a .dc container under the SymbolNet trace path.
        """
        if "symbolnet" not in container:
            container["symbolnet"] = []
        entries = self.format_for_kg_injection(glyph, expansions)
        container["symbolnet"].extend(entries)
        logger.info(f"🧠 Injected {len(entries)} SymbolNet nodes into container")

    def merge_data(self, enrichment_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge enrichment results from multiple sources into a unified metadata dict.

        Args:
            enrichment_results (Dict[str, Dict]): Raw enrichment data keyed by source name.

        Returns:
            Dict[str, Any]: Cleaned and merged semantic metadata.
        """
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