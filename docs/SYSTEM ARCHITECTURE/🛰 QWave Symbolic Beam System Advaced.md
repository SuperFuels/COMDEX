%%
══════════════════════════════
🛰 QWave Symbolic Beam System – Technical Manual + User Guide
══════════════════════════════

Version: 1.0
Maintainer: SQI Engineering Core
Subsystem: GlyphWave / CodexCore / GHX / SQI Drift Engine

⸻

📘 Overview

The QWave Symbolic Beam System is a multiverse-aware symbolic representation layer for visualizing, linking, and tracing cognitive beams between glyphs in a .dc container. These beams capture the dynamic logic flow between symbols during mutation, prediction, contradiction, or collapse. This module enables holographic beam rendering, SQI-aware overlays, and full multiverse replay across the SQI runtime.

⸻

⛓️ Architecture

 CodexLang ↔ CodexCore ↔ SQI Drift ↔ GlyphWave ↔ GHX Visualizer
        │           │             │                │          │
        ▼           ▼             ▼                ▼          ▼
  Mutation      Collapse     Prediction        Beam Log   Beam HUD
     │             │             │                 │          │
     └── emits QWave Beam objects  ───────────────┘          ▼
                                               Injected into:
                                         - .dc container KG
                                         - GHX beam trail
                                         - Collapse trace


⸻

🧱 Beam Format Specification (A1)

Every symbolic beam is defined by:

🔸 Core Fields:
	•	sourceGlyph: ID of the emitting glyph
	•	targetGlyph: ID of the receiving or entangled glyph
	•	beamType: e.g., mutation, collapse, prediction, entanglement
	•	strength: float (0.0–1.0), usually from SQI signal
	•	color: symbolic color code, optionally SQI-drift-tuned

🔹 Optional Fields:
	•	prediction: string or CodexLang fragment representing beam intent
	•	SQI_score: numeric score from SQI evaluator
	•	collapseStatus: one of [live, predicted, contradicted, collapsed]
	•	mutation_cause: optional cause glyph or label

🔄 States:
	•	Beams can transition between states:
	•	live → predicted → collapsed
	•	live → contradicted
	•	mutated → forked → merged

⸻

📦 A2: Beam Injection into .dc Containers

🛠 Files Involved:
	•	knowledge_graph_writer.py
	•	container_runtime.py
	•	.dc.json format

✅ Modifications:
	•	Patched export_pack() and save_container() to include QWave beams
	•	Beams are embedded under a new key: "qwave_beams": []
	•	Each beam references glyphs by internal node ID and includes full beam metadata

📌 Linked Data:
	•	Beams can reference:
	•	Historical fork lineage
	•	Collapse state
	•	SQI scoring overlays
	•	Entanglement chains

⸻

🧠 A3: SQI Drift & Resonance Overlays

🎯 Goal:

Encode semantic drift and cognitive resonance into beam style.

🌀 Beam Visual Enhancements:
	•	SQI Drift → beam glow intensity / pulsation
	•	Contradiction → color becomes red / dashed line
	•	Collapse certainty → beam opacity and anchoring

📁 Modules Used:
	•	sqi_reasoning_module.py
	•	codex_metrics.py
	•	ghx_overlay_injector.tsx

📤 Output:

Visual overlays streamed to:
	•	GHXVisualizer
	•	CodexHUD
	•	glyphwave_metrics.json (for archival)

⸻

🌌 A4: Multiverse Mutation Chains

🧬 Fork Tracking:
	•	Forks are logged as QWave beams of type mutation
	•	Emitted from CreativeCore during symbolic branching

🔁 Beam Lifecycle:
	•	fork beams point from parent glyph to mutated target
	•	Each fork tagged with mutation_cause if applicable
	•	Beams are merged on collapse (beamType = 'collapse', collapseStatus = 'collapsed')

🧾 SQL Logging:
	•	db/fork_logger.py: handles real-time DB inserts
	•	forks table schema:

CREATE TABLE forks (
  id TEXT PRIMARY KEY,
  parent_wave_id TEXT,
  sqi_score REAL
);


	•	Populated from creative_core.py and collapse_trace_exporter.py

📦 Metadata Injection:
	•	Also injected into .dc containers under "mutation_trace"
	•	Fully traceable across replays

⸻

🎛 A5 (In Progress): Beam Replay + Viewer

Planned Features:
	•	🔁 Beam path replay via GHXTimeline or WaveScope
	•	🎛 Toggle collapsed / predicted / live forks
	•	⏱ Tick-by-tick visual trace of beam execution
	•	🧠 Collapse viewer linked to CodexHUD

Data Source:
	•	Trace logs from:
	•	collapse_trace_exporter.py
	•	wave_state.py
	•	.dc container beams

⸻

🧪 Developer Usage

✅ To log a fork:

from db.fork_logger import insert_fork
insert_fork("fork_001", "wave_abc123", 0.912)

