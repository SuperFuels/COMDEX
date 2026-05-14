#!/usr/bin/env python3
# ================================================================
# 🧬 DNA Bridge Integration - Phase R9
# ================================================================
# Connects ReflexConsolidationLayer -> dna_writer mutation engine
# enabling self-directed symbolic code evolution based on reflex data.
# ================================================================

import json, time, logging
from pathlib import Path
from backend.modules.aion_cognition.reflex_consolidation_layer import ReflexConsolidationLayer
from backend.modules.dna_chain import dna_writer
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.writable_guard import is_write_allowed

logger = logging.getLogger(__name__)
OUT = Path("data/analysis/dna_autoproposals.json")

class DNABridgeIntegration:
    def __init__(self, threshold: float = 0.55):
        self.threshold = threshold
        self.consolidator = ReflexConsolidationLayer()
        self.outbox = []

    # ------------------------------------------------------------
    def evaluate_reflex_atlas(self):
        """Load the Cognitive Reflex Atlas and identify weak domains."""
        atlas = self.consolidator.consolidate()
        entries = atlas.get("entries", [])
        weak = [e for e in entries if e["weight"] < self.threshold]
        logger.info(f"[DNA Bridge] {len(weak)} weak reflex domains detected (w < {self.threshold})")
        return weak

    # ------------------------------------------------------------
    def propose_mutations(self):
        """Generate DNA mutation proposals for low-weight entries."""
        weak_entries = self.evaluate_reflex_atlas()
        proposals = []

        for entry in weak_entries:
            domains = ", ".join(entry.get("domains", []))
            reason = f"Low reflex resonance (w={entry['weight']:.3f}) in domains: {domains}"
            context = f"ReflexAtlas::{entry['hash']}"

            try:
                if is_write_allowed("backend/modules/aion_cognition/rulebook_index.py"):
                    proposal = dna_writer.propose_dna_mutation(
                        reason=reason,
                        source="dna_bridge_integration",
                        code_context=context,
                        new_logic="# Auto-generated DNA self-tuning suggestion"
                    )
                    proposals.append(proposal)
                    logger.info(f"[DNA Bridge] Proposed mutation -> {proposal['proposal_id']}")
                else:
                    logger.warning(f"[DNA Bridge] Write not allowed for {context}")
            except Exception as e:
                logger.error(f"[DNA Bridge] Mutation proposal failed: {e}")

        self.outbox = proposals
        self.save()
        return proposals

    # ------------------------------------------------------------
    def save(self):
        """Persist all generated proposals."""
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(self.outbox, indent=2))
        logger.info(f"[DNA Bridge] Saved {len(self.outbox)} mutation proposals -> {OUT}")
        DNA_SWITCH.register(__file__)
        return True