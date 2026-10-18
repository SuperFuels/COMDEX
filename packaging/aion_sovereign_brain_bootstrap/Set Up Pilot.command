#!/bin/zsh
set -e
PACKAGE_DIR="${0:A:h}"
cd "$PACKAGE_DIR"
if [ ! -x ".pilot-setup-venv/bin/python" ]; then
  /usr/bin/python3 -m venv .pilot-setup-venv
  .pilot-setup-venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
fi
exec .pilot-setup-venv/bin/python -m backend.modules.aion_business.runtime.sovereign_setup_service
