#!/bin/zsh
set -e
PACKAGE_DIR="${0:A:h}"
cd "$PACKAGE_DIR"
if [ ! -x ".aion-venv/bin/python" ]; then
  /usr/bin/python3 -m venv .aion-venv
  .aion-venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
fi
export AION_SPEECH_MODEL_PATH="$PACKAGE_DIR/models/faster-whisper-base"
exec /usr/bin/caffeinate -is .aion-venv/bin/python -m backend.modules.aion_fabric.cli serve --demo --open-browser --autonomous-discovery --voice-control
