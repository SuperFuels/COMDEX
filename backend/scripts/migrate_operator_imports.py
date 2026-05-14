#!/usr/bin/env python3
"""
Migration script to replace deprecated operator imports:
- entangle_op
- superpose_op
- measure_op

It will scan the codebase and replace imports/usages with their quantum_ops equivalents.
"""

import os
import re
import argparse

ROOT_DIR = "backend"
REPLACEMENTS = {
    r"from backend\.symatics\.operators\.entangle import entangle_op": "from backend.symatics.quantum_ops import entangle as entangle_op",
    r"from backend\.symatics\.operators\.superpose import superpose_op": "from backend.symatics.quantum_ops import superpose as superpose_op",
    r"from backend\.symatics\.operators\.measure import measure_op": "from backend.symatics.quantum_ops import measure as measure_op",
}

def migrate_file(path: str, apply: bool = False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    for pattern, replacement in REPLACEMENTS.items():
        new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        print(f"⚡ Found deprecated imports in: {path}")
        if apply:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ Updated {path}")

def walk_and_migrate(root: str, apply: bool = False):
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".py"):
                fpath = os.path.join(dirpath, fname)
                migrate_file(fpath, apply)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply fixes in-place")
    args = parser.parse_args()

    walk_and_migrate(ROOT_DIR, apply=args.apply)