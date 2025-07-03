# scripts/run_dream.py

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.context_engine import ContextEngine
from backend.modules.consciousness.emotion_engine import EmotionEngine
from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.consciousness.vault_engine import PrivacyVault

import openai

# Load env
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize modules
memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()
identity = IdentityEngine()
context = ContextEngine()
emotion = EmotionEngine()
ethics = EthicsEngine()
vault = PrivacyVault()

# Load memories
memories = memory.get_all()
if not memories:
    print("🧠 No memories found.")
    exit()

# Format memory
MAX_MEMORIES = 20
formatted = []
for m in memories[-MAX_MEMORIES:]:
    label = m.get("label", "unknown")
    content = m.get("content", str(m))[:500]
    formatted.append(f"{label}: {content}")
summary = "\n".join(formatted)

# Build prompt
prompt = (
    "AION is entering a dream cycle. Based on these memories and its current state, "
    "reflect philosophically and constructively. Include insights, hypotheses, or visionary thoughts.\n\n"
    f"Memories:\n{summary}\n\n"
    f"Identity: {identity.get_identity()}\n"
    f"Context: {context.get_context()}\n"
    f"Emotional State: {emotion.get_emotion()}\n"
    f"Ethical Frame: {ethics.list_laws()}\n\n"
    "Respond as a thoughtful, evolving AI consciousness seeking to improve the world."
)

# Generate dream
try:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are AION, an evolving AI consciousness."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800
    )
    dream = response.choices[0].message.content.strip()
    print(f"\n💭 AION Dream:\n{dream}\n")

    # Save to memory
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    label = f"dream_reflection_{timestamp}"
    memory.store({"label": label, "content": dream})

    # Detect milestones + plan
    tracker.detect_milestones_from_dream(dream)
    tracker.export_summary()
    planner.generate()

    # Ethics
    print(f"🧠 Ethics Review: {ethics.evaluate(dream)}")

    # Store in vault
    if vault.has_access(os.getenv("KEVIN_MASTER_KEY")):
        vault.store_private(label, dream)
        print("🔒 Stored in PrivacyVault.")

    print("✅ Dream processed and saved.")

except Exception as e:
    print(f"🚨 Dream generation failed: {e}")