import json
import os
import re
import difflib
from jsonschema import validate, ValidationError
from typing import Any, Dict, List, Optional, Tuple, Iterable, Union

from backend.modules.patterns.pattern_registry_loader import load_pattern_registry
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
from backend.modules.patterns.pattern_repair_suggester import suggest_pattern_repairs
from backend.modules.symbolic_spreadsheet.sympy.sympy_sheet_executor import execute_sympy_logic
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update

# 🌐 Global flags for runtime control
GLOBAL_FLAGS = {
    "replay_enabled": True,
    "ethics_enabled": True,
    "lightcone_trace": False
}
# ✅ New schema for .atom files
ATOM_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": {"type": "object"},
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "logic", "position"],
                "properties": {
                    "id": {"type": "string"},
                    "logic": {"type": "string"},
                    "position": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 4
                    },
                    "emotion": {"type": "string"},
                    "prediction": {"type": "string"},
                    "trace": {"type": "array", "items": {"type": "string"}},
                    "linked_cells": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "integer"}}
                    },
                    "nested_logic": {"type": "string"}
                }
            }
        }
    },
    "required": ["cells"]
}
# ✅ JSON Schema for validation
SQS_SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": {"type": "object"},
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "logic", "position"],
                "properties": {
                    "id": {"type": "string"},
                    "logic": {"type": "string"},
                    "position": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 4
                    },
                    "emotion": {"type": "string"},
                    "prediction": {"type": "string"},
                    "trace": {"type": "array", "items": {"type": "string"}},
                    "linked_cells": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "integer"}}
                    },
                    "nested_logic": {"type": "string"}
                }
            }
        }
    }
}

# 📦 Canonical loader for .atom symbolic sheets
def load_sqd_sheet(filepath: str) -> List[GlyphCell]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        validate(instance=data, schema=ATOM_SHEET_SCHEMA)
        cell_entries = data.get("cells", [])

        return [GlyphCell.from_dict(entry) for entry in cell_entries]

    except FileNotFoundError:
        print(f"[❌] File not found: {filepath}")
        return []

    except ValidationError as ve:
        print(f"[🛑] Schema error in .atom file: {ve.message}")
        return []

    except Exception as e:
        print(f"[🔥] Failed to load .atom file: {e}")
        return []

# --- F4: Generate prediction forks + live update to QFC ---
def update_prediction_forks(cell: GlyphCell, context: Optional[Dict] = None):
    """
    Creates prediction forks for a cell and pushes live updates to QFC / LightCone HUD.
    """
    try:
        if cell.validated:
            from backend.modules.consciousness.prediction_engine import PredictionEngine
            from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update

            prediction_engine = PredictionEngine()
            forks = prediction_engine.generate_forks(cell.logic, emotion=cell.emotion)
            cell.prediction_forks = forks  # attach forks to cell
            cell.append_trace(f"🔮 Prediction forks updated: {forks}")

            # Push live to QFC / LightCone HUD
            if context and "container_id" in context:
                broadcast_qfc_update(context["container_id"], {
                    "type": "prediction_forks",
                    "source_cell": cell.id,
                    "forks": forks
                })
    except Exception as e:
        print(f"[⚠️ Prediction Forks] Failed for {cell.id}: {e}")

# --- Global helper: generate prediction forks based on logic + emotion ---
def generate_prediction_forks(cell: GlyphCell) -> List[str]:
    """
    Creates alternate prediction paths for a cell based on its logic and emotion.
    """
    forks = []
    base_prediction = cell.prediction or ""
    emotion = (cell.emotion or "neutral").lower()

    if emotion in ["curious", "inspired"]:
        forks.append(f"{base_prediction} + exploratory")
    elif emotion in ["protective", "cautious"]:
        forks.append(f"{base_prediction} + conservative")
    else:
        forks.append(base_prediction)

    if "if" in (cell.logic or ""):
        forks.append(f"{base_prediction} | conditional path")

    return forks


