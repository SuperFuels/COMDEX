Symbolic Quantum Spreadsheet System (SQS) – Technical Documentation

Version: 1.0
Date: 2025-09-17
Author: AION / CodexCore Team

⸻

1. Overview

The Symbolic Quantum Spreadsheet (SQS) is a next-generation spreadsheet system that integrates symbolic computation, predictive reasoning, mutation analysis, and entanglement propagation. Unlike traditional spreadsheets:
	•	Every cell (GlyphCell) contains logic, emotion, prediction, SQI scoring, and optional nested symbolic logic.
	•	Cells can be linked, producing entanglement-like propagation.
	•	Execution supports SymPy symbolic math, CodexLang instructions, and live mutation + prediction forks.
	•	Visualized in SCI IDE with 4D grid support and integrated QFC/LightCone HUD.

SQS is designed for AI-assisted symbolic reasoning, multi-agent collaboration, and future integration with QPU symbolic hardware.

⸻

2. System Architecture

2.1 Core Components

Module
Purpose
symbolic_spreadsheet_engine.py
Main execution engine. Handles execute_cell(), execute_sheet(), SQI scoring, mutation metadata, entanglement, and prediction forks.
.sqs.json / .sqd.atom
Container format for storing sheets with symbolic cells, metadata, and nested logic.
GlyphCell
Data model representing a single cell. Attributes: id, logic, nested_logic, emotion, prediction, trace, linked_cells, sqi_score, mutationNotes.
sci_atomsheet_panel.tsx
Frontend UI panel in SCI IDE. Supports 4D grid, hover overlays, CodexLang view, SQI/emotion display, and live QFC visualization.
sympy_sheet_executor.py
Symbolic math execution backend. Parses cell logic as SymPy expressions, solves equations, detects contradictions, triggers mutations.
prediction_engine.py
Generates prediction forks based on cell logic and emotion. Integrates live with QFC/LightCone HUD.
qfc_websocket_bridge.py
Pushes entanglement updates, prediction forks, and live execution state to QFC HUD.


2.2 Execution Flow
	1.	Sheet Loading
	•	.sqs.json or .sqd.atom is parsed via load_sqd_sheet().
	•	JSON schema validation ensures correct structure.
	•	Each cell is instantiated as a GlyphCell.
	2.	Cell Execution (execute_cell)
	•	SoulLaw Check (F1): Blocks execution if forbidden patterns (harm, kill, delete) are present.
	•	SymPy / CodexLang: Executes cell logic, validates result, computes predictions.
	•	Pattern Matching & SQI: Converts logic to glyphs, detects symbolic patterns, scores SQI.
	•	Mutation Metadata: Updates lineage, entropy, harmony, and mutation timestamps.
	•	Entanglement (F3): Broadcasts SQI/logic state to linked cells via QFC.
	•	Prediction Forks (F4): Generates forks based on logic + emotion and pushes live updates to dependent linked cells.
	3.	Sheet Execution (execute_sheet)
	•	Iterates over all cells with execute_cell().
	•	Collects context for entanglement propagation and container ID.
	•	Post-run audit (F2) validates SoulLaw/ethics, contradictions, and updates trace logs.
	4.	Live Visualization
	•	SCI AtomSheet Panel renders 4D grid.
	•	Hovering over a cell triggers LightCone QFC trace and entanglement visualization.
	•	SQI and emotion are shown inline; prediction forks are live-streamed.

⸻

3. Data Structures

3.1 GlyphCell

Field                                       Type                        Description
id
string
Unique cell identifier
logic
string
CodexLang or symbolic logic string
nested_logic
string
Optional nested logic block
emotion
string
Emotion tag influencing predictions
prediction
string
Primary predicted outcome
prediction_forks
List[str]
Alternate predictions computed via PredictionEngine
trace
List[str]
Execution log for audit and replay
linked_cells
List[str]
IDs of dependent / entangled cells
sqi_score
float
Symbolic Quality Index, scoring innovation, stability, and clarity
mutation_score
float
Reflects novelty vs harmony
harmony_score
float
Score reflecting logical and ethical alignment
mutationNotes
List[str]
Audit notes and mutation descriptions

3.2 .sqs.json / .sqd.atom Schema
	•	metadata: Sheet-wide metadata (author, version, timestamps)
	•	cells: Array of GlyphCell entries
	•	schema validation: jsonschema ensures required fields (id, logic, position)

