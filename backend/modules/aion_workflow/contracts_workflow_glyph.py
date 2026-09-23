from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

WORKFLOW_SAVE_SCHEMA_VERSION = "aion.workflow_save.v1"
WORKFLOW_GLYPH_SCHEMA_VERSION = "aion.workflow_glyph.v1"
WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION = "aion.workflow_canvas_layout.v1"
WORKFLOW_NAMESPACE = "aion.workflow"

AION_WORKFLOW_OP_SEQUENCE = "aion.workflow:sequence"
AION_WORKFLOW_OP_TRIGGER = "aion.workflow:trigger"
AION_WORKFLOW_OP_EXTRACT = "aion.workflow:extract"
AION_WORKFLOW_OP_CLASSIFY = "aion.workflow:classify"
AION_WORKFLOW_OP_ACTION = "aion.workflow:action"
AION_WORKFLOW_OP_APPROVAL = "aion.workflow:approval"
AION_WORKFLOW_OP_WAIT = "aion.workflow:wait"
AION_WORKFLOW_OP_ROUTE = "aion.workflow:route"

SAFE_WORKFLOW_OPS = {
    AION_WORKFLOW_OP_SEQUENCE,
    AION_WORKFLOW_OP_TRIGGER,
    AION_WORKFLOW_OP_EXTRACT,
    AION_WORKFLOW_OP_CLASSIFY,
    AION_WORKFLOW_OP_ACTION,
    AION_WORKFLOW_OP_APPROVAL,
    AION_WORKFLOW_OP_WAIT,
    AION_WORKFLOW_OP_ROUTE,
}

RAW_GLYPH_TOKENS = {"⊕", "↔", "∇", "μ", "π", "⟲", "⊗", "⊖", "★"}


@dataclass(slots=True)
class WorkflowPolicy:
    dry_run_first: bool = True
    approval_before_external_write: bool = True
    raw_glyph_execution: bool = False
    raw_glyphs_are_ui_decoration_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowCanvasPosition:
    node_id: str
    x: float = 0
    y: float = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowCanvasLayout:
    schema_version: str = WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION
    coordinate_space: Literal["absolute_canvas_px"] = "absolute_canvas_px"
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowGlyphStep:
    op: str
    node_id: str
    ref: str
    title: str
    node_type: str
    status: str
    meta: str = ""
    position: dict[str, float] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assert_safe_workflow_glyph(compiled_glyph: dict[str, Any]) -> None:
    if not isinstance(compiled_glyph, dict):
        raise ValueError("compiled_glyph must be an object")

    if compiled_glyph.get("schema_version") != WORKFLOW_GLYPH_SCHEMA_VERSION:
        raise ValueError("compiled_glyph schema_version mismatch")

    if compiled_glyph.get("namespace") != WORKFLOW_NAMESPACE:
        raise ValueError("compiled_glyph namespace mismatch")

    root_op = compiled_glyph.get("op")
    if root_op != AION_WORKFLOW_OP_SEQUENCE:
        raise ValueError(f"compiled_glyph root op must be {AION_WORKFLOW_OP_SEQUENCE}")

    policy = compiled_glyph.get("policy") or {}
    if policy.get("raw_glyph_execution") is not False:
        raise ValueError("raw_glyph_execution must be false")

    if policy.get("raw_glyphs_are_ui_decoration_only") is not True:
        raise ValueError("raw_glyphs_are_ui_decoration_only must be true")

    for step in compiled_glyph.get("steps") or []:
        op = step.get("op")
        if op not in SAFE_WORKFLOW_OPS:
            raise ValueError(f"unsafe workflow step op: {op}")

        if op in RAW_GLYPH_TOKENS:
            raise ValueError(f"raw glyph op is not allowed in workflow steps: {op}")
