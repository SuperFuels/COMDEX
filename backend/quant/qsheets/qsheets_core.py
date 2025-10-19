# ===============================
# 📁 backend/quant/qsheets/qsheets_core.py
# ===============================
"""
🧮 QSheets Core — Quantum Symbolic Spreadsheet Engine
-----------------------------------------------------
Provides a 4D spreadsheet abstraction layer that fuses:
  • QLang symbolic expressions
  • QTensorField resonance computation
  • Symatics Φ–ψ coherence analytics

Each cell stores:
    id, logic (QLang), ψ-field state, resonance metrics, and beam traces.

Extends the AtomSheet / GlyphCell model into the Quantum Quad Core (QQC)
execution domain for resonant symbolic computation.
"""

from __future__ import annotations
import json
import numpy as np
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# --- Quant Imports ----------------------------------------------------
from backend.quant.qlang.qlang_parser import QLangParser
from backend.quant.qtensor.qtensor_field import QTensorField, random_field
from backend.quant.qcompiler.qcompiler_core import QCompilerCore
from backend.modules.atomsheets.models import AtomSheet
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell


# ----------------------------------------------------------------------
# Data Models
# ----------------------------------------------------------------------
@dataclass
class QSheetCell(GlyphCell):
    """
    Quantum-enhanced GlyphCell with field and resonance data.
    Inherits logic, position, emotion, trace, and SQI context.
    """
    ψ: Optional[QTensorField] = None
    Φ_mean: float = 1.0
    ψ_mean: float = 1.0
    resonance_index: float = 1.0
    coherence_energy: float = 1.0

    def __init__(
        self,
        id: str,
        logic: str,
        position: Optional[List[int]] = None,
        emotion: str = "neutral",
        prediction: str = "",
        **kwargs,
    ):
        # initialize parent GlyphCell
        super().__init__(
            id=id,
            logic=logic,
            position=position or [0, 0, 0, 0],
            emotion=emotion,
            prediction=prediction,
        )
        # initialize quantum extensions
        self.ψ = kwargs.get("ψ")
        self.Φ_mean = kwargs.get("Φ_mean", 1.0)
        self.ψ_mean = kwargs.get("ψ_mean", 1.0)
        self.resonance_index = kwargs.get("resonance_index", 1.0)
        self.coherence_energy = kwargs.get("coherence_energy", 1.0)

    def attach_resonance(self, Φ_mean: float, ψ_mean: float, r_idx: float, coh: float):
        """Attach computed resonance metrics to the cell."""
        self.Φ_mean = Φ_mean
        self.ψ_mean = ψ_mean
        self.resonance_index = r_idx
        self.coherence_energy = coh
        self.wave_beams.append({
            "beam_id": f"beam_{self.id}",
            "token": "⟲",
            "resonance_index": r_idx,
            "coherence_energy": coh,
        })


@dataclass
class QSheet(AtomSheet):
    """4D sheet containing QLang + QTensor logic."""
    cells: Dict[str, QSheetCell] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Core Engine
# ----------------------------------------------------------------------
class QSheetsCore:
    """
    Executes QSheets as live quantum-symbolic structures.
    """

    def __init__(self):
        self.parser = QLangParser()
        self.compiler = QCompilerCore()

    # --------------------------------------------------------------
    def load(self, src: str) -> QSheet:
        """Load QSheet from .qsheet (JSON) or legacy .atom file."""
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)

        cells: Dict[str, QSheetCell] = {}
        for c in data.get("cells", []):
            cells[c["id"]] = QSheetCell(
                id=c.get("id", ""),
                logic=c.get("logic", ""),
                position=c.get("position", [0, 0, 0, 0]),
                emotion=c.get("emotion", "neutral"),
                prediction=c.get("prediction", ""),
            )
        return QSheet(
            id=data.get("id", "qsheet"),
            title=data.get("title", ""),
            dims=data.get("dims", [1, 1, 1, 1]),
            meta=data.get("meta", {}),
            cells=cells,
        )

    # --------------------------------------------------------------
    async def execute(self, sheet: QSheet, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute all cells using QLang → QTensor → resonance evaluation.
        """
        ctx = ctx or {}
        results: Dict[str, Any] = {}
        for cid, c in sheet.cells.items():
            if not getattr(c, "logic", None):
                continue

            # Parse / compile / simulate symbolic expression
            expr = self.parser.parse(c.logic)
            graph = self.compiler.compile_expr(expr)
            ψ1, ψ2 = random_field((4, 4)), random_field((4, 4))
            sim = self.compiler.simulate({"ψ1": ψ1, "ψ2": ψ2})

            Φ_mean = float(np.mean(np.abs(ψ1.data)))
            ψ_mean = float(np.mean(np.abs(ψ2.data)))
            r_idx = float(sim.get("correlation", 1.0))
            coh = float(sim.get("measurement", 1.0))

            c.attach_resonance(Φ_mean, ψ_mean, r_idx, coh)

            results[cid] = {
                "correlation": r_idx,
                "measurement": coh,
                "Φ_mean": Φ_mean,
                "ψ_mean": ψ_mean,
            }

        return {
            "status": "ok",
            "cells": len(sheet.cells),
            "results": results,
        }

    # --------------------------------------------------------------
    def export(self, sheet: QSheet, path: Optional[str] = None) -> Dict[str, Any]:
        """Export current QSheet state for HUD / telemetry."""
        payload = {
            "id": sheet.id,
            "title": sheet.title,
            "dims": sheet.dims,
            "meta": sheet.meta,
            "cells": [
                {
                    "id": c.id,
                    "logic": c.logic,
                    "Φ_mean": c.Φ_mean,
                    "ψ_mean": c.ψ_mean,
                    "resonance_index": c.resonance_index,
                    "coherence_energy": c.coherence_energy,
                    "wave_beams": c.wave_beams,
                }
                for c in sheet.cells.values()
            ],
        }
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        return payload

    # --------------------------------------------------------------
    def run_test(self) -> Dict[str, Any]:
        """Self-test for symbolic–tensor fusion."""
        sheet = QSheet(
            id="test_qsheet",
            title="Resonance Demo",
            cells={
                "A1": QSheetCell(id="A1", logic="ψ1 ⊕ ψ2 ∇ μ", position=[0, 0, 0, 0]),
                "B1": QSheetCell(id="B1", logic="ψ1 ↔ ψ2", position=[1, 0, 0, 0]),
            },
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(self.execute(sheet))
        loop.close()
        return {"cells_executed": res["cells"], "status": res["status"]}


# ----------------------------------------------------------------------
# Manual Self-Test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    core = QSheetsCore()
    from pprint import pprint
    pprint(core.run_test())