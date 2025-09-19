SQS & AtomSheets — Technical Overview and User Guide

This document is a single place to understand what the SQS / AtomSheets system is, how it’s wired together (backend ↔ frontend ↔ WebSocket), how to run it, and how to extend it. It’s written so that a new engineer or an AI agent can jump in and be productive.

⸻

0) What is SQS / AtomSheets?
	•	SQS (Symbolic Quantum Spreadsheet) is a multi-dimensional “spreadsheet” for symbolic logic. Cells hold logic expressions (plain symbolic or CodexLang), predictions, emotions, and metadata.
	•	An AtomSheet is a sheet file (JSON) with a 4D grid of GlyphCells. Each cell can be executed via the Codex QPU stack to produce results, beams (for GHX/HUD visualizations), and per-cell quality metrics (SQI, entropy, novelty, harmony).
	•	The system includes:
	•	A backend API (FastAPI) to load, execute, export, upsert cells, and trace lightcones.
	•	A frontend panel (Next.js/React) to render the grid, show metrics and telemetry, and support drag/drop from the SCI Graph.
	•	A panel host/registry so multiple tools (SQS grid, AtomSheet view, Goals) coexist as tabs.

⸻

1) High-Level Architecture

┌──────────────────────────────────────────────────────────────────┐
│ Frontend (Next.js)                                               │
│                                                                  │
│  SciPanelHost ─ Tabs (sqs | atomsheet | goals)                   │
│     ├─ SciSqsPanel (SQS grid + HUD + DnD)                        │
│     ├─ SCIAtomSheetPanel (AtomSheet viewer/editor)               │
│     └─ SciGoalPanel (C3 plugin)                                  │
│                                                                  │
│  Uses REST  ─ /api/atomsheet, /api/atomsheet/execute, /export    │
│          ─ /api/atomsheet/upsert, /api/lightcone                 │
│  Uses WS    ─ ws://.../qfc_socket  (optional)                    │
└──────────────────────────────────────────────────────────────────┘
                ▲                                 │
                │                                 │ WS (telemetry: beams, timelines)
                │ REST                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                                │
│                                                                  │
│  Routers: /api/atomsheet, /api/lightcone                         │
│    ├─ load_atom(dict|path) → AtomSheet                           │
│    ├─ execute_sheet(sheet, ctx) → beams + metrics (E7)           │
│    ├─ to_dc_json(sheet) → export snapshot                        │
│    └─ upsert cell → persist to .atom                             │
│                                                                  │
│  Engines: CodexVirtualQPU, Lightcone tracer                      │
│  Telemetry: qfc_socket.broadcast_qfc_update(container_id, …)     │
│  Registry: persistent sheet/ID map (optional)                    │
└──────────────────────────────────────────────────────────────────┘

2) Core Data Model

2.1 AtomSheet (file format)
	•	Files use the .atom extension (JSON). A minimal example:

{
  "id": "sheet_001",
  "title": "Example Sheet",
  "dims": [4, 4, 1, 1],
  "meta": {},
  "cells": [
    {
      "id": "A1",
      "logic": "2 + 2",
      "position": [0, 0, 0, 0],
      "emotion": "inspired",
      "meta": {}
    }
  ]
}

	•	Schema files (if you validate):
	•	backend/schemas/atom_sheet.schema.json
	•	backend/schemas/glyph_cell_schema.json

2.2 GlyphCell properties (superset)

Common fields the backend serializes to the UI:
	•	id: str
	•	logic: str — symbolic or CodexLang
	•	logic_type?: "codexlang" | string — explicit attribute or from meta.logic_type
	•	position: [x,y,z,t]
	•	emotion?: string
	•	prediction?: string
	•	validated?: boolean
	•	result?: string — last execution result (if any)
	•	Quality metrics (E7):
sqi_score?: number (0..1), entropy?: number, novelty?: number, harmony?: number
	•	CodexLang preview (B6):
codex_eval?: string (server-side humanized preview)
codex_error?: string (if evaluation fails)
	•	wave_beams?: any[] — visualizable beams for the GHX/HUD
	•	meta?: object — any extra, including nested expansion descriptor

The UI prefers codex_eval when present, else falls back to a tiny local tryInterpret(logic).

⸻

3) Backend Walkthrough

3.1 Router: backend/routers/atomsheets.py

Endpoints (all under /api):
	1.	GET /atomsheet
Load and return a sheet:
	•	Query: file, optional container_id
	•	Headers: Authorization: Bearer valid_token (token validation is optional; if provided and not valid_token → 401)
	•	Response:

{
  "id": "...",
  "title": "...",
  "dims": [..],
  "cells": [ { ...serialized GlyphCell... } ],
  "meta": { ... },
  "container_id": "cont1"
}

	2.	POST /atomsheet/execute
