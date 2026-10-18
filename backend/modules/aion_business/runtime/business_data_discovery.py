from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA = "tessaris.business-data-manifest.v1"
SCAN_SCHEMA = "tessaris.business-data-scan.v1"

DEFAULT_SOURCE_ROOTS = ("backend", "desktop", "frontend", "scripts")
DEFAULT_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        "_next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "tests",
        "test",
        "fixtures",
    }
)


@dataclass(frozen=True)
class StoragePattern:
    operation: str
    languages: frozenset[str]
    expression: re.Pattern[str]


@dataclass(frozen=True)
class StorageFinding:
    finding_id: str
    path: str
    line: int
    language: str
    operation: str


PATTERNS = (
    StoragePattern(
        "python.file.open_write",
        frozenset({"python"}),
        re.compile(
            r"\bopen\s*\([^\n]*?(?:,\s*['\"][rubtf]*[wax+][rubtf]*['\"]|mode\s*=\s*['\"][rubtf]*[wax+])"
        ),
    ),
    StoragePattern("python.path.write_text", frozenset({"python"}), re.compile(r"\.write_text\s*\(")),
    StoragePattern("python.path.write_bytes", frozenset({"python"}), re.compile(r"\.write_bytes\s*\(")),
    StoragePattern("python.path.mkdir", frozenset({"python"}), re.compile(r"\.mkdir\s*\(")),
    StoragePattern("python.json.dump", frozenset({"python"}), re.compile(r"\bjson\.dump\s*\(")),
    StoragePattern("python.sqlite.connect", frozenset({"python"}), re.compile(r"\bsqlite3\.connect\s*\(")),
    StoragePattern("python.shutil.copy", frozenset({"python"}), re.compile(r"\bshutil\.(?:copy|copy2|copyfile|copytree)\s*\(")),
    StoragePattern("python.tempfile", frozenset({"python"}), re.compile(r"\btempfile\.(?:NamedTemporaryFile|TemporaryDirectory|mkdtemp|mkstemp)\s*\(")),
    StoragePattern("web.local_storage", frozenset({"javascript", "typescript"}), re.compile(r"\blocalStorage(?:\?\.|\.)setItem(?:\?\.)?\s*\(")),
    StoragePattern("web.session_storage", frozenset({"javascript", "typescript"}), re.compile(r"\bsessionStorage(?:\?\.|\.)setItem(?:\?\.)?\s*\(")),
    StoragePattern("web.indexed_db", frozenset({"javascript", "typescript"}), re.compile(r"\bindexedDB\.open\s*\(")),
    StoragePattern("node.fs.write", frozenset({"javascript", "typescript"}), re.compile(r"\b(?:fs\.)?(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream)\s*\(")),
    StoragePattern("node.fs.mkdir", frozenset({"javascript", "typescript"}), re.compile(r"\b(?:fs\.)?(?:mkdir|mkdirSync)\s*\(")),
    StoragePattern("node.sqlite", frozenset({"javascript", "typescript"}), re.compile(r"\b(?:sqlite3|betterSqlite3|Database)\s*\(")),
)

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

REQUIRED_TOUCHPOINT_FIELDS = frozenset(
    {
        "id",
        "feature",
        "business_purpose",
        "business_owner",
        "source_globs",
        "operations",
        "classification",
        "canonical_record",
        "physical_storage",
        "external_destinations",
        "lifecycle",
        "backup_export",
        "migration_decision",
        "verification",
    }
)
APPROVED_RELEASE_GATE = "approved"
ALLOWED_RELEASE_GATES = frozenset({APPROVED_RELEASE_GATE, "blocking", "unreviewed"})


class ManifestError(ValueError):
    pass


def _finding_id(relative_path: str, line: int, operation: str) -> str:
    material = f"{relative_path}:{line}:{operation}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:20]


def _iter_source_files(
    repository_root: Path,
    source_roots: Iterable[str],
    excluded_parts: frozenset[str],
) -> Iterable[Path]:
    for source_root in source_roots:
        root = repository_root / source_root
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in LANGUAGES:
                continue
            relative = candidate.relative_to(repository_root)
            if any(part in excluded_parts or part.endswith(".app") for part in relative.parts):
                continue
            yield candidate


