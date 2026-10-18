from __future__ import annotations

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text()


def test_phase24b_website_scan_uses_openai_backend_port_8000_not_file_cabinet_8080():
    assert "window.__AION_WEBSITE_SCAN_BACKEND_BASE_URL" in APP_JS
    assert '"http://127.0.0.1:8000"' in APP_JS
    scan_start = APP_JS.index("async function applySmallBusinessWebsiteScanDraft")
    scan_block = APP_JS[scan_start:APP_JS.index("function renderSmallBusinessFoundationReviewPanel", scan_start)]
    assert "/api/local-node/aion/small-business/website-scan" in scan_block
    assert "buildAionLocalBackendUrl" not in scan_block
