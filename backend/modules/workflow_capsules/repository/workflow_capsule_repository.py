from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union
import json
import logging
import re

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)

log = logging.getLogger(__name__)

SAFE_KEY_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _safe_filename(value: str, fallback: str = "workflow_capsule") -> str:
    raw = str(value or fallback).strip() or fallback
    raw = SAFE_KEY_RE.sub("_", raw)
    raw = raw.replace(":", "_")
    return raw.strip("._-") or fallback


class WorkflowCapsuleRepository:
    """
    Filesystem-backed repository for capsule-native workflow glyphs.

    Role:
      canonical_key -> capsule path -> verified WorkflowCapsule

    Important:
      The repository is an index/loader.
      It is NOT the source of semantic meaning.
      The capsule file remains the semantic + executable body.
    """

    def __init__(
        self,
        root: Union[str, Path] = "data/workflow_capsules",
        *,
        core_dir: str = "core",
        workspace_dir: str = "workspace",
    ) -> None:
        self.root = Path(root)
        self.core_dir = core_dir
        self.workspace_dir = workspace_dir

    # ---------------------------------------------------------------------
    # Paths
    # ---------------------------------------------------------------------
    @property
    def core_root(self) -> Path:
        return self.root / self.core_dir

    @property
    def workspace_root(self) -> Path:
        return self.root / self.workspace_dir

    def capsule_filename(self, canonical_key: str) -> str:
        return f"{_safe_filename(canonical_key)}.workflow.wiki.phn"

    def capsule_path(
        self,
        canonical_key: str,
        *,
        scope: str = "core",
        workspace_id: Optional[str] = None,
    ) -> Path:
        if scope == "core":
            return self.core_root / self.capsule_filename(canonical_key)

        safe_workspace = _safe_filename(workspace_id or "default_workspace")
        return self.workspace_root / safe_workspace / self.capsule_filename(canonical_key)

    # ---------------------------------------------------------------------
    # Save / Load
    # ---------------------------------------------------------------------
    def save(
        self,
        capsule: WorkflowCapsule,
        *,
        scope: str = "core",
        workspace_id: Optional[str] = None,
        overwrite: bool = True,
    ) -> Dict[str, object]:
        """
        Save a capsule into the repository.

        Core capsules should generally be treated as built-ins.
        Workspace capsules can be user/workspace-editable.
        """

        path = self.capsule_path(
            capsule.canonical_key,
            scope=scope,
            workspace_id=workspace_id,
        )

        if path.exists() and not overwrite:
            return {
                "ok": False,
                "reason": "capsule_already_exists",
                "canonical_key": capsule.canonical_key,
                "path": str(path),
            }

        capsule.finalize()
        capsule.save(path)

        return {
            "ok": True,
            "canonical_key": capsule.canonical_key,
            "display_name": capsule.display_name,
            "scope": scope,
            "workspace_id": workspace_id,
            "path": str(path),
            "checksum": capsule.meta.get("checksum"),
        }

    def load_path(
        self,
        path: Union[str, Path],
        *,
        verify_checksum: bool = True,
    ) -> WorkflowCapsule:
        capsule = WorkflowCapsule.load(path)

        if verify_checksum:
            expected = capsule.meta.get("checksum")
            actual = capsule.checksum()

            if expected and expected != actual:
                raise ValueError(
                    f"Workflow capsule checksum mismatch: path={path} "
                    f"expected={expected} actual={actual}"
                )

        return capsule

    def load(
        self,
        canonical_key: str,
        *,
        workspace_id: Optional[str] = None,
        prefer_workspace: bool = True,
        verify_checksum: bool = True,
    ) -> Optional[WorkflowCapsule]:
        """
        Resolve a canonical key into a WorkflowCapsule.

        Resolution strategy:
          1. Try deterministic canonical filename path.
          2. Fallback: scan capsule files and match the internal canonical_key.

        This is important because existing capsules may have human-friendly filenames
        like gmail_enquiry_reply.workflow.wiki.phn rather than filenames generated
        from canonical_key.
        """

        candidates: List[Path] = []

        workspace_path = self.capsule_path(
            canonical_key,
            scope="workspace",
            workspace_id=workspace_id,
        )
        core_path = self.capsule_path(canonical_key, scope="core")

        if prefer_workspace and workspace_id:
            candidates.append(workspace_path)

        candidates.append(core_path)

        if not prefer_workspace and workspace_id:
            candidates.append(workspace_path)

        # Fast path: deterministic filename resolution.
        for path in candidates:
            if path.exists():
                capsule = self.load_path(path, verify_checksum=verify_checksum)
                if capsule.canonical_key == canonical_key:
                    return capsule

        # Compatibility path: scan all capsule files and match internal canonical_key.
        scan_paths = self.iter_capsule_paths(
            include_core=True,
            include_workspace=bool(workspace_id),
            workspace_id=workspace_id,
        )

        # Workspace-first ordering when requested.
        if prefer_workspace and workspace_id:
            scan_paths = sorted(
                scan_paths,
                key=lambda x: 0 if f"/{self.workspace_dir}/" in str(x) else 1,
            )

        for path in scan_paths:
            try:
                capsule = self.load_path(path, verify_checksum=verify_checksum)
            except Exception as exc:
                log.warning(
                    "[WorkflowCapsuleRepository] skipped unreadable capsule path=%s error=%s",
                    path,
                    exc,
                )
                continue

            if capsule.canonical_key == canonical_key:
                return capsule

        return None

    def require(
        self,
        canonical_key: str,
        *,
        workspace_id: Optional[str] = None,
        prefer_workspace: bool = True,
        verify_checksum: bool = True,
    ) -> WorkflowCapsule:
        capsule = self.load(
            canonical_key,
            workspace_id=workspace_id,
            prefer_workspace=prefer_workspace,
            verify_checksum=verify_checksum,
        )

        if capsule is None:
            raise FileNotFoundError(f"Workflow capsule not found: {canonical_key}")

        return capsule

    # ---------------------------------------------------------------------
    # Index / Search
    # ---------------------------------------------------------------------
    def iter_capsule_paths(
        self,
        *,
        include_core: bool = True,
        include_workspace: bool = True,
        workspace_id: Optional[str] = None,
    ) -> List[Path]:
        paths: List[Path] = []

        if include_core and self.core_root.exists():
            paths.extend(sorted(self.core_root.glob("*.workflow.wiki.phn")))

        if include_workspace:
            if workspace_id:
                safe_workspace = _safe_filename(workspace_id)
                ws_root = self.workspace_root / safe_workspace
                if ws_root.exists():
                    paths.extend(sorted(ws_root.glob("*.workflow.wiki.phn")))
            elif self.workspace_root.exists():
                paths.extend(sorted(self.workspace_root.glob("*/*.workflow.wiki.phn")))

        return paths

    def list_capsules(
        self,
        *,
        include_core: bool = True,
        include_workspace: bool = True,
        workspace_id: Optional[str] = None,
        verify_checksum: bool = True,
    ) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []

        for path in self.iter_capsule_paths(
            include_core=include_core,
            include_workspace=include_workspace,
            workspace_id=workspace_id,
        ):
            try:
                capsule = self.load_path(path, verify_checksum=verify_checksum)
                rows.append(
                    {
                        "ok": True,
                        "canonical_key": capsule.canonical_key,
                        "display_name": capsule.display_name,
                        "meaning": capsule.meaning,
                        "tags": list(capsule.tags or []),
                        "display_glyph": capsule.display_glyph,
                        "path": str(path),
                        "checksum": capsule.meta.get("checksum"),
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "ok": False,
                        "path": str(path),
                        "error": str(exc),
                    }
                )

        return rows

    def find_by_tags(
        self,
        tags: List[str],
        *,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        wanted = {str(t).strip().lower() for t in tags if str(t).strip()}
        if not wanted:
            return []

        matches: List[Dict[str, object]] = []

        for row in self.list_capsules(workspace_id=workspace_id):
            if not row.get("ok"):
                continue

            row_tags = {str(t).strip().lower() for t in row.get("tags", [])}
            overlap = sorted(wanted.intersection(row_tags))

            if overlap:
                row = dict(row)
                row["matched_tags"] = overlap
                row["score"] = len(overlap)
                matches.append(row)

        return sorted(matches, key=lambda r: int(r.get("score", 0)), reverse=True)

    # ---------------------------------------------------------------------
    # Registry export
    # ---------------------------------------------------------------------
    def build_index(
        self,
        *,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, object]]:
        """
        Build a simple canonical_key -> capsule summary index.
        """

        index: Dict[str, Dict[str, object]] = {}

        for row in self.list_capsules(workspace_id=workspace_id):
            if not row.get("ok"):
                continue

            key = str(row["canonical_key"])

            if key in index:
                existing = index[key]
                log.warning(
                    "[WorkflowCapsuleRepository] duplicate canonical_key=%s paths=%s,%s",
                    key,
                    existing.get("path"),
                    row.get("path"),
                )

            index[key] = row

        return index

    def save_index(
        self,
        path: Union[str, Path] = "data/workflow_capsules/workflow_capsule_index.json",
        *,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, object]:
        index = self.build_index(workspace_id=workspace_id)

        out = {
            "schema_version": "aion.workflow_capsule_index.v1",
            "count": len(index),
            "workspace_id": workspace_id,
            "items": index,
        }

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "ok": True,
            "path": str(path),
            "count": len(index),
        }
