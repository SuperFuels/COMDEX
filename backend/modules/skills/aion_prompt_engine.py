# backend/modules/skills/aion_prompt_engine.py

from typing import Dict, List

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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


def build_prompt_context(user_prompt: str) -> List[Dict[str, str]]:
    """
    Final message list to be sent to OpenAI/GPT. Injects system, skills, and user message.
    """
    return [
        get_aion_personality(),
        {"role": "system", "content": get_skill_context_string()},
        {"role": "user", "content": user_prompt}
    ]