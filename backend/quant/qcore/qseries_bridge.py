# ===============================
# 📁 backend/quant/qcore/qseries_bridge.py
# ===============================
"""
🔗 QSeriesBridge - AtomSheet ↔ QSheet Synchronization Layer
-----------------------------------------------------------

This module converts between classic 4-D AtomSheet / GlyphCell structures
and QSheetCell objects in the Q-Series runtime.  It acts as a universal
bridge for symbolic-photonic synchronization, resonance computation,
and export.

Typical Usage:
    from backend.quant.qcore.qseries_bridge import QSeriesBridge
    bridge = QSeriesBridge(sheet)
    bridge.initialize_qsheet()
    qcells = bridge.qcells
    bridge.compute_all_resonances()
    export = bridge.export_qsheet_json()
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

# --- Imports --------------------------------------------------------------
try:
    from backend.modules.atomsheets.models import AtomSheet
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
except Exception:
    # fallback minimal types
    class AtomSheet:
        def __init__(self, id: str, cells: Dict[str, Any]):
            self.id = id
            self.cells = cells

    class GlyphCell:
        def __init__(self, id: str, logic: str = "", position=None, emotion="neutral"):
            self.id = id
            self.logic = logic
            self.position = position or [0, 0, 0, 0]
            self.emotion = emotion
            self.sqi_score = 1.0

from backend.quant.qcore.qsheet_cell import QSheetCell

# --------------------------------------------------------------------------
class QSeriesBridge:
    """
    🌉 QSeriesBridge - manages conversion and synchronization between
    AtomSheet/GlyphCells and QSheetCells.
    """

    def __init__(self, atomsheet: AtomSheet):
        self.sheet = atomsheet
        self.qcells: Dict[str, QSheetCell] = {}

    # ------------------------------------------------------------------
    # Initialization / Conversion
    # ------------------------------------------------------------------
    def initialize_qsheet(self) -> None:
        """
        🔄 Convert all GlyphCells from the AtomSheet into QSheetCells.
        Existing resonance metrics are preserved when available.
        """
        self.qcells.clear()
        for cid, g in self.sheet.cells.items():
            q = QSheetCell.from_glyph(g)
            # Pull resonance metrics from glyph.meta if present
            meta = getattr(g, "meta", {}) or {}
            q.Φ_mean = meta.get("Φ_mean", q.Φ_mean)
            q.ψ_mean = meta.get("ψ_mean", q.ψ_mean)
            q.κ = meta.get("κ", q.κ)
            q.coherence_energy = meta.get("coherence_energy", q.coherence_energy)
            q.resonance_index = meta.get("resonance_index", q.resonance_index)
            self.qcells[cid] = q

    # ------------------------------------------------------------------
    # Resonance Computation
    # ------------------------------------------------------------------
    def compute_all_resonances(self) -> Dict[str, Dict[str, float]]:
        """
        ⚛️ Compute Φ-ψ resonance state for all QSheetCells.
        Returns mapping of cell_id -> resonance metrics.
        """
        results: Dict[str, Dict[str, float]] = {}
        for cid, qc in self.qcells.items():
            results[cid] = qc.compute_resonance_state()
        return results

    def compute_relational_metrics(self) -> None:
        """
        🧠 Compute entropy / harmony / novelty across all cells.
        """
        qlist = list(self.qcells.values())
        for qc in qlist:
            qc.compute_entropy()
        for qc in qlist:
            qc.compute_harmony_novelty(qlist)

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------
    def sync_back_to_atomsheet(self) -> None:
        """
        ⬅️ Push QSheetCell metrics back into AtomSheet.GlyphCells.
        Ensures the AtomSheet view reflects latest resonance values.
        """
        for cid, qc in self.qcells.items():
            if cid not in self.sheet.cells:
                continue
            g = self.sheet.cells[cid]
            g.sqi_score = qc.sqi_score
            g.meta = getattr(g, "meta", {}) or {}
            g.meta.update({
                "Φ_mean": qc.Φ_mean,
                "ψ_mean": qc.ψ_mean,
                "κ": qc.κ,
                "coherence_energy": qc.coherence_energy,
                "resonance_index": qc.resonance_index,
                "entropy": qc.entropy,
                "novelty": qc.novelty,
                "harmony": qc.harmony,
            })
            g.wave_beams = list(qc.wave_beams)

    # ------------------------------------------------------------------
    # Export / Telemetry
    # ------------------------------------------------------------------
    def export_qsheet_json(self, include_meta: bool = True) -> Dict[str, Any]:
        """
        📤 Export a `.sqs.qsheet.json` snapshot for telemetry or replay.
        """
        return {
            "type": "qsheet_snapshot",
            "sheet_id": self.sheet.id,
            "cell_count": len(self.qcells),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "cells": [
                qc.export_state(include_meta=include_meta)
                for qc in self.qcells.values()
            ],
        }

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def get_cell(self, cid: str) -> Optional[QSheetCell]:
        return self.qcells.get(cid)

    def __repr__(self) -> str:
        return f"QSeriesBridge(sheet={self.sheet.id}, qcells={len(self.qcells)})"