# File: backend/contracts/schemas.py

from typing import List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from jsonschema import Draft202012Validator


# ============================================================
# Pydantic Models (for runtime + code-level ergonomics)
# ============================================================

class BeamEvent(BaseModel):
    event_type: Literal["BeamEvent"] = "BeamEvent"
    eid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin: Literal["photon", "codex", "qwave"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    opcode: str  # e.g., ∇, ⊗, □, MOV, ADD
    args: List[str] = []
    precision: Literal["fp4", "fp8", "int8", "symbolic"] = "symbolic"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    entanglements: List[str] = []


class EntanglementLink(BaseModel):
    event_type: Literal["EntanglementLink"] = "EntanglementLink"
    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    beam_ids: List[str]
    strength: float  # 0.0 -> no link, 1.0 -> fully entangled
    origin: Literal["qwave", "codex", "photon"] = "qwave"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodexCollapseTrace(BaseModel):
    event_type: Literal["CodexCollapseTrace"] = "CodexCollapseTrace"
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin: Literal["codex"] = "codex"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scroll_id: str
    ast_node: str  # e.g., ⊗
    path: List[str]  # AST path to node
    outcome: Literal["collapsed", "forked"]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Unified type
CodexEvent = Union[BeamEvent, EntanglementLink, CodexCollapseTrace]


# ============================================================
# JSON Schemas (for external contract validation)
# ============================================================

BEAM_EVENT_SCHEMA = {
    "type": "object",
    "required": ["event_type", "eid", "origin", "timestamp", "opcode"],
    "properties": {
        "event_type": {"const": "BeamEvent"},
        "eid": {"type": "string"},
        "origin": {"enum": ["photon", "codex", "qwave"]},
        "timestamp": {"type": "string", "format": "date-time"},
        "opcode": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "precision": {"enum": ["fp4", "fp8", "int8", "symbolic"]},
        "metadata": {"type": "object"},
        "entanglements": {"type": "array", "items": {"type": "string"}},
    },
}

ENTANGLEMENT_LINK_SCHEMA = {
    "type": "object",
    "required": ["event_type", "link_id", "beam_ids"],
    "properties": {
        "event_type": {"const": "EntanglementLink"},
        "link_id": {"type": "string"},
        "beam_ids": {"type": "array", "items": {"type": "string"}},
        "strength": {"type": "number"},
        "origin": {"enum": ["qwave", "photon", "codex"]},
        "metadata": {"type": "object"},
    },
}

COLLAPSE_TRACE_SCHEMA = {
    "type": "object",
    "required": ["event_type", "trace_id", "origin", "timestamp", "ast_node"],
    "properties": {
        "event_type": {"const": "CodexCollapseTrace"},
        "trace_id": {"type": "string"},
        "origin": {"enum": ["codex"]},
        "timestamp": {"type": "string", "format": "date-time"},
        "scroll_id": {"type": "string"},
        "ast_node": {"type": "string"},
        "path": {"type": "array", "items": {"type": "string"}},
        "outcome": {"enum": ["collapsed", "forked"]},
        "metadata": {"type": "object"},
    },
}

VALIDATORS = {
    "BeamEvent": Draft202012Validator(BEAM_EVENT_SCHEMA),
    "EntanglementLink": Draft202012Validator(ENTANGLEMENT_LINK_SCHEMA),
    "CodexCollapseTrace": Draft202012Validator(COLLAPSE_TRACE_SCHEMA),
}


def validate_event(event: dict):
    etype = event.get("event_type")
    if etype not in VALIDATORS:
        raise ValueError(f"Unknown event_type: {etype}")
    VALIDATORS[etype].validate(event)
    return True


# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    # Pydantic model -> dict
    be = BeamEvent(origin="photon", opcode="⊗", args=["R1", "R2"])
    print(be.json(indent=2))

    # Validate against schema
    validate_event(be.dict())
    print("✅ BeamEvent validated successfully")

    el = EntanglementLink(
        beam_ids=["eid-1234", "eid-5678"],
        strength=0.87,
        metadata={"collapse_state": "superposed", "phase_shift": 0.12},
    )
    print(el.json(indent=2))
    validate_event(el.dict())
    print("✅ EntanglementLink validated successfully")

    ct = CodexCollapseTrace(
        scroll_id="scroll-xyz",
        ast_node="⊗",
        path=["root", "expr[2]", "⊗"],
        outcome="collapsed",
        metadata={"soul_law": "validated", "confidence": 0.76},
    )
    print(ct.json(indent=2))
    validate_event(ct.dict())
    print("✅ CodexCollapseTrace validated successfully")