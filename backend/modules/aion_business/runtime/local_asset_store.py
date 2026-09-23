from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class LocalAssetStore:
    """
    Local-first writable asset store for Tessaris desktop/runtime outputs.

    Goals:
    - keep user files on local machine by default
    - provide a stable per-workspace folder structure
    - provide safe agent-writable directories
    - prevent arbitrary path traversal by forcing all writes under one root

    Default structure:

        ~/Tessaris/
          workspaces/
            <workspace_id>/
              marketing/
                facebook_posts/
                instagram_posts/
                linkedin_posts/
                x_posts/
                tiktok_posts/
                youtube_posts/
                general_posts/
              agents/
              brand_foundation/
              boardroom/
              audit/
              approvals/
              workflows/
              exports/
              inbox/
              knowledge/
              tmp/

    Notes:
    - All returned paths are absolute Path objects.
    - All write helpers ensure parent directories exist.
    - Callers should store returned paths in runtime metadata / post packages.
    """

    DEFAULT_ROOT_DIRNAME = "Tessaris"

    def __init__(
        self,
        *,
        root_dir: Optional[str | Path] = None,
    ) -> None:
        self.root_dir = self._resolve_root_dir(root_dir)

    def _resolve_root_dir(self, root_dir: Optional[str | Path]) -> Path:
        if root_dir:
            return Path(root_dir).expanduser().resolve()

        env_root = os.getenv("TESSARIS_LOCAL_ROOT")
        if env_root:
            return Path(env_root).expanduser().resolve()

        return (Path.home() / self.DEFAULT_ROOT_DIRNAME).resolve()

    @staticmethod
    def _sanitize_segment(value: Any, fallback: str = "item") -> str:
        text = str(value or "").strip().lower()
        text = text.replace("&", " and ")
        text = re.sub(r"[^\w\s\-\.]+", "_", text)
        text = re.sub(r"[\s/\\]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("._-")
        return text or fallback

    @classmethod
    def _sanitize_workspace_id(cls, workspace_id: Any) -> str:
        return cls._sanitize_segment(workspace_id, "workspace")

    @classmethod
    def _sanitize_agent_id(cls, agent_id: Any) -> str:
        return cls._sanitize_segment(agent_id, "agent")

    @classmethod
    def _sanitize_run_id(cls, run_id: Any) -> str:
        return cls._sanitize_segment(run_id, "run")

    @classmethod
    def _sanitize_filename(cls, filename: Any, fallback: str = "file") -> str:
        name = str(filename or "").strip()
        if not name:
            return fallback

        path = Path(name)
        stem = cls._sanitize_segment(path.stem, fallback)
        suffix = re.sub(r"[^a-zA-Z0-9.]+", "", path.suffix or "")
        if suffix and not suffix.startswith("."):
            suffix = f".{suffix}"
        return f"{stem}{suffix}"

    def _assert_under_root(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        root_resolved = self.root_dir.expanduser().resolve()

        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise ValueError(f"path escapes Tessaris root: {resolved}") from exc

        return resolved

    def ensure_dir(self, path: str | Path) -> Path:
        target = self._assert_under_root(Path(path))
        target.mkdir(parents=True, exist_ok=True)
        return target

    def tessaris_root(self) -> Path:
        return self.ensure_dir(self.root_dir)

    def workspaces_root(self) -> Path:
        return self.ensure_dir(self.tessaris_root() / "workspaces")

    def workspace_root(self, workspace_id: str) -> Path:
        safe_workspace = self._sanitize_workspace_id(workspace_id)
        return self.ensure_dir(self.workspaces_root() / safe_workspace)

    def ensure_workspace_dirs(self, workspace_id: str) -> Dict[str, Path]:
        workspace_root = self.workspace_root(workspace_id)

        paths = {
            "root": workspace_root,
            "marketing": self.ensure_dir(workspace_root / "marketing"),
            "agents": self.ensure_dir(workspace_root / "agents"),
            "brand_foundation": self.ensure_dir(workspace_root / "brand_foundation"),
            "boardroom": self.ensure_dir(workspace_root / "boardroom"),
            "audit": self.ensure_dir(workspace_root / "audit"),
            "approvals": self.ensure_dir(workspace_root / "approvals"),
            "workflows": self.ensure_dir(workspace_root / "workflows"),
            "exports": self.ensure_dir(workspace_root / "exports"),
            "inbox": self.ensure_dir(workspace_root / "inbox"),
            "knowledge": self.ensure_dir(workspace_root / "knowledge"),
            "tmp": self.ensure_dir(workspace_root / "tmp"),
        }

        marketing_root = paths["marketing"]
        for folder in (
            "facebook_posts",
            "instagram_posts",
            "linkedin_posts",
            "x_posts",
            "tiktok_posts",
            "youtube_posts",
            "general_posts",
        ):
            paths[f"marketing_{folder}"] = self.ensure_dir(marketing_root / folder)

        return paths

    def ensure_agent_dirs(self, workspace_id: str, agent_id: str) -> Dict[str, Path]:
        workspace_paths = self.ensure_workspace_dirs(workspace_id)
        agent_root = self.ensure_dir(
            workspace_paths["agents"] / self._sanitize_agent_id(agent_id)
        )

        return {
            "root": agent_root,
            "memory": self.ensure_dir(agent_root / "memory"),
            "outputs": self.ensure_dir(agent_root / "outputs"),
            "drafts": self.ensure_dir(agent_root / "drafts"),
            "tasks": self.ensure_dir(agent_root / "tasks"),
            "logs": self.ensure_dir(agent_root / "logs"),
            "scratch": self.ensure_dir(agent_root / "scratch"),
        }

    def get_marketing_channel_dir(self, workspace_id: str, channel: Optional[str]) -> Path:
        workspace_paths = self.ensure_workspace_dirs(workspace_id)
        normalized = self._sanitize_segment(channel or "general", "general")

        mapping = {
            "facebook": "facebook_posts",
            "facebook_ads": "facebook_posts",
            "instagram": "instagram_posts",
            "linkedin": "linkedin_posts",
            "x": "x_posts",
            "twitter": "x_posts",
            "tiktok": "tiktok_posts",
            "youtube": "youtube_posts",
        }

        folder_name = mapping.get(normalized, "general_posts")
        return workspace_paths[f"marketing_{folder_name}"]

    def get_marketing_run_dir(
        self,
        workspace_id: str,
        channel: Optional[str],
        run_id: str,
    ) -> Path:
        channel_dir = self.get_marketing_channel_dir(workspace_id, channel)
        return self.ensure_dir(channel_dir / self._sanitize_run_id(run_id))

    def get_workflow_run_dir(self, workspace_id: str, run_id: str) -> Path:
        workspace_paths = self.ensure_workspace_dirs(workspace_id)
        return self.ensure_dir(
            workspace_paths["workflows"] / self._sanitize_run_id(run_id)
        )

    def get_approval_dir(self, workspace_id: str, approval_id: str) -> Path:
        workspace_paths = self.ensure_workspace_dirs(workspace_id)
        return self.ensure_dir(
            workspace_paths["approvals"] / self._sanitize_segment(approval_id, "approval")
        )

    def write_text(
        self,
        path: str | Path,
        text: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        target = self._assert_under_root(Path(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(text), encoding=encoding)
        return target

    def write_bytes(
        self,
        path: str | Path,
        data: bytes,
    ) -> Path:
        target = self._assert_under_root(Path(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def write_json(
        self,
        path: str | Path,
        payload: Any,
        *,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> Path:
        target = self._assert_under_root(Path(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=indent, ensure_ascii=ensure_ascii),
            encoding="utf-8",
        )
        return target

    def append_jsonl(
        self,
        path: str | Path,
        record: Dict[str, Any],
        *,
        ensure_ascii: bool = False,
    ) -> Path:
        target = self._assert_under_root(Path(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=ensure_ascii)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
        return target

    def write_marketing_run_bundle(
        self,
        *,
        workspace_id: str,
        run_id: str,
        channel: Optional[str] = None,
        caption: Optional[str] = None,
        carousel: Optional[Iterable[Any]] = None,
        post_package: Optional[Dict[str, Any]] = None,
        publish_result: Optional[Dict[str, Any]] = None,
        generated_image_bytes: Optional[bytes] = None,
        generated_image_filename: Optional[str] = None,
        generated_image_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[str]]:
        run_dir = self.get_marketing_run_dir(workspace_id, channel, run_id)

        created: Dict[str, Optional[str]] = {
            "run_dir": str(run_dir),
            "caption_path": None,
            "carousel_path": None,
            "post_package_path": None,
            "publish_result_path": None,
            "generated_image_path": None,
            "generated_image_metadata_path": None,
        }

        if caption is not None:
            created["caption_path"] = str(
                self.write_text(run_dir / "caption.txt", caption)
            )

        if carousel is not None:
            created["carousel_path"] = str(
                self.write_json(run_dir / "carousel.json", list(carousel))
            )

        if post_package is not None:
            created["post_package_path"] = str(
                self.write_json(run_dir / "post_package.json", post_package)
            )

        if publish_result is not None:
            created["publish_result_path"] = str(
                self.write_json(run_dir / "publish_result.json", publish_result)
            )

        if generated_image_bytes is not None:
            filename = self._sanitize_filename(
                generated_image_filename or "creative.png",
                "creative.png",
            )
            created["generated_image_path"] = str(
                self.write_bytes(run_dir / filename, generated_image_bytes)
            )

        if generated_image_payload is not None:
            created["generated_image_metadata_path"] = str(
                self.write_json(
                    run_dir / "generated_image.json",
                    generated_image_payload,
                )
            )

        return created