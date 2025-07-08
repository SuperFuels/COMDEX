import difflib
import json
import os
import datetime

from backend.modules.dna_chain.switchboard import get_module_path, read_module_file
from backend.modules.llm.llm_mutator import query_gpt4  # ✅ Updated path to LLM interface
from backend.modules.dna_chain.dna_registry import store_proposal

def generate_mutation_proposal(module_key, prompt_reason, override_path=None, dry_run=True):
    path = override_path or get_module_path(module_key)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"❌ Could not locate file for key '{module_key}'.")

    original_code = read_module_file(module_key) if not override_path else open(path, "r", encoding="utf-8").read()

    # 🔍 Construct prompt
    full_prompt = f"""You are CRISPR-AI. Your task is to intelligently mutate Python code.

Reason for mutation:
{prompt_reason}

--- ORIGINAL CODE START ---
{original_code}
--- ORIGINAL CODE END ---

Return the new code ONLY, with improved structure or logic.
"""

    mutated_code = query_gpt4(full_prompt).strip()

    # 🔄 Compute diff
    diff = "\n".join(difflib.unified_diff(
        original_code.splitlines(),
        mutated_code.splitlines(),
        fromfile="original.py",
        tofile="mutated.py",
        lineterm=""
    ))

    # 🧬 Build proposal object
    proposal = {
        "proposal_id": f"{module_key}_{datetime.datetime.utcnow().isoformat()}",
        "file": path,
        "reason": prompt_reason,
        "replaced_code": original_code,
        "new_code": mutated_code,
        "diff": diff,
        "approved": False,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "tokens_used": None,
        "confidence": None,
        "tests_passed": None
    }

    # 💾 Save proposal to registry
    store_proposal(proposal)

    if dry_run:
        print("✅ Proposal stored (dry-run mode).")
    else:
        print("⚠️ Live write is disabled for now — use DNA approval flow.")

    return proposal