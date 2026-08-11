"""Local visual timeline, subtitles, overlays, transitions, music and export."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import av
import imageio_ffmpeg

from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore
from backend.modules.aion_business.runtime.marketing_creative_engine import PLATFORM_PROFILES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CreativeTimelineService:
    TRANSITIONS = {"cut", "fade", "wipeleft", "wiperight", "slideleft", "slideright", "dissolve"}
    MOTION_PRESETS = {"none", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"}
    AUDIO_MASTERING = {"off", "social", "broadcast"}
    BRAND_PRESETS = {"clean", "bold", "cinematic"}

    def __init__(self, asset_store: LocalAssetStore | None = None) -> None:
        self.assets = asset_store or LocalAssetStore()
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def _root(self, workspace_id: str) -> Path:
        return self.assets.ensure_dir(self.assets.ensure_workspace_dirs(workspace_id)["marketing"] / "timelines")

    def _dir(self, workspace_id: str, timeline_id: str) -> Path:
        return self.assets.ensure_dir(self._root(workspace_id) / self.assets._sanitize_run_id(timeline_id))

    def _path(self, workspace_id: str, timeline_id: str) -> Path:
        return self._dir(workspace_id, timeline_id) / "timeline.json"

    def save_voiceover(self, workspace_id: str, filename: str, content: bytes) -> dict[str, Any]:
        if not content:
            raise ValueError("empty_voiceover_recording")
        if len(content) > 100 * 1024 * 1024:
            raise ValueError("voiceover_recording_too_large")
        suffix = Path(filename or "voiceover.webm").suffix.lower()
        if suffix not in {".webm", ".wav", ".mp3", ".m4a", ".aac", ".ogg"}:
            suffix = ".webm"
        root = self.assets.ensure_dir(self.assets.ensure_workspace_dirs(workspace_id)["marketing"] / "voiceovers")
        target = self.assets.write_bytes(root / f"voiceover_{uuid4().hex[:16]}{suffix}", content)
        return {"path": str(target), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "owned_locally": True}

    @staticmethod
    def _existing_optional_path(value: Any, field: str) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"{field}_not_found")
        return str(path)

    def create(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        clips = payload.get("clips") or []
        if not clips:
            raise ValueError("at_least_one_timeline_clip_required")
        normalized = []
        for index, clip in enumerate(clips):
            source = Path(str(clip.get("source_path") or "")).expanduser().resolve()
            if not source.is_file():
                raise ValueError(f"timeline_source_not_found:{source}")
            start = max(0.0, float(clip.get("start_seconds") or 0))
            end = float(clip.get("end_seconds") or 0)
            with av.open(str(source)) as container:
                media_duration = float(container.duration or 0) / 1_000_000
                if media_duration <= 0:
                    video_stream = next((stream for stream in container.streams if stream.type == "video"), None)
                    if video_stream and video_stream.duration is not None and video_stream.time_base is not None:
                        media_duration = float(video_stream.duration * video_stream.time_base)
            if media_duration > 0:
                if start >= media_duration:
                    raise ValueError("clip_start_exceeds_source_duration")
                end = min(end, media_duration)
            if end <= start:
                raise ValueError("clip_end_must_be_after_start")
            motion_preset = str(clip.get("motion_preset") or "none").strip().lower()
            if motion_preset not in self.MOTION_PRESETS:
                raise ValueError("unsupported_clip_motion_preset")
            normalized.append({
                "id": str(clip.get("id") or f"clip_{uuid4().hex[:10]}") , "index": index,
                "source_path": str(source), "start_seconds": start, "end_seconds": end,
                "label": str(clip.get("label") or f"Clip {index + 1}"),
                "motion_preset": motion_preset,
                "motion_intensity": max(0.0, min(float(clip.get("motion_intensity") or 0.5), 1.0)),
            })
        platform = str(payload.get("platform") or "instagram_reels")
        if platform not in PLATFORM_PROFILES:
            raise ValueError("unsupported_timeline_platform")
        transition = dict(payload.get("transition") or {})
        transition_type = str(transition.get("type") or "cut").lower()
        if transition_type not in self.TRANSITIONS:
            raise ValueError("unsupported_timeline_transition")
        transition_duration = max(0.0, min(float(transition.get("duration_seconds") or 0), 2.0))
        if transition_type == "cut":
            transition_duration = 0.0
        shortest = min(item["end_seconds"] - item["start_seconds"] for item in normalized)
        if transition_duration >= shortest:
            raise ValueError("transition_must_be_shorter_than_every_clip")

        subtitles = []
        for item in payload.get("subtitles") or []:
            start = max(0.0, float(item.get("start_seconds") or 0))
            end = float(item.get("end_seconds") or 0)
            text = str(item.get("text") or "").strip()
            if text and end > start:
                subtitles.append({"start_seconds": start, "end_seconds": end, "text": text})
        overlays = []
        for item in payload.get("text_overlays") or []:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            color = str(item.get("color") or "white").strip().lower()
            if not re.fullmatch(r"(?:white|black|yellow|red|blue|green|cyan|magenta|#[0-9a-f]{6})", color):
                raise ValueError("unsupported_text_overlay_color")
            overlays.append({
                "text": text, "start_seconds": max(0.0, float(item.get("start_seconds") or 0)),
                "end_seconds": max(0.1, float(item.get("end_seconds") or 9999)),
                "position": str(item.get("position") or "bottom"),
                "font_size": max(18, min(int(item.get("font_size") or 54), 120)),
                "color": color,
                "animation": str(item.get("animation") or "fade").strip().lower(),
            })
        if any(item["animation"] not in {"none", "fade", "slide_up"} for item in overlays):
            raise ValueError("unsupported_text_overlay_animation")
        audio_mastering = str(payload.get("audio_mastering") or "social").strip().lower()
        if audio_mastering not in self.AUDIO_MASTERING:
            raise ValueError("unsupported_audio_mastering_preset")
        brand_preset = str(payload.get("brand_preset") or "clean").strip().lower()
        if brand_preset not in self.BRAND_PRESETS:
            raise ValueError("unsupported_brand_preset")
        timeline_id = f"timeline_{uuid4().hex[:16]}"
        record = {
            "id": timeline_id, "workspace_id": workspace_id,
            "name": str(payload.get("name") or "Creative timeline"), "platform": platform,
            "clips": normalized, "transition": {"type": transition_type, "duration_seconds": transition_duration},
            "subtitles": subtitles,
            "subtitle_path": self._existing_optional_path(payload.get("subtitle_path"), "subtitle_path"),
            "text_overlays": overlays,
            "logo_path": self._existing_optional_path(payload.get("logo_path"), "logo_path"),
            "music_path": self._existing_optional_path(payload.get("music_path"), "music_path"),
            "music_volume": max(0.0, min(float(payload.get("music_volume") or 0.20), 1.0)),
            "voiceover_path": self._existing_optional_path(payload.get("voiceover_path"), "voiceover_path"),
            "voiceover_volume": max(0.0, min(float(payload.get("voiceover_volume") or 1.0), 2.0)),
            "voiceover_start_seconds": max(0.0, float(payload.get("voiceover_start_seconds") or 0)),
            "duck_music_under_voice": payload.get("duck_music_under_voice") is not False,
            "audio_mastering": audio_mastering,
            "brand_preset": brand_preset,
            "status": "draft", "created_at": _now(),
            "created_by_person_id": str(payload.get("created_by_person_id") or "desktop_user"),
            "export": None,
        }
        self.assets.write_json(self._path(workspace_id, timeline_id), record)
        return record

    def get(self, workspace_id: str, timeline_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, timeline_id)
        if not path.exists():
            raise FileNotFoundError("creative_timeline_not_found")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _has_audio(source: str) -> bool:
        with av.open(source) as container:
            return any(stream.type == "audio" for stream in container.streams)

    @staticmethod
    def _filter_path(path: str) -> str:
        return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    @staticmethod
    def _srt_time(value: float) -> str:
        millis = max(0, round(value * 1000))
        hours, remainder = divmod(millis, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _subtitle_file(self, root: Path, record: dict[str, Any]) -> str | None:
        if record.get("subtitle_path"):
            return record["subtitle_path"]
        subtitles = record.get("subtitles") or []
        if not subtitles:
            return None
        blocks = []
        for index, item in enumerate(subtitles, start=1):
            blocks.append(
                f"{index}\n{self._srt_time(item['start_seconds'])} --> {self._srt_time(item['end_seconds'])}\n{item['text']}\n"
            )
        return str(self.assets.write_text(root / "subtitles.srt", "\n".join(blocks)))

    def export(self, workspace_id: str, timeline_id: str) -> dict[str, Any]:
        record = self.get(workspace_id, timeline_id)
        profile = PLATFORM_PROFILES[record["platform"]]
        width, height = int(profile["width"]), int(profile["height"])
        root = self._dir(workspace_id, timeline_id)
        segment_paths: list[Path] = []
        durations: list[float] = []
        for index, clip in enumerate(record["clips"]):
            target = root / f"segment_{index:03d}.mp4"
            duration = clip["end_seconds"] - clip["start_seconds"]
            durations.append(duration)
            video_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
            motion = str(clip.get("motion_preset") or "none")
            intensity = float(clip.get("motion_intensity") or 0.5)
            frames = max(1, round(duration * 30))
            maximum_zoom = 1.04 + 0.10 * intensity
            zoom_step = max(0.0001, (maximum_zoom - 1.0) / frames)
            if motion == "slow_zoom_in":
                video_filter += f",zoompan=z='min(zoom+{zoom_step:.7f},{maximum_zoom:.5f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30"
            elif motion == "slow_zoom_out":
                video_filter += f",zoompan=z='if(eq(on,0),{maximum_zoom:.5f},max(zoom-{zoom_step:.7f},1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30"
            elif motion in {"pan_left", "pan_right"}:
                progress = f"min(on/{frames},1)"
                x = f"(iw-iw/zoom)*(1-{progress})" if motion == "pan_left" else f"(iw-iw/zoom)*{progress}"
                video_filter += f",zoompan=z='{maximum_zoom:.5f}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30"
            command = [self.ffmpeg, "-y", "-ss", str(clip["start_seconds"]), "-t", str(duration), "-i", clip["source_path"]]
            if self._has_audio(clip["source_path"]):
                command += ["-vf", video_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(target)]
            else:
                command += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-map", "0:v:0", "-map", "1:a:0", "-vf", video_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(target)]
            self._run(command)
            segment_paths.append(target)

        command = [self.ffmpeg, "-y"]
        for segment in segment_paths:
            command += ["-i", str(segment)]
        music_index = None
        if record.get("music_path"):
            music_index = len(segment_paths)
            command += ["-stream_loop", "-1", "-i", record["music_path"]]
        logo_index = None
        if record.get("logo_path"):
            logo_index = len(segment_paths) + (1 if music_index is not None else 0)
            command += ["-loop", "1", "-i", record["logo_path"]]
        voiceover_index = None
        if record.get("voiceover_path"):
            voiceover_index = len(segment_paths) + (1 if music_index is not None else 0) + (1 if logo_index is not None else 0)
            command += ["-i", record["voiceover_path"]]

        filters: list[str] = []
        transition = record.get("transition") or {"type": "cut", "duration_seconds": 0}
        transition_type = transition.get("type", "cut")
        transition_duration = float(transition.get("duration_seconds") or 0)
        if len(segment_paths) == 1:
            filters += ["[0:v]setpts=PTS-STARTPTS[vbase]", "[0:a]asetpts=PTS-STARTPTS[abase]"]
            total_duration = durations[0]
        elif transition_type == "cut" or transition_duration <= 0:
            joined = "".join(f"[{index}:v][{index}:a]" for index in range(len(segment_paths)))
            filters.append(f"{joined}concat=n={len(segment_paths)}:v=1:a=1[vbase][abase]")
            total_duration = sum(durations)
        else:
            previous_v, previous_a = "0:v", "0:a"
            output_duration = durations[0]
            for index in range(1, len(segment_paths)):
                next_v, next_a = f"vx{index}", f"ax{index}"
                offset = max(0.0, output_duration - transition_duration)
                filters.append(f"[{previous_v}][{index}:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[{next_v}]")
                filters.append(f"[{previous_a}][{index}:a]acrossfade=d={transition_duration}:c1=tri:c2=tri[{next_a}]")
                previous_v, previous_a = next_v, next_a
                output_duration += durations[index] - transition_duration
            filters += [f"[{previous_v}]null[vbase]", f"[{previous_a}]anull[abase]"]
            total_duration = output_duration

        current_video = "vbase"
        subtitle_path = self._subtitle_file(root, record)
        if subtitle_path:
            next_video = "vsub"
            filters.append(
                f"[{current_video}]subtitles=filename='{self._filter_path(subtitle_path)}':original_size={width}x{height}:force_style='FontName=Arial,FontSize=9,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=72'[{next_video}]"
            )
            current_video = next_video
        font_path = self._filter_path("/System/Library/Fonts/Supplemental/Arial.ttf")
        for index, overlay in enumerate(record.get("text_overlays") or []):
            text_path = self.assets.write_text(root / f"overlay_{index:02d}.txt", overlay["text"])
            position = overlay.get("position")
            target_y = "h*0.08" if position == "top" else "(h-text_h)/2" if position == "center" else "h-text_h-h*0.10"
            animation = overlay.get("animation", "fade")
            if animation == "slide_up":
                y = f"'if(lt(t,{overlay['start_seconds'] + 0.45}),h-(t-{overlay['start_seconds']})/0.45*(h-({target_y})),{target_y})'"
                alpha = "1"
            else:
                y = target_y
                alpha = f"'if(lt(t,{overlay['start_seconds'] + 0.35}),max(0,(t-{overlay['start_seconds']})/0.35),if(gt(t,{overlay['end_seconds'] - 0.35}),max(0,({overlay['end_seconds']}-t)/0.35),1))'" if animation == "fade" else "1"
            next_video = f"vtext{index}"
            filters.append(
                f"[{current_video}]drawtext=fontfile='{font_path}':textfile='{self._filter_path(str(text_path))}':fontcolor={overlay['color']}:fontsize={overlay['font_size']}:alpha={alpha}:box=1:boxcolor=black@0.55:boxborderw=16:x=(w-text_w)/2:y={y}:enable='between(t,{overlay['start_seconds']},{overlay['end_seconds']})'[{next_video}]"
            )
            current_video = next_video
        if logo_index is not None:
            logo_width = max(96, round(width * 0.18))
            filters.append(f"[{logo_index}:v]scale={logo_width}:-1[logo]")
            filters.append(f"[{current_video}][logo]overlay=W-w-40:40:format=auto:eof_action=repeat[vlogo]")
            current_video = "vlogo"
        filters.append(f"[{current_video}]format=yuv420p[vfinal]")

        current_audio = "abase"
        if music_index is not None:
            fade_out_start = max(0.0, total_duration - 0.8)
            filters.append(f"[{music_index}:a]volume={record.get('music_volume', 0.2)},atrim=duration={total_duration},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_start}:d=0.8[music]")
        if voiceover_index is not None:
            delay_ms = round(float(record.get("voiceover_start_seconds") or 0) * 1000)
            filters.append(f"[{voiceover_index}:a]volume={record.get('voiceover_volume', 1.0)},adelay={delay_ms}|{delay_ms},atrim=duration={total_duration},asetpts=PTS-STARTPTS,asplit=2[voice_mix][voice_side]")
            if music_index is not None and record.get("duck_music_under_voice"):
                filters.append("[music][voice_side]sidechaincompress=threshold=0.025:ratio=10:attack=20:release=350[ducked_music]")
                filters.append(f"[{current_audio}][ducked_music][voice_mix]amix=inputs=3:duration=first:dropout_transition=2[premaster]")
            elif music_index is not None:
                filters.append(f"[{current_audio}][music][voice_mix]amix=inputs=3:duration=first:dropout_transition=2[premaster]")
            else:
                filters.append(f"[{current_audio}][voice_mix]amix=inputs=2:duration=first:dropout_transition=2[premaster]")
            current_audio = "premaster"
        elif music_index is not None:
            filters.append(f"[{current_audio}][music]amix=inputs=2:duration=first:dropout_transition=2[premaster]")
            current_audio = "premaster"
        mastering = record.get("audio_mastering", "social")
        if mastering != "off":
            target = -16 if mastering == "social" else -14
            filters.append(f"[{current_audio}]loudnorm=I={target}:TP=-1.5:LRA=11[amastered]")
            current_audio = "amastered"

        output = root / f"{record['platform']}_export.mp4"
        command += ["-filter_complex", ";".join(filters), "-map", "[vfinal]", "-map", f"[{current_audio}]", "-t", str(total_duration), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)]
        self._run(command)
        thumbnail = root / "thumbnail.jpg"
        self._run([self.ffmpeg, "-y", "-ss", str(min(0.5, total_duration / 2)), "-i", str(output), "-frames:v", "1", "-q:v", "2", str(thumbnail)])
        data = output.read_bytes()
        record["status"] = "exported"
        record["export"] = {
            "path": str(output), "thumbnail_path": str(thumbnail), "width": width, "height": height,
            "ratio": profile["ratio"], "duration_seconds": total_duration, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "created_at": _now(), "owned_locally": True,
            "features": {"subtitles": bool(subtitle_path), "text_overlays": len(record.get("text_overlays") or []), "logo": logo_index is not None, "music": music_index is not None, "voiceover": voiceover_index is not None, "ducking": bool(voiceover_index is not None and music_index is not None and record.get("duck_music_under_voice")), "audio_mastering": mastering, "motion_clips": sum(1 for clip in record["clips"] if clip.get("motion_preset") != "none"), "transition": transition_type, "brand_preset": record.get("brand_preset")},
        }
        self.assets.write_json(self._path(workspace_id, timeline_id), record)
        return record

    @staticmethod
    def _run(command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg_export_failed:{result.stderr[-2200:]}")