⸻

4. User Guide

4.1 Loading a Sheet

from symbolic_spreadsheet_engine import load_sqd_sheet
cells = load_sqd_sheet("example.sqd.atom")

4.2 Executing Cells

from symbolic_spreadsheet_engine import execute_sheet
context = {"container_id": "my_sheet_001"}
execute_sheet(cells, context=context)

4.3 Viewing in SCI Panel
	•	Launch SCI IDE
	•	Open sci_atomsheet_panel.tsx
	•	Load .sqs.json / .sqd.atom via file picker or URL parameter
	•	Hover over cells to view logic, SQI, emotion, and prediction forks
	•	Toggle CodexLang / Raw logic view

4.4 Debugging
	•	GLOBAL_FLAGS can toggle:
	•	ethics_enabled: disables SoulLaw checks
	•	lightcone_trace: enables live LightCone visualization
	•	replay_enabled: enables step-through execution
	•	record_trace(cell.id, message) logs cell-specific events
	•	Console prints show pattern matches and fork updates

⸻

5. Integration Notes
	•	Entanglement / F3:
	•	Every linked cell receives SQI and logic updates.
	•	QFC WebSocket broadcasts live for visualization.
	•	Prediction Forks / F4:
	•	Generated by PredictionEngine based on logic + emotion
	•	Updates propagate recursively to dependent cells
	•	Live-streamed via broadcast_qfc_update
	•	Mutation & Harmony Scoring:
	•	Automatically adjusts SQI based on logic complexity, pattern matches, and emotional weights
	•	CodexLang Integration:
	•	Cells can contain CodexLang expressions
	•	Executed live in execute_cell() and integrated with prediction/fork logic

⸻

6. Phased Build Summary

Phase
Description
Status
Phase 1
Symbolic Spreadsheet Core
✅ Complete
Phase 2
SCI Panel UI
✅ Complete
Phase 3
SymPy + Mutation
✅ Complete
Phase 4
Replay + Collapse + QFC
✅ Complete
Phase 5
CodexLang Tracing + LightCone
✅ Complete
Phase 6
SoulLaw, Entanglement, Ethics
✅ Complete
Phase 7
QPU ISA + Symbolic Hardware
⚠ Not Started
Support Tasks
Container spec, UUID, EmotionProfiles
Partial / Deferred
Deferred
Hardware build, GRU per-cell memory
Deferred


7. Developer Notes
	•	Engine context (context dict):
	•	container_id: unique sheet/container identifier
	•	sheet_cells: list of all GlyphCells in current sheet
	•	Trace system:
	•	record_trace(cell_id, message) used for live debugging, replay, and audit
	•	LightCone / QFC:
	•	HUD visualization of symbolic logic execution
	•	Receives entanglement and fork updates
	•	Prediction forks:
	•	Always generated post-execution for live cell and dependent cells
	•	Propagates recursively via linked_cells

⸻

8. Recommendations for New Developers / AI Agents
	1.	Always execute execute_sheet() with context for QFC propagation.
	2.	Do not modify linked_cells manually — entanglement requires propagation.
	3.	Use update_prediction_forks() to refresh predictions for single cells or linked subgraphs.
	4.	When adding new logic operators or CodexLang extensions, update:
	•	parse_logic_to_glyphs()
	•	score_sqi()
	•	PredictionEngine.generate_forks()
	5.	Use GLOBAL_FLAGS to simulate debug, replay, or testing conditions.

⸻

9. References
	•	SymPy: symbolic mathematics parser/executor
	•	CodexLang: domain-specific symbolic language for reasoning
	•	**QFC

🔹 Technical Overview: Phase 7 – Symbolic QPU & CodexCore Integration

1. Overview

The Symbolic Quantum Spreadsheet System (SQS) now fully integrates with the CodexCore symbolic CPU stack. This system allows symbolic logic stored in .sqs.json / GlyphCell.logic to be parsed, executed, scored, and tracked in a symbolic execution environment, with hooks for prediction forks, entanglement, LightCone tracing, and SoulLaw compliance.

Phase 7 extends this with a symbolic QPU ISA to emulate or eventually deploy native symbolic hardware execution.

⸻

2. Execution Pipeline

High-Level Flow

