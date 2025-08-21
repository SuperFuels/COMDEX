import time
import threading
import asyncio
from typing import Dict, Any, Optional

from backend.modules.consciousness.state_manager import StateManager
from backend.modules.websocket_manager import WebSocketManager, broadcast_event  
from backend.modules.glyphos.glyph_watcher import GlyphWatcher
from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.glyphos.entanglement_utils import entangle_glyphs
from backend.modules.security.key_fragment_resolver import KeyFragmentResolver
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.collapse.collapse_trace_exporter import export_collapse_trace
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.ucs.ucs_entanglement import entangle_containers
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.lean.lean_proofverifier import validate_lean_container

try:
    # ✅ Lazy import to avoid circular dependency
    from backend.modules.glyphos.glyph_executor import GlyphExecutor
except ImportError:
    GlyphExecutor = None

try:
    from backend.modules.glyphos.glyph_summary import summarize_glyphs
except ImportError:
    summarize_glyphs = None

ENCRYPTION_KEY = b'\x00' * 32  # Placeholder key


class ContainerRuntime:
    def __init__(self, state_manager: StateManager, tick_interval: float = 2.0):
        self.state_manager = state_manager
        self.executor = self._init_executor(state_manager)
        self.glyph_watcher = GlyphWatcher(state_manager)
        self.tick_interval = tick_interval
        self.running = False
        self.logs: list[Dict[str, Any]] = []
        self.websocket = WebSocketManager()
        self.tick_counter = 0
        self.loop_enabled = False
        self.loop_interval = 50
        self.rewind_buffer: list[Dict[str, Any]] = []
        self.max_rewind = 5
        self.ucs = ucs_runtime
        self.geometry_loader = UCSGeometryLoader()
        self.async_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._start_event_loop, daemon=True)
        self.loop_thread.start()
        self.ucs_features = UCSBaseContainer.global_features  # ✅ Apply UCS global features (time_dilation, gravity, micro_grid)
        self.vault_manager = ContainerVaultManager(ENCRYPTION_KEY)
        self._registered_once: set[str] = set()
        self._soullaw_checked_containers: set[str] = set()
        self._soul_law_checked = set() 

    def set_active_container(self, container_id: str):
        self.active_container_id = container_id
        self._soullaw_checked_containers.discard(container_id)  # or self._soullaw_checked_containers.clear() for per-session

    def load_and_activate_container(self, container_id: str) -> Dict[str, Any]:
        container = self.vault_manager.load_container_by_id(container_id)

        if container is None:
            raise ValueError(f"❌ Container '{container_id}' could not be loaded (got None).")

        if not isinstance(container, dict):
            raise TypeError(f"❌ Invalid container format for '{container_id}': expected dict, got {type(container).__name__}")

        # ✅ Set container in both internal runtime and state manager
        self.container = container
        self.state_manager.set_current_container(container)

        # ✅ Run predictions (B1/B2 logic) BEFORE decrypting
        try:
            from backend.modules.codex.codex_trace import CodexTrace

            prediction = run_prediction_on_container(container)
            if prediction.get("prediction_count", 0) > 0:
                self.state_manager.set_metadata("container_prediction", prediction)
                CodexTrace.log_prediction(prediction)
        except Exception as e:
            print(f"⚠️ Prediction failed for container '{container_id}': {e}")

        # ✅ Decrypt and finalize
        return self.get_decrypted_current_container()
    
    @staticmethod
    def load_container_from_path(path: str) -> dict:
        """
        Directly load a .dc.json container from file for testing.
        """
        from backend.modules.utils.file_loader import load_dc_container
        return load_dc_container(path)


    # Optional global instance (singleton pattern)
    container_runtime_instance: Optional["ContainerRuntime"] = None

    def _init_executor(self, state_manager: StateManager):
        """
        Lazy-initialize GlyphExecutor to break circular import chains.
        """
        global GlyphExecutor
        if 'GlyphExecutor' not in globals() or GlyphExecutor is None:
            from backend.modules.glyphos.glyph_executor import GlyphExecutor as GE
            GlyphExecutor = GE
        return GlyphExecutor(state_manager)

    def _get_glyph_trace(self):
        """
        Lazy loader for glyph_trace to avoid circular import.
        """
        from backend.modules.glyphos.glyph_trace_logger import glyph_trace
        return glyph_trace

    def _start_event_loop(self):
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_loop, daemon=True).start()
            print("▶️ Container Runtime started.")

    def stop(self):
        self.running = False
        print("⏹️ Container Runtime stopped.")

    from backend.modules.consciousness.prediction_engine import run_prediction_on_container

    def get_decrypted_current_container(self) -> Dict[str, Any]:
        container = self.state_manager.get_current_container()
        
        if container is None:
            raise ValueError("❌ No current container loaded (state_manager returned None)")

        encrypted_blob = container.get("encrypted_glyph_data")
        avatar_state = self.state_manager.get_avatar_state()

        if encrypted_blob:
            success = self.vault_manager.load_container_glyph_data(
                encrypted_blob,
                avatar_state=avatar_state
            )
            if success:
                container["cubes"] = self.vault_manager.get_microgrid().export_index()
            else:
                print("⚠️ Warning: Failed to decrypt container glyph data or access denied.")
                container["cubes"] = {}

        container_id = container.get("id")
        seed_links = container.get("entangled", [])
        for other_id in seed_links:
            if other_id and other_id != container_id:
                try:
                    entangle_glyphs("↔", container_id, other_id, sender="container_runtime", push=True)
                except Exception as e:
                    print(f"⚠️ Failed to seed-entangle {container_id} ↔ {other_id}: {e}")

        try:
            resolver = KeyFragmentResolver(container_id)
            glyphs = list(container.get("cubes", {}).values())
            resolver.recombine_all(glyphs)
        except Exception as e:
            print(f"⚠️ Key fragment recombination failed: {e}")

        if container.get("geometry"):
            self.geometry_loader.register_geometry(
                container.get("name", container_id),
                container.get("symbol", "❔"),
                container.get("geometry", "unknown")
            )
            self.ucs.save_container(container["id"], container)

        self._ensure_registry_entry(container)

        # 🧪 Atom Container Detection
        if container.get("container_kind") == "atom":
            container["isAtom"] = True
            container["electronCount"] = len(container.get("electrons", []))

            # 🔮 B1: Prediction logic for atom containers
            try:
                predictions = run_prediction_on_container(container)
                if predictions.get("prediction_count", 0) > 0:
                    logger.info(f"[SQI Predict] ✅ {predictions['prediction_count']} predictions made.")
                    container["predictions"] = predictions
            except Exception as e:
                logger.warning(f"[SQI Predict] ⚠️ Prediction failed: {e}")
        else:
            container["isAtom"] = False
            container["electronCount"] = 0
        from backend.modules.lean.lean_utils import is_lean_container
        # ✅ Lean Container Validation
        if is_lean_container(container):
            try:
                validate_lean_container(container)
            except Exception as e:
                logger.warning(f"⚠️ Lean container validation failed: {e}")

        return container

    def unload_container(self, container_id: str) -> bool:
        """
        Remove a container from local state and UCS; unregisters its address from the global registry.
        """
        try:
            # Drop from state manager memory
            self.state_manager.all_containers.pop(container_id, None)
            # Remove from UCS (this also attempts to unregister from the global registry, per your UCSRuntime.remove_container)
            try:
                self.ucs.remove_container(container_id)
            except Exception as e:
                print(f"⚠️ UCS remove_container failed for {container_id}: {e}")
            # Forget local "registered once" marker to allow re-add later if needed
            self._registered_once.discard(container_id)
            print(f"🧹 Unloaded container: {container_id}")
            return True
        except Exception as e:
            print(f"❌ unload_container error for {container_id}: {e}")
            return False
    def log_glyph_trace(self, container_id: str, data: dict):
        """
        Log glyph trace for a container (lazy import).
        """
        glyph_trace = self._get_glyph_trace()
        glyph_trace.record(container_id, data)

    def run_tick(self) -> Dict[str, Any]:
        container = self.get_decrypted_current_container()
        cubes = container.get("cubes", {})
        tick_log = {"executed": []}

        # ✅ Check SoulLaw once per container session
        cid = container.get("id")
        if cid and cid not in self._soullaw_checked_containers:
            try:
                self.ucs.soul_law.validate_access(container)
                self._soullaw_checked_containers.add(cid)
                print(f"🔒 UCS SoulLaw checked once for container {cid}.")
            except Exception as e:
                print(f"⚠️ UCS SoulLaw enforcement failed: {e}")

        # ✅ Maintain rewind buffer
        if self.max_rewind > 0:
            self.rewind_buffer.append({"cubes": cubes.copy()})
            if len(self.rewind_buffer) > self.max_rewind:
                self.rewind_buffer.pop(0)

        self.glyph_watcher.scan_for_bytecode()

        # ✅ Execute glyphs
        for coord_str, data in cubes.items():
            if "glyph" in data and data["glyph"]:
                try:
                    x, y, z = map(int, coord_str.split(","))
                    glyph_str = data["glyph"]
                    print(f"⚙️ Executing glyph at {coord_str}")

                    # ↔ Entanglement fork
                    if "↔" in glyph_str:
                        self.fork_entangled_path(container, coord_str, glyph_str)
                        print(f"🔀 Entangled fork triggered at {coord_str}")

                    # ⧖ SoulLaw collapse glyph
                    if "⧖" in glyph_str:
                        avatar_state = self.state_manager.get_avatar_state()
                        verdict = SoulLawValidator.evaluate_glyph(
                            glyph_str,
                            identity=avatar_state.get("id") if avatar_state else None
                        )

                        container.setdefault("soul_law_trace", []).append({
                            "coord": coord_str,
                            "glyph": glyph_str,
                            "verdict": verdict,
                            "tick": self.tick_counter,
                            "timestamp": time.time()
                        })

                        self.websocket.broadcast({
                            "type": "soul_law_event",
                            "data": {
                                "coord": coord_str,
                                "glyph": glyph_str,
                                "verdict": verdict,
                                "tick": self.tick_counter,
                                "timestamp": time.time(),
                                "container_id": container.get("id")
                            }
                        })

                        export_collapse_trace(
                            expression=glyph_str,
                            output=verdict,
                            adapter_name="SoulLawValidator",
                            identity=avatar_state.get("id") if avatar_state else None,
                            timestamp=time.time(),
                            extra={"coord": coord_str, "trigger_metadata": {"source": "ContainerRuntime"}}
                        )

                        broadcast_glyph_event({
                            "type": "glyph_execution",
                            "data": {
                                "glyph": glyph_str,
                                "tick": self.tick_counter,
                                "coord": coord_str,
                                "containerId": container.get("id", "unknown"),
                                "timestamp": time.time(),
                                "soul_law_verdict": verdict
                            }
                        })

                    # Asynchronous execution
                    coro = self.executor.execute_glyph_at(x, y, z)
                    asyncio.run_coroutine_threadsafe(coro, self.async_loop)
                    tick_log["executed"].append(coord_str)

                except Exception as e:
                    print(f"❌ Failed to execute glyph at {coord_str}: {e}")

        # ✅ Visual highlight
        if container.get("id"):
            try:
                self.ucs.visualizer.highlight(container["id"])
                print(f"🎨 UCS Visualization: Highlighted {container['id']} in GHX.")
            except Exception as e:
                print(f"⚠️ UCS visualization sync failed: {e}")

        self.tick_counter += 1
        tick_log["timestamp"] = time.time()
        tick_log["tick"] = self.tick_counter

        # ✅ Container rewind loop
        if self.loop_enabled and self.tick_counter % self.loop_interval == 0:
            if self.rewind_buffer:
                rewind_state = self.rewind_buffer[0]
                container["cubes"] = rewind_state["cubes"].copy()
                print("🔄 Container loop: state rewound.")

        self.apply_decay(container["cubes"])

        # ✅ Time dilation
        if self.ucs_features.get("time_dilation"):
            factor = self.ucs_features.get("time_dilation_factor", 1.0)
            time.sleep(self.tick_interval * (1 / factor))

        return tick_log

    def _ensure_registry_entry(self, container: Dict[str, Any]) -> None:
        cid = container.get("id")
        if not cid or cid in self._registered_once:
            return
        try:
            self.ucs.register_container(cid, container)
            self.ucs.save_container(cid, container)
            self._registered_once.add(cid)

            if container.get("geometry"):
                try:
                    self.geometry_loader.register_geometry(
                        container.get("name", cid),
                        container.get("symbol", "❔"),
                        container.get("geometry", "unknown"),
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ UCS registry ensure failed for {cid}: {e}")

    def save_container(self):
        container = self.state_manager.get_current_container()
        microgrid = self.vault_manager.get_microgrid()
        glyph_data = microgrid.export_index()

        from backend.modules.codex.symbolic_key_deriver import export_collapse_trace_with_soullaw_metadata
        try:
            avatar_state = self.state_manager.get_avatar_state()
            identity = avatar_state.get("id") if avatar_state else None
            collapse_metadata = export_collapse_trace_with_soullaw_metadata(identity=identity)
            container["collapse_metadata"] = collapse_metadata
            print("🔐 Injected SoulLaw collapse trace into container metadata.")
        except Exception as e:
            print(f"⚠️ Failed to inject collapse metadata: {e}")

        try:
            encrypted_blob = self.vault_manager.save_container_glyph_data(glyph_data)
            container["encrypted_glyph_data"] = encrypted_blob
            print(f"💾 Container glyph data encrypted and saved, size: {len(encrypted_blob)} bytes")
        except Exception as e:
            print(f"❌ Failed to encrypt and save container glyph data: {e}")

    def fork_entangled_path(self, container: Dict[str, Any], coord: str, glyph: str):
        original_name = container.get("id", "default")
        entangled_id = f"{original_name}_entangled"

        if entangled_id in self.state_manager.all_containers:
            print(f"↔ Entangled container {entangled_id} already exists.")
            return

        forked_container = {
            **container,
            "id": entangled_id,
            "origin": original_name,
            "entangled": True,
            "created_from": coord,
            "glyph": glyph,
            "cubes": container.get("cubes", {}).copy(),
            "metadata": {
                "entangled_from": original_name,
                "trigger_glyph": glyph,
                "fork_time": time.time()
            }
        }

        self.state_manager.all_containers[entangled_id] = forked_container
        print(f"🌌 Forked entangled container: {entangled_id}")

        # ✅ Register entanglement in UCS
        try:
            from backend.modules.dimensions.universal_container_system.ucs_entanglement import entangle_containers
            entangle_containers(original_name, entangled_id)
            print(f"↔ UCS entanglement registered: {original_name} ↔ {entangled_id}")
        except ImportError:
            print("⚠️ UCS entanglement module not found. Skipping UCS registration.")

        # ✅ Auto-register geometry in UCS (GHX sync)
        try:
            from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
            geometry_loader = UCSGeometryLoader()
            geometry_loader.register_geometry(
                forked_container.get("name", entangled_id),
                forked_container.get("symbol", "❔"),
                forked_container.get("geometry", "entangled")
            )
            print(f"🎨 UCS geometry synced for entangled container: {entangled_id}")
        except ImportError:
            print("⚠️ UCS geometry loader not found. Skipping auto-geometry sync.")

    def apply_decay(self, cubes: Dict[str, Any]):
        pass

    def load_glyphpush_packet(self, packet: TeleportPacket):
        try:
            target_container = self.state_manager.get_current_container()
            payload = packet.payload or {}

            trace = payload.get("replay_trace", [])
            cubes = trace[-1]["cubes"] if trace else {}

            target_container["cubes"] = cubes
            target_container["glyph_trace"] = trace
            target_container["trigger"] = payload.get("trigger", {})
            target_container["origin_snapshot"] = {
                "portal_id": packet.portal_id,
                "source": packet.source,
                "timestamp": packet.timestamp
            }

            if payload.get("collapse_trace"):
                target_container["collapse_trace"] = payload["collapse_trace"]
            if payload.get("entangled_identity"):
                target_container["entangled_identity"] = payload["entangled_identity"]

            # ✅ Sync to UCS runtime (register updated container state)
            self.ucs.save_container(target_container["id"], target_container)
            print(f"🛰️ GlyphPush replay loaded and UCS-synced for container: {target_container.get('id')}")

        except Exception as e:
            print(f"❌ Failed to load GlyphPush packet: {e}")

    async def run_replay(self, replay_glyphs: list[dict], container_id: Optional[str] = None):
        """
        Replays a sequence of glyphs with tick-based logging, entanglement links,
        and broadcasts glyph_replay WebSocket events for UI (H7).
        """
        container = self.get_decrypted_current_container()
        container_id = container_id or container.get("id", "unknown")

        start_tick = self.tick_counter
        replay_trace = []
        print(f"🎬 Starting glyph replay for container {container_id}...")

        for glyph_entry in replay_glyphs:
            coord = glyph_entry.get("coord", "0,0,0")
            glyph_str = glyph_entry.get("glyph", "")
            entangled = glyph_entry.get("entangled", [])

            # Execute glyph in runtime
            print(f"🔁 Replaying glyph: {glyph_str} @ {coord}")
            try:
                x, y, z = map(int, coord.split(","))
                await self.executor.execute_glyph_at(x, y, z)
            except Exception as e:
                print(f"❌ Replay execution failed for {coord}: {e}")

            # Append tick snapshot
            replay_trace.append({
                "tick": self.tick_counter,
                "coord": coord,
                "glyph": glyph_str,
                "entangled": entangled,
                "cubes": container.get("cubes", {}).copy()
            })

            # Broadcast incremental replay glyph
            await send_codex_ws_event("glyph_replay", {
                "glyph": glyph_str,
                "coord": coord,
                "tick": self.tick_counter,
                "entangled": entangled,
                "container_id": container_id,
                "timestamp": time.time()
            })

            self.tick_counter += 1
            await asyncio.sleep(self.tick_interval)

        end_tick = self.tick_counter

        # ✅ Log replay to glyph_trace
        glyph_trace.add_glyph_replay(
            glyphs=[g["glyph"] for g in replay_glyphs],
            tick_range=(start_tick, end_tick),
            container_id=container_id,
            replay_trace=replay_trace
        )

        # ✅ Broadcast replay complete (with snapshot)
        await send_codex_ws_event("glyph_replay_complete", {
            "container_id": container_id,
            "tick_start": start_tick,
            "tick_end": end_tick,
            "glyph_count": len(replay_glyphs),
            "snapshot": replay_trace[-1] if replay_trace else {}
        })

        print(f"✅ Glyph replay completed: {len(replay_glyphs)} glyphs from tick {start_tick} → {end_tick}")

from backend.modules.dimensions.container_expander import ContainerExpander

def expand_universal_container_system(container_id: str, direction: str = "z", layers: int = 1) -> str:
    """High-level wrapper for UCS-based expansion."""
    expander = ContainerExpander(container_id)
    return expander.grow_space(direction=direction, layers=layers)

def collapse_container(container_id: str) -> str:
    """Collapses a container (reduces runtime space and updates UCS)."""
    expander = ContainerExpander(container_id)
    result = expander.grow_space(direction="z", layers=-1)
    return f"🔻 Collapsed container {container_id}: {result}"

def get_container_runtime() -> 'ContainerRuntime':
    """
    Lazily initialize and return the global ContainerRuntime instance 
    to prevent circular imports.
    """
    global container_runtime_instance
    if container_runtime_instance is None:
        from backend.modules.consciousness.state_manager import StateManager
        container_runtime_instance = ContainerRuntime(StateManager())
    return container_runtime_instance

# --- 🔁 Electron-triggered QWave Teleport Logic ---

from backend.modules.glyphvault import vault_bridge
from backend.modules.teleport.teleport_packet import TeleportPacket


def teleport_to_linked_container(link_container_id: str) -> Dict[str, Any]:
    """
    Given a container ID from an electron node, teleport to its snapshot
    using symbolic Vault logic and runtime payload injection.
    """
    try:
        snapshot_id = vault_bridge.get_container_snapshot_id(link_container_id)
        print(f"[TELEPORT] Resolving snapshot for container: {link_container_id} → {snapshot_id}")

        teleport_packet = TeleportPacket(
            source_container_id="electronic_atom",
            target_container_id=link_container_id,
            snapshot_id=snapshot_id,
            payload={"trigger": "electron_click", "confidence": 0.95}
        )

        result = inject_payload(teleport_packet)
        print(f"[TELEPORT] Success: {result}")
        return {"status": "ok", "snapshot": snapshot_id}

    except Exception as e:
        print(f"[TELEPORT ERROR] Failed to teleport to {link_container_id}: {e}")
        return {"status": "error", "message": str(e)}