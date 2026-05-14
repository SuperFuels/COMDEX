SCI (Spatial Cognition Interface) — Technical Architecture & User Guide

This doc explains how SCI is built, how it works end-to-end, what it connects to, and how to use/extend it. It’s written so a new engineer can jump in and be productive fast.

⸻

0) TL;DR
	•	Frontend: Next.js + React + Three.js. The core visual is QuantumFieldCanvas (QFC), a 3D scene of Glyph nodes, Links, and QWave beams with overlays, replay, export, and split (Real/Dream) views.
	•	Collaboration: A tiny y-websocket server (server/collab-server.ts) plus a React hook useSharedField that syncs nodes/links/beams and presence (cursor, selection, viewport) across users.
	•	Data in/out: REST APIs like /api/qfc_view/[containerId], /api/qfc/graph, /api/inject_scroll, /api/mutate_from_branch, /api/test-mixed-beams.
	•	Events: Window shims—broadcast_qfc_update(...) → window CustomEvents keep pre-existing “QFC live update” flows working.
	•	Build/Run: npm run dev runs Next.js and the collab server together. Env: NEXT_PUBLIC_COLLAB_WS, COLLAB_PORT, COLLAB_HOST.

⸻

1) Module Map (what’s done, where it lives)

A) SCI Core Framework (✅)
	•	A1 — Symbolic Graph Runtime (SGR):
The base graph of GlyphNode[] + Link[] consumed by QFC. You can load from /api/qfc_view/:containerId (preferred) or /api/qfc/graph?container_id=....
Shape (simplified):


type Vec3 = [number, number, number];

export interface GlyphNode {
  id: string | number;
  position: Vec3;
  label?: string;
  tick?: number;
  containerId?: string;
  collapse_state?: "collapsed" | "breakthrough" | "deadend" | string;
  entropy?: number;
  predicted?: boolean;
  // ...other annotations
}

export interface Link {
  source: string; target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
}


	•	A2 — QuantumFieldCanvas Embedding (QFC):
frontend/components/Hologram/quantum_field_canvas.tsx renders the field. Responsible for:
	•	3D scene (Three.js via @react-three/fiber)
	•	Orbit controls, tweened centering
	•	Overlays (emotion, entropy, strategy, etc.)
	•	Replay/record
	•	Split Real/Dream canvases
	•	Export panel & HUD controls
	•	A3 — Relevance Scroll Engine:
Drops “scrolls” (text/intent) into glyphs → calls /api/inject_scroll → server responds with new glyphs/links → injected live via QFC event shim.
	•	A4 — Glyph Execution Field:
Visual+interactive execution of glyph semantics—operators highlighted (HighlightedOperator) and logic overlays (BeamLogicOverlay) to support symbolic reasoning steps.
	•	A5 — Attention + Focus Tracker:
“Center to Glyph” + Observer viewport. Helpers:

export function setOrbitTargetToGlyphFactory({nodes, cameraRef, controlsRef}) { /* tween/snap */ }
export function centerToGlyphFactory({mergedNodes, setObserverPosition, setOrbitTargetToGlyph}) { /* find + center */ }

Also isInObserverView marks nodes in the observer’s FOV.

	•	A6 — Container Workspace Loader:
QuantumFieldCanvasLoader loads data for a containerId, merges live websocket additions, and hands the result to QFC. Teleporting to a node can navigate to /dimension/:container.

B) Interaction Systems (✅)
	•	B1 — Scroll Pull + Drop:
Dragging or programmatically injecting scrolls triggers /api/inject_scroll. Result is broadcast (broadcast_qfc_update) to update the field in place.
	•	B2 — Center POV Logic Anchor:
centerToGlyphFactory + setOrbitTargetToGlyphFactory for smooth camera target moves.
	•	B3 — Snap-to-Memory Graph:
snapToEntangledMemoryLayout (optional “layout snap” for consistent spatial positioning across sessions).
	•	B4 — Session Recorder (Replay/History):
On key actions (e.g., scroll injection), capture a frame (glyphs, links, observer, branch, etc.) into replayFrames[]. A simple tick-based playback advances frames at 100ms per step.
	•	B5 — Hover Memory Context Preview:
HoverMemorySummary / HoverAgentLogicView near a node shows last memory summary, containerId, agentId.

C) Toolchain + Plugin Layer (✅)
	•	C1 — AION Engine Dock:
Emotion/Goal/Strategy overlays (EmotionOverlay, StrategyOverlay) use node annotations (e.g., goalType, memoryTrace).
	•	C2 — CodexCore Trigger Hub:
Handles QWave triggers/logic overlay to tie symbolic ops to beams.
	•	C3 — Mutation + Innovation Toolkit:
“Mutation trails” / HoverMutationTrace visualizes changes, plus rewrite probabilities, goal matching, etc.
	•	C4 — Tranquility Auto-Iteration Runner:
Batch/auto iteration flows can stream QWave packets; captured and visualized as beams.
	•	C5 — Logic Synthesizer:
Scroll → Field link; convert high-level scrolls into edges/ops on the graph.

D) Export + Recall Systems (✅)
	•	D1 — Save Session to .dc.json:
Not shown here, but the loader expects SCI format .dc.json. Export panel gathers filtered node snapshots into a JSON.
	•	D2 — Stream QWave Packets:
QWaveBeam rendering + rerouting path logic (rerouteBeam), plus renderQWaveBeamsLocal helper.
	•	D3 — Field→Memory Writeback Hooks:
When scrolls mutate the field, the backend stores derived memory traces; frontend renders via memoryTrace overlays.
	•	D4 — Field Metrics:
EntropyNode, goal match / rewrite success scores, novelty lines—displayed on nodes/links/beams.
	•	D5 — Session Seeding:
Captured frames and .dc.json let you re-enter a session with containerId.

E) Future Expansion
	•	E3 — Multi-Agent Collaboration (✅ now integrated):
Shared graph state & presence via Yjs.
	•	E4 — External Plugin Runtime + Import Hooks (🚧 later).

⸻

2) Collaboration Layer (E3) — How it works

Server
	•	File: server/collab-server.ts
	•	Tech: Node HTTP + ws + y-websocket (v1.5.4, server API stable)
	•	Behavior: One Yjs doc per ?room=... (use containerId for room name)
	•	Config:


# .env or .env.local
NEXT_PUBLIC_COLLAB_WS=ws://localhost:1234
COLLAB_PORT=1234
COLLAB_HOST=0.0.0.0

Client Hook
	•	File: collab/useSharedField.ts
	•	Provides live arrays: nodes, links, beams
	•	Also presence: { me, others } + mutation API applyOp

const { nodes, links, beams, applyOp, others } = useSharedField(containerId);

// CRDT mutations
applyOp.addNode({...}); applyOp.updateNode(id, patch); applyOp.removeNode(id);
applyOp.addLink(...);   applyOp.updateLink(...);       applyOp.removeLink(...);
applyOp.addBeam(...);   applyOp.updateBeam(...);       applyOp.removeBeam(...);

// Presence
applyOp.setCursor(x, y);
applyOp.setSelection(["id1","id2"]);
applyOp.setViewport([cx,cy,cz], zoom);


Yjs doc shape (on the wire)
We store everything under graph map:

graph:
  nodes: Map<string, Map>   // { id, position, label, ... }
  links: Map<string, Map>   // { id, source, target, type, ... }
  beams: Map<string, Map>   // { id, source(vec3), target(vec3), sqiScore, ... }

Presence is via awareness (provider.awareness), we only publish { user: Presence }.

Presence UI
	•	File: collab/PresenceLayer.tsx
	•	Renders other users’ cursors on top of the app (fixed overlay).
	•	You add it once, outside any <Canvas>:

<PresenceLayer others={others} />

Viewport broadcasting
	•	In QFC, OrbitControls’s onChange calls applyOp.setViewport, throttled by lastViewportSent.
This lets other clients show your current looking center & crude zoom metric.

⸻

3) QuantumFieldCanvas (QFC) — How it stitches together

Props (public API)

type ExtendedGlyphNode = GlyphNode & {
  containerId?: string; predicted?: boolean; locked?: boolean; color?: string;
  label?: string; emotion?: { type?: string; intensity?: number } | boolean;
};

interface QuantumFieldCanvasProps {
  nodes: ExtendedGlyphNode[];
  links: Link[];
  beams?: any[];                 // optional local fallback
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;
  containerId?: string;          // used as collaboration "room"
  predictedMode?: boolean;
  predictedOverlay?: { nodes: ExtendedGlyphNode[]; links: Link[] };
}

Data sources inside QFC
	1.	Collaborative live state via useSharedField(roomId)
	2.	Fallback to props.nodes/links/beams if shared arrays are empty
	3.	Live “QFC server push” via useQfcSocket(containerId) merges extra glyphs/links during the session
	4.	Optional: /api/test-mixed-beams demo loader for beam visuals