def scan_repository(
    repository_root: str | Path,
    *,
    source_roots: Iterable[str] = DEFAULT_SOURCE_ROOTS,
    excluded_parts: frozenset[str] = DEFAULT_EXCLUDED_PARTS,
) -> dict[str, Any]:
    """Find likely persistence operations without collecting source text or data values."""

    root = Path(repository_root).resolve()
    findings: list[StorageFinding] = []
    scanned_files = 0

    for source_file in sorted(_iter_source_files(root, source_roots, excluded_parts)):
        scanned_files += 1
        language = LANGUAGES[source_file.suffix.lower()]
        relative = source_file.relative_to(root).as_posix()
        try:
            lines = source_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, source_line in enumerate(lines, start=1):
            if source_line.lstrip().startswith(("#", "//", "*")):
                continue
            for pattern in PATTERNS:
                if language in pattern.languages and pattern.expression.search(source_line):
                    findings.append(
                        StorageFinding(
                            finding_id=_finding_id(relative, line_number, pattern.operation),
                            path=relative,
                            line=line_number,
                            language=language,
                            operation=pattern.operation,
                        )
                    )

    ordered = sorted(findings, key=lambda item: (item.path, item.line, item.operation))
    return {
        "schema_version": SCAN_SCHEMA,
        "privacy": "source_locations_only_no_business_values",
        "repository_root_name": root.name,
        "scanned_files": scanned_files,
        "finding_count": len(ordered),
        "findings": [asdict(item) for item in ordered],
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest_unreadable:{exc}") from exc
    validate_manifest(payload)
    return payload


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ManifestError("manifest_schema_invalid")
    sessions = manifest.get("required_discovery_sessions")
    if not isinstance(sessions, list) or not sessions:
        raise ManifestError("required_discovery_sessions_missing")
    session_ids: set[str] = set()
    for session in sessions:
        if not isinstance(session, dict) or not session.get("id") or not session.get("name"):
            raise ManifestError("discovery_session_invalid")
        if session["id"] in session_ids:
            raise ManifestError(f"discovery_session_duplicate:{session['id']}")
        session_ids.add(session["id"])

    touchpoints = manifest.get("touchpoints")
    if not isinstance(touchpoints, list):
        raise ManifestError("touchpoints_invalid")
    touchpoint_ids: set[str] = set()
    for touchpoint in touchpoints:
        if not isinstance(touchpoint, dict):
            raise ManifestError("touchpoint_invalid")
        missing = sorted(REQUIRED_TOUCHPOINT_FIELDS - touchpoint.keys())
        if missing:
            raise ManifestError(f"touchpoint_fields_missing:{','.join(missing)}")
        if touchpoint["id"] in touchpoint_ids:
            raise ManifestError(f"touchpoint_duplicate:{touchpoint['id']}")
        touchpoint_ids.add(touchpoint["id"])
        if not isinstance(touchpoint["source_globs"], list) or not touchpoint["source_globs"]:
            raise ManifestError(f"touchpoint_source_globs_invalid:{touchpoint['id']}")
        if not isinstance(touchpoint["operations"], list) or not touchpoint["operations"]:
            raise ManifestError(f"touchpoint_operations_invalid:{touchpoint['id']}")
        release_gate = touchpoint.get("release_gate", "unreviewed")
        if release_gate not in ALLOWED_RELEASE_GATES:
            raise ManifestError(f"touchpoint_release_gate_invalid:{touchpoint['id']}")


def _matching_touchpoint(finding: dict[str, Any], touchpoints: list[dict[str, Any]]) -> str | None:
    for touchpoint in touchpoints:
        if finding["operation"] not in touchpoint["operations"] and "*" not in touchpoint["operations"]:
            continue
        if any(fnmatch.fnmatch(finding["path"], pattern) for pattern in touchpoint["source_globs"]):
            return str(touchpoint["id"])
    return None


def reconcile_scan(scan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    if scan.get("schema_version") != SCAN_SCHEMA:
        raise ValueError("scan_schema_invalid")

    declared: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    for finding in scan.get("findings", []):
        touchpoint_id = _matching_touchpoint(finding, manifest["touchpoints"])
        if touchpoint_id:
            declared.append({**finding, "touchpoint_id": touchpoint_id})
        else:
            unknown.append(finding)

    incomplete_sessions = [
        session["id"]
        for session in manifest["required_discovery_sessions"]
        if session.get("status") != "complete"
    ]
    blocking_touchpoint_ids = sorted(
        str(touchpoint["id"])
        for touchpoint in manifest["touchpoints"]
        if touchpoint.get("release_gate", "unreviewed") != APPROVED_RELEASE_GATE
    )
    blocking_ids = set(blocking_touchpoint_ids)
    blocking_declared = [
        finding for finding in declared if finding["touchpoint_id"] in blocking_ids
    ]
    return {
        "schema_version": "tessaris.business-data-reconciliation.v1",
        "manifest_schema_version": MANIFEST_SCHEMA,
        "finding_count": len(declared) + len(unknown),
        "declared_count": len(declared),
        "declared_release_approved_count": len(declared) - len(blocking_declared),
        "declared_release_blocking_count": len(blocking_declared),
        "unknown_count": len(unknown),
        "blocking_touchpoint_count": len(blocking_touchpoint_ids),
        "blocking_touchpoint_ids": blocking_touchpoint_ids,
        "incomplete_discovery_session_count": len(incomplete_sessions),
        "incomplete_discovery_sessions": incomplete_sessions,
        "vault_boundary_ready": (
            not unknown and not incomplete_sessions and not blocking_touchpoint_ids
        ),
        "declared_findings": declared,
        "unknown_findings": unknown,
    }
