from __future__ import annotations

from pathlib import Path
from typing import Optional


class DocumentTextLoader:
    """
    Minimal loader for parsed_text_ref.

    v0 rules:
      - If parsed_text_ref is an existing filesystem path, read it.
      - If parsed_text_ref looks like "parsed/xxx.txt", treat it as relative to base_dir.
    """

    def __init__(self, *, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def load_text(self, *, parsed_text_ref: Optional[str]) -> str:
        if not parsed_text_ref:
            return ""

        ref = str(parsed_text_ref).strip()
        if not ref:
            return ""

        p = Path(ref)
        if not p.is_absolute():
            p = (self.base_dir / ref).resolve()

        if not p.exists() or not p.is_file():
            return ""

        return p.read_text(encoding="utf-8", errors="ignore")