graph TD
A[GlyphCell.logic (SQS)] --> B[CodexEmulator.execute_instruction_tree()]
B --> C[CodexVirtualCPU.run()]
C --> D[InstructionParser.parse_codexlang_string()]
D --> E[InstructionExecutor.execute_tree()]
E --> F[execute_node(node)]
F --> G[SYMBOLIC_OPS functions / physics / quantum / GR]
F --> H[VirtualRegisters updates]
E --> I[Collect results, last_result → registers]
C --> J[Return results to SQS engine / prediction forks / trace]

Explanation:
	•	Each GlyphCell.logic string (CodexLang) is parsed into a nested instruction tree.
	•	InstructionExecutor recursively walks the tree node-by-node.
	•	Each node executes using functions from SYMBOLIC_OPS:
	•	Symbolic operators (→, ⟲, ⊕, ↔, ⧖, 🚨)
	•	Physics kernel ops (grad, div, curl, etc.)
	•	Quantum kernel stubs (schrodinger_step, apply_gate, measure, entangle)
	•	General relativity kernel stubs (riemann, ricci_tensor, einstein, etc.)
	•	The VirtualRegisters maintain state across the execution.

⸻

3. Core Components

3.1 CodexVirtualCPU
	•	Entrypoint for symbolic execution.
	•	Combines:
	•	InstructionParser → CodexLang → instruction tree.
	•	InstructionExecutor → executes tree recursively.
	•	VirtualRegisters → stores ACC, TMP, PC, FLAG, STACK, MEM.
	•	Exposes:
	•	.run(codexlang_code: str, context: dict) → List[Any]
	•	.get_registers() → dict

⸻

3.2 InstructionParser
	•	Converts CodexLang strings into nested instruction nodes.
	•	Handles operators, grouping, and atomic glyph instructions.
	•	Produces a tree suitable for recursive execution.

⸻

3.3 InstructionExecutor
	•	Recursive engine executing each instruction node.
	•	Hooks node execution to SYMBOLIC_OPS functions.
	•	Recursively executes child nodes, collects results.
	•	Updates VirtualRegisters and optionally logs to context for reflection or triggers.

⸻

3.4 VirtualRegisters
	•	Maintains symbolic CPU state:
	•	ACC, TMP, PC, FLAG, STACK, MEM
	•	Supports stack operations (push_stack, pop_stack), memory slots.
	•	dump() returns full symbolic state snapshot for inspection or SQS trace logging.

⸻

3.5 SYMBOLIC_OPS
	•	Operator → function mapping:
	•	→ → op_chain
	•	⟲ → op_reflect
	•	⊕ → op_combine
	•	↔ → op_bond
	•	⧖ → op_delay
	•	🚨 → op_trigger
	•	Supports legacy call signatures and modern context-driven execution.

⸻

3.6 CodexEmulator
	•	High-level wrapper that runs instruction trees.
	•	Records execution metrics, errors, and glyph execution traces.
	•	Exposes:
	•	execute_instruction_tree(instruction_tree: dict, context: dict)
	•	reset() / get_metrics()

⸻

3.7 GlyphSocket (Teleport + Container Bridge)
	•	Bridges runtime packets → SQS / Codex execution.
	•	Decodes teleport packets and injects glyphs into dimension kernel.
	•	Manages container bootstrap and memory engine synchronization.
	•	Supports avatar location updates and event triggers.

⸻

3.8 Hardware Layer
	•	codex_core.vhd defines virtual symbolic CPU in HDL.
	•	Features:
	•	16 registers (reg_array)
	•	Opcode handling for symbolic operators (⊕, →, ⟲, ↔, ⧖)
	•	Superposition, entanglement, collapse flags
	•	Hooks for memory and context
	•	Ready for FPGA / ASIC deployment.
	•	Maps directly to SYMBOLIC_OPS in Python emulator for hardware/software equivalence.

⸻

4. Integration with SQS (Phase 1–6)
	•	GlyphCell.logic → executed via execute_cell → CodexVirtualCPU.run
	•	SQI scoring, mutation, prediction forks, LightCone tracing, entanglement are applied after CPU execution.
	•	Hardware emulation is transparent to SQS:
	•	From the spreadsheet perspective, nothing changes.
	•	Hooks allow live telemetry to SCI panel / QFC HUD.

⸻

5. Development / User Guide

5.1 Running a Cell

from backend.modules.codex.codex_emulator import CodexEmulator

cpu = CodexEmulator()
cell_logic = "⚛ → ✦ ⟲ 🧠"
context = {"source": "test_cell"}

