from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def test_desktop_local_renderer_knows_explicit_bridge_actions() -> None:
    text = APP_JS.read_text()

    assert '"make.trigger_scenario"' in text
    assert '"zapier.trigger_zap"' in text
    assert '"n8n.trigger_workflow"' in text

    assert "Would prepare a Make.com scenario trigger after approval." in text
    assert "Would prepare a Zapier Zap trigger after approval." in text
    assert "Would prepare an n8n workflow trigger after approval." in text
    assert "Live bridge execution is not enabled." in text
