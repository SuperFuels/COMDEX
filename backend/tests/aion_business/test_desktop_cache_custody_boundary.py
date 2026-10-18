from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    next_function = source.find("\n  function ", start + 1)
    return source[start:] if next_function == -1 else source[start:next_function]


def test_desktop_cache_cannot_write_business_json_to_browser_storage():
    source = (
        REPOSITORY_ROOT / "desktop/mac/src/lib/desktop-cache.js"
    ).read_text(encoding="utf-8")

    assert "localStorage.setItem" not in source
    json_writer = _function_body(source, "writeJsonStorage")
    assert "return false" in json_writer
    assert "AionDesktopPreferences" not in json_writer
    cache_writer = _function_body(source, "persistCache")
    assert "writeJsonStorage" not in cache_writer
    assert "return normalized" in cache_writer


def test_desktop_binding_writes_only_registered_content_free_preferences():
    cache_source = (
        REPOSITORY_ROOT / "desktop/mac/src/lib/desktop-cache.js"
    ).read_text(encoding="utf-8")
    preference_source = (
        REPOSITORY_ROOT / "desktop/mac/src/aion_desktop_preferences.js"
    ).read_text(encoding="utf-8")

    text_writer = _function_body(cache_source, "writeTextStorage")
    assert "AionDesktopPreferences?.isAllowedKey" in text_writer
    assert "AionDesktopPreferences.set" in text_writer
    for key in (
        "aionDesktop.activeTab",
        "aionDesktop.boardroomViewMode",
        "aionDesktop.operationsFlowViewMode",
        "aionDesktop.activeZone",
        "aionDesktop.liveAgentsView",
        "aionDesktop.marketingCalendarMode",
    ):
        assert repr(key) in preference_source


def test_foundation_session_keeps_packet_in_guardian_and_routes_only_preferences():
    source = (
        REPOSITORY_ROOT / "desktop/mac/src/aion_development_business_session.js"
    ).read_text(encoding="utf-8")

    assert "localStorage.setItem" not in source
    assert "sessionStorage.setItem" not in source
    completion = _function_body(source, "hasCompletedBusiness")
    assert "localStorage" not in completion
    assert "foundation_ready_for_finance_handoff" in completion
    restoration = _function_body(source, "restoreCompletedBusiness")
    assert "AionDesktopPreferences.set" in restoration
