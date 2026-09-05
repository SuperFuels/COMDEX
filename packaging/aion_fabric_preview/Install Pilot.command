#!/bin/zsh
set -e

SOURCE_DIR="${0:A:h}"
INSTALL_DIR="$HOME/Library/Application Support/Pilot Fabric"
AGENT_DIR="$HOME/Library/LaunchAgents"
AGENT_FILE="$AGENT_DIR/com.tessaris.pilot-fabric.plist"
PYTHON_BIN="$INSTALL_DIR/.pilot-venv/bin/python"

mkdir -p "$INSTALL_DIR" "$AGENT_DIR"
if [ "$SOURCE_DIR" != "$INSTALL_DIR" ]; then
  /usr/bin/ditto --noqtn "$SOURCE_DIR" "$INSTALL_DIR"
fi
if [ ! -x "$PYTHON_BIN" ]; then
  /usr/bin/python3 -m venv "$INSTALL_DIR/.pilot-venv"
fi
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$INSTALL_DIR/requirements.txt"

PLIST_TMP="$(mktemp)"
/bin/cat > "$PLIST_TMP" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.tessaris.pilot-fabric</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/caffeinate</string><string>-is</string>
    <string>$PYTHON_BIN</string><string>-m</string><string>backend.modules.aion_fabric.cli</string>
    <string>serve</string><string>--demo</string><string>--autonomous-discovery</string><string>--voice-control</string>
  </array>
  <key>WorkingDirectory</key><string>$INSTALL_DIR</string>
  <key>EnvironmentVariables</key><dict><key>AION_SPEECH_MODEL_PATH</key><string>$INSTALL_DIR/models/faster-whisper-base</string></dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$INSTALL_DIR/pilot.log</string>
  <key>StandardErrorPath</key><string>$INSTALL_DIR/pilot-error.log</string>
</dict></plist>
PLIST
/usr/bin/plutil -lint "$PLIST_TMP" >/dev/null
/bin/mv "$PLIST_TMP" "$AGENT_FILE"
/bin/chmod 600 "$AGENT_FILE"

/bin/launchctl bootout "gui/$(id -u)/com.tessaris.pilot-fabric" 2>/dev/null || true
/bin/launchctl bootstrap "gui/$(id -u)" "$AGENT_FILE"
/bin/launchctl enable "gui/$(id -u)/com.tessaris.pilot-fabric"
for attempt in {1..30}; do
  /usr/bin/curl -fsS "http://127.0.0.1:8765/health" >/dev/null 2>&1 && break
  /bin/sleep 1
done
/usr/bin/open "http://127.0.0.1:8765/"
echo "Pilot is installed. It will now start automatically and recover if it stops."
read -k 1 "?Press any key to close."
