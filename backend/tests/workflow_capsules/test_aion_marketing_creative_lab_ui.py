from pathlib import Path


APP_JS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def test_creative_lab_is_embedded_in_marketing_workspace():
    source = APP_JS.read_text(encoding="utf-8")
    assert "CREATIVE INTELLIGENCE LAB" in source
    assert "Images, video, clipping and winner learning" in source
    assert "${renderAionMarketingCreativeLab()}" in source
    assert 'apiPost("/api/aion/marketing/creative/plan"' in source


def test_creative_lab_keeps_spend_and_publishing_gated():
    source = APP_JS.read_text(encoding="utf-8")
    assert "NO AUTO SPEND" in source
    assert "NO AUTO PUBLISH" in source
    assert "EVIDENCE GATED" in source


def test_creative_lab_exposes_exact_approved_render_and_local_export():
    source = APP_JS.read_text(encoding="utf-8")
    assert "PREMIUM SOURCE RENDER" in source
    assert "Prepare render contract" in source
    assert "Start paid render" in source
    assert "LOCAL TIMELINE & CLIP EXPORTER" in source
    assert "Visual multi-clip production timeline" in source
    assert 'chooseLocalMedia?.({ kind: "video", multiple: true' in source
    assert "data-aion-timeline-clip-card" in source
    assert "data-aion-timeline-subtitles" in source
    assert "data-aion-timeline-transition" in source
    assert "data-aion-timeline-music-volume" in source
    assert "data-aion-timeline-voiceover" in source
    assert "data-aion-record-timeline-voiceover" in source
    assert "navigator.mediaDevices.getUserMedia" in source
    assert "data-aion-timeline-duck-music" in source
    assert "data-aion-timeline-audio-mastering" in source
    assert "data-aion-timeline-clip-motion" in source
    assert "GOVERNED PUBLICATION PACKAGE" in source
    assert "data-aion-prepare-publication" in source
    assert "data-aion-choose-render-references" in source
    assert "reference_asset_paths" in source
    assert "/renders/${encodeURIComponent(lab.renderJob.id)}/approve" in source
    assert "/timelines/${encodeURIComponent(result.timeline.id)}/export" in source


def test_unified_campaign_journey_replaces_hidden_legacy_launch_path():
    source = APP_JS.read_text(encoding="utf-8")
    assert "AION CAMPAIGN COMMAND" in source
    assert "Plan & create campaign" in source
    assert "renderAionMarketingCampaignJourney" in source
    assert "Approve draft & create assets" in source
    assert "Create with full control" in source
    assert "inferAionMarketingPlatformsFromBrief" in source
    assert "CAMPAIGN CALENDAR" in source
    assert 'data-aion-connect-marketing-provider' in source
