import time
import threading
import asyncio
from typing import Dict, Any, Optional
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.websocket_manager import WebSocketManager
from backend.modules.glyphos.glyph_watcher import GlyphWatcher

from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager

try:
    from backend.modules.glyphos.glyph_summary import summarize_glyphs
except ImportError:
    summarize_glyphs = None

# Stub: get encryption key from config/env securely in real system
ENCRYPTION_KEY = b'\x00' * 32  # 32-byte zero key placeholder

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

        # Initialize ContainerVaultManager for encryption/decryption of glyph cubes
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
                    # Use decrypted cubes for summary
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
        """
        Get current container with decrypted cubes loaded from encrypted storage.
        Fallback to plaintext cubes if no encrypted data found or decryption fails.
        """
        container = self.state_manager.get_current_container()
        encrypted_blob = container.get("encrypted_glyph_data")
        avatar_state = self.state_manager.get_avatar_state()

        if encrypted_blob:
            success = self.vault_manager.load_container_glyph_data(
                encrypted_blob,
                avatar_state=avatar_state
            )
            if success:
                # Replace cubes with decrypted glyph map
                container["cubes"] = self.vault_manager.get_microgrid().export_index()
                return container
            else:
                print("⚠️ Warning: Failed to decrypt container glyph data or access denied.")
                # Optionally fallback to unencrypted cubes for safety
                container["cubes"] = {}
                return container

        # No encrypted glyph data present, return as is
        return container

    def save_container(self):
        """
        Serialize current glyph data and encrypt before saving to container state.
        """
        container = self.state_manager.get_current_container()
        microgrid = self.vault_manager.get_microgrid()

        # Export glyph data currently loaded in microgrid
        glyph_data = microgrid.export_index()
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
        # Placeholder decay logic - implement as needed
        pass


# ✅ Global runtime instance for external access (must be outside class)
container_runtime = ContainerRuntime(StateManager())

def get_container_runtime():
    return container_runtime