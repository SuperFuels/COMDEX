from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22x_additions_append_after_last_bullet_not_after_blank_gap():
    assert "lastBulletIndex" in TEXT
    assert "return lastBulletIndex + 1" in TEXT
    assert r"/^\s*[-–—*]\s+/" in TEXT


def test_phase22x_social_additions_prefer_content_plan():
    assert 'lowerValue.includes("twitter")' in TEXT
    assert 'lowerValue.includes("post")' in TEXT
    assert "/content plan/i" in TEXT
