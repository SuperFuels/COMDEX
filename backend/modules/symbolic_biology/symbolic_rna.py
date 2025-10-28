#!/usr/bin/env python3
# ================================================================
# 🧬 SymbolicRNA — Messenger Layer (DNA → RNA)
# ================================================================
# Extracts symbolic scrolls from Codex memory or .dc containers.
# Acts as a messenger for glyph fragments, rewrite tags, and mutation
# sequences passed into the Ribosome Engine for synthesis.
# ================================================================
from pathlib import Path
import json, time, logging, random
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
from backend.modules.soul.soul_laws import validate_ethics

logger = logging.getLogger(__name__)
OUT = Path("data/analysis/symbolic_rna_traces.json")

class SymbolicRNA:
    def __init__(self, source="codex_memory"):
        self.memory = MemoryEngine()
        self.source = source
        self.scrolls = []
        self.timestamp = time.time()

    # ------------------------------------------------------------
    def transcribe(self, container: str, include_mutations: bool = True):
        """
        Extract symbolic scrolls (logic sequences) from a .dc container or
        memory source, optionally applying CRISPR-AI mutation injections.
        """
        try:
            mem_data = self.memory.load_container(container)
        except Exception:
            logger.warning(f"[RNA] Could not load memory container: {container}")
            return []

        for glyph in mem_data.get("glyphs", []):
            scroll = {
                "id": glyph.get("id"),
                "content": glyph.get("logic", ""),
                "entropy": glyph.get("entropy", 0.5),
                "coherence": glyph.get("coherence", 0.5),
                "tags": glyph.get("tags", []),
                "ethical": True,
                "mutated": False,
            }

            # Inject symbolic mutation if flagged or entropy too high
            if include_mutations and scroll["entropy"] > 0.7:
                try:
                    mutation = generate_mutation_proposal(
                        sequence=scroll["content"],
                        context={"source": container, "id": glyph.get("id")},
                    )
                    if validate_ethics(mutation):
                        scroll["mutation"] = mutation
                        scroll["mutated"] = True
                except Exception as e:
                    logger.error(f"[RNA] Mutation skipped for {glyph.get('id')}: {e}")

            self.scrolls.append(scroll)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(self.scrolls, indent=2))
        logger.info(f"[RNA] Transcribed {len(self.scrolls)} symbolic scrolls → {OUT}")
        return self.scrolls

    # ------------------------------------------------------------
    def extract_from_container(self, container_path: str):
        """
        Alternate mode: direct .dc → RNA scroll extraction
        (used by symbolic biology and Ribosome pipelines).
        """
        path = Path(container_path)
        if not path.exists():
            raise FileNotFoundError(f"Container not found: {path}")

        try:
            data = json.loads(path.read_text())
        except Exception as e:
            logger.error(f"[SymbolicRNA] Failed to load container {path}: {e}")
            return {}

        # Apply a symbolic mutation proposal for entropy adaptation
        seq = "ATCGATCG"
        mutation = generate_mutation_proposal(seq, context={"container": str(path)})

        scroll = {
            "type": "RNA_SCROLL",
            "source": str(path),
            "timestamp": time.time(),
            "content": data,
            "mutation_proposal": mutation,
        }

        logger.info(f"[SymbolicRNA] Extracted RNA scroll from {path.name}")
        return scroll

    # ------------------------------------------------------------
    def export_scroll(self, path="data/exports/symbolic_scroll.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.scrolls, open(path, "w"), indent=2)
        logger.info(f"[RNA] Exported symbolic scroll → {path}")
        return path