# -*- coding: utf-8 -*-
# backend/modules/sqi/drift_types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class DriftStatus(str, Enum):
    OPEN = "OPEN"         # has gaps
    DRIFTING = "DRIFTING" # gaps known + growing/complex
    CLOSED = "CLOSED"     # no gaps

@dataclass
class DriftGap:
    name: str
    reason: str
    missing: List[str] = field(default_factory=list)
    weight: float = 1.0     # how "big" the gap feels
    hints: List[str] = field(default_factory=list)

@dataclass
class DriftReport:
    container_id: Optional[str]
    total_weight: float
    status: DriftStatus
    gaps: List[DriftGap] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)