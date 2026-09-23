#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
unity_bin="/Volumes/Install macOS Sonoma/Tessaris/Unity/Editors/6000.0.79f1/Unity/Unity.app/Contents/MacOS/Unity"

if [[ ! -x "$unity_bin" ]]; then
  print -u2 "Connect the Tessaris SD card before building Spatial Boardroom."
  exit 1
fi

"$unity_bin" \
  -batchmode \
  -nographics \
  -quit \
  -projectPath "$project_dir" \
  -executeMethod Tessaris.SpatialBoardroom.Editor.SpatialBoardroomProjectSetup.BuildForBatch \
  -logFile "$project_dir/Logs/build-macos.log"

print "Built: $project_dir/Builds/macOS/Tessaris Spatial Boardroom.app"
