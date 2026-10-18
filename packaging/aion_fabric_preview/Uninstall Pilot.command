#!/bin/zsh
set -e

INSTALL_DIR="$HOME/Library/Application Support/Pilot Fabric"
AGENT_FILE="$HOME/Library/LaunchAgents/com.tessaris.pilot-fabric.plist"
/bin/launchctl bootout "gui/$(id -u)/com.tessaris.pilot-fabric" 2>/dev/null || true
if [ -f "$AGENT_FILE" ]; then
  /bin/rm "$AGENT_FILE"
fi
echo "Pilot automatic startup has been removed."
echo "Your local Pilot data remains in $INSTALL_DIR so it can be restored."
echo "The folder can be moved to Trash separately if you also want to erase that data."
read -k 1 "?Press any key to close."
