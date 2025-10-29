#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🖥️ Photon Developer Console (CLI)
────────────────────────────────────────────
Developer interface for running and inspecting .ptn pages.
"""

import argparse
import json
from pathlib import Path
from backend.modules.ptn.ptn_runner import run_photon_page


def main():
    parser = argparse.ArgumentParser(
        description="Tessaris Photon Page Console — run and inspect .ptn capsules"
    )
    parser.add_argument("command", choices=["run", "inspect"], help="Action to perform")
    parser.add_argument("target", help="Path to .ptn file or keyword 'last'")
    args = parser.parse_args()

    if args.command == "run":
        result = run_photon_page(args.target)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "inspect":
        # TODO: Hook into PhotonMemoryGrid later
        print("Inspection mode placeholder — will attach to PhotonMemoryGrid trace.")


if __name__ == "__main__":
    main()