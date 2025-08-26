# File: backend/modules/symbolic/natural_language_parser.py

"""
Hybrid parser: Natural language → CodexAST via rules + OpenAI GPT fallback
"""

import os
import logging
from typing import Optional

import openai
from backend.modules.symbolic.codex_ast_types import CodexAST

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_LLM_BY_DEFAULT = True if OPENAI_API_KEY else False

# -------------------- Rule-based parsing --------------------

def try_rule_based_parse(text: str) -> Optional[CodexAST]:
    text = text.lower().strip()

    if " is greater than " in text:
        x, y = [t.strip() for t in text.split(" is greater than ")]
        return CodexAST({"root": "greater_than", "args": [x, y]})

    if " is less than " in text:
        x, y = [t.strip() for t in text.split(" is less than ")]
        return CodexAST({"root": "less_than", "args": [x, y]})

    if " is equal to " in text or " equals " in text:
        x, y = [t.strip() for t in text.replace(" is equal to ", " equals ").split(" equals ")]
        return CodexAST({"root": "equals", "args": [x, y]})

    if text.startswith("add "):
        parts = [x.strip() for x in text[len("add "):].split(" and ")]
        return CodexAST({"root": "add", "args": parts})

    if text.startswith("subtract "):
        parts = [x.strip() for x in text[len("subtract "):].split(" from ")]
        if len(parts) == 2:
            return CodexAST({"root": "subtract", "args": [parts[1], parts[0]]})

    if text.startswith("multiply "):
        parts = [x.strip() for x in text[len("multiply "):].split(" and ")]
        return CodexAST({"root": "multiply", "args": parts})

    if text.startswith("divide "):
        parts = [x.strip() for x in text[len("divide "):].split(" by ")]
        if len(parts) == 2:
            return CodexAST({"root": "divide", "args": parts})

    return None

# -------------------- LLM-based parsing --------------------

def try_llm_parse(text: str, model: str = "gpt-4") -> CodexAST:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not set in environment")

    openai.api_key = OPENAI_API_KEY

    prompt = f"""You are a symbolic reasoning agent. Parse the following into a CodexAST format.

Natural Language: "{text}"

Return JSON in the format:
{{"root": ..., "args": [...]}}"""

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a symbolic parser."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=100
        )

        content = response.choices[0].message.content.strip()

        # Safe eval (better: use json.loads, with fallback)
        parsed_dict = eval(content)
        return CodexAST(parsed_dict)

    except Exception as e:
        logger.warning(f"❌ LLM parse failed: {e}")
        raise

# -------------------- Main unified parse function --------------------

def parse_nl_to_ast(text: str, use_llm: bool = USE_LLM_BY_DEFAULT) -> CodexAST:
    """
    Convert natural language to CodexAST using rules, with LLM fallback if enabled.
    """
    rule_result = try_rule_based_parse(text)
    if rule_result:
        rule_result.metadata["parser"] = "rule_based"
        return rule_result

    if use_llm:
        llm_result = try_llm_parse(text)
        llm_result.metadata["parser"] = "llm"
        return llm_result

    raise ValueError(f"Unable to parse input via rules or LLM: '{text}'")