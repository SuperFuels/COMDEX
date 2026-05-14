# 📦 File: backend/modules/glyphwave/qwave/qwave_beam.py

from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any
import uuid
import time


QWaveBeamState = Literal["live", "predicted", "collapsed", "contradicted"]
QWaveBeamType = Literal["QWAVE", "LIGHT", "PREDICTIVE", "SIMULATED"]


@dataclass
class QWaveBeam:
    # 🌐 Core Identity
    id: str = field(default_factory=lambda: f"qbeam_{uuid.uuid4().hex}")
    timestamp: float = field(default_factory=time.time)

    # 📍 Beam Endpoints
    sourceGlyph: str = ""
    targetGlyph: str = ""

    # ⚙️ Beam Properties
    beamType: QWaveBeamType = "QWAVE"
    strength: float = 1.0
    color: str = "#00FFFF"
    state: QWaveBeamState = "live"

    # 🧠 Optional Symbolic Fields
    prediction: Optional[str] = None
    SQI_score: Optional[float] = None
    collapseStatus: Optional[str] = None

    # 🔁 Additional Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "sourceGlyph": self.sourceGlyph,
            "targetGlyph": self.targetGlyph,
            "beamType": self.beamType,
            "strength": self.strength,
            "color": self.color,
            "state": self.state,
            "prediction": self.prediction,
            "SQI_score": self.SQI_score,
            "collapseStatus": self.collapseStatus,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "QWaveBeam":
        return QWaveBeam(
            id=data.get("id", f"qbeam_{uuid.uuid4().hex}"),
            timestamp=data.get("timestamp", time.time()),
            sourceGlyph=data["sourceGlyph"],
            targetGlyph=data["targetGlyph"],
            beamType=data.get("beamType", "QWAVE"),
            strength=data.get("strength", 1.0),
            color=data.get("color", "#00FFFF"),
            state=data.get("state", "live"),
            prediction=data.get("prediction"),
            SQI_score=data.get("SQI_score"),
            collapseStatus=data.get("collapseStatus"),
            metadata=data.get("metadata", {}),
        )

    def describe(self) -> str:
        return (
            f"QWaveBeam {self.id}: {self.sourceGlyph} -> {self.targetGlyph} "
            f"[{self.beamType}, {self.state}, strength={self.strength}]"
        )


# ✅ Helper: Quick creation function
def create_qwave_beam(
    source: str,
    target: str,
    beamType: QWaveBeamType = "QWAVE",
    strength: float = 1.0,
    color: str = "#00FFFF",
    state: QWaveBeamState = "live",
    prediction: Optional[str] = None,
    SQI_score: Optional[float] = None,
    collapseStatus: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> QWaveBeam:
    return QWaveBeam(
        sourceGlyph=source,
        targetGlyph=target,
        beamType=beamType,
        strength=strength,
        color=color,
        state=state,
        prediction=prediction,
        SQI_score=SQI_score,
        collapseStatus=collapseStatus,
        metadata=metadata or {},
    )
