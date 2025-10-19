# ===============================
# 📁 backend/quant/qcore/qsheet_cell.py
# ===============================
"""
💠 QSheetCell — Symbolic-Photonic Extension of GlyphCell
-------------------------------------------------------

A QSheetCell represents the Q-Series version of a GlyphCell:
a 4-D symbolic element enriched with photonic resonance metrics
(Φ_mean, ψ_mean, κ, coherence_energy) and cross-layer integration
hooks for QPy, QTensor, and QLearn.

Each QSheetCell acts as a live symbolic-physical carrier in the
Tessaris architecture, unifying logic, resonance, and cognition.

Example:
    from backend.quant.qcore.qsheet_cell import QSheetCell
    q = QSheetCell.from_glyph(glyph_cell)
    q.compute_resonance_state()
    state = q.export_state()
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import math
import uuid
from datetime import datetime

# --- Defensive import for GlyphCell ---
try:
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
except Exception:
    # fallback minimal GlyphCell
    class GlyphCell:  # type: ignore
        def __init__(self, id: str, logic: str = "", position=None, emotion="neutral"):
            self.id = id
            self.logic = logic
            self.position = position or [0, 0, 0, 0]
            self.emotion = emotion
            self.sqi_score = 1.0
            self.wave_beams = []
            self.trace = []

# --- Utility ---
def now_utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class QSheetCell:
    """
    🧬 QSheetCell — Symbolic-Photonic state carrier.

    Extends GlyphCell with physical resonance metrics and
    symbolic introspection data for Q-Series modules.
    """
    id: str
    logic: str
    position: List[int]
    emotion: str = "neutral"

    # --- Symbolic resonance metrics ---
    Φ_mean: float = 1.0
    ψ_mean: float = 1.0
    κ: float = 0.0              # curvature / coupling
    coherence_energy: float = 1.0
    resonance_index: float = 1.0
    phase_offset: float = 0.0
    phase_velocity: float = 0.0

    # --- Symbolic cognition metrics (E7) ---
    entropy: float = 0.0
    novelty: float = 0.0
    harmony: float = 1.0
    sqi_score: float = 1.0

    # --- Trace / history ---
    trace: List[str] = field(default_factory=list)
    wave_beams: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=now_utc_iso)

    # --- Contextual metadata ---
    meta: Dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # Construction
    # =========================================================================
    @classmethod
    def from_glyph(cls, glyph: GlyphCell) -> "QSheetCell":
        """
        🔄 Create a QSheetCell from an existing GlyphCell.
        Copies logical and emotional state; initializes resonance defaults.
        """
        return cls(
            id=glyph.id,
            logic=glyph.logic,
            position=getattr(glyph, "position", [0, 0, 0, 0]),
            emotion=getattr(glyph, "emotion", "neutral"),
            sqi_score=getattr(glyph, "sqi_score", 1.0),
            trace=list(getattr(glyph, "trace", [])),
            wave_beams=list(getattr(glyph, "wave_beams", [])),
            meta=getattr(glyph, "meta", {}) or {},
        )

    def to_glyph(self) -> GlyphCell:
        """
        ↩️ Convert back to a GlyphCell (for AtomSheet export or legacy engines).
        """
        g = GlyphCell(
            id=self.id,
            logic=self.logic,
            position=self.position,
            emotion=self.emotion,
        )
        g.sqi_score = self.sqi_score
        g.trace = list(self.trace)
        g.wave_beams = list(self.wave_beams)
        # Optionally attach resonance info into meta
        g.meta = dict(self.meta)
        g.meta.update({
            "Φ_mean": self.Φ_mean,
            "ψ_mean": self.ψ_mean,
            "κ": self.κ,
            "coherence_energy": self.coherence_energy,
            "resonance_index": self.resonance_index,
        })
        return g

    # =========================================================================
    # Symbolic resonance computations
    # =========================================================================
    def compute_resonance_state(self) -> Dict[str, float]:
        """
        🔬 Compute Φ–ψ resonance metrics and update the cell.
        This simplified model uses symbolic heuristics that will later
        be replaced by the QTensor physics engine.
        """
        # Basic pseudo-wave inference from logic length and emotion
        length_factor = len(self.logic) / 42.0
        emotion_factor = {
            "neutral": 1.0,
            "inspired": 1.1,
            "curious": 1.05,
            "melancholy": 0.95,
            "playful": 1.08,
        }.get(self.emotion, 1.0)

        Φ = max(0.01, min(1.0, emotion_factor * (0.8 + 0.2 * math.sin(length_factor))))
        ψ = max(0.01, min(1.0, 1.0 - abs(0.5 - length_factor % 1.0)))
        κ = round(math.tanh((Φ - ψ) * 3.0), 6)
        coherence = 1.0 - abs(Φ - ψ) * 0.5
        resonance_index = (Φ * ψ * coherence)

        self.Φ_mean = Φ
        self.ψ_mean = ψ
        self.κ = κ
        self.coherence_energy = coherence
        self.resonance_index = resonance_index
        self.phase_offset = (Φ - ψ)
        self.phase_velocity = κ * 0.42  # placeholder scaling

        beam = {
            "beam_id": f"beam_{self.id}_{uuid.uuid4().hex[:8]}",
            "token": "∇",
            "Φψ": {"Φ": Φ, "ψ": ψ, "κ": κ, "coherence": coherence},
            "timestamp": now_utc_iso(),
        }
        self.wave_beams.append(beam)

        return {
            "Φ_mean": Φ,
            "ψ_mean": ψ,
            "κ": κ,
            "coherence_energy": coherence,
            "resonance_index": resonance_index,
        }

    # =========================================================================
    # Derived metrics
    # =========================================================================
    def compute_entropy(self) -> float:
        if not self.logic:
            self.entropy = 0.0
            return 0.0
        chars = [ch for ch in self.logic if ch.strip()]
        freq = {c: chars.count(c) for c in set(chars)}
        total = len(chars)
        H = -sum((n / total) * math.log2(n / total) for n in freq.values())
        max_H = math.log2(len(freq)) if len(freq) > 1 else 1.0
        self.entropy = round(H / max_H, 4)
        return self.entropy

    def compute_harmony_novelty(self, peers: List["QSheetCell"]) -> None:
        """
        Compute harmony (average similarity) and novelty (1 - max similarity)
        among a list of peer cells using token overlap.
        """
        tokens = set(self.logic.split())
        sims = []
        for p in peers:
            if p.id == self.id:
                continue
            ptoks = set(p.logic.split())
            union = tokens | ptoks
            if not union:
                continue
            sims.append(len(tokens & ptoks) / len(union))
        self.harmony = sum(sims) / len(sims) if sims else 1.0
        self.novelty = 1.0 - (max(sims) if sims else 0.0)

    # =========================================================================
    # Export
    # =========================================================================
    def export_state(self, include_meta: bool = True) -> Dict[str, Any]:
        """
        📤 Export full Q-Series symbolic-photonic state.
        Compatible with `.sqs.qsheet.json` and telemetry serialization.
        """
        data = asdict(self)
        if not include_meta:
            data.pop("meta", None)
        return data

    # =========================================================================
    # Representation
    # =========================================================================
    def __repr__(self) -> str:
        return (
            f"QSheetCell(id={self.id}, Φ={self.Φ_mean:.3f}, ψ={self.ψ_mean:.3f}, "
            f"κ={self.κ:.3f}, coherence={self.coherence_energy:.3f}, "
            f"emotion={self.emotion}, sqi={self.sqi_score:.2f})"
        )