Execute sheet (by path or inline JSON) via the Codex QPU stack.
	•	Body:

{
  "file": "backend/data/sheets/example_sheet.atom",
  "container_id": "cont1",
  "options": {
    "benchmark_silent": true,
    "batch_collapse": true,
    "expand_nested": false,
    "max_nested_depth": 1,
    "phase9_enabled": false,
    "phase10_enabled": false,
    "phase10_precision": "fp8"
  }
}

•	Returns:

{
  "ok": true,
  "sheet_id": "…",
  "beam_counts": { "A1": 3, "B1": 1, ... },
  "metrics": { "execution_time_ms": 12, "sqi": { "A1": 0.88, ... } },
  "cells": [ { ...serialized, includes E7 metrics + beams... } ]
}

	•	If container_id is provided and benchmark_silent is false, the router emits a lightweight WS broadcast (see §3.5).

	3.	GET /atomsheet/export
Return a .dc.json-style snapshot (in memory) for the sheet.
	4.	POST /atomsheet/upsert
Insert/update a cell and persist the .atom file.
	•	Body:

{
  "file": "backend/data/sheets/example_sheet.atom",
  "id": "optional-existing-id",
  "logic": "new logic",
  "position": [x,y,z,t],
  "emotion": "neutral",
  "meta": { "logic_type": "codexlang" }
}

•	Returns { "ok": true, "id": "the-cell-id" }.

These endpoints rely on the engine functions: load_atom, execute_sheet, to_dc_json.

3.2 Engine: backend/modules/atomsheets/atomsheet_engine.py (naming may vary)

Core responsibilities implemented (or stubbed):
	•	load_atom(input) — accepts a file path or a dict, returns an AtomSheet object (with cells dict).
	•	execute_sheet(sheet, ctx) — runs cells through the CodexVirtualQPU (defensive).
Adds:
	•	Sheet collapse beam (∑ counts by cell)
	•	Nested expansion (A5) when ctx.expand_nested and depth < max_nested_depth
	•	SQI refresh per cell (safe fallbacks)
	•	E7 compute: entropy, novelty, harmony
	•	CodexLang evaluation (B6): if logic_type == "codexlang" (or meta.logic_type) → set codex_eval/codex_error
	•	to_dc_json(sheet) — returns a stable export snapshot.

3.3 Security
	•	The atomsheet router uses HTTPBearer(auto_error=False).
If a token is present it must be "valid_token", otherwise 401. If absent, endpoints still work (by design) unless you tighten it.
	•	The LightCone API (below) expects the token and validates it strictly.

3.4 LightCone tracer API

File: backend/api/api_lightcone.py
GET /lightcone
	•	Query params:
	•	entry_id or entry_ids[]
	•	direction (forward | reverse)
	•	file (sheet path) — defaults to an example if omitted
	•	container_id (optional)
	•	push_to_qfc (default true)
	•	Auth: Authorization: Bearer valid_token (strict).
	•	Behavior:
	•	Loads/validates the sheet (async-safe file IO)
	•	Runs forward/reverse tracer over the cell graph
	•	Optionally broadcasts the trace to QFC WebSocket
	•	Returns { "trace": [...] } (single) or { "traces": {id: [...]}} (batch).

3.5 WebSocket Telemetry (optional)
	•	The atomsheet router uses a best-effort _broadcast(container_id, payload) that calls:
backend.modules.qfc.qfc_socket.broadcast_qfc_update(container_id, payload)
	•	If the module is missing, it won’t crash; it logs a trace.
	•	Typical messages:
	•	"type": "atomsheet_executed" with counts/metrics
	•	QPU timeline / Phase9 dreams / Phase10 vectorized events (produced by lower layers)

⸻

4) Frontend Walkthrough

4.1 Panel Host + Registry
	•	Host page: frontend/pages/sci/SciPanelHost.tsx
	•	Renders a top bar with “+ AtomSheet”, “+ SQS”, “+ Goals” to open new tabs.
	•	Remembers open tabs in localStorage.
	•	Deep-link support: /sci/SciPanelHost?panel=sqs&file=[path]&containerId=[id]&title=[t]
	•	Imports the default panel registrations once:

import "./panels/register_atomsheet";
import "./panels/register_sqs";
import "./panels/register_goals";


	Panel registry core: frontend/pages/sci/panels/panel_registry.ts
	•	Exposes registerPanel, getPanel, listPanels for dynamic panel discovery.
	•	Registrations:
	•	frontend/pages/sci/panels/register_atomsheet.ts
	•	frontend/pages/sci/panels/register_sqs.ts
	•	frontend/pages/sci/panels/register_goals.ts

