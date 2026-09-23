from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.perception import PhoneVisualPerception


JPEG = b"\xff\xd8\xff" + (b"x" * 64)


def test_phone_perception_discards_pixels_and_infers_netflix_profile(tmp_path):
    perception = PhoneVisualPerception(
        tmp_path,
        analyzer=lambda path: {
            "texts": ["Netflix", "Who's watching?", "Kevin", "Mia"],
            "labels": [{"label": "television", "confidence": 0.91}],
        },
    )
    record = perception.analyze(JPEG, "image/jpeg")
    assert record["image_retained"] is False
    assert record["inference"]["surface"] == "netflix"
    assert record["inference"]["view"] == "profile_chooser"
    assert not list((tmp_path / "perception").glob("*.jpg"))
    persisted = json.loads((tmp_path / "perception" / "latest_phone_vision.json").read_text())
    assert persisted["image_sha256"] == record["image_sha256"]


def test_phone_perception_recognises_netflix_choose_a_profile_wording(tmp_path):
    perception = PhoneVisualPerception(
        tmp_path,
        analyzer=lambda path: {
            "texts": ["NETFLIX", "Choose a profile", "beccanewman979", "kids"],
            "text_observations": [
                {"text": "NETFLIX", "x": 0.14, "y": 0.70},
                {"text": "Choose a profile", "x": 0.15, "y": 0.69},
                {"text": "beccanewman979", "x": 0.28, "y": 0.62},
                {"text": "kids", "x": 0.22, "y": 0.46},
                {"text": "BACKGROUND PROGRAMME TITLE", "x": 0.73, "y": 0.38},
            ],
            "labels": [],
        },
    )
    record = perception.analyze(JPEG, "image/jpeg")
    assert record["inference"]["surface"] == "netflix"
    assert record["inference"]["view"] == "profile_chooser"
    assert record["inference"]["profile_names"] == ["beccanewman979", "kids"]
    assert perception.known_profiles()["names"] == ["beccanewman979", "kids"]


def test_phone_perception_infers_google_consent(tmp_path):
    perception = PhoneVisualPerception(
        tmp_path,
        analyzer=lambda path: {"texts": ["Google", "Before you continue", "Accept all", "Reject all"], "labels": []},
    )
    record = perception.analyze(JPEG, "image/jpeg")
    assert record["inference"]["surface"] == "web_browser"
    assert record["inference"]["view"] == "google_consent"


def test_phone_perception_rejects_unbounded_or_unknown_images(tmp_path):
    perception = PhoneVisualPerception(tmp_path, analyzer=lambda path: {})
    with pytest.raises(ValueError, match="JPEG, PNG, or HEIC"):
        perception.analyze(b"not-an-image", "text/plain")
    with pytest.raises(ValueError, match="5 MiB"):
        perception.analyze(b"\xff\xd8\xff" + (b"x" * (5 * 1024 * 1024)), "image/jpeg")


def test_phone_perception_keeps_bounded_text_geometry_not_pixels(tmp_path):
    perception = PhoneVisualPerception(
        tmp_path,
        analyzer=lambda path: {
            "texts": ["A subtitle line"],
            "text_observations": [{"text": "A subtitle line", "confidence": 0.94, "x": 0.1, "y": 0.08, "width": 0.8, "height": 0.05}],
            "labels": [],
        },
    )
    record = perception.analyze(JPEG, "image/jpeg")
    assert record["text_observations"][0]["y"] == 0.08
    assert record["text_observations"][0]["text"] == "A subtitle line"
    assert record["image_retained"] is False


def test_owner_can_save_all_five_distinct_profile_labels(tmp_path):
    perception = PhoneVisualPerception(tmp_path, analyzer=lambda path: {})
    saved = perception.save_profile_names(["Becca", "Kevin", "Mia", "Kids", "Guest"])
    assert saved["names"] == ["Becca", "Kevin", "Mia", "Kids", "Guest"]
    assert saved["source"] == "owner_private_controller"
    assert perception.known_profiles()["names"] == saved["names"]

    with pytest.raises(ValueError, match="all five"):
        perception.save_profile_names(["Becca", "Kevin"])
