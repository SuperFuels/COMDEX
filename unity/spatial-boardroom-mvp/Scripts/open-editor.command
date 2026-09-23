#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
unity_app="/Volumes/Install macOS Sonoma/Tessaris/Unity/Editors/6000.0.79f1/Unity/Unity.app"

if [[ ! -d "$unity_app" ]]; then
  print -u2 "Connect the Tessaris SD card before opening Spatial Boardroom."
  exit 1
fi

open -a "$unity_app" --args -projectPath "$project_dir"
