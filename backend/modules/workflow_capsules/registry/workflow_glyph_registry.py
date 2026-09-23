from __future__ import annotations

"""
Workflow Glyph Registry - Aion Workflow Capsules v1
──────────────────────────────────────────────────
Registry/index layer for capsule-native workflow glyphs.

Important architecture rule:
  The registry is NOT the source of workflow meaning.
  The WorkflowCapsule is the semantic + executable source of truth.

Mental model:
  intent / canonical_key / display_glyph / alias
      -> WorkflowGlyphRegistry
      -> WorkflowCapsuleRepository
      -> WorkflowCapsule
      -> compiled workflow glyph / executor

Identity rules:
  canonical_key = executable identity
  display_glyph = UI shorthand only
  user_alias = optional workspace/local shortcut
  raw Symatics symbols/operators are reserved and must not be workflow identities
"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import logging
import re
import time

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)

log = logging.getLogger(__name__)


REGISTRY_SCHEMA_VERSION = "aion.workflow_glyph_registry.v1"


# Do not allow workflows to claim core Symatics / Photon / GlyphOS operators.
# These are display/semantic operators, not workflow executable identities.
RESERVED_GLYPH_TOKENS = {
    "^",
    "⊕",
    "↔",
    "⟲",
    "∇",
    "μ",
    "π",
    "φ",
    "Φ",
    "λ",
    "ρ",
    "Ī",
    "ψ",
    "κ",
    "τ",
    "Σ",
    "Δ",
    "Ω",
    "∞",
    "∴",
    "∵",
    "→",
    "←",
    "↦",
    "⧖",
    "◌",
    "⬢",
}


_CANONICAL_RE = re.compile(r"^workflow:[a-zA-Z0-9_.-]+\.v\d+$")


def _now() -> float:
    return time.time()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def is_valid_workflow_key(value: str) -> bool:
    return bool(_CANONICAL_RE.match(_norm(value)))


def is_reserved_glyph(value: Optional[str]) -> bool:
    if not value:
        return False
    return _norm(value) in RESERVED_GLYPH_TOKENS



def _is_workflow_capsule_file(path: Path) -> bool:
    """
    Only real workflow capsules should enter the glyph registry.

    Exclude runtime artifacts:
      - approvals/*
      - runs/*
      - feedback/*
      - registry/index JSON files

    The registry is an index of semantic/executable capsules, not execution logs.
    """
    parts = set(path.parts)

    if {"approvals", "runs", "feedback"} & parts:
        return False

    name = path.name

    if name in {
        "workflow_capsule_index.json",
        "workflow_glyph_registry.json",
    }:
        return False

    if name.endswith(".workflow.wiki.phn"):
        return True

    # Allow future explicit JSON capsule files, but do not ingest arbitrary runtime JSON.
    if name.endswith(".workflow_capsule.json"):
        return True

    return False


@dataclass
class WorkflowGlyphRegistryEntry:
    canonical_key: str
    capsule_path: str

    display_name: str = ""
    display_glyph: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    checksum: Optional[str] = None
    signed_by: Optional[str] = None
    schema_version: str = REGISTRY_SCHEMA_VERSION
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_capsule(
        cls,
        capsule: WorkflowCapsule,
        *,
        capsule_path: str,
        aliases: Optional[List[str]] = None,
    ) -> "WorkflowGlyphRegistryEntry":
        meta = capsule.meta or {}
        return cls(
            canonical_key=capsule.canonical_key,
            capsule_path=str(capsule_path),
            display_name=capsule.display_name,
            display_glyph=capsule.display_glyph,
            tags=list(capsule.tags or []),
            aliases=list(aliases or []),
            checksum=meta.get("checksum") or capsule.checksum(),
            signed_by=meta.get("signed_by"),
        )


@dataclass
class WorkflowGlyphMatch:
    canonical_key: str
    reason: str
    score: float
    entry: WorkflowGlyphRegistryEntry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_key": self.canonical_key,
            "reason": self.reason,
            "score": self.score,
            "entry": self.entry.to_dict(),
        }


class WorkflowGlyphRegistry:
    """
    Lightweight resolver over workflow capsules.

    The registry can resolve by:
      - exact canonical_key
      - display_glyph
      - aliases
      - tags
      - display_name / meaning-ish text via repository-backed capsule lookup

    It does not execute workflows and does not mutate learning memory.
    """

    def __init__(
        self,
        *,
        repository: Optional[WorkflowCapsuleRepository] = None,
        registry_path: str | Path = "data/workflow_capsules/workflow_glyph_registry.json",
    ) -> None:
        self.repository = repository or WorkflowCapsuleRepository()
        self.registry_path = Path(registry_path)
        self.entries: Dict[str, WorkflowGlyphRegistryEntry] = {}

    # ------------------------------------------------------------------
    # Build / load / save
    # ------------------------------------------------------------------
    def build_from_repository(self) -> Dict[str, Any]:
        """
        Build registry entries from the repository and direct capsule file scan.

        Important:
        - Repository index may be stale or empty.
        - The capsule files are the source of truth.
        - This method therefore scans data/workflow_capsules directly as fallback.
        """
        discovered: Dict[str, Dict[str, Any]] = {}

        # First: ask repository if it exposes list_capsules().
        try:
            capsules = self.repository.list_capsules()
        except Exception as e:
            log.warning("[WorkflowGlyphRegistry] repository.list_capsules failed: %s", e)
            capsules = []

        for item in capsules or []:
            try:
                capsule = item.get("capsule")
                path = item.get("path") or (capsule.meta or {}).get("source_path")
                if isinstance(capsule, WorkflowCapsule) and path:
                    discovered[capsule.canonical_key] = {
                        "capsule": capsule,
                        "path": str(path),
                    }
            except Exception as e:
                log.warning("[WorkflowGlyphRegistry] skipped repository item: %s", e)

        # Second: direct scan capsule roots. This is the hard fallback.
        #
        # Important:
        # - When a repository is explicitly injected, its root is authoritative.
        # - Do not also scan the default data/workflow_capsules tree, otherwise
        #   isolated tests and workspace-specific registries get polluted by
        #   unrelated local capsules and stale aliases.
        scan_roots = []

        repo_root = getattr(self.repository, "root", None)
        if repo_root:
            scan_roots.append(Path(repo_root))
        else:
            scan_roots.append(Path("data/workflow_capsules"))

        for root in scan_roots:
            if not root.exists():
                continue

            patterns = [
                "**/*.workflow.wiki.phn",
                "**/*.workflow.phn",
                "**/*.json",
            ]

            for pattern in patterns:
                for path in root.glob(pattern):
                    if path.name in {
                        "workflow_capsule_index.json",
                        "workflow_glyph_registry.json",
                    }:
                        continue

                    try:
                        capsule = WorkflowCapsule.load(path)
                    except Exception as e:
                        log.warning("[WorkflowGlyphRegistry] failed loading %s: %s", path, e)
                        continue

                    discovered[capsule.canonical_key] = {
                        "capsule": capsule,
                        "path": str(path),
                    }

        self.entries = {}

        collisions: List[str] = []
        rejected: List[Dict[str, Any]] = []

        seen_display_glyphs: Dict[str, str] = {}
        seen_aliases: Dict[str, str] = {}

        for key, item in sorted(discovered.items(), key=lambda kv: kv[0]):
            capsule = item["capsule"]
            path = item["path"]

            if not isinstance(capsule, WorkflowCapsule):
                continue

            try:
                self._validate_capsule_for_registry(capsule)
            except ValueError as e:
                rejected.append(
                    {
                        "canonical_key": getattr(capsule, "canonical_key", None),
                        "path": str(path),
                        "reason": str(e),
                    }
                )
                continue

            key = capsule.canonical_key
            if key in self.entries:
                collisions.append(key)
                continue

            display_glyph = capsule.display_glyph
            if display_glyph:
                dg = _norm_lower(display_glyph)
                if dg in seen_display_glyphs:
                    rejected.append(
                        {
                            "canonical_key": key,
                            "path": str(path),
                            "reason": f"display_glyph collision: {display_glyph}",
                        }
                    )
                    continue
                seen_display_glyphs[dg] = key

            aliases = self._aliases_from_capsule(capsule)
            alias_collision = None
            for alias in aliases:
                a = _norm_lower(alias)
                if a in seen_aliases:
                    alias_collision = alias
                    break
                seen_aliases[a] = key

            if alias_collision:
                rejected.append(
                    {
                        "canonical_key": key,
                        "path": str(path),
                        "reason": f"alias collision: {alias_collision}",
                    }
                )
                continue

            self.entries[key] = WorkflowGlyphRegistryEntry.from_capsule(
                capsule,
                capsule_path=str(path),
                aliases=aliases,
            )

        return {
            "ok": not collisions and not rejected,
            "count": len(self.entries),
            "collisions": collisions,
            "rejected": rejected,
            "discovered": len(discovered),
        }

    def save(self) -> Dict[str, Any]:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        body = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "updated_at": _now(),
            "count": len(self.entries),
            "entries": {
                key: entry.to_dict()
                for key, entry in sorted(self.entries.items(), key=lambda kv: kv[0])
            },
        }

        tmp = self.registry_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.registry_path)

        return {
            "ok": True,
            "path": str(self.registry_path),
            "count": len(self.entries),
        }

    def load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            self.build_from_repository()
            return self.save()

        body = json.loads(self.registry_path.read_text(encoding="utf-8"))
        raw_entries = body.get("entries") or {}

        self.entries = {}
        for key, value in raw_entries.items():
            if not isinstance(value, dict):
                continue
            self.entries[key] = WorkflowGlyphRegistryEntry(**value)

        return {
            "ok": True,
            "path": str(self.registry_path),
            "count": len(self.entries),
        }

    def rebuild_and_save(self) -> Dict[str, Any]:
        build = self.build_from_repository()
        saved = self.save()
        return {
            "ok": bool(build.get("ok")) and bool(saved.get("ok")),
            "build": build,
            "saved": saved,
        }

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------
    def resolve(self, value: str, *, min_score: float = 0.35) -> Optional[WorkflowCapsule]:
        matches = self.find(value, limit=1, min_score=min_score)
        if not matches:
            return None

        entry = matches[0].entry
        capsule_path = getattr(entry, "capsule_path", None)

        if capsule_path:
            try:
                return self.repository.load_path(capsule_path)
            except Exception as exc:
                log.warning(
                    "[WorkflowGlyphRegistry] failed loading matched capsule_path=%s error=%s; falling back to canonical lookup",
                    capsule_path,
                    exc,
                )

        return self.repository.require(matches[0].canonical_key)

    def require(self, value: str, *, min_score: float = 0.35) -> WorkflowCapsule:
        capsule = self.resolve(value, min_score=min_score)
        if capsule is None:
            raise FileNotFoundError(f"Workflow glyph/capsule not found: {value}")
        return capsule

    def find(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.35,
    ) -> List[WorkflowGlyphMatch]:
        if not self.entries:
            self.load()

        q = _norm(query)
        ql = q.lower()

        if not q:
            return []

        matches: List[WorkflowGlyphMatch] = []

        for entry in self.entries.values():
            score = 0.0
            reason = ""

            if q == entry.canonical_key:
                score = 1.0
                reason = "exact_canonical_key"

            elif ql == _norm_lower(entry.display_glyph):
                score = 0.96
                reason = "display_glyph"

            elif ql in {_norm_lower(a) for a in entry.aliases}:
                score = 0.92
                reason = "alias"

            elif ql in {_norm_lower(t) for t in entry.tags}:
                score = 0.75
                reason = "tag"

            elif ql == _norm_lower(entry.display_name):
                score = 0.72
                reason = "display_name"

            else:
                # Lightweight text score. Repository remains source of meaning.
                text_parts = [
                    entry.canonical_key,
                    entry.display_name,
                    entry.display_glyph or "",
                    " ".join(entry.tags or []),
                    " ".join(entry.aliases or []),
                ]

                # Add capsule meaning if the capsule is cheap to load.
                try:
                    capsule = self.repository.require(entry.canonical_key)
                    text_parts.append(capsule.meaning or "")
                    text_parts.append(" ".join(capsule.allowed_use_cases or []))
                except Exception:
                    pass

                score = self._text_match_score(ql, " ".join(text_parts).lower())
                reason = "semantic_text"

            if score >= min_score:
                matches.append(
                    WorkflowGlyphMatch(
                        canonical_key=entry.canonical_key,
                        reason=reason,
                        score=round(float(score), 4),
                        entry=entry,
                    )
                )

        matches.sort(key=lambda m: (-m.score, m.canonical_key))
        return matches[: max(1, int(limit))]

    def resolve_index(self) -> Dict[str, Any]:
        if not self.entries:
            self.load()

        return {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "count": len(self.entries),
            "entries": {
                key: entry.to_dict()
                for key, entry in sorted(self.entries.items(), key=lambda kv: kv[0])
            },
        }

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _validate_capsule_for_registry(self, capsule: WorkflowCapsule) -> None:
        if not is_valid_workflow_key(capsule.canonical_key):
            raise ValueError(f"invalid canonical_key: {capsule.canonical_key}")

        if is_reserved_glyph(capsule.display_glyph):
            raise ValueError(f"display_glyph uses reserved operator: {capsule.display_glyph}")

        # Preserve source-of-truth checksum check.
        expected = (capsule.meta or {}).get("checksum")
        actual = capsule.checksum()
        if expected and expected != actual:
            raise ValueError(f"checksum mismatch expected={expected} actual={actual}")

        for alias in self._aliases_from_capsule(capsule):
            if is_reserved_glyph(alias):
                raise ValueError(f"alias uses reserved operator: {alias}")
            if alias.startswith("workflow:"):
                raise ValueError(f"alias cannot look like canonical_key: {alias}")

    def _aliases_from_capsule(self, capsule: WorkflowCapsule) -> List[str]:
        aliases: List[str] = []

        audit_rules = capsule.audit_rules if isinstance(capsule.audit_rules, dict) else {}
        resonance = capsule.resonance if isinstance(capsule.resonance, dict) else {}
        meta = capsule.meta if isinstance(capsule.meta, dict) else {}

        for source in (audit_rules, resonance, meta):
            for key in ("aliases", "user_aliases", "intent_aliases"):
                aliases.extend(_as_list(source.get(key)))

        # Convenience aliases from display name and display glyph.
        if capsule.display_name:
            aliases.append(capsule.display_name)

        # Optional user glyph only if explicitly placed in meta/resonance/audit.
        # display_glyph is resolved separately.
        return _dedupe_keep_order(aliases)

    def _text_match_score(self, q: str, text: str) -> float:
        q_tokens = {t for t in re.split(r"[^a-z0-9_]+", q.lower()) if t}
        t_tokens = {t for t in re.split(r"[^a-z0-9_]+", text.lower()) if t}

        if not q_tokens or not t_tokens:
            return 0.0

        overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens))
        phrase = 1.0 if q in text else 0.0

        return min(1.0, (0.65 * overlap) + (0.35 * phrase))


def _dedupe_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        v = str(value or "").strip()
        if not v:
            continue
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def build_workflow_glyph_registry(
    *,
    repository: Optional[WorkflowCapsuleRepository] = None,
    registry_path: str | Path = "data/workflow_capsules/workflow_glyph_registry.json",
) -> WorkflowGlyphRegistry:
    registry = WorkflowGlyphRegistry(repository=repository, registry_path=registry_path)
    registry.build_from_repository()
    return registry