4.2 SQS / AtomSheet Panels
	•	SCIAtomSheetPanel (file: frontend/pages/sci/sci_atomsheet_panel.tsx)
Key behaviors:
	•	Loads the sheet then POST /api/atomsheet/execute to enrich cells with E7 metrics and codex_eval.
	•	Renders Emotion/SQI, and badges for entropy, novelty, harmony.
	•	Shows a nested expand (↘) button when meta.nested.type === "ref".
	•	DnD: supports drop from the SCI Graph on empty grid slots to upsert a cell via /api/atomsheet/upsert.
	•	HUD: supports pin/follow + debounced updates for LightCone tracing.
	•	SciSqsPanel is a simpler sibling, also wired to the same endpoints, used as a generic SQS grid view.
	•	SciGoalPanel (C3): local-storage goal tracker, registered as a panel.

4.3 DnD contract (Graph → Sheet)
	•	Drop MIME type: application/x-sci-graph
	•	Payload example:

{
  "logic": "f(x) = x^2",
  "emotion": "curious",
  "meta": { "logic_type": "codexlang" }
}

	•	The panel converts the hovered slot coordinates [x,y,z,t] into the position and calls:
POST /api/atomsheet/upsert.

4.4 LightCone HUD
	•	Hover a cell → if follow selection is on and not pinned, the panel debounces a call to /api/lightcone.
	•	Click a cell → immediate non-debounced call and pins the trace.
	•	Controls:
	•	📌 Pin/Unpin Trace
	•	🧲 Follow Hover
	•	🌌 Direction toggle Forward/Reverse

4.5 Environment variables

Frontend expects:

NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_QFC_WS=ws://localhost:8000/ws     # optional if WS bridge present
NEXT_PUBLIC_AUTH_TOKEN=valid_token

5) Running the System

5.1 Backend
	1.	Ensure minimal stubs exist:
	•	backend/utils/glyph_schema_validator.py with validate_atomsheet (returns (True, "")).
	•	backend/modules/utils/time_utils.py has now_utc_iso() and now_utc_ms().
	2.	Mount routers defensively in backend/main.py (atomsheets is required; lightcone optional).
	3.	Run:

uvicorn backend.main:app --reload

4.	Health check:

curl http://localhost:8000/health

	5.	Smoke test:
curl "http://localhost:8000/api/atomsheet?file=backend/data/sheets/example_sheet.atom" \
  -H "Authorization: Bearer valid_token"
curl -X POST http://localhost:8000/api/atomsheet/execute \
  -H "Authorization: Bearer valid_token" -H "Content-Type: application/json" \
  -d '{"file":"backend/data/sheets/example_sheet.atom","options":{"benchmark_silent":true}}'

5.2 Frontend
	1.	Create .env.local as above.
	2.	Start Next:

npm run dev

	3.	Open /sci (or /sci/SciPanelHost), click + SQS or + AtomSheet, choose a file (default sample is backend/data/sheets/example_sheet.atom).

⸻

6) How Execution Works (Under the Hood)
	1.	User opens sheet → FE calls POST /api/atomsheet/execute with the file path and options.
	2.	Backend execute_sheet:
	•	Prepares a context with sheet_cells, recursion depth/limits, and metrics.
	•	Invokes CodexVirtualQPU on each cell (defensive try/except).
	•	Refreshes SQI per cell (lazy fallback to default).
	•	Appends a collapse beam with counts (∑).
	•	Computes E7 metrics: entropy, novelty, harmony.
	•	Evaluates CodexLang when logic_type == "codexlang" (or meta.logic_type):
sets codex_eval (rendered preview) and codex_error if something fails.
	•	Performs nested expansion (A5) for cells with meta.nested descriptors when enabled.
	3.	Returns serialized cells so UI immediately shows updated SQI/E7 and any new beams.
	4.	If container_id present and not silent → optional WS atomsheet_executed broadcast for HUD.

⸻

7) Using the System

7.1 Create a new AtomSheet
	•	Create backend/data/sheets/my_first.atom:

{
  "id": "my_first",
  "title": "My First Sheet",
  "dims": [3, 3, 1, 1],
  "meta": {},
  "cells": [
    { "id": "A1", "logic": "1 + 1", "position": [0,0,0,0], "emotion": "curious" },
    { "id": "B1", "logic": "f(x) = x+3", "position": [1,0,0,0], "emotion": "inspired",
      "meta": { "logic_type": "codexlang" } }
  ]
}

	•	Open the panel & set file to this path.
	•	You’ll see codex_eval for the CodexLang cell and E7 badges for both cells.

7.2 Drag a node from SCI Graph
	•	Your Graph should set DnD payload:

