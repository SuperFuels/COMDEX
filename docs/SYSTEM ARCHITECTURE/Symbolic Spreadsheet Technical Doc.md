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

    
