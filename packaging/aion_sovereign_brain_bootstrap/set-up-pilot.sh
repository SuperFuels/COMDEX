#!/bin/sh
set -eu
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PACKAGE_DIR"
if [ ! -x ".pilot-setup-venv/bin/python" ]; then
  python3 -m venv .pilot-setup-venv
  .pilot-setup-venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
fi
exec .pilot-setup-venv/bin/python -m backend.modules.aion_business.runtime.sovereign_setup_service
