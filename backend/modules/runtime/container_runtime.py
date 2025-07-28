import time
import threading
import asyncio
from typing import Dict, Any, Optional

from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.websocket_manager import WebSocketManager, broadcast_glyph_event
from backend.modules.glyphos.glyph_watcher import GlyphWatcher
from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.glyphos.entanglement_utils import entangle_glyphs
from backend.modules.security.key_fragment_resolver import KeyFragmentResolver
from backend.modules.glyphos.glyph_trace_logger import glyph_trace 
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event 
from backend.modules.soullaw.soul_law_validator import SoulLawValidator
from backend.modules.glyphos.collapse_trace_exporter import export_collapse_trace

try:
    from backend.modules.glyphos.glyph_summary import summarize_glyphs
except ImportError:
    summarize_glyphs = None

ENCRYPTION_KEY = b'\x00' * 32  # Placeholder key


class ContainerRuntime:
    def __init__(self, state_manager: StateManager, tick_interval: float = 2.0):
        self.state_manager = state_manager
        self.executor = GlyphExecutor(state_manager)
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

        self.async_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._start_event_loop, daemon=True)
        self.loop_thread.start()

        self.vault_manager = ContainerVaultManager(ENCRYPTION_KEY)

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

    def run_loop(self):
        while self.running:
            tick_log = self.run_tick()
            self.logs.append(tick_log)

            if self.websocket:
                self.websocket.broadcast({"type": "tick_log", "data": tick_log})
                self.websocket.broadcast({
                    "type": "dimension_tick",
                    "data": {
                        "tick": self.tick_counter,
                        "timestamp": time.time()
                    }
                })

                if summarize_glyphs:
                    container = self.get_decrypted_current_container()
                    cubes = container.get("cubes", {})
                    summary = summarize_glyphs(cubes)
                    self.websocket.broadcast({"type": "glyph_summary", "data": summary})

            time.sleep(self.tick_interval)

    def run_tick(self) -> Dict[str, Any]:
        container = self.get_decrypted_current_container()
        cubes = container.get("cubes", {})
        tick_log = {"executed": []}

        if self.max_rewind > 0:
            self.rewind_buffer.append({"cubes": cubes.copy()})
            if len(self.rewind_buffer) > self.max_rewind:
                self.rewind_buffer.pop(0)

        self.glyph_watcher.scan_for_bytecode()

        for coord_str, data in cubes.items():
            if "glyph" in data and data["glyph"]:
                try:
                    x, y, z = map(int, coord_str.split(","))
                    print(f"⚙️ Executing glyph at {coord_str}")

                    if "↔" in data["glyph"]:
                        self.fork_entangled_path(container, coord_str, data["glyph"])
                        print(f"🔀 Entangled fork triggered at {coord_str}")

                    if "⧖" in data["glyph"]:
                        glyph_str = data["glyph"]
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

                    coro = self.executor.execute_glyph_at(x, y, z)
                    asyncio.run_coroutine_threadsafe(coro, self.async_loop)
                    tick_log["executed"].append(coord_str)

                except Exception as e:
                    print(f"❌ Failed to execute glyph at {coord_str}: {e}")

        self.tick_counter += 1
        tick_log["timestamp"] = time.time()
        tick_log["tick"] = self.tick_counter

        if self.loop_enabled and self.tick_counter % self.loop_interval == 0:
            if self.rewind_buffer:
                rewind_state = self.rewind_buffer[0]
                container["cubes"] = rewind_state["cubes"].copy()
                print("🔄 Container loop: state rewound.")

        self.apply_decay(container["cubes"])
        return tick_log

    def get_decrypted_current_container(self) -> Dict[str, Any]:
        container = self.state_manager.get_current_container()
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
            resolver.run_full_recombination(glyphs)
        except Exception as e:
            print(f"⚠️ Key fragment recombination failed: {e}")

        return container

    def save_container(self):
        container = self.state_manager.get_current_container()
        microgrid = self.vault_manager.get_microgrid()
        glyph_data = microgrid.export_index()

        # ✅ Inject SoulLaw collapse trace into container metadata
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

            print(f"🛰️ GlyphPush replay loaded into container: {target_container.get('id')}")
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


# ✅ Global instance
container_runtime = ContainerRuntime(StateManager())

def get_container_runtime():
    return container_runtime