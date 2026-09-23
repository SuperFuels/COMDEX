from __future__ import annotations

from backend.modules.aion_fabric.live_media_authority import LiveMediaAuthority


def test_subtitle_dubbing_overlay_and_audio_fail_closed_without_platform_and_rights(tmp_path):
    authority = LiveMediaAuthority(tmp_path)

    assert authority.subtitle_projection(platform_grants={}, subtitle_rights={})["authorized"] is False
    assert authority.local_dubbing(platform_grants={"authorized_audio_output_route": True}, content_rights={})["authorized"] is False
    assert authority.compact_overlay(platform_grants={"native_overlay_authority": True})["authorized"] is False
    assert authority.audio_enhancement(platform_grants={"audio_dsp_control": True, "audio_dsp_presets": []}, preset="dialogue_clarity")["authorized"] is False


def test_platform_media_action_is_authorized_only_when_every_required_grant_is_present(tmp_path):
    authority = LiveMediaAuthority(tmp_path)
    subtitles = authority.subtitle_projection(
        platform_grants={"native_overlay_authority": True, "caption_projection_authority": True},
        subtitle_rights={"projection_authorized": True},
    )
    audio = authority.audio_enhancement(
        platform_grants={"audio_dsp_control": True, "audio_dsp_presets": ["dialogue_clarity"]},
        preset="dialogue_clarity",
    )

    assert subtitles["authorized"] is True
    assert audio["authorized"] is True
    assert audio["model_output_treated_as_permission"] is False


def test_highlights_are_links_from_authorized_feed_never_scraped_video(tmp_path):
    authority = LiveMediaAuthority(tmp_path)
    result = authority.authorized_highlights(event={"authorized_highlights": [
        {"title": "Goal 1", "url": "https://provider.example/highlight/1", "provider": "Official feed", "provider_verified": True, "rights_authorized": True},
        {"title": "Unlicensed copy", "url": "https://video.example/copy", "provider_verified": False, "rights_authorized": False},
    ]})

    assert result["authorized"] is True
    assert len(result["evidence"]["routes"]) == 1
    assert result["evidence"]["video_downloaded"] is False