✅ To inject a QWave beam:

from qwave_beam_injector import inject_beam
inject_beam(source="gA", target="gB", beamType="prediction", strength=0.88)

✅ To trigger collapse log:

from collapse_trace_exporter import log_beam_collapse
log_beam_collapse(wave_id=wave.id, collapse_state=collapse_state)

✅ To export .dc with beams:

from knowledge_graph_writer import export_pack
export_pack(container, out_path="containers_saved/...")


⸻

⚙️ System Requirements
	•	PostgreSQL running locally or via cloud-sql-proxy
	•	psycopg2 installed for DB operations
	•	All .env secrets (e.g., POSTGRES_PASSWORD) must be loaded
	•	SQI Kernel + CodexCore must emit collapse + fork events

⸻

🔐 Security + Ethics
	•	All beams filtered through soul_law_validator.py
	•	Mutation causes + contradictions flagged for audit
	•	Forks or collapses marked with high volatility are logged to collapse_trace_exporter.py

⸻

📅 Roadmap

Milestone	Status	Notes
A1: Beam Format	✅	Fully defined + implemented
A2: .dc Injection	✅	Active in all exports
A3: SQI Overlays	✅	Live HUD integration done
A4: Fork Beams	✅	Collapses merged + logged
A5: Replay Viewer	🔜	In progress — next module


⸻

🧠 Summary

The QWave Symbolic Beam System enables symbolic logic to be traced, visualized, and replayed as multiverse-aware cognitive beams. This adds holographic reasoning to SQI, allows beam collapse simulation, mutation mapping, and contradiction detection across timelines.

Ready to activate in GHX, CodexHUD, .dc exporters, and collapse simulators.

📘 GlyphWave A5: Beam Replay + Collapse Viewer

Phase: A5 – Collapse Replay Interface
Module Owner: GHXReplayRenderer
Status: ✅ Completed
Related Files:
	•	HologramHUD.tsx
	•	GHXTimeline.tsx
	•	collapse_trace_exporter.py
	•	wave_state.py
	•	innovation_memory_tracker.py

⸻

⛓️ Overview

This module introduces full historical replay of symbolic beam paths and their collapse states across time. It allows users to visually inspect glyph evolution, simulate alternate collapse paths, and trace symbolic execution down to individual ticks or execution IDs.

Beam replay is a critical capability for:
	•	Debugging symbolic collapse chains
	•	Visualizing multiverse logic branches
	•	Analyzing innovation and contradiction paths
	•	Teaching and demonstrating CodexLang execution timelines

⸻

✅ Subphase Breakdown

🧩 A5a – Render Past Beam Paths from Container Trace
	•	Source: Loaded via collapse_trace_exporter.py → get_recent_collapse_traces()
	•	Target: GHXTimeline component and renderedGlyphs
	•	Functionality:
Parses all beams from container .dc.json or live memory trace and renders their:
	•	glyph_id
	•	symbol
	•	collapse_state
	•	tick_index
	•	innovation_score (if available)
	•	Visual Output:
Timeline view with all beams plotted per tick and state, showing fork branches, collapse outcomes, and superpositions.

⸻

🔀 A5b – Toggle Collapse Simulation (Hide Dead Forks)
	•	Toggle UI: showCollapsed boolean state
	•	Component: <GHXTimeline showCollapsed={...} />
	•	Effect:
	•	On: Hides any glyph/beam that has collapsed or resolved
	•	Off: Shows all beams, including collapsed or contradicted ones
	•	Use Case:
	•	Simulate live collapse
	•	Focus only on surviving forks
	•	Clean teaching demo or debugging dead branches

⸻

