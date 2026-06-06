from pathlib import Path
import json

PKG = Path("desktop/mac/package.json")

def test_desktop_packaging_excludes_app_js_backups() -> None:
    data = json.loads(PKG.read_text())
    files = data.get("build", {}).get("files", [])
    joined = "\n".join(files)
    assert "!src/*.bak*" in joined
    assert "!src/**/*.bak*" in joined
    assert "!**/*.bak-*" in joined or "!**/*.bak_*" in joined
