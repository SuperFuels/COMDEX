#!/usr/bin/env python3
from backend.modules.aion_fabric.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["serve", "--demo", "--open-browser", "--autonomous-discovery"]))
