# File: backend/tests/test_self_rewrite_loop.py

import os
import time
import pytest
from backend.modules.dna_chain.dna_writer import create_proposal
from backend.modules.dna_chain.dna_switch import approve_proposal
from backend.modules.dna_chain.switchboard import get_module_path

TEST_MODULE = "backend/modules/skills/goal_engine.py"
ORIGINAL_CODE = "x = 1 + 1"
NEW_CODE = "x = 42  # rewritten by AION"
REASON = "Test rewrite contradiction"

@pytest.fixture(scope="module")
def setup_test_module():
    abs_path = get_module_path(TEST_MODULE)
    backup_path = abs_path + ".bak"

    # Backup original
    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
            original = f.read()
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(original)

    # Write dummy contradictory block
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(f"# TEST MODULE\n{ORIGINAL_CODE}\n")

    yield abs_path, backup_path

    # Cleanup
    if os.path.exists(backup_path):
        with open(backup_path, "r", encoding="utf-8") as f:
            restored = f.read()
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(restored)
        os.remove(backup_path)


def test_self_rewrite_flow(setup_test_module):
    abs_path, _ = setup_test_module

    # Create rewrite proposal
    proposal = create_proposal(
        file=TEST_MODULE,
        replaced_code=ORIGINAL_CODE,
        new_code=NEW_CODE,
        reason=REASON,
    )
    assert proposal["proposal_id"].startswith("py-backend_modules_skills_goal_engine")

    # Apply it via DNA switch
    result = approve_proposal(proposal["proposal_id"])
    assert result["status"] == "applied"

    # Confirm updated content
    with open(abs_path, "r", encoding="utf-8") as f:
        contents = f.read()
    assert NEW_CODE in contents