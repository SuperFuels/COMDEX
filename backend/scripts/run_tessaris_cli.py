# backend/scripts/run_tessaris_cli.py

import argparse
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.tessaris.thought_branch import ThoughtBranch

def run_tessaris(glyph, depth):
    engine = TessarisEngine(container_id="cli_container")
    print(f"[CLI] Seeding thought with glyph: {glyph}")
    thought_id, root = engine.seed_thought(glyph, source="cli")
    engine.expand_thought(thought_id, depth=depth)
    branch = ThoughtBranch.from_root(root, origin_id=thought_id)
    engine.execute_branch(branch)
    print("[CLI] Execution complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TessarisEngine from CLI")
    parser.add_argument("glyph", type=str, help="Glyph input to seed the thought (e.g. '⟦ Goal | Learn → Reflect ⟧')")
    parser.add_argument("--depth", type=int, default=2, help="Recursion depth for thought expansion")

    args = parser.parse_args()
    run_tessaris(args.glyph, args.depth)