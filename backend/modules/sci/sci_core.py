# ============================================================
# 🧠 SCI Core - Spatial Cognition Interface + Photon Runtime Gateway
# ============================================================
# Combines the classical SCI workspace model (scrolls, tabs, QFC fields)
# with the new PhotonLang runtime engine for real-time execution,
# telemetry (.ptn) recording, and QFC visualization.

from __future__ import annotations
import os
import json
import asyncio
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================
# ⚙️ Base SCI Components
# ============================================================
from backend.modules.sci.scroll_engine import ScrollEngine
try:
    from backend.modules.photonlang.interpreter import QuantumFieldCanvas
except Exception:
    class QuantumFieldCanvas:
        def __init__(self, *_, **__): self.state = {}
        def resonate(self, seq, intensity=1.0): 
            print(f"[StubQFC] Resonating {seq} @ {intensity}")
            self.state["resonance"] = {"seq": seq, "intensity": intensity}
            return self.state["resonance"]
try:
    from backend.core.plugins.aion_engine_dock import AIONEngineDock as EngineDock
except Exception:
    class EngineDock:
        def __init__(self):
            print("[StubEngineDock] Using stubbed EngineDock (AION plugin not loaded)")
        def run(self, engine_type, field_id, params=None):
            print(f"[StubEngineDock] run({engine_type}, {field_id})")
            return {"status": "ok", "result": f"stub_output_for_{engine_type}"}
from backend.modules.sci.sci_file_manager import SCIFileManager

# ============================================================
# 🌐 Optional Runtime Bridges
# ============================================================
try:
    from backend.modules.photonlang.interpreter import run_source
except Exception:
    def run_source(source: str, **kwargs):
        print("⚠️ [Stub] Photon runtime not loaded.")
        return {"status": "stub", "source": source}

try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload, source="sci_core"):
        print(f"[StubQFC] Render skipped from {source}")

try:
    from backend.modules.photonlang.integrations.photon_telemetry_recorder import save_telemetry_snapshot
except Exception:
    def save_telemetry_snapshot(container_id, label, state, sqi_feedback, qqc_feedback):
        path = f"artifacts/telemetry/fake_snapshot_{datetime.utcnow().timestamp()}.ptn"
        print(f"[StubTelemetry] Would save -> {path}")
        return path

try:
    from backend.modules.sci.container_workspace_loader import update_active_workspace
except Exception:
    async def update_active_workspace(container_id: str, state: Dict[str, Any]):
        print(f"[StubSCI] Updated workspace {container_id} with new state {list(state.keys())}")

try:
    from backend.modules.sci.sci_qfc_export_bridge import broadcast_qfc_event
except Exception:
    async def broadcast_qfc_event(payload):
        try:
            # resolve any coroutine values in payload
            for k, v in list(payload.items()):
                if asyncio.iscoroutine(v):
                    payload[k] = await v
            print(f"[StubBroadcast] {json.dumps(payload, indent=2)}")
        except Exception as e:
            print(f"[StubBroadcast] ⚠️ Could not serialize payload: {e}")

class SCIRuntimeGateway:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls(container_id="sci_runtime_default")
        return cls._instance
# ============================================================
# 🧩 Spatial Cognition Interface
# ============================================================

