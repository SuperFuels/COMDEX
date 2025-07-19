# File: backend/modules/dna_chain/llm_mutator.py

import openai
import os
from datetime import datetime

# ✅ Load API key from environment or config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ✅ Prompt template for mutation proposal
def build_mutation_prompt(file_path: str, original_code: str, context: str = "") -> str:
    return f"""
You are a code mutation engine (CRISPR-AI) helping an autonomous AI system improve itself.

The following Python source file is being considered for enhancement:

📁 File: {file_path}

Context:
{context}

--- Original Code Start ---
{original_code}
--- Original Code End ---

Your job is to propose improvements, optimizations, or ethical safeguards.
Return ONLY the new proposed code version (no explanations).
If no changes are needed, return the original code.
"""

# ✅ Mutation runner
def generate_mutation(file_path: str, original_code: str, context: str = "") -> dict:
    prompt = build_mutation_prompt(file_path, original_code, context)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are CRISPR-AI, a code mutation assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4096
        )
        new_code = response["choices"][0]["message"]["content"].strip()
        timestamp = datetime.utcnow().isoformat()

        return {
            "success": True,
            "file": file_path,
            "original_code": original_code,
            "new_code": new_code,
            "timestamp": timestamp,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 🧪 Quick test method (optional)
if __name__ == "__main__":
    test_path = "backend/modules/hexcore/sample_agent.py"
    with open(test_path, "r") as f:
        original = f.read()

    result = generate_mutation(test_path, original, context="Improve agent communication logic")

    if result["success"]:
        print("✅ Mutation Proposal:")
        print(result["new_code"])
    else:
        print("❌ Error:", result["error"])

    # ✅ Alias for compatibility
def query_gpt4(prompt: str) -> str:
    result = generate_mutation("generated.py", "N/A", context=prompt)
    if result["success"]:
        return result["new_code"]
    raise RuntimeError(result.get("error", "Unknown error"))