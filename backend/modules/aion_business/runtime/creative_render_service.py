"""Persistent, exact-approved creative render jobs with local asset ownership."""

from __future__ import annotations

import hashlib
import json
import base64
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore
from backend.modules.vault.ai_provider_key_store import get_ai_provider_secret


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CreativeRenderService:
    """Paid provider calls are impossible until the immutable job is approved."""

    ALLOWED_PROVIDERS = {"openai", "gemini"}
    ALLOWED_RATIOS = {"9:16", "16:9"}

    def __init__(self, asset_store: LocalAssetStore | None = None) -> None:
        self.assets = asset_store or LocalAssetStore()

    def _jobs_dir(self, workspace_id: str) -> Path:
        root = self.assets.ensure_workspace_dirs(workspace_id)["marketing"]
        return self.assets.ensure_dir(root / "creative_jobs")

    def _job_dir(self, workspace_id: str, job_id: str) -> Path:
        return self.assets.ensure_dir(self._jobs_dir(workspace_id) / self.assets._sanitize_run_id(job_id))

    def _path(self, workspace_id: str, job_id: str) -> Path:
        return self._job_dir(workspace_id, job_id) / "job.json"

    def _read(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, job_id)
        if not path.exists():
            raise FileNotFoundError("creative_render_job_not_found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, workspace_id: str, job: dict[str, Any]) -> dict[str, Any]:
        job["updated_at"] = _now()
        self.assets.write_json(self._path(workspace_id, job["id"]), job)
        return job

    @staticmethod
    def _approval_contract(job: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": job["id"], "workspace_id": job["workspace_id"],
            "provider": job["provider"], "model": job["model"],
            "prompt": job["prompt"], "ratio": job["ratio"],
            "duration_seconds": job["duration_seconds"], "resolution": job["resolution"],
            "reference_asset_paths": job.get("reference_asset_paths", []),
        }

    def prepare(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        provider = str(payload.get("provider") or "gemini").strip().lower()
        if provider not in self.ALLOWED_PROVIDERS:
            raise ValueError("provider_not_enabled_for_direct_paid_rendering")
        prompt = str(payload.get("prompt") or "").strip()
        if len(prompt) < 10:
            raise ValueError("render_prompt_too_short")
        ratio = str(payload.get("ratio") or "9:16")
        if ratio not in self.ALLOWED_RATIOS:
            raise ValueError("unsupported_video_ratio")
        duration = int(payload.get("duration_seconds") or 8)
        if provider == "openai":
            duration = min((4, 8, 12), key=lambda item: abs(item - duration))
            model = str(payload.get("model") or "sora-2")
            if model not in {"sora-2", "sora-2-pro"}:
                raise ValueError("unsupported_openai_video_model")
        else:
            duration = min((4, 6, 8), key=lambda item: abs(item - duration))
            model = str(payload.get("model") or "veo-3.1-generate-preview")
            if model not in {"veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"}:
                raise ValueError("unsupported_gemini_video_model")
        resolution = str(payload.get("resolution") or "720p")
        if resolution not in {"720p", "1080p", "4k"}:
            raise ValueError("unsupported_video_resolution")
        if provider == "openai" and resolution not in {"720p", "1080p"}:
            raise ValueError("unsupported_openai_video_resolution")
        if resolution in {"1080p", "4k"} and provider == "gemini":
            duration = 8
        references = payload.get("reference_asset_paths") or []
        legacy_reference = str(payload.get("reference_asset_path") or "").strip()
        if legacy_reference and legacy_reference not in references:
            references = [legacy_reference, *references]
        references = [str(Path(item).expanduser().resolve()) for item in references if str(item).strip()]
        maximum_references = 1 if provider == "openai" else 3
        if len(references) > maximum_references:
            raise ValueError(f"{provider}_supports_at_most_{maximum_references}_reference_images")
        for reference in references:
            if not Path(reference).is_file():
                raise ValueError("reference_asset_not_found")
            mime = mimetypes.guess_type(reference)[0] or ""
            if not mime.startswith("image/"):
                raise ValueError("reference_asset_must_be_an_image")
        if references and provider == "gemini":
            duration = 8

        job_id = f"render_{uuid4().hex[:16]}"
        job = {
            "id": job_id, "workspace_id": workspace_id, "kind": "video_generation",
            "provider": provider, "model": model, "prompt": prompt, "ratio": ratio,
            "duration_seconds": duration, "resolution": resolution,
            "reference_asset_paths": references, "reference_asset_path": references[0] if references else None,
            "rendition_id": payload.get("rendition_id"),
            "campaign_plan_hash": payload.get("campaign_plan_hash"),
            "status": "prepared", "created_by_person_id": str(payload.get("created_by_person_id") or "desktop_user"),
            "created_at": _now(), "updated_at": _now(), "approval": None,
            "provider_job_id": None, "asset": None, "error": None,
        }
        job["approval_hash"] = _hash(self._approval_contract(job))
        return self._write(workspace_id, job)

    def approve(self, workspace_id: str, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        job = self._read(workspace_id, job_id)
        if job["status"] != "prepared":
            raise ValueError("only_prepared_render_jobs_can_be_approved")
        expected = str(payload.get("expected_approval_hash") or "")
        if expected != job["approval_hash"] or expected != _hash(self._approval_contract(job)):
            raise PermissionError("render_job_changed_since_review")
        if payload.get("paid_generation_authorized") is not True:
            raise PermissionError("paid_generation_must_be_explicitly_authorized")
        ceiling = float(payload.get("maximum_cost_eur") or 0)
        if ceiling <= 0:
            raise ValueError("positive_cost_ceiling_required")
        job["approval"] = {
            "approved_by_person_id": str(payload.get("approved_by_person_id") or ""),
            "approved_at": _now(), "approved_hash": expected,
            "maximum_cost_eur": ceiling, "paid_generation_authorized": True,
        }
        job["status"] = "approved"
        return self._write(workspace_id, job)

    def submit(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        job = self._read(workspace_id, job_id)
        if job["status"] != "approved" or not job.get("approval", {}).get("paid_generation_authorized"):
            raise PermissionError("exact_paid_render_approval_required")
        if job["approval"]["approved_hash"] != _hash(self._approval_contract(job)):
            raise PermissionError("render_job_changed_after_approval")
        key = get_ai_provider_secret(job["provider"])
        if not key:
            raise ValueError(f"{job['provider']}_api_key_missing")
        try:
            result = self._submit_openai(job, key) if job["provider"] == "openai" else self._submit_gemini(job, key)
        except Exception as exc:
            job["status"] = "submission_failed"
            job["error"] = str(exc)[:1000]
            self._write(workspace_id, job)
            raise
        job["provider_job_id"] = result["provider_job_id"]
        job["provider_response"] = result.get("provider_response")
        job["status"] = result.get("status", "submitted")
        job["submitted_at"] = _now()
        return self._write(workspace_id, job)

    def poll(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        job = self._read(workspace_id, job_id)
        if job["status"] not in {"submitted", "processing", "queued"}:
            return job
        key = get_ai_provider_secret(job["provider"])
        if not key:
            raise ValueError(f"{job['provider']}_api_key_missing")
        result = self._poll_openai(job, key) if job["provider"] == "openai" else self._poll_gemini(job, key)
        job["status"] = result["status"]
        job["provider_response"] = result.get("provider_response")
        if result.get("download_url"):
            job["asset"] = self._download(workspace_id, job, result["download_url"], key, result.get("auth_mode"))
            job["status"] = "completed"
            job["completed_at"] = _now()
        if result.get("error"):
            job["error"] = result["error"]
        return self._write(workspace_id, job)

    def get(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        return self._read(workspace_id, job_id)

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        jobs = []
        for path in self._jobs_dir(workspace_id).glob("*/job.json"):
            try:
                jobs.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(jobs, key=lambda item: item.get("created_at", ""), reverse=True)

    @staticmethod
    def _submit_openai(job: dict[str, Any], key: str) -> dict[str, Any]:
        sizes = {("9:16", "720p"): "720x1280", ("9:16", "1080p"): "1024x1792", ("16:9", "720p"): "1280x720", ("16:9", "1080p"): "1792x1024"}
        data = {"model": job["model"], "prompt": job["prompt"], "seconds": str(job["duration_seconds"]), "size": sizes[(job["ratio"], job["resolution"])]}
        files = None
        handle = None
        references = job.get("reference_asset_paths") or []
        if references:
            handle = open(references[0], "rb")
            files = {"input_reference": (Path(references[0]).name, handle)}
        try:
            response = requests.post("https://api.openai.com/v1/videos", headers={"Authorization": f"Bearer {key}"}, data=data, files=files, timeout=90)
            response.raise_for_status()
            body = response.json()
        finally:
            if handle:
                handle.close()
        return {"provider_job_id": body["id"], "status": body.get("status", "submitted"), "provider_response": body}

    @staticmethod
    def _submit_gemini(job: dict[str, Any], key: str) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{job['model']}:predictLongRunning"
        instance: dict[str, Any] = {"prompt": job["prompt"]}
        references = job.get("reference_asset_paths") or []
        if references:
            instance["referenceImages"] = []
            for reference in references:
                mime = mimetypes.guess_type(reference)[0] or "image/png"
                encoded = base64.b64encode(Path(reference).read_bytes()).decode("ascii")
                instance["referenceImages"].append({
                    "image": {"inlineData": {"mimeType": mime, "data": encoded}},
                    "referenceType": "asset",
                })
        body = {"instances": [instance], "parameters": {"aspectRatio": job["ratio"], "durationSeconds": str(job["duration_seconds"]), "resolution": job["resolution"], "sampleCount": 1}}
        response = requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=90)
        response.raise_for_status()
        data = response.json()
        return {"provider_job_id": data["name"], "status": "submitted", "provider_response": data}

    @staticmethod
    def _poll_openai(job: dict[str, Any], key: str) -> dict[str, Any]:
        base = f"https://api.openai.com/v1/videos/{job['provider_job_id']}"
        response = requests.get(base, headers={"Authorization": f"Bearer {key}"}, timeout=45)
        response.raise_for_status()
        body = response.json()
        status = str(body.get("status") or "processing").lower()
        if status in {"completed", "succeeded"}:
            return {"status": "completed", "download_url": f"{base}/content", "auth_mode": "bearer", "provider_response": body}
        if status in {"failed", "cancelled"}:
            return {"status": "failed", "error": str(body.get("error") or status), "provider_response": body}
        return {"status": "processing", "provider_response": body}

    @staticmethod
    def _poll_gemini(job: dict[str, Any], key: str) -> dict[str, Any]:
        operation = str(job["provider_job_id"]).lstrip("/")
        response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/{operation}", headers={"x-goog-api-key": key}, timeout=45)
        response.raise_for_status()
        body = response.json()
        if not body.get("done"):
            return {"status": "processing", "provider_response": body}
        if body.get("error"):
            return {"status": "failed", "error": str(body["error"]), "provider_response": body}
        samples = body.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
        uri = samples[0].get("video", {}).get("uri") if samples else None
        if not uri:
            return {"status": "failed", "error": "gemini_completed_without_video_uri", "provider_response": body}
        return {"status": "completed", "download_url": uri, "auth_mode": "google_key", "provider_response": body}

    def _download(self, workspace_id: str, job: dict[str, Any], url: str, key: str, auth_mode: str | None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {key}"} if auth_mode == "bearer" else ({"x-goog-api-key": key} if auth_mode == "google_key" else {})
        response = requests.get(url, headers=headers, timeout=300, allow_redirects=True)
        response.raise_for_status()
        data = response.content
        target = self.assets.write_bytes(self._job_dir(workspace_id, job["id"]) / "source.mp4", data)
        return {"path": str(target), "mime_type": response.headers.get("content-type", "video/mp4"), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "owned_locally": True}
