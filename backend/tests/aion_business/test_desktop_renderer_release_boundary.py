from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_electron_runtime_and_release_use_only_the_src_renderer_tree():
    main = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
    package = json.loads((ROOT / "desktop/mac/package.json").read_text(encoding="utf-8"))
    release_files = package["build"]["files"]

    assert 'path.join(__dirname, "..", "src", "index.html")' in main
    assert 'path.join(process.resourcesPath || "", "src", "index.html")' in main
    assert 'path.join(__dirname, "..", "index.html")' not in main
    assert "src/**/*" in release_files
    assert "app.js" not in release_files
    assert "index.html" not in release_files
    assert "!src/*.bak*" in release_files
    assert "!src/**/*.bak*" in release_files
