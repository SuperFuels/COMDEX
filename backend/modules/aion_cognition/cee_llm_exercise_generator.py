# ================================================================
# 🧠 CEE LLM Exercise Generator - Phase 45G.11
# ================================================================
"""
Generates batches of symbolic or lexical exercises using a large language model.
Each call can request multiple test items at once.
"""

import os
import json
import logging
import random
import time

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# Load environment variables from .env.local (and other .env files)
load_dotenv(dotenv_path=".env.local", override=True)

logger = logging.getLogger(__name__)

# Fetch the API key
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    logger.error("OpenAI API key not found in environment variable OPENAI_API_KEY. Aborting client creation.")
    raise OpenAIError("The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable. i️ See docs.")

# Initialize client with the key
client = OpenAI(api_key=_api_key)


# ================================================================
# 🧩 Exercise Batch Generator
# ================================================================
def generate_llm_exercise_batch(topic="physics", test_type="cloze", count=10, difficulty="medium"):
    """
    Request a batch of exercises from the LLM.
    Returns a list of normalized dicts matching CEE exercise schema.
    """
    prompt = f"""
    Generate {count} short {test_type} exercises on topic "{topic}" (difficulty: {difficulty}).
    Each item must be JSON with: type, prompt, options, answer.
    Do not repeat questions. Keep each under 100 characters.
    Return a JSON array only.
    """

    # -------------------------------
    # LLM Call
    # -------------------------------
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.error(f"[CEE-LLM] Request failed for topic '{topic}', type '{test_type}': {e}")
        return []

    # -------------------------------
    # Parse and normalize JSON
    # -------------------------------
    try:
        content = resp.choices[0].message.content
        data = json.loads(content)
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            logger.warning(f"[CEE-LLM] Unexpected output format: {data}")
            items = []
    except Exception as e:
        logger.error(f"[CEE-LLM] Failed to parse LLM response: {e}")
        logger.debug(f"Raw LLM content: {getattr(resp.choices[0].message, 'content', '')}")
        items = []

    # -------------------------------
    # Add timestamps and resonance metadata
    # -------------------------------
    for item in items:
        item.setdefault("type", test_type)
        item["resonance"] = {
            "ρ": round(random.uniform(0.6, 0.9), 3),
            "I": round(random.uniform(0.8, 1.0), 3),
            "SQI": round(random.uniform(0.7, 0.95), 3),
        }
        item["timestamp"] = time.time()

    logger.info(f"[CEE-LLM] Generated {len(items)} exercises for topic '{topic}'.")
    return items