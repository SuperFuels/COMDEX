Backend (FastAPI)

/backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.browser_api import router as browser_router
from backend.routes.container_ws import ws_router

app = FastAPI(title="SoulNet Browser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(browser_router, prefix="/browser")
app.include_router(ws_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}





/backend/routes/browser_api.py

from fastapi import APIRouter, HTTPException
from shared.schemas.api import CreateSession, SessionInfo, PromptIn, SessionList
from backend.modules.browser.browser_manager import BrowserManager
from backend.modules.browser.wormhole_router import resolve_address

router = APIRouter(tags=["browser"])
manager = BrowserManager.shared()

@router.post("/sessions", response_model=SessionInfo)
def create_session(req: CreateSession):
    container_id = req.container_id
    if not container_id and req.address:
        container_id = resolve_address(req.address)
    if not container_id:
        raise HTTPException(404, "Container not found or resolvable")
    session = manager.create_session(container_id, time_ratio=req.time_ratio or 1.0)
    return SessionInfo(**session)

@router.post("/sessions/{sid}/prompt")
def send_prompt(sid: str, body: PromptIn):
    manager.enqueue_prompt(sid, body.text, body.context or {})
    return {"accepted": True}

@router.post("/sessions/{sid}/time")
def set_time(sid: str, body: dict):
    r = float(body.get("time_ratio", 1.0))
    manager.set_time_ratio(sid, r)
    return {"ok": True}

@router.delete("/sessions/{sid}")
def close_session(sid: str):
    manager.close_session(sid)
    return {"ok": True}

@router.get("/sessions", response_model=SessionList)
def list_sessions():
    return SessionList(items=[SessionInfo(**s) for s in manager.list_sessions()])







/backend/routes/container_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.modules.browser.browser_manager import BrowserManager

ws_router = APIRouter()
manager = BrowserManager.shared()

@ws_router.websocket("/ws/containers/{sid}")
async def ws_container(websocket: WebSocket, sid: str):
    await websocket.accept()
    await manager.attach_ws(sid, websocket)
    try:
        while True:
            # Optional: receive inbound commands (not needed for MVP)
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.detach_ws(sid, websocket)






/backend/modules/browser/browser_manager.py

import asyncio, uuid
from typing import Dict, Any, List, Set
from fastapi import WebSocket
from shared.schemas.events import WSEventOpen, WSEventState, WSEventOutput, WSEventError, WSEventClose
from backend.adapters.ucs_bridge import UCSBridge

class BrowserManager:
    _instance = None

    @classmethod
    def shared(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.ws_clients: Dict[str, Set[WebSocket]] = {}
        self.ucs = UCSBridge()

    # ---- lifecycle ----
    def create_session(self, container_id: str, time_ratio: float = 1.0) -> Dict[str, Any]:
        sid = str(uuid.uuid4())
        self.ucs.ensure_loaded(container_id)
        self.sessions[sid] = {
            "session_id": sid,
            "container_id": container_id,
            "time_ratio": time_ratio,
            "created_at": asyncio.get_event_loop().time(),
        }
        self.ws_clients[sid] = set()
        return self.sessions[sid]

    def list_sessions(self) -> List[Dict[str, Any]]:
        return list(self.sessions.values())

    async def attach_ws(self, sid: str, ws: WebSocket):
        if sid not in self.sessions:
            await ws.send_json(WSEventError(type="ERROR", session_id=sid, message="Unknown session").model_dump())
            await ws.close()
            return
        self.ws_clients[sid].add(ws)
        s = self.sessions[sid]
        await ws.send_json(WSEventOpen(type="OPEN", session_id=sid, container_id=s["container_id"], meta={}).model_dump())
        await ws.send_json(WSEventState(type="STATE", session_id=sid, status="ready", time_ratio=s["time_ratio"]).model_dump())

    async def detach_ws(self, sid: str, ws: WebSocket):
        self.ws_clients.get(sid, set()).discard(ws)

    def set_time_ratio(self, sid: str, r: float):
        if sid in self.sessions:
            self.sessions[sid]["time_ratio"] = max(0.1, min(r, 1000.0))
            asyncio.create_task(self._broadcast(sid, WSEventState(type="STATE", session_id=sid, status="ready", time_ratio=self.sessions[sid]["time_ratio"]).model_dump()))

    def close_session(self, sid: str):
        if sid in self.sessions:
            asyncio.create_task(self._broadcast(sid, WSEventClose(type="CLOSE", session_id=sid, reason="closed by server").model_dump()))
            del self.sessions[sid]
            self.ws_clients.pop(sid, None)

    # ---- actions ----
    def enqueue_prompt(self, sid: str, text: str, context: Dict[str, Any]):
        if sid not in self.sessions:
            return
        session = self.sessions[sid]
        container_id = session["container_id"]
        time_ratio = session["time_ratio"]
        # Run async so REST returns immediately
        asyncio.create_task(self._execute_and_stream(sid, container_id, text, context, time_ratio))

    async def _execute_and_stream(self, sid: str, container_id: str, text: str, context: Dict[str, Any], time_ratio: float):
        try:
            async for chunk in self.ucs.execute_prompt_stream(container_id, text, context, time_ratio=time_ratio):
                await self._broadcast(sid, WSEventOutput(type="OUTPUT", session_id=sid, stream=[chunk]).model_dump())
        except Exception as e:
            await self._broadcast(sid, WSEventError(type="ERROR", session_id=sid, message=str(e)).model_dump())

    # ---- broadcast ----
    async def _broadcast(self, sid: str, frame: Dict[str, Any]):
        dead = []
        for ws in self.ws_clients.get(sid, set()):
            try:
                await ws.send_json(frame)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.detach_ws(sid, ws)





/backend/modules/browser/wormhole_router.py

from typing import Optional
from backend.adapters.ucs_bridge import UCSBridge

_bridge = UCSBridge()

def resolve_address(address: Optional[str]) -> Optional[str]:
    if not address: return None
    # Basic heuristics: accept raw id, ucs://..., dimension://...
    if address.startswith("ucs://") or address.startswith("dimension://"):
        cid = _bridge.resolve(address)
        return cid
    return address  # assume it's already an id






/backend/adapters/ucs_bridge.py
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any

class UCSBridge:
    """
    Thin adapter over UCS runtime.
    Uses optional methods if present; falls back to no-ops/stubs for MVP.
    """
    def __init__(self):
        try:
            from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
            self.ucs = get_ucs_runtime()
        except Exception:
            self.ucs = None

    def ensure_loaded(self, container_id: str):
        # If you have a loader, call it here. For MVP, assume already available.
        return container_id

    def resolve(self, key: str) -> Optional[str]:
        try:
            if hasattr(self.ucs, "resolve_atom"):
                return self.ucs.resolve_atom(key)
        except Exception:
            pass
        return None

    async def execute_prompt_stream(self, container_id: str, text: str, context: Dict[str, Any], time_ratio: float = 1.0) -> AsyncGenerator[str, None]:
        """
        Stub stream: emits a few fake chunks. Replace with real runtime execution call.
        """
        # Example of yielding chunks (simulate dilation)
        yield f"[{container_id}] » {text}"
        await asyncio.sleep(0.05)
        yield f"(context: {list(context.keys()) or '∅'}, time×{time_ratio:g})"
        await asyncio.sleep(0.05)
        yield "…execution complete."





/shared/schemas/events.py

from pydantic import BaseModel
from typing import Dict, List, Optional

class WSEventBase(BaseModel):
    type: str
    session_id: str

class WSEventOpen(WSEventBase):
    container_id: str
    meta: Dict = {}

class WSEventState(WSEventBase):
    status: str
    time_ratio: float

class WSEventOutput(WSEventBase):
    stream: List[str]

class WSEventError(WSEventBase):
    message: str
    code: Optional[str] = None

class WSEventClose(WSEventBase):
    reason: Optional[str] = None

    




/shared/schemas/api.py

from pydantic import BaseModel
from typing import Optional, List

class CreateSession(BaseModel):
    container_id: Optional[str] = None
    address: Optional[str] = None
    time_ratio: Optional[float] = 1.0

class SessionInfo(BaseModel):
    session_id: str
    container_id: str
    time_ratio: float
    created_at: float

class PromptIn(BaseModel):
    text: str
    context: dict | None = None

class SessionList(BaseModel):
    items: List[SessionInfo]






Frontend (React + TS)

Assumes Next.js or Vite + React. Adjust imports as needed.

/frontend/shared/ts/events.ts

export type WSEvent =
  | { type: "OPEN"; session_id: string; container_id: string; meta: any }
  | { type: "STATE"; session_id: string; status: string; time_ratio: number }
  | { type: "OUTPUT"; session_id: string; stream: string[] }
  | { type: "ERROR"; session_id: string; message: string; code?: string }
  | { type: "CLOSE"; session_id: string; reason?: string };






/frontend/lib/api.ts

const API = process.env.NEXT_PUBLIC_BACKEND_HTTP_URL || "http://localhost:8000";

export async function createSession(body: { containerId?: string; address?: string; time_ratio?: number }) {
  const r = await fetch(`${API}/browser/sessions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
    container_id: body.containerId, address: body.address, time_ratio: body.time_ratio,
  })});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function sendPrompt(sessionId: string, body: { text: string; context?: any }) {
  const r = await fetch(`${API}/browser/sessions/${sessionId}/prompt`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function setTime(sessionId: string, time_ratio: number) {
  const r = await fetch(`${API}/browser/sessions/${sessionId}/time`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ time_ratio }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}









/frontend/lib/ws.ts

const WS = process.env.NEXT_PUBLIC_BACKEND_WS_URL || "ws://localhost:8000";
import type { WSEvent } from "@/shared/ts/events";

export function openWS(path: string, onEvent: (evt: WSEvent) => void) {
  const ws = new WebSocket(`${WS}${path}`);
  ws.onmessage = (m) => {
    try { onEvent(JSON.parse(m.data)); } catch {}
  };
  return ws;
}








/frontend/state/browserStore.ts


import { create } from "zustand";

type Tab = { tabId: string; sessionId: string; title: string; containerId: string };
type Store = {
  tabs: Tab[];
  activeTabId?: string;
  addTab: (s: { session_id: string; container_id: string }) => void;
  closeTab: (tabId: string) => void;
  setActive: (tabId: string) => void;
};

export const useBrowserStore = create<Store>((set) => ({
  tabs: [],
  addTab: (s) => set((st) => ({
    tabs: [...st.tabs, { tabId: s.session_id, sessionId: s.session_id, title: s.container_id, containerId: s.container_id }],
    activeTabId: s.session_id
  })),
  closeTab: (tabId) => set((st) => ({ tabs: st.tabs.filter(t => t.tabId !== tabId), activeTabId: st.activeTabId === tabId ? st.tabs[0]?.tabId : st.activeTabId })),
  setActive: (tabId) => set({ activeTabId: tabId }),
}));








/frontend/hooks/useContainerSession.ts

import { useEffect, useRef, useState } from "react";
import { openWS } from "@/lib/ws";
import { createSession, sendPrompt, setTime } from "@/lib/api";
import type { WSEvent } from "@/shared/ts/events";

export function useContainerSession() {
  const [session, setSession] = useState<{ sessionId?: string; containerId?: string; timeRatio: number }>({ timeRatio: 1 });
  const [stream, setStream] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  async function open(target: { containerId?: string; address?: string; time_ratio?: number }) {
    const s = await createSession({ containerId: target.containerId, address: target.address, time_ratio: target.time_ratio });
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








/frontend/components/Browser/AddressBar.tsx


import { useState } from "react";

export function AddressBar({ onOpen }: { onOpen: (target: { address?: string; containerId?: string }) => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="flex gap-2 w-full">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="ucs://local/atom_maxwell#atom or container_id"
        className="flex-1 border rounded px-3 py-2"
      />
      <button onClick={() => onOpen(value.startsWith("ucs://") || value.startsWith("dimension://") ? { address: value } : { containerId: value })}
              className="px-3 py-2 rounded bg-black text-white">Open</button>
    </div>
  );
}







/frontend/components/Browser/PromptBar.tsx

import { useState } from "react";

export function PromptBar({ onSend }: { onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  return (
    <div className="flex gap-2">
      <input className="flex-1 border rounded px-3 py-2" value={text} onChange={(e)=>setText(e.target.value)} placeholder="Enter CodexLang / intent…"/>
      <button className="px-3 py-2 rounded bg-indigo-600 text-white" onClick={()=>{ if(text.trim()) onSend(text); }}>Send</button>
    </div>
  );
}





/frontend/components/Browser/TabBar.tsx

import { useBrowserStore } from "@/state/browserStore";

export function TabBar() {
  const { tabs, activeTabId, setActive, closeTab } = useBrowserStore();
  return (
    <div className="flex gap-2 border-b py-2 overflow-x-auto">
      {tabs.map(t => (
        <div key={t.tabId} className={`px-3 py-1 rounded cursor-pointer ${activeTabId===t.tabId ? "bg-gray-200" : "bg-gray-100"}`} onClick={()=>setActive(t.tabId)}>
          <span className="mr-2">{t.title}</span>
          <button onClick={(e)=>{ e.stopPropagation(); closeTab(t.tabId); }}>✕</button>
        </div>
      ))}
    </div>
  );
}








/frontend/components/Browser/Viewport.tsx

export function Viewport({ stream }: { stream: string[] }) {
  return (
    <div className="border rounded p-3 min-h-[300px] bg-white overflow-auto">
      {stream.length === 0 ? <div className="text-gray-400">No output yet.</div> :
        stream.map((line, i) => <div key={i} className="font-mono text-sm whitespace-pre-wrap">{line}</div>)
      }
    </div>
  );
}








/frontend/pages/browser/index.tsx

import { useContainerSession } from "@/hooks/useContainerSession";
import { useBrowserStore } from "@/state/browserStore";
import { AddressBar } from "@/components/Browser/AddressBar";
import { TabBar } from "@/components/Browser/TabBar";
import { PromptBar } from "@/components/Browser/PromptBar";
import { Viewport } from "@/components/Browser/Viewport";

export default function BrowserPage() {
  const { session, stream, open, prompt } = useContainerSession();
  const { addTab } = useBrowserStore();

  async function openTarget(target: { address?: string; containerId?: string }) {
    const s = await open(target);
    // useContainerSession doesn't return; but createSession returns tab from store in a fuller impl.
    // For MVP, we just keep single-tab view with working stream.
  }

  return (
    <div className="p-4 flex flex-col gap-4">
      <TabBar />
      <AddressBar onOpen={openTarget}/>
      <Viewport stream={stream}/>
      <PromptBar onSend={prompt}/>
    </div>
  );
}








Environment

Backend

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000


Frontend
# .env.local
NEXT_PUBLIC_BACKEND_HTTP_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000



Run your Next/Vite dev server at localhost:3000.

⸻

How SoulNet “plugs in” later
	•	When you ship a dimension page renderer for a container (e.g., maxwell.viewer.tsx), register it in a map keyed by container_id and render it inside Viewport instead of the generic console. No API changes needed.
	•	Replace UCSBridge.execute_prompt_stream stub with your true runtime (CodexCore/Tessaris/GlyphOS) call that yields chunks.






    