#!/bin/zsh
set -e

cd /Users/kevinrobinson/dev/COMDEX
exec .venv/bin/python -m backend.AION.system.aion_development_dashboard \
  --repo-root /Users/kevinrobinson/dev/COMDEX