Merge & render flow
	•	Predicted merge: mergePredictedGraphLocal({ nodes, links, tickFilter, showCollapsed }) returns mergedNodes, mergedLinks (combines “real” + “predicted” layer depending on toggles).
	•	Beams: renderQWaveBeamsLocal({ beamData, setSelectedBeam }) returns a JSX list of QWaveBeam.
	•	Overlays: Entropy, Emotion, Strategy, ObserverViewport, MemoryScroller, Hover previews, Trails, etc.
	•	Split/Unified view:
	•	Split: Left = Real; Right = Dream/Predicted
	•	Unified: Single canvas, both layers via toggles
	•	HUD: Buttons: Predicted toggle, Split, Replay, Fade Real Nodes, Overlay On/Off, Export panel.
	•	Export: Filters + dumps nodes to JSON (respect showCollapsed and tickFilter).

Event shims (keep older flows working)
	•	broadcast_qfc_update(payload) → window.dispatchEvent("qfc_update", {detail:payload})
	•	The loader or other code may listen and merge into graphAdds or Yjs, depending on your wiring.
	•	Also used: window.dispatchEvent("focus_glyph", { detail: { glyphId } }) to center camera.

⸻

4) APIs the UI talks to
	•	GET /api/qfc_view/:containerId → { nodes, links } + traces (preferred rich response).
QFC annotates nodes (goalType, memoryTrace, containerId).
	•	GET /api/qfc/graph?container_id=... → fallback minimal { nodes, links }.
	•	POST /api/inject_scroll → body { glyph, scroll }
Returns { glyphs: [...], links: [...] } to append; QFC centers camera and records a replay frame.
	•	POST /api/mutate_from_branch → body { trailId }
Returns mutated field; QFC broadcasts to live view.
	•	GET /api/test-mixed-beams → demo beams.

Expected node augmentations (frontend expects these if present):
	•	node.collapse_state: "collapsed"|"breakthrough"|"deadend"|...
	•	node.entropy: number
	•	node.goalMatchScore, node.rewriteSuccessProb (for SQI)
	•	node.memoryTrace = { summary, containerId, agentId }

⸻

5) How to run, environments, and scripts

Env

# root .env or .env.local
NEXT_PUBLIC_COLLAB_WS=ws://localhost:1234
COLLAB_PORT=1234
COLLAB_HOST=0.0.0.0

Scripts (package.json)

{
  "scripts": {
    "build": "next build frontend",
    "start": "next start frontend",
    "collab": "ts-node --transpile-only -P tsconfig.collab.json server/collab-server.ts",
    "dev": "concurrently \"next dev frontend\" \"npm run collab\""
  }
}

TS for the collab server (tsconfig.collab.json at repo root)

{
  "compilerOptions": {
    "target": "ES2020",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "strict": false,
    "resolveJsonModule": true,
    "types": ["node"],
    "typeRoots": ["./types", "./node_modules/@types"],
    "outDir": "dist-collab"
  },
  "include": ["server/**/*.ts", "types/**/*.d.ts"]
}

Next.js config (frontend/next.config.js)

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
  env: { NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL },
};
module.exports = nextConfig;

Collab server file (root: server/collab-server.ts)

import http, { IncomingMessage } from "http";
import { WebSocketServer } from "ws";
import { setupWSConnection } from "y-websocket/bin/utils";

const server = http.createServer();
const wss = new WebSocketServer({ server });

wss.on("connection", (conn: any, req: IncomingMessage) => {
  try {
    const url = new URL(req.url || "/", "http://localhost");
    const room = url.searchParams.get("room") || "default";
    setupWSConnection(conn, req, { docName: room, gc: true });
  } catch (err) {
    console.error("❌ WebSocket error:", err);
  }
});

const PORT = Number(process.env.COLLAB_PORT || 1234);
const HOST = process.env.COLLAB_HOST || "0.0.0.0";
server.listen(PORT, HOST, () => {
  console.log(`🔗 Collab server listening on ws://${HOST}:${PORT}`);
});

Type shim (root: types/y-websocket-utils.d.ts)

declare module "y-websocket/bin/utils" {
  import type { IncomingMessage } from "http";
  import type WebSocket from "ws";
  export function setupWSConnection(
    conn: WebSocket,
    req: IncomingMessage,
    opts?: { docName?: string; gc?: boolean }
  ): void;
}

Dependencies (key pins)
	•	y-websocket@1.5.4 (server import path stable)
	•	@react-three/drei@9.93.0 (compatible with React 18)
	•	react@18.3.x, three@0.178.x

⸻

