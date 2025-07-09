# File: backend/scripts/run_consciousness.py

from backend.modules.consciousness.consciousness_manager import ConsciousnessManager

if __name__ == "__main__":
    manager = ConsciousnessManager()
    result = manager.run_cycle(mode="test")

    print(f"\n🧠 Cycle result: {result}")