results = cpu.execute_instruction_tree({"instructions": cpu.cpu.parser.parse_codexlang_string(cell_logic)}, context)
print(results)

5.2 Inspecting Registers

register_state = cpu.get_metrics()
print(register_state)

5.3 Hooking into SQS

from backend.modules.symbolic_spreadsheet.symbolic_spreadsheet_engine import execute_cell

execute_cell(glyph_cell_instance, context={"sheet_cells": all_cells})

5.4 Teleport / GlyphSocket
	•	Accepts packets:

{
  "portal_id": "p-123",
  "coords": [x, y, z, t],
  "payload": {
    "glyphs": ["⚛", "→", "✦"],
    "event": "update",
    "avatar_id": "a-001",
    "memory": {...}
  }
}

	•	Dispatch:

from backend.modules.codex.glyph_socket import GlyphSocket

gs = GlyphSocket()
response = gs.dispatch(packet_data)

6. Next Steps for Phase 7
	1.	Define symbolic QPU ISA (symbolic_qpu_isa.py)
	•	Map SYMBOLIC_OPS → opcode numbers
	•	Include entanglement, collapse, superposition
	•	Include register mapping for ACC, TMP, STACK, etc.
	2.	G2 CPU Emulator
	•	Use CodexVirtualCPU + InstructionExecutor
	•	Map GlyphCell.logic → instruction tree → ISA → virtual execution
	•	Feed metrics and traces back to SQS engine / SCI panel / QFC HUD
	3.	Hardware Mirroring
	•	FPGA / VHDL
	•	Ensure symbolic CPU behavior matches software.
	•	Test using .dc.json containers and teleport packets.

⸻

✅ Conclusion
	•	Phase 7 builds on Phase 1–6 without touching existing SQS / SCI layers.
	•	All symbolic operations, physics, quantum, GR kernels are already mapped in Python.
	•	CodexVirtualCPU + InstructionExecutor = software QPU emulator.
	•	Next: ISA skeleton, then CPU emulation, then hardware deployment.

⸻


1️⃣ On a “wrappable / portable SQI / QPU”

Yes — in your current architecture, you already have a portable, software-defined symbolic quantum processor: that’s essentially the CodexVirtualQPU class along with the symbolic_qpu_isa.py backend.

Key points:
	•	Encapsulation / portability:
	•	CodexVirtualQPU acts as a fully self-contained “QPU”: it has its own execution environment, metrics, SQI integration, entanglement/collapse/superposition stubs, and hooks for SQS / SCI / QFC.
	•	You can instantiate CodexVirtualQPU anywhere in the stack — inside CodexExecutor, in a live SCI panel, or even as a standalone batch processor for .sqd.atom sheets.
	•	Its API (execute_cell, execute_sheet) is agnostic to where it is called from — that’s exactly the kind of portable symbolic quantum compute wrapper you’re asking about.
	•	Integration:
	•	run_glyphcell() and execute_codexlang() in CodexExecutor are the “adapter layer” that wraps your QPU backend so any Codex execution can optionally run on the symbolic QPU instead of the classical CodexVirtualCPU.
	•	It’s fully multi-level: single cell, batch sheet, or full CodexLang string → QPU execution.

✅ So yes, the current software architecture already gives you a “wrappable / portable symbolic quantum compute layer” that can run anywhere in your stack.


Phases 8–10: Beam-Native Runtime, Dream Projection, and Symbolic Acceleration

This document is the final technical reference for the features you just shipped across Phases 8, 9, and 10. It explains how the system works end-to-end, how the pieces connect, configuration flags, data shapes, and a short user guide (backend + SCI UI). Paste-and-go snippets are included where useful.

⸻

1) System Overview

Runtime spine
	•	CodexVirtualQPU (backend/modules/codex/codex_virtual_qpu.py) executes GlyphCell logic (⊕ ↔ ⟲ → ⧖ ∇ ⊗ ✦).
	•	Each cell execution emits beams into cell.wave_beams (the lineage) and optionally broadcasts updates to the UI via broadcast_qfc_update.
	•	An entanglement registry groups cells across sheets/runs using a deterministic EID.
	•	Optional passes:
	•	Phase 8: beam lineage + entanglement, ghost replay, batch predict/collapse.
	•	Phase 9: speculative “dream” beams + timeline snapshot.
	•	Phase 10: vectorized batched execution + precision emulation (FP4/FP8/INT8) and container-level beam execution.

