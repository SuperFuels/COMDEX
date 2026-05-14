from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Literal
import time
import json
import uuid


TeacherType = Literal["human", "gpt", "claude", "system"]


@dataclass
class CorrectionRecord:
    # What AION said before correction
    aion_original_response: str

    # What the teacher says is better / correct
    corrected_response: str

    # Why correction was made (critical signal for D-Lang)
    correction_reason: str

    # What concept is being taught (critical signal for D-Lang)
    concept_label: str

    # How confident AION should store this learning
    target_confidence: float  # [0,1]

    # Optional tags for routing later
    tags: List[str] = field(default_factory=list)

    # Optional structured notes
    notes: Optional[str] = None


@dataclass
class TeachingTurn:
    turn_id: str
    user_input: str
    inferred_intent: Optional[str] = None
    topic: Optional[str] = None

    # AION state at time of response
    aion_response: Optional[str] = None
    aion_confidence: Optional[float] = None

    # Teacher correction payload
    correction: Optional[CorrectionRecord] = None

    # Teacher evaluation
    accepted_as_is: bool = False
    teaching_notes: Optional[str] = None

    timestamp: float = field(default_factory=time.time)


@dataclass
class TeachingSession:
    session_id: str
    teacher_type: TeacherType
    teacher_id: str  # e.g. "kevin", "gpt-5", "claude"
    mode: Literal["manual", "assisted", "automated"]
    objective: str

    student_id: str = "AION"
    language_track: str = "D-Lang"   # language acquisition stream
    task_track: str = "D-Task"       # outcome/task refinement stream

    turns: List[TeachingTurn] = field(default_factory=list)

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, turn: TeachingTurn) -> None:
        self.turns.append(turn)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def new_teaching_session(
    teacher_type: TeacherType,
    teacher_id: str,
    mode: Literal["manual", "assisted", "automated"],
    objective: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TeachingSession:
    return TeachingSession(
        session_id=f"teach_{uuid.uuid4().hex[:12]}",
        teacher_type=teacher_type,
        teacher_id=teacher_id,
        mode=mode,
        objective=objective,
        metadata=metadata or {},
    )


def validate_target_confidence(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value