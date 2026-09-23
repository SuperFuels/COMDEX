from pathlib import Path

MAIN = Path("desktop/mac/electron/main.js")


def test_phase23i_desktop_backend_launcher_uses_uvicorn_not_backend_main_module():
    text = MAIN.read_text()

    assert '"uvicorn"' in text
    assert '"backend.main:app"' in text
    assert '"--host"' in text
    assert '"127.0.0.1"' in text
    assert '"--port"' in text
    assert '"8080"' in text
    assert '["-m", "backend.main"]' not in text