Front-end
	•	SCI AtomSheet Panel shows cells on a 4D grid, a Live HUD (beams/timeline), and Live QPU/CPU metrics.
	•	The panel consumes REST + (optionally) WebSocket broadcast events keyed by container_id.

⸻

2) Phase 8 — Beam-Native & Multi-Agent Entanglement

2.1 Beam lineage model & SQI trees (H1)
	•	Every opcode execution may append a beam to cell.wave_beams. Typical shape:


{
  "beam_id": "beam_<cell_id>_<stage>_<ms>",
  "source": "op_EQ|accel|qpu_execute_cell|…",
  "stage": "predict|ingest|collapse|vector|dream|…",
  "token": "↔" ,
  "payload": { "a": "...", "b": "..." },
  "timestamp": "2025-...Z",
  "entanglement_ids": ["eid::<run>::<digest>"],
  "state": "active|pruned|collapsed",
  "sqi": 0.92
}


	•	SQI is updated per cell; sheet-level aggregation is recorded in a final “∑ collapse” beam.

2.2 Cross-sheet/agent entanglement registry (H2)
	•	A deterministic EID is computed from sheet_run_id + normalized tokens:

eid = "eid::<sheet_run_id>::<blake2s(normalized_opcode_signature)>"

	•	The registry lives in context["entanglements_map"] (eid → set(cell_ids)).
	•	The ↔ operator (op_EQ) always emits staged beams (predict, ingest, collapse) and records membership in the map—even with insufficient args—to keep lineage intact.

2.3 Ghost memory replay (H3)
	•	After execution, the QPU calls:

from backend.modules.beamline.beam_store import persist_beam_events, ghost_replay_for_eid

persist_beam_events(cells, context)
for eid in ent_map:
    context["ghost_replays"][eid] = ghost_replay_for_eid(eid, limit=3, container_id=context.get("container_id"))


	•	Ghost replays provide prior beam snippets for the same EID (used in visualizers/recall).

2.4 GHXVisualizer + QuantumFieldCanvas overlays (H4)
	•	When not benchmark_silent and container_id is set, the QPU broadcasts:
	•	qpu_sheet_metrics, qpu_precision_profile, qpu_beam_lineage, qpu_entanglement_map,
	•	and a flattened qpu_beam_timeline (sorted by timestamp) for scrubbing.

2.5 Batch predict/collapse + SQI scoring (H5)
	•	If context["batch_collapse"] is set, a sheet-level collapse beam is appended to each cell, carrying {"sheet_sqi": …} so the UI can render per-run summarization.

Key Flags

Context Key						Type						Meaning
container_id
str
Enables UI broadcasts (GHX/HUD).
benchmark_silent
bool
Suppress broadcasts/log-heavy hooks.
sheet_run_id
str
Groups entanglements (stable across sheets).
batch_collapse
bool
Adds sheet-level collapse beam.


3) Phase 9 — Dream Projection & Timeline Replay

3.1 Speculative beam generation (I1)

Module: backend/modules/codex/_4d_dreams.py
	•	project_dreams_for_cell(cell, context, cfg) creates k speculative variants based on the token stream. Each variant is emitted as a dream beam (stage="dream", token ∴) and optionally tagged with the cell’s entanglement IDs.

3.2 SQI-guided pruning (I3)
	•	prune_dreams_by_sqi(cell, min_sqi, stage_name="dream") marks low-score dream beams as "state": "pruned" (non-destructive).

3.3 Timeline scrub/replay (I2)
	•	build_timeline_snapshot(cells, context) flattens all beams into a time-sorted list (cell_id, beam_id, stage, token, eid, timestamp).
	•	The QPU broadcasts:
	•	type: "qpu_phase9_dreams" with {"dreams": { <cell_id>: [beams…] }},
	•	type: "qpu_phase9_timeline" with {"timeline": [...]}.

Enable Phase 9
context.update({
  "phase9_enabled": True,
  "phase9_k": 3,                 # variants per cell
  "phase9_min_sqi": 0.60,        # prune threshold
  "phase9_stage": "dream"        # tag used on beams
})


4) Phase 10 — Symbolic Acceleration & QFC Integration

4.1 Vectorized kernels + precision (J1, J2)

