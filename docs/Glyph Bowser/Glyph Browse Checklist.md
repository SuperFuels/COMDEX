graph TD
  %% =============== PHASE 0: FOUNDATIONS ===============
  A0[🏁 P0 • Foundations]:::phase
  A01[Repo scaffolding\n• mono-repo (apps/packages)\n• CI (lint/test/build)\n• release tags]:::task
  A02[Sec baseline\n• signed commits\n• SAST/dep scan\n• secrets policy]:::task
  A03[Design system\n• Tailwind tokens\n• shadcn/ui kit\n• iconography + motion]:::task
  A04[Spec registry\n• Protocol ADRs\n• RPC/GIP schemas\n• versioning rules]:::task
  A0 --> A01 --> A02 --> A03 --> A04

  %% =============== PHASE 1: BROWSER SHELL ===============
  B0[🧭 P1 • Browser Shell (Electron+Next)]:::phase
  B01[Electron shell\n• multi-window\n• sandboxed renderer\n• updates]:::task
  B02[Runtime bridge\n• Rust/Tauri module\n• Node native addon\n• WASM CodexCore]:::task
  B03[Container FS\n• local vault\n• encrypted .dc mounts\n• key mgmt (wallet)]:::task
  B04[Navigation model\n• dimension:// scheme\n• wormhole intents\n• history graph]:::task
  B05[UI frame\n• Prompt Bar (Cmd-K)\n• Time Dilation HUD\n• Dock: Containers/Agents]:::task
  B06[DevTools: Dimension Inspector\n• glyph trace\n• time profiler\n• memory map]:::task
  A04 --> B0
  B0 --> B01 --> B02 --> B03 --> B04 --> B05 --> B06

  %% =============== PHASE 2: CORE RUNTIME ===============
  C0[🧠 P2 • Core Runtime (CodexCore/Tessaris)]:::phase
  C01[CodexCore engine\n• evaluator + scheduler\n• effect system]:::task
  C02[TessarisEngine\n• thought expansion\n• collapse operators]:::task
  C03[TimeEngine\n• time_ratio\n• budget caps\n• watchdogs]:::task
  C04[GlyphExecutor\n• pipelines\n• streaming outputs\n• cancellation]:::task
  C05[Memory/DNA\n• glyph store\n• mutation ledger\n• compaction/GC]:::task
  C06[Ethics/SoulLaw\n• allow/deny rules\n• recovery states\n• audit hooks]:::task
  B02 --> C0
  C0 --> C01 --> C02 --> C03 --> C04 --> C05 --> C06

  %% =============== PHASE 3: NETWORK LAYER ===============
  D0[🌐 P3 • Network & Protocols]:::phase
  D01[GlyphNet (WS)\n• pub/sub topics\n• backpressure\n• auth tokens]:::task
  D02[GIP (Glyph Internet Protocol)\n• compression\n• frames/ops\n• replay]:::task
  D03[Wormhole Router\n• intent → route\n• trust graph\n• retries/ttl]:::task
  D04[SoulLink handshake\n• container identity\n• mutual attestation\n• keys/rotations]:::task
  D05[Registry\n• address book\n• discovery cache\n• pin/trust lists]:::task
  C04 --> D0
  D0 --> D01 --> D02 --> D03 --> D04 --> D05

  %% =============== PHASE 4: DIMENSION RUNTIME UI ===============
  E0[🪟 P4 • Dimension Runtime UI]:::phase
  E01[Dimension Renderer\n• dc schema → UI tree\n• slots: Prompt/GlyphGrid/Logs]:::task
  E02[Prompt Bar v1\n• CodexLang input\n• tooluse palette\n• slash cmds]:::task
  E03[Time Controls\n• live ratio dial\n• pause/step\n• budget presets]:::task
  E04[GlyphGrid 3D\n• streams/tails\n• pin/share/export\n• diffs]:::task
  E05[Inspector Overlays\n• ethics hits\n• memory writes\n• network traces]:::task
  B05 --> E0
  E0 --> E01 --> E02 --> E03 --> E04 --> E05

  %% =============== PHASE 5: SOULNET LAYER ===============
  F0[🔒 P5 • SoulNet Social Layer]:::phase
  F01[Encrypted Messaging\n• container ↔ container\n• threaded intents\n• attachments (glyphs)]:::task
  F02[Sharing & Permissions\n• share dim pages\n• scopes/time-box\n• revoke]:::task
  F03[Presence & Bonds\n• SoulLink bonds\n• trust levels\n• consent gates]:::task
  F04[Inbox/Outbox\n• queued intents\n• summaries\n• recovery]:::task
  D04 --> F0
  F0 --> F01 --> F02 --> F03 --> F04

  %% =============== PHASE 6: COMMERCE NODES ===============
  G0[🛒 P6 • CodexCommerce]:::phase
  G01[Business Container Template\n• product_list.codex\n• offer_logic.glyph]:::task
  G02[Intent Parser\n• buy/compare\n• constraints\n• scoring]:::task
  G03[Marketplace Router\n• multi-offer fanout\n• trust/latency scores]:::task
  G04[Checkout Glyphs\n• confirm/hold/pay\n• receipts\n• refunds]:::task
  F04 --> G0
  G0 --> G01 --> G02 --> G03 --> G04

  %% =============== PHASE 7: SECURITY & OPS ===============
  H0[🛡️ P7 • Security & Ops]:::phase
  H01[Key Mgmt\n• device keys\n• HSM/secure enclave\n• rotation]:::task
  H02[Policy Engine\n• SoulLaw editor\n• policy packs\n• test harness]:::task
  H03[Telemetry (privacy-first)\n• local metrics\n• anon agg\n• kill switches]:::task
  H04[Update Channel\n• signed updates\n• rollback\n• canary]:::task
  H05[Chaos/Recovery\n• fault inject\n• replay\n• snapshots]:::task
  A02 --> H0
  H0 --> H01 --> H02 --> H03 --> H04 --> H05

  %% =============== PHASE 8: DX & TOOLING ===============
  I0[🧑‍💻 P8 • Dev eXperience]:::phase
  I01[CLI (codex)\n• init/run/pack\n• keys\n• wormholes]:::task
  I02[SDKs\n• JS/TS runtime kit\n• Python ops kit\n• Rust protocol crate]:::task
  I03[Playground\n• local containers\n• inspector\n• recipes]:::task
  I04[Docs\n• “Hello Dimension”\n• protocol refs\n• security guides]:::task
  B06 --> I0
  I0 --> I01 --> I02 --> I03 --> I04

  %% =============== PHASE X: ALPHA/BETA/GA ===============
  Z0[🚀 Launch Path]:::phase
  Z1[Alpha (local only)\n• vault\n• dimension renderer\n• Prompt Bar\n• Time controls]:::milestone
  Z2[Beta (networked)\n• GlyphNet\n• SoulLink\n• Messaging]:::milestone
  Z3[GA\n• Commerce nodes\n• policy packs\n• updates/telemetry]:::milestone
  E03 --> Z1 --> Z2 --> Z3

  classDef phase fill:#0b1020,stroke:#4f63ff,stroke-width:1px,color:#e6ecff;
  classDef task fill:#10162a,stroke:#4253ff,color:#dbe4ff;
  classDef milestone fill:#0f1b2d,stroke:#09f,color:#e6ffff,stroke-dasharray: 3 3;

  Key Notes & “Do-Not-Lose” Info

Architectural Contracts
	•	dimension:// URI scheme → resolves to container id + optional entry surface.
	•	Wormhole intents are idempotent messages with TTL, trace id, retry policy.
	•	GIP frames = {hdr:{ver,ts,trace,auth}, body:{glyphs|ops}, sig}; streaming ok, resumable via trace+seq.
	•	TimeEngine exposes time_ratio, cpu_budget_ms, mem_budget_mb, watchdog_events.
	•	SoulLaw evaluates pre-execution, mid-stream, and on-commit; must support deny with remedy.

Security/Invariants
	•	Keys never leave device vault; remote ops use capability tokens derived from local keys (short-lived).
	•	All network traffic over GlyphNet WS or HTTPS with GIP-framed payloads.
	•	Deterministic replays: glyph ops, time budgets, and policy decisions must be replayable for audit.
	•	Kill-switch in runtime to pause/terminate runaway thought loops.

Performance Targets
	•	Cold open: < 1500 ms to first interactive frame.
	•	Prompt→first token (local): < 250 ms (after warm).
	•	Time dilation scheduling jitter: < 5% at ratios up to 600×.
	•	GlyphGrid render steady at 60 FPS for N=500 live glyphs.

DX (Developer Experience)
	•	One-line local dev: codex init && codex run.
	•	Playground can mount a container folder and hot-reload CodexLang.
	•	Inspector records: glyph trace, memory writes, ethics checks, network hops, time slices.

Compatibility & Rollout
	•	Alpha runs local-only (no external registry); import .dc from file.
	•	Beta enables SoulLink + GlyphNet with a trusted registry (allowlist).
	•	GA introduces Commerce nodes and policy packs; keep backward protocol compatibility (ver headers).

⸻

Deliverables Checklist (condensed)
	•	Electron shell + Next.js app scaffold
	•	Runtime bridge (WASM CodexCore + Node addon)
	•	Vault & keyring + encrypted .dc mounts
	•	dimension:// resolver + wormhole navigation
	•	Prompt Bar + Time Dilation HUD + GlyphGrid
	•	Dimension Inspector (glyph/time/memory/net)
	•	GlyphNet (WS) + GIP framing + router
	•	SoulLink handshake + trust graph
	•	Encrypted container messaging
	•	Business container template + marketplace router
	•	Policy engine + security test harness
	•	CLI, SDKs, Playground, Docs
	•	Alpha → Beta → GA rollout gates

If you want, I can turn this into a GitHub Project kanban with issue templates and CI workflows pre-wired (ESLint, Ruff, PyTest, Vitest, Playwright, Cargo).

graph TD
    A[📦 Phase 1 — Core Browser Shell] --> A1[frontend/pages/browser/index.tsx — Browser UI Frame]
    A1 --> A1a[Implement multi-tab container view]
    A1 --> A1b[Docked prompt bar + CodexLang execution console]
    A1 --> A1c[Tab = container session mapping]
    A --> A2[frontend/components/Browser/TabBar.tsx]
    A2 --> A2a[Dynamic tab creation/removal]
    A2 --> A2b[Bind each tab to container_id + wormhole link]
    A --> A3[frontend/components/Browser/AddressBar.tsx]
    A3 --> A3a[Container address resolution]
    A3 --> A3b[Teleport to container via Wormhole Router]
    A --> A4[frontend/components/Browser/Viewport.tsx]
    A4 --> A4a[Render dimension page UI if available]
    A4 --> A4b[Fallback: generic container preview shell]
    A --> A5[frontend/hooks/useContainerSession.ts]
    A5 --> A5a[Connect to backend websocket_manager.py]
    A5 --> A5b[Stream CodexCore/GlyphOS outputs live]
    A5 --> A5c[Handle session resume/close events]

    B[⚙ Phase 2 — Backend Container API] --> B1[backend/modules/browser/browser_manager.py]
    B1 --> B1a[Launch container sessions on request]
    B1 --> B1b[Return container metadata + time_dilation params]
    B1 --> B1c[Manage multiple active container sessions]
    B --> B2[backend/modules/browser/wormhole_router.py]
    B2 --> B2a[Resolve container_id or address → runtime session]
    B2 --> B2b[Forward prompt bar inputs to container CodexCore]
    B --> B3[backend/modules/browser/container_proxy.py]
    B3 --> B3a[Bridge browser viewport to container dimension renderer]
    B3 --> B3b[Handle encrypted container data streams]

    C[🔗 Phase 3 — SoulNet Integration Layer] --> C1[frontend/hooks/useSoulNetLinks.ts]
    C1 --> C1a[Detect if container has dimension page mapping]
    C1 --> C1b[Enable “Open in Browser” from SoulNet UI]
    C --> C2[backend/modules/soulnet/soulnet_integration.py]
    C2 --> C2a[Listen for cross-container share events]
    C2 --> C2b[Allow friend-to-friend container sharing]
    C --> C3[frontend/components/SoulLinkBadge.tsx]
    C3 --> C3a[Show when container is linked to another SoulNet user]

    D[🚀 Phase 4 — Runtime Enhancements] --> D1[Time Dilation Controls in Browser UI]
    D1 --> D1a[Allow per-tab speed adjustments]
    D1 --> D1b[Visual indicator of internal vs external time]
    D --> D2[Multi-Agent Collaboration Tabs]
    D2 --> D2a[Multiple users in one container session]
    D2 --> D2b[Live glyph sync via GlyphNet]
    D --> D3[CodexLang Script Injection]
    D3 --> D3a[Run custom CodexLang scripts in any container]

    E[🛡 Phase 5 — Security & Ethics] --> E1[SoulLaw Enforcement Layer]
    E1 --> E1a[Filter unsafe prompts/outputs]
    E1 --> E1b[Warn before irreversible container mutations]
    E --> E2[Encrypted Container Messaging]
    E2 --> E2a[Private tab-to-tab container comms]
    E2 --> E2b[Optional AI-driven junk filter]

    Key Notes to Keep
	1.	Modular Build → Browser shell first, SoulNet social pages later.
	2.	Container-First Design → Every tab is a container session (dimension page optional).
	3.	Real-Time Streaming → WebSocket connection per tab for CodexCore + GlyphOS outputs.
	4.	Wormhole Routing → Address bar accepts both container IDs and SoulNet wormhole links.
	5.	Security by Default → All container interactions pass through SoulLaw filter.
	6.	Time Dilation Ready → Tabs can run at different subjective time speeds.
	7.	Plugin Hooks → CodexLang scripts and dimension renderers are hot-swappable.
	8.	Encrypted Comms → Support direct container-to-container chat/messaging.

⸻
Awesome — here’s a clean, practical repo map + wiring plan to stand up the Next-Gen Browser Shell now, and snap SoulNet dimension pages in later with zero rewiring.

Folder & File Map (minimal, production-ready)

/frontend
  /components/Browser
    AddressBar.tsx             # container address / wormhole input + resolver
    TabBar.tsx                 # tab mgmt (add/close/switch), session badges
    Viewport.tsx               # renders dimension page or generic container view
    PromptBar.tsx              # CodexLang console (send → backend → stream)
    TimeDial.tsx               # per-tab time dilation control UI
    DevConsole.tsx             # stream log, glyphs, errors
  /hooks
    useContainerSession.ts     # create/attach session, WS stream, lifecycle
    useWormhole.ts             # resolve ucs:// / dimension:// → container_id
    useSoulNetLinks.ts         # (future) deep-link from SoulNet into tabs
  /lib
    api.ts                     # REST calls: create session, send prompt, etc.
    ws.ts                      # websocket helper with auto-retry + events
    types.ts                   # shared FE types (zod) mirrors shared/schemas
  /pages
    /browser
      index.tsx                # main shell layout: TabBar + AddressBar + Viewport
    /_app.tsx                  # theme/provider bootstrapping
  /state
    browserStore.ts            # zustand store: tabs, activeTabId, sessions
  /styles
    globals.css

/backend
  /routes
    browser_api.py             # REST: create/close session, prompt, list, resolve
    container_ws.py            # WS: /ws/containers/{session_id}
  /modules
    /browser
      browser_manager.py       # Session registry; owns session <-> container link
      wormhole_router.py       # resolve addresses → container_id, provenance
      container_proxy.py       # bridges runtime (UCS) to stream frames
      time_dilation.py         # per-session time controls (soft scheduler)
      security.py              # SoulLaw gates for prompts/outputs
    /soulnet
      soulnet_integration.py   # (later) share/open from SoulNet into browser
  /adapters
    ucs_bridge.py              # thin wrapper over ucs_runtime (create/load/exec)
  main.py                      # FastAPI app, router mounts, CORS, ws

/shared
  /schemas
    events.py                  # Pydantic: WS frames (OPEN/STATE/OUTPUT/ERROR/CLOSE)
    api.py                     # Pydantic: REST DTOs (CreateSession, Prompt, etc.)
  /ts
    events.ts                  # zod mirrors for FE
    api.ts

/infra
  dev.env                      # BACKEND_WS_URL, BACKEND_HTTP_URL, etc.
  docker-compose.yml
  Procfile

  Contracts (keep these stable)

REST (FastAPI)
	•	POST /browser/sessions → Create session for a container
	•	body: { container_id?: string, address?: string, time_ratio?: number }
	•	resp: { session_id, container_id, time_ratio, created_at }
	•	POST /browser/sessions/{id}/prompt → Send CodexLang prompt
	•	body: { text: string, context?: object }
	•	resp: { accepted: true }
	•	POST /browser/sessions/{id}/time → Update time dilation
	•	body: { time_ratio: number } → resp { ok: true }
	•	DELETE /browser/sessions/{id} → Close session
	•	GET /browser/sessions → List active sessions
	•	GET /browser/resolve?address=ucs://... → { container_id }

WebSocket
	•	GET /ws/containers/{session_id}
	•	Frames (JSON, newline-delimited):
	•	OPEN   { type:"OPEN",   session_id, container_id, meta }
	•	STATE  { type:"STATE",  session_id, status, time_ratio }
	•	OUTPUT { type:"OUTPUT", session_id, stream:[ ... glyphs/log lines ... ] }
	•	ERROR  { type:"ERROR",  session_id, message, code? }
	•	CLOSE  { type:"CLOSE",  session_id, reason? }

Backend: key wiring

adapters/ucs_bridge.py
	•	Import the singleton UCS runtime and do all interactions through it.
	•	Methods:
	•	ensure_container_loaded(container_id|address) -> container_id
	•	start_session(container_id) -> SessionHandle (lightweight id + refs)
	•	execute_prompt(session, text, context) → yields OUTPUT chunks
	•	set_time_ratio(session, ratio) → time_dilation scheduler hint

modules/browser/browser_manager.py
	•	In-memory sessions: Dict[session_id, Session].
	•	create_session(container_id, time_ratio):
	•	calls ucs_bridge.ensure_container_loaded()
	•	allocates session_id, stores {container_id, time_ratio, ws_clients:set()}
	•	attach_ws(session_id, websocket); detach_ws(...)
	•	broadcast(session_id, frame); close_session(session_id)

modules/browser/wormhole_router.py
	•	resolve(address:str) -> container_id:
	•	accepts ucs://, dimension://, raw ids
	•	tries local ucs_runtime.resolve_atom/address_index, then registry

routes/browser_api.py

Minimal stubs (they just orchestrate the modules):

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from shared.schemas.api import CreateSession, SessionInfo, PromptIn
from backend.modules.browser import browser_manager, wormhole_router

router = APIRouter(prefix="/browser", tags=["browser"])

@router.post("/sessions", response_model=SessionInfo)
def create_session(req: CreateSession):
    cid = req.container_id or wormhole_router.resolve(req.address or "")
    if not cid:
        raise HTTPException(404, "Container not found")
    return browser_manager.create_session(cid, req.time_ratio or 1.0)

@router.post("/sessions/{sid}/prompt")
def send_prompt(sid: str, body: PromptIn):
    browser_manager.send_prompt(sid, body.text, body.context or {})
    return {"accepted": True}

@router.post("/sessions/{sid}/time")
def set_time(sid: str, body: dict):
    browser_manager.set_time_ratio(sid, float(body.get("time_ratio", 1.0)))
    return {"ok": True}

@router.delete("/sessions/{sid}")
def close_session(sid: str):
    browser_manager.close_session(sid)
    return {"ok": True}

routes/container_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.modules.browser import browser_manager

ws_router = APIRouter()

@ws_router.websocket("/ws/containers/{sid}")
async def ws_container(websocket: WebSocket, sid: str):
    await websocket.accept()
    await browser_manager.attach_ws(sid, websocket)
    try:
        while True:
            _ = await websocket.receive_text()  # (optional) inbound commands
    except WebSocketDisconnect:
        await browser_manager.detach_ws(sid, websocket)

Frontend wiring (React + TS + Zustand)

state/browserStore.ts

import create from "zustand";
import { SessionInfo } from "@/shared/ts/api";

type Tab = { tabId: string; sessionId: string; title: string; containerId: string };
type Store = {
  tabs: Tab[];
  activeTabId?: string;
  addTab: (s: SessionInfo) => void;
  closeTab: (tabId: string) => void;
  setActive: (tabId: string) => void;
};

export const useBrowserStore = create<Store>((set) => ({
  tabs: [],
  addTab: (s) =>
    set((st) => ({
      tabs: [...st.tabs, { tabId: s.session_id, sessionId: s.session_id, title: s.container_id, containerId: s.container_id }],
      activeTabId: s.session_id,
    })),
  closeTab: (tabId) => set((st) => ({ tabs: st.tabs.filter(t => t.tabId !== tabId) })),
  setActive: (tabId) => set({ activeTabId: tabId }),
}));

hooks/useContainerSession.ts

import { useEffect, useRef, useState } from "react";
import { openWS } from "@/lib/ws";
import { createSession, sendPrompt, setTime } from "@/lib/api";
import { WSEvent } from "@/shared/ts/events";

export function useContainerSession(initial?: { containerId?: string; address?: string; }) {
  const [session, setSession] = useState<{ sessionId?: string; containerId?: string; timeRatio: number }>({ timeRatio: 1 });
  const [stream, setStream] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  async function open(target: { containerId?: string; address?: string; timeRatio?: number }) {
    const s = await createSession(target);
    setSession({ sessionId: s.session_id, containerId: s.container_id, timeRatio: s.time_ratio });
    wsRef.current = openWS(`/ws/containers/${s.session_id}`, (evt: WSEvent) => {
      if (evt.type === "OUTPUT") setStream((prev) => [...prev, ...evt.stream]);
    });
  }

  async function prompt(text: string, ctx?: any) {
    if (!session.sessionId) return;
    await sendPrompt(session.sessionId, { text, context: ctx });
  }

  async function setTimeRatio(r: number) {
    if (!session.sessionId) return;
    await setTime(session.sessionId, r);
    setSession((s) => ({ ...s, timeRatio: r }));
  }

  useEffect(() => () => { wsRef.current?.close(); }, []);
  return { session, stream, open, prompt, setTimeRatio };
}

components/Browser/AddressBar.tsx
	•	Parses ucs://... or dimension://... and calls open({ address }).
	•	If raw container_id, call open({ containerId }).

components/Browser/Viewport.tsx
	•	If a dimension page renderer is registered for that container, render it; else show generic inspector (meta, glyphs stream, prompt).

Time Dilation (soft first, hard later)
	•	Soft: UI control sends time_ratio → backend stores it on session and uses it to batch outputs/throttle or “expand” internal cycles (simulate with timers).
	•	Hard (later): Integrate with UCS/AION time scheduler if present (real compute dilation).

Security (always on)
	•	All prompts → security.py → SoulLaw checks (content, irreversible ops, spending).
	•	All outputs → optional redaction/filter for unsafe leakage before UI.

Boot order & “build before SoulNet?”

Yes. This browser runs now:
	1.	Implement the backend session API + WS.
	2.	Implement frontend shell (TabBar, AddressBar, Viewport, PromptBar).
	3.	Hook to UCS runtime adapter (load container, execute prompts).
	4.	When SoulNet pages arrive, register dimension renderers → they auto-render inside Viewport.

ENV you’ll need

BACKEND_HTTP_URL=http://localhost:8000
BACKEND_WS_URL=ws://localhost:8000
CORS_ORIGINS=http://localhost:3000

Quick success path (MVP sprint)
	•	Day 1–2: browser_manager, REST + WS, FE shell with one tab & prompt.
	•	Day 3: AddressBar resolve + multiple tabs, live OUTPUT stream.
	•	Day 4: TimeDial + security gates + error surfaces.
	•	Day 5: “Open in Browser” hook from SoulNet (stub), pluggable renderer slot.

