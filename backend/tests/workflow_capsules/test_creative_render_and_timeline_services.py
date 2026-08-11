import subprocess

import imageio_ffmpeg
import pytest

from backend.modules.aion_business.runtime.creative_render_service import CreativeRenderService
from backend.modules.aion_business.runtime.creative_timeline_service import CreativeTimelineService
from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore


def test_paid_render_requires_exact_hash_and_explicit_cost_authority(tmp_path):
    service = CreativeRenderService(LocalAssetStore(root_dir=tmp_path / "tessaris"))
    job = service.prepare("demo", {
        "provider": "gemini", "prompt": "A cinematic close-up of a carefully repaired tiled bathroom.",
        "ratio": "9:16", "duration_seconds": 8, "resolution": "720p",
    })
    assert job["status"] == "prepared"
    with pytest.raises(PermissionError):
        service.approve("demo", job["id"], {
            "expected_approval_hash": job["approval_hash"], "approved_by_person_id": "owner",
            "maximum_cost_eur": 5, "paid_generation_authorized": False,
        })
    approved = service.approve("demo", job["id"], {
        "expected_approval_hash": job["approval_hash"], "approved_by_person_id": "owner",
        "maximum_cost_eur": 5, "paid_generation_authorized": True,
    })
    assert approved["status"] == "approved"
    assert approved["approval"]["maximum_cost_eur"] == 5


def test_timeline_exports_real_platform_mp4_and_thumbnail(tmp_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    source = tmp_path / "source.mp4"
    subprocess.run([
        ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=2:r=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264",
        "-c:a", "aac", "-shortest", str(source),
    ], check=True, capture_output=True)
    service = CreativeTimelineService(LocalAssetStore(root_dir=tmp_path / "tessaris"))
    timeline = service.create("demo", {
        "name": "Two-cut test", "platform": "instagram_reels",
        "clips": [
            {"source_path": str(source), "start_seconds": 0, "end_seconds": 0.7},
            {"source_path": str(source), "start_seconds": 1.0, "end_seconds": 1.7},
        ],
    })
    exported = service.export("demo", timeline["id"])
    assert exported["status"] == "exported"
    assert exported["export"]["width"] == 1080
    assert exported["export"]["height"] == 1920
    assert exported["export"]["owned_locally"] is True
    assert (tmp_path / "tessaris").exists()


def test_timeline_exports_transition_subtitles_overlay_logo_and_music(tmp_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    sources = []
    for index, color in enumerate(("blue", "green")):
        source = tmp_path / f"source-{index}.mp4"
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=640x360:d=2:r=30",
            "-f", "lavfi", "-i", f"sine=frequency={440 + index * 100}:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(source),
        ], check=True, capture_output=True)
        sources.append(source)
    music = tmp_path / "music.wav"
    logo = tmp_path / "logo.png"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=5", str(music)], check=True, capture_output=True)
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=white:s=160x64:d=1", "-frames:v", "1", str(logo)], check=True, capture_output=True)
    service = CreativeTimelineService(LocalAssetStore(root_dir=tmp_path / "tessaris"))
    timeline = service.create("advanced", {
        "name": "Advanced editor proof", "platform": "instagram_reels",
        "clips": [{"source_path": str(path), "start_seconds": 0, "end_seconds": 2} for path in sources],
        "transition": {"type": "fade", "duration_seconds": 0.4},
        "subtitles": [{"start_seconds": 0, "end_seconds": 1.8, "text": "Verified subtitle"}],
        "text_overlays": [{"text": "VERIFIED OVERLAY", "start_seconds": 0, "end_seconds": 3.6, "position": "top"}],
        "logo_path": str(logo), "music_path": str(music), "music_volume": 0.1,
    })
    exported = service.export("advanced", timeline["id"])
    features = exported["export"]["features"]
    assert features["subtitles"] is True
    assert features["text_overlays"] == 1
    assert features["logo"] is True
    assert features["music"] is True
    assert features["transition"] == "fade"
    assert features["audio_mastering"] == "social"
    assert exported["export"]["bytes"] > 1000
