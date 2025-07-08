# scripts/run_glyph_runtime.py
from backend.modules.runtime.container_runtime import run_glyph_runtime
from backend.modules.consciousness.state_manager import state_manager

if __name__ == "__main__":
    print("🚀 Triggering Glyph Runtime Tick")
    run_glyph_runtime(state_manager)