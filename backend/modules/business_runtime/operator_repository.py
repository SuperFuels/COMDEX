from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional
import json

from .contracts_operator import AgentOperator


class OperatorRepository:
    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "operators.json"

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, rows: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def save(self, operator: AgentOperator) -> None:
        rows = [r for r in self._load() if r.get("id") != operator.id]
        rows.append(asdict(operator))
        self._save(rows)

    def get(self, operator_id: str) -> Optional[dict]:
        for row in self._load():
            if row.get("id") == operator_id:
                return row
        return None

    def list(self, department_key: str | None = None) -> list[dict]:
        rows = self._load()
        if department_key:
            rows = [r for r in rows if r.get("department_key") == department_key]
        return rows