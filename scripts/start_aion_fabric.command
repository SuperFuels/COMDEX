#!/bin/zsh
set -e
SCRIPT_DIR="${0:A:h}"
REPO_DIR="${SCRIPT_DIR:h}"
cd "$REPO_DIR"
exec /usr/bin/caffeinate -is "$REPO_DIR/.venv/bin/python" -m backend.modules.aion_fabric.cli serve --demo --open-browser --autonomous-discovery --voice-control