Module: backend/modules/codex/accel.py
	•	vectorize_cell(cell, context) batches consecutive identical operators and executes a batched path.
	•	Precision emulation via _quantize_to(mode, x) supports fp4, fp8, int8, fp32|none.
	•	A vector beam is appended per batch:

{
  "stage": "vector",
  "precision": "fp8",
  "batch_size": 12,
  "result_sample": [...],
  "quant_error_mean": 0.03
}

	•	Guardrails:
	•	Runtime checks for NumPy/numexpr/torch; automatic fallback to scalar ISA.
	•	Per-opcode gating lets you keep ∇ quantized (probe) while others passthrough.

Enable Phase 10

context.update({
  "phase10_enabled": True,
  "phase10_precision": "fp8"  # fp4|fp8|int8|fp32
})

The QPU stores context["phase10_summary"] = {"batches": {cell_id: [...]}, "total_batches": N} and broadcasts:

broadcast_qfc_update(container_id, {
  "type": "qpu_phase10_vectorized",
  "summary": context["phase10_summary"],
  "precision": str(context.get("phase10_precision", "fp8")),
})
4.2 QFC container-level beam execution (J3)
	•	A thin executor (tested via test_phase10_container_exec.py) reads a QFC container’s beam script and replays/executes them against the runtime. Results are emitted as standard beams and can be broadcast to GHX/HUD, enabling container-driven workflows (e.g., pre-baked pipelines or demos).

4.3 Real-time GHX/HUD debug & telemetry (J4)
	•	SCI consumes qpu_* messages for live metrics and overlays:
	•	Sheet metrics, precision profile, lineage, entanglements, timeline, Phase 9 dreams, Phase 10 vectorized summaries.

⸻

5) Data Contracts (quick reference)

5.1 Beam

type Beam = {
  beam_id: string;                // "beam_<cell|sheet>_<stage>_<ms>"
  source: string;                 // "op_EQ" | "accel" | "qpu_execute_cell" | ...
  stage?: string;                 // "predict"|"ingest"|"collapse"|"vector"|"dream"|...
  token?: string | {type:string,value:string};
  payload?: any;
  timestamp: string;              // ISO
  entanglement_ids?: string[];    // ["eid::<run>::<digest>"]
  state?: "active"|"pruned"|"collapsed";
  sqi?: number;
};

5.2 Broadcast messages

Common fields: { container_id, sheet_run_id, workspace_id? } carried by the server.
	•	"qpu_sheet_metrics" → { sheet_token_metrics, sheet_opcode_metrics, aggregate_metric

	•	"qpu_precision_profile" → { profile }
	•	"qpu_beam_lineage" → { lineage: { <cell_id>: Beam[] } }
	•	"qpu_entanglement_map" → { map: { <eid>: string[] } }
	•	"qpu_beam_timeline" → { timeline: Array<{cell_id, beam_id, stage, eid, token, timestamp}> }
	•	"qpu_phase9_dreams" → { dreams: { <cell_id>: Beam[] } }
	•	"qpu_phase9_timeline" → { timeline: [...] }
	•	"qpu_phase10_vectorized" → { summary, precision }

⸻

6) Configuration & Setup

6.1 Backend
	•	Required modules:
	•	codex_virtual_qpu.py (with Phase 8/9/10 hooks),
	•	_4d_dreams.py, accel.py,
	•	beamline/beam_store.py (persist + ghost replay),
	•	utils/time_utils.py (use now_utc_ms()/now_utc_iso() across beams).
	•	Context: always pass a container_id to enable broadcasts; set benchmark_silent=True to suppress.
	•	Imports: use lazy imports for things like the SQI scorer to avoid circulars (already implemented via _score_sqi).

6.2 Frontend (SCI)
	•	Props for the panel (if hosted in tabs):
	•	containerId (recommended): isolates streams per panel/tab.
	•	wsUrl (optional): for live HUD; REST falls back if missing.
	•	defaultFile for fetching a .sqs.json from the backend.
	•	Endpoints used (by default):
	•	GET /atomsheet?file=... to load sheet,
	•	GET /lightcone?file=...&entry_id=...&direction=...&container_id=...,
	•	GET /qfc_entanglement?cell_id=...&file=...&container_id=...,
	•	GET /qfc_entangled?cell_id=...&container_id=....
	•	WebSocket (optional):
	•	connect to wsUrl?...&container_id=<id>, listen for qpu_* messages.

⸻