class SpatialCognitionInterface:
    """Core runtime for SCI cognitive field management and scroll operations."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.scroll_engine = ScrollEngine(user_id)
        self.qfc = QuantumFieldCanvas()
        self.engine_dock = EngineDock()
        self.tab_manager = FieldTabManager()
        self.file_manager = SCIFileManager(user_id)
        self.active_field_id = None

    # ------------------------------------------------------------
    # Field / Tab Management
    # ------------------------------------------------------------
    def create_new_field(self, preset: Optional[str] = None) -> str:
        field_id = self.tab_manager.create_new_tab(preset)
        self.active_field_id = field_id
        self.qfc.initialize_field(field_id, preset=preset)
        return field_id

    def switch_to_field(self, field_id: str):
        if self.tab_manager.field_exists(field_id):
            self.active_field_id = field_id
            self.qfc.load_field(field_id)
        else:
            raise ValueError(f"Field '{field_id}' does not exist")

    # ------------------------------------------------------------
    # Scroll & Engine Injection
    # ------------------------------------------------------------
    def inject_scroll(self, scroll_id: str, target_field_id: Optional[str] = None):
        field_id = target_field_id or self.active_field_id
        if not field_id:
            raise RuntimeError("No active field to inject into")
        scroll_data = self.scroll_engine.fetch_scroll(scroll_id)
        self.qfc.inject_scroll(field_id, scroll_data)

    def run_engine(self, engine_type: str, field_id: Optional[str] = None, params: Optional[Dict] = None):
        field_id = field_id or self.active_field_id
        if not field_id:
            raise RuntimeError("No active field")
        engine_output = self.engine_dock.run(engine_type, field_id, params)
        self.qfc.apply_engine_output(field_id, engine_output)

    # ------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------
    def save_current_session(self):
        if not self.active_field_id:
            return
        field_data = self.qfc.export_field(self.active_field_id)
        self.file_manager.save_session(field_id=self.active_field_id, data=field_data)

    def load_saved_session(self, field_id: str):
        data = self.file_manager.load_session(field_id)
        self.qfc.load_field_from_data(field_id, data)
        self.active_field_id = field_id

    def export_all_fields(self) -> Dict[str, Any]:
        export = {}
        for field_id in self.tab_manager.list_all_tabs():
            export[field_id] = self.qfc.export_field(field_id)
        return export

    def shutdown(self):
        self.save_current_session()
        self.scroll_engine.shutdown()
        self.qfc.shutdown()
        self.engine_dock.shutdown()
        self.tab_manager.shutdown()


# ============================================================
# 🧬 SCI Runtime Gateway - PhotonLang Execution
# ============================================================

class SCIRuntimeGateway:
    """
    Central execution engine for PhotonLang inside the SCI IDE.
    Handles live execution, telemetry persistence, and visualization.
    """

    def __init__(self, container_id: str = "default_sci_container"):
        self.container_id = container_id

    # ============================================================
    # ▶ Execute Photon Source
    # ============================================================
    import asyncio
    import json
    import os
    import traceback
    from datetime import datetime
    from typing import Any, Dict, Optional

    async def run_photon_source(self, source: str, *, label: Optional[str] = "photon_exec") -> Dict[str, Any]:
        """Execute PhotonLang code from the SCI IDE editor."""
        print(f"⚙️ [SCI Runtime] Running Photon source ({len(source)} chars)...")

        try:
            # ------------------------------------------------------------
            # 1️⃣ Execute Photon source through interpreter
            # ------------------------------------------------------------
            result = run_source(source)
            if asyncio.iscoroutine(result):
                result = await result  # resolve coroutine safely

            if not isinstance(result, dict):
                result = {"status": "error", "result": str(result)}

            state = result.get("last", {})
            glyph_boot = result.get("glyph_boot", False)

            # ------------------------------------------------------------
            # 2️⃣ Save runtime telemetry snapshot (.ptn)
            # ------------------------------------------------------------
            telemetry_path = save_telemetry_snapshot(
                self.container_id,
                label or "photon_exec",
                state,
                {"sqi_score": 1.0},
                {"qqc_energy": 1.0},
            )

            # ------------------------------------------------------------
            # 3️⃣ Broadcast SQI / Resonance State for IDE meters
            # ------------------------------------------------------------
            try:
                current_sqi = float(state.get("sqi", 1.0))
                resonance_energy = float(state.get("resonance", 1.0))

                await broadcast_qfc_event({
                    "type": "sqi_state",
                    "data": {
                        "sqi_score": current_sqi,
                        "qqc_energy": resonance_energy,
                        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                        "container_id": self.container_id,
                    },
                })

                print(f"[SCI Runtime] ⚡ SQI broadcast -> SQI={current_sqi:.3f}, QQC={resonance_energy:.3f}")

                # ------------------------------------------------------------
                # 3️⃣b Auto-Commit High SQI State -> Knowledge Graph + Lean
                # ------------------------------------------------------------
                import aiohttp
                THRESHOLD = float(os.getenv("SCI_SQI_AUTOCOMMIT_THRESHOLD", "0.95"))
                BACKEND_URL = os.getenv("SCI_BACKEND_URL", "http://localhost:8080")

                if current_sqi >= THRESHOLD:
                    print(f"[AutoCommit] High SQI detected ({current_sqi:.3f}) - committing to Knowledge Graph...")

                    payload = {
                        "label": f"HarmonicAtom_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}",
                        "sqi": current_sqi,
                        "container_id": self.container_id,
                        "waveform": state.get("waveform") or state,
                        "user_id": getattr(self, "user_id", self.container_id),
                    }

                    async with aiohttp.ClientSession() as session:
                        url = f"{BACKEND_URL}/api/sci/commit_atom"
                        r = await session.post(url, json=payload)
                        if r.status != 200:
                            raise RuntimeError(f"commit_atom HTTP {r.status}: {await r.text()}")
                        resp = await r.json()
                        print(f"[AutoCommit] ✅ KG+Lean commit ok -> {resp.get('atom_ref')}")

            except Exception as e:
                print(f"[SCI Runtime] ⚠️ SQI broadcast or auto-commit failed: {e}")

            # ------------------------------------------------------------
            # 4️⃣ Persist execution result to Resonant Memory
            # ------------------------------------------------------------
            try:
                from backend.modules.resonant_memory.resonant_memory_saver import save_scroll_to_memory
                if asyncio.iscoroutine(state):
                    state = await state
                save_scroll_to_memory(
                    user_id=self.container_id,
                    label=f"photon_exec::{label}",
                    content=json.dumps(state, ensure_ascii=False, default=str),
                    metadata={
                        "glyph_boot": glyph_boot,
                        "telemetry_path": telemetry_path,
                        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                        "origin": "sci_runtime_gateway",
                    },
                )
            except Exception as e:
                print(f"[SCI Runtime] ⚠️ Failed to persist execution memory: {e}")

            # ------------------------------------------------------------
            # 5️⃣ Build runtime frame for SCI + QFC broadcast
            # ------------------------------------------------------------
            frame = {
                "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                "container_id": self.container_id,
                "state": state,
                "telemetry_path": telemetry_path,
                "glyph_boot": glyph_boot,
                "status": result.get("status", "ok"),
            }

            # ------------------------------------------------------------
            # 6️⃣ Broadcast to SCI & Quantum Field Canvas
            # ------------------------------------------------------------
            await broadcast_qfc_event({
                "type": "sci_runtime_frame",
                "frame": frame,
                "source": "sci_core",
            })
            await trigger_qfc_render({"type": "runtime_frame", "frame": frame}, source="sci_core")

            # ------------------------------------------------------------
            # 7️⃣ Update workspace container state
            # ------------------------------------------------------------
            await update_active_workspace(self.container_id, state)

            print(f"✅ [SCI Runtime] Photon execution complete -> {telemetry_path}")
            return {"ok": True, "frame": frame, "telemetry_path": telemetry_path}

        except Exception as e:
            err = traceback.format_exc()
            print(f"❌ [SCI Runtime Error]: {e}\n{err}")
            return {"ok": False, "error": str(e)}


    # ============================================================
    # 🧠 Workspace Update Stub (Safe for Async + Tests)
    # ============================================================
    async def update_active_workspace(container_id, state):
        """Safe async workspace state updater for SCI IDE / QFC."""
        if asyncio.iscoroutine(state):
            state = await state
        if not isinstance(state, dict):
            print(f"[StubSCI] ⚠ Unexpected state type: {type(state)}")
            state = {"_raw": str(state)}
        print(f"[StubSCI] Updated workspace {container_id} with new state {list(state.keys())}")
        return state
# ------------------------------------------------------------
# 🧠 FieldTabManager Stub (for SCI IDE multi-field sessions)
# ------------------------------------------------------------
class FieldTabManager:
    """Simple in-memory tab/session tracker for SCI IDE fields."""

    def __init__(self):
        self.tabs = {}
        self.active = None

    def create_new_tab(self, preset: str | None = None) -> str:
        field_id = f"field_{len(self.tabs) + 1}"
        self.tabs[field_id] = {"preset": preset or "default", "created": True}
        self.active = field_id
        print(f"[FieldTabManager] Created new field: {field_id}")
        return field_id

    def list_all_tabs(self):
        return list(self.tabs.keys())

    def field_exists(self, field_id: str) -> bool:
        return field_id in self.tabs

    def shutdown(self):
        print("[FieldTabManager] Tabs cleared.")
        self.tabs.clear()
        self.active = None
        
# ============================================================
# 🔧 Demo / CLI Test Harness
# ============================================================

async def _demo():
    gateway = SCIRuntimeGateway(container_id="test_sci_session")

    photon_code = """
AtomSheet("base").seed("⊕↔μ⟲")
canvas = QuantumFieldCanvas()
canvas.resonate("⊕↔μ⟲", intensity=0.9)
save_as_ptn("test_photon_exec", env=locals())
"""

    result = await gateway.run_photon_source(photon_code)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_demo())