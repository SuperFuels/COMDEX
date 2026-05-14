#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAP_CANDIDATES = [
    ROOT / "backend/modules/photonlang/python_token_map.json",
    ROOT / "backend/modules/photonlang/photonlang/python_token_map.json",  # legacy fallback
]
OUT = ROOT / "docs/photon/token_table.md"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_map() -> dict:
    for p in MAP_CANDIDATES:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("python_token_map.json not found in expected locations")

def render_table(title: str, mapping: dict[str, str]) -> str:
    lines = [f"### {title}", "", "| Python Token | Photon Glyph |", "|---|---|"]
    for k, v in sorted(mapping.items(), key=lambda kv: kv[0]):
        lines.append(f"| `{k}` | `{v}` |")
    lines.append("")
    return "\n".join(lines)

def main() -> None:
    data = load_map()
    keywords = data.get("keywords", {})
    operators = data.get("operators", {})
    punct = data.get("punct", data.get("punctuation", {}))
    ops_and_punct = {**operators, **punct}

    parts = [
        "# Photon Token Table",
        "",
        render_table("Keywords", keywords),
        render_table("Operators & Punctuation", ops_and_punct),
        "_Generated from `python_token_map.json`._",
        "",
    ]
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()