e.dataTransfer.setData(
  "application/x-sci-graph",
  JSON.stringify({ logic: "g(y)=y^2", emotion: "playful", meta: { logic_type: "codexlang" } })
);

	•	Drop into an empty grid slot → panel calls POST /api/atomsheet/upsert.
	•	The sheet is saved to disk and reloaded.

7.3 Trace a LightCone
	•	Hover a cell (with Follow Hover ON) → debounced GET /api/lightcone.
	•	Click a cell → immediate trace & Pin.
	•	Toggle Forward/Reverse to change direction.

⸻

8) Extending the System

8.1 Add a new panel
	1.	Create a React component under frontend/components/SQS/MyPanel.tsx.
	2.	Register it in frontend/pages/sci/panels/register_my_panel.ts:

import { registerPanel } from "./panel_registry";
import MyPanel from "@/components/SQS/MyPanel";

registerPanel({
  id: "my-panel" as any, // extend PanelTypeId if you want type safety
  title: "My Panel",
  component: MyPanel,
  makeDefaultProps: () => ({})
});

	3.	Import the registration file in SciPanelHost.tsx (once).

8.2 Add a new logic type
	•	Decide a new logic_type string, e.g. "lispish".
	•	In execute_sheet, detect it (attribute or meta.logic_type) and call your evaluator to set codex_eval/codex_error.
	•	UI automatically prefers codex_eval.

8.3 Add more metrics
	•	Implement a compute_xyz_metrics(cells) helper and call it inside execute_sheet after QPU execution.
	•	Add UI badges in the cell footer (re-use the Badge component).

⸻

9) Troubleshooting & Notes
	•	Tests failing: many test files cover parts of the old/extended system not required for boot. Focus on uvicorn + Next compiling first. We already added stubs (e.g., glyph_schema_validator) so /api/lightcone won’t crash on import.
	•	Path aliases: ensure your Next tsconfig.json supports @/ paths the way your code imports them.
	•	SSR: any code that uses window or localStorage should guard or run client-side only; the Host page uses client-side hydration (and you can use dynamic(..., { ssr: false }) if needed).
	•	Auth token: by default we accept valid_token. Set NEXT_PUBLIC_AUTH_TOKEN=valid_token.

⸻

10) Checklist Status (today)
	•	Core (A1–A6) ✅
	•	Features
	•	B1 ✅ Multi-Dim Grid
	•	B2 ✅ Expandable (nested ref/inline + UI)
	•	B3 ✅ Predictive/Forking (surface field + beams; generator logic lives in QPU layers)
	•	B4 ⏳ Scrolls/Memory UI (fields present; UI surfacing minimal—add a 📜 popover if desired)
	•	B5 ✅ Symbolic execution inside cells
	•	B6 ✅ CodexLang live formulas (server preview + UI)
	•	Tooling/Plugins
	•	C1 ✅ Loader + Registry
	•	C2 ✅ E7 visualizers (badges)
	•	C3 ✅ Goals panel (registered + working with localStorage)
	•	C4 ✅ SQI plugin (scoring integration)
	•	C5 ✅ SoulLaw overlay (plumbed in scoring/validation hooks)
	•	Implementation Sequence
	•	E1–E3 ✅ Engine + format + model
	•	E4 ✅ SCI panel
	•	E5 ✅ Drag/Drop Graph → Sheet (upsert endpoint + slot handling)
	•	E6 ✅ Symbolic execution support
	•	E7 ✅ Entropy/Confidence visualization
	•	E8 ✅ Export to .dc.json

⸻

11) API Reference (quick)

/api/atomsheet (GET)
	•	file: path to .atom
	•	container_id?: string
	•	Returns: { id, title, dims, meta, container_id, cells: [...] }

/api/atomsheet/execute (POST)
	•	Body: { file | sheet, container_id?, options? }
	•	Returns: { ok, sheet_id, beam_counts, metrics, cells }

/api/atomsheet/export (GET)
	•	file: path
	•	Returns: snapshot JSON (.dc style)

/api/atomsheet/upsert (POST)
	•	Body: { file, id?, logic, position, emotion?, meta? }
	•	Returns: { ok, id }

/api/lightcone (GET)
	•	Params: entry_id|entry_ids[], direction, file, container_id?, push_to_qfc?
	•	Returns: { trace: [...] } or { traces: {id:[...]}}

⸻

12) Suggested Next Steps
	•	B4 UI: show scrolls/memory in a small 📜 popover on each cell; editable dialog with save-to-upsert.
	•	HUD polish: add counters (nodes / edges / ms), and wire /qfc_entanglement to real graph storage (for now, stub returns []).
	•	Samples: add nested_demo.atom and entangle_demo.atom with tiny READMEs.