# 🔢 Executes a single cell’s logic
def execute_cell(cell: GlyphCell, context: Optional[Dict] = None):
    """
    Executes a GlyphCell:
    - F1: SoulLaw pre-filter
    - SymPy / CodexLang logic execution
    - Pattern matching & SQI scoring
    - F3: Entangled logic links
    - F4: Prediction forks (live + dependent updates)
    - Mutation metadata & trace logging
    """
    context = context or {}
    sheet_cells = context.get("sheet_cells", [])

    cell.append_trace(f"Executed at pos={cell.position}")

    # --- F1: SoulLaw pre-filter (forbidden patterns) ---
    SOULLAW_FORBIDDEN_PATTERNS = [
        r"destruct", r"harm", r"overwrite", r"delete", r"kill", r"selfdestruct"
    ]

    def check_soul_law(cell: GlyphCell) -> Optional[str]:
        logic_text = (cell.logic or "").lower()
        nested_text = (cell.nested_logic or "").lower()
        for pattern in SOULLAW_FORBIDDEN_PATTERNS:
            if re.search(pattern, logic_text) or re.search(pattern, nested_text):
                return f"Blocked by SoulLaw pattern: '{pattern}'"
        return None

    violation_msg = check_soul_law(cell)
    if violation_msg:
        cell.validated = False
        cell.result = f"⚠️ {violation_msg}"
        cell.append_trace(violation_msg)
        return  # Skip further execution

    # --- SymPy / CodexLang execution ---
    sympy_out = execute_sympy_logic(cell)
    cell.result = sympy_out.get("result")
    cell.validated = sympy_out.get("validated")
    cell.prediction = sympy_out.get("prediction")
    cell.sympy_result = sympy_out.get("sympy_result")
    cell.simplified = sympy_out.get("simplified")
    cell.sympy_error = sympy_out.get("error")
    cell.contradiction = sympy_out.get("contradiction")
    cell.mutation_suggestion = sympy_out.get("mutation_suggestion")
    cell.sqi_trigger = sympy_out.get("sqi_trigger")
    cell.emotion_trigger = sympy_out.get("emotion_trigger")

    # --- Pattern matching + SQI scoring ---
    glyphs = parse_logic_to_glyphs(cell.logic)
    matched_patterns = detect_patterns(glyphs)
    cell.sqi_score = score_sqi(cell)

    if matched_patterns:
        print(f"🔍 Patterns matched in {cell.id}: {matched_patterns}")
    else:
        print(f"🔍 No patterns matched in {cell.id}")

    # --- Mutation & harmony metadata ---
    from datetime import datetime
    cell.mutation_type = "symbolic"
    cell.mutation_parent_id = None
    cell.mutation_score = cell.sqi_score
    cell.mutation_timestamp = datetime.utcnow().isoformat() + "Z"

    pattern_count = len(matched_patterns)
    cell.harmony_score = min(1.0, 0.5 + pattern_count * 0.2 if cell.validated else 0.1)

    # --- F3: Entangled logic links ---
    for linked_id in cell.linked_cells or []:
        try:
            linked_ctx = context.copy()
            linked_ctx["parent_cell_id"] = cell.id
            if "container_id" in linked_ctx:
                broadcast_qfc_update(linked_ctx["container_id"], {
                    "type": "entanglement",
                    "source_cell": cell.id,
                    "target_cell": linked_id,
                    "sqi": cell.sqi_score
                })
        except Exception as e:
            print(f"[⚠️ Entanglement] Failed for {cell.id} -> {linked_id}: {e}")

    # --- F4: Update this cell's prediction forks and broadcast ---
    if cell.validated:
        cell.prediction_forks = generate_prediction_forks(cell)
        cell.append_trace(f"🔮 Prediction forks: {cell.prediction_forks}")
        if "container_id" in context:
            broadcast_qfc_update(context["container_id"], {
                "type": "prediction_forks",
                "source_cell": cell.id,
                "forks": cell.prediction_forks
            })

    # --- F4: Update prediction forks for dependent linked cells ---
    for linked_id in cell.linked_cells or []:
        linked_cell = next((c for c in sheet_cells if c.id == linked_id), None)
        if linked_cell and linked_cell.validated:
            linked_cell.prediction_forks = generate_prediction_forks(linked_cell)
            linked_cell.append_trace(f"🔮 Prediction forks updated due to {cell.id}")
            if "container_id" in context:
                broadcast_qfc_update(context["container_id"], {
                    "type": "prediction_forks",
                    "source_cell": linked_cell.id,
                    "forks": linked_cell.prediction_forks
                })

    # --- LightCone propagation ---
    if GLOBAL_FLAGS["lightcone_trace"]:
        trace_lightcone(cell)

    # --- Trace log ---
    record_trace(cell.id, cell.trace)