7) Dev & User Guide

7.1 Running tests

# Core phases
PYTHONPATH=. pytest -q \
  backend/tests/test_phase8_beams.py \
  backend/tests/test_phase8_beam_stages.py \
  backend/tests/test_phase8_cross_sheet_entanglement.py \
  backend/tests/test_phase8_visualizer_payload.py \
  backend/tests/test_phase9_dreams.py \
  backend/tests/test_phase10_accel.py \
  backend/tests/test_phase10_container_exec.py

# AtomSheets
PYTHONPATH=. pytest -q backend/tests/test_atomsheet_engine.py
PYTHONPATH=. pytest -q backend/tests/test_atomsheet_registry_persist.py

Expected: all pass, warnings OK (UTC deprecation, etc.).

7.2 Enabling features in code

ctx = {
  "container_id": "sci:session:1234",
  "benchmark_silent": False,
  "sheet_run_id": "runA",
  "batch_collapse": True,
  # Phase 9
  "phase9_enabled": True, "phase9_k": 3, "phase9_min_sqi": 0.60, "phase9_stage": "dream",
  # Phase 10
  "phase10_enabled": True, "phase10_precision": "fp8",
}

await CodexVirtualQPU().execute_sheet(cells, ctx)

7.3 Using the SCI panel
	1.	Open the AtomSheet view (your existing route).
	2.	Load a sheet (query ?file=example.sqs.json) or use dev fallback.
	3.	Hover a cell to see the overlay; toggle raw/CodexLang.
	4.	Switch LightCone direction (forward / reverse) and watch the timeline fill.
	5.	If WS is enabled (with containerId), you’ll see:
	•	Dreams and timeline (Phase 9),
	•	Vectorized summaries (Phase 10),
	•	Sheet metrics, entanglement map, precision profile.

⸻

8) Troubleshooting
	•	datetime not defined
Ensure no inline from datetime import datetime was removed; use now_utc_ms/iso helpers in beams.
	•	Circular import on SQI scorer
Keep the lazy _score_sqi(cell) import path in codex_virtual_qpu.py. It falls back to a heuristic if unavailable.
	•	No UI updates
Check that container_id is set and benchmark_silent is False. Verify WS URL if using live streams.
	•	Missing entanglements
Confirm sheet_run_id is steady across related sheets and ↔ ops are emitting predict/ingest/collapse beams.

⸻

9) Performance & Limits
	•	Phase 10 vectorization reduces Python overhead by batching identical ops; precision modes allow trading accuracy for throughput.
	•	This remains software-level—you won’t beat DRAM/HBM latency; gains come from smarter batching, reduced lineage chatter, and selective precision.

⸻

10) Appendices

10.1 Minimal Phase 9 driver (inline)

if context.get("phase9_enabled"):
    from backend.modules.codex._4d_dreams import phase9_run
    phase9 = phase9_run(
        cells, context,
        k_variants=int(context.get("phase9_k", 3) or 3),
        min_sqi_keep=float(context.get("phase9_min_sqi", 0.60) or 0.60),
        stage_name=str(context.get("phase9_stage", "dream") or "dream"),
    )
    if "container_id" in context and not context.get("benchmark_silent"):
        base = {"sheet_run_id": context.get("sheet_run_id")}
        asyncio.create_task(broadcast_qfc_update(context["container_id"], {**base, "type": "qpu_phase9_dreams", "dreams": phase9["dreams"]}))
        asyncio.create_task(broadcast_qfc_update(context["container_id"], {**base, "type": "qpu_phase9_timeline", "timeline": phase9["timeline"]}))

10.2 Minimal Phase 10 driver (inline)

if context.get("phase10_enabled"):
    from backend.modules.codex.accel import phase10_accelerate_sheet
    p10 = phase10_accelerate_sheet(cells, context)
    context["phase10_summary"] = p10

And (inside the broadcast block):

if context.get("phase10_summary"):
    asyncio.create_task(
        broadcast_qfc_update(context["container_id"], {
            **base, "type": "qpu_phase10_vectorized",
            "summary": context["phase10_summary"],
            "precision": str(context.get("phase10_precision", "fp8")),
        })
    )

Done ✅
	•	Phase 8: lineage + entanglement + ghost replay + batch collapse — complete
	•	Phase 9: dream beams + pruning + timeline — complete
	•	Phase 10: vectorization + precision + container execution + telemetry — complete