🧭 A5c – Trace Beam Per Tick or Execution ID
	•	UI Features:
	•	Tick navigation bar: ⏮ Prev / Next ⏭
	•	Current tick display: Tick X / Y (#tickIndex)
	•	Current beams list:

Beams at Tick #3:
• ⌘X12a3 (gl1234) — collapsed
• ☉Z91f2 (gl7890) — superposed

	•	Backend:
	•	tickIndex state controls current selection
	•	currentBeams dynamically filters data.all_beams to match tickIndex
	•	Canvas overlay updates per-tick view (optional integration)
	•	Optional Integration:
	•	Canvas glyph highlights based on currentBeams
	•	Dynamic HUD narration or mutation feedback

⸻

🧪 Technical Implementation Notes
	•	All ticked beams are indexed via tick_index in WaveState
	•	Collapsed states tracked via collapse_state (collapsed, superposed, contradicted, etc.)
	•	Fallback rendering ensures graceful UI if trace is incomplete
	•	Live tick (liveTick) can be displayed for real-time alignment with current simulation

⸻

🧑‍💻 Developer Usage

To use or extend this module:
	1.	Ensure your container .dc.json has embedded collapse traces via collapse_trace_exporter.py.
	2.	Call <GHXTimeline glyphs={data?.all_beams} showCollapsed={...} />
	3.	Control tickIndex, currentTick, and currentBeams from the parent HUD
	4.	Optional: Integrate with startRecording() / stopRecording() for beam replay export
	5.	Canvas extensions (highlighting per tick) can read from currentBeams

⸻

🧭 User Guide

🔍 Viewing All Beam History
	•	Enable Replay Mode toggle in the HUD
	•	Scroll through the full GHX timeline to see collapse paths

🪄 Hiding Collapsed Branches
	•	Toggle Hide Collapsed in the GHX timeline
	•	This filters the view to only active, unresolved glyphs

⏮ Navigating Ticks
	•	Use ⏮ Prev and Next ⏭ buttons to step through each symbolic tick
	•	See tick count, glyph count, and collapse status

🔦 Inspecting Beams
	•	See detailed list of beams at the current tick in the HUD:
	•	Symbol, glyph ID, and state
	•	Hover/click to trace further logic or review collapse history

⸻

🧱 Future Enhancements (A5+)
	•	🧬 Add per-tick beam mutation graph (QEntropy Drift)
	•	🕳 Show teleportation jumps between forks
	•	🧠 Add CodexLang execution diff per tick
	•	🌀 Auto-play tick replay as video or slideshow

⸻

🏁 Summary

The A5 Beam Replay module provides symbolic simulation transparency, multiverse insight, and fine-grained control over collapse analysis. It is the foundation for timeline-driven debugging, CodexLang introspection, and symbolic AI education.

Status: ✅ Fully Implemented
Next Phase: A6 – Mutation Beam Viewer (fork entropy + symbolic divergence)

⸻
📘 GlyphWave A6 Integration: Technical + User Documentation

Module Scope: QuantumFieldCanvas.tsx, beam_renderer.tsx, polar_snap.ts, overlay_toggles.tsx
Feature Group: A6 – QWave ↔ QuantumFieldCanvas Integration
Status: ✅ COMPLETE

⸻

🧠 Overview

The A6 phase integrates QWave beam rendering, glyph collapse overlays, polar snapping, and symbolic state toggles directly into the QuantumFieldCanvas. It visualizes symbolic propagation and collapse dynamics in real time using CodexCore predictions and SQI metrics.

⸻

🔧 Technical Breakdown

✅ A6a: Add Beam Rendering Layer

File: quantum_field_canvas.tsx
	•	Component Imported: QWaveBeam
	•	Location Injected:
After rendering links, before rendering glyph nodes:

<QWaveBeam beams={qwaveBeams} overlayState={overlayState} />


	•	Source: @/components/QuantumField/beam_renderer
	•	Data: Consumes live beam metadata from collapse traces or prediction pulses.

✅ A6b: Animate Propagation / Decay / Coherence

File: beam_renderer.tsx
	•	Props:

interface BeamProps {
  beams: BeamEvent[];
  overlayState: OverlayToggleState;
}


	•	Visual Styles by State:
	•	predicted: dashed pulse (faint glow)
	•	collapsed: solid bright beam
	•	contradicted: broken segments (red flicker)
	•	coherenceDecay: gradient fade with opacity falloff
	•	Animation: via useFrame() and shaderMaterial interpolation

✅ A6c: Snap to Polar Grid

File: polar_snap.ts
	•	Function: snapToPolarGrid(nodes, centerId, radius)
	•	Logic:
	•	Find centerNode by id
	•	Arrange entangled glyphs (same trailId) around center in polar symmetry
	•	Position update uses angle + radius math:

x = center + r * cos(angle)
z = center + r * sin(angle)


	•	Usage: Called during glyph node position normalization in loader/init
	•	Imported as:

import { snapToPolarGrid } from "../QuantumField/polar_snap";



✅ A6d: Toggle Overlays

File: overlay_toggles.tsx
	•	State Hook:

const [overlayState, setOverlayState] = useState({
  prediction: true,
  contradiction: true,
  collapse: true,
  coherence: true,
});


	•	Toggles Rendered: Checkbox UI for each overlay layer
	•	Connected to: <QWaveBeam /> + any HUDs using overlay props
	•	Persistence (optional): Can sync to local storage or Codex session

⸻

🧪 Test & Debugging Notes
	•	✅ All QWave beam types render on initial mount
	•	✅ Collapse and contradiction states animate correctly
	•	✅ Polar snapping applies cleanly to trailId clusters
	•	✅ Overlay toggles respond live and reflect correctly in render
	•	🔄 Future: Add beam trace per tick or simulation mode (A7)

⸻

🎮 User Instructions

How to View Beams:
	•	Open a .dc.json container inside GHX/QFC.
	•	Ensure collapse_trace metadata is available.
	•	The canvas will render glowing beams between entangled glyphs.

How to Use Overlays:
	•	Use the Overlay Toggles Panel (top-right) to switch visibility:
	•	✅ Predictions (dashed, pulsing)
	•	❌ Contradictions (red flicker)
	•	✅ Collapses (solid)
	•	✅ Coherence Decay (fade)

How to Snap:
	•	Entangled glyphs auto-snap around central trail hubs.
	•	Triggered on canvas load or layout refresh.

Debugging Tips:
	•	No beams? Check collapse_trace or wave_state fields in container.
	•	Glitches? Ensure position of nodes is a [number, number, number] tuple.

⸻

🧭 Navigation
	•	QuantumFieldCanvas.tsx: Main canvas logic + state injection
	•	beam_renderer.tsx: QWave beam visual logic
	•	polar_snap.ts: Glyph layout transformation
	•	overlay_toggles.tsx: UI toggle panel

⸻

📌 Next Steps
	•	✅ A6 COMPLETE
	•	🔜 A7: Beam Replay Controls (tick-based navigation)
	•	🔜 A8: QWave Collapse/Decoherence Graph in HUD

⸻

📎 Changelog
	•	v1.0: Initial QWave beam integration, overlay toggles, polar snap
	•	v1.1: Animation layer for coherence + prediction pulses
	•	v1.2: HUD hooks for future replay and metric overlays

Generated by CodexCore :: QWave A6 Protocol :: 2025-09-05

📘 GlyphWave QWave Phase A7: Developer Testing + Simulation Tools

⸻

🧭 Overview

Phase A7 of the GlyphWave QWave system introduces core developer tooling for testing, debugging, and simulating beam behaviors such as forks, contradictions, and collapses. It includes support for:
	•	Loading test .dc.json containers with synthetic QWave beams
	•	Runtime simulation of beam behavior (forks, contradictions, coherence decay)
	•	CLI/API interfaces to inject synthetic packets into the system

This phase is essential for verifying deterministic collapse, tracking multi-branch collapse events, and performing integration tests with the CodexCore runtime, SQI prediction engine, and GHX replay HUD.

⸻

🔧 Developer Tasks (Completed ✅)

✅ A7a: Test .dc Container with Mixed Beam Types
	•	File: mixed_beam_test.dc.json
	•	Location: backend/modules/dimensions/containers/tests/
	•	Description: Includes entangled, collapsed, predicted, contradicted beams and glyphs with SQI overlays.
	•	Used In: QuantumFieldCanvasLoader.tsx to load container state.

✅ A7b: Simulate Beam Forks, Contradictions, Collapse
	•	Components:
	•	wave_state.py: Simulates collapse state
	•	collapse_trace_exporter.py: Logs beam state transitions
	•	GHXTimeline: Visual replay of beam paths
	•	Effects Rendered:
	•	Glow/fade for predicted/collapsed
	•	Dashed for contradictions
	•	HUD overlays for SQI metrics

✅ A7c: Add CLI + API to Inject Synthetic Beam Packets
	•	API Endpoint: /api/test-mixed-beams
	•	Backend Stub: Returns JSON payload with glyphs[], beams[]
	•	Frontend Hook:
	•	useEffect() in QuantumFieldCanvas.tsx
	•	Fetches beam test data and renders with <QWaveBeam> and <GlyphNodeRenderer>

⸻

🖥️ Technical Integration

📁 File Structure

frontend/components/QuantumField/
├── QuantumFieldCanvas.tsx ✅
├── beam_renderer.tsx ✅
├── polar_snap.ts ✅

backend/modules/dimensions/containers/tests/
├── mixed_beam_test.dc.json ✅

pages/api/test-mixed-beams.ts ✅

🔁 Data Flow

graph TD
    TestDC[mixed_beam_test.dc.json] -->|loaded by API| APIEndpoint[/api/test-mixed-beams/]
    APIEndpoint -->|JSON: glyphs + beams| CanvasLoader[QuantumFieldCanvasLoader]
    CanvasLoader --> QFC[QuantumFieldCanvas.tsx]
    QFC --> BeamRender[QWaveBeam]
    QFC --> GlyphRender[GlyphNodeRenderer]


⸻

👤 User Guide: How to Use A7 Testing Tools

1. 🔬 Load Mixed Beam Test Container

Use this to visually inspect beam types:

<QuantumFieldCanvasLoader containerId="mixed_beam_test" />

Or fetch via API:

fetch("/api/test-mixed-beams").then((r) => r.json()).then(setBeamData);

2. 🧪 Observe Collapse + Prediction Visuals
	•	Collapsed: Faded glow, gray HUD caption
	•	Predicted: Cyan glow, pulsing animation
	•	Contradicted: Dashed line, red warning in HUD
	•	Entangled: Pink beam, pulsating trail

3. 📡 Inject New Synthetic Beam Packets

Via CLI or test endpoint:

curl -X POST http://localhost:3000/api/test-mixed-beams \
     -H "Content-Type: application/json" \
     -d '{ "new_beam": { ... } }'

NOTE: Modify or extend test-mixed-beams.ts to handle injected payloads.

4. 🔁 Replay via GHX

Open GHXTimeline and scrub across ticks to view collapse states and beam propagation paths.

⸻

🛠️ Future Additions (Phase B Suggestions)
	•	Time-sequenced beam propagation (tick-wise replay)
	•	Dynamic container mutation (live beam injection during QFC runtime)
	•	SQI feedback loop: auto-mutate beams based on goal alignment
	•	Auto-detect incoherent contradictions and log to SQI

⸻

✅ Status

All Phase A7 tasks are completed and integrated with the QWave core, GHX visualizer, and .dc test infrastructure.

⸻

🧾 References
	•	frontend/components/QuantumField/QuantumFieldCanvas.tsx
	•	backend/modules/glyphwave/core/wave_state.py
	•	backend/modules/collapse/collapse_trace_exporter.py
	•	frontend/components/GHX/GHXTimeline.tsx

⸻

For further testing or extending the beam simulation toolkit, please fork the test container or add new CLI flags under scripts/dev/test_beam_tool.py (future B1 task).

📘 A8 – Full System Integration Points

QWave Beam + Symbolic Execution Chain

⸻

🔧 Overview

Phase A8 finalizes the system-wide integration of QWave beam logic across all symbolic execution paths within the Codex + GlyphOS stack. This enables real-time emission, tracking, and visualization of symbolic beam events (prediction, collapse, contradiction, ingestion) triggered by core execution events. It also routes symbolic reasoning into the QuantumFieldCanvas and GHX HUDs.

Each subphase (A8a–A8d) injects emit_qwave_beam(...) into key execution modules to emit telemetry-rich WaveState packets for each meaningful symbolic event.

⸻

🔌 Integration Points

Step
Module
Description
✅ A8a
codex_executor.py
Hooked into symbolic mutation and CodexLang evaluation loops to emit mutation beams
✅ A8b
prediction_engine.py
Emits predicted beams for each CodexLang forecast or symbolic logic fork
✅ A8c
symbolic_ingestion_engine.py
Emits ingestion beams when knowledge is absorbed into the symbolic runtime
✅ A8d
GHXVisualizer.tsx (optional)
Triggers visual overlays when beam events should be emphasized on the frontend


🧠 A8a – Mutation Hook: codex_executor.py

Location: backend/modules/codex/codex_executor.py

Hook: Inject emit_qwave_beam(...) inside the main symbolic mutation handler, right after new CodexLang forks or glyph rewrites.

emit_qwave_beam(
    glyph_id=new_glyph.id,
    result=result_data,
    source="codex_executor",
    state="mutated",
    context={"container_id": container.id, "tick": current_tick}
)

Purpose:
Log each symbolic mutation as a mutated beam, tied to specific glyph ID, CodexLang prediction, and container execution trace.

⸻

🔮 A8b – Prediction Hook: prediction_engine.py

Location: backend/modules/prediction/prediction_engine.py

Hook: Inside forecast_glyph_paths() or equivalent prediction function:

emit_qwave_beam(
    glyph_id=predicted_glyph.id,
    result=prediction,
    source="prediction_engine",
    state="predicted",
    context={"container_id": container_id, "tick": tick}
)

Purpose:
Emit real-time predicted beams from the SQI runtime whenever logical branches are forecast. Used for coherence tracking and contradiction alerts.

⸻

📥 A8c – Ingestion Hook: symbolic_ingestion_engine.py

Location: backend/modules/logic/symbolic_ingestion_engine.py

Hook: Inside the ingestion or KG insertion logic:

emit_qwave_beam(
    glyph_id=glyph.id,
    result=ingested_data,
    source="symbolic_ingestion_engine",
    state="ingested",
    context={"container_id": container_id}
)

Purpose:
Marks knowledge injection events with an ingested QWave, allowing the runtime and HUD to trace origin glyphs and absorption paths.

⸻

🛰️ A8d – Frontend Hook: GHXVisualizer.tsx (optional)

Location: frontend/components/GHX/GHXVisualizer.tsx

Hook: In useEffect or WebSocket handler for beam events, trigger visual overlays based on beam state:

if (beam.state === "mutated") {
    highlightGlyph(beam.glyph_id, { mode: "mutation", glow: true });
}

Purpose:
Inject reactive visual cues into the holographic canvas or HUD based on symbolic event types. Enables timeline replay, source tracing, and coherence analysis.

⸻

⛓️ Example Beam Chain

A full execution cycle across A8 points may emit the following beams:
	1.	predicted – Forked from CodexLang forecast
	2.	mutated – Result of CodexCore logic mutation
	3.	ingested – Absorbed symbolic knowledge or glyph
	4.	collapsed – Finalized path chosen by SQI runtime (optional)

All beams share:
	•	glyph_id
	•	qwave_id
	•	container_id
	•	tick
	•	source, state, timestamp
	•	Optional: prediction, metadata, sqi_score

These are logged via wave_state.py and visualized via QuantumFieldCanvas.tsx.

⸻

🔁 Long-Term Benefits

Feature
Benefit
🔬 Telemetry
Full symbolic traceability per container/tick
🎯 Debugging
Visual inspection of where forks collapse or fail
🔐 Security
Future SoulLaw auditing, fork poisoning detection
🧠 Intelligence
Enables mutation scoring and beam-based reasoning
🛰️ GHX Overlay
Contextual overlays in CodexHUD + GHXVisualizer


✅ Status

Subtask
Status
Commit / Path
A8a – Mutation Hook
✅ Complete
codex_executor.py
A8b – Prediction Hook
✅ Complete
prediction_engine.py
A8c – Ingestion Hook
✅ Complete
symbolic_ingestion_engine.py
A8d – GHX Visual Overlay
✅ Complete (optional)
GHXVisualizer.tsx


📁 Related Files
	•	emit_beam.py – Central emit_qwave_beam() logic
	•	wave_state.py – Defines WaveState packet structure
	•	collapse_trace_exporter.py – Telemetry sink
	•	GHXVisualizer.tsx – Holographic visualizer
	•	QuantumFieldCanvas.tsx – Field-based glyph display
	•	CodexHUD.tsx – Symbolic state HUD and trend overlays


A9: QWave Beam Schema + Developer Documentation

📖 Overview

This document defines the schema updates, documentation, and developer integration notes for QWave Beam-based execution inside the SQI runtime. This phase (A9) finalizes schema integration, beam field semantics, and provides annotated usage examples.

⸻

🔁 Schema Update: Container Support for QWave Beams

🔧 container.schema.json

Add a new top-level key to .dc.json container files:

"qwave_beams": [
  {
    "beam_id": "string",  // UUID or symbolic hash
    "origin_node": "string",  // originating glyph/node ID
    "prediction": "string",  // CodexLang string or AST
    "sqi_score": "float",  // symbolic quality index
    "collapse_state": "string",  // collapsed, contradicted, predicted
    "entanglement": ["string"],  // linked beam IDs
    "timestamp": "ISO8601 string",
    "metadata": { "any": "optional fields" }
  }
]

📦 Example Entry

{
  "beam_id": "beam-9473-ab1",
  "origin_node": "glyph-A92",
  "prediction": "(if goal => mutate x)",
  "sqi_score": 0.942,
  "collapse_state": "collapsed",
  "entanglement": ["beam-9472-zd3"],
  "timestamp": "2025-09-06T12:33:01Z",
  "metadata": {
    "creative_fork": true,
    "mutation_path": "/forks/goal_variant_2"
  }
}


⸻

🔠 Beam Field Descriptions

Field	Description
beam_id	Unique beam instance ID. May be symbolic or hashed.
origin_node	ID of the glyph or QNode where beam originated.
prediction	CodexLang string or symbolic AST representing this beam’s logic.
sqi_score	SQI-calculated quality/intelligence score. Range: [0.0 – 1.0].
collapse_state	State of beam: collapsed, predicted, contradicted, live.
entanglement	Other beams symbolically entangled with this one.
timestamp	Time beam was emitted or collapsed.
metadata	Optional extensible data: creative origin, teleport ID, QKD status, etc.


⸻

📓 Dev Examples + API Logging

✍️ Example Usage in codex_executor.py

from glyphwave.qwave.beam_logger import log_beam_prediction
log_beam_prediction(
    beam_id="beam-447",
    origin_node="X31-goal",
    prediction="(loop if resonance > 0.9)",
    sqi_score=0.988,
    collapse_state="collapsed",
    entanglement=["beam-445", "beam-446"]
)

🛰️ Sample FastAPI Output (GET /gw/state)

{
  "active_beams": 14,
  "last_beam": {
    "beam_id": "beam-1234-xyz",
    "collapse_state": "predicted",
    "sqi_score": 0.934,
    "prediction": "(mutate glyph if entropy < threshold)"
  }
}


⸻

🏁 Next Steps
	•	Ensure container_runtime.py uses updated schema when saving/loading
	•	Expose schema in knowledge_graph_writer.py → export_pack()
	•	Integrate schema field validation in container_validator.py
	•	Extend GHXVisualizer to allow per-beam schema inspection

⸻

✅ A9 Completion Criteria
	•	Schema fully reflected in .dc.json and runtime
	•	Beam fields logged and visualized
	•	Dev examples in notebooks + test APIs
	•	GHX + QFC renderers can resolve beam metadata
	•	Ready for tensor/Q2 overlays or creative forks

⸻

Version: QWaveBeam.Schema.v1
Date: 2025-09-06
Author: AION Intelligence Systems
Related: A8, Q2, CodexLang Mutation Streams

✅ A9b: Document Beam Field Meanings, States

📘 QWave Beam Field Reference

Field		
Description								Example						beam_id
Unique identifier of the beam
"beam_7e21"
source_id
Glyph or node that emitted the beam
"glyph_a1"
target_id
Target glyph/node this beam aims to reach
"glyph_b7"
carrier_type
Type of medium used to transmit the beam (symbolic/optical/quantum)
"symbolic"
modulation_strategy
Method used to encode meaning on the carrier
"phase_pulse"
coherence
Stability of the beam signal (0.0–1.0)
0.92
entangled_path
List of intermediate glyphs forming entangled links
["g1", "g2", "g3"]
mutation_trace
History of symbolic transformations or forks affecting this beam
["mutate:x", "collapse:y"]
collapse_state
Contextual execution frame or symbolic state during collapse
"mutated"


🧠 Beam Lifecycle States

Collapse State										Meaning
"predicted"
Beam is inferred but not yet executed or verified
"active"
Beam is live and interacting with target glyphs
"mutated"
Beam logic has been symbolically transformed
"collapsed"
Beam has reached terminal execution or contradiction
"contradicted"
Beam failed due to logical inconsistency
"expired"
Beam coherence decayed below threshold
"forked"
Beam split into alternate paths for exploration
"teleported"
Beam used QGlyph entanglement to jump frames
null
Context unknown or not recorded		

✅ A9c: Add Examples in Dev Notebooks + API Logs

📒 Dev Notebook Example (Jupyter)

from backend.modules.glyphwave.qwave.qwave_writer import collect_qwave_beams
from backend.modules.container.container_runtime import safe_load_container_by_id

container = safe_load_container_by_id("test_abc_123")
beams = collect_qwave_beams(container["id"])

for beam in beams:
    print(f"🔸 Beam {beam['beam_id']} from {beam['source']} ➝ {beam['target']}")
    print(f"    Carrier: {beam['carrier_type']} | Mod: {beam['modulation_strategy']}")
    print(f"    Coherence: {beam['coherence']} | Collapse: {beam.get('collapse_state')}")

🛰️ Sample API Log (from collapse_trace_exporter.py
{
  "event": "qwave_beam_emitted",
  "container_id": "container_xyz",
  "beam": {
    "beam_id": "beam_88f1",
    "source_id": "glyph_src",
    "target_id": "glyph_tgt",
    "carrier_type": "quantum",
    "modulation_strategy": "holographic_interference",
    "coherence": 0.85,
    "entangled_path": ["glyph_x1", "glyph_y7"],
    "mutation_trace": ["fork:m1", "collapse:z3"],
    "collapse_state": "mutated"
  },
  "timestamp": "2025-09-06T14:22:00Z"
}

📘 GlyphWave Carrier System – Technical Overview & Integration Guide

Version: GW-SKELETON-C1
Modules Covered:
	•	B1–B8: 🌐 Core Carrier Skeletons
	•	C1–C2b: 🔁 Adapters + SQI Event Bus Hooks

⸻

🔧 Part B – Core Carrier System Skeletons

B1. constants.py – 🌐 Protocol Constants

Defines all constants related to GlyphWave transmission:

GW_CHANNELS = ["audio", "optic", "symbolic"]
DEFAULT_GAIN = 0.7
DEFAULT_DURATION = 2.0
MODULATION_SCHEMES = ["FM", "AM", "PWM", "QPSK"]

Used across scheduler, runtime, modulation wrappers, etc.

⸻

B2. feature_flag.py – 🧩 Feature Gating

Core feature toggle, global access:

def gw_enabled() -> bool:
    return os.getenv("GLYPHWAVE_ENABLED", "1") == "1"

Supports runtime toggle of GlyphWave routing across SQI and GHX.

⸻

B3. interfaces.py – 📐 GlyphWave Contracts

Defines formal interfaces:

class IGlyphWaveCarrier:
    def send(self, packet: Dict[str, Any]) -> None: ...
    def recv(self) -> Optional[Dict[str, Any]]: ...

class PhaseScheduler:
    def select(...) -> Tuple[CarrierType, ModulationType]: ...

Used to enforce pluggability of custom carriers (e.g. optical, virtual beam).

⸻

B4. gwip_codec.py – 📡 Format Translation

Converts between:
	•	.gip: raw GIP packets
	•	.gwip: enriched GlyphWave packets

def encode_gwip(gip_packet: Dict) -> Dict:
    # Inject beam, carrier, modulation
def decode_gwip(gwip_packet: Dict) -> Dict:
    # Extract original payload

Allows seamless upgrade of legacy packets to high-fidelity GlyphWave.

⸻

B5. scheduler.py – 🕰️ Phase & Modulation Logic

Manages:
	•	PLL drift simulation
	•	jitter injection
	•	phase lock per session

Used by CarrierScheduler.select() during push_wave()

⸻

B6. carrier_memory.py – 📦 Buffer System

Thread-safe buffers:

transmit_buffer = Queue()
receive_buffer = Queue()

Used by runtime for safe, async packet dispatch.

⸻

B7. wave_scope.py – 📊 Metrics/Telemetry Logger

Logs:
	•	Beam event types
	•	SNR, throughput
	•	Collapse rate
	•	QKD stats

Also streams to HUD overlays if available (stream_to_hud(event)).

⸻

B8. runtime.py – 🚀 GlyphWave Runtime Engine

Main orchestration:

class GlyphWaveRuntime(IGlyphWaveCarrier):
    def send(self, packet): ...
    def recv(self): ...

Used globally via:
from .adapters import send_packet, recv_packet

🔁 Part C – Adapters + SQI Bus Hooks

C1. adapters.py – 🔌 Send/Recv Integration Layer

Allows legacy .gip calls to benefit from GlyphWave silently.

✅ Send Path – send_packet(packet)

def send_packet(packet: Dict[str, Any]) -> None:
    if gw_enabled():
        get_runtime().send(packet)
    else:
        legacy_send_gip_packet(packet)  # 🔁 Required

✅ You must implement:
from backend.modules.gip.gip_adapter_net import legacy_send_gip_packet

✅ Recv Path – recv_packet()
def recv_packet() -> Optional[Dict[str, Any]]:
    if gw_enabled():
        return get_runtime().recv()
    return legacy_recv_gip_packet()

✅ You must implement:
from backend.modules.gip.gip_adapter_net import legacy_recv_gip_packet

These hooks ensure bi-directional compatibility with legacy GIP or upgraded GWIP.

⸻

C2. sqi_event_bus_gw.py – 📬 SQI Publish Wrapper

Wraps sqi_event_bus.publish() and routes via GlyphWave if enabled.

✅ C2a – Wrap publish

def init_gw_publish_wrapper(fallback_publish_func):
    global _fallback_publish
    _fallback_publish = fallback_publish_func

def publish(event: Dict[str, Any]) -> None:
    wave_scope.log_beam_event(event["type"], meta=event.get("meta"))
    stream_to_hud(event)

    if gw_enabled():
        send_packet(event)
    elif _fallback_publish:
        _fallback_publish(event)


Called during sqi_event_bus.py runtime init:
from backend.modules.sqi import sqi_event_bus_gw
sqi_event_bus_gw.init_gw_publish_wrapper(publish)

✅ C2b – Feature-gate by context

Inside sqi_event_bus_gw.py, gw_enabled() may be extended to:
	•	Check container class
	•	Validate traits (glyphwave_allowed)
	•	Override for simulation/test

⸻

🧑‍🏫 User Integration Guide

🔁 Integrating GlyphWave Into SQI Event Bus
	1.	Inside sqi_event_bus.py, wrap your publish logic:

from backend.modules.sqi import sqi_event_bus_gw
sqi_event_bus_gw.init_gw_publish_wrapper(publish)

	2.	Now any call to publish(event) will route through:

	•	📊 wave_scope
	•	📡 send_packet() (via GWIP if enabled)
	•	or fallback to legacy

⸻

📡 Sending and Receiving GlyphWave Packets

Use drop-in calls:

from backend.modules.glyphwave.adapters import send_packet, recv_packet

send_packet({
  "type": "collapse_detected",
  "meta": {...},
  "payload": {...}
})

packet = recv_packet()
if packet:
    process_event(packet)

No need to modify legacy GIP logic if adapters are active.

⸻

🧪 Dev Tools (FastAPI)

Optional testing routes (Phase D):
	•	GET /gw/state – runtime inspection
	•	POST /gw/send – simulate beam transmission
	•	GET /gw/recv – receive pending packets

These allow manual testing of beam modulation, QKD, GWIP routing.

⸻

✅ Prerequisites / Gotchas

Requirement
Description
legacy_send_gip_packet(packet)
Must exist in gip_adapter_net.py
legacy_recv_gip_packet()
Must exist (or mocked)
GLYPHWAVE_ENABLED=1
Set in env to enable routing
sqi_event_bus.publish()
Must be wrapped via init_gw_publish_wrapper()
GHXVisualizer
Can stream via stream_to_hud(event)
runtime.get_runtime()
Creates single GlyphWaveRuntime() per process


✅ Completion Checklist
Task
Status
Carrier skeletons B1–B8
✅ Complete
Adapters.py send/recv hooks
✅ Complete
SQI wrapper module
✅ Complete
Feature toggle
✅ Included
Dev testing routes
🟡 Optional
GIP legacy fallback
❗MUST EXIST or provide mocks
