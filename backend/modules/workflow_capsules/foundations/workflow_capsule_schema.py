"""
Workflow Capsule Schema - Aion Workflow Glyph Capsules v1
────────────────────────────────────────────────────────
Defines the canonical capsule structure for capsule-native workflow glyphs.

A workflow capsule is the semantic + executable body behind a compressed
workflow glyph handle.

Mental model:
  glyph handle / canonical_key -> workflow capsule -> compiled workflow glyph -> executor

This intentionally mirrors WikiCapsule style while adding:
- canonical workflow identity
- policy / vault requirements
- compiled workflow glyph payload
- executable graph body
- audit / resonance metadata

Important architecture rule:
  The glyph is the compressed handle.
  The workflow capsule is the semantic body.
  The compiled workflow glyph is the executable body.

Important safety rule:
  Workflow execution MAY run under policy.
  Workflow learning / feedback / reinforcement MUST remain CAU-governed.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import json
import logging
import re
import time

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

log = logging.getLogger(__name__)


DEFAULT_SIGNER = "Tessaris-Core"
SCHEMA_VERSION = "aion.workflow_capsule.v1"


@dataclass
class WorkflowCapsulePolicy:
    dry_run_first: bool = True
    approval_before_external_write: bool = True
    external_writes_allowed: bool = False
    allow_autonomous_execution: bool = False
    max_runtime_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_any(cls, value: Any) -> "WorkflowCapsulePolicy":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return cls()

        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in value.items() if k in allowed})


@dataclass
class WorkflowCapsule:
    canonical_key: str
    display_name: str
    meaning: str

    # Optional UI/display handle only. Never the executable identity.
    display_glyph: Optional[str] = None

    # Optional category tags for search and Aion reasoning.
    tags: List[str] = field(default_factory=list)

    # Natural-language allowed use cases / intent boundaries.
    allowed_use_cases: List[str] = field(default_factory=list)

    # Security/runtime config.
    policy: WorkflowCapsulePolicy = field(default_factory=WorkflowCapsulePolicy)
    vault_requirements: List[str] = field(default_factory=list)

    # Executable body.
    workflow_id: Optional[str] = None
    workflow_graph: Dict[str, Any] = field(default_factory=dict)
    compiled_glyph: Dict[str, Any] = field(default_factory=dict)

    # Trace/resonance/audit.
    audit_rules: Dict[str, Any] = field(default_factory=dict)
    resonance: Dict[str, Any] = field(default_factory=dict)
    entangled_links: Dict[str, List[str]] = field(default_factory=dict)

    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        if isinstance(self.policy, WorkflowCapsulePolicy):
            data["policy"] = self.policy.to_dict()

        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", SCHEMA_VERSION)
        meta.setdefault("version", "1.0")
        meta.setdefault("signed_by", DEFAULT_SIGNER)
        meta.setdefault("timestamp", time.time())
        meta.setdefault("sqi_score", 0.0)
        meta.setdefault("ρ", 0.0)
        meta.setdefault("Ī", 0.0)

        return data

    def stable_dict(self) -> Dict[str, Any]:
        """
        Stable dict used for checksum.

        Excludes mutable/derived fields that must not invalidate the semantic body:
        - meta.checksum
        - meta.source_path
        """
        data = self.to_dict()
        meta = dict(data.get("meta") or {})
        meta.pop("checksum", None)
        meta.pop("source_path", None)
        data["meta"] = meta
        return data

    def checksum(self) -> str:
        return hashlib.sha3_256(
            json.dumps(
                self.stable_dict(),
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()

    def finalize(self) -> "WorkflowCapsule":
        self.meta.setdefault("schema_version", SCHEMA_VERSION)
        self.meta.setdefault("version", "1.0")
        self.meta.setdefault("signed_by", DEFAULT_SIGNER)
        self.meta.setdefault("timestamp", time.time())

        if isinstance(self.resonance, dict):
            self.meta.setdefault("sqi_score", self.resonance.get("sqi_score", 0.0))
            self.meta.setdefault("ρ", self.resonance.get("ρ", 0.0))
            self.meta.setdefault("Ī", self.resonance.get("Ī", 0.0))
        else:
            self.meta.setdefault("sqi_score", 0.0)
            self.meta.setdefault("ρ", 0.0)
            self.meta.setdefault("Ī", 0.0)

        self.meta["checksum"] = self.checksum()
        return self

    def to_json(self, path: Union[str, Path, None] = None, indent: int = 2) -> str:
        self.finalize()
        js = json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

        if path:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(js, encoding="utf-8")

        return js

    def to_phn_text(self) -> str:
        """
        ASCII-safe .workflow.wiki.phn representation.

        Uses a JSON body inside a simple wrapper so the capsule can round-trip
        reliably while still remaining capsule-native.
        """
        self.finalize()
        body = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        return "^workflow_capsule {\n" + body + "\n}\n"

    def save(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".json":
            self.to_json(path)
        else:
            path.write_text(self.to_phn_text(), encoding="utf-8")

        return path

    @classmethod
    def from_text(cls, text: str) -> "WorkflowCapsule":
        """
        Parse .workflow.wiki.phn, JSON, YAML, or fenced variants.

        Important:
        The .workflow.wiki.phn wrapper looks like:

            ^workflow_capsule {
            {
              "canonical_key": "...",
              ...
            }
            }

        Do NOT strip all lines equal to "}".
        That corrupts the inner JSON object.
        """
        cleaned = _extract_capsule_payload(text)

        data: Any = None

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as json_error:
            if yaml is not None:
                try:
                    data = yaml.safe_load(cleaned)
                except Exception as yaml_error:
                    log.warning(
                        "[WorkflowCapsule] YAML parse failed after JSON parse failed. "
                        "json_error=%s yaml_error=%s",
                        json_error,
                        yaml_error,
                    )

        if not isinstance(data, dict):
            data = _plain_text_fallback(cleaned)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowCapsule":
        """
        Normalize dict payloads into a WorkflowCapsule.

        Kept permissive because older files/callers may use earlier aliases:
        - title -> display_name
        - description -> meaning
        - key -> canonical_key
        """
        if not isinstance(data, dict):
            raise TypeError("WorkflowCapsule.from_dict expected dict")

        data = dict(data)

        if "title" in data and "display_name" not in data:
            data["display_name"] = data.pop("title")

        if "description" in data and "meaning" not in data:
            data["meaning"] = data.pop("description")

        if "key" in data and "canonical_key" not in data:
            data["canonical_key"] = data.pop("key")

        data.setdefault(
            "canonical_key",
            _slug_to_workflow_key(str(data.get("display_name") or "workflow")),
        )
        data.setdefault("display_name", data["canonical_key"])
        data.setdefault("meaning", "")
        data.setdefault("display_glyph", None)
        data.setdefault("tags", [])
        data.setdefault("allowed_use_cases", [])
        data.setdefault("policy", {})
        data.setdefault("vault_requirements", [])
        data.setdefault("workflow_id", None)
        data.setdefault("workflow_graph", {})
        data.setdefault("compiled_glyph", {})
        data.setdefault("audit_rules", {})
        data.setdefault("resonance", {})
        data.setdefault("entangled_links", {})
        data.setdefault("meta", {})

        normalized = {
            "canonical_key": str(data["canonical_key"]),
            "display_name": str(data["display_name"]),
            "meaning": str(data["meaning"]),
            "display_glyph": data.get("display_glyph"),
            "tags": _list_of_str(data.get("tags")),
            "allowed_use_cases": _list_of_str(data.get("allowed_use_cases")),
            "policy": WorkflowCapsulePolicy.from_any(data.get("policy")),
            "vault_requirements": _list_of_str(data.get("vault_requirements")),
            "workflow_id": data.get("workflow_id"),
            "workflow_graph": _dict_or_empty(data.get("workflow_graph")),
            "compiled_glyph": _dict_or_empty(data.get("compiled_glyph")),
            "audit_rules": _dict_or_empty(data.get("audit_rules")),
            "resonance": _dict_or_empty(data.get("resonance")),
            "entangled_links": _dict_of_list_str(data.get("entangled_links")),
            "meta": _dict_or_empty(data.get("meta")),
        }

        meta = normalized["meta"]
        meta.setdefault("schema_version", SCHEMA_VERSION)
        meta.setdefault("version", "1.0")
        meta.setdefault("signed_by", DEFAULT_SIGNER)
        meta.setdefault("timestamp", time.time())
        meta.setdefault("sqi_score", 0.0)
        meta.setdefault("ρ", 0.0)
        meta.setdefault("Ī", 0.0)

        capsule = cls(**normalized)

        # Preserve existing checksum if present. If absent, finalize it.
        capsule.meta.setdefault("checksum", capsule.checksum())
        return capsule

    @classmethod
    def load(cls, path: Union[str, Path]) -> "WorkflowCapsule":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow capsule file not found: {path}")

        capsule = cls.from_text(path.read_text(encoding="utf-8"))
        capsule.meta.setdefault("source_path", str(path))

        expected = capsule.meta.get("checksum")
        actual = capsule.checksum()

        if expected and expected != actual:
            log.warning(
                "[WorkflowCapsule] checksum mismatch for %s: expected=%s actual=%s",
                path,
                expected,
                actual,
            )

        capsule.meta.setdefault("checksum", actual)
        return capsule


def _extract_capsule_payload(text: str) -> str:
    """
    Extract the structured payload from:
    - plain JSON
    - plain YAML
    - fenced JSON/YAML
    - wrapped .workflow.wiki.phn text

    The key point is balanced-object extraction.
    We only remove the outer ^workflow_capsule line, not arbitrary braces.
    """
    raw = (text or "").strip()

    raw = _strip_code_fences(raw)

    lines: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()

        if stripped.startswith("^workflow_capsule"):
            continue

        if stripped == "---":
            continue

        lines.append(line)

    raw = "\n".join(lines).strip()

    # Most current files are wrapped JSON. Extract the first balanced object.
    json_obj = _extract_first_balanced_json_object(raw)
    if json_obj:
        return json_obj

    return raw


def _strip_code_fences(text: str) -> str:
    raw = text.strip()

    if "```" not in raw:
        return raw

    cleaned: List[str] = []
    in_fence = False

    for line in raw.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _extract_first_balanced_json_object(text: str) -> Optional[str]:
    """
    Return the first balanced JSON-like object in text.

    Handles nested braces and quoted strings.
    """
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\" and in_string:
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _plain_text_fallback(cleaned: str) -> Dict[str, Any]:
    title_match = re.search(r"^#\s*(.+)$", cleaned, re.MULTILINE)
    display_name = (
        title_match.group(1).strip()
        if title_match
        else "Untitled Workflow Capsule"
    )
    key = _slug_to_workflow_key(display_name)

    return {
        "canonical_key": key,
        "display_name": display_name,
        "meaning": cleaned or "Workflow capsule with no structured body.",
        "policy": {},
        "workflow_graph": {},
        "compiled_glyph": {},
        "meta": {},
    }


def _slug_to_workflow_key(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", ".", value.strip().lower()).strip(".")
    slug = slug or "workflow"
    return f"workflow:{slug}.v1"


def _dict_or_empty(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_str(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value]


def _dict_of_list_str(value: Any) -> Dict[str, List[str]]:
    if not isinstance(value, dict):
        return {}

    out: Dict[str, List[str]] = {}
    for k, v in value.items():
        out[str(k)] = _list_of_str(v)
    return out


def make_workflow_capsule(
    canonical_key: str,
    display_name: str,
    meaning: str,
    *,
    display_glyph: Optional[str] = None,
    tags: Optional[List[str]] = None,
    allowed_use_cases: Optional[List[str]] = None,
    policy: Optional[Union[WorkflowCapsulePolicy, Dict[str, Any]]] = None,
    vault_requirements: Optional[List[str]] = None,
    workflow_id: Optional[str] = None,
    workflow_graph: Optional[Dict[str, Any]] = None,
    compiled_glyph: Optional[Dict[str, Any]] = None,
    audit_rules: Optional[Dict[str, Any]] = None,
    resonance: Optional[Dict[str, Any]] = None,
    entangled_links: Optional[Dict[str, List[str]]] = None,
) -> WorkflowCapsule:
    capsule = WorkflowCapsule(
        canonical_key=canonical_key,
        display_name=display_name,
        meaning=meaning,
        display_glyph=display_glyph,
        tags=tags or [],
        allowed_use_cases=allowed_use_cases or [],
        policy=WorkflowCapsulePolicy.from_any(policy or {}),
        vault_requirements=vault_requirements or [],
        workflow_id=workflow_id,
        workflow_graph=workflow_graph or {},
        compiled_glyph=compiled_glyph or {},
        audit_rules=audit_rules or {},
        resonance=resonance or {},
        entangled_links=entangled_links or {},
        meta={
            "schema_version": SCHEMA_VERSION,
            "signed_by": DEFAULT_SIGNER,
            "timestamp": time.time(),
            "sqi_score": (resonance or {}).get("sqi_score", 0.0),
            "ρ": (resonance or {}).get("ρ", 0.0),
            "Ī": (resonance or {}).get("Ī", 0.0),
            "version": "1.0",
        },
    )

    return capsule.finalize()