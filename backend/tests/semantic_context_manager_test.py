"""
Semantic Context Manager Test — Phase 43B
------------------------------------------
Verifies:
  - Synchronization with ConversationMemory
  - Correct short-term ↔ long-term topic management
  - Context summarization and recall

Run with:
  PYTHONPATH=. python backend/tests/semantic_context_manager_test.py
"""

import json
from backend.modules.aion_language.semantic_context_manager import CTX
from backend.modules.aion_language.conversation_memory import MEM

def run_tests():
    print("=== 🧪 SemanticContextManager Test Start ===")

    # Ensure conversation memory is seeded
    MEM.buffer.clear()
    MEM.remember("Hello Aion", "Hello, User.", emotion_state="neutral", semantic_field="greeting")
    MEM.remember("Can you stabilize drift?", "Stabilizing drift field...", emotion_state="focused", semantic_field="stability")
    MEM.remember("Forecast the next harmonic", "Predicting harmonic field...", emotion_state="analytical", semantic_field="resonance")
    MEM._save()

    # 1️⃣ Update CTX from memory
    CTX.update_from_memory()

    # 2️⃣ Print summarized context
    summary = CTX.summarize()
    print("\n--- Context Summary ---")
    print(json.dumps(summary, indent=2))

    # 3️⃣ Test topic recall queries
    print("\n--- Recall Tests ---")
    print("Recall 'stability':", CTX.recall_topic("stability"))
    print("Recall 'resonance':", CTX.recall_topic("resonance"))
    print("Recall 'unknown':", CTX.recall_topic("unknown"))

    # 4️⃣ Re-load to verify persistence
    from importlib import reload
    import backend.modules.aion_language.semantic_context_manager as scm
    reload(scm)
    new_CTX = scm.CTX
    print(f"\nReloaded context with {len(new_CTX.long_term)} long-term topics.")

    print("=== ✅ SemanticContextManager Test Complete ===")

if __name__ == "__main__":
    run_tests()