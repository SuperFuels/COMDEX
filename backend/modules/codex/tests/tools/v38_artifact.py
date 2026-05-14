from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.modules.codex.hardware.symbolic_qpu_isa import execute_qpu_opcode, get_qpu_metrics
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

from backend.modules.lean.lean_utils import (
    normalize_codexlang,
    validate_logic_trees,
    normalize_validation_errors,
    inject_preview_and_links,
)

@dataclass
class V38Artifact:
    run_id: str
    timestamp_utc: str
    sheet_run_id: str
    ops: Dict[str, Any]
    qpu_metrics: Dict[str, Any]
    beams_count: int
    eids: List[str]
    nabla_values: List[float]
    lean_errors: List[Dict[str, str]]
    lean_container: Dict[str, Any]

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _collect_eids(beams: List[dict]) -> List[str]:
    out: List[str] = []
    for b in beams or []:
        eid = b.get("eid")
        if b.get("token") == "↔" and eid:
            out.append(str(eid))
    return sorted(set(out))

def generate_v38_artifact(out_dir: str | None = None) -> Path:
    out_root = Path(out_dir or os.getenv("V38_ARTIFACT_DIR", ".runtime/artifacts/v38")).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    sheet_run_id = os.getenv("V38_SHEET_RUN_ID", "v38_run")
    cell = GlyphCell(id="cell_v38", logic="logic:↔ math:∇", position=[0, 0, 0, 0])
    ctx: Dict[str, Any] = {"sheet_run_id": sheet_run_id}

    eq_res = execute_qpu_opcode("logic:↔", ["x", "y"], cell, ctx)

    nabla_vals: List[float] = []
    for _ in range(10):
        v = execute_qpu_opcode("math:∇", [], cell, ctx)[0]
        nabla_vals.append(float(v))

    beams = getattr(cell, "wave_beams", []) or []
    eids = _collect_eids(beams)

    lean_container: Dict[str, Any] = {
        "metadata": {"origin": "lean_import", "source_path": "v38_artifact"},
        "symbolic_logic": [
            {
                "name": "v38_equiv_demo",
                "symbol": "⟦ Theorem ⟧",
                "logic": "logic:↔(x,y)",
                "codexlang": {"logic": "logic:↔(x,y)", "symbol": "⟦ Theorem ⟧"},
                "depends_on": [],
            }
        ],
        "thought_tree": [],
    }

    normalize_codexlang(lean_container)
    inject_preview_and_links(lean_container)
    lean_errs = normalize_validation_errors(validate_logic_trees(lean_container))

    art = V38Artifact(
        run_id=f"v38_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        timestamp_utc=_utc_now(),
        sheet_run_id=sheet_run_id,
        ops={"logic:↔": eq_res, "math:∇": nabla_vals},
        qpu_metrics=get_qpu_metrics(),
        beams_count=len(beams),
        eids=eids,
        nabla_values=nabla_vals,
        lean_errors=lean_errs,
        lean_container=lean_container,
    )

    json_path = out_root / f"{art.run_id}.json"
    md_path = out_root / f"{art.run_id}.md"

    json_path.write_text(json.dumps(asdict(art), indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append(f"# v38 Artifact: {art.run_id}\n")
    md.append(f"- Timestamp (UTC): `{art.timestamp_utc}`")
    md.append(f"- sheet_run_id: `{art.sheet_run_id}`")
    md.append(f"- Beams: `{art.beams_count}`")
    md.append(f"- EIDs: `{', '.join(art.eids) if art.eids else '(none)'}`\n")
    md.append("## ∇ (real numbers)\n")
    md.append("```")
    md.append("\n".join([str(x) for x in art.nabla_values]))
    md.append("```\n")
    md.append("## Lean validation\n")
    md.append("```json")
    md.append(json.dumps(art.lean_errors, indent=2, ensure_ascii=False))
    md.append("```\n")
    md_path.write_text("\n".join(md), encoding="utf-8")

    return json_path

if __name__ == "__main__":
    p = generate_v38_artifact()
    print(f"[v38] wrote {p}")
