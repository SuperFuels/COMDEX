# backend/modules/tests/entangle_test.py
import time

from backend.modules.runtime.container_runtime import get_container_runtime

# 1) Spin up the global ContainerRuntime
cr = get_container_runtime()
sm = cr.state_manager

# 2) Make a minimal in-memory container with a ↔ glyph
cid = "demo_entangle"
container = {
    "id": cid,
    "name": "Demo Entangle",
    "cubes": {
        # ↔ here is what triggers fork_entangled_path(...) in run_tick()
        "0,0,0": {"glyph": "↔ fork-me"}
    },
}

# 3) Register as the current container
sm.set_current_container(container)
cr.set_active_container(cid)

print("Before tick, current container id:", container.get("id"))

# 4) Run one tick – this will:
#    - decrypt/load current container
#    - see the glyph with ↔
#    - call fork_entangled_path(...)
tick_log = cr.run_tick()
print("Tick log:", tick_log)

# 5) Try to inspect any registry dict StateManager exposes
loaded = getattr(sm, "loaded_containers", None)
allc   = getattr(sm, "all_containers", None)

if isinstance(loaded, dict):
    print("Loaded containers:", list(loaded.keys()))
elif isinstance(allc, dict):
    print("All containers:", list(allc.keys()))
else:
    print("No explicit container registry on StateManager (only current container in memory).")

print("Done.")