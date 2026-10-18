from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
UI = Path("desktop/mac/src/aion_cybersecurity_workspace.js").read_text(encoding="utf-8")
INDEX = Path("desktop/mac/src/index.html").read_text(encoding="utf-8")


def test_cybersecurity_is_a_connected_specialist_route():
    assert 'departmentKey === "cybersecurity"' in APP
    assert '["legal", "cybersecurity", "procurement", "projects"].includes(entry.specialist.slug)' in APP
    assert '"cybersecurity",' in APP


def test_workspace_has_split_pilot_and_operational_views():
    assert "Security Pilot" in UI
    assert 'data-acw-tab="${key}"' in UI
    for label in ("Posture", "Assets", "Findings", "Checks", "Incidents", "Authority"):
        assert label in UI


def test_disruptive_boundary_is_visible_and_never_automatic():
    assert "never automatic" in UI
    assert "Execution is currently disabled" in UI
    assert "APPROVED_NOT_EXECUTED" not in UI  # authoritative state comes from backend


def test_safe_guard_heartbeat_is_read_only_and_module_is_loaded():
    assert 'request("/scan/safe")' in UI
    assert "20 * 1000" in UI
    assert "30 * 60 * 1000" in UI
    assert '<script src="./aion_cybersecurity_workspace.js"></script>' in INDEX


def test_aion_investigation_is_bounded_by_deterministic_guard_evidence():
    assert 'department_id: "cybersecurity"' in UI
    assert "Stay within this evidence" in UI
    assert "Evidence boundary:" in UI


def test_explicit_checks_are_available_without_automatic_authority():
    for endpoint in ("/updates/check", "/vulnerabilities/assess", "/domains/check", "/secrets/scan", "/attachments/analyse", "/backups/restore-tests"):
        assert endpoint in UI
    assert "Nothing will be installed" in UI
    assert "content not retained" in UI


def test_desktop_sentinel_is_evidence_driven_and_opens_cybersecurity():
    main = Path("desktop/mac/electron/main.js").read_text(encoding="utf-8")
    preload = Path("desktop/mac/electron/preload.js").read_text(encoding="utf-8")
    sentinel = Path("desktop/mac/electron/aion-sentinel.html").read_text(encoding="utf-8")
    assert "aion-security-sentinel-status" in main
    assert "aion-open-cybersecurity" in main
    assert "getSecuritySentinelStatus" in preload
    assert "AION Security Sentinel" in UI
    for state in ("observing", "investigating", "review", "urgent", "verified", "offline"):
        assert f"[data-state={state}]" in sentinel