# 🔒 SoulLaw Ethics Validator
def validate_cell_ethics(cell: GlyphCell) -> bool:
    forbidden = ["destruct", "harm", "overwrite"]
    return not any(word in cell.logic.lower() for word in forbidden)


# 🌌 Dummy lightcone propagation model
def trace_lightcone(cell: GlyphCell):
    print(f"[Lightcone] Tracing from {cell.id} at {cell.position}")


# 🥲 Post-run SoulLaw / ethics audit
def audit_sheet(cells: List[GlyphCell]):
    """
    Walks all cells after execution to log SoulLaw violations, ethics, and contradictions.
    """
    for cell in cells:
        # SoulLaw / ethics violations
        if not cell.validated:
            note = getattr(cell, "mutationNotes", [])
            note.append("⚠️ Audit: blocked or invalid by SoulLaw/ethics")
            cell.mutationNotes = note
            record_trace(cell.id, "⚠️ Audit: blocked or invalid by SoulLaw/ethics")

        # Contradiction detection
        if getattr(cell, "contradiction", False):
            record_trace(cell.id, "⚠️ Audit: logic contradiction detected")

# 🥲 Execute full sheet
def execute_sheet(cells: List[GlyphCell], context: Optional[Dict] = None):
    """
    Execute all cells in a sheet with full pipeline:
    - F1: SoulLaw pre-filter
    - SymPy / CodexLang logic execution
    - Pattern matching & SQI scoring
    - F3: Entangled logic links
    - F4: Prediction forks (live + dependent updates)
    - Mutation metadata & trace logging
    - F2: Post-run SoulLaw / ethics audit
    """

    # Ensure context exists and inject sheet_cells + container_id for entanglement / forks
    context = context or {}
    context["sheet_cells"] = cells
    context["container_id"] = context.get("container_id", "default_container")

    # Execute each cell in order
    for cell in cells:
        execute_cell(cell, context=context)

    # --- F2: Post-run SoulLaw / ethics audit ---
    audit_sheet(cells)

    # --- F2: Post-run SoulLaw / ethics audit ---
    def audit_sheet(cells: List[GlyphCell]):
        """
        Walk all cells after execution to log SoulLaw violations and other flags.
        """
        for cell in cells:
            if not cell.validated:
                note = getattr(cell, "mutationNotes", [])
                note.append("⚠️ Audit: blocked or invalid by SoulLaw/ethics")
                cell.mutationNotes = note
                record_trace(cell.id, "⚠️ Audit: blocked or invalid by SoulLaw/ethics")
            if getattr(cell, "contradiction", False):
                record_trace(cell.id, "⚠️ Audit: logic contradiction detected")

    audit_sheet(cells)


# 🌐 Dynamic flag control
def set_flag(key: str, value: bool):
    if key in GLOBAL_FLAGS:
        GLOBAL_FLAGS[key] = value
        print(f"[Flag] Set {key} → {value}")
    else:
        print(f"[Flag] Unknown toggle key: {key}")

