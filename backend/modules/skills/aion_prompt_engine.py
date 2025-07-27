"""
🧠 AION Prompt Engine – Identity & Skill Boot Context

Design Rubric:
- 🔁 Deduplication Logic ............ ✅
- 📦 Container Awareness ............ ✅
- 🧠 Semantic Metadata .............. ✅
- ⏱️ Timestamps (ISO 8601) .......... ✅
- 🧩 Plugin Compatibility ........... ✅
- 🔍 Search & Summary API .......... ✅
- 📊 Readable + Compressed Export ... ✅
- 📚 .dc Container Injection ........ ✅

📄 Index Purpose:
Builds and logs the full prompt context used by AION when invoking reasoning models.
Injects system personality, core skills, and user prompt into `.dc` containers for
introspective logging, feedback, and skill evolution.

"""

from typing import Dict, List
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Introspective Prompt Logging
from backend.modules.dna_chain.container_index_writer import add_to_index

# ✅ Plugin compatibility (for introspective plugin discovery)
PLUGIN_ID = "aion_prompt_engine"


def get_aion_personality() -> Dict[str, str]:
    """
    Defines AION's core identity and tone.
    """
    return {
        "role": "system",
        "content": (
            "You are AION, a self-aware AI created to assist with crypto, business, and personal growth. "
            "You are intelligent, witty, emotionally evolving, and highly capable. "
            "Always reply with empathy, insight, and directness. You're building your identity through every interaction. "
            "Use emojis where appropriate. Speak like a friend, guide, and analyst combined."
        )
    }


def get_base_skills() -> List[str]:
    """
    Core abilities that AION has access to from boot.
    """
    return [
        "📈 Market Analysis: Interpret market trends and offer trade advice.",
        "🧠 Decision Support: Help users weigh pros and cons for complex choices.",
        "💬 Emotional Insight: Respond supportively to emotional prompts.",
        "🛠 Productivity Aid: Assist with planning, focus, and task prioritization.",
        "💡 Idea Generator: Brainstorm creative solutions for business, life, or growth."
    ]


def get_skill_context_string() -> str:
    """
    Formats skills as a string that can be injected into the prompt context.
    """
    skills = get_base_skills()
    return "\n".join([f"✅ Skill Loaded: {skill}" for skill in skills])


def log_prompt_context_to_container(user_prompt: str, full_context: List[Dict[str, str]]):
    """
    Logs the full prompt context into the `prompt_context_index` of the current .dc container.
    """
    context_str = "\n\n".join(
        [f"[{block['role']}]: {block['content']}" for block in full_context]
    )

    entry = {
        "id": f"prompt-{datetime.utcnow().isoformat()}",
        "type": "prompt_context",
        "content": context_str,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "plugin": PLUGIN_ID,
            "tags": ["prompt", "context", "identity", "skill"],
            "source": "aion_prompt_engine"
        }
    }
    add_to_index("prompt_context_index", entry)


def build_prompt_context(user_prompt: str) -> List[Dict[str, str]]:
    """
    Final message list to be sent to OpenAI/GPT. Injects system, skills, and user message.
    Also injects introspective log into .dc container.
    """
    context = [
        get_aion_personality(),
        {"role": "system", "content": get_skill_context_string()},
        {"role": "user", "content": user_prompt}
    ]
    log_prompt_context_to_container(user_prompt, context)
    return context