# backend/modules/holo/holo_ir.py
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

HoloId = str
ContainerId = str


@dataclass
class HoloIR:
    # — Identity & lineage —
    holo_id: HoloId
    container_id: ContainerId
    name: Optional[str] = None
    symbol: Optional[str] = None
    # e.g. "memory", "sandbox", "crystal", "library", "snapshot", "program"
    kind: Optional[str] = None

    origin: Dict[str, Any] = dc_field(default_factory=dict)
    version: Dict[str, Any] = dc_field(default_factory=dict)

    # — Graph / GHX layout —
    ghx: Dict[str, Any] = dc_field(default_factory=dict)

    # — Field physics / metrics —
    field: Dict[str, Any] = dc_field(default_factory=dict)

    # — Beams / QWave —
    beams: List[Dict[str, Any]] = dc_field(default_factory=list)
    multiverse_frame: Optional[str] = None

    # — Views / lenses —
    views: Dict[str, Any] = dc_field(default_factory=dict)

    # — Indexing / patterns —
    indexing: Dict[str, Any] = dc_field(default_factory=dict)

    # — Timefold / snapshots —
    timefold: Dict[str, Any] = dc_field(default_factory=dict)

    # — Ledger / security —
    ledger: Dict[str, Any] = dc_field(default_factory=dict)
    security: Dict[str, Any] = dc_field(default_factory=dict)

    # — Sandbox / collaboration —
    sandbox: Dict[str, Any] = dc_field(default_factory=dict)
    collaboration: Dict[str, Any] = dc_field(default_factory=dict)

    # — References / extra —
    references: Dict[str, Any] = dc_field(default_factory=dict)
    extra: Dict[str, Any] = dc_field(default_factory=dict)