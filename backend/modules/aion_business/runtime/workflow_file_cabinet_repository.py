from __future__ import annotations

import json
import base64
import csv
import io
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowFileCabinetRepository:
    """
    Workspace-scoped persisted workflow file cabinet.

    This stores the desktop workflow tree under the AION Business runtime root.
    It is intentionally separate from workflow execution definitions.
    """

    @staticmethod
    def _safe_id(value: str) -> str:
        value = str(value or "").strip()
        if not value:
            return "default"
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "default"

    @classmethod
    def cabinet_dir(cls, workspace_id: str) -> Path:
        workspace_id = cls._safe_id(workspace_id)
        AIONBusinessPaths.ensure_base_dirs()
        path = AIONBusinessPaths.ROOT / "workflow_file_cabinets" / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def cabinet_file(cls, workspace_id: str) -> Path:
        return cls.cabinet_dir(workspace_id) / "tree.json"

    @classmethod
    def default_tree(cls, workspace_id: str) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)
        now = _now_iso()
        return {
            "version": 1,
            "workspace_id": workspace_id,
            "root": {
                "id": "root",
                "type": "folder",
                "name": "Workflows",
                "children": [],
            },
            "metadata": {
                "created_at": now,
                "updated_at": now,
                "source": "aion_business_workflow_file_cabinet",
            },
        }

    @classmethod
    def load(cls, workspace_id: str) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)
        path = cls.cabinet_file(workspace_id)

        if not path.exists():
            payload = cls.default_tree(workspace_id)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            return payload

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = cls.default_tree(workspace_id)

        payload.setdefault("version", 1)
        payload.setdefault("workspace_id", workspace_id)
        payload.setdefault("root", {"id": "root", "type": "folder", "name": "Workflows", "children": []})
        payload.setdefault("metadata", {})
        payload["metadata"].setdefault("created_at", _now_iso())
        payload["metadata"].setdefault("updated_at", _now_iso())
        payload["metadata"].setdefault("source", "aion_business_workflow_file_cabinet")
        return payload

    @classmethod
    def save(cls, workspace_id: str, tree: Dict[str, Any]) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)

        if not isinstance(tree, dict):
            raise ValueError("Workflow file cabinet payload must be an object")

        existing_created_at = None
        path = cls.cabinet_file(workspace_id)
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                existing_created_at = (existing.get("metadata") or {}).get("created_at")
            except Exception:
                existing_created_at = None

        payload = dict(tree)
        payload["version"] = int(payload.get("version") or 1)
        payload["workspace_id"] = workspace_id

        root = payload.get("root")

        # Desktop cabinet currently uses the live visible shape:
        # {
        #   schema_version: "aion.workflow_file_cabinet.v1",
        #   business_container: "...",
        #   folders: [...]
        # }
        #
        # Older backend shape uses:
        # {
        #   version: 1,
        #   workspace_id: "...",
        #   root: { id, type, name, children }
        # }
        #
        # Accept both. If root is absent but folders exists, wrap folders into root.children.
        if not isinstance(root, dict):
            folders = payload.get("folders")
            if isinstance(folders, list):
                root = {
                    "id": "root",
                    "type": "folder",
                    "name": "Workflows",
                    "children": folders,
                }
                payload["root"] = root
            else:
                raise ValueError("Workflow file cabinet payload requires root object or folders array")

        root.setdefault("id", "root")
        root.setdefault("type", "folder")
        root.setdefault("name", "Workflows")
        root.setdefault("children", [])

        # Preserve the desktop-native shape too, so both backend and desktop callers can use it.
        if "folders" not in payload and isinstance(root.get("children"), list):
            payload["folders"] = root["children"]
        payload.setdefault("schema_version", "aion.workflow_file_cabinet.v1")
        payload.setdefault("business_container", workspace_id)

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        now = _now_iso()
        metadata["created_at"] = metadata.get("created_at") or existing_created_at or now
        metadata["updated_at"] = now
        metadata["source"] = "aion_business_workflow_file_cabinet"
        payload["metadata"] = metadata

        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    @staticmethod
    def _walk(nodes: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            yield node
            yield from WorkflowFileCabinetRepository._walk(node.get("children") or [])

    @classmethod
    def item(cls, workspace_id: str, item_id: str) -> Dict[str, Any]:
        tree = cls.load(workspace_id)
        nodes = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        for node in cls._walk(nodes):
            if str(node.get("id") or "") == str(item_id or ""):
                return node
        raise KeyError("file_cabinet_item_not_found")

    @staticmethod
    def protection(node: Dict[str, Any]) -> Dict[str, Any]:
        provenance = node.get("provenance") if isinstance(node.get("provenance"), dict) else {}
        explicit = str(node.get("deletion_policy") or "").strip().lower()
        created_by = str(provenance.get("created_by") or node.get("created_by") or "").strip().lower()
        status = str(node.get("status") or "").strip().lower()
        document_type = str(node.get("document_type") or "").strip().lower()
        source = str(node.get("source_of_truth") or "").strip().lower()

        user_removable = explicit in {"user_removable", "removable"} or (
            created_by in {"user", "user_upload", "authorised_user"}
            and status not in {"accepted", "approved", "sealed", "verified", "promoted"}
        )
        protected = not user_removable and (
            explicit in {"protected", "immutable", "append_only"}
            or node.get("type") == "business_container_artifact"
            or source in {"business_container", "boardroom", "evidence_ledger"}
            or "boardroom" in document_type
            or any(token in document_type for token in ("evidence", "receipt", "ledger", "reconciliation"))
            or status in {"accepted", "approved", "sealed", "verified", "promoted"}
        )
        return {
            "protected": bool(protected),
            "deletion_policy": "protected_record" if protected else "user_removable",
            "reason": (
                "Board, evidence or governed business record"
                if protected else "User-owned item; removable with confirmation"
            ),
        }

    @classmethod
    def _artifact_path(cls, workspace_id: str, node: Dict[str, Any]) -> Path:
        raw = str((node.get("target") or {}).get("storage_path") or "").strip()
        if not raw:
            raise FileNotFoundError("artifact_storage_path_missing")

        root = AIONBusinessPaths.ROOT.resolve()
        candidate = Path(raw)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        elif raw.startswith(".runtime/AION_BUSINESS/"):
            resolved = (Path.cwd() / raw).resolve()
        else:
            resolved = (root / raw).resolve()

        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("artifact_path_outside_business_runtime") from exc
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError("artifact_file_missing")
        return resolved

    @classmethod
    def preview(cls, workspace_id: str, item_id: str) -> Dict[str, Any]:
        node = cls.item(workspace_id, item_id)
        protection = cls.protection(node)
        if node.get("type") == "workflow":
            return {"ok": True, "kind": "workflow", "node": node, "protection": protection}

        path = cls._artifact_path(workspace_id, node)
        suffix = path.suffix.lower()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        result: Dict[str, Any] = {
            "ok": True,
            "kind": "unknown",
            "name": str(node.get("name") or path.name),
            "document_type": str(node.get("document_type") or suffix.lstrip(".") or "artifact"),
            "mime_type": mime_type,
            "byte_size": path.stat().st_size,
            "protection": protection,
            "node": {k: v for k, v in node.items() if k != "children"},
        }

        if suffix in {".xlsx", ".xlsm"}:
            from openpyxl import load_workbook

            workbook = load_workbook(path, read_only=True, data_only=True)
            sheets = []
            for sheet in workbook.worksheets[:8]:
                rows = []
                max_row = min(max(int(sheet.max_row or 1), 1), 120)
                max_col = min(max(int(sheet.max_column or 1), 1), 30)
                for row in sheet.iter_rows(min_row=1, max_row=max_row, max_col=max_col, values_only=True):
                    rows.append(["" if value is None else str(value) for value in row])
                sheets.append({"name": sheet.title, "rows": rows})
            result.update(kind="spreadsheet", sheets=sheets)
        elif suffix == ".csv":
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            rows = list(csv.reader(io.StringIO(text)))[:250]
            result.update(kind="spreadsheet", sheets=[{"name": path.stem, "rows": rows}])
        elif suffix == ".docx":
            from docx import Document

            doc = Document(path)
            blocks = [{"type": "paragraph", "text": p.text} for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                blocks.append({"type": "table", "rows": [[cell.text for cell in row.cells] for row in table.rows]})
            result.update(kind="document", blocks=blocks[:500])
        elif suffix == ".pdf":
            if path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("pdf_preview_too_large")
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            result.update(kind="pdf", data_url=f"data:application/pdf;base64,{encoded}")
        elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            if path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("image_preview_too_large")
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            result.update(kind="image", data_url=f"data:{mime_type};base64,{encoded}")
        elif suffix in {".json", ".jsonl", ".txt", ".md", ".log", ".yaml", ".yml", ".xml", ".html"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            if suffix == ".json":
                try:
                    text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            result.update(kind="text", text=text[:500_000], truncated=len(text) > 500_000)
        else:
            result.update(kind="download", message="This file can be retained and opened with its native desktop application.")
        return result
