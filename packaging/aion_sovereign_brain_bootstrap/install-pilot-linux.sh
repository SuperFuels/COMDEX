#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
  echo "Run this developer installer as root." >&2
  exit 1
fi
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
id tessaris >/dev/null 2>&1 || useradd --system --home /var/lib/tessaris --shell /usr/sbin/nologin tessaris
install -d -m 0755 /opt/tessaris/aion
install -d -o tessaris -g tessaris -m 0700 /var/lib/tessaris/pilot-brain
cp -R "$PACKAGE_DIR/payload/." /opt/tessaris/aion/
python3 -m venv /opt/tessaris/aion/runtime
/opt/tessaris/aion/runtime/bin/python -m pip install --disable-pip-version-check -r /opt/tessaris/aion/requirements.txt
install -m 0644 "$PACKAGE_DIR/pilot-aion-brain.service" /etc/systemd/system/pilot-aion-brain.service
systemctl daemon-reload
systemctl enable --now pilot-aion-brain.service
echo "Pilot AION Brain service installed. Run the local setup service to create the customer-owned brain."