6) User Guide (how to use the UI)
	•	HUD (top-left):
	•	🔮 Predicted Layer — toggles predicted overlay (ghost/dream nodes/links).
	•	🧠 Split View — left (Real) vs right (Dream). In split, left canvas sends presence viewport.
	•	▶️/⏸ Replay — starts/stops playback of captured frames (from scroll injections, etc.).
	•	🌓 Fade Real Nodes — dims non-predicted to emphasize predicted layer.
	•	🌐 Overlay — show/hide extra predicted overlay (alternate renderer).
	•	HUD (top-right):
	•	Branch Selector & Retry — pick a branch trail and trigger /api/mutate_from_branch.
	•	Export Panel — shows Tick filter and count of collapsed nodes and lets you download a filtered JSON snapshot.
	•	3D Canvas Interactions:
	•	OrbitControls: Drag to rotate, wheel to zoom. Viewport is shared to collaborators (others see your cursor and viewpoint).
	•	Click a node: Focus/teleport logic (if enabled) or pop hover summary.
	•	Hover a node: Shows memory summary, entropy overlay, lock icon, etc.
	•	Beams: Visualize symbolic/QWave connections; clicking can open preview panel.
	•	Collaboration UX:
	•	Presence cursors: See other users’ cursors overlaid.
	•	Viewport sharing: Others can see your current camera center and zoom.
	•	Selections: (If wired) selecting glyphs broadcasts your selection to collaborators.

⸻

7) Developer Guide (extending safely)

Add a new overlay
	1.	Create a React component (e.g., EmotionPulseOverlay already exists).
	2.	Pass minimal props (positions, ids) — do not mutate global state inside overlay.
	3.	Add it under the appropriate canvas block (Real or Dream). Guard it with boolean flags.

Add a new plugin tool (Toolchain C*)
	•	Add trigger points (buttons or hotkeys) in the HUD; wire API calls.
	•	Surface results by:
	•	pushing to Yjs via applyOp.addNode/addLink/addBeam, or
	•	broadcasting via broadcast_qfc_update(result) to keep legacy flows working.

Add a new API
	•	Return shapes consistent with SGR: { nodes, links }.
	•	Annotate with optional goalType, memoryTrace, entropy, etc.
	•	If it should update live, broadcast_qfc_update(...) with those nodes/links or write them into the Yjs doc from the backend.

⸻

8) Troubleshooting (fast fixes)
	•	Bottom of file “greyed out”: Almost always an unmatched JSX bracket or a stray character after </> and before );. Ensure only one return ( ... ) in each component and no extra );d or similar trailing junk.
	•	Duplicate const nodes/links identifiers: Make sure you only define them once per scope. When switching to collaborative data, remove old duplicates.
	•	Next.js “output: export” errors: Do not set output: 'export' if you use API routes/middleware. Use the config above.
	•	y-websocket/bin/utils import error: Pin y-websocket@1.5.4 and keep the type shim in types/.
	•	drei peer dep conflict: Use @react-three/drei@9.93.0 with React 18.
	•	ts-node “NodeNext” error: The collab tsconfig already sets module/moduleResolution to NodeNext.
	•	Multiple lockfiles: Keep one (root package-lock.json). Delete frontend/yarn.lock.

⸻

9) Validation Checklist
	•	Run:

npm install
npm run dev

You should see:
	•	🔗 Collab server listening on ws://0.0.0.0:1234
	•	Next.js dev server ready at http://localhost:3000

	•	Open two browser tabs on the same container route:
	•	Move camera in tab A → presence viewport propagates to tab B (cursor + awareness).
	•	Inject a scroll (HUD or drag-drop) → new glyphs/links appear in both tabs.
	•	Toggle overlays, switch split view, export JSON — no errors.

⸻

10) File Pointers (quick index)
	•	Core Canvas: frontend/components/Hologram/quantum_field_canvas.tsx
	•	Presence UI: collab/PresenceLayer.tsx
	•	Shared State (hook): collab/useSharedField.ts
	•	Collab Server: server/collab-server.ts
	•	Type shim: types/y-websocket-utils.d.ts
	•	QWave Beam renderer: components/QuantumField/beam_renderer
	•	Overlays & trails: components/QuantumField/*
	•	Loader: QuantumFieldCanvasLoader (in same file as QFC)

⸻

That’s the whole system: QFC visualizes and manipulates a symbolic memory graph, overlays cognition signals, records sessions, exports snapshots, and now supports multi-user collaboration via Yjs with presence. If you stick to the shapes and extension patterns above, you can add new overlays, tools, or APIs without breaking the core.

