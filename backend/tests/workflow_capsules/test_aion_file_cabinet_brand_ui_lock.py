from pathlib import Path


APP = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"
TEXT = APP.read_text(encoding="utf-8")


def test_file_cabinet_uses_branded_sidebar_icon():
    assert 'class="aion-sidebar-file-cabinet-icon"' in TEXT
    assert 'style.id = "tessaris-file-cabinet-brand-v19"' in TEXT
    assert "stroke:currentColor" in TEXT


def test_file_cabinet_sits_below_toolbar_at_reduced_width():
    branded = TEXT.split('style.id = "tessaris-file-cabinet-brand-v19"', 1)[1]
    assert "top:54px !important" in branded
    assert "height:calc(100vh - 54px) !important" in branded
    assert "width:min(425px, calc(100vw - 64px)) !important" in branded


def test_file_cabinet_uses_current_tessaris_language_and_sync_state():
    assert "Tessaris · Business files" in TEXT
    assert "Documents &amp; workflows" in TEXT
    assert "aion-file-cabinet-sync-dot" in TEXT
    assert "> New folder" in TEXT
    assert "Save workflow" in TEXT


def test_file_cabinet_branding_preserves_existing_governed_actions():
    assert 'data-aion-cabinet-top-folder="true"' in TEXT
    assert 'data-aion-workflow-save="true"' in TEXT
    assert 'data-aion-file-cabinet-open-workflow=' in TEXT
    assert 'data-aion-file-cabinet-open-artifact=' in TEXT
