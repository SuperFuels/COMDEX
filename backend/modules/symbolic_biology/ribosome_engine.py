#!/usr/bin/env python3
# ================================================================
# 🧫 RibosomeEngine — Phase R12: Symbolic Protein Translator
# ================================================================
# Translates SymbolicRNA scrolls into symbolic protein chains and
# photon traces for QQC/Aion execution. Integrates Symatics codon
# mapping, resonance drift, and ethics validation.
# ================================================================

import json, time, logging, math, random
from pathlib import Path
from backend.modules.soul.soul_laws import validate_ethics
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

logger = logging.getLogger(__name__)
OUT = Path("data/analysis/ribosome_synthesis_traces.json")

Theta = ResonanceHeartbeat(namespace="ribosome_engine")

class RibosomeEngine:
    def __init__(self):
        self.history = []
        self.last_synthesis = None
        self.emit_photon_trace = True

    # ------------------------------------------------------------
    def synthesize(self, path: str):
        """Read RNA scroll JSON and synthesize symbolic protein output."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"RNA scroll not found: {path}")

        scroll = json.loads(p.read_text())
        logger.info(f"[🧬 Ribosome] Synthesizing from RNA scroll ({len(str(scroll))} chars)...")

        # 🔬 Extract symbolic text
        if isinstance(scroll, dict) and "content" in scroll:
            if isinstance(scroll["content"], dict) and "glyphs" in scroll["content"]:
                # Flatten glyph logic strings
                content = " ".join([g.get("logic", "") for g in scroll["content"]["glyphs"]])
            else:
                content = str(scroll["content"])
        else:
            content = str(scroll)

        metadata = {
            "source": scroll.get("source", "unknown"),
            "timestamp": scroll.get("timestamp", 0),
            "mutation": scroll.get("mutation_proposal", {}),
        }

        product, photon_trace = self.translation_pipeline(content, metadata)

        out_path = Path("data/tmp/ribosome_output.prot")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(product)
        logger.info(f"[✅ Ribosome] Synthesis complete → {out_path}")

        if self.emit_photon_trace:
            photo_path = Path("data/tmp/ribosome_photon_trace.photo")
            photo_path.write_text(json.dumps(photon_trace, indent=2))
            logger.info(f"[💡 PhotonTrace] Emitted → {photo_path}")

        self.last_synthesis = {
            "timestamp": time.time(),
            "input": path,
            "output": str(out_path),
            "photon_trace": str(photo_path) if self.emit_photon_trace else None,
        }
        self.history.append(self.last_synthesis)
        self.export_results()
        return product

    # ------------------------------------------------------------
    def translation_pipeline(self, content: str, metadata: dict):
        """
        Translates Symatics symbolic operators into codons and
        synthesizes a symbolic protein chain with resonance drift.
        """
        # Symatics codon map
        codon_map = {
            "⊕": ("SYN", "Superposition", "💠"),
            "↔": ("ENT", "Entanglement", "🪞"),
            "⟲": ("RES", "Resonance", "🔁"),
            "⇒": ("TRG", "Trigger", "🎯"),
            "μ": ("MES", "Measurement", "📏"),
            "π": ("PRO", "Projection", "📡"),
        }

        tokens = list(content.replace("\n", " ").replace(" ", ""))
        protein_chain = []
        photon_trace = []

        sqi, rho = 0.55, 0.75
        drift = 0.02

        for sym in tokens:
            if sym in codon_map:
                codon, label, icon = codon_map[sym]
                sqi = min(1.0, round(sqi + random.uniform(0.01, drift), 3))
                rho = max(0.0, round(rho - random.uniform(0.005, 0.02), 3))
                entry = f"{icon} {label} ({codon}) | SQI={sqi:.2f} | ρ={rho:.2f}"
                protein_chain.append(entry)
                photon_trace.append({
                    "symbol": sym,
                    "codon": codon,
                    "phase": label,
                    "sqi": sqi,
                    "rho": rho,
                    "timestamp": time.time()
                })

        # Ethics validation: ensure final sequence passes resonance law
        full_sequence = " ".join([p["codon"] for p in photon_trace])
        ethical = validate_ethics(full_sequence)
        Theta.event("protein_synthesis", integrity=sqi, resonance=rho, ethics=ethical)

        header = (
            f"🧬 SYMBOLIC PROTEIN CHAIN\n"
            f"Origin: {metadata.get('source', 'unknown')}\n"
            f"Phase: R12 — Symatic Translation\n"
            f"Codons processed: {len(protein_chain)}\n"
            f"Ethics: {'✅' if ethical else '⚠️'}\n"
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"────────────────────────────\n"
        )

        return header + "\n".join(protein_chain), photon_trace

    # ------------------------------------------------------------
    def export_results(self, path="data/exports/symbolic_synthesis.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.history, open(path, "w"), indent=2)
        logger.info(f"[Ribosome] Exported synthesis results → {path}")
        return path