# 🔄 Step-through replay + mutation lineage walker
def replay_mutation_lineage(cells: List[GlyphCell], start_cell_id: str, step_limit: int = 10):
    lineage = []
    visited_ids = set()
    cell_map = {cell.id: cell for cell in cells}
    current_id = start_cell_id
    steps = 0

    print(f"\n🚦 Starting replay from cell: {start_cell_id}")

    while current_id and steps < step_limit:
        if current_id in visited_ids:
            print(f"🔁 Loop detected at {current_id}, stopping.")
            break

        cell = cell_map.get(current_id)
        if not cell:
            print(f"[❌] Cell not found: {current_id}")
            break

        print(f"\n📍 Step {steps + 1}: {cell.id}")
        print(f"🧬 Logic:      {cell.logic}")
        print(f"🎭 Emotion:    {cell.emotion}")
        print(f"🧪 Prediction: {cell.prediction}")
        print(f"📊 SQI:        {cell.sqi_score}")
        print(f"🧬 Mutation:   type={getattr(cell, 'mutation_type', 'n/a')} | score={getattr(cell, 'mutation_score', 'n/a')}")
        print(f"🕰 Timestamp:  {getattr(cell, 'mutation_timestamp', 'n/a')}")
        print(f"⬅️  Parent:     {getattr(cell, 'mutation_parent_id', None)}")

        lineage.append(cell)
        visited_ids.add(current_id)
        current_id = getattr(cell, 'mutation_parent_id', None)
        steps += 1

    print(f"\n✅ Lineage traversal complete. {len(lineage)} steps visited.")
    return lineage

# 🥵 Convert logic string into simplified glyphs
def parse_logic_to_glyphs(logic: str) -> List[Dict[str, str]]:
    raw_tokens = tokenize_symbol_text_to_glyphs(logic)
    normalized = []

    for token in raw_tokens:
        token_type = token["type"]
        value = token["value"]

        if token_type == "bracket":
            token_type = "paren"
        elif token_type == "variable" and value in {"sin", "cos", "tan", "log", "exp"}:
            token_type = "function"

        normalized.append({"type": token_type, "value": value})

    return normalized


# 🧠 Pattern detector using glyph comparison
def detect_patterns(logic: str) -> List[str]:
    try:
        glyphs = logic if isinstance(logic, list) else parse_logic_to_glyphs(logic)
        preprocessed = []

        for g in glyphs:
            if g.get("type") == "symbol" and isinstance(g.get("text"), str):
                tokenized = tokenize_symbol_text_to_glyphs(g["text"])
                preprocessed.extend(tokenized)
            else:
                preprocessed.append(g)

        patterns = load_pattern_registry()
        matched = []

        print(f"🌟 Detecting patterns in container: unknown")
        print(f"📦 Input glyphs: {glyphs}")
        print(f"🔄 Normalized glyphs: {preprocessed}")
        print(f"📚 Loaded {len(patterns)} patterns in registry\n")

        for i, pattern in enumerate(patterns):
            pattern_name = pattern.get("name", f"unnamed_{i}")
            pattern_glyphs = pattern.get("glyphs", [])

            print(f"🔍 [{i}] Checking pattern: {pattern_name}")
            print(f"🔘 Pattern glyphs: {pattern_glyphs}")
            print(f"🔘 Target glyphs:  {preprocessed}")

            if len(pattern_glyphs) != len(preprocessed):
                print(f"❌ NO MATCH: {pattern_name} (length mismatch)\n")
                similarity = difflib.SequenceMatcher(None, str(pattern_glyphs), str(preprocessed)).ratio()
                if 0.5 < similarity < 0.75:
                    suggestions = suggest_pattern_repairs(" ".join(g["value"] for g in preprocessed if "value" in g))
                    for s in suggestions:
                        print(f"🛠 Suggested patch for near-match ({pattern_name}): {s['issues']} → {s['patch']}")
                continue

            match = all(
                pattern_glyph.get("type") == glyph.get("type") and
                (pattern_glyph.get("value") is None or pattern_glyph.get("value") == glyph.get("value"))
                for pattern_glyph, glyph in zip(pattern_glyphs, preprocessed)
            )

            if match:
                matched.append(pattern_name)
                print(f"✅ MATCHED: {pattern_name}\n")
            else:
                print(f"❌ NO MATCH: {pattern_name}\n")
                similarity = difflib.SequenceMatcher(None, str(pattern_glyphs), str(preprocessed)).ratio()
                if 0.5 < similarity < 0.75:
                    suggestions = suggest_pattern_repairs(" ".join(g["value"] for g in preprocessed if "value" in g))
                    for s in suggestions:
                        print(f"🛠 Suggested patch for near-match ({pattern_name}): {s['issues']} → {s['patch']}")

        print(f"🌟 Final matched patterns: {matched}")
        return matched

    except Exception as e:
        print(f"[Error] Pattern detection failed: {e}")
        return []


