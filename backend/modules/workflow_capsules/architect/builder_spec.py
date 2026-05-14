from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "aion.workflow_builder_spec.v1"


@dataclass(slots=True)
class MissingConnectorWarning:
    connector: str
    reason: str
    step_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClarificationQuestion:
    question_id: str
    question: str
    required: bool = True
    field: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowStepSpec:
    step_id: str
    node_type: str
    label: str
    config: Dict[str, Any] = field(default_factory=dict)
    risk_tier: str = "low"
    requires_approval: bool = False
    connector: Optional[str] = None
    missing_connector: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowEdgeSpec:
    source: str
    target: str
    condition: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowBuilderSpec:
    workflow_name: str
    goal: str
    steps: List[WorkflowStepSpec] = field(default_factory=list)
    edges: List[WorkflowEdgeSpec] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    requires_clarification: bool = False
    clarification_questions: List[ClarificationQuestion] = field(default_factory=list)
    connectors_required: List[str] = field(default_factory=list)
    missing_connectors: List[MissingConnectorWarning] = field(default_factory=list)
    must_not_do: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "workflow_name": self.workflow_name,
            "goal": self.goal,
            "requires_clarification": self.requires_clarification,
            "clarification_questions": [q.to_dict() for q in self.clarification_questions],
            "connectors_required": list(self.connectors_required),
            "missing_connectors": [m.to_dict() for m in self.missing_connectors],
            "must_not_do": list(self.must_not_do),
            "steps": [s.to_dict() for s in self.steps],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowBuilderSpec":
        steps = [
            WorkflowStepSpec(
                step_id=str(s.get("step_id") or ""),
                node_type=str(s.get("node_type") or ""),
                label=str(s.get("label") or ""),
                config=dict(s.get("config") or {}),
                risk_tier=str(s.get("risk_tier") or "low"),
                requires_approval=bool(s.get("requires_approval") is True),
                connector=s.get("connector"),
                missing_connector=bool(s.get("missing_connector") is True),
                notes=str(s.get("notes") or ""),
            )
            for s in list(data.get("steps") or [])
            if isinstance(s, dict)
        ]

        edges = []
        for e in list(data.get("edges") or []):
            if isinstance(e, list) and len(e) >= 2:
                edges.append(WorkflowEdgeSpec(source=str(e[0]), target=str(e[1])))
            elif isinstance(e, dict):
                edges.append(
                    WorkflowEdgeSpec(
                        source=str(e.get("source") or ""),
                        target=str(e.get("target") or ""),
                        condition=e.get("condition") if isinstance(e.get("condition"), dict) else None,
                    )
                )

        missing = [
            MissingConnectorWarning(
                connector=str(m.get("connector") or ""),
                reason=str(m.get("reason") or ""),
                step_id=m.get("step_id"),
            )
            for m in list(data.get("missing_connectors") or [])
            if isinstance(m, dict)
        ]

        questions = [
            ClarificationQuestion(
                question_id=str(q.get("question_id") or q.get("id") or ""),
                question=str(q.get("question") or ""),
                required=bool(q.get("required", True)),
                field=q.get("field"),
            )
            for q in list(data.get("clarification_questions") or [])
            if isinstance(q, dict)
        ]

        return cls(
            schema_version=str(data.get("schema_version") or SCHEMA_VERSION),
            workflow_name=str(data.get("workflow_name") or ""),
            goal=str(data.get("goal") or ""),
            requires_clarification=bool(data.get("requires_clarification") is True),
            clarification_questions=questions,
            connectors_required=[str(x) for x in list(data.get("connectors_required") or [])],
            missing_connectors=missing,
            must_not_do=[str(x) for x in list(data.get("must_not_do") or [])],
            steps=steps,
            edges=edges,
        )
