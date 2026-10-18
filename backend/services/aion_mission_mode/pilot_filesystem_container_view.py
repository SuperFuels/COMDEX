"""
AION Phase 21E — Pilot File System and Business Container View.

This module defines the read-model contract for showing Pilot-created artifacts
inside the correct business container.

Security rule:
- The file system view is a read model.
- It does not create files.
- It does not execute tools.
- It does not expose credentials.
- It only displays container-contained artifact metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List


class PilotFilesystemContractError(ValueError):
    pass


def _hash_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _assert_no_secret_text(value: Any) -> None:
    forbidden = [
        "password",
        "api_key",
        "apikey",
        "secret",
        "token",
        "cookie",
        "session",
        "bearer ",
        "private_key",
    ]

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k).lower()
                if any(term in key for term in forbidden):
                    raise PilotFilesystemContractError(f"secret-like field is not allowed in file view: {k}")
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            low = node.lower()
            if any(term in low for term in forbidden):
                raise PilotFilesystemContractError("secret-like text is not allowed in file view")

    walk(value)


@dataclass(frozen=True)
class PilotArtifactView:
    artifact_id: str
    artifact_type: str
    title: str
    business_id: str
    mission_id: str
    mission_run_id: str
    step_id: str
    container_path: str
    artifact_hash: str
    receipt_hash: str
    status: str
    preview_status: str
    open_output_enabled: bool
    download_output_enabled: bool
    view_receipt_enabled: bool
    live_external_action_enabled: bool = False


class PilotFilesystemContainerView:
    VALID_STATUSES = {"draft", "preview", "approved_preview", "sealed_receipt"}
    VALID_PREVIEW_STATUSES = {"draft_only", "preview_only", "receipt_available", "approved_preview"}

    @classmethod
    def expected_artifact_prefix(cls, business_id: str, mission_id: str, run_id: str) -> str:
        return f"business/{business_id}/missions/{mission_id}/runs/{run_id}/artifacts/"

    @classmethod
    def build_artifact_view(cls, artifact: Dict[str, Any]) -> Dict[str, Any]:
        required = [
            "artifact_id",
            "artifact_type",
            "title",
            "business_id",
            "mission_id",
            "mission_run_id",
            "step_id",
            "container_path",
            "artifact_hash",
            "receipt_hash",
            "status",
            "preview_status",
        ]
        missing = [field for field in required if not artifact.get(field)]
        if missing:
            raise PilotFilesystemContractError(f"missing artifact fields: {', '.join(missing)}")

        expected_prefix = cls.expected_artifact_prefix(
            artifact["business_id"],
            artifact["mission_id"],
            artifact["mission_run_id"],
        )
        if not artifact["container_path"].startswith(expected_prefix):
            raise PilotFilesystemContractError("artifact path escapes business mission run container")

        if ".." in artifact["container_path"].split("/"):
            raise PilotFilesystemContractError("artifact path must not contain parent traversal")

        _assert_no_secret_text(artifact)

        if artifact["status"] not in cls.VALID_STATUSES:
            raise PilotFilesystemContractError(f"invalid artifact status: {artifact['status']}")

        if artifact["preview_status"] not in cls.VALID_PREVIEW_STATUSES:
            raise PilotFilesystemContractError(f"invalid preview status: {artifact['preview_status']}")

        view = PilotArtifactView(
            artifact_id=artifact["artifact_id"],
            artifact_type=artifact["artifact_type"],
            title=artifact["title"],
            business_id=artifact["business_id"],
            mission_id=artifact["mission_id"],
            mission_run_id=artifact["mission_run_id"],
            step_id=artifact["step_id"],
            container_path=artifact["container_path"],
            artifact_hash=artifact["artifact_hash"],
            receipt_hash=artifact["receipt_hash"],
            status=artifact["status"],
            preview_status=artifact["preview_status"],
            open_output_enabled=True,
            download_output_enabled=True,
            view_receipt_enabled=True,
            live_external_action_enabled=False,
        )

        payload = asdict(view)
        payload["filesystem_view_hash"] = _hash_payload(payload)
        return payload

    @classmethod
    def build_file_tree(cls, business_id: str, artifacts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        views: List[Dict[str, Any]] = [cls.build_artifact_view(a) for a in artifacts]

        for view in views:
            if view["business_id"] != business_id:
                raise PilotFilesystemContractError("artifact business_id does not match selected container")

        tree = {
            "business_id": business_id,
            "view_type": "pilot_business_container_file_tree",
            "read_model_only": True,
            "raw_tool_execution_enabled": False,
            "live_external_action_buttons_enabled": False,
            "credential_visibility": "masked",
            "artifact_count": len(views),
            "artifacts": sorted(views, key=lambda item: item["container_path"]),
        }
        tree["file_tree_hash"] = _hash_payload(tree)
        return tree

    @classmethod
    def build_empty_file_tree(cls, business_id: str) -> Dict[str, Any]:
        return cls.build_file_tree(business_id, [])
