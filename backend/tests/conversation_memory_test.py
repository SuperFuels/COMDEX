"""
Conversation Memory Test — Phase 43A
------------------------------------
Validates short-term conversational memory:
- Storage of user ↔ system exchanges
- Recall of recent turns
- Semantic + emotional summarization

Run with:
  PYTHONPATH=. python backend/tests/conversation_memory_test.py
"""

import json
from backend.modules.aion_language.conversation_memory import MEM

def run_tests():
    print("=== 🧪 ConversationMemory Test Start ===")

    # 1️⃣ Clear current buffer for a clean test
    MEM.buffer.clear()
    MEM._save()

    # 2️⃣ Add several mock dialogue turns
    MEM.remember("Hello Aion", "Hello, User.", emotion_state="neutral", semantic_field="greeting")
    MEM.remember("Can you stabilize drift?", "Activating stabilizer...", emotion_state="focused", semantic_field="stability")
    MEM.remember("Forecast the next harmonic", "Forecasting resonance horizon...", emotion_state="analytical", semantic_field="resonance")

    # 3️⃣ Recall last 2 turns
    last_two = MEM.recall(2)
    print("\n--- Last 2 Exchanges ---")
    for turn in last_two:
        print(f"{turn['user_text']} → {turn['system_response']}")

    # 4️⃣ Summarize memory
    summary = MEM.summarize_context()
    print("\n--- Memory Summary ---")
    print(json.dumps(summary, indent=2))

    # 5️⃣ Validate persistence (reload test)
    print("\n--- Reload Check ---")
    from importlib import reload
    import backend.modules.aion_language.conversation_memory as cm
    reload(cm)
    new_MEM = cm.MEM
    print(f"Reloaded {len(new_MEM.buffer)} items from saved memory.")

    print("=== ✅ ConversationMemory Test Complete ===")

if __name__ == "__main__":
    run_tests()