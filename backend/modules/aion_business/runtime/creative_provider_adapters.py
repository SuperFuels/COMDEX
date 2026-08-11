"""Validated request builders for replaceable creative rendering providers.

These functions create request contracts only. Network calls and spend remain behind
the Marketing approval boundary.
"""

from __future__ import annotations

from typing import Any


def openai_video_request(prompt: str, ratio: str = "9:16", seconds: int = 8, quality: str = "standard") -> dict[str, Any]:
    sizes = {"9:16": "720x1280", "16:9": "1280x720"}
    allowed_seconds = min((4, 8, 12), key=lambda value: abs(value - int(seconds)))
    return {"model": "sora-2-pro" if quality == "high" else "sora-2", "prompt": prompt, "size": sizes.get(ratio, "720x1280"), "seconds": str(allowed_seconds)}


def gemini_veo_request(prompt: str, ratio: str = "9:16", seconds: int = 8) -> dict[str, Any]:
    return {"model": "veo-3.1-generate-preview", "prompt": prompt, "config": {"aspectRatio": ratio, "durationSeconds": max(4, min(int(seconds), 8))}}


def runway_video_request(prompt: str, ratio: str = "9:16", seconds: int = 10) -> dict[str, Any]:
    return {"model": "gen4.5", "promptText": prompt, "ratio": ratio, "duration": max(5, min(int(seconds), 10))}


def luma_video_request(prompt: str, ratio: str = "9:16", loop: bool = False) -> dict[str, Any]:
    return {"model": "ray-2", "prompt": prompt, "aspect_ratio": ratio, "loop": bool(loop)}
