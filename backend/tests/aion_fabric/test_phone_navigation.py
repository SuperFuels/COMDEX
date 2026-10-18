from backend.modules.aion_fabric.navigation import PhoneVerifiedNavigation


def test_phone_navigation_verifies_profile_left_chooser(tmp_path):
    verifier = PhoneVerifiedNavigation(tmp_path)
    verifier.begin("profile_2", expected="profile_selected", before_image_sha256="a" * 64)
    result = verifier.verify({
        "image_sha256": "b" * 64,
        "inference": {"surface": "netflix", "view": "browse"},
    })
    assert result["success"] is True
    assert verifier.snapshot()["pending"] is None


def test_phone_navigation_does_not_claim_unobserved_screen_change(tmp_path):
    verifier = PhoneVerifiedNavigation(tmp_path)
    verifier.begin("left", expected="screen_changed", before_image_sha256="a" * 64)
    result = verifier.verify({
        "image_sha256": "a" * 64,
        "inference": {"surface": "netflix", "view": "browse"},
    })
    assert result["success"] is False