# 🔍 Simple glyph sequence matcher (strict match)
def glyph_match(pattern: List[Dict[str, str]], target: List[Dict[str, str]]) -> bool:
    if len(pattern) != len(target):
        return False
    for p, t in zip(pattern, target):
        if p["type"] != t["type"]:
            return False
        if "value" in p and "value" in t and p["value"] != t["value"]:
            return False
    return True

# ─────────────────────────────────────────────────────────────────────────────
# Minimal shim class expected by API routes/tests
# Provides: SymbolicSpreadsheet.from_dict(...), .execute_sheet(...)
# Returns executed List[GlyphCell] so callers can iterate and cell.to_dict()
# ─────────────────────────────────────────────────────────────────────────────
class SymbolicSpreadsheet:
    def __init__(self, cells: List[GlyphCell], metadata: Optional[Dict] = None):
        self.cells: List[GlyphCell] = cells
        # accept both "metadata" and legacy "meta"
        self.metadata: Dict[str, Any] = metadata or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolicSpreadsheet":
        # Be permissive: validate if schema available, but don't hard-fail here
        try:
            # Prefer ATOM schema; falls back to SQS if present
            if "cells" in data:
                try:
                    validate(instance=data, schema=ATOM_SHEET_SCHEMA)  # type: ignore[arg-type]
                except Exception:
                    # try legacy SQS schema if present
                    try:
                        validate(instance=data, schema=SQS_SCHEMA)  # type: ignore[arg-type]
                    except Exception:
                        pass
        except Exception:
            pass

        meta = data.get("metadata") or data.get("meta") or {}
        cells_data = data.get("cells") or []

        cells: List[GlyphCell] = []
        for entry in cells_data:
            try:
                cells.append(GlyphCell.from_dict(entry))
            except Exception:
                # Very defensive fallback for partial entries
                cells.append(
                    GlyphCell(
                        id=str(entry.get("id", f"cell_{len(cells)}")),
                        logic=str(entry.get("logic", "")),
                        position=entry.get("position", [0, 0, 0, 0]),
                    )
                )

        return cls(cells=cells, metadata=meta)

    def execute_sheet(self, context: Optional[Dict] = None) -> List[GlyphCell]:
        """
        Execute the sheet in-place using the module-level pipeline (already imported above).
        Returns the (now executed) list of GlyphCell instances.
        """
        # Reuse the module's execute_sheet(cells, context) function
        try:
            execute_sheet(self.cells, context=context)  # type: ignore[misc]
        except Exception as e:
            record_trace("SymbolicSpreadsheet", f"[Execute Error] {e}")
            raise
        return self.cells

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "cells": [c.to_dict() if hasattr(c, "to_dict") else {
                "id": c.id,
                "logic": getattr(c, "logic", ""),
                "position": getattr(c, "position", [0, 0, 0, 0]),
                "emotion": getattr(c, "emotion", None),
                "prediction": getattr(c, "prediction", None),
            } for c in self.cells],
        }

# 🤪 CLI runner
if __name__ == "__main__":
    path = "example_sheet.atom"  # 🧬 Canonical AtomSheet format
    sheet = load_sqd_sheet(path)
    execute_sheet(sheet)

    # 🪞 Mutation Lineage Replay
    if sheet:
        last_id = sheet[-1].id
        replay_mutation_lineage(sheet, start_cell_id=last_id, step_limit=5)

    # 🖨️ Print Cell Results
    for cell in sheet:
        print("📄 ------------------------")
        print(f"🆔 ID:        {cell.id}")
        print(f"🤮 Logic:     {cell.logic}")
        print(f"📌 Position:  {cell.position}")
        print(f"💡 Emotion:   {cell.emotion}")
        print(f"🔮 Prediction:{cell.prediction}")
        print(f"📊 SQI:       {cell.sqi_score}")
        print(f"✅ Validated: {cell.validated}")
        print(f"⚙️ Result:    {cell.result}")
        print(f"📈 Trace:     {cell.trace}")
        print(f"📌 Linked:    {cell.linked_cells}")
        print(f"📂 Nested:    {cell.nested_logic}")
        print("")