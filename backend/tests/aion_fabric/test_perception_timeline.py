from __future__ import annotations

from backend.modules.aion_fabric.perception_timeline import MultiFrameScreenPerception


def _frame(index, *, surface="netflix", title="The Crown", text=None):
    perception = {
        "image_sha256": f"{index:064x}",
        "observed_at": f"2026-08-30T10:00:{index:02d}+00:00",
        "texts": [text] if text else [],
    }
    fused = {
        "surface": surface,
        "app": {"id": "netflix", "title": "Netflix"},
        "confidence": 0.9,
        "summary": "Netflix screen",
        "subtitles": {"lines": [f"subtitle {index}"]},
        "scoreboard": {"detected": False},
        "provider_metadata": {"provider": "netflix", "title": title, "metadata_status": "official_api_verified"},
    }
    return perception, fused


def test_single_frame_does_not_establish_stable_surface_or_programme(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    perception, fused = _frame(1)
    result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert result["surface_stable"] is False
    assert result["surface"] == "uncertain"
    assert result["programme"]["stable"] is False


def test_two_consistent_frames_establish_surface_and_title(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    for index in (1, 2):
        perception, fused = _frame(index)
        result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert result["surface"] == "netflix"
    assert result["surface_stable"] is True
    assert result["programme"]["title"] == "The Crown"
    assert result["programme"]["stable"] is True
    assert result["programme"]["provider_verified"] is True


def test_conflicting_surface_stays_uncertain_until_majority(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    for index, surface in ((1, "netflix"), (2, "youtube")):
        perception, fused = _frame(index, surface=surface, title="")
        result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert result["surface_stable"] is False
    assert result["surface"] == "uncertain"


def test_duplicate_frame_is_ignored(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    perception, fused = _frame(1)
    service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert result["duplicate_frame_ignored"] is True
    assert service.snapshot()["retained_structured_frames"] == 1


def test_playback_position_is_ocr_evidence_not_provider_verified(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    perception, fused = _frame(1, text="12:34 / 52:10")
    result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert result["playback_position"]["position"] == "12:34"
    assert result["playback_position"]["duration"] == "52:10"
    assert result["playback_position"]["verified_by_provider"] is False


def test_only_bounded_structured_frames_are_retained(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    for index in range(1, 15):
        perception, fused = _frame(index)
        service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    snapshot = service.snapshot()
    assert snapshot["retained_structured_frames"] == 12
    assert snapshot["source_pixels_retained"] is False


def test_signed_provider_telemetry_overrides_ocr_position_and_verifies_programme(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    telemetry = {
        "authenticated": True,
        "provider": "netflix",
        "content": {"content_id": "81234567", "title": "The Crown"},
        "playback": {"state": "playing", "position_seconds": 321, "duration_seconds": 3600},
        "entitlement": {"status": "included", "verified": True},
        "record_hash": "a" * 64,
    }
    for index in (1, 2):
        perception, fused = _frame(index, title="")
        result = service.accept(
            perception=perception,
            fused=fused,
            observer_session_id="session_a",
            provider_telemetry=telemetry,
        )

    assert result["programme"]["title"] == "The Crown"
    assert result["programme"]["provider_verified"] is True
    assert result["programme"]["signed_playback_telemetry"] is True
    assert result["playback_position"]["position_seconds"] == 321
    assert result["playback_position"]["verified_by_provider"] is True


def test_two_new_surface_frames_reset_old_programme_context(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    for index in (1, 2):
        perception, fused = _frame(index, surface="netflix", title="The Crown")
        service.accept(perception=perception, fused=fused, observer_session_id="session_a")

    perception, fused = _frame(3, surface="youtube", title="")
    pending = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert pending["context_transition"]["pending"] is True

    perception, fused = _frame(4, surface="youtube", title="Space documentary")
    changed = service.accept(perception=perception, fused=fused, observer_session_id="session_a")
    assert changed["surface"] == "youtube"
    assert changed["context_transition"]["changed"] is True
    assert changed["context_transition"]["from_surface"] == "netflix"
    assert changed["programme"]["title"] != "The Crown"
    assert changed["context_transition"]["old_context_evidence_reused"] is False


def test_repeated_ocr_title_is_stable_but_not_provider_verified(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    for index in (1, 2):
        perception, fused = _frame(index, title="")
        fused["programme_candidates"] = [{
            "title": "The Crown",
            "ocr_confidence": 0.95,
            "geometry_score": 0.8,
            "source": "owner_capture_repeated_confirmation_required",
        }]
        result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")

    assert result["programme"]["title"] == "The Crown"
    assert result["programme"]["stable"] is True
    assert result["programme"]["identity_source"] == "repeated_ocr"
    assert result["programme"]["provider_verified"] is False
    assert result["programme"]["catalogue_verified"] is False
    assert result["programme"]["current_playback_verified"] is False


def test_public_catalogue_identity_does_not_claim_current_playback(tmp_path):
    service = MultiFrameScreenPerception(tmp_path)
    perception, fused = _frame(1, title="The Crown")
    fused["provider_metadata"].update({
        "provider": "programme_catalogue",
        "metadata_status": "public_catalogue_exact_match",
        "catalogue_identity_verified": True,
        "current_playback_verified": False,
    })
    result = service.accept(perception=perception, fused=fused, observer_session_id="session_a")

    assert result["programme"]["title"] == "The Crown"
    assert result["programme"]["stable"] is True
    assert result["programme"]["identity_source"] == "public_programme_catalogue"
    assert result["programme"]["catalogue_verified"] is True
    assert result["programme"]["provider_verified"] is False
    assert result["programme"]["current_playback_verified"] is False
