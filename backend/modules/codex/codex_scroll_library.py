# backend/modules/codex/codex_scroll_library.py

import os
import json
from pathlib import Path

SCROLL_DIR = Path("data/codex_scrolls")
SCROLL_DIR.mkdir(parents=True, exist_ok=True)

def save_named_scroll(name: str, content: dict):
    path = SCROLL_DIR / f"{name}.codex"
    with open(path, "w") as f:
        json.dump(content, f, indent=2)

def load_named_scroll(name: str) -> dict:
    path = SCROLL_DIR / f"{name}.codex"
    if not path.exists():
        raise FileNotFoundError(f"Scroll '{name}' not found.")
    with open(path, "r") as f:
        return json.load(f)

def list_scrolls() -> list[str]:
    return [p.stem for p in SCROLL_DIR.glob("*.codex")]